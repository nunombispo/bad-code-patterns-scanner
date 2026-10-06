"""Command line for the phase 1 deterministic scan."""

from pathlib import Path

import typer

from badscan.fetch import FetchError
from badscan.library.loader import LibraryError
from badscan.orchestrator import ScanOptions, execute_scan
from badscan.report import render
from badscan.walk import DEFAULT_MAX_FILES

app = typer.Typer(add_completion=False, no_args_is_help=True)


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
) -> None:
    """Run saved regex rules. This command does not call a model."""

    if format not in {"text", "json"}:
        typer.echo(f"unknown format: {format}", err=True)
        raise typer.Exit(2)
    try:
        result = execute_scan(
            target,
            ScanOptions(
                include_tests=include_tests,
                max_files=max_files,
                min_severity=min_severity,
                min_confidence=min_confidence,
            ),
        )
    except (FetchError, LibraryError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc

    report = render(result, format)
    if output is not None:
        output.write_text(report, encoding="utf-8")
    typer.echo(report, nl=False)
    raise typer.Exit(1 if result.findings else 0)
