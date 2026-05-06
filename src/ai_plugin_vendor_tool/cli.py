"""CLI entry point: `ai-plugin-vendor-tool sync` / `check`."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ai_plugin_vendor_tool import config, fetch, lock, mirror, notice
from ai_plugin_vendor_tool.config import PluginMeta, Source
from ai_plugin_vendor_tool.lock import LockData, LockEntry


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai-plugin-vendor-tool",
        description="Vendor Claude Code plugin skills from upstream GitHub repos.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--plugin-root",
        type=Path,
        default=None,
        help="Path to the plugin root. Defaults to walking up from CWD.",
    )
    common.add_argument(
        "--source",
        action="append",
        metavar="NAME",
        help="Restrict to the named source (repeatable).",
    )

    sync = sub.add_parser("sync", parents=[common], help="Fetch sources, mirror skills.")
    sync.add_argument(
        "--prune",
        action="store_true",
        help="After sync, remove skill dirs not listed in the new lock.",
    )

    sub.add_parser("check", parents=[common], help="Resolve refs and report drift.")

    return p


def _resolve_plugin_root(arg: Path | None) -> Path:
    start = arg if arg is not None else Path.cwd()
    return config.discover_plugin_root(start)


def _select_sources(all_sources: list[Source], wanted: list[str] | None) -> list[Source]:
    if not wanted:
        return list(all_sources)
    return [s for s in all_sources if s.name in wanted]


def _do_check(sources: list[Source], lock_data: LockData) -> int:
    drift: list[tuple[str, str | None, str]] = []
    for s in sources:
        sha = fetch.resolve_commit(s.repo, s.ref)
        entry = lock_data.get(s.name)
        old = entry["commit"] if entry is not None else None
        if sha != old:
            drift.append((s.name, old, sha))
    if drift:
        print("drift detected:")
        for name, old, new in drift:
            old_s = old[:12] if old else "(absent)"
            print(f"  {name}: {old_s} -> {new[:12]}")
        return 1
    print("in sync")
    return 0


def _do_sync(
    plugin_root: Path,
    meta: PluginMeta,
    all_sources: list[Source],
    selected: list[Source],
    lock_data: LockData,
    prune: bool,
) -> int:
    vendor_dir = plugin_root / "vendor"
    skills_dir = plugin_root / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    reserved = {meta.name}

    for s in selected:
        print(f"syncing {s.name} from {s.repo}@{s.ref}")
        sha = fetch.resolve_commit(s.repo, s.ref)
        pristine = vendor_dir / s.name
        shutil.rmtree(pristine, ignore_errors=True)
        fetch.fetch_subtree(s.repo, sha, s.subpath, pristine)
        skills = mirror.mirror_source(s, pristine, skills_dir, reserved_names=reserved)
        lock_data[s.name] = LockEntry(
            repo=s.repo,
            ref=s.ref,
            commit=sha,
            skills=skills,
        )
        print(f"  -> {sha[:12]} ({len(skills)} skills)")

    if prune:
        listed = {n for e in lock_data.values() for n in e["skills"]}
        for child in sorted(skills_dir.iterdir()):
            if child.name in reserved or child.name in listed:
                continue
            if not child.is_dir() or not (child / "SKILL.md").is_file():
                continue
            print(f"pruning orphan skill {child.name}")
            shutil.rmtree(child)

    lock.write_lock(plugin_root / config.VENDOR_LOCK, lock_data)
    notice.write_notice(plugin_root / "NOTICE", meta, all_sources, lock_data)
    print("done")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        plugin_root = _resolve_plugin_root(args.plugin_root)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    meta = config.load_plugin_meta(plugin_root)
    all_sources = config.load_sources(plugin_root)
    if not all_sources:
        print(
            f"error: no sources defined in {plugin_root / config.VENDOR_TOML}",
            file=sys.stderr,
        )
        return 2

    selected = _select_sources(all_sources, args.source)
    if args.source and not selected:
        print(f"error: no matching sources: {args.source}", file=sys.stderr)
        return 2

    lock_data = lock.read_lock(plugin_root / config.VENDOR_LOCK)

    if args.cmd == "check":
        return _do_check(selected, lock_data)
    if args.cmd == "sync":
        return _do_sync(plugin_root, meta, all_sources, selected, lock_data, args.prune)
    return 2  # unreachable; argparse enforces required subcommand


if __name__ == "__main__":
    raise SystemExit(main())
