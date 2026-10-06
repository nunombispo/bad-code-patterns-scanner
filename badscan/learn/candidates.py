"""Local store for proposals that passed validation.

This directory is outside the tool git repository. Confirm and reject are what
write rules back into the checkout.
"""

import os
from pathlib import Path

from badscan.library.schema import dump_pattern, load_pattern_file
from badscan.models import Pattern


def candidates_root() -> Path:
    override = os.environ.get("BADSCAN_CANDIDATES")
    if override:
        return Path(override)
    return Path.home() / ".local" / "share" / "badscan" / "candidates"


def write_candidate(pattern: Pattern, root: Path | None = None) -> Path:
    directory = root or candidates_root()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{pattern.id}.yaml"
    stored = pattern.model_copy(update={"status": "candidate"})
    path.write_text(dump_pattern(stored), encoding="utf-8")
    return path


def read_candidates(root: Path | None = None) -> list[Pattern]:
    directory = root or candidates_root()
    if not directory.is_dir():
        return []
    paths = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix in {".yaml", ".yml"}
    )
    return [load_pattern_file(path) for path in paths]


def delete_candidate(pattern_id: str, root: Path | None = None) -> None:
    directory = root or candidates_root()
    path = directory / f"{pattern_id}.yaml"
    if path.is_file():
        path.unlink()
