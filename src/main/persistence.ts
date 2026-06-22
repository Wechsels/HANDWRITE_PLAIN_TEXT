/**
 * TOML 配置持久化（移植自 src/config/persistence.py）。
 * 用 smol-toml 替代 Python `toml`/`tomllib`。
 */
import * as fs from 'node:fs'
import { stringify, parse } from 'smol-toml'
import {
  documentToDict,
  documentFromDict,
  type DocumentModel
} from '@shared/settings'

export function saveModel(model: DocumentModel, filePath: string): void {
  const data = documentToDict(model)
  const toml = stringify(data as Record<string, unknown>)
  fs.writeFileSync(filePath, toml, 'utf-8')
}

export function loadModel(filePath: string): DocumentModel {
  const raw = fs.readFileSync(filePath, 'utf-8')
  const data = parse(raw) as Record<string, unknown>
  return documentFromDict(data)
}
