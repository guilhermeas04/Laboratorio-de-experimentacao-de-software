"""Gravacao de respostas brutas e saidas intermediarias do LAB3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def repository_slug(full_name: str) -> str:
    return full_name.replace("/", "__").replace("\\", "__")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
