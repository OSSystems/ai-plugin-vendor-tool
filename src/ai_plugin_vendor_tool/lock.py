"""JSON lockfile read/write."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast


class LockEntry(TypedDict):
    """One source's pinned state inside the lockfile.

    Public contract — keys land in `vendor/vendored-skills.lock` verbatim.
    Renames or removals require a major-version bump (see docs/roadmap.md).
    """

    repo: str
    ref: str
    commit: str
    skills: list[str]


LockData = dict[str, LockEntry]


def read_lock(path: Path) -> LockData:
    try:
        return cast(LockData, json.loads(path.read_text()))
    except FileNotFoundError:
        return {}


def write_lock(path: Path, data: LockData) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
