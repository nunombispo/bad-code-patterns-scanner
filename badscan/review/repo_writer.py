"""Write a pattern back to the tool repository.

Confirm and reject each open a pull request. The decision is recorded when
that pull request is merged.
"""

import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from badscan.library.schema import dump_pattern
from badscan.models import Pattern, PatternOrigin


class ReviewError(ValueError):
    """A candidate could not be written back to the tool repository."""


def tool_checkout(explicit: Path | None = None) -> Path:
    """Return the git checkout that holds rules/."""

    if explicit is not None:
        root = explicit.resolve()
        _validate_checkout(root)
        return root
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() and (candidate / "rules" / "builtin").is_dir():
            _reject_installed_copy(candidate)
            return candidate
    raise ReviewError("review runs inside a git checkout of this tool; pass --repo")


def confirm_pattern(
    pattern: Pattern,
    repo: Path | None = None,
    *,
    model_name: str | None = None,
) -> str:
    """Open a pull request that adds the rule to rules/learned."""

    return _open_pattern_pr(
        pattern,
        repo,
        model_name=model_name,
        status="confirmed",
        folder="learned",
        branch=f"learned/{pattern.id}",
        title=f"Add learned pattern {pattern.id}",
        summary=(
            "Merging this pull request adds the pattern to `rules/learned` so later scans use it."
        ),
    )


def reject_pattern(
    pattern: Pattern,
    repo: Path | None = None,
    *,
    model_name: str | None = None,
) -> str:
    """Open a pull request that records the rule in rules/rejected."""

    return _open_pattern_pr(
        pattern,
        repo,
        model_name=model_name,
        status="rejected",
        folder="rejected",
        branch=f"rejected/{pattern.id}",
        title=f"Reject pattern {pattern.id}",
        summary=(
            "Merging this pull request records the pattern in `rules/rejected` "
            "so later learn passes do not propose it again."
        ),
    )


def _open_pattern_pr(
    pattern: Pattern,
    repo: Path | None,
    *,
    model_name: str | None,
    status: str,
    folder: str,
    branch: str,
    title: str,
    summary: str,
) -> str:
    root = tool_checkout(repo)
    stored = _prepare(pattern, model_name, status)
    base = _base_branch(root)
    with tempfile.TemporaryDirectory(prefix="badscan-pr-") as tmp:
        work = Path(tmp) / "checkout"
        added = _git(root, "worktree", "add", "-b", branch, str(work), base)
        if added.returncode != 0:
            detail = (added.stderr or added.stdout).strip()
            raise ReviewError(detail or "could not create the pull request branch")
        try:
            path = work / "rules" / folder / f"{pattern.id}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dump_pattern(stored), encoding="utf-8")
            _commit(work, path, title)
            return publish_pattern_pr(root, branch, base, title, _pr_body(stored, summary))
        finally:
            _git(root, "worktree", "remove", "--force", str(work))


def publish_pattern_pr(repo: Path, branch: str, base: str, title: str, body: str) -> str:
    """Push the pattern branch and open a GitHub pull request. Returns the PR URL."""

    slug = _github_slug(repo)
    pushed = _git(repo, "push", "-u", "origin", f"{branch}:{branch}")
    if pushed.returncode != 0:
        detail = (pushed.stderr or pushed.stdout).strip()
        raise ReviewError(detail or "git push failed")
    created = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            slug,
            "--base",
            base,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if created.returncode != 0:
        detail = (created.stderr or created.stdout).strip()
        raise ReviewError(detail or "gh pr create failed")
    url = created.stdout.strip()
    if not url:
        raise ReviewError("gh pr create did not return a pull request URL")
    return url


def _prepare(pattern: Pattern, model_name: str | None, status: str) -> Pattern:
    origin = pattern.origin.model_copy() if pattern.origin is not None else PatternOrigin()
    if model_name and not origin.model:
        origin.model = model_name
    if status == "confirmed":
        origin.confirmed_at = date.today()
    return pattern.model_copy(update={"status": status, "origin": origin})


def _pr_body(pattern: Pattern, summary: str) -> str:
    examples = pattern.examples
    match = examples.match if examples is not None else ""
    reject = examples.reject if examples is not None and examples.reject else ""
    model = "unknown"
    if pattern.origin is not None and pattern.origin.model:
        model = pattern.origin.model
    return (
        f"{summary}\n\n"
        f"{pattern.message}\n\n"
        "Match example:\n"
        f"```\n{match}\n```\n\n"
        "Reject example:\n"
        f"```\n{reject}\n```\n\n"
        f"Proposed by `{model}`.\n"
    )


def _base_branch(repo: Path) -> str:
    remote_head = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if remote_head.returncode == 0 and "/" in remote_head.stdout:
        return remote_head.stdout.strip().split("/", 1)[1]
    for name in ("main", "master"):
        if _git(repo, "rev-parse", "--verify", "--quiet", name).returncode == 0:
            return name
    current = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    name = current.stdout.strip()
    if current.returncode == 0 and name and name != "HEAD":
        return name
    raise ReviewError("could not determine the base branch for the pull request")


def _github_slug(repo: Path) -> str:
    remote = _git(repo, "remote", "get-url", "origin")
    url = remote.stdout.strip()
    if remote.returncode != 0 or not url:
        raise ReviewError("origin remote is missing; cannot open a pull request")
    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/]+?)(?:\.git)?$", url)
    if match is None:
        raise ReviewError(f"origin is not a GitHub repository: {url}")
    return match.group("slug")


def _validate_checkout(root: Path) -> None:
    if not (root / ".git").exists():
        raise ReviewError(f"{root} is not a git checkout")
    if not (root / "rules" / "builtin").is_dir():
        raise ReviewError(f"{root} has no rules/builtin directory")
    _reject_installed_copy(root)


def _reject_installed_copy(root: Path) -> None:
    if "site-packages" in root.parts:
        raise ReviewError("refusing to write patterns into an installed copy")


def _commit(repo: Path, path: Path, message: str) -> None:
    relative = path.relative_to(repo).as_posix()
    added = _git(repo, "add", "--", relative)
    if added.returncode != 0:
        raise ReviewError(added.stderr.strip() or "git add failed")
    committed = _git(repo, "commit", "-m", message)
    if committed.returncode != 0:
        detail = (committed.stderr or committed.stdout).strip()
        raise ReviewError(detail or "git commit failed")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
