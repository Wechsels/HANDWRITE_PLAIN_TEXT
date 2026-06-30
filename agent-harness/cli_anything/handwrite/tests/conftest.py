"""Shared fixtures + path bootstrap for cli-anything-handwrite tests.

Inserts the `agent-harness/` directory on sys.path so `cli_anything` imports
resolve whether or not the package is pip-installed.
"""
import os
import sys
from pathlib import Path

# agent-harness/ = tests/ -> handwrite/ -> cli_anything/ -> agent-harness/
_AGENT_HARNESS = Path(__file__).resolve().parents[3]
if str(_AGENT_HARNESS) not in sys.path:
    sys.path.insert(0, str(_AGENT_HARNESS))

# Repo root (the HandWrite project) = agent-harness parent.
REPO_ROOT = _AGENT_HARNESS.parent

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    """A real (OS-native) temporary directory — never an MSYS /tmp path."""
    return str(tmp_path)


@pytest.fixture
def font_path():
    """First .ttf in ttf_library/, or skip if absent (real-software dependency)."""
    ttf_dir = REPO_ROOT / "ttf_library"
    if not ttf_dir.is_dir():
        pytest.skip("ttf_library/ not found — project checkout required")
    ttfs = sorted(p for p in ttf_dir.iterdir() if p.suffix.lower() == ".ttf")
    if not ttfs:
        pytest.skip("no .ttf in ttf_library/ — required by the real render backend")
    return str(ttfs[0])


@pytest.fixture
def project_root():
    """The HandWrite project root (node_modules + ttf_library live here)."""
    return REPO_ROOT


@pytest.fixture
def cli_env(project_root, monkeypatch):
    """Env for subprocess CLI runs: project root + PYTHONPATH."""
    monkeypatch.setenv("HANDWRITE_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("PYTHONPATH", str(_AGENT_HARNESS))
    return dict(os.environ)
