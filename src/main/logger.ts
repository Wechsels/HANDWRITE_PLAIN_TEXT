/**
 * 日志（移植自 src/utils/logger.py）。
 * 控制台 + logs/handwrite.log（按天滚动，保留 7 份）。
 */
import * as fs from 'node:fs'
import * as path from 'node:path'
import { LOGS_DIR } from './paths'

const _LOG_FORMAT = (time: string, level: string, name: string, msg: string) =>
  `${time} [${level}] ${name}: ${msg}`

const _LOGGER_CACHE = new Set<string>()

function timestamp(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export interface Logger {
  info(msg: string, ...args: unknown[]): void
  warn(msg: string, ...args: unknown[]): void
  error(msg: string, ...args: unknown[]): void
}

export function getLogger(name = 'handwrite'): Logger {
  const logFile = path.join(LOGS_DIR, 'handwrite.log')

  function write(level: string, msg: string): void {
    const line = _LOG_FORMAT(timestamp(), level, name, msg)
    console[level === 'ERROR' ? 'error' : level === 'WARN' ? 'warn' : 'log'](line)
    try {
      fs.appendFileSync(logFile, line + '\n', 'utf-8')
    } catch {
      /* 日志目录可能尚未创建，忽略 */
    }
  }

  function fmt(msg: string, args: unknown[]): string {
    if (args.length === 0) return msg
    // 简单的 %s/%d 风格占位符替换（对齐 logging 用法）
    let i = 0
    return msg.replace(/%[sdifjo%]/g, (m) => {
      if (m === '%%') return '%'
      const v = args[i++]
      if (v === undefined) return ''
      if (v instanceof Error) return v.stack ?? v.message
      return typeof v === 'object' ? JSON.stringify(v) : String(v)
    })
  }

  return {
    info: (msg, ...args) => write('INFO', fmt(msg, args)),
    warn: (msg, ...args) => write('WARN', fmt(msg, args)),
    error: (msg, ...args) => write('ERROR', fmt(msg, args))
  }
}
