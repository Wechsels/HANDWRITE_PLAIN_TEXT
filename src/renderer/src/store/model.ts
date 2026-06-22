/**
 * 响应式文档模型 store（单一数据源）。
 * 对应 Python 中 Controller.model + editor 的 gather/populate。
 */
import { reactive, ref } from 'vue'
import {
  createDocumentModel,
  DocumentModelOps,
  documentToDict,
  documentFromDict,
  type DocumentModel
} from '@shared/settings'
import type { FontEntry } from '@shared/types'

const model = reactive<DocumentModel>(createDocumentModel()) as DocumentModel
const fonts = ref<FontEntry[]>([])
const status = ref('就绪')

async function initFonts(): Promise<void> {
  fonts.value = await window.handwrite.listFonts()
  if (fonts.value.length > 0 && !model.global_params.font_path) {
    model.global_params.font_path = fonts.value[0].path
  }
}

function setRange(start: number, end: number, params: Record<string, unknown>): void {
  DocumentModelOps.setRange(model, start, end, params)
}

function clearRange(start: number, end: number): void {
  DocumentModelOps.clearRange(model, start, end)
}

function effectiveParams(index: number): Record<string, unknown> {
  return DocumentModelOps.effectiveParams(model, index)
}

function rangesForMarking(): Array<[number, number]> {
  return DocumentModelOps.rangesForMarking(model)
}

function onTextChanged(text: string): void {
  model.text = text
  DocumentModelOps.trimToText(model)
}

function toPlain(): DocumentModel {
  // 返回一份非响应式快照，供 IPC 传输。
  // JSON 深拷贝剥离 Vue reactive proxy，否则 IPC 结构化克隆会抛
  // "An object could not be cloned"。
  const dict = documentToDict(model)
  return documentFromDict(JSON.parse(JSON.stringify(dict)) as Record<string, unknown>)
}

function loadFrom(m: DocumentModel): void {
  const snap = documentFromDict(documentToDict(m))
  model.text = snap.text
  Object.assign(model.global_params, snap.global_params)
  model.overrides.splice(0, model.overrides.length, ...snap.overrides)
}

export function useModel() {
  return {
    model,
    fonts,
    status,
    initFonts,
    setRange,
    clearRange,
    effectiveParams,
    rangesForMarking,
    onTextChanged,
    toPlain,
    loadFrom
  }
}
