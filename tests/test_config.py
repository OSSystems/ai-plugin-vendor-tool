from __future__ import annotations

from pathlib import Path

import pytest

from ai_plugin_vendor_tool import config


def test_load_plugin_meta_reads_plugin_json(make_plugin):
    root = make_plugin(name="demo-plugin", author="Demo Org", license="MIT")
    meta = config.load_plugin_meta(root)
    assert meta.name == "demo-plugin"
    assert meta.author == "Demo Org"
    assert meta.license == "MIT"


def test_load_plugin_meta_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        config.load_plugin_meta(tmp_path)


def test_load_plugin_meta_falls_back_when_author_unset(make_plugin):
    root = make_plugin(manifest={"name": "x", "license": "Apache-2.0"})
    meta = config.load_plugin_meta(root)
    assert meta.name == "x"
    assert meta.author == ""
    assert meta.license == "Apache-2.0"


def test_load_sources_parses_toml(make_plugin):
    root = make_plugin(
        vendor_toml="""
        [[source]]
        name            = "alice-skills"
        repo            = "alice/skills"
        ref             = "main"
        subpath         = "skills"
        license         = "Apache-2.0"
        attribution     = "Alice"
        attribution_url = "https://github.com/alice/skills"

        [[source]]
        name            = "bob-skills"
        repo            = "bob/skills"
        exclude_globs   = ["docs/**"]
        """
    )
    sources = config.load_sources(root)
    assert len(sources) == 2

    alice = sources[0]
    assert alice.name == "alice-skills"
    assert alice.repo == "alice/skills"
    assert alice.ref == "main"
    assert alice.subpath == "skills"
    assert alice.license == "Apache-2.0"
    assert alice.attribution == "Alice"
    assert alice.attribution_url == "https://github.com/alice/skills"
    assert alice.exclude_globs == []

    bob = sources[1]
    assert bob.name == "bob-skills"
    assert bob.ref == "main"  # default
    assert bob.subpath == ""  # default
    assert bob.license == "Apache-2.0"  # default
    assert bob.exclude_globs == ["docs/**"]
    assert bob.skill_name == ""  # default
    assert bob.substitutions == {}  # default
    assert bob.executable == []  # default


def test_load_sources_parses_skill_name_and_substitutions(make_plugin):
    root = make_plugin(
        vendor_toml="""
        [[source]]
        name          = "remote-ssh-dev"
        repo          = "owner/remote-ssh-dev"
        subpath       = "skill"
        skill_name    = "remote-ssh-dev"
        substitutions = { "__ROOT__/skill" = "${CLAUDE_PLUGIN_ROOT}/skills/remote-ssh-dev" }
        executable    = ["scripts/*.sh"]
        """
    )
    sources = config.load_sources(root)
    assert len(sources) == 1
    s = sources[0]
    assert s.skill_name == "remote-ssh-dev"
    assert s.substitutions == {"__ROOT__/skill": "${CLAUDE_PLUGIN_ROOT}/skills/remote-ssh-dev"}
    assert s.executable == ["scripts/*.sh"]


def test_load_sources_missing_returns_empty(make_plugin):
    root = make_plugin()  # no vendor_toml
    assert config.load_sources(root) == []


def test_load_sources_unknown_field_reports_name_and_key(make_plugin):
    root = make_plugin(
        vendor_toml="""
        [[source]]
        name    = "alice-skills"
        repo    = "alice/skills"
        subpaht = "skills"
        """
    )
    with pytest.raises(ValueError, match=r"alice-skills.*subpaht"):
        config.load_sources(root)


def test_load_sources_missing_required_field_reports_clearly(make_plugin):
    root = make_plugin(
        vendor_toml="""
        [[source]]
        repo = "alice/skills"
        """
    )
    with pytest.raises(ValueError, match="name"):
        config.load_sources(root)


def test_discover_plugin_root_walks_up(make_plugin):
    root = make_plugin()
    # Create a deeply nested cwd inside the plugin.
    nested = root / "skills" / "foo" / "bar"
    nested.mkdir(parents=True)
    assert config.discover_plugin_root(nested) == root


def test_discover_plugin_root_at_root(make_plugin):
    root = make_plugin()
    assert config.discover_plugin_root(root) == root


def test_discover_plugin_root_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        config.discover_plugin_root(tmp_path)
