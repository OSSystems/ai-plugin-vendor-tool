"""Shared pytest fixtures."""

from __future__ import annotations

import json
import os
import stat
import sys
import tarfile
import textwrap
from io import BytesIO
from pathlib import Path

import pytest


@pytest.fixture
def make_plugin(tmp_path: Path):
    """Build a minimal Claude Code plugin tree under tmp_path.

    Returns the plugin root. The caller can pass `manifest=...` (a dict
    overriding the default plugin.json) and `vendor_toml=...` (a string for
    vendor/vendored-skills.toml).
    """

    def _make(
        *,
        name: str = "demo-plugin",
        author: str = "Demo Org",
        license: str = "Apache-2.0",
        manifest: dict | None = None,
        vendor_toml: str | None = None,
        subdir: str = "plugin",
    ) -> Path:
        root = tmp_path / subdir
        (root / ".claude-plugin").mkdir(parents=True)
        (root / "vendor").mkdir()
        (root / "skills").mkdir()
        manifest_data = manifest if manifest is not None else {
            "name": name,
            "version": "0.1.0",
            "description": "demo",
            "author": {"name": author},
            "license": license,
        }
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(manifest_data, indent=2) + "\n"
        )
        if vendor_toml is not None:
            (root / "vendor" / "vendored-skills.toml").write_text(textwrap.dedent(vendor_toml))
        return root

    return _make


def _build_tarball(layout: dict[str, str | bytes], root_prefix: str) -> bytes:
    """Build a gzipped tar with `<root_prefix>/<key>` -> value entries."""
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # Add the root dir entry first (mirrors GitHub's tarball shape).
        info = tarfile.TarInfo(name=root_prefix.rstrip("/") + "/")
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        tf.addfile(info)
        for rel, content in sorted(layout.items()):
            data = content.encode() if isinstance(content, str) else content
            info = tarfile.TarInfo(name=f"{root_prefix.rstrip('/')}/{rel}")
            info.size = len(data)
            info.mode = 0o644
            tf.addfile(info, BytesIO(data))
    return buf.getvalue()


@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch):
    """Install a fake `gh` shim on PATH that serves canned responses.

    Usage::

        gh = fake_gh()
        gh.set_commit("alice/skills", "main", "abc123")
        gh.set_tarball("alice/skills", "abc123", root_prefix="alice-skills-abc",
                       layout={"skills/foo/SKILL.md": "# foo"})

    The shim handles two argv forms:
      - gh api repos/<repo>/commits/<ref> -q .sha   -> echoes the SHA.
      - gh api repos/<repo>/tarball/<sha>           -> streams the tarball.
    """

    state_dir = tmp_path / "_fake_gh_state"
    state_dir.mkdir()
    bin_dir = tmp_path / "_fake_gh_bin"
    bin_dir.mkdir()

    shim_path = bin_dir / "gh"
    shim_src = textwrap.dedent(
        f"""
        #!{sys.executable}
        import json
        import sys
        from pathlib import Path

        STATE = Path({str(state_dir)!r})
        argv = sys.argv[1:]

        def fail(msg, code=2):
            sys.stderr.write(f"fake gh: {{msg}}\\n")
            sys.exit(code)

        if len(argv) >= 2 and argv[0] == "api":
            ep = argv[1]
            # commits endpoint
            if "/commits/" in ep:
                _, _, repo_ref = ep.partition("repos/")
                repo, _, ref = repo_ref.partition("/commits/")
                key = f"commit__{{repo.replace('/', '__')}}__{{ref}}"
                p = STATE / key
                if not p.is_file():
                    fail(f"unset commit {{repo}}@{{ref}}")
                # Optional `-q .sha` is ignored; we always print the SHA.
                sys.stdout.write(p.read_text())
                sys.exit(0)
            if "/tarball/" in ep:
                _, _, repo_sha = ep.partition("repos/")
                repo, _, sha = repo_sha.partition("/tarball/")
                key = f"tarball__{{repo.replace('/', '__')}}__{{sha}}"
                p = STATE / key
                if not p.is_file():
                    fail(f"unset tarball {{repo}}@{{sha}}")
                sys.stdout.buffer.write(p.read_bytes())
                sys.exit(0)
        fail(f"unhandled argv {{argv}}")
        """
    ).strip() + "\n"
    shim_path.write_text(shim_src)
    shim_path.chmod(shim_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    class _Gh:
        def set_commit(self, repo: str, ref: str, sha: str) -> None:
            key = f"commit__{repo.replace('/', '__')}__{ref}"
            (state_dir / key).write_text(sha)

        def set_tarball(
            self,
            repo: str,
            sha: str,
            *,
            root_prefix: str,
            layout: dict[str, str | bytes],
        ) -> None:
            key = f"tarball__{repo.replace('/', '__')}__{sha}"
            (state_dir / key).write_bytes(_build_tarball(layout, root_prefix))

    return _Gh()


# Re-export json for any tests that import it from conftest indirectly.
__all__ = ["make_plugin", "fake_gh", "json"]
