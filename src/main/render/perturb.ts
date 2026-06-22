/**
 * 笔画级扰动（移植自 src/render/perturb.py，vendored 自 handright BSD-3-Clause）。
 *
 * 改动点与 Python 版一致：逐字形提取笔画，接受逐字形 sigma 与目标画布偏移，
 * 写入 RGBA 画布。此处把 PIL "1" 位图替换为 `inkAt(x,y)` 谓词，
 * 把 PIL `canvas.load()[x,y]=fill` 替换为对 RGBA Uint8ClampedArray 的直接写入。
 */

const _MAX_INT16_VALUE = 0xffff

type BBox = [number, number, number, number] // [left, upper, right, lower]
type Pt = [number, number]

/** 提取所有笔画（4 邻域连通墨迹分量），返回每笔的像素点列表。 */
function extractStrokes(inkAt: (x: number, y: number) => boolean, bbox: BBox): Pt[][] {
  const [left, upper, right, lower] = bbox
  if (right >= _MAX_INT16_VALUE || lower >= _MAX_INT16_VALUE) {
    throw new Error('glyph bitmap too large for stroke extraction')
  }
  const visited = new Set<number>()
  const key = (x: number, y: number): number => (x << 16) | y
  const strokes: Pt[][] = []

  for (let y = upper; y < lower; y++) {
    for (let x = left; x < right; x++) {
      if (!inkAt(x, y) || visited.has(key(x, y))) continue
      // flood fill 一个连通分量 = 一笔
      const stroke: Pt[] = []
      const stack: Pt[] = [[x, y]]
      visited.add(key(x, y))
      while (stack.length) {
        const [cx, cy] = stack.pop()!
        stroke.push([cx, cy])
        if (cy - 1 >= upper && inkAt(cx, cy - 1) && !visited.has(key(cx, cy - 1))) {
          visited.add(key(cx, cy - 1)); stack.push([cx, cy - 1])
        }
        if (cy + 1 < lower && inkAt(cx, cy + 1) && !visited.has(key(cx, cy + 1))) {
          visited.add(key(cx, cy + 1)); stack.push([cx, cy + 1])
        }
        if (cx - 1 >= left && inkAt(cx - 1, cy) && !visited.has(key(cx - 1, cy))) {
          visited.add(key(cx - 1, cy)); stack.push([cx - 1, cy])
        }
        if (cx + 1 < right && inkAt(cx + 1, cy) && !visited.has(key(cx + 1, cy))) {
          visited.add(key(cx + 1, cy)); stack.push([cx + 1, cy])
        }
      }
      strokes.push(stroke)
    }
  }
  return strokes
}

function rotate(center: Pt, x: number, y: number, theta: number): Pt {
  if (theta === 0) return [x, y]
  const cosT = Math.cos(theta)
  const sinT = Math.sin(theta)
  const dx = x - center[0]
  const dy = y - center[1]
  return [dx * cosT + dy * sinT + center[0], dy * cosT - dx * sinT + center[1]]
}

export interface RGBA { r: number; g: number; b: number; a: number }

/**
 * 在 scratch 位图 `inkAt` 的 `inkBbox` 区域提取笔画，按 sigma 扰动后写入页面 RGBA 缓冲。
 *
 * @param pageData 页面 RGBA 缓冲（Uint8ClampedArray）
 * @param pageW    页面宽
 * @param pageH    页面高
 * @param offset   (ox, oy) 笔画像素落点的全局偏移
 * @param fill     RGBA 填充
 * @param rand     种子化随机源
 */
export function perturbGlyph(
  inkAt: (x: number, y: number) => boolean,
  inkBbox: BBox,
  pageData: Uint8ClampedArray,
  pageW: number,
  pageH: number,
  offset: Pt,
  sigmaX: number,
  sigmaY: number,
  sigmaTheta: number,
  fill: RGBA,
  rand: { gauss: (mu: number, sigma: number) => number }
): void {
  const strokes = extractStrokes(inkAt, inkBbox)
  const [ox, oy] = offset
  for (const stroke of strokes) {
    if (stroke.length === 0) continue
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const [x, y] of stroke) {
      if (x < minX) minX = x
      if (x > maxX) maxX = x
      if (y < minY) minY = y
      if (y > maxY) maxY = y
    }
    const center: Pt = [(minX + maxX) / 2, (minY + maxY) / 2]
    const dx = rand.gauss(0, sigmaX)
    const dy = rand.gauss(0, sigmaY)
    const theta = rand.gauss(0, sigmaTheta)
    for (const [lx, ly] of stroke) {
      const [nx, ny] = rotate(center, lx, ly, theta)
      const tx = Math.round(nx + ox + dx)
      const ty = Math.round(ny + oy + dy)
      if (tx >= 0 && tx < pageW && ty >= 0 && ty < pageH) {
        const idx = (ty * pageW + tx) * 4
        pageData[idx] = fill.r
        pageData[idx + 1] = fill.g
        pageData[idx + 2] = fill.b
        pageData[idx + 3] = fill.a
      }
    }
  }
}
