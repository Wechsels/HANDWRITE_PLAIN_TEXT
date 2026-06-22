import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication

from app.editor_window import EditorWindow
from app.state import Controller
from utils.logger import get_logger


def main() -> int:
    logger = get_logger("main")
    app = QApplication(sys.argv)
    controller = Controller()
    window = EditorWindow(controller)
    window.show()
    logger.info("editor window shown")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
