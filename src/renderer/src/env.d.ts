/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

import type { DocumentModel } from '@shared/settings'
import type { FontEntry } from '@shared/types'

declare global {
  interface HandwriteApi {
    listFonts: () => Promise<FontEntry[]>
    render: (model: DocumentModel) => Promise<{ pages: string[] }>
    saveConfig: (model: DocumentModel) => Promise<string | null>
    loadConfig: () => Promise<DocumentModel | null>
    openOutputsFolder: () => Promise<void>
    readImageAsDataUrl: (filePath: string) => Promise<string>
    getPreviewPaths: () => Promise<string[]>
    isPreview: () => boolean
  }
  interface Window {
    handwrite: HandwriteApi
  }
}

export {}
