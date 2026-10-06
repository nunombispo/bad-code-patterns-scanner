"""Parse one pattern YAML document into a Pattern."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from badscan.models import Pattern


class PatternParseError(ValueError):
    """A pattern file does not match the schema."""


def parse_pattern(text: str, *, source: str) -> Pattern:
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise PatternParseError(f"{source}: pattern file must be a mapping")
    try:
        return Pattern.model_validate(loaded)
    except ValidationError as exc:
        raise PatternParseError(f"{source}: {exc}") from exc


def load_pattern_file(path: Path) -> Pattern:
    return parse_pattern(path.read_text(encoding="utf-8"), source=str(path))
