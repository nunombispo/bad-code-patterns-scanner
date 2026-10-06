"""Check a model proposal before it can become a candidate."""

from badscan.engine.runner import run_patterns
from badscan.models import Pattern, ScannedFile


def validate_proposal(pattern: Pattern, known_ids: set[str]) -> str | None:
    """Return a reason to drop the proposal, or None when it may be stored."""

    if pattern.id in known_ids:
        return f"{pattern.id} is already in the pattern library"
    examples = pattern.examples
    if examples is None or not examples.match.strip() or not (examples.reject or "").strip():
        return f"{pattern.id} needs a match example and a reject example"
    language = "python" if "*" in pattern.languages else pattern.languages[0]
    matched = run_patterns([pattern], [_file("src/match.py", language, examples.match)])
    rejected = run_patterns(
        [pattern],
        [_file("src/reject.py", language, examples.reject or "")],
    )
    if not matched:
        return f"{pattern.id} match example did not trigger the detector"
    if rejected:
        return f"{pattern.id} reject example triggered the detector"
    return None


def _file(path: str, language: str, text: str) -> ScannedFile:
    return ScannedFile(relative_path=path, language=language, text=text, kind="source")
