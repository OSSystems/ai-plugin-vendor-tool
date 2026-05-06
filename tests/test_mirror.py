from __future__ import annotations

from pathlib import Path
from typing import Any

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
