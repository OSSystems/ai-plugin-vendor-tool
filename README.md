# ai-plugin-vendor-tool

Vendor third-party Claude Code skills from upstream GitHub repos into a
plugin's `skills/` tree, with a JSON lockfile and an Apache-2.0-style
`NOTICE` for attribution.

Lifted out of `freedom-rtos-ai/plugins/freedom-rtos-dev/scripts/sync_vendored.py`
so any Claude Code plugin can vendor skills without copy-pasting the script.

## Prerequisites

- **Python 3.11+**.
- **[`gh`](https://cli.github.com/) on `PATH`**, authenticated via `gh auth login`
  (or `GH_TOKEN` in the environment). Authentication is required even for public
  sources — unauthenticated GitHub API calls are rate-limited to 60/hour.
- A **Claude Code plugin directory** containing `.claude-plugin/plugin.json`.

The Nix package wraps `gh` onto the binary's `PATH` automatically.

## Install

### Nix flake (consume from another flake)

The tool is exposed as `packages.<system>.default`, with `gh` wrapped onto its `PATH`.

```nix
{
  inputs.ai-plugin-vendor-tool.url = "github:OSSystems/ai-plugin-vendor-tool";
  inputs.ai-plugin-vendor-tool.inputs.nixpkgs.follows = "nixpkgs";
  # ...
  outputs = { self, nixpkgs, ai-plugin-vendor-tool, ... }: {
    devShells.x86_64-linux.default = nixpkgs.legacyPackages.x86_64-linux.mkShell {
      packages = [
        ai-plugin-vendor-tool.packages.x86_64-linux.default
      ];
    };
  };
}
```

Or run it directly without installing:

```sh
nix run github:OSSystems/ai-plugin-vendor-tool -- sync
```

### Nix (this repo)

```sh
cd ai-plugin-vendor-tool
direnv allow      # or: nix develop
ai-plugin-vendor-tool --help
```

### pip

```sh
pip install -e .
```

## Quickstart

In a Claude Code plugin (a directory containing `.claude-plugin/plugin.json`):

1. Describe the upstream sources you want to vendor:

   ```sh
   mkdir -p vendor
   cat > vendor/vendored-skills.toml <<'TOML'
   [[source]]
   name            = "ksachdeva-zephyr-rtos-ai"
   repo            = "ksachdeva/zephyr-rtos-ai"
   ref             = "main"
   subpath         = "skills"
   license         = "Apache-2.0"
   attribution     = "Kapil Sachdeva"
   attribution_url = "https://github.com/ksachdeva/zephyr-rtos-ai"
   TOML
   ```

1. Sync:

   ```sh
   ai-plugin-vendor-tool sync
   ```

That produces:

- `vendor/<source-name>/` — pristine upstream copy of the configured `subpath`.
- `skills/<each-skill>/` — every upstream directory containing a `SKILL.md`,
  mirrored where Claude Code discovers it.
- `vendor/vendored-skills.lock` — pinned commit SHAs, JSON, sorted keys.
- `NOTICE` — generated attribution block.

1. Commit the lock and `NOTICE`. Whether you commit `vendor/<source-name>/`
   itself is up to the plugin: checking it in pins the exact tree; gitignoring
   it keeps the repo light and relies on `sync` to repopulate. The lock alone
   is enough to fully reproduce a sync.

## CLI

```sh
ai-plugin-vendor-tool sync  [--plugin-root PATH] [--source NAME ...] [--prune]
ai-plugin-vendor-tool check [--plugin-root PATH] [--source NAME ...]
```

Common flags:

- `--plugin-root PATH` — defaults to walking up from the current directory
  looking for `.claude-plugin/plugin.json`.
- `--source NAME` — repeatable; restrict the operation to specific sources.
  Other sources keep their existing lock entries untouched.

`sync` only:

- `--prune` — after syncing, remove `skills/<dir>/` entries that aren't
  listed in the new lock (and aren't the plugin's own reserved skill).

### `check`

Read-only. Resolves each configured `ref` to a SHA and compares against the
lock. Exit codes:

- `0` — every selected source matches its lock entry.
- `1` — at least one source has drifted (or has no lock entry yet).
- `2` — usage error (missing plugin root, unknown source filter, etc.).

Use in CI to fail builds when upstream advances but the plugin hasn't been
re-synced.

### `sync`

Mutating. Always re-resolves `ref` → SHA, refetches the pristine copy,
re-mirrors into `skills/`, and rewrites the lock and `NOTICE`. Same exit-code
conventions as `check` except `1` (drift) is not produced.

## How it works

Per source, on `sync`:

1. `gh api repos/<repo>/commits/<ref>` → resolve `ref` to a full commit SHA.
1. `gh api repos/<repo>/tarball/<sha>` → stream the tarball; extract only the
   configured `subpath` into `vendor/<source-name>/`.
1. Mirror each top-level entry of the pristine copy into `skills/`:
   - Directories with a `SKILL.md` become skill entries and land in the lock.
   - Directories without one are still copied (treated as shared resources)
     but do not appear in the lock's `skills` list.
   - Loose top-level files are copied as-is alongside the skills.
   - Anything matching an `exclude_globs` pattern is skipped.
   - Any entry whose name matches the plugin's own `name` is skipped — your
     methodology skill is never overwritten by an upstream directory of the
     same name.
1. Write `vendor/vendored-skills.lock` and `NOTICE`.

## TOML schema

`<plugin-root>/vendor/vendored-skills.toml` is a list of `[[source]]` tables:

```toml
[[source]]
name            = "<unique slug for this source>"    # required
repo            = "<owner>/<repo>"                   # required — GitHub
ref             = "main"                             # default: "main" (branch, tag, or SHA)
subpath         = "skills"                           # default: "" (whole repo)
exclude_globs   = []                                 # globs evaluated under the pristine copy
license         = "Apache-2.0"                       # default: "Apache-2.0" — appears in NOTICE
attribution     = "<copyright holder>"               # appears in NOTICE
attribution_url = "https://github.com/<owner>/<repo>" # falls back to https://github.com/<repo>
```

`name` must be unique across sources — it's the slug used for the
`vendor/<name>/` directory, the lock key, and the NOTICE block heading.

## Lock format

`<plugin-root>/vendor/vendored-skills.lock` — JSON, sorted keys, indented:

```json
{
  "ksachdeva-zephyr-rtos-ai": {
    "commit": "5e1f0c3d8a9b...",
    "ref": "main",
    "repo": "ksachdeva/zephyr-rtos-ai",
    "skills": ["zephyr-gpio", "zephyr-i2c"]
  }
}
```

Treat it as a public contract: it's checked into downstream plugin repos.

## Plugin metadata

`name`, `author.name`, and `license` are read from
`.claude-plugin/plugin.json` and used in the `NOTICE` header. The plugin's
own `name` is also reserved during skill mirroring — an upstream directory
matching the plugin name is skipped, never overwriting the plugin's own
methodology skill.

## Plugin layout the tool expects

```
<plugin-root>/
├── .claude-plugin/
│   └── plugin.json                     # provides name, author.name, license
├── vendor/
│   ├── vendored-skills.toml            # input — list of upstream sources
│   ├── vendored-skills.lock            # output — pinned commits
│   └── <source-name>/                  # output — pristine upstream subtree
├── skills/
│   ├── <plugin-name>/                  # plugin's own skill — reserved
│   └── <upstream-skill>/               # output — mirrored from vendor/
└── NOTICE                              # output — attribution
```

## CI recipe

A typical CI job to fail when upstream drifts:

```yaml
- run: ai-plugin-vendor-tool check
```

To open an automated PR that re-syncs on drift, run `sync` in a scheduled
workflow and commit the resulting `vendor/`, `skills/`, lock, and NOTICE.

## Development

```sh
nix develop          # or: direnv allow
pytest               # all tests, offline (uses a fake gh shim)
nix fmt              # treefmt: nixfmt + ruff + mdformat + taplo + pyright
ruff check src tests
```

Tests must run offline. The `fake_gh` fixture in `tests/conftest.py` drops a
shim on `PATH` that serves canned commit SHAs and tarballs — never make real
network calls from tests.

See [`CLAUDE.md`](CLAUDE.md), [`docs/decisions.md`](docs/decisions.md), and
[`docs/architecture.md`](docs/architecture.md) for the design rationale.
