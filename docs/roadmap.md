# Roadmap & extension rules

## Known follow-ups (out of scope until requested)

- **Migrate `freedom-rtos-dev`.** Delete its in-tree `scripts/sync_vendored.py`, point its README
  and any CI at `ai-plugin-vendor-tool sync`. Can land in the customer repo as a single PR.
- **Second plugin format (Codex etc.).** Revisit decision #5 in [`decisions.md`](decisions.md) and
  introduce a thin `Format` strategy *then* — not before. The current shape assumes Claude Code's
  `.claude-plugin/plugin.json` and `SKILL.md` conventions.
- **Non-GitHub sources.** Revisit `fetch.py`'s `gh` dependency. Likely a per-source `kind` field in
  the TOML schema and a small dispatch.

## Rules for safely extending the tool

- The TOML schema (`vendor/vendored-skills.toml`) is a public contract once the first downstream
  plugin pins this tool. **New optional fields are fine; renames or removals are not** without a
  major-version bump.
- The lock format (`vendor/vendored-skills.lock`) is also a public contract — `freedom-rtos-dev`
  checks it into git. Same rule.
- The NOTICE rendering is a public contract for legal compliance. Reformatting requires a major
  version bump.
- Any change touching `cli.py` must keep `sync` / `check` argument shapes backwards-compatible
  (additive flags are fine).
