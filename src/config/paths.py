from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
TTF_LIBRARY_DIR = PROJECT_ROOT / "ttf_library"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = PROJECT_ROOT / "logs"

for _dir in (OUTPUTS_DIR, LOGS_DIR, TTF_LIBRARY_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
