import { describe, it, expect } from 'vitest'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { createDocumentModel, DocumentModelOps, type DocumentModel, type GlobalParams } from '../src/shared/settings'
import { layoutDocument } from '../src/main/render/layout'
import { Rng } from '../src/main/render/rand'

/** 在 ttf_library/ 下找任意 .ttf；无则跳过整组布局测试（与 Python 版同样依赖字体）。 */
function findFont(): string | null {
  const dir = path.join(process.cwd(), 'ttf_library')
  if (!fs.existsSync(dir)) return null
  const files = fs.readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.ttf'))
  if (files.length === 0) return null
  return path.join(dir, files[0])
}

const FONT = findFont()
const describeOrSkip = FONT ? describe : describe.skip

function makeModel(text: string, kw: Partial<GlobalParams> = {}): DocumentModel {
  const m = createDocumentModel(FONT ?? 'x.ttf')
  const gp: Partial<GlobalParams> = {
    rate: 1,
    line_spacing: 70,
    font_size: 30,
    margin_top: 10,
    margin_bottom: 10,
    margin_left: 10,
    margin_right: 10,
    line_spacing_sigma: 0,
    font_size_sigma: 0,
    word_spacing_sigma: 0,
    ...kw
  }
  Object.assign(m.global_params, gp)
  m.text = text
  return m
}

function countJobs(pages: ReturnType<typeof layoutDocument>['pages']): number {
  return pages.reduce((s, p) => s + p.length, 0)
}

describeOrSkip('layout', () => {
  it('single line one page', () => {
    const m = makeModel('abc')
    const { pages, pageSize } = layoutDocument(m, new Rng(0))
    expect(pages.length).toBe(1)
    expect(countJobs(pages)).toBe(3)
    expect(pages.every((p) => p.every((j) => j.page === 0))).toBe(true)
    expect(pageSize).toEqual([m.global_params.paper_w, m.global_params.paper_h])
  })

  it('newline advances line', () => {
    const m = makeModel('ab\ncd')
    const { pages } = layoutDocument(m, new Rng(0))
    expect(pages.length).toBe(1)
    const jobs = pages[0]
    const yAb = jobs.slice(0, 2).map((j) => j.y)
    const yCd = jobs.slice(2).map((j) => j.y)
    expect(Math.max(...yAb)).toBeLessThan(Math.min(...yCd))
  })

  it('long text multi page', () => {
    const text = '字'.repeat(500)
    const m = makeModel(text)
    const { pages } = layoutDocument(m, new Rng(0))
    expect(pages.length).toBeGreaterThanOrEqual(2)
    expect(countJobs(pages)).toBe(500)
  })

  it('center alignment applies offset', () => {
    const m = makeModel('ab', { alignment: 'center' })
    const { pages } = layoutDocument(m, new Rng(0))
    const jobs = pages[0]
    const gp = m.global_params
    expect(jobs[0].x).toBeGreaterThan(gp.margin_left)
  })

  it('left alignment no offset', () => {
    const m = makeModel('ab', { alignment: 'left' })
    const { pages } = layoutDocument(m, new Rng(0))
    expect(Math.abs(pages[0][0].x - m.global_params.margin_left)).toBeLessThan(1)
  })

  it('override changes font size', () => {
    const m = makeModel('abc')
    DocumentModelOps.setRange(m, 0, 1, { font_size: 50 })
    const { pages } = layoutDocument(m, new Rng(0))
    const jobs = pages[0]
    expect(jobs[0].font_size).toBe(50)
    expect(jobs[1].font_size).toBe(30)
  })

  it('override underline carried', () => {
    const m = makeModel('abc')
    DocumentModelOps.setRange(m, 1, 2, { underline: true })
    const { pages } = layoutDocument(m, new Rng(0))
    const jobs = pages[0]
    expect(jobs[0].underline).toBe(false)
    expect(jobs[1].underline).toBe(true)
  })

  it('empty text one blank page', () => {
    const m = makeModel('')
    const { pages } = layoutDocument(m, new Rng(0))
    expect(pages).toEqual([[]])
  })
})
