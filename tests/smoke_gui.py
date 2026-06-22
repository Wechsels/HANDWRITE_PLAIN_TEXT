"""端到端冒烟：构造编辑器、施加选区覆盖、渲染、检查落盘、配置保存/加载。"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.editor_window import EditorWindow
from app.state import Controller
from config.paths import OUTPUTS_DIR
from config.settings import ADJUSTABLE_KEYS


def wait_for_signal(signal, timeout_ms=15000):
    loop = QEventLoop()
    signal.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    QCoreApplication.processEvents()


def main():
    from config.paths import OUTPUTS_DIR as OUT
    app = QApplication.instance() or QApplication(sys.argv)
    controller = Controller()
    win = EditorWindow(controller)
    win.show()
    QCoreApplication.processEvents()

    # set text & selection
    win.text_edit.setPlainText("使用 PySide6 编写的手写字生成器，旨在完成一些手写作业任务。")
    QCoreApplication.processEvents()
    from PySide6.QtGui import QTextCursor
    cur = win.text_edit.textCursor()
    cur.setPosition(2)
    cur.setPosition(8, QTextCursor.KeepAnchor)
    win.text_edit.setTextCursor(cur)
    QCoreApplication.processEvents()

    # tweak override fields
    win.ov_font_size.setValue(45)
    win.ov_perturb_x.setValue(3.5)
    win.ov_underline.setChecked(True)
    win._on_apply_override()
    QCoreApplication.processEvents()

    assert win.controller.model.ranges_for_marking() == [(2, 8)], \
        f"覆盖区间未生效: {win.controller.model.ranges_for_marking()}"

    # render synchronously (call render_pages directly, no worker thread in this smoke)
    win.gather_into_model()
    from render.renderer import render_pages
    imgs = render_pages(win.controller.model, seed=42, save=True)
    assert len(imgs) >= 1
    files = sorted([f for f in os.listdir(OUT) if f.endswith(".png")])
    print("渲染页:", len(imgs), "  落盘:", files)
    assert files, "未落盘任何 PNG"

    # save & reload
    cfg = Path(win.controller.model.global_params.paper_w and ".tmp_cfg.toml" or ".tmp_cfg.toml")
    cfg_path = Path(__file__).parent / ".tmp_cfg.toml"
    try:
        win.controller.save_to(str(cfg_path))
        win.controller.load_from(str(cfg_path))
        assert win.controller.model.ranges_for_marking() == [(2, 8)], "保存/加载后覆盖丢失"
        assert "PySide6" in win.text_edit.toPlainText()
        print("保存/加载往返通过")
    finally:
        if cfg_path.exists():
            cfg_path.unlink()

    win.close()
    app.processEvents()
    print("冒烟测试通过")


if __name__ == "__main__":
    main()
