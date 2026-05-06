# CLAUDE.md

`ai-plugin-vendor-tool` — a self-contained Python CLI that vendors third-party Claude Code skills
from upstream GitHub repos into a plugin's `skills/` tree, with a JSON lockfile and Apache-2.0-style
`NOTICE` generation.

## Quick reference

- **Enter dev shell:** `nix develop` (or `direnv allow` once)
- **Run tests:** `pytest` (offline; uses a fake `gh` shim on `PATH`)
- **Format + lint + type-check:** `nix fmt` (treefmt runs every tool listed in
  [`formatter.nix`](formatter.nix))
- **Run the CLI from the source tree:** `python -m ai_plugin_vendor_tool sync|check`
- **User-facing usage:** see [`README.md`](README.md)

## Required pre-commit checks

Before every `git commit`, both of the following must succeed:

1. `pytest` — full suite, offline.
1. `nix fmt` — treefmt drives every formatter, linter, and type checker registered in
   [`formatter.nix`](formatter.nix). A clean working tree afterwards (`git diff --quiet`) means
   nothing else needed reformatting.

If either step fails or rewrites files, fix the cause and re-stage before committing — do not
bypass with `--no-verify`.

## Guardrails (apply to every change)

1. **Stay narrow.** Add abstractions only when a *concrete* second need arrives — no speculative
   plugin-format strategy registry, no support for non-GitHub sources, no premature generalization.
   See decision #2 in [`docs/decisions.md`](docs/decisions.md).
1. **Don't break public contracts.** The vendor TOML schema, lock file format, and NOTICE rendering
   are consumed by downstream plugins that pin this tool. New optional fields are fine; renames or
   removals require a major-version bump. See [`docs/architecture.md`](docs/architecture.md).
1. **TDD.** Every module gets failing tests before code. Tests must run offline — use the `fake_gh`
   fixture in `tests/conftest.py`, never make real network calls.
1. **Stdlib-only runtime.** Adding a third-party runtime dep needs a real justification (stdlib
   would force an awkward shape). Dev dependencies (`pytest`, `mypy`, `ruff`, …) are unconstrained.

## More

- [`docs/decisions.md`](docs/decisions.md) — origin, off-the-shelf alternatives considered, full
  list of locked architectural decisions.
- [`docs/architecture.md`](docs/architecture.md) — module layout, public contracts (TOML schema,
  lock format, NOTICE rendering).
- [`docs/roadmap.md`](docs/roadmap.md) — known follow-ups, rules for safely extending the tool.
