/**
 * 文档模型与选区覆盖逻辑（移植自 src/config/settings.py）。
 * 纯逻辑，无 node/浏览器 API，由 renderer 与 main worker 共用。
 *
 * 关键不变量与 Python 版逐行对齐：
 * - set_range: 在 [start,end) 上 split/trim 现有段，合并新参数，gap 区域写入全新 override，最后合并相邻同参数段。
 * - clear_range: 在 [start,end) 内删除 override，保留外侧。
 * - effective_params: 全局参数叠加覆盖 index 的段。
 */
import type { OverrideParams, AdjustableView } from './types'
import type { RGBA } from './palette'
import { DEFAULT_FILL, DEFAULT_BACKGROUND } from './palette'

export const ADJUSTABLE_KEYS: readonly AdjustableView[] = [
  'font_size',
  'word_spacing',
  'perturb_x_sigma',
  'perturb_y_sigma',
  'perturb_theta_sigma',
  'fill',
  'alignment',
  'underline'
] as const

/** 全局渲染参数。默认值与 Python `GlobalParams` dataclass 完全一致。 */
export interface GlobalParams {
  paper_w: number
  paper_h: number
  font_path: string
  font_size: number
  line_spacing: number
  word_spacing: number
  margin_top: number
  margin_bottom: number
  margin_left: number
  margin_right: number
  fill: RGBA
  background: RGBA
  rate: number
  line_spacing_sigma: number
  font_size_sigma: number
  word_spacing_sigma: number
  perturb_x_sigma: number
  perturb_y_sigma: number
  perturb_theta_sigma: number
  alignment: string
  underline: boolean
}

export function defaultGlobalParams(fontPath = ''): GlobalParams {
  return {
    paper_w: 667,
    paper_h: 945,
    font_path: fontPath,
    font_size: 30,
    line_spacing: 70,
    word_spacing: 1,
    margin_top: 10,
    margin_bottom: 10,
    margin_left: 10,
    margin_right: 10,
    fill: [...DEFAULT_FILL] as RGBA,
    background: [...DEFAULT_BACKGROUND] as RGBA,
    rate: 4,
    line_spacing_sigma: 1.0,
    font_size_sigma: 1.0,
    word_spacing_sigma: 1.0,
    perturb_x_sigma: 1.0,
    perturb_y_sigma: 1.0,
    perturb_theta_sigma: 0.05,
    alignment: 'left',
    underline: false
  }
}

export interface RangeOverride {
  start: number
  end: number
  params: OverrideParams
}

export function rangeOverrideFromDict(d: {
  start: number
  end: number
  params?: Record<string, unknown>
}): RangeOverride {
  return {
    start: Number(d.start),
    end: Number(d.end),
    params: { ...(d.params ?? {}) }
  }
}

export interface DocumentModel {
  text: string
  global_params: GlobalParams
  overrides: RangeOverride[]
}

export function createDocumentModel(fontPath = ''): DocumentModel {
  return {
    text: '',
    global_params: defaultGlobalParams(fontPath),
    overrides: []
  }
}

export function globalParamsToDict(gp: GlobalParams): Record<string, unknown> {
  return { ...gp }
}

export function globalParamsFromDict(d: Record<string, unknown>): GlobalParams {
  const base = defaultGlobalParams()
  const out: GlobalParams = { ...base }
  for (const k of Object.keys(base) as (keyof GlobalParams)[]) {
    if (k in d && d[k] !== undefined && d[k] !== null) {
      // @ts-expect-error 受控赋值：键来自 base 自身
      out[k] = d[k]
    }
  }
  return out
}

export function rangeOverrideToDict(o: RangeOverride): Record<string, unknown> {
  return { start: o.start, end: o.end, params: { ...o.params } }
}

export function documentToDict(m: DocumentModel): Record<string, unknown> {
  return {
    text: m.text,
    global_params: globalParamsToDict(m.global_params),
    overrides: m.overrides.map(rangeOverrideToDict)
  }
}

export function documentFromDict(d: Record<string, unknown>): DocumentModel {
  const gp = globalParamsFromDict(
    (d.global_params as Record<string, unknown>) ?? {}
  )
  const overrides = ((d.overrides as Array<{ start: number; end: number; params?: Record<string, unknown> }>) ?? []).map(
    rangeOverrideFromDict
  )
  return {
    text: (d.text as string) ?? '',
    global_params: gp,
    overrides
  }
}

/** 提取一个 override params 对象中合法的 adjustable 键（值非 null/undefined）。 */
function cleanParams(params: Record<string, unknown>): OverrideParams {
  const cleaned: OverrideParams = {}
  for (const k of ADJUSTABLE_KEYS) {
    const v = (params as Record<string, unknown>)[k]
    if (v !== undefined && v !== null) {
      // @ts-expect-error 受控赋值
      cleaned[k] = v
    }
  }
  return cleaned
}

function clampRange(n: number, start: number, end: number): [number, number] {
  start = Math.max(0, Math.min(start, n))
  end = Math.max(start, Math.min(end, n))
  return [start, end]
}

export class DocumentModelOps {
  /** 在 model 上原地操作：合并 newParams 到 [start,end)。 */
  static setRange(model: DocumentModel, start: number, end: number, newParams: OverrideParams): void {
    const n = model.text.length
    ;[start, end] = clampRange(n, start, end)
    const cleaned = cleanParams(newParams as Record<string, unknown>)
    if (start >= end || Object.keys(cleaned).length === 0) return

    DocumentModelOps.splitAt(model, start)
    DocumentModelOps.splitAt(model, end)

    const inside = model.overrides.filter((s) => s.start >= start && s.end <= end)
    for (const seg of inside) {
      Object.assign(seg.params, cleaned)
    }

    const covered = [...inside].sort((a, b) => a.start - b.start)
    const gaps: RangeOverride[] = []
    let cursor = start
    for (const seg of covered) {
      if (seg.start > cursor) {
        gaps.push({ start: cursor, end: seg.start, params: { ...cleaned } })
      }
      cursor = seg.end
    }
    if (cursor < end) {
      gaps.push({ start: cursor, end, params: { ...cleaned } })
    }

    model.overrides.push(...gaps)
    model.overrides.sort((a, b) => a.start - b.start)
    DocumentModelOps.mergeAdjacent(model)
  }

  /** 删除 [start,end) 内的 override，保留外侧。 */
  static clearRange(model: DocumentModel, start: number, end: number): void {
    const n = model.text.length
    ;[start, end] = clampRange(n, start, end)
    if (start >= end) return
    DocumentModelOps.splitAt(model, start)
    DocumentModelOps.splitAt(model, end)
    model.overrides = model.overrides.filter(
      (s) => !(s.start >= start && s.end <= end)
    )
  }

  /** 把任意跨越 point 的段切两段。point 越界则不动。 */
  static splitAt(model: DocumentModel, point: number): void {
    if (point <= 0 || point >= model.text.length) return
    const newList: RangeOverride[] = []
    for (const seg of model.overrides) {
      if (seg.start < point && point < seg.end) {
        newList.push({ start: seg.start, end: point, params: { ...seg.params } })
        newList.push({ start: point, end: seg.end, params: { ...seg.params } })
      } else {
        newList.push(seg)
      }
    }
    model.overrides = newList
  }

  /** 合并相邻且参数相同的段。 */
  static mergeAdjacent(model: DocumentModel): void {
    if (model.overrides.length === 0) return
    const merged: RangeOverride[] = [model.overrides[0]]
    for (const seg of model.overrides.slice(1)) {
      const last = merged[merged.length - 1]
      if (last.end === seg.start && paramsEqual(last.params, seg.params)) {
        last.end = seg.end
      } else {
        merged.push(seg)
      }
    }
    model.overrides = merged
  }

  static overrideAt(model: DocumentModel, index: number): RangeOverride | null {
    for (const seg of model.overrides) {
      if (seg.start <= index && index < seg.end) return seg
    }
    return null
  }

  /** 全局参数叠加覆盖 index 的段。 */
  static effectiveParams(model: DocumentModel, index: number): Record<string, unknown> {
    const base = globalParamsToDict(model.global_params) as Record<string, unknown>
    const seg = DocumentModelOps.overrideAt(model, index)
    if (seg) Object.assign(base, seg.params)
    return base
  }

  static rangesForMarking(model: DocumentModel): Array<[number, number]> {
    return model.overrides.map((s) => [s.start, s.end] as [number, number])
  }

  /** 文本缩短时裁剪越界 override，对应 editor `_on_text_changed`。 */
  static trimToText(model: DocumentModel): void {
    const n = model.text.length
    model.overrides = model.overrides.filter((o) => o.start < n && o.end <= n)
    for (const o of model.overrides) {
      o.start = Math.max(0, o.start)
      o.end = Math.min(o.end, n)
    }
  }
}

function paramsEqual(a: OverrideParams, b: OverrideParams): boolean {
  const ak = Object.keys(a)
  const bk = Object.keys(b)
  if (ak.length !== bk.length) return false
  for (const k of ak) {
    const av = a[k as keyof OverrideParams]
    const bv = b[k as keyof OverrideParams]
    if (Array.isArray(av) && Array.isArray(bv)) {
      if (av.length !== bv.length || av.some((v, i) => v !== (bv as unknown[])[i])) return false
    } else if (av !== bv) {
      return false
    }
  }
  return true
}

export { DEFAULT_FILL, DEFAULT_BACKGROUND }
