"""Fetch source tarballs from GitHub via `gh` and extract a subpath."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


class GhError(RuntimeError):
    """Raised when a `gh` invocation fails. Carries `gh`'s stderr in the message."""


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
    return out.strip()


def fetch_subtree(repo: str, sha: str, subpath: str, dest: Path) -> None:
    """Stream the GitHub tarball for `repo@sha` and extract `subpath` into `dest`.

    `subpath` is relative to the repo root. An empty string extracts the whole
    repo. The leading `<repo>-<sha-prefix>/` directory GitHub injects in its
    tarballs is stripped. Tarball members that would escape `dest` (via `..`
    or absolute paths) are rejected.
    """
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["gh", "api", f"repos/{repo}/tarball/{sha}"]
    label = f"gh api repos/{repo}/tarball/{sha}"
    # stderr → tempfile so the OS buffers it; reading a pipe after the tar
    # stream has finished can deadlock if gh wrote enough to fill the buffer.
    with tempfile.TemporaryFile() as errf:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf) as proc:
            if proc.stdout is None:
                raise GhError("gh subprocess did not expose a stdout pipe")
            tar_error: tarfile.TarError | None = None
            try:
                with tarfile.open(fileobj=proc.stdout, mode="r|gz") as tf:
                    _extract_subtree(tf, subpath, dest)
            except tarfile.TarError as exc:
                tar_error = exc
        errf.seek(0)
        err = errf.read().decode(errors="replace").strip()
    if tar_error is not None:
        raise GhError(f"{label} failed (exit {proc.returncode}): {err or tar_error}") from tar_error
    if proc.returncode != 0:
        raise GhError(f"{label} failed (exit {proc.returncode}): {err}")


def _extract_subtree(tf: tarfile.TarFile, subpath: str, dest: Path) -> None:
    dest_resolved = dest.resolve()
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
        target = (dest / rel).resolve()
        if not target.is_relative_to(dest_resolved):
            raise ValueError(f"tarball entry would escape dest: {m.name!r}")
        if m.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif m.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            data = tf.extractfile(m)
            if data is not None:
                with target.open("wb") as f:
                    shutil.copyfileobj(data, f)
