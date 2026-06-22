from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from config.persistence import load_model, save_model
from config.settings import ADJUSTABLE_KEYS, DocumentModel
from utils.logger import get_logger

logger = get_logger("controller")


class Controller(QObject):
    renderCompleted = Signal(list)
    renderFailed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.model = DocumentModel()
        self.editor = None
        self._worker = None

    def set_editor(self, editor) -> None:
        self.editor = editor

    def start_render(self, parent=None) -> None:
        if self.editor is None:
            return
        self.editor.gather_into_model()
        from app.render_worker import RenderWorker
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        self._worker = RenderWorker(self.model, parent=parent)
        self._worker.finished_ok.connect(self._on_rendered)
        self._worker.failed.connect(self._on_render_failed)
        self._worker.start()

    def _on_rendered(self, paths: list[str]) -> None:
        self.renderCompleted.emit(paths)

    def _on_render_failed(self, msg: str) -> None:
        logger.error("render failed: %s", msg)
        self.renderFailed.emit(msg)

    def apply_range_override(self, start: int, end: int, params: dict) -> None:
        cleaned = {k: v for k, v in params.items() if k in ADJUSTABLE_KEYS and v is not None}
        self.model.set_range(start, end, cleaned)
        if self.editor is not None:
            self.editor.apply_markings()

    def clear_range_override(self, start: int, end: int) -> None:
        self.model.clear_range(start, end)
        if self.editor is not None:
            self.editor.apply_markings()

    def save_to(self, path: str) -> None:
        if self.editor is not None:
            self.editor.gather_into_model()
        save_model(self.model, path)

    def load_from(self, path: str) -> None:
        self.model = load_model(path)
        if self.editor is not None:
            self.editor.populate_from_model()
