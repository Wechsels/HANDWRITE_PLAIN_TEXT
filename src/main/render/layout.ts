/**
 * 布局引擎（移植自 src/render/layout.py）。
 *
 * 把文本按全局参数 + 选区覆盖排版为分页的 GlyphJob 列表。
 * 换行规则、对齐、gauss 抖动、分页逻辑与 Python 版逐行对齐。
 */
import type { DocumentModel } from '@shared/settings'
import { DocumentModelOps } from '@shared/settings'
import type { GlyphJob } from '@shared/types'
import type { RGBA } from '@shared/palette'
import { getInkWidth } from './fontCache'
import type { Rng } from './rand'

// 提前换行：这些字符不宜出现在行尾
const START_CHARS = '"（[<'
// 禁止行首：这些字符不宜出现在行首
const END_CHARS = '，。》？；：' + '"' + '】｝、！％）,.>?;:]}!%)′″℃℉'

interface LineItem {
  i: number
  ch: string
  fs: number
  x: number
  y: number
  advance: number
  fill: RGBA
  ul: boolean
  sigmas: [number, number, number]
}

function lineAlignment(model: DocumentModel, lineBuffer: LineItem[]): string {
  if (lineBuffer.length) {
    return DocumentModelOps.effectiveParams(model, lineBuffer[0].i)['alignment'] as string
  }
  return model.global_params.alignment
}

export interface LayoutResult {
  pages: GlyphJob[][]
  pageSize: [number, number]
}

export function layoutDocument(model: DocumentModel, rand: Rng): LayoutResult {
  const gp = model.global_params
  const rate = gp.rate
  const pw = gp.paper_w * rate
  const ph = gp.paper_h * rate
  const lm = gp.margin_left * rate
  const rm = gp.margin_right * rate
  const tm = gp.margin_top * rate
  const bm = gp.margin_bottom * rate
  const lineSpacing = gp.line_spacing * rate
  const lss = gp.line_spacing_sigma * rate
  const fss = gp.font_size_sigma * rate
  const wss = gp.word_spacing_sigma * rate
  const baseFontSizePx = gp.font_size * rate

  const text = model.text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const n = text.length

  const pages: GlyphJob[][] = []
  let currentJobs: GlyphJob[] = []
  let lineBuffer: LineItem[] = []
  let pageIndex = 0
  let x = lm
  let y = tm + lineSpacing - baseFontSizePx

  function flushLine(alignment: string): void {
    if (lineBuffer.length === 0) return
    const firstX = lineBuffer[0].x
    const last = lineBuffer[lineBuffer.length - 1]
    const lineWidth = last.x + last.advance - firstX
    const avail = pw - lm - rm
    const offsetX = alignment === 'center' ? Math.max(0.0, (avail - lineWidth) / 2) : 0.0
    for (const it of lineBuffer) {
      currentJobs.push({
        char: it.ch,
        page: pageIndex,
        x: it.x + offsetX,
        y: it.y,
        font_size: it.fs,
        perturb_x_sigma: it.sigmas[0],
        perturb_y_sigma: it.sigmas[1],
        perturb_theta_sigma: it.sigmas[2],
        fill: it.fill,
        underline: it.ul
      })
    }
    lineBuffer = []
  }

  function nextLine(): void {
    flushLine(lineAlignment(model, lineBuffer))
    y += lineSpacing
    x = lm
  }

  function newPage(): void {
    flushLine(lineAlignment(model, lineBuffer))
    if (currentJobs.length) pages.push(currentJobs)
    currentJobs = []
    pageIndex = pages.length
    y = tm + lineSpacing - baseFontSizePx
  }

  let i = 0
  while (i < n) {
    const ch = text[i]
    if (ch === '\n') {
      nextLine()
      if (y > ph - bm - baseFontSizePx) newPage()
      i += 1
      continue
    }

    const eff = DocumentModelOps.effectiveParams(model, i)
    const fsNominal = (eff.font_size as number) * rate
    const fsActual = Math.max(Math.round(rand.gauss(fsNominal, fss)), 1)
    const advance = getInkWidth(gp.font_path, fsActual, ch)

    const needWrap =
      (x > pw - rm - 2 * fsActual && START_CHARS.includes(ch)) ||
      (x > pw - rm - fsActual && !END_CHARS.includes(ch))
    if (needWrap) {
      nextLine()
      if (y > ph - bm - baseFontSizePx) newPage()
      continue // reprocess ch on the new line
    }

    const yJit = rand.gauss(y, lss)
    const sigmas: [number, number, number] = [
      eff.perturb_x_sigma as number,
      eff.perturb_y_sigma as number,
      eff.perturb_theta_sigma as number
    ]
    lineBuffer.push({
      i,
      ch,
      fs: fsActual,
      x,
      y: yJit,
      advance,
      fill: eff.fill as RGBA,
      ul: eff.underline as boolean,
      sigmas
    })
    x += rand.gauss((eff.word_spacing as number) * rate + advance, wss)
    i += 1
  }

  flushLine(lineAlignment(model, lineBuffer))
  if (currentJobs.length) pages.push(currentJobs)
  if (pages.length === 0) pages.push([])
  return { pages, pageSize: [pw, ph] }
}
