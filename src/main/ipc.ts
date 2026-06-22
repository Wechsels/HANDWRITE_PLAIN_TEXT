/**
 * IPC 处理器（移植自 src/app/state.py Controller + editor_window 中的文件/预览动作）。
 */
import { app, ipcMain, dialog, shell, BrowserWindow } from 'electron'
import * as fs from 'node:fs'
import * as path from 'node:path'
import type { DocumentModel } from '@shared/settings'
import { listFonts } from './fonts'
import { saveModel, loadModel } from './persistence'
import { renderPages, RenderError } from './render/renderer'
import { OUTPUTS_DIR, TTF_LIBRARY_DIR } from './paths'
import { getLogger } from './logger'

const log = getLogger('ipc')

let previewWindow: BrowserWindow | null = null
let previewPaths: string[] = []

/** 主进程是否处于预览窗口上下文（预览窗口自己调用 isPreview 同步判定）。 */
ipcMain.on('handwrite:isPreview', (event) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  event.returnValue = win ? win.getTitle().startsWith('HandWrite Preview') : false
})

export function registerIpc(getEditorWindow: () => BrowserWindow | null): void {
  ipcMain.handle('handwrite:listFonts', async () => listFonts())

  ipcMain.handle('handwrite:render', async (_e, model: DocumentModel) => {
    if (listFonts().length === 0) {
      throw new Error(`请在 ${TTF_LIBRARY_DIR} 目录放置 .ttf 字体。`)
    }
    try {
      const { paths } = renderPages(model, null, true)
      previewPaths = paths
      openPreview(getEditorWindow())
      return { pages: paths }
    } catch (err) {
      if (err instanceof RenderError) throw new Error(err.message)
      throw err
    }
  })

  ipcMain.handle('handwrite:saveConfig', async (_e, model: DocumentModel) => {
    const win = getEditorWindow()
    const res = await dialog.showSaveDialog(win ?? new BrowserWindow(), {
      title: '保存配置',
      defaultPath: 'config.toml',
      filters: [{ name: 'TOML Files', extensions: ['toml'] }]
    })
    if (res.canceled || !res.filePath) return null
    saveModel(model, res.filePath)
    log.info('config saved: %s', res.filePath)
    return res.filePath
  })

  ipcMain.handle('handwrite:loadConfig', async () => {
    const win = getEditorWindow()
    const res = await dialog.showOpenDialog(win ?? new BrowserWindow(), {
      title: '加载配置',
      filters: [{ name: 'TOML Files', extensions: ['toml'] }],
      properties: ['openFile']
    })
    if (res.canceled || res.filePaths.length === 0) return null
    const p = res.filePaths[0]
    const model = loadModel(p)
    log.info('config loaded: %s', p)
    return model
  })

  ipcMain.handle('handwrite:openOutputs', async () => {
    fs.mkdirSync(OUTPUTS_DIR, { recursive: true })
    await shell.openPath(OUTPUTS_DIR)
  })

  ipcMain.handle('handwrite:readImage', async (_e, filePath: string) => {
    const buf = fs.readFileSync(filePath)
    const ext = path.extname(filePath).slice(1) || 'png'
    return `data:image/${ext};base64,${buf.toString('base64')}`
  })

  ipcMain.handle('handwrite:getPreviewPaths', async () => previewPaths)
}

/** 打开（或刷新）预览窗口。对应 Python `PreviewWindow` 模态对话框。 */
export function openPreview(parent: BrowserWindow | null): void {
  if (previewWindow && !previewWindow.isDestroyed()) {
    previewWindow.close()
  }
  previewWindow = new BrowserWindow({
    title: 'HandWrite Preview',
    width: 900,
    height: 1100,
    parent: parent ?? undefined,
    modal: !!parent,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })
  previewWindow.on('closed', () => {
    previewWindow = null
  })

  if (process.env['ELECTRON_RENDERER_URL']) {
    void previewWindow.loadURL(`${process.env['ELECTRON_RENDERER_URL']}#/preview`)
  } else {
    void previewWindow.loadFile(path.join(__dirname, '../renderer/index.html'), {
      hash: 'preview'
    })
  }
}

// 抑制未使用 import 警告
void app
