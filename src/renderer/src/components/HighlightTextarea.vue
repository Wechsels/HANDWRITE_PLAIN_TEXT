<template>
  <div class="hl-wrap">
    <div ref="overlay" class="hl-overlay" v-html="overlayHtml"></div>
    <textarea
      ref="ta"
      class="hl-input"
      :value="modelValue"
      :placeholder="placeholder"
      spellcheck="false"
      @input="onInput"
      @scroll="syncScroll"
      @select="emitSelection"
      @keyup="emitSelection"
      @mouseup="emitSelection"
    ></textarea>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted } from 'vue'

const props = defineProps<{
  modelValue: string
  ranges: Array<[number, number]>
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'select', start: number, end: number): void
}>()

const ta = ref<HTMLTextAreaElement | null>(null)
const overlay = ref<HTMLDivElement | null>(null)

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const overlayHtml = computed(() => {
  const text = props.modelValue
  const ranges = [...props.ranges].sort((a, b) => a[0] - b[0])
  let html = ''
  let cursor = 0
  for (const [start, end] of ranges) {
    if (start < cursor) continue
    if (end <= start) continue
    html += escapeHtml(text.slice(cursor, start))
    html += '<span class="hl-mark">' + escapeHtml(text.slice(start, end)) + '</span>'
    cursor = end
  }
  html += escapeHtml(text.slice(cursor))
  // 末尾换行占位，保证 overlay 高度与 textarea 一致
  if (text.endsWith('\n') || text.length === 0) html += '&nbsp;'
  return html
})

function onInput(e: Event): void {
  const v = (e.target as HTMLTextAreaElement).value
  emit('update:modelValue', v)
}

function syncScroll(): void {
  if (overlay.value && ta.value) {
    overlay.value.scrollTop = ta.value.scrollTop
    overlay.value.scrollLeft = ta.value.scrollLeft
  }
}

function emitSelection(): void {
  const el = ta.value
  if (!el) return
  emit('select', el.selectionStart, el.selectionEnd)
}

watch(
  () => props.modelValue,
  () => {
    nextTick(syncScroll)
  }
)

onMounted(() => {
  nextTick(syncScroll)
})

defineExpose({
  focus: () => ta.value?.focus(),
  getSelection: () => {
    const el = ta.value
    return el ? [el.selectionStart, el.selectionEnd] as [number, number] : [0, 0]
  }
})
</script>

<style scoped>
.hl-wrap {
  position: relative;
  flex: 1;
  display: flex;
  min-height: 0;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}
.hl-overlay,
.hl-input {
  position: absolute;
  inset: 0;
  margin: 0;
  padding: 8px;
  border: 0;
  font-family: 'Consolas', 'Microsoft YaHei', monospace;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow: auto;
  letter-spacing: 0;
}
.hl-overlay {
  color: transparent;
  pointer-events: none;
  z-index: 1;
  background: transparent;
}
.hl-input {
  background: transparent;
  color: #000;
  outline: none;
  resize: none;
  z-index: 2;
  caret-color: #000;
}
:deep(.hl-mark) {
  background: var(--mark);
  border-radius: 2px;
}
</style>
