"""Stateful session: holds the DocumentModel, undo/redo, output dir, seed.

Session files are JSON (``*.hwsess.json``) — distinct from the portable TOML
project file. Saves use atomic exclusive file locking (``_locked_save_json``),
per guides/session-locking.md. One-shot CLI mutations auto-save unless
``--dry-run``; the REPL never auto-saves (per guides/auto-save-dry-run.md).
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model import document_from_dict, document_to_dict

SESSION_SUFFIX = ".hwsess.json"
MAX_HISTORY = 50

try:
    import fcntl  # type: ignore
except ImportError:
    fcntl = None  # type: ignore  # Windows / unsupported FS — proceed unlocked


def _locked_save_json(path: str, data: Dict[str, Any], **dump_kwargs) -> None:
    """Atomically write JSON with exclusive file locking (truncates inside lock)."""
    try:
        f = open(path, "r+")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        f = open(path, "w")
    with f:
        _locked = False
        if fcntl is not None:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                _locked = True
            except OSError:
                pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.flush()
        finally:
            if _locked:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass


def _locked_load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        if fcntl is not None:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            except OSError:
                pass
        return json.load(f)


class Session:
    """In-memory + file-backed session wrapping a DocumentModel."""

    def __init__(self) -> None:
        self.model: Dict[str, Any] = {"text": "", "global_params": {}, "overrides": []}
        self.project_path: Optional[str] = None  # portable .toml path
        self.session_path: Optional[str] = None  # .hwsess.json path
        self.output_dir: str = "outputs"
        self.seed: Optional[int] = None
        self.last_outputs: List[str] = []
        self._undo: List[Dict[str, Any]] = []
        self._redo: List[Dict[str, Any]] = []
        self._modified: bool = False

    # ── project / model state ──────────────────────────────────────────
    def has_project(self) -> bool:
        return bool(self.model.get("global_params"))

    def set_model(self, model: Dict[str, Any], project_path: Optional[str] = None) -> None:
        self.model = document_from_dict(model)
        if project_path:
            self.project_path = project_path
        self._modified = True
        self._undo.clear()
        self._redo.clear()

    def snapshot(self) -> None:
        """Push current model onto undo stack before a mutation."""
        self._undo.append(copy.deepcopy(self.model))
        if len(self._undo) > MAX_HISTORY:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(copy.deepcopy(self.model))
        self.model = self._undo.pop()
        self._modified = True
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(copy.deepcopy(self.model))
        self.model = self._redo.pop()
        self._modified = True
        return True

    def history(self) -> Dict[str, Any]:
        return {"undo_depth": len(self._undo), "redo_depth": len(self._redo),
                "modified": self._modified}

    # ── persistence ────────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": document_to_dict(self.model),
            "project_path": self.project_path,
            "output_dir": self.output_dir,
            "seed": self.seed,
            "last_outputs": self.last_outputs,
            "undo_depth": len(self._undo),
            "redo_depth": len(self._redo),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Session":
        s = cls()
        s.model = document_from_dict(d.get("model") or {})
        s.project_path = d.get("project_path")
        s.output_dir = d.get("output_dir", "outputs")
        s.seed = d.get("seed")
        s.last_outputs = d.get("last_outputs", [])
        return s

    def save_session(self, path: Optional[str] = None) -> str:
        path = path or self.session_path
        if not path:
            raise ValueError("no session path set; pass path= or set session_path")
        _locked_save_json(path, self.to_dict(), ensure_ascii=False, indent=2)
        self.session_path = path
        self._modified = False
        return path

    @classmethod
    def load_session(cls, path: str) -> "Session":
        s = cls.from_dict(_locked_load_json(path))
        s.session_path = path
        s._modified = False
        return s

    def status(self) -> Dict[str, Any]:
        return {
            "has_project": self.has_project(),
            "project_path": self.project_path,
            "session_path": self.session_path,
            "output_dir": self.output_dir,
            "seed": self.seed,
            "text_length": len(self.model.get("text", "")),
            "overrides": len(self.model.get("overrides", [])),
            "modified": self._modified,
            **self.history(),
        }

    def mark_modified(self) -> None:
        self._modified = True
