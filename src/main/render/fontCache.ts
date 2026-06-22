/**
 * 字体注册与字形光栅化缓存（移植自 src/render/font_cache.py）。
 *
 * 用 @napi-rs/canvas 替代 PIL ImageFont/ImageDraw：
 * - `GlobalFonts.registerFromPath` 一次性注册 TTF，缓存 fontPath→family。
 * - 单字形渲染到 scratch canvas，读 alpha 通道扫描真实墨迹 bbox（等价 PIL `font.getbbox`）。
 */
import { GlobalFonts, createCanvas, type SKRSContext2D } from '@napi-rs/canvas'

const _FAMILY_CACHE = new Map<string, string>()
const _MISSING = new Set<string>()

/** 墨迹阈值：alpha >= INK_THRESHOLD 视为落墨（模拟 PIL "1" 模式的 mono 二值化）。 */
const INK_THRESHOLD = 128

export function getFontFamily(fontPath: string): string | null {
  const cached = _FAMILY_CACHE.get(fontPath)
  if (cached) return cached
  if (_MISSING.has(fontPath)) return null

  // family 名用文件名 stem，保证唯一可引用
  const base = fontPath.replace(/[/\\]+/g, '/').split('/').pop() ?? fontPath
  const stem = base.replace(/\.[^.]+$/, '')
  const family = `hw_${stem}`
  try {
    const ok = GlobalFonts.registerFromPath(fontPath, family)
    if (!ok) {
      _MISSING.add(fontPath)
      return null
    }
  } catch {
    _MISSING.add(fontPath)
    return null
  }
  _FAMILY_CACHE.set(fontPath, family)
  return family
}

export function clearFontCache(): void {
  _FAMILY_CACHE.clear()
  _MISSING.clear()
  _GLYPH_CACHE.clear()
}

/** 缓存 key：fontPath|size|char —— layout 测宽与 renderer 绘制共用同一份光栅化结果。 */
const _GLYPH_CACHE = new Map<string, RasterizedGlyph>()

export function getRasterized(fontPath: string, size: number, char: string): RasterizedGlyph | null {
  const key = `${fontPath}|${size}|${char}`
  const hit = _GLYPH_CACHE.get(key)
  if (hit) return hit
  const family = getFontFamily(fontPath)
  if (!family) return null
  const r = rasterizeGlyph(family, size, char)
  _GLYPH_CACHE.set(key, r)
  return r
}

/** 字形墨迹宽度（advance），等价 Python `font.getbbox(ch)` 的 `r - l`。 */
export function getInkWidth(fontPath: string, size: number, char: string): number {
  const r = getRasterized(fontPath, size, char)
  if (!r || !r.inkBbox) return 0
  return r.inkBbox[2] - r.inkBbox[0]
}

export interface RasterizedGlyph {
  scratchW: number
  scratchH: number
  /** RGBA 像素数据，alpha 通道用于判定落墨。 */
  alpha: Uint8Array
  /** 墨迹 bbox [left, upper, right, lower]（scratch 坐标，半开区间）。无墨迹时为 null。 */
  inkBbox: [number, number, number, number] | null
}

/**
 * 渲染单字形到 scratch canvas 并返回 alpha + 墨迹 bbox。
 * 等价 Python: `Image.new("1",(3*pad,3*pad)); ImageDraw.text((pad,pad),char,fill=1,font=font); font.getbbox(char)`。
 */
export function rasterizeGlyph(family: string, size: number, char: string): RasterizedGlyph {
  const pad = Math.max(size, 1)
  const dim = 3 * pad
  const canvas = createCanvas(dim, dim)
  const ctx = canvas.getContext('2d') as SKRSContext2D
  ctx.clearRect(0, 0, dim, dim)
  ctx.fillStyle = 'rgba(0,0,0,0)'
  ctx.font = `${size}px "${family}"`
  ctx.textBaseline = 'top'
  ctx.textAlign = 'left'
  ctx.fillStyle = '#ffffff'
  ctx.fillText(char, pad, pad)

  const imageData = ctx.getImageData(0, 0, dim, dim)
  const data = imageData.data
  const alpha = new Uint8Array(dim * dim)
  for (let i = 0; i < alpha.length; i++) {
    alpha[i] = data[i * 4 + 3]
  }

  // 扫描真实墨迹 bbox
  let minX = dim, minY = dim, maxX = -1, maxY = -1
  for (let y = 0; y < dim; y++) {
    for (let x = 0; x < dim; x++) {
      if (alpha[y * dim + x] >= INK_THRESHOLD) {
        if (x < minX) minX = x
        if (x > maxX) maxX = x
        if (y < minY) minY = y
        if (y > maxY) maxY = y
      }
    }
  }
  const inkBbox: [number, number, number, number] | null =
    maxX < 0 ? null : [minX, minY, maxX + 1, maxY + 1]

  return { scratchW: dim, scratchH: dim, alpha, inkBbox }
}
