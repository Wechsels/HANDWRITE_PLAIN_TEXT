from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QTextEdit, QToolBar, QVBoxLayout, QWidget,
)

from config.paths import TTF_LIBRARY_DIR
from config.settings import ADJUSTABLE_KEYS, GlobalParams
from fonts.font_catalog import list_fonts
from palette import ALIGNMENT_OPTIONS, BACKGROUND_COLOR_DICT, FONT_COLOR_DICT, RATE_DICT
from utils.logger import get_logger

logger = get_logger("editor")

MARK_COLOR = QColor(255, 192, 192)


def _safe_int(s: str, default: int) -> int:
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return default


def _safe_float(s: str, default: float) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


class EditorWindow(QMainWindow):
    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.controller.set_editor(self)

        self.setWindowTitle("HandWrite Plain Text - Editor")
        self.resize(1280, 820)

        self._build_toolbar()
        self._build_central()
        self._populate_defaults()
        self.apply_markings()

    def _build_toolbar(self) -> None:
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction("预览", self._on_preview)
        tb.addAction("导出", self._on_export)
        tb.addSeparator()
        tb.addAction("保存配置", self._on_save_config)
        tb.addAction("加载配置", self._on_load_config)
        self.status_label = QLabel("就绪")
        tb.addSeparator()
        tb.addWidget(self.status_label)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlaceholderText("在此输入要生成手写体的文本…")
        self.text_edit.selectionChanged.connect(self._on_selection_changed)
        self.text_edit.textChanged.connect(self._on_text_changed)
        left_layout.addWidget(self.text_edit, 1)

        right = QSplitter(Qt.Vertical)
        right.addWidget(self._build_global_panel())
        right.addWidget(self._build_override_panel())
        right.setSizes([600, 240])

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([700, 520])

    def _build_global_panel(self) -> QWidget:
        box = QGroupBox("全局参数")
        form = QFormLayout(box)

        self.spin_paper_w = QSpinBox(); self.spin_paper_w.setRange(50, 10000)
        self.spin_paper_h = QSpinBox(); self.spin_paper_h.setRange(50, 10000)
        self.combo_font = QComboBox()
        for name, path in list_fonts():
            self.combo_font.addItem(name, path)
        self.spin_font_size = QSpinBox(); self.spin_font_size.setRange(2, 200)
        self.spin_line_spacing = QSpinBox(); self.spin_line_spacing.setRange(2, 400)
        self.spin_word_spacing = QSpinBox(); self.spin_word_spacing.setRange(-100, 200)
        self.spin_margin_top = QSpinBox(); self.spin_margin_top.setRange(0, 1000)
        self.spin_margin_bottom = QSpinBox(); self.spin_margin_bottom.setRange(0, 1000)
        self.spin_margin_left = QSpinBox(); self.spin_margin_left.setRange(0, 1000)
        self.spin_margin_right = QSpinBox(); self.spin_margin_right.setRange(0, 1000)
        self.combo_char_color = QComboBox()
        for k, v in FONT_COLOR_DICT.items():
            self.combo_char_color.addItem(k, v)
        self.combo_bg_color = QComboBox()
        for k, v in BACKGROUND_COLOR_DICT.items():
            self.combo_bg_color.addItem(k, v)
        self.combo_rate = QComboBox()
        for k, v in RATE_DICT.items():
            self.combo_rate.addItem(k, v)
        self.spin_line_spacing_sigma = QDoubleSpinBox()
        self.spin_line_spacing_sigma.setRange(0, 50); self.spin_line_spacing_sigma.setDecimals(2); self.spin_line_spacing_sigma.setSingleStep(0.5)
        self.spin_font_size_sigma = QDoubleSpinBox()
        self.spin_font_size_sigma.setRange(0, 50); self.spin_font_size_sigma.setDecimals(2); self.spin_font_size_sigma.setSingleStep(0.5)
        self.spin_word_spacing_sigma = QDoubleSpinBox()
        self.spin_word_spacing_sigma.setRange(0, 50); self.spin_word_spacing_sigma.setDecimals(2); self.spin_word_spacing_sigma.setSingleStep(0.5)
        self.spin_perturb_x_sigma = QDoubleSpinBox()
        self.spin_perturb_x_sigma.setRange(0, 50); self.spin_perturb_x_sigma.setDecimals(2); self.spin_perturb_x_sigma.setSingleStep(0.5)
        self.spin_perturb_y_sigma = QDoubleSpinBox()
        self.spin_perturb_y_sigma.setRange(0, 50); self.spin_perturb_y_sigma.setDecimals(2); self.spin_perturb_y_sigma.setSingleStep(0.5)
        self.spin_perturb_theta_sigma = QDoubleSpinBox()
        self.spin_perturb_theta_sigma.setRange(0, 1); self.spin_perturb_theta_sigma.setDecimals(3); self.spin_perturb_theta_sigma.setSingleStep(0.01)
        self.combo_alignment = QComboBox()
        self.combo_alignment.addItems(ALIGNMENT_OPTIONS)
        self.check_underline = QCheckBox("全局下划线")

        form.addRow("纸张宽 (px)", self.spin_paper_w)
        form.addRow("纸张高 (px)", self.spin_paper_h)
        form.addRow("字体", self.combo_font)
        form.addRow("字体大小 (px)", self.spin_font_size)
        form.addRow("行距 (px)", self.spin_line_spacing)
        form.addRow("字距 (px)", self.spin_word_spacing)
        form.addRow("上边距 (px)", self.spin_margin_top)
        form.addRow("下边距 (px)", self.spin_margin_bottom)
        form.addRow("左边距 (px)", self.spin_margin_left)
        form.addRow("右边距 (px)", self.spin_margin_right)
        form.addRow("字体颜色", self.combo_char_color)
        form.addRow("背景颜色", self.combo_bg_color)
        form.addRow("渲染倍率", self.combo_rate)
        form.addRow("行距扰动 σ", self.spin_line_spacing_sigma)
        form.addRow("字号扰动 σ", self.spin_font_size_sigma)
        form.addRow("字距扰动 σ", self.spin_word_spacing_sigma)
        form.addRow("横向笔画扰动 σ", self.spin_perturb_x_sigma)
        form.addRow("纵向笔画扰动 σ", self.spin_perturb_y_sigma)
        form.addRow("旋转笔画扰动 σ", self.spin_perturb_theta_sigma)
        form.addRow("对齐", self.combo_alignment)
        form.addRow("", self.check_underline)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(box)
        return scroll

    def _build_override_panel(self) -> QWidget:
        box = QGroupBox("选区参数覆盖（先在文本中选中字符，再调整以下参数并点击「应用到选区」）")
        layout = QVBoxLayout(box)
        self.override_label = QLabel("当前未选中任何字符")
        layout.addWidget(self.override_label)

        form = QFormLayout()
        self.ov_font_size = QSpinBox(); self.ov_font_size.setRange(2, 200)
        self.ov_word_spacing = QSpinBox(); self.ov_word_spacing.setRange(-100, 200)
        self.ov_perturb_x = QDoubleSpinBox(); self.ov_perturb_x.setRange(0, 50); self.ov_perturb_x.setDecimals(2); self.ov_perturb_x.setSingleStep(0.5)
        self.ov_perturb_y = QDoubleSpinBox(); self.ov_perturb_y.setRange(0, 50); self.ov_perturb_y.setDecimals(2); self.ov_perturb_y.setSingleStep(0.5)
        self.ov_perturb_theta = QDoubleSpinBox(); self.ov_perturb_theta.setRange(0, 1); self.ov_perturb_theta.setDecimals(3); self.ov_perturb_theta.setSingleStep(0.01)
        self.ov_color = QComboBox()
        for k, v in FONT_COLOR_DICT.items():
            self.ov_color.addItem(k, v)
        self.ov_alignment = QComboBox(); self.ov_alignment.addItems(ALIGNMENT_OPTIONS)
        self.ov_underline = QCheckBox("选区下划线")

        form.addRow("字体大小", self.ov_font_size)
        form.addRow("字距", self.ov_word_spacing)
        form.addRow("横向笔画扰动 σ", self.ov_perturb_x)
        form.addRow("纵向笔画扰动 σ", self.ov_perturb_y)
        form.addRow("旋转笔画扰动 σ", self.ov_perturb_theta)
        form.addRow("字体颜色", self.ov_color)
        form.addRow("对齐", self.ov_alignment)
        form.addRow("", self.ov_underline)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_apply_ov = QPushButton("应用到选区")
        self.btn_clear_ov = QPushButton("清除选区覆盖")
        self.btn_apply_ov.clicked.connect(self._on_apply_override)
        self.btn_clear_ov.clicked.connect(self._on_clear_override)
        btn_row.addWidget(self.btn_apply_ov)
        btn_row.addWidget(self.btn_clear_ov)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)
        return box

    def _populate_defaults(self) -> None:
        gp = self.controller.model.global_params
        self.spin_paper_w.setValue(gp.paper_w)
        self.spin_paper_h.setValue(gp.paper_h)
        self._select_font_path(gp.font_path)
        self.spin_font_size.setValue(gp.font_size)
        self.spin_line_spacing.setValue(gp.line_spacing)
        self.spin_word_spacing.setValue(gp.word_spacing)
        self.spin_margin_top.setValue(gp.margin_top)
        self.spin_margin_bottom.setValue(gp.margin_bottom)
        self.spin_margin_left.setValue(gp.margin_left)
        self.spin_margin_right.setValue(gp.margin_right)
        self._select_color(self.combo_char_color, gp.fill)
        self._select_color(self.combo_bg_color, gp.background)
        self._select_rate(gp.rate)
        self.spin_line_spacing_sigma.setValue(gp.line_spacing_sigma)
        self.spin_font_size_sigma.setValue(gp.font_size_sigma)
        self.spin_word_spacing_sigma.setValue(gp.word_spacing_sigma)
        self.spin_perturb_x_sigma.setValue(gp.perturb_x_sigma)
        self.spin_perturb_y_sigma.setValue(gp.perturb_y_sigma)
        self.spin_perturb_theta_sigma.setValue(gp.perturb_theta_sigma)
        self.combo_alignment.setCurrentText(gp.alignment)
        self.check_underline.setChecked(gp.underline)

        if not self.text_edit.toPlainText():
            self.text_edit.setPlainText(
                "使用 PySide6 编写的手写字生成器，旨在完成一些手写作业任务。\n"
                "支持选区级参数覆盖：在文本中选中字段并调整覆盖参数。"
            )

    def populate_from_model(self) -> None:
        self._populate_defaults()
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(self.controller.model.text)
        self.text_edit.blockSignals(False)
        self.apply_markings()
        self._on_selection_changed()

    def _select_font_path(self, path: str) -> None:
        for i in range(self.combo_font.count()):
            if self.combo_font.itemData(i) == path:
                self.combo_font.setCurrentIndex(i)
                return
        if self.combo_font.count() > 0:
            self.combo_font.setCurrentIndex(0)

    def _select_color(self, combo: QComboBox, rgba) -> None:
        for i in range(combo.count()):
            if tuple(combo.itemData(i)) == tuple(rgba):
                combo.setCurrentIndex(i)
                return

    def _select_rate(self, rate: int) -> None:
        for k, v in RATE_DICT.items():
            if v == rate:
                self.combo_rate.setCurrentText(k)
                return

    def gather_into_model(self) -> None:
        gp = self.controller.model.global_params
        gp.paper_w = self.spin_paper_w.value()
        gp.paper_h = self.spin_paper_h.value()
        gp.font_path = self.combo_font.currentData() or gp.font_path
        gp.font_size = self.spin_font_size.value()
        gp.line_spacing = max(self.spin_line_spacing.value(), gp.font_size)
        gp.word_spacing = self.spin_word_spacing.value()
        gp.margin_top = self.spin_margin_top.value()
        gp.margin_bottom = self.spin_margin_bottom.value()
        gp.margin_left = self.spin_margin_left.value()
        gp.margin_right = self.spin_margin_right.value()
        gp.fill = tuple(self.combo_char_color.currentData() or (0, 0, 0, 255))
        gp.background = tuple(self.combo_bg_color.currentData() or (255, 255, 255, 255))
        gp.rate = self.combo_rate.currentData() or 4
        gp.line_spacing_sigma = self.spin_line_spacing_sigma.value()
        gp.font_size_sigma = self.spin_font_size_sigma.value()
        gp.word_spacing_sigma = self.spin_word_spacing_sigma.value()
        gp.perturb_x_sigma = self.spin_perturb_x_sigma.value()
        gp.perturb_y_sigma = self.spin_perturb_y_sigma.value()
        gp.perturb_theta_sigma = self.spin_perturb_theta_sigma.value()
        gp.alignment = self.combo_alignment.currentText()
        gp.underline = self.check_underline.isChecked()
        self.controller.model.text = self.text_edit.toPlainText()

    def _current_selection(self):
        c = self.text_edit.textCursor()
        a, b = c.selectionStart(), c.selectionEnd()
        if a == b:
            return None, None
        return min(a, b), max(a, b)

    def _on_selection_changed(self) -> None:
        a, b = self._current_selection()
        if a is None:
            self.override_label.setText("当前未选中任何字符")
            self._set_override_panel_enabled(False)
            return
        self.override_label.setText(f"当前选区: [{a}, {b})  长度 {b - a}")
        self._set_override_panel_enabled(True)
        eff = self.controller.model.effective_params(a)
        self.ov_font_size.setValue(int(eff["font_size"]))
        self.ov_word_spacing.setValue(int(eff["word_spacing"]))
        self.ov_perturb_x.setValue(float(eff["perturb_x_sigma"]))
        self.ov_perturb_y.setValue(float(eff["perturb_y_sigma"]))
        self.ov_perturb_theta.setValue(float(eff["perturb_theta_sigma"]))
        self._select_color(self.ov_color, eff["fill"])
        self.ov_alignment.setCurrentText(eff["alignment"])
        self.ov_underline.setChecked(bool(eff["underline"]))

    def _set_override_panel_enabled(self, enabled: bool) -> None:
        for w in (self.ov_font_size, self.ov_word_spacing, self.ov_perturb_x,
                  self.ov_perturb_y, self.ov_perturb_theta, self.ov_color,
                  self.ov_alignment, self.ov_underline,
                  self.btn_apply_ov, self.btn_clear_ov):
            w.setEnabled(enabled)

    def _on_apply_override(self) -> None:
        a, b = self._current_selection()
        if a is None:
            QMessageBox.information(self, "提示", "请先在文本中选中要覆盖的字符。")
            return
        params = {
            "font_size": self.ov_font_size.value(),
            "word_spacing": self.ov_word_spacing.value(),
            "perturb_x_sigma": self.ov_perturb_x.value(),
            "perturb_y_sigma": self.ov_perturb_y.value(),
            "perturb_theta_sigma": self.ov_perturb_theta.value(),
            "fill": tuple(self.ov_color.currentData() or (0, 0, 0, 255)),
            "alignment": self.ov_alignment.currentText(),
            "underline": self.ov_underline.isChecked(),
        }
        self.controller.apply_range_override(a, b, params)
        self.status_label.setText(f"已应用选区覆盖 [{a}, {b})")

    def _on_clear_override(self) -> None:
        a, b = self._current_selection()
        if a is None:
            return
        self.controller.clear_range_override(a, b)
        self.status_label.setText(f"已清除选区覆盖 [{a}, {b})")

    def _on_text_changed(self) -> None:
        self.controller.model.text = self.text_edit.toPlainText()
        n = len(self.controller.model.text)
        self.controller.model.overrides = [
            o for o in self.controller.model.overrides if o.start < n and o.end <= n
        ]
        for o in self.controller.model.overrides:
            o.start = max(0, o.start)
            o.end = min(o.end, n)
        self.apply_markings()

    def apply_markings(self) -> None:
        selections = []
        for start, end in self.controller.model.ranges_for_marking():
            if start >= end:
                continue
            cursor = self.text_edit.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setBackground(MARK_COLOR)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)
        self.text_edit.setExtraSelections(selections)

    def _on_preview(self) -> None:
        if not list_fonts():
            QMessageBox.warning(self, "字体缺失", f"请在 {TTF_LIBRARY_DIR} 目录放置 .ttf 字体。")
            return
        self.status_label.setText("渲染中…")
        self.controller.renderCompleted.connect(self._show_preview)
        self.controller.start_render(self)

    def _show_preview(self, paths) -> None:
        self.controller.renderCompleted.disconnect(self._show_preview)
        self.status_label.setText(f"渲染完成: {len(paths)} 页")
        from app.preview_window import PreviewWindow
        dlg = PreviewWindow(paths, self)
        dlg.exec()
        self.status_label.setText("就绪")

    def _on_export(self) -> None:
        self._on_preview()

    def _on_save_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存配置", "", "TOML Files (*.toml)")
        if not path:
            return
        self.controller.save_to(path)
        self.status_label.setText(f"配置已保存: {path}")

    def _on_load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "TOML Files (*.toml)")
        if not path:
            return
        try:
            self.controller.load_from(path)
            self.status_label.setText(f"配置已加载: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))
