<template>
  <div class="preview">
    <div
      ref="stage"
      class="stage"
      @wheel.prevent="onWheel"
      @mousedown="onDown"
      @mousemove="onMove"
      @mouseup="onUp"
      @mouseleave="onUp"
    >
      <img
        v-if="currentUrl"
        :src="currentUrl"
        class="page"
        :style="{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }"
        draggable="false"
      />
      <div v-else class="empty">无预览页</div>
    </div>

    <div class="controls">
      <button @click="prev" :disabled="pageIndex <= 0">◀ 上一页</button>
      <input
        type="number"
        v-model.number="pageIndex"
        :min="0"
        :max="Math.max(0, paths.length - 1)"
        style="width: 64px"
      />
      <span>共 {{ paths.length }} 页</span>
      <button @click="next" :disabled="pageIndex >= paths.length - 1">下一页 ▶</button>
      <span class="sep"></span>
      <button @click="zoomIn">放大</button>
      <button @click="zoomOut">缩小</button>
      <button @click="resetZoom">还原 100%</button>
      <span class="sep"></span>
      <button @click="openFolder">打开输出文件夹</button>
      <button @click="close">关闭</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

const paths = ref<string[]>([])
const pageIndex = ref(0)
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const urlCache = ref<Record<number, string>>({})
const stage = ref<HTMLDivElement | null>(null)

const currentUrl = computed(() => urlCache.value[pageIndex.value] ?? null)

async function loadPage(idx: number): Promise<void> {
  if (idx < 0 || idx >= paths.value.length) return
  if (urlCache.value[idx]) return
  const url = await window.handwrite.readImageAsDataUrl(paths.value[idx])
  urlCache.value = { ...urlCache.value, [idx]: url }
}

watch(pageIndex, (idx) => {
  void loadPage(idx)
})

function prev(): void {
  if (pageIndex.value > 0) pageIndex.value--
}
function next(): void {
  if (pageIndex.value < paths.value.length - 1) pageIndex.value++
}

function clampZoom(z: number): number {
  return Math.min(20, Math.max(0.05, z))
}
function zoomAt(factor: number): void {
  zoom.value = clampZoom(zoom.value * factor)
}
function onWheel(e: WheelEvent): void {
  const factor = e.deltaY > 0 ? 1 / 1.25 : 1.25
  zoomAt(factor)
}
function zoomIn(): void {
  zoomAt(1.25)
}
function zoomOut(): void {
  zoomAt(1 / 1.25)
}
function resetZoom(): void {
  zoom.value = 1
  pan.value = { x: 0, y: 0 }
}

// 拖动平移
let dragging = false
let lastX = 0
let lastY = 0
function onDown(e: MouseEvent): void {
  dragging = true
  lastX = e.clientX
  lastY = e.clientY
}
function onMove(e: MouseEvent): void {
  if (!dragging) return
  pan.value = {
    x: pan.value.x + (e.clientX - lastX),
    y: pan.value.y + (e.clientY - lastY)
  }
  lastX = e.clientX
  lastY = e.clientY
}
function onUp(): void {
  dragging = false
}

async function openFolder(): Promise<void> {
  await window.handwrite.openOutputsFolder()
}
function close(): void {
  window.close()
}

onMounted(async () => {
  paths.value = await window.handwrite.getPreviewPaths()
  pageIndex.value = 0
  await loadPage(0)
})
</script>

<style scoped>
.preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #2a2a2a;
}
.stage {
  flex: 1;
  overflow: hidden;
  position: relative;
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stage:active {
  cursor: grabbing;
}
.page {
  max-width: none;
  max-height: none;
  transform-origin: center center;
  user-select: none;
  pointer-events: none;
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.5);
}
.empty {
  color: #aaa;
}
.controls {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: #1e1e1e;
  border-top: 1px solid #444;
}
.controls button {
  background: #333;
  color: #eee;
  border-color: #555;
}
.controls button:hover {
  background: #3a3a3a;
}
.controls .sep {
  width: 1px;
  height: 22px;
  background: #555;
  margin: 0 4px;
}
.controls span {
  color: #ddd;
}
</style>
