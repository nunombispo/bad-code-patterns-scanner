"""Show each candidate and confirm, reject, or skip it."""

from collections.abc import Callable
from pathlib import Path

import typer

from badscan.learn.candidates import delete_candidate, read_candidates
from badscan.models import Pattern
from badscan.review.repo_writer import confirm_pattern, reject_pattern

Chooser = Callable[[Pattern], str]


def review_candidates(repo: Path | None = None, chooser: Chooser | None = None) -> list[str]:
    """Apply a decision to each stored candidate. Returns a line per decision."""

    choose = chooser or prompt_decision
    notes: list[str] = []
    candidates = read_candidates()
    if not candidates:
        return ["no candidates"]
    for pattern in candidates:
        decision = choose(pattern).strip().lower()
        if decision in {"c", "confirm"}:
            url = confirm_pattern(pattern, repo)
            delete_candidate(pattern.id)
            notes.append(f"opened pull request for {pattern.id}: {url}")
        elif decision in {"r", "reject"}:
            reject_pattern(pattern, repo)
            delete_candidate(pattern.id)
            notes.append(f"rejected {pattern.id}")
        else:
            notes.append(f"skipped {pattern.id}")
    return notes


def prompt_decision(pattern: Pattern) -> str:
    typer.echo(f"\n{pattern.id}  {pattern.severity}  {pattern.confidence:.2f}")
    typer.echo(pattern.message)
    detect = pattern.detect
    if detect.type == "regex":
        typer.echo(f"regex: {detect.regex}")
    else:
        typer.echo(f"ast: {detect.predicate}")
    if pattern.examples is not None:
        typer.echo("match example:")
        typer.echo(pattern.examples.match)
        typer.echo("reject example:")
        typer.echo(pattern.examples.reject or "")
    return typer.prompt("confirm, reject, or skip", default="skip")
