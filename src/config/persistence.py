from __future__ import annotations

import tomllib
import toml

from config.settings import DocumentModel


def save_model(model: DocumentModel, path: str) -> None:
    data = model.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        toml.dump(data, f)


def load_model(path: str) -> DocumentModel:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return DocumentModel.from_dict(data)
