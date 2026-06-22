from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


class _ZoomView(QGraphicsView):
    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(self.renderHints() | self.renderHints())
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._zoom = 1.0

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier or True:
            factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
            new_zoom = self._zoom * factor
            if 0.05 <= new_zoom <= 20.0:
                self.scale(factor, factor)
                self._zoom = new_zoom

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom = 1.0

    def zoom_in(self) -> None:
        self.wheelEvent(_FakeWheel(120))

    def zoom_out(self) -> None:
        self.wheelEvent(_FakeWheel(-120))


class _FakeWheel:
    def __init__(self, dy):
        self._dy = dy

    def angleDelta(self):
        from PySide6.QtCore import QPoint
        return QPoint(0, self._dy)

    def modifiers(self):
        return 0


class PreviewWindow(QDialog):
    def __init__(self, image_paths: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HandWrite Plain Text - Preview")
        self.resize(900, 1100)
        self._paths = image_paths
        self._page_index = 0
        self._pixmap_cache: dict[int, QPixmap] = {}

        layout = QVBoxLayout(self)
        self.scene = QGraphicsScene()
        self.view = _ZoomView(self.scene, self)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        layout.addWidget(self.view, 1)

        ctrl = QHBoxLayout()
        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_next = QPushButton("下一页 ▶")
        self.spin_page = QSpinBox(); self.spin_page.setRange(0, max(0, len(image_paths) - 1))
        self.lbl_total = QLabel(f"共 {len(image_paths)} 页")
        self.btn_zoom_in = QPushButton("放大")
        self.btn_zoom_out = QPushButton("缩小")
        self.btn_zoom_reset = QPushButton("还原 100%")
        self.btn_open_folder = QPushButton("打开输出文件夹")
        self.btn_close = QPushButton("关闭")
        for w in (self.btn_prev, self.spin_page, self.lbl_total, self.btn_next,
                  self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_reset,
                  self.btn_open_folder, self.btn_close):
            ctrl.addWidget(w)
        ctrl.addStretch(1)
        layout.addLayout(ctrl)

        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)
        self.spin_page.valueChanged.connect(self._on_page_changed)
        self.btn_zoom_in.clicked.connect(self.view.zoom_in)
        self.btn_zoom_out.clicked.connect(self.view.zoom_out)
        self.btn_zoom_reset.clicked.connect(self.view.reset_zoom)
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        self.btn_close.clicked.connect(self.close)

        if image_paths:
            self._load_page(0)

    def _on_prev(self) -> None:
        if self._page_index > 0:
            self.spin_page.setValue(self._page_index - 1)

    def _on_next(self) -> None:
        if self._page_index < len(self._paths) - 1:
            self.spin_page.setValue(self._page_index + 1)

    def _on_page_changed(self, idx: int) -> None:
        self._load_page(idx)

    def _load_page(self, idx: int) -> None:
        if not self._paths:
            return
        idx = max(0, min(idx, len(self._paths) - 1))
        self._page_index = idx
        pix = self._pixmap_cache.get(idx)
        if pix is None:
            img = QImage(self._paths[idx])
            if img.isNull():
                return
            pix = QPixmap.fromImage(img)
            self._pixmap_cache[idx] = pix
        self.pixmap_item.setPixmap(pix)
        self.scene.setSceneRect(pix.rect())
        if self.spin_page.value() != idx:
            self.spin_page.blockSignals(True)
            self.spin_page.setValue(idx)
            self.spin_page.blockSignals(False)
        self.btn_prev.setEnabled(idx > 0)
        self.btn_next.setEnabled(idx < len(self._paths) - 1)

    def _on_open_folder(self) -> None:
        from config.paths import OUTPUTS_DIR
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUTS_DIR)))

    def clear_cache(self) -> None:
        self._pixmap_cache.clear()
