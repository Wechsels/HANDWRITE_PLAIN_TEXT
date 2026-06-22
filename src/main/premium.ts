/**
 * 付费功能抽象层（stub，不实装）。移植自 src/premium/interfaces.py。
 *
 * 保留 3 类未来付费接口的清晰抽象，后续接入无需重写业务代码：
 * 1. PaperPresetProvider：输出纸张参数预设（A4 / B5 / 信纸…）
 * 2. AIFontEdgeEnhancer：AI 字体边缘调整
 * 3. OfficialDocPresetProvider：输出公文格式预设（标题/正文/落款…）
 */

export interface PaperPreset {
  name: string
  paper_w: number
  paper_h: number
  margin_top: number
  margin_bottom: number
  margin_left: number
  margin_right: number
}

export abstract class PaperPresetProvider {
  abstract getPresets(): PaperPreset[]
  /** 把预设合并进 params，返回新的 GlobalParams 字段字典。 */
  abstract apply(presetName: string, params: Record<string, unknown>): Record<string, unknown>
}

export abstract class AIFontEdgeEnhancer {
  /** 对渲染后的位图做边缘调整，返回处理后的 buffer。 */
  abstract enhance(
    buf: Uint8ClampedArray,
    w: number,
    h: number,
    params: Record<string, unknown>
  ): Uint8ClampedArray
}

export abstract class OfficialDocPresetProvider {
  /** 把 text 按公文结构分段，返回渲染前可消费的覆盖区间列表。 */
  abstract apply(
    text: string,
    params: Record<string, unknown>
  ): Array<{ start: number; end: number; params: Record<string, unknown> }>
}

/** 未激活的默认占位。所有 provider 调用都返回原始输入，不改变行为。 */
class NullRegistry {
  paper: PaperPresetProvider | null = null
  edgeEnhancer: AIFontEdgeEnhancer | null = null
  docPreset: OfficialDocPresetProvider | null = null

  enhanceImage(
    buf: Uint8ClampedArray,
    w: number,
    h: number,
    params: Record<string, unknown>
  ): Uint8ClampedArray {
    if (this.edgeEnhancer === null) return buf
    return this.edgeEnhancer.enhance(buf, w, h, params)
  }
}

export const registry = new NullRegistry()
