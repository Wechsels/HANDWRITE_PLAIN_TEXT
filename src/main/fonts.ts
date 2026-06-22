import * as fs from 'node:fs'
import * as path from 'node:path'
import { TTF_LIBRARY_DIR } from './paths'
import type { FontEntry } from '@shared/types'

export function listFonts(): FontEntry[] {
  const dir = TTF_LIBRARY_DIR
  const result: FontEntry[] = []
  if (!fs.existsSync(dir)) return result
  const files = fs.readdirSync(dir).sort()
  for (const name of files) {
    if (name.toLowerCase().endsWith('.ttf')) {
      const full = path.join(dir, name)
      const stem = name.replace(/\.[^.]+$/, '')
      result.push({ name: stem, path: full })
    }
  }
  return result
}

export function defaultFontPath(): string {
  const fonts = listFonts()
  if (fonts.length === 0) {
    throw new Error(`No .ttf font found in ${TTF_LIBRARY_DIR}`)
  }
  return fonts[0].path
}
