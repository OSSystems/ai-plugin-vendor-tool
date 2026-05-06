from __future__ import annotations

import json
from pathlib import Path

from ai_plugin_vendor_tool import lock
from ai_plugin_vendor_tool.lock import LockData, LockEntry


def test_read_lock_missing_returns_empty(tmp_path: Path) -> None:
    assert lock.read_lock(tmp_path / "nonexistent.lock") == {}


def test_write_then_read_lock_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "test.lock"
    data: LockData = {
        "alice-skills": LockEntry(
            repo="alice/skills",
            ref="main",
            commit="abc123",
            skills=["one", "two"],
        ),
    }
    lock.write_lock(path, data)
    assert lock.read_lock(path) == data


def test_write_lock_sorts_keys_and_indents(tmp_path: Path) -> None:
    # Use two well-formed entries so the test reflects the real lock shape;
    # ordering is checked via JSON output, not the entry contents.
    path = tmp_path / "test.lock"
    data: LockData = {
        "zebra": LockEntry(repo="z/z", ref="main", commit="z", skills=[]),
        "alpha": LockEntry(repo="a/a", ref="main", commit="a", skills=[]),
    }
    lock.write_lock(path, data)
    text = path.read_text()
    assert text.endswith("\n")
    assert text.index('"alpha"') < text.index('"zebra"')
    # Indented (multiline) form, not collapsed.
    assert "\n" in text.strip()
    # Sanity-check the JSON is well-formed.
    assert json.loads(text) == data
