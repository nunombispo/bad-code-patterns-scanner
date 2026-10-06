"""Parse one pattern YAML document into a Pattern."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from badscan.engine.ast_catalog import PREDICATES
from badscan.models import Pattern


class PatternParseError(ValueError):
    """A pattern file does not match the schema."""


def parse_pattern(text: str, *, source: str) -> Pattern:
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise PatternParseError(f"{source}: pattern file must be a mapping")
    try:
        pattern = Pattern.model_validate(loaded)
    except ValidationError as exc:
        raise PatternParseError(f"{source}: {exc}") from exc
    if pattern.detect.type == "ast" and pattern.detect.predicate not in PREDICATES:
        known = ", ".join(sorted(PREDICATES))
        raise PatternParseError(
            f"{source}: unknown AST predicate {pattern.detect.predicate!r}; known: {known}"
        )
    return pattern


def load_pattern_file(path: Path) -> Pattern:
    return parse_pattern(path.read_text(encoding="utf-8"), source=str(path))


def dump_pattern(pattern: Pattern) -> str:
    payload = pattern.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(payload, sort_keys=False)
