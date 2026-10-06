"""Choose source chunks the saved rules did not already explain."""

import ast
from dataclasses import dataclass

from badscan.models import Finding, ScannedFile

HIGH_CONFIDENCE = 0.85
MAX_CHUNKS = 30
WINDOW_LINES = 80


@dataclass(frozen=True)
class Chunk:
    path: str
    start_line: int
    end_line: int
    language: str
    text: str


def select_chunks(
    files: list[ScannedFile],
    findings: list[Finding],
    *,
    limit: int = MAX_CHUNKS,
) -> list[Chunk]:
    explained = {finding.path for finding in findings if finding.confidence >= HIGH_CONFIDENCE}
    selected: list[Chunk] = []
    for source in files:
        if source.kind != "source" or source.relative_path in explained:
            continue
        selected.extend(_chunks_for(source))
        if len(selected) >= limit:
            return selected[:limit]
    return selected


def _chunks_for(source: ScannedFile) -> list[Chunk]:
    if source.language == "python":
        parsed = _python_chunks(source)
        if parsed:
            return parsed
    return _windows(source)


def _python_chunks(source: ScannedFile) -> list[Chunk]:
    try:
        tree = ast.parse(source.text)
    except SyntaxError:
        return []
    lines = source.text.splitlines()
    chunks: list[Chunk] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = node.end_lineno or start
        chunks.append(_make(source, start, end, lines))
    return chunks


def _windows(source: ScannedFile) -> list[Chunk]:
    lines = source.text.splitlines() or [""]
    chunks: list[Chunk] = []
    start = 1
    while start <= len(lines):
        end = min(start + WINDOW_LINES - 1, len(lines))
        chunks.append(_make(source, start, end, lines))
        start = end + 1
    return chunks


def _make(source: ScannedFile, start: int, end: int, lines: list[str]) -> Chunk:
    return Chunk(
        path=source.relative_path,
        start_line=start,
        end_line=end,
        language=source.language,
        text="\n".join(lines[start - 1 : end]),
    )
