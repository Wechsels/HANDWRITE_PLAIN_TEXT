from PySide6.QtGui import QColor

FONT_COLOR_DICT = {
    "black": (0, 0, 0, 255),
    "white": (255, 255, 255, 255),
    "red": (255, 0, 0, 255),
    "blue": (0, 0, 255, 255),
}

BACKGROUND_COLOR_DICT = {
    "transparent": (0, 0, 0, 0),
    "white": (255, 255, 255, 255),
}

RATE_DICT = {
    "x1": 1,
    "x2": 2,
    "x4": 4,
    "x8": 8,
    "x16": 16,
    "x32": 32,
    "x64": 64,
}

ALIGNMENT_OPTIONS = ("left", "center")


def rgba_to_qcolor(rgba: tuple[int, int, int, int]) -> QColor:
    return QColor(*rgba)


def qcolor_to_rgba(color: QColor) -> tuple[int, int, int, int]:
    return (color.red(), color.green(), color.blue(), color.alpha())
