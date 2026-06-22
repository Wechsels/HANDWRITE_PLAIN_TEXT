/**
 * 共享类型与 IPC 契约（移植自 src/render/layout.py 的 GlyphJob 等）。
 */
import type { RGBA } from './palette'

/** 布局阶段产出的单字形渲染任务。对应 Python `GlyphJob` dataclass。 */
export interface GlyphJob {
  char: string
  page: number
  x: number
  y: number
  font_size: number
  perturb_x_sigma: number
  perturb_y_sigma: number
  perturb_theta_sigma: number
  fill: RGBA
  underline: boolean
}

/** 可被选区覆盖的参数键。对应 Python `ADJUSTABLE_KEYS`。 */
export type AdjustableView =
  | 'font_size'
  | 'word_spacing'
  | 'perturb_x_sigma'
  | 'perturb_y_sigma'
  | 'perturb_theta_sigma'
  | 'fill'
  | 'alignment'
  | 'underline'

export type OverrideParams = Partial<Record<AdjustableView, number | RGBA | string | boolean>>

/** IPC：font 列表项。 */
export interface FontEntry {
  name: string
  path: string
}
