"""Apply one regex pattern to scanned files."""

import re

import pathspec

from badscan.models import Finding, Pattern, ScannedFile

_SNIPPET_LIMIT = 240


def language_applies(pattern: Pattern, language: str) -> bool:
    names = {item.lower() for item in pattern.languages}
    return "*" in names or language.lower() in names


def exclude_spec(excludes: list[str]) -> pathspec.PathSpec | None:
    if not excludes:
        return None
    return pathspec.PathSpec.from_lines("gitignore", excludes)


def scan_regex(pattern: Pattern, files: list[ScannedFile]) -> list[Finding]:
    detect = pattern.detect
    if detect.type != "regex":
        return []
    compiled = re.compile(detect.regex)
    excluded = exclude_spec(detect.exclude)
    findings: list[Finding] = []
    for source in files:
        if not language_applies(pattern, source.language):
            continue
        if excluded is not None and excluded.match_file(source.relative_path):
            continue
        for match in compiled.finditer(source.text):
            if match.start() == match.end():
                continue
            start_line, end_line, snippet = _snippet(source.text, match.start(), match.end())
            findings.append(
                Finding(
                    rule_id=pattern.id,
                    category=pattern.category,
                    severity=pattern.severity,
                    confidence=pattern.confidence,
                    path=source.relative_path,
                    start_line=start_line,
                    end_line=end_line,
                    snippet=snippet,
                    message=pattern.message,
                )
            )
    return findings


def _snippet(text: str, start: int, end: int) -> tuple[int, int, str]:
    start_line = text.count("\n", 0, start) + 1
    end_line = text.count("\n", 0, max(end - 1, start)) + 1
    lines = text.splitlines()
    snippet = "\n".join(lines[start_line - 1 : end_line]).strip()
    if len(snippet) > _SNIPPET_LIMIT:
        snippet = snippet[:_SNIPPET_LIMIT] + "..."
    return start_line, end_line, snippet
