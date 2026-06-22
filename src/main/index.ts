/**
 * Electron 主进程入口。
 * 创建编辑器窗口并注册 IPC。
 */
import { app, BrowserWindow, shell } from 'electron'
import * as path from 'node:path'
import { ensureDirs } from './paths'
import { registerIpc } from './ipc'
import { getLogger } from './logger'

const log = getLogger('main')

let editorWindow: BrowserWindow | null = null

function createEditorWindow(): void {
  editorWindow = new BrowserWindow({
    title: 'HandWrite Plain Text - Editor',
    width: 1280,
    height: 820,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  editorWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env['ELECTRON_RENDERER_URL']) {
    void editorWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void editorWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  ensureDirs()
  registerIpc(() => editorWindow)
  createEditorWindow()
  log.info('editor window shown')

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createEditorWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
