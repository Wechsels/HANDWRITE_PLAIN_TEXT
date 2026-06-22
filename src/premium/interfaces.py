"""付费功能抽象层（stub，不实装）。

保留 3 类未来付费接口的清晰抽象，后续接入无需重写业务代码：
1. PaperPresetProvider：输出纸张参数预设（A4 / B5 / 信纸…）
2. AIFontEdgeEnhancer：AI 字体边缘调整
3. OfficialDocPresetProvider：输出公文格式预设（标题/正文/落款…）
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaperPresetProvider(ABC):
    @abstractmethod
    def get_presets(self) -> list[dict[str, int]]:
        """返回 [{name, paper_w, paper_h, margin_top, margin_bottom, margin_left, margin_right}, ...]"""

    @abstractmethod
    def apply(self, preset_name: str, params: dict) -> dict:
        """把预设合并进 params，返回新的 GlobalParams 字段字典。"""


class AIFontEdgeEnhancer(ABC):
    @abstractmethod
    def enhance(self, image, params: dict) -> Any:
        """对渲染后的 PIL Image 做边缘调整，返回处理后的 Image。"""


class OfficialDocPresetProvider(ABC):
    @abstractmethod
    def apply(self, text: str, params: dict) -> dict:
        """把 text 按公文结构分段（标题/正文/落款…），返回渲染前可消费的覆盖区间列表。"""


class _NullRegistry:
    """未激活的默认占位。所有 provider 调用都返回原始输入，不改变行为。"""

    paper: PaperPresetProvider | None = None
    edge_enhancer: AIFontEdgeEnhancer | None = None
    doc_preset: OfficialDocPresetProvider | None = None

    def enhance_image(self, image, params: dict):
        if self.edge_enhancer is None:
            return image
        return self.edge_enhancer.enhance(image, params)


registry = _NullRegistry()
