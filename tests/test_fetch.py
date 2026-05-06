from __future__ import annotations

from pathlib import Path

import pytest

from ai_plugin_vendor_tool import fetch
from ai_plugin_vendor_tool.fetch import GhError


def test_resolve_commit_calls_gh(fake_gh) -> None:
    fake_gh.set_commit("alice/skills", "main", "abc123def4567890")
    assert fetch.resolve_commit("alice/skills", "main") == "abc123def4567890"


def test_resolve_commit_strips_whitespace(fake_gh) -> None:
    fake_gh.set_commit("alice/skills", "main", "abc123\n")
    assert fetch.resolve_commit("alice/skills", "main") == "abc123"


def test_resolve_commit_raises_gh_error_when_gh_fails(fake_gh) -> None:
    # No commit set up for this ref → fake gh exits non-zero.
    with pytest.raises(GhError, match="gh api"):
        fetch.resolve_commit("alice/skills", "missing-ref")


def test_fetch_subtree_extracts_subpath(fake_gh, tmp_path: Path) -> None:
    fake_gh.set_tarball(
        "alice/skills",
        "abc123",
        root_prefix="alice-skills-abc123",
        layout={
            "README.md": "top-level\n",
            "skills/foo/SKILL.md": "# foo\n",
            "skills/foo/notes.md": "notes\n",
            "skills/bar/SKILL.md": "# bar\n",
            "other/ignored.md": "ignored\n",
        },
    )

    dest = tmp_path / "pristine"
    fetch.fetch_subtree("alice/skills", "abc123", "skills", dest)

    assert (dest / "foo" / "SKILL.md").read_text() == "# foo\n"
    assert (dest / "foo" / "notes.md").read_text() == "notes\n"
    assert (dest / "bar" / "SKILL.md").read_text() == "# bar\n"
    # README.md and other/ are outside the subpath and must not appear.
    assert not (dest / "README.md").exists()
    assert not (dest / "other").exists()


def test_fetch_subtree_empty_subpath_extracts_full_root(fake_gh, tmp_path: Path) -> None:
    fake_gh.set_tarball(
        "alice/skills",
        "abc123",
        root_prefix="alice-skills-abc123",
        layout={
            "README.md": "hi\n",
            "skills/foo/SKILL.md": "# foo\n",
        },
    )

    dest = tmp_path / "pristine"
    fetch.fetch_subtree("alice/skills", "abc123", "", dest)

    assert (dest / "README.md").read_text() == "hi\n"
    assert (dest / "skills" / "foo" / "SKILL.md").read_text() == "# foo\n"


def test_fetch_subtree_propagates_gh_failure(monkeypatch, tmp_path: Path) -> None:
    """If `gh` is missing, fetch_subtree must surface the error, not corrupt dest."""
    monkeypatch.setenv("PATH", "/no-such-dir")
    with pytest.raises((FileNotFoundError, OSError)):
        fetch.fetch_subtree("alice/skills", "abc123", "skills", tmp_path / "pristine")
