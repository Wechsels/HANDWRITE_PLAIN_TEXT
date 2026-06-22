/**
 * preload：通过 contextBridge 暴露受控的 IPC API 给渲染进程。
 */
import { contextBridge, ipcRenderer } from 'electron'

const api = {
  listFonts: (): Promise<FontEntry[]> => ipcRenderer.invoke('handwrite:listFonts'),
  render: (model: DocumentModel): Promise<{ pages: string[] }> =>
    ipcRenderer.invoke('handwrite:render', model),
  saveConfig: (model: DocumentModel): Promise<string | null> =>
    ipcRenderer.invoke('handwrite:saveConfig', model),
  loadConfig: (): Promise<DocumentModel | null> =>
    ipcRenderer.invoke('handwrite:loadConfig'),
  openOutputsFolder: (): Promise<void> => ipcRenderer.invoke('handwrite:openOutputs'),
  readImageAsDataUrl: (filePath: string): Promise<string> =>
    ipcRenderer.invoke('handwrite:readImage', filePath),
  getPreviewPaths: (): Promise<string[]> =>
    ipcRenderer.invoke('handwrite:getPreviewPaths'),
  isPreview: (): boolean => ipcRenderer.sendSync('handwrite:isPreview')
}

contextBridge.exposeInMainWorld('handwrite', api)