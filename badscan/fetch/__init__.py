"""Resolve a scan target to a local directory."""

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from badscan.fetch.github import FetchError, GitHubRepo, clone_repository, parse_github_target


@contextmanager
def acquire(target: str) -> Iterator[Path]:
    """Yield a directory or file to scan.

    An existing local path is used as-is. A GitHub slug or URL is shallow-cloned
    into a temporary directory and removed when the scan finishes.
    """

    local = Path(target)
    if "://" not in target and local.exists():
        yield local.resolve()
        return

    spec = parse_github_target(target)
    destination = clone_repository(spec)
    try:
        yield destination
    finally:
        _remove_clone(destination)


def _remove_clone(destination: Path) -> None:
    parent = destination.parent
    if parent.name.startswith("badscan-") and parent.is_dir():
        shutil.rmtree(parent, ignore_errors=True)


__all__ = ["FetchError", "GitHubRepo", "acquire", "parse_github_target"]
