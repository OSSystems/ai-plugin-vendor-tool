from __future__ import annotations

from pathlib import Path

from ai_plugin_vendor_tool import notice
from ai_plugin_vendor_tool.config import PluginMeta, Source


def _meta() -> PluginMeta:
    return PluginMeta(name="demo-plugin", author="Demo Org", license="Apache-2.0")


def _sources() -> list[Source]:
    return [
        Source(
            name="alice-skills",
            repo="alice/skills",
            ref="main",
            license="Apache-2.0",
            attribution="Alice",
            attribution_url="https://github.com/alice/skills",
        ),
    ]


def _lock() -> dict:
    return {
        "alice-skills": {
            "repo": "alice/skills",
            "ref": "main",
            "commit": "abc123def456789",
            "skills": ["one", "two", "three"],
        }
    }


def test_render_notice_header_uses_plugin_meta():
    text = notice.render_notice(_meta(), _sources(), _lock())
    assert text.startswith("demo-plugin\nCopyright (c) Demo Org\n")
    assert "Licensed under the Apache-2.0 License" in text


def test_render_notice_lists_skills():
    text = notice.render_notice(_meta(), _sources(), _lock())
    assert "## alice-skills" in text
    assert "Source:       https://github.com/alice/skills" in text
    assert "License:      Apache-2.0" in text
    assert "Attribution:  Alice" in text
    assert "Ref:          main (commit abc123def456789)" in text
    assert "Skills (3): one, two, three" in text


def test_render_notice_attribution_url_falls_back_to_repo():
    src = Source(name="bob-skills", repo="bob/skills", attribution="Bob")
    text = notice.render_notice(_meta(), [src], {"bob-skills": {"commit": "x", "skills": []}})
    assert "Source:       https://github.com/bob/skills" in text


def test_render_notice_handles_unknown_lock_entry():
    src = Source(name="charlie", repo="charlie/skills", attribution="Charlie")
    text = notice.render_notice(_meta(), [src], {})
    assert "Ref:          main (commit (unknown))" in text
    assert "Skills (0): (none)" in text


def test_write_notice_creates_file(tmp_path: Path):
    out = tmp_path / "NOTICE"
    notice.write_notice(out, _meta(), _sources(), _lock())
    assert out.read_text() == notice.render_notice(_meta(), _sources(), _lock())
