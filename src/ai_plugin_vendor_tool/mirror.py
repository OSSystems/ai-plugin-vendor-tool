"""Mirror a pristine vendored copy into a plugin's skills/ tree."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from ai_plugin_vendor_tool.config import Source


def mirror_source(
    src: Source,
    pristine: Path,
    skills_dir: Path,
    reserved_names: set[str],
) -> list[str]:
    """Copy each top-level entry from `pristine` into `skills_dir`.

    Returns the sorted list of skill names — i.e. directories that contained
    a SKILL.md. Directories without SKILL.md are still copied (treated as
    shared resources) but are not in the returned list. Loose files at the
    top level are copied as-is. Entries matching `src.exclude_globs` (relative
    to `pristine`) are skipped, as are entries whose name is in
    `reserved_names`.
    """
    excluded: set[Path] = {p for pat in src.exclude_globs for p in pristine.glob(pat)}

    def ignore(dirname: str, names: list[str]) -> list[str]:
        d = Path(dirname)
        return [n for n in names if (d / n) in excluded]

    skills: list[str] = []
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
            if (target / "SKILL.md").is_file():
                skills.append(entry.name)
            else:
                print(f"  copied shared dir {entry.name} (no SKILL.md)", file=sys.stderr)
        elif entry.is_file():
            shutil.copy2(entry, target)
            print(f"  copied shared file {entry.name}", file=sys.stderr)
    return sorted(skills)
