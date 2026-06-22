/**
 * 调色板与枚举选项（移植自 src/palette.py）。
 * 颜色为 [r, g, b, a] 元组，与 Python 版 RGBA 一致。
 */

export type RGBA = [number, number, number, number]

export const FONT_COLOR_DICT: Record<string, RGBA> = {
  black: [0, 0, 0, 255],
  white: [255, 255, 255, 255],
  red: [255, 0, 0, 255],
  blue: [0, 0, 255, 255]
}

export const BACKGROUND_COLOR_DICT: Record<string, RGBA> = {
  transparent: [0, 0, 0, 0],
  white: [255, 255, 255, 255]
}

export const RATE_DICT: Record<string, number> = {
  x1: 1,
  x2: 2,
  x4: 4,
  x8: 8,
  x16: 16,
  x32: 32,
  x64: 64
}

export const ALIGNMENT_OPTIONS: readonly string[] = ['left', 'center'] as const

export const DEFAULT_FILL: RGBA = [0, 0, 0, 255]
export const DEFAULT_BACKGROUND: RGBA = [255, 255, 255, 255]

export function tupleEquals(a: RGBA, b: RGBA): boolean {
  return a[0] === b[0] && a[1] === b[1] && a[2] === b[2] && a[3] === b[3]
}
