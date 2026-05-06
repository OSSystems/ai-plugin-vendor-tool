# Architecture

## Module layout

```
src/ai_plugin_vendor_tool/
├── __init__.py
├── __main__.py        # `python -m ai_plugin_vendor_tool`
├── cli.py             # argparse → dispatch sync/check; orchestration
├── config.py          # PluginMeta, Source dataclasses; plugin-root discovery
├── fetch.py           # gh-tarball subtree extraction
├── mirror.py          # pristine vendor/ → skills/ with reserved-name protection
├── lock.py            # JSON read/write
└── notice.py          # NOTICE rendering parametrised on PluginMeta
```

`cli.py` is the only module that knows about the others. Each lower module is independently
testable and has a narrow public surface.

## Public contracts

These are consumed by downstream plugins that pin this tool. Treat them as API.

### Vendor TOML schema

Located at `<plugin-root>/vendor/vendored-skills.toml`. A list of `[[source]]` tables:

```toml
[[source]]
name            = "<unique slug for this source>"
repo            = "<owner>/<repo>"             # GitHub
ref             = "main"                       # branch, tag, or SHA
subpath         = "skills"                     # subtree to extract; "" = repo root
exclude_globs   = []                           # globs evaluated under the pristine copy
license         = "Apache-2.0"                 # appears in NOTICE
attribution     = "<copyright holder>"         # appears in NOTICE
attribution_url = "https://github.com/..."     # falls back to https://github.com/<repo>
```

### Lock file

Located at `<plugin-root>/vendor/vendored-skills.lock`. JSON, sorted keys, indented:

```json
{
  "<source-name>": {
    "repo":   "<owner>/<repo>",
    "ref":    "<branch-or-tag-or-sha>",
    "commit": "<full-resolved-sha>",
    "skills": ["sorted", "list", "of", "skill-dirs"]
  }
}
```

### NOTICE rendering

Located at `<plugin-root>/NOTICE`. Header parametrised on `PluginMeta` (name, author, license)
read from `.claude-plugin/plugin.json`; one block per source listing attribution, license, ref +
commit, and the verbatim skill list. The exact format is in `notice.render_notice` and is locked
for legal compliance — reformatting requires a major version bump.

## Plugin layout the tool expects

```
<plugin-root>/
├── .claude-plugin/
│   └── plugin.json                     # provides name, author.name, license
├── vendor/
│   ├── vendored-skills.toml            # input — list of upstream sources
│   ├── vendored-skills.lock            # output — pinned commits
│   └── <source-name>/                  # output — pristine upstream copy
└── skills/
    ├── <plugin-name>/                  # plugin's own skill — reserved, never overwritten
    └── <upstream-skill>/                # output — mirrored from vendor/
```

The plugin's own `name` (from `plugin.json`) is reserved during the mirror: an upstream directory
matching the plugin name is skipped, never overwriting the plugin's methodology skill.
