"""Shallow-clone one public GitHub repository."""

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from urllib.parse import urlparse

_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


class FetchError(ValueError):
    """The target could not be read or cloned."""


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    repo: str
    branch: str | None = None

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}.git"


def parse_github_target(target: str) -> GitHubRepo:
    text = target.strip()
    if not text:
        raise FetchError("missing scan target")
    if "://" in text:
        return _parse_url(text)
    parts = text.split("/")
    if len(parts) != 2:
        raise FetchError(f"not a local path or GitHub repository: {target}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return GitHubRepo(_component(owner), _component(repo))


def clone_repository(spec: GitHubRepo) -> Path:
    """Clone spec into a fresh temp directory and return the checkout."""

    parent = Path(tempfile.mkdtemp(prefix="badscan-"))
    destination = parent / spec.repo
    command = ["git", "clone", "--depth", "1"]
    if spec.branch is not None:
        command.extend(["--branch", spec.branch])
    command.extend(["--", spec.clone_url, str(destination)])
    completed = run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise FetchError(f"git clone failed for {spec.owner}/{spec.repo}: {detail}")
    return destination


def _parse_url(target: str) -> GitHubRepo:
    parsed = urlparse(target)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"https", "http"} or host != "github.com":
        raise FetchError(f"only public github.com repositories can be fetched: {target}")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise FetchError(f"not a GitHub repository url: {target}")
    owner = _component(parts[0])
    repo = _component(parts[1].removesuffix(".git"))
    if len(parts) == 2:
        return GitHubRepo(owner, repo)
    if len(parts) >= 4 and parts[2] == "tree":
        branch = "/".join(parts[3:])
        if not _BRANCH.fullmatch(branch) or branch.startswith("-") or ".." in branch.split("/"):
            raise FetchError(f"unsupported branch in GitHub url: {target}")
        return GitHubRepo(owner, repo, branch)
    raise FetchError(f"unsupported GitHub url: {target}")


def _component(value: str) -> str:
    if not _COMPONENT.fullmatch(value):
        raise FetchError(f"invalid GitHub owner or repository name: {value}")
    return value
