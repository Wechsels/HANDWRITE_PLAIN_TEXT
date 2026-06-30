import { createRequire } from "node:module";
import * as fs from "node:fs";
import * as path from "node:path";
import { GlobalFonts, createCanvas } from "@napi-rs/canvas";
import { parse, stringify } from "smol-toml";
//#region \0rolldown/runtime.js
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __esmMin = (fn, res) => () => (fn && (res = fn(fn = 0)), res);
var __exportAll = (all, no_symbols) => {
	let target = {};
	for (var name in all) __defProp(target, name, {
		get: all[name],
		enumerable: true
	});
	if (!no_symbols) __defProp(target, Symbol.toStringTag, { value: "Module" });
	return target;
};
var __copyProps = (to, from, except, desc) => {
	if (from && typeof from === "object" || typeof from === "function") for (var keys = __getOwnPropNames(from), i = 0, n = keys.length, key; i < n; i++) {
		key = keys[i];
		if (!__hasOwnProp.call(to, key) && key !== except) __defProp(to, key, {
			get: ((k) => from[k]).bind(null, key),
			enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable
		});
	}
	return to;
};
var __toCommonJS = (mod) => __hasOwnProp.call(mod, "module.exports") ? mod["module.exports"] : __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var __require = /* @__PURE__ */ createRequire(import.meta.url);
//#endregion
//#region src/shared/palette.ts
var DEFAULT_FILL = [
	0,
	0,
	0,
	255
];
var DEFAULT_BACKGROUND = [
	255,
	255,
	255,
	255
];
//#endregion
//#region src/shared/settings.ts
var ADJUSTABLE_KEYS = [
	"font_size",
	"word_spacing",
	"perturb_x_sigma",
	"perturb_y_sigma",
	"perturb_theta_sigma",
	"fill",
	"alignment",
	"underline"
];
function defaultGlobalParams(fontPath = "") {
	return {
		paper_w: 667,
		paper_h: 945,
		font_path: fontPath,
		font_size: 30,
		line_spacing: 70,
		word_spacing: 1,
		margin_top: 10,
		margin_bottom: 10,
		margin_left: 10,
		margin_right: 10,
		fill: [...DEFAULT_FILL],
		background: [...DEFAULT_BACKGROUND],
		rate: 4,
		line_spacing_sigma: 1,
		font_size_sigma: 1,
		word_spacing_sigma: 1,
		perturb_x_sigma: 1,
		perturb_y_sigma: 1,
		perturb_theta_sigma: .05,
		alignment: "left",
		underline: false
	};
}
function rangeOverrideFromDict(d) {
	return {
		start: Number(d.start),
		end: Number(d.end),
		params: { ...d.params ?? {} }
	};
}
function globalParamsToDict(gp) {
	return { ...gp };
}
function globalParamsFromDict(d) {
	const base = defaultGlobalParams();
	const out = { ...base };
	for (const k of Object.keys(base)) if (k in d && d[k] !== void 0 && d[k] !== null) out[k] = d[k];
	return out;
}
function rangeOverrideToDict(o) {
	return {
		start: o.start,
		end: o.end,
		params: { ...o.params }
	};
}
function documentToDict(m) {
	return {
		text: m.text,
		global_params: globalParamsToDict(m.global_params),
		overrides: m.overrides.map(rangeOverrideToDict)
	};
}
function documentFromDict(d) {
	const gp = globalParamsFromDict(d.global_params ?? {});
	const overrides = (d.overrides ?? []).map(rangeOverrideFromDict);
	return {
		text: d.text ?? "",
		global_params: gp,
		overrides
	};
}
/** 提取一个 override params 对象中合法的 adjustable 键（值非 null/undefined）。 */
function cleanParams(params) {
	const cleaned = {};
	for (const k of ADJUSTABLE_KEYS) {
		const v = params[k];
		if (v !== void 0 && v !== null) cleaned[k] = v;
	}
	return cleaned;
}
function clampRange(n, start, end) {
	start = Math.max(0, Math.min(start, n));
	end = Math.max(start, Math.min(end, n));
	return [start, end];
}
var DocumentModelOps = class DocumentModelOps {
	/** 在 model 上原地操作：合并 newParams 到 [start,end)。 */
	static setRange(model, start, end, newParams) {
		const n = model.text.length;
		[start, end] = clampRange(n, start, end);
		const cleaned = cleanParams(newParams);
		if (start >= end || Object.keys(cleaned).length === 0) return;
		DocumentModelOps.splitAt(model, start);
		DocumentModelOps.splitAt(model, end);
		const inside = model.overrides.filter((s) => s.start >= start && s.end <= end);
		for (const seg of inside) Object.assign(seg.params, cleaned);
		const covered = [...inside].sort((a, b) => a.start - b.start);
		const gaps = [];
		let cursor = start;
		for (const seg of covered) {
			if (seg.start > cursor) gaps.push({
				start: cursor,
				end: seg.start,
				params: { ...cleaned }
			});
			cursor = seg.end;
		}
		if (cursor < end) gaps.push({
			start: cursor,
			end,
			params: { ...cleaned }
		});
		model.overrides.push(...gaps);
		model.overrides.sort((a, b) => a.start - b.start);
		DocumentModelOps.mergeAdjacent(model);
	}
	/** 删除 [start,end) 内的 override，保留外侧。 */
	static clearRange(model, start, end) {
		const n = model.text.length;
		[start, end] = clampRange(n, start, end);
		if (start >= end) return;
		DocumentModelOps.splitAt(model, start);
		DocumentModelOps.splitAt(model, end);
		model.overrides = model.overrides.filter((s) => !(s.start >= start && s.end <= end));
	}
	/** 把任意跨越 point 的段切两段。point 越界则不动。 */
	static splitAt(model, point) {
		if (point <= 0 || point >= model.text.length) return;
		const newList = [];
		for (const seg of model.overrides) if (seg.start < point && point < seg.end) {
			newList.push({
				start: seg.start,
				end: point,
				params: { ...seg.params }
			});
			newList.push({
				start: point,
				end: seg.end,
				params: { ...seg.params }
			});
		} else newList.push(seg);
		model.overrides = newList;
	}
	/** 合并相邻且参数相同的段。 */
	static mergeAdjacent(model) {
		if (model.overrides.length === 0) return;
		const merged = [model.overrides[0]];
		for (const seg of model.overrides.slice(1)) {
			const last = merged[merged.length - 1];
			if (last.end === seg.start && paramsEqual(last.params, seg.params)) last.end = seg.end;
			else merged.push(seg);
		}
		model.overrides = merged;
	}
	static overrideAt(model, index) {
		for (const seg of model.overrides) if (seg.start <= index && index < seg.end) return seg;
		return null;
	}
	/** 全局参数叠加覆盖 index 的段。 */
	static effectiveParams(model, index) {
		const base = globalParamsToDict(model.global_params);
		const seg = DocumentModelOps.overrideAt(model, index);
		if (seg) Object.assign(base, seg.params);
		return base;
	}
	static rangesForMarking(model) {
		return model.overrides.map((s) => [s.start, s.end]);
	}
	/** 文本缩短时裁剪越界 override，对应 editor `_on_text_changed`。 */
	static trimToText(model) {
		const n = model.text.length;
		model.overrides = model.overrides.filter((o) => o.start < n && o.end <= n);
		for (const o of model.overrides) {
			o.start = Math.max(0, o.start);
			o.end = Math.min(o.end, n);
		}
	}
};
function paramsEqual(a, b) {
	const ak = Object.keys(a);
	const bk = Object.keys(b);
	if (ak.length !== bk.length) return false;
	for (const k of ak) {
		const av = a[k];
		const bv = b[k];
		if (Array.isArray(av) && Array.isArray(bv)) {
			if (av.length !== bv.length || av.some((v, i) => v !== bv[i])) return false;
		} else if (av !== bv) return false;
	}
	return true;
}
//#endregion
//#region src/main/render/fontCache.ts
/**
* 字体注册与字形光栅化缓存（移植自 src/render/font_cache.py）。
*
* 用 @napi-rs/canvas 替代 PIL ImageFont/ImageDraw：
* - `GlobalFonts.registerFromPath` 一次性注册 TTF，缓存 fontPath→family。
* - 单字形渲染到 scratch canvas，读 alpha 通道扫描真实墨迹 bbox（等价 PIL `font.getbbox`）。
*/
var _FAMILY_CACHE = /* @__PURE__ */ new Map();
var _MISSING = /* @__PURE__ */ new Set();
/** 墨迹阈值：alpha >= INK_THRESHOLD 视为落墨（模拟 PIL "1" 模式的 mono 二值化）。 */
var INK_THRESHOLD = 128;
function getFontFamily(fontPath) {
	const cached = _FAMILY_CACHE.get(fontPath);
	if (cached) return cached;
	if (_MISSING.has(fontPath)) return null;
	const family = `hw_${(fontPath.replace(/[/\\]+/g, "/").split("/").pop() ?? fontPath).replace(/\.[^.]+$/, "")}`;
	try {
		if (!GlobalFonts.registerFromPath(fontPath, family)) {
			_MISSING.add(fontPath);
			return null;
		}
	} catch {
		_MISSING.add(fontPath);
		return null;
	}
	_FAMILY_CACHE.set(fontPath, family);
	return family;
}
/** 缓存 key：fontPath|size|char —— layout 测宽与 renderer 绘制共用同一份光栅化结果。 */
var _GLYPH_CACHE = /* @__PURE__ */ new Map();
function getRasterized(fontPath, size, char) {
	const key = `${fontPath}|${size}|${char}`;
	const hit = _GLYPH_CACHE.get(key);
	if (hit) return hit;
	const family = getFontFamily(fontPath);
	if (!family) return null;
	const r = rasterizeGlyph(family, size, char);
	_GLYPH_CACHE.set(key, r);
	return r;
}
/** 字形墨迹宽度（advance），等价 Python `font.getbbox(ch)` 的 `r - l`。 */
function getInkWidth(fontPath, size, char) {
	const r = getRasterized(fontPath, size, char);
	if (!r || !r.inkBbox) return 0;
	return r.inkBbox[2] - r.inkBbox[0];
}
/**
* 渲染单字形到 scratch canvas 并返回 alpha + 墨迹 bbox。
* 等价 Python: `Image.new("1",(3*pad,3*pad)); ImageDraw.text((pad,pad),char,fill=1,font=font); font.getbbox(char)`。
*/
function rasterizeGlyph(family, size, char) {
	const pad = Math.max(size, 1);
	const dim = 3 * pad;
	const ctx = createCanvas(dim, dim).getContext("2d");
	ctx.clearRect(0, 0, dim, dim);
	ctx.fillStyle = "rgba(0,0,0,0)";
	ctx.font = `${size}px "${family}"`;
	ctx.textBaseline = "top";
	ctx.textAlign = "left";
	ctx.fillStyle = "#ffffff";
	ctx.fillText(char, pad, pad);
	const data = ctx.getImageData(0, 0, dim, dim).data;
	const alpha = new Uint8Array(dim * dim);
	for (let i = 0; i < alpha.length; i++) alpha[i] = data[i * 4 + 3];
	let minX = dim, minY = dim, maxX = -1, maxY = -1;
	for (let y = 0; y < dim; y++) for (let x = 0; x < dim; x++) if (alpha[y * dim + x] >= INK_THRESHOLD) {
		if (x < minX) minX = x;
		if (x > maxX) maxX = x;
		if (y < minY) minY = y;
		if (y > maxY) maxY = y;
	}
	return {
		scratchW: dim,
		scratchH: dim,
		alpha,
		inkBbox: maxX < 0 ? null : [
			minX,
			minY,
			maxX + 1,
			maxY + 1
		]
	};
}
//#endregion
//#region src/main/render/layout.ts
var START_CHARS = "\"（[<";
var END_CHARS = "，。》？；：\"】｝、！％）,.>?;:]}!%)′″℃℉";
function lineAlignment(model, lineBuffer) {
	if (lineBuffer.length) return DocumentModelOps.effectiveParams(model, lineBuffer[0].i)["alignment"];
	return model.global_params.alignment;
}
function layoutDocument(model, rand) {
	const gp = model.global_params;
	const rate = gp.rate;
	const pw = gp.paper_w * rate;
	const ph = gp.paper_h * rate;
	const lm = gp.margin_left * rate;
	const rm = gp.margin_right * rate;
	const tm = gp.margin_top * rate;
	const bm = gp.margin_bottom * rate;
	const lineSpacing = gp.line_spacing * rate;
	const lss = gp.line_spacing_sigma * rate;
	const fss = gp.font_size_sigma * rate;
	const wss = gp.word_spacing_sigma * rate;
	const baseFontSizePx = gp.font_size * rate;
	const text = model.text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
	const n = text.length;
	const pages = [];
	let currentJobs = [];
	let lineBuffer = [];
	let pageIndex = 0;
	let x = lm;
	let y = tm + lineSpacing - baseFontSizePx;
	function flushLine(alignment) {
		if (lineBuffer.length === 0) return;
		const firstX = lineBuffer[0].x;
		const last = lineBuffer[lineBuffer.length - 1];
		const lineWidth = last.x + last.advance - firstX;
		const avail = pw - lm - rm;
		const offsetX = alignment === "center" ? Math.max(0, (avail - lineWidth) / 2) : 0;
		for (const it of lineBuffer) currentJobs.push({
			char: it.ch,
			page: pageIndex,
			x: it.x + offsetX,
			y: it.y,
			font_size: it.fs,
			perturb_x_sigma: it.sigmas[0],
			perturb_y_sigma: it.sigmas[1],
			perturb_theta_sigma: it.sigmas[2],
			fill: it.fill,
			underline: it.ul
		});
		lineBuffer = [];
	}
	function nextLine() {
		flushLine(lineAlignment(model, lineBuffer));
		y += lineSpacing;
		x = lm;
	}
	function newPage() {
		flushLine(lineAlignment(model, lineBuffer));
		if (currentJobs.length) pages.push(currentJobs);
		currentJobs = [];
		pageIndex = pages.length;
		y = tm + lineSpacing - baseFontSizePx;
	}
	let i = 0;
	while (i < n) {
		const ch = text[i];
		if (ch === "\n") {
			nextLine();
			if (y > ph - bm - baseFontSizePx) newPage();
			i += 1;
			continue;
		}
		const eff = DocumentModelOps.effectiveParams(model, i);
		const fsNominal = eff.font_size * rate;
		const fsActual = Math.max(Math.round(rand.gauss(fsNominal, fss)), 1);
		const advance = getInkWidth(gp.font_path, fsActual, ch);
		if (x > pw - rm - 2 * fsActual && START_CHARS.includes(ch) || x > pw - rm - fsActual && !END_CHARS.includes(ch)) {
			nextLine();
			if (y > ph - bm - baseFontSizePx) newPage();
			continue;
		}
		const yJit = rand.gauss(y, lss);
		const sigmas = [
			eff.perturb_x_sigma,
			eff.perturb_y_sigma,
			eff.perturb_theta_sigma
		];
		lineBuffer.push({
			i,
			ch,
			fs: fsActual,
			x,
			y: yJit,
			advance,
			fill: eff.fill,
			ul: eff.underline,
			sigmas
		});
		x += rand.gauss(eff.word_spacing * rate + advance, wss);
		i += 1;
	}
	flushLine(lineAlignment(model, lineBuffer));
	if (currentJobs.length) pages.push(currentJobs);
	if (pages.length === 0) pages.push([]);
	return {
		pages,
		pageSize: [pw, ph]
	};
}
//#endregion
//#region src/main/render/perturb.ts
/**
* 笔画级扰动（移植自 src/render/perturb.py，vendored 自 handright BSD-3-Clause）。
*
* 改动点与 Python 版一致：逐字形提取笔画，接受逐字形 sigma 与目标画布偏移，
* 写入 RGBA 画布。此处把 PIL "1" 位图替换为 `inkAt(x,y)` 谓词，
* 把 PIL `canvas.load()[x,y]=fill` 替换为对 RGBA Uint8ClampedArray 的直接写入。
*/
var _MAX_INT16_VALUE = 65535;
/** 提取所有笔画（4 邻域连通墨迹分量），返回每笔的像素点列表。 */
function extractStrokes(inkAt, bbox) {
	const [left, upper, right, lower] = bbox;
	if (right >= _MAX_INT16_VALUE || lower >= _MAX_INT16_VALUE) throw new Error("glyph bitmap too large for stroke extraction");
	const visited = /* @__PURE__ */ new Set();
	const key = (x, y) => x << 16 | y;
	const strokes = [];
	for (let y = upper; y < lower; y++) for (let x = left; x < right; x++) {
		if (!inkAt(x, y) || visited.has(key(x, y))) continue;
		const stroke = [];
		const stack = [[x, y]];
		visited.add(key(x, y));
		while (stack.length) {
			const [cx, cy] = stack.pop();
			stroke.push([cx, cy]);
			if (cy - 1 >= upper && inkAt(cx, cy - 1) && !visited.has(key(cx, cy - 1))) {
				visited.add(key(cx, cy - 1));
				stack.push([cx, cy - 1]);
			}
			if (cy + 1 < lower && inkAt(cx, cy + 1) && !visited.has(key(cx, cy + 1))) {
				visited.add(key(cx, cy + 1));
				stack.push([cx, cy + 1]);
			}
			if (cx - 1 >= left && inkAt(cx - 1, cy) && !visited.has(key(cx - 1, cy))) {
				visited.add(key(cx - 1, cy));
				stack.push([cx - 1, cy]);
			}
			if (cx + 1 < right && inkAt(cx + 1, cy) && !visited.has(key(cx + 1, cy))) {
				visited.add(key(cx + 1, cy));
				stack.push([cx + 1, cy]);
			}
		}
		strokes.push(stroke);
	}
	return strokes;
}
function rotate(center, x, y, theta) {
	if (theta === 0) return [x, y];
	const cosT = Math.cos(theta);
	const sinT = Math.sin(theta);
	const dx = x - center[0];
	const dy = y - center[1];
	return [dx * cosT + dy * sinT + center[0], dy * cosT - dx * sinT + center[1]];
}
/**
* 在 scratch 位图 `inkAt` 的 `inkBbox` 区域提取笔画，按 sigma 扰动后写入页面 RGBA 缓冲。
*
* @param pageData 页面 RGBA 缓冲（Uint8ClampedArray）
* @param pageW    页面宽
* @param pageH    页面高
* @param offset   (ox, oy) 笔画像素落点的全局偏移
* @param fill     RGBA 填充
* @param rand     种子化随机源
*/
function perturbGlyph(inkAt, inkBbox, pageData, pageW, pageH, offset, sigmaX, sigmaY, sigmaTheta, fill, rand) {
	const strokes = extractStrokes(inkAt, inkBbox);
	const [ox, oy] = offset;
	for (const stroke of strokes) {
		if (stroke.length === 0) continue;
		let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
		for (const [x, y] of stroke) {
			if (x < minX) minX = x;
			if (x > maxX) maxX = x;
			if (y < minY) minY = y;
			if (y > maxY) maxY = y;
		}
		const center = [(minX + maxX) / 2, (minY + maxY) / 2];
		const dx = rand.gauss(0, sigmaX);
		const dy = rand.gauss(0, sigmaY);
		const theta = rand.gauss(0, sigmaTheta);
		for (const [lx, ly] of stroke) {
			const [nx, ny] = rotate(center, lx, ly, theta);
			const tx = Math.round(nx + ox + dx);
			const ty = Math.round(ny + oy + dy);
			if (tx >= 0 && tx < pageW && ty >= 0 && ty < pageH) {
				const idx = (ty * pageW + tx) * 4;
				pageData[idx] = fill.r;
				pageData[idx + 1] = fill.g;
				pageData[idx + 2] = fill.b;
				pageData[idx + 3] = fill.a;
			}
		}
	}
}
//#endregion
//#region src/main/render/rand.ts
/**
* 种子化随机数（移植自 Python `random.Random`）。
*
* 不与 Python Mersenne Twister 逐位对齐，仅保证：
* - 同 seed → 同输出序列（可复现）；
* - gauss 分布形状与 Python 一致（Box-Muller + gauss_next 缓存，sigma==0 返回 mu）。
*
* Python `random.gauss`:
*   x2pi = random() * 2π; g2rad = sqrt(-2 ln(1-random())); z = cos(x2pi)*g2rad; next = sin(x2pi)*g2rad
*/
var TWO_PI = Math.PI * 2;
var Rng = class {
	state;
	gaussNext = null;
	constructor(seed) {
		this.state = seed >>> 0;
	}
	/** [0, 1) 均匀分布。 */
	random() {
		this.state |= 0;
		this.state = this.state + 1831565813 | 0;
		let t = Math.imul(this.state ^ this.state >>> 15, 1 | this.state);
		t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
		return ((t ^ t >>> 14) >>> 0) / 4294967296;
	}
	gauss(mu, sigma) {
		if (sigma === 0) return mu;
		let z = this.gaussNext;
		this.gaussNext = null;
		if (z === null) {
			const x2pi = this.random() * TWO_PI;
			const g2rad = Math.sqrt(-2 * Math.log(1 - this.random()));
			z = Math.cos(x2pi) * g2rad;
			this.gaussNext = Math.sin(x2pi) * g2rad;
		}
		return mu + z * sigma;
	}
};
/** 用 crypto 生成一个 32 位种子（seed=null 时使用）。 */
function randomSeed() {
	const buf = new Uint32Array(1);
	const g = globalThis;
	if (g.crypto?.getRandomValues) {
		g.crypto.getRandomValues(buf);
		return buf[0];
	}
	return Math.floor(Math.random() * 4294967296) >>> 0;
}
function makeRng(seed) {
	return new Rng(seed === null ? randomSeed() : seed);
}
//#endregion
//#region src/main/premium.ts
/** 未激活的默认占位。所有 provider 调用都返回原始输入，不改变行为。 */
var NullRegistry = class {
	paper = null;
	edgeEnhancer = null;
	docPreset = null;
	enhanceImage(buf, w, h, params) {
		if (this.edgeEnhancer === null) return buf;
		return this.edgeEnhancer.enhance(buf, w, h, params);
	}
};
var registry = new NullRegistry();
//#endregion
//#region agent-harness/cli_src/electron-stub.js
var app;
var init_electron_stub = __esmMin((() => {
	app = {
		isPackaged: false,
		getAppPath: () => process.cwd(),
		getPath: () => process.cwd()
	};
}));
//#endregion
//#region src/main/paths.ts
var paths_exports = /* @__PURE__ */ __exportAll({
	LOGS_DIR: () => LOGS_DIR,
	OUTPUTS_DIR: () => OUTPUTS_DIR,
	PROJECT_ROOT: () => PROJECT_ROOT,
	TTF_LIBRARY_DIR: () => TTF_LIBRARY_DIR,
	ensureDirs: () => ensureDirs
});
function projectRoot() {
	if (app.isPackaged) return process.resourcesPath;
	return app.getAppPath();
}
function userRoot() {
	if (app.isPackaged) return app.getPath("userData");
	return projectRoot();
}
/** 启动时确保目录存在（对应 Python paths.py 末尾的 mkdir）。 */
function ensureDirs() {
	for (const d of [
		OUTPUTS_DIR,
		LOGS_DIR,
		TTF_LIBRARY_DIR
	]) fs.mkdirSync(d, { recursive: true });
}
var PROJECT_ROOT, TTF_LIBRARY_DIR, OUTPUTS_DIR, LOGS_DIR;
var init_paths = __esmMin((() => {
	init_electron_stub();
	PROJECT_ROOT = projectRoot();
	TTF_LIBRARY_DIR = path.join(PROJECT_ROOT, "ttf_library");
	OUTPUTS_DIR = path.join(userRoot(), "outputs");
	LOGS_DIR = path.join(userRoot(), "logs");
}));
//#endregion
//#region src/main/render/renderer.ts
/**
* 渲染管线（移植自 src/render/renderer.py）。
*
* 把 DocumentModel 渲染为分页 RGBA 位图。用 Uint8ClampedArray 缓冲替代 PIL Image，
* 用 @napi-rs/canvas 编码 PNG。笔画扰动委托 perturbGlyph。
*/
var RenderError = class extends Error {};
function fillBackground(buf, bg) {
	const [r, g, b, a] = bg;
	for (let i = 0; i < buf.length; i += 4) {
		buf[i] = r;
		buf[i + 1] = g;
		buf[i + 2] = b;
		buf[i + 3] = a;
	}
}
function drawUnderline(buf, w, h, job, inkWidth) {
	const uy = Math.floor(job.y + job.font_size);
	const thickness = Math.max(1, Math.floor(Math.max(job.font_size, 1) / 10));
	const x0 = Math.floor(job.x);
	const x1 = Math.floor(job.x + inkWidth);
	const [r, g, b, a] = job.fill;
	for (let ty = uy; ty < uy + thickness; ty++) {
		if (ty < 0 || ty >= h) continue;
		for (let tx = x0; tx <= x1; tx++) {
			if (tx < 0 || tx >= w) continue;
			const idx = (ty * w + tx) * 4;
			buf[idx] = r;
			buf[idx + 1] = g;
			buf[idx + 2] = b;
			buf[idx + 3] = a;
		}
	}
}
function renderGlyph(buf, w, h, job, fontPath, rand) {
	const r = getRasterized(fontPath, job.font_size, job.char);
	if (!r || !r.inkBbox) return;
	const pad = Math.max(job.font_size, 1);
	const inkWidth = r.inkBbox[2] - r.inkBbox[0];
	const offset = [job.x - pad, job.y - pad];
	const inkAt = (x, y) => r.alpha[y * r.scratchW + x] >= 128;
	const fill = {
		r: job.fill[0],
		g: job.fill[1],
		b: job.fill[2],
		a: job.fill[3]
	};
	perturbGlyph(inkAt, r.inkBbox, buf, w, h, offset, job.perturb_x_sigma, job.perturb_y_sigma, job.perturb_theta_sigma, fill, rand);
	if (job.underline) drawUnderline(buf, w, h, job, inkWidth);
}
function renderPages(model, seed = null, save = true) {
	const gp = model.global_params;
	if (gp.font_size > gp.line_spacing) throw new RenderError("font_size 必须 <= line_spacing");
	if (gp.paper_w <= 0 || gp.paper_h <= 0) throw new RenderError("纸张宽高必须为正");
	const rand = makeRng(seed);
	const { pages, pageSize } = layoutDocument(model, rand);
	const [cw, ch] = pageSize;
	const bg = gp.background;
	const result = [];
	for (const pageJobs of pages) {
		const buf = new Uint8ClampedArray(cw * ch * 4);
		fillBackground(buf, bg);
		for (const job of pageJobs) renderGlyph(buf, cw, ch, job, gp.font_path, rand);
		const enhanced = registry.enhanceImage(buf, cw, ch, { font_path: gp.font_path });
		result.push({
			width: cw,
			height: ch,
			data: enhanced
		});
	}
	const paths = [];
	if (save) paths.push(...saveOutputs(result));
	return {
		pages: result,
		paths
	};
}
/** 把页面位图编码为 PNG 落盘到 OUTPUTS_DIR，清掉旧 png。返回文件路径列表。 */
function saveOutputs(images) {
	const { OUTPUTS_DIR } = (init_paths(), __toCommonJS(paths_exports));
	const fs = __require("node:fs");
	const path = __require("node:path");
	fs.mkdirSync(OUTPUTS_DIR, { recursive: true });
	for (const f of fs.readdirSync(OUTPUTS_DIR)) if (f.endsWith(".png")) try {
		fs.unlinkSync(path.join(OUTPUTS_DIR, f));
	} catch {}
	const outPaths = [];
	images.forEach((im, i) => {
		const canvas = createCanvas(im.width, im.height);
		const ctx = canvas.getContext("2d");
		const imageData = ctx.createImageData(im.width, im.height);
		imageData.data.set(im.data);
		ctx.putImageData(imageData, 0, 0);
		const p = path.join(OUTPUTS_DIR, `${i}.png`);
		fs.writeFileSync(p, canvas.toBuffer("image/png"));
		outPaths.push(p);
	});
	return outPaths;
}
//#endregion
//#region src/main/persistence.ts
/**
* TOML 配置持久化（移植自 src/config/persistence.py）。
* 用 smol-toml 替代 Python `toml`/`tomllib`。
*/
function saveModel(model, filePath) {
	const toml = stringify(documentToDict(model));
	fs.writeFileSync(filePath, toml, "utf-8");
}
function loadModel(filePath) {
	return documentFromDict(parse(fs.readFileSync(filePath, "utf-8")));
}
//#endregion
//#region agent-harness/cli_src/cli_render_entry.ts
/**
* Headless render backend entry — the bridge the Python CLI invokes via
* `node render_backend.mjs`. It uses the REAL render pipeline
* (layout → perturb → fontCache → renderer) and the REAL persistence layer
* (smol-toml + documentFromDict/documentToDict). It does NOT touch Electron:
* `renderPages` is called with `save=false` so `saveOutputs` (the only Electron
* touch, via lazy `require('../paths')`) never runs.
*
* Subcommands (selected by first argv):
*   render <model.json> <outdir> [seed]        -> JSON {ok,seed,pages:[{width,height,path,bytes}]}
*   serialize-toml <model.json> <out.toml>      -> JSON {ok,path}
*   load-toml <in.toml> <out.json>              -> JSON {ok,model}
*   list-fonts <out.json> [ttf_dir]             -> JSON {ok,fonts:[{name,path}]}
*   probe                                       -> JSON {ok,node,hasCanvas,ttfLibrary,fonts}
*
* The Python side always passes JSON via stdout. Errors -> JSON {ok:false,error}.
*/
function emit(obj) {
	process.stdout.write(JSON.stringify(obj));
}
/** Walk up from `from` (default cwd) to find a directory containing `ttf_library/`. */
function findProjectRoot(from = process.cwd()) {
	let dir = path.resolve(from);
	for (let i = 0; i < 12; i++) {
		if (fs.existsSync(path.join(dir, "ttf_library"))) return dir;
		if (fs.existsSync(path.join(dir, "package.json")) && fs.existsSync(path.join(dir, "src"))) return dir;
		const parent = path.dirname(dir);
		if (parent === dir) break;
		dir = parent;
	}
	return process.cwd();
}
function listFontsIn(dir) {
	const result = [];
	if (!fs.existsSync(dir)) return result;
	for (const name of fs.readdirSync(dir).sort()) if (name.toLowerCase().endsWith(".ttf")) {
		const full = path.join(dir, name);
		const stem = name.replace(/\.[^.]+$/, "");
		result.push({
			name: stem,
			path: full
		});
	}
	return result;
}
/** Encode an in-memory RGBA page to a PNG file with the real @napi-rs/canvas. */
function writePagePng(page, outPath) {
	const canvas = createCanvas(page.width, page.height);
	const ctx = canvas.getContext("2d");
	const imageData = ctx.createImageData(page.width, page.height);
	imageData.data.set(page.data);
	ctx.putImageData(imageData, 0, 0);
	fs.writeFileSync(outPath, canvas.toBuffer("image/png"));
}
function cmdRender(modelPath, outdir, seedArg) {
	const raw = fs.readFileSync(modelPath, "utf-8");
	const model = documentFromDict(JSON.parse(raw));
	const gp = model.global_params;
	if (!gp.font_path || !fs.existsSync(gp.font_path)) {
		const root = findProjectRoot();
		const fonts = listFontsIn(path.join(root, "ttf_library"));
		if (fonts.length === 0) {
			emit({
				ok: false,
				error: `No .ttf font found in ${path.join(root, "ttf_library")}`
			});
			return;
		}
		gp.font_path = fonts[0].path;
	}
	const seed = seedArg === void 0 || seedArg === "" ? null : Number(seedArg);
	fs.mkdirSync(outdir, { recursive: true });
	for (const f of fs.readdirSync(outdir)) if (f.endsWith(".png")) try {
		fs.unlinkSync(path.join(outdir, f));
	} catch {}
	let result;
	try {
		result = renderPages(model, seed, false);
	} catch (e) {
		emit({
			ok: false,
			error: e instanceof RenderError || e instanceof Error ? e.message : String(e)
		});
		return;
	}
	const pages = result.pages.map((p, i) => {
		const pPath = path.join(outdir, `${i}.png`);
		writePagePng(p, pPath);
		const stat = fs.statSync(pPath);
		return {
			width: p.width,
			height: p.height,
			path: pPath,
			bytes: stat.size,
			index: i
		};
	});
	emit({
		ok: true,
		seed: seed ?? -1,
		pages,
		page_count: pages.length,
		model: documentToDict(model)
	});
}
function cmdSerializeToml(modelPath, outToml) {
	const raw = fs.readFileSync(modelPath, "utf-8");
	const model = documentFromDict(JSON.parse(raw));
	fs.mkdirSync(path.dirname(path.resolve(outToml)) || ".", { recursive: true });
	saveModel(model, outToml);
	emit({
		ok: true,
		path: path.resolve(outToml)
	});
}
function cmdLoadToml(inToml, outJson) {
	const dict = documentToDict(loadModel(inToml));
	if (outJson && outJson !== "-") {
		fs.mkdirSync(path.dirname(path.resolve(outJson)) || ".", { recursive: true });
		fs.writeFileSync(outJson, JSON.stringify(dict), "utf-8");
	}
	emit({
		ok: true,
		model: dict
	});
}
function cmdListFonts(outJson, ttfDir) {
	const root = findProjectRoot();
	const dir = ttfDir || path.join(root, "ttf_library");
	const fonts = listFontsIn(dir);
	if (outJson && outJson !== "-") fs.writeFileSync(outJson, JSON.stringify({
		ok: true,
		fonts
	}), "utf-8");
	emit({
		ok: true,
		fonts,
		dir
	});
}
function cmdProbe() {
	const root = findProjectRoot();
	const dir = path.join(root, "ttf_library");
	emit({
		ok: true,
		node: process.version,
		hasCanvas: true,
		project_root: root,
		ttf_library: dir,
		fonts: listFontsIn(dir)
	});
}
function main() {
	const [, , sub, ...rest] = process.argv;
	try {
		switch (sub) {
			case "render":
				if (rest.length < 2) {
					emit({
						ok: false,
						error: "usage: render <model.json> <outdir> [seed]"
					});
					return;
				}
				cmdRender(rest[0], rest[1], rest[2]);
				return;
			case "serialize-toml":
				if (rest.length < 2) {
					emit({
						ok: false,
						error: "usage: serialize-toml <model.json> <out.toml>"
					});
					return;
				}
				cmdSerializeToml(rest[0], rest[1]);
				return;
			case "load-toml":
				if (rest.length < 1) {
					emit({
						ok: false,
						error: "usage: load-toml <in.toml> [out.json]"
					});
					return;
				}
				cmdLoadToml(rest[0], rest[1]);
				return;
			case "list-fonts":
				cmdListFonts(rest[0] ?? "-", rest[1]);
				return;
			case "probe":
				cmdProbe();
				return;
			default: emit({
				ok: false,
				error: `unknown subcommand: ${sub ?? "(none)"}`
			});
		}
	} catch (e) {
		emit({
			ok: false,
			error: e instanceof Error ? e.message : String(e)
		});
	}
}
main();
//#endregion
export {};
