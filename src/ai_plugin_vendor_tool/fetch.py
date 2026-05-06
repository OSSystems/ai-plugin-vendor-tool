"""Fetch source tarballs from GitHub via `gh` and extract a subpath."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
from pathlib import Path


class GhError(RuntimeError):
    """Raised when a `gh` invocation fails or returns no usable output."""


def resolve_commit(repo: str, ref: str) -> str:
    """Resolve `repo@ref` to a full commit SHA via `gh api`."""
    try:
        out = subprocess.check_output(
            ["gh", "api", f"repos/{repo}/commits/{ref}", "-q", ".sha"],
            text=True,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise GhError(
            f"gh api repos/{repo}/commits/{ref} failed (exit {exc.returncode}): "
            f"{(exc.stderr or '').strip()}"
        ) from exc
    sha = out.strip()
    if not sha:
        raise GhError(f"gh api repos/{repo}/commits/{ref} returned no SHA")
    return sha


def fetch_subtree(repo: str, sha: str, subpath: str, dest: Path) -> None:
    """Stream the GitHub tarball for `repo@sha` and extract `subpath` into `dest`.

    `subpath` is relative to the repo root. An empty string extracts the whole
    repo. The leading `<repo>-<sha-prefix>/` directory GitHub injects in its
    tarballs is stripped.
    """
    dest.mkdir(parents=True, exist_ok=True)
    with subprocess.Popen(
        ["gh", "api", f"repos/{repo}/tarball/{sha}"],
        stdout=subprocess.PIPE,
    ) as proc:
        if proc.stdout is None:
            raise GhError("gh subprocess did not expose a stdout pipe")
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|gz") as tf:
                _extract_subtree(tf, subpath, dest)
        finally:
            # Drain whatever the child still has buffered so it can exit
            # cleanly; tarfile may have stopped reading early.
            proc.stdout.close()
        if proc.wait() != 0:
            raise subprocess.CalledProcessError(proc.returncode, proc.args)


def _extract_subtree(tf: tarfile.TarFile, subpath: str, dest: Path) -> None:
    sub_prefix: str | None = None
    for m in tf:
        if sub_prefix is None:
            root_prefix = m.name.split("/", 1)[0] + "/"
            sub_prefix = f"{root_prefix}{subpath.rstrip('/')}/" if subpath else root_prefix
        if not m.name.startswith(sub_prefix):
            continue
        rel = m.name[len(sub_prefix) :]
        if not rel:
            continue
        target = dest / rel
        if m.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif m.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            data = tf.extractfile(m)
            if data is not None:
                with target.open("wb") as f:
                    shutil.copyfileobj(data, f)
