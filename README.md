# HandWrite Plain Text / 手写体纯文本生成器

中文（默认） | [English](#english)

> **必须**把 `.ttf` 字体文件放入 `ttf_library/` 目录。启动后会自动列出供选择；目录为空时点预览会**直接报错**。

---

## 简介

基于 `handright` 项目笔画级扰动（vendor 自 v8.2.0，BSD-3-Clause）+ 自建布局引擎，把纯文本渲染成"手写体"图片，用于公文写作，志愿书，思想汇报等无意义的手写文本。

技术栈：**Electron + Vue 3 + TypeScript + FontAwesome + Node.js**。渲染管线使用 `@napi-rs/canvas` 做字体光栅化与像素级笔画扰动。

另提供 `cli-anything-handwrite` Python CLI（`agent-harness/`），通过 `vite.config.cli.ts` 构建的 headless Node 桥调用**同一渲染管线**，供 Agent 程序化驱动。

## 功能

- **多窗口**：编辑窗口与预览窗口分离；预览支持缩放、拖动、打开输出文件夹；关闭预览后回到编辑窗口。
- **全局参数**：纸张宽高、字体、字号、行距、字距、留白、颜色、倍率、6 类扰动 sigma、对齐、下划线。
- **选区级覆盖**：在文本区选中字段后可单独调整字号、字距、横/纵/旋转笔画扰动、颜色、对齐、下划线。覆盖过的字段在编辑器中以红色背景标记；再次选中可看到已调参数。
- **配置保存**：保存/加载 TOML 文件，包含全部全局参数、文本、所有选区覆盖。

## 依赖

- Node.js ≥ 20
- Electron（开发依赖，随 `npm install` 安装）
- 运行时依赖：`@napi-rs/canvas`、`smol-toml`、`vue`、`vue-router`、`@fortawesome/fontawesome-free`

## 安装与运行

```bash
# 1. 进入项目根
cd HANDWRITE_PLAIN_TEXT

# 2. 安装依赖
npm install

# 3. 启动（开发模式）
npm run dev
```

打包：

```bash
npm run build      # 构建产物
npm run package    # 构建并打包为可执行文件（electron-builder）
```

## 字体

**必须**把 `.ttf` 字体文件放入 `ttf_library/` 目录。启动后会自动列出供选择；目录为空时点预览会**直接报错**。 `.ttf` 字体文件可搭配 [HANDWRITE TTF FONTBUILDER](https://github.com/Wechsels/HANDWRITE_TTF_FONTBUILDER.git) 项目生成。

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
npm test
```

覆盖选区模型（`tests/rangeModel.test.ts`）与布局引擎（`tests/layout.test.ts`），断言与原 Python 版一致。布局测试需要 `ttf_library/` 下存在 `.ttf` 字体，否则该组自动跳过。

## 项目结构

```
src/              # Vue 渲染进程 + Electron 主进程 + 渲染管线
  shared/         # 主进程与渲染进程共用的纯逻辑（文档模型、调色板、类型）
  main/           # Electron 主进程 + 渲染管线（layout/perturb/renderer/fontCache）
  preload/        # contextBridge IPC 桥
  renderer/       # Vue 3 渲染进程（编辑器 + 预览窗口）
tests/            # Vitest 单测
agent-harness/    # cli-anything-handwrite Python CLI（调用同一渲染管线）
skills/           # 技能描述
```

## Agent CLI

`agent-harness/` 下是 `cli-anything-handwrite`：基于 Click 的 Python CLI + REPL，调用与 GUI 相同的渲染管线（通过 `vite.config.cli.ts` 构建出的 `agent-harness/cli_anything/handwrite/scripts/render_backend.mjs` 作为 headless Node 桥）。所有命令支持 `--json` 输出。

```bash
cd agent-harness
pip install -e .                           # 安装 CLI
npx vite build --config ../vite.config.cli.ts   # 构建 headless 渲染后端（首次需要）
handwrite-cli --help
handwrite-cli project new --text "你好"
handwrite-cli render run --out ./out
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

Stack: **Electron + Vue 3 + TypeScript + FontAwesome + Node.js**. The render pipeline uses `@napi-rs/canvas` for font rasterization and pixel-level stroke perturbation.

Also ships `cli-anything-handwrite`, a Python CLI under `agent-harness/` that drives the same render pipeline via a headless Node bridge (built with `vite.config.cli.ts`).

### Features

- **Multi-window**: Editor + Preview (modal). Preview returns focus to editor on close.
- **Global params**: paper size, font, size/line/word spacing, margins, colors, resolution, 6 perturbation sigmas, alignment, underline.
- **Range-level overrides**: select a span in the editor and override its font size, word spacing, x/y/θ stroke perturbation, color, alignment, underline. Overridden spans are marked with a red background; re-selecting them shows the adjusted values.
- **Config persistence**: TOML save/load including text and all per-range overrides.

### Install & run

```bash
cd HANDWRITE_PLAIN_TEXT
npm install
npm run dev
```

Package: `npm run package`.

### Tests

```bash
npm test
```

Covers the range model (`tests/rangeModel.test.ts`) and the layout engine (`tests/layout.test.ts`). Layout tests require a `.ttf` font in `ttf_library/`; otherwise that suite is skipped.

### Project layout

```
src/              # Vue renderer + Electron main + render pipeline
agent-harness/    # cli-anything-handwrite Python CLI (same render pipeline)
skills/           # Skill descriptions
```

### Agent CLI

```bash
cd agent-harness
pip install -e .
npx vite build --config ../vite.config.cli.ts   # build headless backend (once)
handwrite-cli --help
```

### License

[![License: WNCPL v1.0](https://img.shields.io/badge/License-WNCPL%20v1.0-orange.svg)](LICENSE)

This project is released under the **Wechsels Non-Commercial License v1.0 (WNCPL v1.0)**.

- Allowed: view, modify, redistribute for non-commercial purposes
- Prohibited: any form of commercial use
- Required: retain copyright notice and license copy; derivative works must use this license

The vendored `handright` stroke-perturbation code remains under its original **BSD-3-Clause** license — see `LICENSE-handright.txt` for details.

See the [LICENSE](LICENSE) file for full terms. Copyright (c) 2026 Yurui He (GitHub: Wechsels).
