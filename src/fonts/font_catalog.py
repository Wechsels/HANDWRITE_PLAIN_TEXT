import fnmatch

from config.paths import TTF_LIBRARY_DIR


def list_fonts() -> list[tuple[str, str]]:
    """Return [(display_name, absolute_path), ...] for every .ttf in ttf_library."""
    result = []
    if not TTF_LIBRARY_DIR.exists():
        return result
    for file in sorted(TTF_LIBRARY_DIR.iterdir()):
        if fnmatch.fnmatch(file.name, "*.ttf"):
            result.append((file.stem, str(file)))
    return result


def default_font_path() -> str:
    fonts = list_fonts()
    if not fonts:
        raise FileNotFoundError(f"No .ttf font found in {TTF_LIBRARY_DIR}")
    return fonts[0][1]
