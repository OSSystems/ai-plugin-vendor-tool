# Decisions log

The rationale here is *why the tool has the shape it does*. Future sessions should not relitigate
these choices without a concrete reason.

## Origin

Extracted from `freedom-rtos-ai/plugins/freedom-rtos-dev/scripts/sync_vendored.py` — a ~230-line
stdlib-only script that vendored Zephyr-related skills from `ksachdeva/zephyr-rtos-ai` into a
Claude Code plugin's `skills/` tree. The customer wanted it lifted into a reusable tool that other
marketplace repos could consume.

## Off-the-shelf alternatives considered (and rejected)

| Tool                  | Why rejected                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------------- |
| `vendir` (carvel.dev) | Closest match; covers fetch + lock + subpath. Doesn't generate NOTICE or classify SKILL.md. Adds Go binary dep. |
| `git subtree`         | No multi-source lock, no NOTICE, awkward subpath semantics.                                                     |
| `git submodules`      | Pulls full repos, no subpath, no NOTICE.                                                                        |
| `degit`               | Snapshot clone only — no lockfile, no multi-source.                                                             |
| `niv`                 | Pins Nix inputs; no file extraction.                                                                            |

The user explicitly chose **self-contained** over wrapping any of these: keeps deps minimal, full
control over NOTICE format and skill classification, and the original script was already
stdlib-only with no real pain points.

## Locked decisions

1. **Self-contained, minimal deps.** Runtime: stdlib only (`tomllib`, `tarfile`, `subprocess` for
   `gh`, `json`, `pathlib`, `dataclasses`, `shutil`, `argparse`). Dev: `pytest`. Third-party Python
   packages are permitted in principle but require justification — the bar is "stdlib would force
   an awkward shape." None met that bar at first cut.

2. **Scope = what is needed today only.** Claude Code plugins, GitHub-hosted sources,
   Apache-2.0-style NOTICE generation. Out of scope: Codex / other plugin formats, non-GitHub
   sources, plugin-format strategy registry. **Add abstractions only when a second concrete need
   arrives.** A speculative strategy pattern was considered and explicitly dropped.

3. **TDD.** Every module gets failing tests before code. Tests must run offline — a fake `gh` shim
   is dropped on `PATH` via `monkeypatch` for tests touching `fetch.py` / `cli.py`.

4. **Subcommand CLI: `sync` and `check`.** Not the original's `--check` flag. Clearer separation
   of read-only verification from mutation. `--source NAME` (repeatable) and `--prune` are flags on
   `sync`.

5. **Plugin metadata source: `.claude-plugin/plugin.json`.** Single source of truth for `name`,
   `author.name`, `license`. The vendor TOML stays focused on upstream sources only — no `[plugin]`
   block. The plugin `name` doubles as the reserved name during the skill mirror, so the plugin's
   own methodology skill never gets clobbered by an upstream directory of the same name.

6. **Plugin-root discovery.** Walk up from `--plugin-root PATH` (or CWD) looking for
   `.claude-plugin/plugin.json`. (For where everything lives relative to the discovered root, see
   the plugin layout diagram in [`architecture.md`](architecture.md).)

7. **TOML schema unchanged from the original.** Migrating the `freedom-rtos-dev` plugin is a
   path-move + script-deletion, no schema edit. See `docs/architecture.md` for the schema itself.

8. **Lock format unchanged from the original.** JSON, sorted keys. Shipping a different lock format
   would break drop-in migration; the gain (e.g. YAML, comments) doesn't earn that cost yet.

9. **`gh` subprocess for fetch.** Not `httpx` / `urllib`. Reason: `gh` handles GitHub auth (its
   keychain), rate-limit retries, and GHE transparently — replacing it would mean reimplementing
   all of that. The price is one external binary dependency, satisfied by Nix.

10. **Packaging: `pyproject.toml` + `[project.scripts]` console entry.** Lets `nix run` build a
    real package and downstream plugins `pip install` the tool. The Python source uses the `src/`
    layout to avoid the implicit-CWD-import trap.
