"""Load confirmed patterns from rules/builtin and rules/learned."""

import os
from pathlib import Path

from badscan.library.schema import load_pattern_file
from badscan.models import Pattern


class LibraryError(ValueError):
    """The on-disk pattern library cannot be loaded."""


def rules_root() -> Path:
    """Locate the tool repository's rules directory.

    BADSCAN_RULES wins. Otherwise use rules packaged beside the library, then
    rules/ at the checkout root, then a rules/builtin found from the working directory.
    """

    override = os.environ.get("BADSCAN_RULES")
    if override:
        root = Path(override)
        if not (root / "builtin").is_dir():
            raise LibraryError(f"BADSCAN_RULES={override} has no builtin/ directory")
        return root

    here = Path(__file__).resolve()
    packaged = here.parents[1] / "rules"
    if (packaged / "builtin").is_dir():
        return packaged
    if len(here.parents) > 2:
        checkout = here.parents[2] / "rules"
        if (checkout / "builtin").is_dir():
            return checkout
    for candidate in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        rules = candidate / "rules"
        if (rules / "builtin").is_dir():
            return rules
    raise LibraryError("could not find rules/builtin from the package or the working directory")


def load_patterns(root: Path | None = None) -> list[Pattern]:
    """Return confirmed builtin and learned patterns, builtin first."""

    rules = root if root is not None else rules_root()
    patterns: list[Pattern] = []
    seen: set[str] = set()
    for folder in ("builtin", "learned"):
        for path in _pattern_files(rules / folder):
            pattern = load_pattern_file(path)
            if pattern.status != "confirmed":
                raise LibraryError(f"{path}: only confirmed patterns are loaded")
            if pattern.id in seen:
                raise LibraryError(f"duplicate pattern id {pattern.id} in {path}")
            seen.add(pattern.id)
            patterns.append(pattern)
    return patterns


def load_known_ids(root: Path | None = None) -> set[str]:
    """Ids already stored as builtin, learned, or rejected rules.

    The learn path sends these to the model and drops duplicate proposals.
    Rejected files are not executed.
    """

    rules = root if root is not None else rules_root()
    ids: set[str] = set()
    for folder in ("builtin", "learned", "rejected"):
        directory = rules / folder
        if not directory.is_dir():
            raise LibraryError(f"missing pattern directory: {directory}")
        for path in _pattern_files(directory):
            ids.add(load_pattern_file(path).id)
    return ids


def _pattern_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise LibraryError(f"missing pattern directory: {directory}")
    return sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix in {".yaml", ".yml"}
    )
