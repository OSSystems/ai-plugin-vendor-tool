"""Plugin metadata and source-config loading."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PLUGIN_MANIFEST = Path(".claude-plugin/plugin.json")
VENDOR_TOML = Path("vendor/vendored-skills.toml")
VENDOR_LOCK = Path("vendor/vendored-skills.lock")


@dataclass(frozen=True, slots=True)
class PluginMeta:
    name: str
    author: str
    license: str


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    repo: str
    ref: str = "main"
    subpath: str = ""
    exclude_globs: list[str] = field(default_factory=list)
    license: str = "Apache-2.0"
    attribution: str = ""
    attribution_url: str = ""


def load_plugin_meta(root: Path) -> PluginMeta:
    """Read the plugin manifest at <root>/.claude-plugin/plugin.json."""
    raw: dict[str, Any] = json.loads((root / PLUGIN_MANIFEST).read_text())
    if "name" not in raw:
        raise KeyError(f"{PLUGIN_MANIFEST} is missing required field 'name'")
    author_field = raw.get("author")
    if isinstance(author_field, dict):
        author = author_field.get("name", "")
    elif author_field is None:
        author = ""
    else:
        author = str(author_field)
    return PluginMeta(
        name=raw["name"],
        author=author,
        license=raw.get("license", "Apache-2.0"),
    )


def load_sources(root: Path) -> list[Source]:
    """Read vendor/vendored-skills.toml and return its [[source]] entries.

    Returns an empty list if the file does not exist.
    """
    try:
        with (root / VENDOR_TOML).open("rb") as f:
            data: dict[str, Any] = tomllib.load(f)
    except FileNotFoundError:
        return []
    return [Source(**s) for s in data.get("source", [])]


def discover_plugin_root(start: Path) -> Path:
    """Walk up from `start` until a directory containing the plugin manifest is found.

    Raises FileNotFoundError if no ancestor (or `start` itself) has one.
    """
    start = start.resolve()
    candidates = [start, *start.parents] if start.is_dir() else list(start.parents)
    for candidate in candidates:
        if (candidate / PLUGIN_MANIFEST).is_file():
            return candidate
    raise FileNotFoundError(f"no .claude-plugin/plugin.json found from {start} upward")
