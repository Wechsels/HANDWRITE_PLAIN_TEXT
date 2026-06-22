from PIL import ImageFont

_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def get_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (font_path, size)
    font = _FONT_CACHE.get(key)
    if font is None:
        font = ImageFont.truetype(font_path, size)
        _FONT_CACHE[key] = font
    return font


def clear_cache() -> None:
    _FONT_CACHE.clear()
