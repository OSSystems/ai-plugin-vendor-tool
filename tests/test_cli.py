from __future__ import annotations

import json

import pytest

from ai_plugin_vendor_tool import __version__, cli


def _setup_alice(fake_gh, sha: str = "abc123def4567890") -> None:
    fake_gh.set_commit("alice/skills", "main", sha)
    fake_gh.set_tarball(
        "alice/skills",
        sha,
        root_prefix=f"alice-skills-{sha[:7]}",
        layout={
            "skills/foo/SKILL.md": "# foo\n",
            "skills/bar/SKILL.md": "# bar\n",
            "skills/README.md": "shared\n",
        },
    )


def _alice_toml() -> str:
    return """
        [[source]]
        name            = "alice-skills"
        repo            = "alice/skills"
        ref             = "main"
        subpath         = "skills"
        license         = "Apache-2.0"
        attribution     = "Alice"
        attribution_url = "https://github.com/alice/skills"
    """


def test_sync_creates_lock_notice_and_skills(make_plugin, fake_gh):
    root = make_plugin(name="demo-plugin", author="Demo Org", vendor_toml=_alice_toml())
    _setup_alice(fake_gh)

    rc = cli.main(["sync", "--plugin-root", str(root)])
    assert rc == 0

    lock_path = root / "vendor" / "vendored-skills.lock"
    lock_data = json.loads(lock_path.read_text())
    assert lock_data["alice-skills"]["repo"] == "alice/skills"
    assert lock_data["alice-skills"]["commit"] == "abc123def4567890"
    assert lock_data["alice-skills"]["skills"] == ["bar", "foo"]

    assert (root / "skills" / "foo" / "SKILL.md").is_file()
    assert (root / "skills" / "bar" / "SKILL.md").is_file()
    # Loose top-level file from the vendored subtree.
    assert (root / "skills" / "README.md").is_file()

    notice = (root / "NOTICE").read_text()
    assert "demo-plugin" in notice
    assert "Demo Org" in notice
    assert "abc123def4567890" in notice
    assert "Skills (2): bar, foo" in notice


def test_sync_skips_reserved_plugin_name(make_plugin, fake_gh):
    root = make_plugin(name="demo-plugin", vendor_toml=_alice_toml())
    fake_gh.set_commit("alice/skills", "main", "abc123")
    fake_gh.set_tarball(
        "alice/skills",
        "abc123",
        root_prefix="alice-skills-abc",
        layout={
            "skills/demo-plugin/SKILL.md": "# evil\n",  # would clobber plugin's own
            "skills/foo/SKILL.md": "# foo\n",
        },
    )

    rc = cli.main(["sync", "--plugin-root", str(root)])
    assert rc == 0

    assert not (root / "skills" / "demo-plugin").exists()
    assert (root / "skills" / "foo").is_dir()


def test_check_in_sync(make_plugin, fake_gh, capsys):
    root = make_plugin(vendor_toml=_alice_toml())
    _setup_alice(fake_gh)
    cli.main(["sync", "--plugin-root", str(root)])

    rc = cli.main(["check", "--plugin-root", str(root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "in sync" in out


def test_check_detects_drift(make_plugin, fake_gh, capsys):
    root = make_plugin(vendor_toml=_alice_toml())
    _setup_alice(fake_gh, sha="oldsha000000")
    cli.main(["sync", "--plugin-root", str(root)])

    # Upstream advances.
    fake_gh.set_commit("alice/skills", "main", "newsha111111")

    rc = cli.main(["check", "--plugin-root", str(root)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "drift detected" in out
    assert "alice-skills" in out


def test_check_drift_when_lock_missing(make_plugin, fake_gh, capsys):
    root = make_plugin(vendor_toml=_alice_toml())
    fake_gh.set_commit("alice/skills", "main", "newsha")

    rc = cli.main(["check", "--plugin-root", str(root)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "drift detected" in out
    assert "(absent)" in out


def test_sync_prune_removes_orphan_skills(make_plugin, fake_gh):
    root = make_plugin(vendor_toml=_alice_toml())
    _setup_alice(fake_gh)

    # Pre-existing orphan skill (e.g. left over from a removed source).
    orphan = root / "skills" / "orphan-skill"
    orphan.mkdir(parents=True)
    (orphan / "SKILL.md").write_text("# orphan\n")

    rc = cli.main(["sync", "--plugin-root", str(root), "--prune"])
    assert rc == 0
    assert not (root / "skills" / "orphan-skill").exists()
    assert (root / "skills" / "foo" / "SKILL.md").is_file()


def test_sync_keeps_plugin_own_skill_during_prune(make_plugin, fake_gh):
    root = make_plugin(name="demo-plugin", vendor_toml=_alice_toml())
    _setup_alice(fake_gh)

    own = root / "skills" / "demo-plugin"
    own.mkdir(parents=True)
    (own / "SKILL.md").write_text("# methodology\n")

    rc = cli.main(["sync", "--plugin-root", str(root), "--prune"])
    assert rc == 0
    assert (own / "SKILL.md").is_file()


def test_sync_source_filter_only_syncs_named(make_plugin, fake_gh):
    toml = (
        _alice_toml()
        + """
        [[source]]
        name            = "bob-skills"
        repo            = "bob/skills"
        ref             = "main"
        subpath         = "skills"
        attribution     = "Bob"
    """
    )
    root = make_plugin(vendor_toml=toml)
    _setup_alice(fake_gh)
    fake_gh.set_commit("bob/skills", "main", "bobsha")
    fake_gh.set_tarball(
        "bob/skills",
        "bobsha",
        root_prefix="bob-skills-bob",
        layout={"skills/bob-thing/SKILL.md": "# bob\n"},
    )

    # First, sync only alice. The lock should not list bob.
    rc = cli.main(["sync", "--plugin-root", str(root), "--source", "alice-skills"])
    assert rc == 0
    lock = json.loads((root / "vendor" / "vendored-skills.lock").read_text())
    assert "alice-skills" in lock
    assert "bob-skills" not in lock
    assert (root / "skills" / "foo").is_dir()
    assert not (root / "skills" / "bob-thing").exists()


def test_sync_unknown_source_filter_errors(make_plugin, fake_gh):
    root = make_plugin(vendor_toml=_alice_toml())
    rc = cli.main(["sync", "--plugin-root", str(root), "--source", "no-such"])
    assert rc != 0


def test_plugin_root_default_walks_up(make_plugin, fake_gh, monkeypatch):
    root = make_plugin(vendor_toml=_alice_toml())
    _setup_alice(fake_gh)
    nested = root / "skills"
    monkeypatch.chdir(nested)

    rc = cli.main(["sync"])
    assert rc == 0
    assert (root / "vendor" / "vendored-skills.lock").is_file()


def test_missing_vendor_toml_returns_error_code(make_plugin):
    root = make_plugin()  # no vendor_toml
    rc = cli.main(["sync", "--plugin-root", str(root)])
    assert rc != 0


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out
