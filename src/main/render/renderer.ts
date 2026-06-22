/**
 * 渲染管线（移植自 src/render/renderer.py）。
 *
 * 把 DocumentModel 渲染为分页 RGBA 位图。用 Uint8ClampedArray 缓冲替代 PIL Image，
 * 用 @napi-rs/canvas 编码 PNG。笔画扰动委托 perturbGlyph。
 */
import { createCanvas, type SKRSContext2D } from '@napi-rs/canvas'
import type { DocumentModel } from '@shared/settings'
import type { RGBA } from '@shared/palette'
import type { GlyphJob } from '@shared/types'
import { layoutDocument } from './layout'
import { getRasterized } from './fontCache'
import { perturbGlyph, type RGBA as FillRGBA } from './perturb'
import { makeRng, type Rng } from './rand'
import { registry } from '../premium'

export class RenderError extends Error {}

export interface PageImage {
  width: number
  height: number
  data: Uint8ClampedArray
}

function fillBackground(buf: Uint8ClampedArray, bg: RGBA): void {
  const [r, g, b, a] = bg
  for (let i = 0; i < buf.length; i += 4) {
    buf[i] = r
    buf[i + 1] = g
    buf[i + 2] = b
    buf[i + 3] = a
  }
}

function drawUnderline(
  buf: Uint8ClampedArray,
  w: number,
  h: number,
  job: GlyphJob,
  inkWidth: number
): void {
  const uy = Math.floor(job.y + job.font_size)
  const thickness = Math.max(1, Math.floor(Math.max(job.font_size, 1) / 10))
  const x0 = Math.floor(job.x)
  const x1 = Math.floor(job.x + inkWidth)
  const [r, g, b, a] = job.fill
  for (let ty = uy; ty < uy + thickness; ty++) {
    if (ty < 0 || ty >= h) continue
    for (let tx = x0; tx <= x1; tx++) {
      if (tx < 0 || tx >= w) continue
      const idx = (ty * w + tx) * 4
      buf[idx] = r
      buf[idx + 1] = g
      buf[idx + 2] = b
      buf[idx + 3] = a
    }
  }
}

function renderGlyph(
  buf: Uint8ClampedArray,
  w: number,
  h: number,
  job: GlyphJob,
  fontPath: string,
  rand: Rng
): void {
  const r = getRasterized(fontPath, job.font_size, job.char)
  if (!r || !r.inkBbox) return
  const pad = Math.max(job.font_size, 1)
  const inkWidth = r.inkBbox[2] - r.inkBbox[0]
  const offset: [number, number] = [job.x - pad, job.y - pad]
  const inkAt = (x: number, y: number): boolean =>
    r.alpha[y * r.scratchW + x] >= 128
  const fill: FillRGBA = {
    r: job.fill[0],
    g: job.fill[1],
    b: job.fill[2],
    a: job.fill[3]
  }
  perturbGlyph(
    inkAt,
    r.inkBbox,
    buf,
    w,
    h,
    offset,
    job.perturb_x_sigma,
    job.perturb_y_sigma,
    job.perturb_theta_sigma,
    fill,
    rand
  )
  if (job.underline) drawUnderline(buf, w, h, job, inkWidth)
}

export function renderPages(
  model: DocumentModel,
  seed: number | null = null,
  save = true
): { pages: PageImage[]; paths: string[] } {
  const gp = model.global_params
  if (gp.font_size > gp.line_spacing) {
    throw new RenderError('font_size 必须 <= line_spacing')
  }
  if (gp.paper_w <= 0 || gp.paper_h <= 0) {
    throw new RenderError('纸张宽高必须为正')
  }

  const rand = makeRng(seed)
  const { pages, pageSize } = layoutDocument(model, rand)
  const [cw, ch] = pageSize
  const bg = gp.background
  const result: PageImage[] = []

  for (const pageJobs of pages) {
    const buf = new Uint8ClampedArray(cw * ch * 4)
    fillBackground(buf, bg)
    for (const job of pageJobs) {
      renderGlyph(buf, cw, ch, job, gp.font_path, rand)
    }
    const enhanced = registry.enhanceImage(buf, cw, ch, { font_path: gp.font_path })
    result.push({ width: cw, height: ch, data: enhanced })
  }

  const paths: string[] = []
  if (save) paths.push(...saveOutputs(result))
  return { pages: result, paths }
}

/** 把页面位图编码为 PNG 落盘到 OUTPUTS_DIR，清掉旧 png。返回文件路径列表。 */
export function saveOutputs(images: PageImage[]): string[] {
  // 延迟引入 paths，避免循环依赖 & 让 worker 也可用
  const { OUTPUTS_DIR } = require('../paths') as { OUTPUTS_DIR: string }
  const fs = require('node:fs') as typeof import('node:fs')
  const path = require('node:path') as typeof import('node:path')
  fs.mkdirSync(OUTPUTS_DIR, { recursive: true })
  for (const f of fs.readdirSync(OUTPUTS_DIR)) {
    if (f.endsWith('.png')) {
      try {
        fs.unlinkSync(path.join(OUTPUTS_DIR, f))
      } catch {
        /* ignore */
      }
    }
  }
  const outPaths: string[] = []
  images.forEach((im, i) => {
    const canvas = createCanvas(im.width, im.height)
    const ctx = canvas.getContext('2d') as SKRSContext2D
    const imageData = ctx.createImageData(im.width, im.height)
    imageData.data.set(im.data)
    ctx.putImageData(imageData, 0, 0)
    const p = path.join(OUTPUTS_DIR, `${i}.png`)
    fs.writeFileSync(p, canvas.toBuffer('image/png'))
    outPaths.push(p)
  })
  return outPaths
}
