"""Plugin metadata and source-config loading."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PLUGIN_MANIFEST = Path(".claude-plugin/plugin.json")
VENDOR_TOML = Path("vendor/vendored-skills.toml")


@dataclass
class PluginMeta:
    name: str
    author: str
    license: str


@dataclass
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
    data = json.loads((root / PLUGIN_MANIFEST).read_text())
    author = data.get("author") or {}
    return PluginMeta(
        name=data["name"],
        author=author.get("name", "") if isinstance(author, dict) else str(author),
        license=data.get("license", "Apache-2.0"),
    )


def load_sources(root: Path) -> list[Source]:
    """Read vendor/vendored-skills.toml and return its [[source]] entries.

    Returns an empty list if the file does not exist.
    """
    path = root / VENDOR_TOML
    if not path.is_file():
        return []
    with path.open("rb") as f:
        data = tomllib.load(f)
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
