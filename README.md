# ai-plugin-vendor-tool

Vendor third-party Claude Code skills from upstream GitHub repos into a
plugin's `skills/` tree, with a JSON lockfile and an Apache-2.0-style
`NOTICE` for attribution.

Lifted out of `freedom-rtos-ai/plugins/freedom-rtos-dev/scripts/sync_vendored.py`
so any Claude Code plugin can vendor skills without copy-pasting the script.

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

Or run it directly:

```sh
nix run github:OSSystems/ai-plugin-vendor-tool -- --help
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

ai-plugin-vendor-tool sync
```

This populates:

- `vendor/<source-name>/` — pristine upstream copy.
- `skills/<each-skill>/` — each upstream directory containing a `SKILL.md`,
  mirrored where Claude Code discovers it.
- `vendor/vendored-skills.lock` — pinned commit SHAs.
- `NOTICE` — generated attribution block.

## CLI

```sh
ai-plugin-vendor-tool sync  [--plugin-root PATH] [--source NAME ...] [--prune]
ai-plugin-vendor-tool check [--plugin-root PATH] [--source NAME ...]
```

- `--plugin-root PATH` — defaults to walking up from CWD looking for
  `.claude-plugin/plugin.json`.
- `--source NAME` — repeatable; restrict the operation to specific sources.
- `--prune` — after syncing, remove `skills/<dir>/` entries that aren't
  listed in the new lock.
- `check` — resolves each ref to a SHA and exits non-zero if any source
  has drifted from the lock. Read-only.

## TOML schema

```toml
[[source]]
name            = "<unique slug for this source>"
repo            = "<owner>/<repo>"             # GitHub
ref             = "main"                        # branch, tag, or SHA
subpath         = "skills"                      # subtree to extract; "" for repo root
exclude_globs   = []                            # globs evaluated under the pristine copy
license         = "Apache-2.0"                  # appears in NOTICE
attribution     = "<copyright holder>"          # appears in NOTICE
attribution_url = "https://github.com/..."      # falls back to https://github.com/<repo>
```

## Plugin metadata

`name`, `author.name`, and `license` are read from
`.claude-plugin/plugin.json` and used in the `NOTICE` header. The plugin's
own `name` is also reserved during skill mirroring — an upstream directory
matching the plugin name is skipped, never overwriting the plugin's own
methodology skill.

## Development

```sh
nix develop          # or direnv allow
pytest               # all tests, offline (uses a fake gh shim)
nix fmt              # treefmt: nixfmt + ruff + mdformat + taplo
ruff check src tests
```

See `CLAUDE.md` for the design decisions behind the current shape.
