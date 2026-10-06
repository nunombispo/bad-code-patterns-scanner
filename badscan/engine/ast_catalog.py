"""Fixed structural checks. A pattern names one of these ids."""

import ast

from badscan.engine.regex import exclude_spec, language_applies
from badscan.models import Finding, Pattern, ScannedFile

_SNIPPET_LIMIT = 240

CatalogHit = tuple[int, int]


def _bare_except(tree: ast.AST) -> list[CatalogHit]:
    hits: list[CatalogHit] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        bare = node.type is None
        blanket = isinstance(node.type, ast.Name) and node.type.id == "Exception"
        if bare or blanket:
            hits.append((node.lineno, node.end_lineno or node.lineno))
    return hits


def _eval_exec(tree: ast.AST) -> list[CatalogHit]:
    hits: list[CatalogHit] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id in {"eval", "exec"}:
            hits.append((node.lineno, node.end_lineno or node.lineno))
    return hits


def _call_keyword(tree: ast.AST, name: str, value: object) -> list[CatalogHit]:
    hits: list[CatalogHit] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != name:
                continue
            constant = keyword.value
            if isinstance(constant, ast.Constant) and constant.value is value:
                hits.append((node.lineno, node.end_lineno or node.lineno))
    return hits


def _subprocess_shell(tree: ast.AST) -> list[CatalogHit]:
    return _call_keyword(tree, "shell", True)


def _requests_verify_false(tree: ast.AST) -> list[CatalogHit]:
    return _call_keyword(tree, "verify", False)


PREDICATES = {
    "bare-except": _bare_except,
    "eval-exec": _eval_exec,
    "subprocess-shell": _subprocess_shell,
    "requests-verify-false": _requests_verify_false,
}


def scan_ast(pattern: Pattern, files: list[ScannedFile]) -> list[Finding]:
    detect = pattern.detect
    if detect.type != "ast":
        return []
    predicate = PREDICATES.get(detect.predicate)
    if predicate is None:
        return []
    excluded = exclude_spec(detect.exclude)
    findings: list[Finding] = []
    for source in files:
        if source.language != "python" or not language_applies(pattern, source.language):
            continue
        if excluded is not None and excluded.match_file(source.relative_path):
            continue
        try:
            tree = ast.parse(source.text)
        except SyntaxError:
            continue
        for start_line, end_line in predicate(tree):
            findings.append(
                Finding(
                    rule_id=pattern.id,
                    category=pattern.category,
                    severity=pattern.severity,
                    confidence=pattern.confidence,
                    path=source.relative_path,
                    start_line=start_line,
                    end_line=end_line,
                    snippet=_line_snippet(source.text, start_line, end_line),
                    message=pattern.message,
                )
            )
    return findings


def _line_snippet(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    snippet = "\n".join(lines[start_line - 1 : end_line]).strip()
    if len(snippet) > _SNIPPET_LIMIT:
        snippet = snippet[:_SNIPPET_LIMIT] + "..."
    return snippet
