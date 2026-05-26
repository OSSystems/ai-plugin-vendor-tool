from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ai_plugin_vendor_tool import mirror
from ai_plugin_vendor_tool.config import Source


def _src(**kwargs: Any) -> Source:
    """Build a Source with sensible test defaults; kwargs override fields."""
    defaults: dict[str, Any] = {"name": "demo", "repo": "demo/skills"}
    return Source(**{**defaults, **kwargs})


def _make_skill(root: Path, name: str, *extra_files: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"# {name}\n")
    for f in extra_files:
        (skill_dir / f).parent.mkdir(parents=True, exist_ok=True)
        (skill_dir / f).write_text("hi\n")


def test_mirror_copies_skills_returns_sorted_names(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    _make_skill(pristine, "zephyr-gpio")
    _make_skill(pristine, "zephyr-i2c")
    _make_skill(pristine, "alpha-skill")

    result = mirror.mirror_source(_src(), pristine, skills_dir, reserved_names=set())

    assert result == ["alpha-skill", "zephyr-gpio", "zephyr-i2c"]
    assert (skills_dir / "zephyr-gpio" / "SKILL.md").is_file()
    assert (skills_dir / "alpha-skill" / "SKILL.md").is_file()


def test_mirror_skips_reserved_names(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    _make_skill(pristine, "demo-plugin")  # plugin's own name
    _make_skill(pristine, "real-skill")

    result = mirror.mirror_source(_src(), pristine, skills_dir, reserved_names={"demo-plugin"})

    assert result == ["real-skill"]
    assert not (skills_dir / "demo-plugin").exists()
    assert (skills_dir / "real-skill").is_dir()


def test_mirror_treats_dirs_without_skill_md_as_shared_resource(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Has SKILL.md => skill
    _make_skill(pristine, "real-skill")
    # No SKILL.md => shared dir; copied but not in returned skill list
    shared = pristine / "shared-resources"
    shared.mkdir()
    (shared / "common.md").write_text("hi\n")

    result = mirror.mirror_source(_src(), pristine, skills_dir, reserved_names=set())

    assert result == ["real-skill"]
    assert (skills_dir / "shared-resources" / "common.md").is_file()


def test_mirror_copies_loose_top_level_files(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    _make_skill(pristine, "real-skill")
    (pristine / "README.md").write_text("upstream readme\n")

    result = mirror.mirror_source(_src(), pristine, skills_dir, reserved_names=set())

    assert result == ["real-skill"]
    assert (skills_dir / "README.md").read_text() == "upstream readme\n"


def test_mirror_honors_exclude_globs(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    _make_skill(pristine, "keep-skill", "extras/big.bin")
    _make_skill(pristine, "drop-skill")

    src = _src(exclude_globs=["drop-skill", "*/extras"])
    result = mirror.mirror_source(src, pristine, skills_dir, reserved_names=set())

    assert result == ["keep-skill"]
    assert not (skills_dir / "drop-skill").exists()
    assert (skills_dir / "keep-skill" / "SKILL.md").is_file()
    assert not (skills_dir / "keep-skill" / "extras").exists()


def test_mirror_replaces_stale_target_dir(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    _make_skill(pristine, "skill-a")
    # Pre-existing stale file inside the target.
    (skills_dir / "skill-a").mkdir()
    (skills_dir / "skill-a" / "OLD.txt").write_text("stale\n")

    mirror.mirror_source(_src(), pristine, skills_dir, reserved_names=set())

    assert (skills_dir / "skill-a" / "SKILL.md").is_file()
    assert not (skills_dir / "skill-a" / "OLD.txt").exists()


def test_mirror_single_skill_mode_renames_subtree(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Upstream keeps SKILL.md at the subpath root (not in a named dir).
    pristine.mkdir()
    (pristine / "SKILL.md").write_text("# upstream\n")
    (pristine / "scripts").mkdir()
    (pristine / "scripts" / "run.sh").write_text("echo hi\n")

    src = _src(skill_name="remote-ssh-dev")
    result = mirror.mirror_source(src, pristine, skills_dir, reserved_names=set())

    assert result == ["remote-ssh-dev"]
    assert (skills_dir / "remote-ssh-dev" / "SKILL.md").is_file()
    assert (skills_dir / "remote-ssh-dev" / "scripts" / "run.sh").is_file()


def test_mirror_single_skill_mode_requires_skill_md(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    pristine.mkdir()
    (pristine / "scripts").mkdir()

    src = _src(skill_name="remote-ssh-dev")
    with pytest.raises(ValueError, match=r"no.*SKILL\.md"):
        mirror.mirror_source(src, pristine, skills_dir, reserved_names=set())


def test_mirror_single_skill_mode_skips_reserved_name(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    pristine.mkdir()
    (pristine / "SKILL.md").write_text("# x\n")

    src = _src(skill_name="demo-plugin")
    result = mirror.mirror_source(src, pristine, skills_dir, reserved_names={"demo-plugin"})

    assert result == []
    assert not (skills_dir / "demo-plugin").exists()


def test_mirror_applies_substitutions(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill = pristine / "remote"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("run __ROOT__/skill/scripts/run.sh\n")
    (skill / "scripts").mkdir()
    (skill / "scripts" / "run.sh").write_text("no placeholder here\n")

    src = _src(substitutions={"__ROOT__/skill": "${CLAUDE_PLUGIN_ROOT}/skills/remote"})
    result = mirror.mirror_source(src, pristine, skills_dir, reserved_names=set())

    assert result == ["remote"]
    assert (skills_dir / "remote" / "SKILL.md").read_text() == (
        "run ${CLAUDE_PLUGIN_ROOT}/skills/remote/scripts/run.sh\n"
    )
    # Files without the token are left untouched.
    assert (skills_dir / "remote" / "scripts" / "run.sh").read_text() == "no placeholder here\n"


def test_mirror_sets_executable_bit(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill = pristine / "remote"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# x\n")
    run = skill / "scripts" / "run.sh"
    run.write_text("echo hi\n")
    run.chmod(0o644)
    doc = skill / "README.md"
    doc.write_text("doc\n")
    doc.chmod(0o644)

    src = _src(executable=["scripts/*.sh"])
    mirror.mirror_source(src, pristine, skills_dir, reserved_names=set())

    out_run = skills_dir / "remote" / "scripts" / "run.sh"
    assert out_run.stat().st_mode & 0o111 == 0o111
    # Non-matching files keep their original (non-executable) mode.
    assert (skills_dir / "remote" / "README.md").stat().st_mode & 0o111 == 0


def test_mirror_substitutions_skip_binary_files(tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill = pristine / "s"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("__TOK__\n")
    (skill / "blob.bin").write_bytes(b"\xff\xfe\x00__TOK__\x00")

    src = _src(substitutions={"__TOK__": "X"})
    mirror.mirror_source(src, pristine, skills_dir, reserved_names=set())

    assert (skills_dir / "s" / "SKILL.md").read_text() == "X\n"
    # Binary file is not decodable as UTF-8, so it is left byte-for-byte.
    assert (skills_dir / "s" / "blob.bin").read_bytes() == b"\xff\xfe\x00__TOK__\x00"
