from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from config.settings import DocumentModel
from render.renderer import render_pages
from utils.logger import get_logger

logger = get_logger("render-worker")


class RenderWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, model: DocumentModel, parent=None) -> None:
        super().__init__(parent)
        self.model = model
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            from config.paths import OUTPUTS_DIR
            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
            images = render_pages(self.model, seed=None, save=True)
            if self._cancelled:
                return
            paths = []
            for i in range(len(images)):
                p = OUTPUTS_DIR / f"{i}.png"
                if p.exists():
                    paths.append(str(p))
            self.finished_ok.emit(paths)
        except Exception:
            logger.error("render error: %s", traceback.format_exc())
            self.failed.emit(traceback.format_exc())
