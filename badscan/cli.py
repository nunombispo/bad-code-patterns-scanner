"""Command line for scanning and for reviewing learned patterns."""

from pathlib import Path

import typer

from badscan.fetch import FetchError
from badscan.library.loader import LibraryError
from badscan.orchestrator import LearnOutcome, ScanOptions, execute_learn, execute_scan
from badscan.report import render
from badscan.review.prompt import review_candidates
from badscan.review.repo_writer import ReviewError
from badscan.walk import DEFAULT_MAX_FILES

app = typer.Typer(add_completion=False, no_args_is_help=True)
patterns_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(patterns_app, name="patterns")


@app.callback()
def main() -> None:
    """Scan a local tree or one public GitHub repository for saved bad-code patterns."""


@app.command()
def scan(
    target: str = typer.Argument(help="Local path, owner/repo, or a github.com URL"),
    format: str = typer.Option("text", "--format", help="text or json"),
    output: Path | None = typer.Option(None, "-o", "--output", help="Write the report here"),
    min_severity: str = typer.Option("low", "--min-severity", help="low, medium, or high"),
    min_confidence: float = typer.Option(0.0, "--min-confidence", help="Minimum confidence"),
    include_tests: bool = typer.Option(False, "--include-tests", help="Also scan tests and docs"),
    max_files: int = typer.Option(DEFAULT_MAX_FILES, "--max-files", help="Maximum files to read"),
    no_network: bool = typer.Option(False, "--no-network", help="Skip PyPI and npm lookups"),
    learn: bool = typer.Option(False, "--learn", help="Ask the configured model for new patterns"),
) -> None:
    """Run saved rules. --learn sends selected source to the configured model."""

    if format not in {"text", "json"}:
        typer.echo(f"unknown format: {format}", err=True)
        raise typer.Exit(2)
    settings = ScanOptions(
        include_tests=include_tests,
        max_files=max_files,
        min_severity=min_severity,
        min_confidence=min_confidence,
        no_network=no_network,
    )
    try:
        outcome = execute_learn(target, settings) if learn else None
        result = outcome.result if outcome is not None else execute_scan(target, settings)
    except (FetchError, LibraryError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc

    report = render(result, format)
    if output is not None:
        output.write_text(report, encoding="utf-8")
    typer.echo(report, nl=False)
    if outcome is not None:
        typer.echo(_learn_summary(outcome), err=True, nl=False)
    raise typer.Exit(1 if result.findings else 0)


@patterns_app.command("review")
def review(
    repo: Path | None = typer.Option(None, "--repo", help="Tool checkout that receives the commit"),
) -> None:
    """Confirm or reject a candidate by opening a pull request."""

    try:
        notes = review_candidates(repo)
    except ReviewError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    for note in notes:
        typer.echo(note)
    raise typer.Exit(0)


def _learn_summary(outcome: LearnOutcome) -> str:
    lines: list[str] = []
    count = len(outcome.candidates)
    noun = "candidate" if count == 1 else "candidates"
    lines.append(f"{count} {noun} stored for review")
    for pattern in outcome.candidates:
        lines.append(f"  {pattern.id}")
    for note in outcome.skipped:
        lines.append(f"skipped: {note}")
    return "\n".join(lines) + "\n"
