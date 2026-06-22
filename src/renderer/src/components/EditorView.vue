<template>
  <div class="editor">
    <div class="toolbar">
      <button @click="onPreview" title="预览">
        <i class="fa-solid fa-eye"></i> 预览
      </button>
      <button @click="onPreview" title="导出（同预览）">
        <i class="fa-solid fa-download"></i> 导出
      </button>
      <span class="sep"></span>
      <button @click="onSaveConfig" title="保存配置">
        <i class="fa-solid fa-floppy-disk"></i> 保存配置
      </button>
      <button @click="onLoadConfig" title="加载配置">
        <i class="fa-solid fa-folder-open"></i> 加载配置
      </button>
      <span class="sep"></span>
      <span class="status">{{ status }}</span>
    </div>

    <div class="body">
      <div class="left">
        <HighlightTextarea
          ref="editor"
          v-model="model.text"
          :ranges="ranges"
          placeholder="在此输入要生成手写体的文本…"
          @update:modelValue="onTextChanged"
          @select="onSelection"
        />
      </div>

      <div class="right">
        <div class="panel global">
          <div class="panel-title">全局参数</div>
          <div class="form-row">
            <label>纸张宽 (px)</label>
            <input type="number" v-model.number="gp.paper_w" min="50" max="10000" />
          </div>
          <div class="form-row">
            <label>纸张高 (px)</label>
            <input type="number" v-model.number="gp.paper_h" min="50" max="10000" />
          </div>
          <div class="form-row">
            <label>字体</label>
            <select v-model="fontPath">
              <option v-for="f in fonts" :key="f.path" :value="f.path">{{ f.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>字体大小 (px)</label>
            <input type="number" v-model.number="gp.font_size" min="2" max="200" />
          </div>
          <div class="form-row">
            <label>行距 (px)</label>
            <input type="number" v-model.number="gp.line_spacing" min="2" max="400" />
          </div>
          <div class="form-row">
            <label>字距 (px)</label>
            <input type="number" v-model.number="gp.word_spacing" min="-100" max="200" />
          </div>
          <div class="form-row">
            <label>上边距 (px)</label>
            <input type="number" v-model.number="gp.margin_top" min="0" max="1000" />
          </div>
          <div class="form-row">
            <label>下边距 (px)</label>
            <input type="number" v-model.number="gp.margin_bottom" min="0" max="1000" />
          </div>
          <div class="form-row">
            <label>左边距 (px)</label>
            <input type="number" v-model.number="gp.margin_left" min="0" max="1000" />
          </div>
          <div class="form-row">
            <label>右边距 (px)</label>
            <input type="number" v-model.number="gp.margin_right" min="0" max="1000" />
          </div>
          <div class="form-row">
            <label>字体颜色</label>
            <select v-model="charColorKey">
              <option v-for="k in Object.keys(FONT_COLOR_DICT)" :key="k" :value="k">{{ k }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>背景颜色</label>
            <select v-model="bgColorKey">
              <option v-for="k in Object.keys(BACKGROUND_COLOR_DICT)" :key="k" :value="k">{{ k }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>渲染倍率</label>
            <select v-model="rateKey">
              <option v-for="k in Object.keys(RATE_DICT)" :key="k" :value="k">{{ k }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>行距扰动 σ</label>
            <input type="number" v-model.number="gp.line_spacing_sigma" min="0" max="50" step="0.5" />
          </div>
          <div class="form-row">
            <label>字号扰动 σ</label>
            <input type="number" v-model.number="gp.font_size_sigma" min="0" max="50" step="0.5" />
          </div>
          <div class="form-row">
            <label>字距扰动 σ</label>
            <input type="number" v-model.number="gp.word_spacing_sigma" min="0" max="50" step="0.5" />
          </div>
          <div class="form-row">
            <label>横向笔画扰动 σ</label>
            <input type="number" v-model.number="gp.perturb_x_sigma" min="0" max="50" step="0.5" />
          </div>
          <div class="form-row">
            <label>纵向笔画扰动 σ</label>
            <input type="number" v-model.number="gp.perturb_y_sigma" min="0" max="50" step="0.5" />
          </div>
          <div class="form-row">
            <label>旋转笔画扰动 σ</label>
            <input type="number" v-model.number="gp.perturb_theta_sigma" min="0" max="1" step="0.01" />
          </div>
          <div class="form-row">
            <label>对齐</label>
            <select v-model="gp.alignment">
              <option v-for="a in ALIGNMENT_OPTIONS" :key="a" :value="a">{{ a }}</option>
            </select>
          </div>
          <div class="form-row">
            <label></label>
            <label><input type="checkbox" v-model="gp.underline" /> 全局下划线</label>
          </div>
        </div>

        <div class="panel override">
          <div class="panel-title">选区参数覆盖（先在文本中选中字符，再调整并点击「应用到选区」）</div>
          <div class="ov-label">{{ overrideLabel }}</div>
          <div class="form-row">
            <label>字体大小</label>
            <input type="number" v-model.number="ov.font_size" min="2" max="200" :disabled="!hasSel" />
          </div>
          <div class="form-row">
            <label>字距</label>
            <input type="number" v-model.number="ov.word_spacing" min="-100" max="200" :disabled="!hasSel" />
          </div>
          <div class="form-row">
            <label>横向笔画扰动 σ</label>
            <input type="number" v-model.number="ov.perturb_x_sigma" min="0" max="50" step="0.5" :disabled="!hasSel" />
          </div>
          <div class="form-row">
            <label>纵向笔画扰动 σ</label>
            <input type="number" v-model.number="ov.perturb_y_sigma" min="0" max="50" step="0.5" :disabled="!hasSel" />
          </div>
          <div class="form-row">
            <label>旋转笔画扰动 σ</label>
            <input type="number" v-model.number="ov.perturb_theta_sigma" min="0" max="1" step="0.01" :disabled="!hasSel" />
          </div>
          <div class="form-row">
            <label>字体颜色</label>
            <select v-model="ovColorKey" :disabled="!hasSel">
              <option v-for="k in Object.keys(FONT_COLOR_DICT)" :key="k" :value="k">{{ k }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>对齐</label>
            <select v-model="ov.alignment" :disabled="!hasSel">
              <option v-for="a in ALIGNMENT_OPTIONS" :key="a" :value="a">{{ a }}</option>
            </select>
          </div>
          <div class="form-row">
            <label></label>
            <label><input type="checkbox" v-model="ov.underline" :disabled="!hasSel" /> 选区下划线</label>
          </div>
          <div class="btn-row">
            <button @click="onApplyOverride" :disabled="!hasSel">应用到选区</button>
            <button @click="onClearOverride" :disabled="!hasSel">清除选区覆盖</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import HighlightTextarea from './HighlightTextarea.vue'
import { useModel } from '../store/model'
import {
  FONT_COLOR_DICT,
  BACKGROUND_COLOR_DICT,
  RATE_DICT,
  ALIGNMENT_OPTIONS,
  tupleEquals,
  type RGBA
} from '@shared/palette'

const { model, fonts, status, initFonts, setRange, clearRange, effectiveParams, rangesForMarking, onTextChanged, toPlain, loadFrom } =
  useModel()

const gp = computed(() => model.global_params)
const ranges = computed(() => rangesForMarking())
const editor = ref<InstanceType<typeof HighlightTextarea> | null>(null)

const fontPath = computed<string>({
  get: () => gp.value.font_path,
  set: (v) => {
    gp.value.font_path = v
  }
})

function keyForColor(dict: Record<string, RGBA>, rgba: RGBA): string {
  for (const [k, v] of Object.entries(dict)) {
    if (tupleEquals(v, rgba)) return k
  }
  return Object.keys(dict)[0]
}

const charColorKey = computed<string>({
  get: () => keyForColor(FONT_COLOR_DICT, gp.value.fill),
  set: (k) => {
    gp.value.fill = [...FONT_COLOR_DICT[k]] as RGBA
  }
})
const bgColorKey = computed<string>({
  get: () => keyForColor(BACKGROUND_COLOR_DICT, gp.value.background),
  set: (k) => {
    gp.value.background = [...BACKGROUND_COLOR_DICT[k]] as RGBA
  }
})
const rateKey = computed<string>({
  get: () => {
    for (const [k, v] of Object.entries(RATE_DICT)) if (v === gp.value.rate) return k
    return 'x4'
  },
  set: (k) => {
    gp.value.rate = RATE_DICT[k]
  }
})

// 选区
const selStart = ref(0)
const selEnd = ref(0)
const hasSel = computed(() => selStart.value !== selEnd.value)
const overrideLabel = computed(() =>
  hasSel.value
    ? `当前选区: [${selStart.value}, ${selEnd.value})  长度 ${selEnd.value - selStart.value}`
    : '当前未选中任何字符'
)

const ov = reactive({
  font_size: 30,
  word_spacing: 1,
  perturb_x_sigma: 1.0,
  perturb_y_sigma: 1.0,
  perturb_theta_sigma: 0.05,
  alignment: 'left',
  underline: false
})
const ovFill = ref<RGBA>([...FONT_COLOR_DICT.black])
const ovColorKey = computed<string>({
  get: () => keyForColor(FONT_COLOR_DICT, ovFill.value),
  set: (k) => {
    ovFill.value = [...FONT_COLOR_DICT[k]] as RGBA
  }
})

function onSelection(start: number, end: number): void {
  selStart.value = Math.min(start, end)
  selEnd.value = Math.max(start, end)
  if (selStart.value === selEnd.value) return
  const eff = effectiveParams(selStart.value)
  ov.font_size = Number(eff.font_size)
  ov.word_spacing = Number(eff.word_spacing)
  ov.perturb_x_sigma = Number(eff.perturb_x_sigma)
  ov.perturb_y_sigma = Number(eff.perturb_y_sigma)
  ov.perturb_theta_sigma = Number(eff.perturb_theta_sigma)
  ovFill.value = [...(eff.fill as RGBA)]
  ov.alignment = String(eff.alignment)
  ov.underline = Boolean(eff.underline)
}

function onApplyOverride(): void {
  if (!hasSel.value) {
    alert('请先在文本中选中要覆盖的字符。')
    return
  }
  setRange(selStart.value, selEnd.value, {
    font_size: ov.font_size,
    word_spacing: ov.word_spacing,
    perturb_x_sigma: ov.perturb_x_sigma,
    perturb_y_sigma: ov.perturb_y_sigma,
    perturb_theta_sigma: ov.perturb_theta_sigma,
    fill: [...ovFill.value] as RGBA,
    alignment: ov.alignment,
    underline: ov.underline
  })
  status.value = `已应用选区覆盖 [${selStart.value}, ${selEnd.value})`
}

function onClearOverride(): void {
  if (!hasSel.value) return
  clearRange(selStart.value, selEnd.value)
  status.value = `已清除选区覆盖 [${selStart.value}, ${selEnd.value})`
}

function clampForSend(): void {
  // 对齐 Python gather_into_model: line_spacing = max(spin, font_size)
  if (gp.value.line_spacing < gp.value.font_size) {
    gp.value.line_spacing = gp.value.font_size
  }
}

async function onPreview(): Promise<void> {
  if (fonts.value.length === 0) {
    alert(`请在 ttf_library/ 目录放置 .ttf 字体。`)
    return
  }
  clampForSend()
  status.value = '渲染中…'
  try {
    const snap = toPlain()
    const res = await window.handwrite.render(snap)
    status.value = `渲染完成: ${res.pages.length} 页`
  } catch (err) {
    status.value = '就绪'
    alert(String(err instanceof Error ? err.message : err))
  }
}

async function onSaveConfig(): Promise<void> {
  clampForSend()
  const p = await window.handwrite.saveConfig(toPlain())
  if (p) status.value = `配置已保存: ${p}`
}

async function onLoadConfig(): Promise<void> {
  try {
    const m = await window.handwrite.loadConfig()
    if (!m) return
    loadFrom(m)
    status.value = '配置已加载'
  } catch (err) {
    alert(String(err instanceof Error ? err.message : err))
  }
}

onMounted(async () => {
  await initFonts()
  if (!model.text) {
    model.text = '使用 Electron + Vue 编写的手写字生成器，旨在完成一些手写作业任务。\n支持选区级参数覆盖：在文本中选中字段并调整覆盖参数。'
    onTextChanged(model.text)
  }
})
</script>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.body {
  flex: 1;
  display: flex;
  min-height: 0;
  gap: 6px;
  padding: 6px;
}
.left {
  flex: 1;
  display: flex;
  min-width: 0;
}
.right {
  width: 380px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  overflow: auto;
}
.panel.global {
  flex: 1;
}
.panel.override {
  flex: 0 0 auto;
  max-height: 45%;
}
.panel-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #222;
}
.ov-label {
  margin-bottom: 6px;
  color: #555;
}
.btn-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
