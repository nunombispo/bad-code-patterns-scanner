from pathlib import Path

import pytest

from badscan.library.loader import LibraryError, load_known_ids, load_patterns
from badscan.library.schema import PatternParseError, parse_pattern

SAMPLE = """\
id: ai.residue.assistant-voice
status: confirmed
severity: high
confidence: 0.93
category: ai-residue
languages: ["*"]
message: Pasted assistant prose is still in this file.
detect:
  type: regex
  regex: '(?i)as an ai'
  exclude: ["**/docs/**"]
examples:
  match: "As an AI, here is the handler."
  reject: "This handler validates the request."
"""


def _write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def test_parse_pattern_matches_schema() -> None:
    pattern = parse_pattern(SAMPLE, source="sample.yaml")
    assert pattern.id == "ai.residue.assistant-voice"
    assert pattern.detect.type == "regex"
    assert pattern.detect.exclude == ["**/docs/**"]
    assert pattern.examples is not None
    assert pattern.examples.reject is not None


def test_load_builtin_and_learned(tmp_path: Path) -> None:
    _write(tmp_path / "builtin", "residue.yaml", SAMPLE)
    learned = SAMPLE.replace("ai.residue.assistant-voice", "learned.placeholder-key")
    learned = learned.replace("ai-residue", "placeholder-secret")
    _write(tmp_path / "learned", "placeholder.yaml", learned)

    patterns = load_patterns(tmp_path)
    assert [pattern.id for pattern in patterns] == [
        "ai.residue.assistant-voice",
        "learned.placeholder-key",
    ]


def test_invalid_regex_is_rejected() -> None:
    broken = SAMPLE.replace("(?i)as an ai", "(")
    with pytest.raises(PatternParseError):
        parse_pattern(broken, source="broken.yaml")


def test_known_ast_predicate_parses() -> None:
    ast_rule = SAMPLE.replace(
        "type: regex\n  regex: '(?i)as an ai'",
        "type: ast\n  predicate: bare-except",
    )
    pattern = parse_pattern(ast_rule, source="ast.yaml")
    assert pattern.detect.type == "ast"
    assert pattern.detect.predicate == "bare-except"


def test_unknown_ast_predicate_is_rejected() -> None:
    ast_rule = SAMPLE.replace(
        "type: regex\n  regex: '(?i)as an ai'",
        "type: ast\n  predicate: invented-check",
    )
    with pytest.raises(PatternParseError, match="unknown AST predicate"):
        parse_pattern(ast_rule, source="ast.yaml")


def test_duplicate_id_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "builtin", "one.yaml", SAMPLE)
    _write(tmp_path / "learned", "two.yaml", SAMPLE)
    with pytest.raises(LibraryError, match="duplicate pattern id"):
        load_patterns(tmp_path)


def test_known_ids_include_rejected_rules(tmp_path: Path) -> None:
    _write(tmp_path / "builtin", "one.yaml", SAMPLE)
    rejected = SAMPLE.replace("ai.residue.assistant-voice", "learned.old-idea")
    rejected = rejected.replace("status: confirmed", "status: rejected")
    _write(tmp_path / "rejected", "old.yaml", rejected)
    (tmp_path / "learned").mkdir()
    assert load_known_ids(tmp_path) == {"ai.residue.assistant-voice", "learned.old-idea"}
    assert [pattern.id for pattern in load_patterns(tmp_path)] == ["ai.residue.assistant-voice"]


def test_unconfirmed_pattern_is_rejected(tmp_path: Path) -> None:
    candidate = SAMPLE.replace("status: confirmed", "status: candidate")
    _write(tmp_path / "builtin", "one.yaml", candidate)
    (tmp_path / "learned").mkdir()
    with pytest.raises(LibraryError, match="only confirmed"):
        load_patterns(tmp_path)
