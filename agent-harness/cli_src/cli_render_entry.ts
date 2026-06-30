/**
 * Headless render backend entry — the bridge the Python CLI invokes via
 * `node render_backend.mjs`. It uses the REAL render pipeline
 * (layout → perturb → fontCache → renderer) and the REAL persistence layer
 * (smol-toml + documentFromDict/documentToDict). It does NOT touch Electron:
 * `renderPages` is called with `save=false` so `saveOutputs` (the only Electron
 * touch, via lazy `require('../paths')`) never runs.
 *
 * Subcommands (selected by first argv):
 *   render <model.json> <outdir> [seed]        -> JSON {ok,seed,pages:[{width,height,path,bytes}]}
 *   serialize-toml <model.json> <out.toml>      -> JSON {ok,path}
 *   load-toml <in.toml> <out.json>              -> JSON {ok,model}
 *   list-fonts <out.json> [ttf_dir]             -> JSON {ok,fonts:[{name,path}]}
 *   probe                                       -> JSON {ok,node,hasCanvas,ttfLibrary,fonts}
 *
 * The Python side always passes JSON via stdout. Errors -> JSON {ok:false,error}.
 */
import * as fs from 'node:fs'
import * as path from 'node:path'
import { createCanvas, type SKRSContext2D } from '@napi-rs/canvas'
import { documentFromDict, documentToDict, type DocumentModel } from '../../src/shared/settings'
import { renderPages, RenderError } from '../../src/main/render/renderer'
import { saveModel, loadModel } from '../../src/main/persistence'

function emit(obj: unknown): void {
  process.stdout.write(JSON.stringify(obj))
}

/** Walk up from `from` (default cwd) to find a directory containing `ttf_library/`. */
function findProjectRoot(from: string = process.cwd()): string {
  let dir = path.resolve(from)
  for (let i = 0; i < 12; i++) {
    if (fs.existsSync(path.join(dir, 'ttf_library'))) return dir
    if (fs.existsSync(path.join(dir, 'package.json')) && fs.existsSync(path.join(dir, 'src'))) return dir
    const parent = path.dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

function listFontsIn(dir: string): Array<{ name: string; path: string }> {
  const result: Array<{ name: string; path: string }> = []
  if (!fs.existsSync(dir)) return result
  for (const name of fs.readdirSync(dir).sort()) {
    if (name.toLowerCase().endsWith('.ttf')) {
      const full = path.join(dir, name)
      const stem = name.replace(/\.[^.]+$/, '')
      result.push({ name: stem, path: full })
    }
  }
  return result
}

/** Encode an in-memory RGBA page to a PNG file with the real @napi-rs/canvas. */
function writePagePng(page: { width: number; height: number; data: Uint8ClampedArray }, outPath: string): void {
  const canvas = createCanvas(page.width, page.height)
  const ctx = canvas.getContext('2d') as SKRSContext2D
  const imageData = ctx.createImageData(page.width, page.height)
  imageData.data.set(page.data)
  ctx.putImageData(imageData, 0, 0)
  fs.writeFileSync(outPath, canvas.toBuffer('image/png'))
}

function cmdRender(modelPath: string, outdir: string, seedArg?: string): void {
  const raw = fs.readFileSync(modelPath, 'utf-8')
  const model = documentFromDict(JSON.parse(raw) as Record<string, unknown>) as DocumentModel
  const gp = model.global_params
  if (!gp.font_path || !fs.existsSync(gp.font_path)) {
    // Auto-resolve font from ttf_library if the model's font_path is missing.
    const root = findProjectRoot()
    const fonts = listFontsIn(path.join(root, 'ttf_library'))
    if (fonts.length === 0) {
      emit({ ok: false, error: `No .ttf font found in ${path.join(root, 'ttf_library')}` })
      return
    }
    gp.font_path = fonts[0].path
  }
  const seed = seedArg === undefined || seedArg === '' ? null : Number(seedArg)
  fs.mkdirSync(outdir, { recursive: true })
  // Clear stale PNGs in outdir (mirrors saveOutputs behavior, but to a chosen dir).
  for (const f of fs.readdirSync(outdir)) {
    if (f.endsWith('.png')) {
      try { fs.unlinkSync(path.join(outdir, f)) } catch { /* ignore */ }
    }
  }
  let result
  try {
    result = renderPages(model, seed, false)
  } catch (e) {
    const msg = e instanceof RenderError || e instanceof Error ? e.message : String(e)
    emit({ ok: false, error: msg })
    return
  }
  const pages = result.pages.map((p, i) => {
    const pPath = path.join(outdir, `${i}.png`)
    writePagePng(p, pPath)
    const stat = fs.statSync(pPath)
    return { width: p.width, height: p.height, path: pPath, bytes: stat.size, index: i }
  })
  emit({ ok: true, seed: seed ?? -1, pages, page_count: pages.length, model: documentToDict(model) })
}

function cmdSerializeToml(modelPath: string, outToml: string): void {
  const raw = fs.readFileSync(modelPath, 'utf-8')
  const model = documentFromDict(JSON.parse(raw) as Record<string, unknown>) as DocumentModel
  fs.mkdirSync(path.dirname(path.resolve(outToml)) || '.', { recursive: true })
  saveModel(model, outToml)
  emit({ ok: true, path: path.resolve(outToml) })
}

function cmdLoadToml(inToml: string, outJson: string): void {
  const model = loadModel(inToml)
  const dict = documentToDict(model)
  if (outJson && outJson !== '-') {
    fs.mkdirSync(path.dirname(path.resolve(outJson)) || '.', { recursive: true })
    fs.writeFileSync(outJson, JSON.stringify(dict), 'utf-8')
  }
  emit({ ok: true, model: dict })
}

function cmdListFonts(outJson: string, ttfDir?: string): void {
  const root = findProjectRoot()
  const dir = ttfDir || path.join(root, 'ttf_library')
  const fonts = listFontsIn(dir)
  if (outJson && outJson !== '-') {
    fs.writeFileSync(outJson, JSON.stringify({ ok: true, fonts }), 'utf-8')
  }
  emit({ ok: true, fonts, dir })
}

function cmdProbe(): void {
  const root = findProjectRoot()
  const dir = path.join(root, 'ttf_library')
  emit({
    ok: true,
    node: process.version,
    hasCanvas: true,
    project_root: root,
    ttf_library: dir,
    fonts: listFontsIn(dir)
  })
}

function main(): void {
  const [, , sub, ...rest] = process.argv
  try {
    switch (sub) {
      case 'render':
        if (rest.length < 2) { emit({ ok: false, error: 'usage: render <model.json> <outdir> [seed]' }); return }
        cmdRender(rest[0], rest[1], rest[2]); return
      case 'serialize-toml':
        if (rest.length < 2) { emit({ ok: false, error: 'usage: serialize-toml <model.json> <out.toml>' }); return }
        cmdSerializeToml(rest[0], rest[1]); return
      case 'load-toml':
        if (rest.length < 1) { emit({ ok: false, error: 'usage: load-toml <in.toml> [out.json]' }); return }
        cmdLoadToml(rest[0], rest[1]); return
      case 'list-fonts':
        cmdListFonts(rest[0] ?? '-', rest[1]); return
      case 'probe':
        cmdProbe(); return
      default:
        emit({ ok: false, error: `unknown subcommand: ${sub ?? '(none)'}` })
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    emit({ ok: false, error: msg })
  }
}

main()
