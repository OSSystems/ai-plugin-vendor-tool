from __future__ import annotations

from pathlib import Path

from ai_plugin_vendor_tool import lock


def test_read_lock_missing_returns_empty(tmp_path: Path):
    assert lock.read_lock(tmp_path / "nonexistent.lock") == {}


def test_write_then_read_lock_roundtrips(tmp_path: Path):
    path = tmp_path / "test.lock"
    data = {
        "alice-skills": {
            "repo": "alice/skills",
            "ref": "main",
            "commit": "abc123",
            "skills": ["one", "two"],
        }
    }
    lock.write_lock(path, data)
    assert lock.read_lock(path) == data


def test_write_lock_sorts_keys_and_indents(tmp_path: Path):
    path = tmp_path / "test.lock"
    data = {"zebra": 2, "alpha": 1}
    lock.write_lock(path, data)
    text = path.read_text()
    assert text.endswith("\n")
    assert text.index('"alpha"') < text.index('"zebra"')
    # Indented (multiline) form, not collapsed.
    assert "\n" in text.strip()
