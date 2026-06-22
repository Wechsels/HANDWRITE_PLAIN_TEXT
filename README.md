# HandWrite Plain Text / 手写体纯文本生成器

中文（默认） | [English](#english)

> **必须**把 `.ttf` 字体文件放入 `ttf_library/` 目录。启动后会自动列出供选择；目录为空时编辑器会**直接报错**。 

---

## 简介

基于 `handright` 项目笔画级扰动（vendor 自 v8.2.0，BSD-3-Clause）+ 自建布局引擎，把纯文本渲染成"手写体"图片，用于公文写作，志愿书，思想汇报等无意义的手写文本。

## 功能

- **多窗口**：编辑窗口与预览窗口分离；预览支持缩放、拖动、打开输出文件夹；关闭预览后回到编辑窗口。
- **全局参数**：纸张宽高、字体、字号、行距、字距、留白、颜色、倍率、6 类扰动 sigma、对齐、下划线。
- **选区级覆盖**：在文本区选中字段后可单独调整字号、字距、横/纵/旋转笔画扰动、颜色、对齐、下划线。覆盖过的字段在编辑器中以红色背景标记；再次选中可看到已调参数。
- **配置持久化**：保存/加载 TOML 文件，包含全部全局参数、文本、所有选区覆盖。

## 依赖

- Python 3.13
- PySide6 ≥ 6.9
- Pillow ≥ 10
- toml ≥ 0.10.2

可选：pytest（开发/单测）。

## 安装与运行

```bash
# 1. 进入项目根
cd HANDWRITE_PLAIN_TEXT

# 2. 用 uv 创建虚拟环境并安装依赖
uv sync

# 3. 启动
uv run python src/main.py
```

> 也可手动：`uv venv && uv pip install -e . && python src/main.py`

## 字体

**必须**把 `.ttf` 字体文件放入 `ttf_library/` 目录。启动后会自动列出供选择；目录为空时编辑器会**直接报错**。 `.ttf` 字体文件可搭配[HANDWRITE TTF FONTBUILDER](https://github.com/Wechsels/HANDWRITE_TTF_FONTBUILDER.git)项目生成。

## 输出

渲染结果按页落盘到 `outputs/0.png`、`outputs/1.png` …。预览窗口的「打开输出文件夹」按钮可直接打开该目录。

## 选区覆盖操作

1. 在文本区用鼠标选中要单独控制的字段。
2. 右侧「选区参数覆盖」面板自动预填该字段的当前有效参数。
3. 调整要覆盖的项，点击「应用到选区」→ 该字段在编辑器中以红色背景标记。
4. 再次选中该字段，参数面板会显示已调参数。
5. 点击「清除选区覆盖」可恢复全局默认。

## 单测

```bash
uv run --group test python -m pytest tests/ -q
```

## 许可证

[![License: WNCPL v1.0](https://img.shields.io/badge/License-WNCPL%20v1.0-orange.svg)](LICENSE)

本项目基于 **Wechsels 非商用许可证 v1.0 (WNCPL v1.0)** 发布。

- 允许:查看、修改、非商业场景下分发
- 禁止:任何形式的商用
- 强制:保留版权声明与许可证副本；衍生作品必须使用本协议

第三方库 `handright`(vendor 化的笔画扰动代码)继续遵循其原始 **BSD-3-Clause** 许可证,详见 `LICENSE-handright.txt`。

详情请参阅 [LICENSE](LICENSE) 文件。Copyright (c) 2026 Yurui He (GitHub: Wechsels)。

---

<a name="english"></a>

## English

A decoupled multi-window handwritten-text generator. Edit and preview live in separate windows; preview supports zoom/drag and opens the output folder directly.

### Features

- **Multi-window**: Editor + Preview (modal). Preview returns focus to editor on close.
- **Global params**: paper size, font, size/line/word spacing, margins, colors, resolution, 6 perturbation sigmas, alignment, underline.
- **Range-level overrides**: select a span in the editor and override its font size, word spacing, x/y/θ stroke perturbation, color, alignment, underline. Overridden spans are marked with a red background; re-selecting them shows the adjusted values.
- **Config persistence**: TOML save/load including text and all per-range overrides.

### Install & run

```bash
cd Code-05-HANDWRITE_PLAIN_TEXT
uv sync
uv run python src/main.py
```

### Tests

```bash
uv run --group test python -m pytest tests/ -q
```

### License

[![License: WNCPL v1.0](https://img.shields.io/badge/License-WNCPL%20v1.0-orange.svg)](LICENSE)

This project is released under the **Wechsels Non-Commercial License v1.0 (WNCPL v1.0)**.

- Allowed: view, modify, redistribute for non-commercial purposes
- Prohibited: any form of commercial use
- Required: retain copyright notice and license copy; derivative works must use this license

The vendored `handright` stroke-perturbation code remains under its original **BSD-3-Clause** license — see `LICENSE-handright.txt` for details.

See the [LICENSE](LICENSE) file for full terms. Copyright (c) 2026 Yurui He (GitHub: Wechsels).
