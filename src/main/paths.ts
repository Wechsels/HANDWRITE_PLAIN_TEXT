/**
 * 路径定义（移植自 src/config/paths.py）。
 *
 * dev：项目根（与 Python 版一致）。
 * packaged：ttf_library 打进 resources；outputs/logs 落到 userData。
 */
import { app } from 'electron'
import * as fs from 'node:fs'
import * as path from 'node:path'

function projectRoot(): string {
  if (app.isPackaged) return process.resourcesPath
  // dev：electron-vite 启动时 app.getAppPath() 就是项目根
  return app.getAppPath()
}

function userRoot(): string {
  if (app.isPackaged) {
    return app.getPath('userData')
  }
  return projectRoot()
}

export const PROJECT_ROOT = projectRoot()
export const TTF_LIBRARY_DIR = path.join(PROJECT_ROOT, 'ttf_library')
export const OUTPUTS_DIR = path.join(userRoot(), 'outputs')
export const LOGS_DIR = path.join(userRoot(), 'logs')

/** 启动时确保目录存在（对应 Python paths.py 末尾的 mkdir）。 */
export function ensureDirs(): void {
  for (const d of [OUTPUTS_DIR, LOGS_DIR, TTF_LIBRARY_DIR]) {
    fs.mkdirSync(d, { recursive: true })
  }
}
