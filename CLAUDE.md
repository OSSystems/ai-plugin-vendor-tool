# CLAUDE.md

`ai-plugin-vendor-tool` — a self-contained Python CLI that vendors third-party Claude Code skills
from upstream GitHub repos into a plugin's `skills/` tree, with a JSON lockfile and Apache-2.0-style
`NOTICE` generation.

## Quick reference

- **Enter dev shell:** `nix develop` (or `direnv allow` once)
- **Run tests:** `pytest` (offline; uses a fake `gh` shim on `PATH`)
- **Format:** `nix fmt`
- **Run the CLI from the source tree:** `python -m ai_plugin_vendor_tool sync|check`
- **User-facing usage:** see [`README.md`](README.md)

## Guardrails (apply to every change)

1. **Stay narrow.** Add abstractions only when a *concrete* second need arrives — no speculative
   plugin-format strategy registry, no support for non-GitHub sources, no premature generalization.
   See decision #2 in [`docs/decisions.md`](docs/decisions.md).
2. **Don't break public contracts.** The vendor TOML schema, lock file format, and NOTICE rendering
   are consumed by downstream plugins that pin this tool. New optional fields are fine; renames or
   removals require a major-version bump. See [`docs/architecture.md`](docs/architecture.md).
3. **TDD.** Every module gets failing tests before code. Tests must run offline — use the `fake_gh`
   fixture in `tests/conftest.py`, never make real network calls.
4. **Stdlib-only runtime.** Adding a third-party runtime dep needs a real justification (stdlib
   would force an awkward shape). `pytest` is the only dev dep.

## More

- [`docs/decisions.md`](docs/decisions.md) — origin, off-the-shelf alternatives considered, full
  list of locked architectural decisions.
- [`docs/architecture.md`](docs/architecture.md) — module layout, public contracts (TOML schema,
  lock format, NOTICE rendering).
- [`docs/roadmap.md`](docs/roadmap.md) — known follow-ups, rules for safely extending the tool.
