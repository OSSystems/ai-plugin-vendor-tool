"""Mirror a pristine vendored copy into a plugin's skills/ tree."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

from ai_plugin_vendor_tool.config import Source


def mirror_source(
    src: Source,
    pristine: Path,
    skills_dir: Path,
    reserved_names: set[str],
) -> list[str]:
    """Copy a pristine vendored tree into `skills_dir`.

    Two layouts are supported:

    - Default: each top-level entry of `pristine` is mirrored into `skills_dir`.
      Directories with a SKILL.md become skill entries (and land in the returned
      list); directories without one are copied as shared resources; loose files
      are copied as-is.
    - Single-skill (`src.skill_name` set): the entire `pristine` subtree is one
      skill, mirrored to `skills_dir/<skill_name>/`. Requires a SKILL.md at the
      root of `pristine`.

    Entries matching `src.exclude_globs` (relative to `pristine`) are skipped, as
    are entries whose name is in `reserved_names`. After copying, `src.substitutions`
    are applied to every UTF-8 file written. Returns the sorted list of skill names.
    """
    excluded: set[Path] = {p for pat in src.exclude_globs for p in pristine.glob(pat)}

    def ignore(dirname: str, names: list[str]) -> list[str]:
        d = Path(dirname)
        return [n for n in names if (d / n) in excluded]

    if src.skill_name:
        skills, copied = _mirror_single(src, pristine, skills_dir, reserved_names, ignore)
    else:
        skills, copied = _mirror_entries(pristine, skills_dir, excluded, reserved_names, ignore)

    if src.substitutions:
        _apply_substitutions(copied, src.substitutions)
    if src.executable:
        _apply_executable(copied, src.executable)

    return sorted(skills)


def _mirror_single(
    src: Source,
    pristine: Path,
    skills_dir: Path,
    reserved_names: set[str],
    ignore: Callable[[str, list[str]], list[str]],
) -> tuple[list[str], list[Path]]:
    if not (pristine / "SKILL.md").is_file():
        raise ValueError(
            f"source {src.name!r}: skill_name={src.skill_name!r} is set but there is no "
            f"SKILL.md at the root of subpath {src.subpath!r}"
        )
    if src.skill_name in reserved_names:
        print(f"  skipping {src.skill_name}: reserved name", file=sys.stderr)
        return [], []
    target = skills_dir / src.skill_name
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(pristine, target, ignore=ignore)
    return [src.skill_name], [target]


def _mirror_entries(
    pristine: Path,
    skills_dir: Path,
    excluded: set[Path],
    reserved_names: set[str],
    ignore: Callable[[str, list[str]], list[str]],
) -> tuple[list[str], list[Path]]:
    skills: list[str] = []
    copied: list[Path] = []
    for entry in sorted(pristine.iterdir()):
        if entry in excluded:
            continue
        if entry.name in reserved_names:
            print(f"  skipping {entry.name}: reserved name", file=sys.stderr)
            continue
        target = skills_dir / entry.name
        if entry.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(entry, target, ignore=ignore)
            copied.append(target)
            if (target / "SKILL.md").is_file():
                skills.append(entry.name)
            else:
                print(f"  copied shared dir {entry.name} (no SKILL.md)", file=sys.stderr)
        elif entry.is_file():
            shutil.copy2(entry, target)
            copied.append(target)
            print(f"  copied shared file {entry.name}", file=sys.stderr)
    return skills, copied


def _apply_executable(roots: Iterable[Path], patterns: list[str]) -> None:
    for root in roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            for p in sorted(root.glob(pat)):
                if p.is_file():
                    p.chmod(p.stat().st_mode | 0o111)


def _apply_substitutions(roots: Iterable[Path], substitutions: dict[str, str]) -> None:
    for root in roots:
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # binary or non-UTF-8; leave untouched
            new = text
            for old, repl in substitutions.items():
                new = new.replace(old, repl)
            if new != text:
                f.write_text(new, encoding="utf-8")
