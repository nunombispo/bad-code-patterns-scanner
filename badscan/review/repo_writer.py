"""Write a confirmed or rejected pattern into this checkout and commit it."""

import subprocess
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
    raise ReviewError("confirm runs inside a git checkout of this tool; pass --repo")


def confirm_pattern(
    pattern: Pattern,
    repo: Path | None = None,
    *,
    model_name: str | None = None,
) -> Path:
    message = f"Add learned pattern {pattern.id}"
    return _write(pattern, "learned", "confirmed", repo, model_name, message)


def reject_pattern(
    pattern: Pattern,
    repo: Path | None = None,
    *,
    model_name: str | None = None,
) -> Path:
    message = f"Reject pattern {pattern.id}"
    return _write(pattern, "rejected", "rejected", repo, model_name, message)


def _write(
    pattern: Pattern,
    folder: str,
    status: str,
    repo: Path | None,
    model_name: str | None,
    message: str,
) -> Path:
    root = tool_checkout(repo)
    origin = pattern.origin.model_copy() if pattern.origin is not None else PatternOrigin()
    if model_name and not origin.model:
        origin.model = model_name
    if status == "confirmed":
        origin.confirmed_at = date.today()
    stored = pattern.model_copy(update={"status": status, "origin": origin})
    path = root / "rules" / folder / f"{pattern.id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pattern(stored), encoding="utf-8")
    _commit(root, path, message)
    return path


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
