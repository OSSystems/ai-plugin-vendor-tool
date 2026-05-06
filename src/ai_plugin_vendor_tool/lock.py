"""JSON lockfile read/write."""

from __future__ import annotations

import json
from pathlib import Path


def read_lock(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def write_lock(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
