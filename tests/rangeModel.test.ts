import { describe, it, expect } from 'vitest'
import { stringify, parse } from 'smol-toml'
import {
  createDocumentModel,
  DocumentModelOps,
  documentToDict,
  documentFromDict,
  type DocumentModel,
  type RangeOverride
} from '../src/shared/settings'

function makeModel(text = 'abcdefghij'): DocumentModel {
  const m = createDocumentModel('x.ttf') // x.ttf：占位路径，range 逻辑不依赖真实字体
  m.text = text
  return m
}

describe('range model', () => {
  it('set_range creates override', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, 2, 5, { perturb_x_sigma: 3.0 })
    expect(DocumentModelOps.rangesForMarking(m)).toEqual([[2, 5]])
    expect(DocumentModelOps.effectiveParams(m, 0)['perturb_x_sigma']).toBe(1.0)
    expect(DocumentModelOps.effectiveParams(m, 3)['perturb_x_sigma']).toBe(3.0)
    expect(DocumentModelOps.effectiveParams(m, 5)['perturb_x_sigma']).toBe(1.0)
  })

  it('set_range partial overlap splits', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, 2, 6, { font_size: 40 })
    DocumentModelOps.setRange(m, 4, 8, { perturb_y_sigma: 5.0 })
    expect(DocumentModelOps.effectiveParams(m, 3)['font_size']).toBe(40)
    expect(DocumentModelOps.effectiveParams(m, 3)['perturb_y_sigma']).toBe(1.0)
    expect(DocumentModelOps.effectiveParams(m, 5)['font_size']).toBe(40)
    expect(DocumentModelOps.effectiveParams(m, 5)['perturb_y_sigma']).toBe(5.0)
    expect(DocumentModelOps.effectiveParams(m, 7)['font_size']).toBe(30)
    expect(DocumentModelOps.effectiveParams(m, 7)['perturb_y_sigma']).toBe(5.0)
    expect(DocumentModelOps.effectiveParams(m, 8)['perturb_y_sigma']).toBe(1.0)
  })

  it('merge semantics preserves prior keys', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, 0, 4, { font_size: 50 })
    DocumentModelOps.setRange(m, 1, 3, { perturb_x_sigma: 2.0 })
    expect(DocumentModelOps.effectiveParams(m, 2)['font_size']).toBe(50)
    expect(DocumentModelOps.effectiveParams(m, 2)['perturb_x_sigma']).toBe(2.0)
  })

  it('clear_range keeps outside', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, 2, 8, { font_size: 40 })
    DocumentModelOps.clearRange(m, 4, 6)
    expect(DocumentModelOps.effectiveParams(m, 3)['font_size']).toBe(40)
    expect(DocumentModelOps.effectiveParams(m, 5)['font_size']).toBe(30)
    expect(DocumentModelOps.effectiveParams(m, 7)['font_size']).toBe(40)
    expect(DocumentModelOps.rangesForMarking(m)).toEqual([
      [2, 4],
      [6, 8]
    ])
  })

  it('override_at and reselect shows adjusted', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, 3, 6, { perturb_theta_sigma: 0.2, font_size: 35 })
    const seg = DocumentModelOps.overrideAt(m, 4)
    expect(seg).not.toBeNull()
    expect(seg!.params['perturb_theta_sigma']).toBe(0.2)
    expect(DocumentModelOps.effectiveParams(m, 4)['font_size']).toBe(35)
  })

  it('adjacent same params merge', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, 0, 3, { font_size: 40 })
    DocumentModelOps.setRange(m, 3, 6, { font_size: 40 })
    expect(DocumentModelOps.rangesForMarking(m)).toEqual([[0, 6]])
  })

  it('clamp and empty noop', () => {
    const m = makeModel()
    DocumentModelOps.setRange(m, -5, 100, { font_size: 40 })
    expect(DocumentModelOps.rangesForMarking(m)).toEqual([[0, 10]])
    DocumentModelOps.setRange(m, 2, 2, { font_size: 99 })
    expect(m.overrides.length).toBe(1)
    DocumentModelOps.setRange(m, 1, 3, {})
    expect(m.overrides.length).toBe(1)
  })

  it('persistence roundtrip (smol-toml)', () => {
    const m = makeModel('hello world')
    DocumentModelOps.setRange(m, 0, 5, { font_size: 44, underline: true })
    const dict = documentToDict(m)
    const loaded = documentFromDict(parse(stringify(dict)) as Record<string, unknown>)
    expect(loaded.text).toBe('hello world')
    expect(loaded.global_params.font_path).toBe('x.ttf')
    expect(DocumentModelOps.rangesForMarking(loaded)).toEqual([[0, 5]])
    expect(DocumentModelOps.effectiveParams(loaded, 2)['font_size']).toBe(44)
    expect(DocumentModelOps.effectiveParams(loaded, 2)['underline']).toBe(true)
  })

  it('range override to/from dict', () => {
    const o: RangeOverride = { start: 1, end: 3, params: { font_size: 40 } }
    const dict = { start: o.start, end: o.end, params: { ...o.params } }
    expect(dict.start).toBe(1)
    expect(dict.end).toBe(3)
    expect(dict.params).toEqual({ font_size: 40 })
  })
})
