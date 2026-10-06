"""Dispatch patterns onto scanned files.

Regex and AST patterns run here. Registry checks run beside this, because they
need network lookups the pattern schema cannot express.
"""

from badscan.engine.ast_catalog import scan_ast
from badscan.engine.regex import scan_regex
from badscan.models import Finding, Pattern, ScannedFile


class EngineError(ValueError):
    """A loaded pattern cannot be executed."""


def run_patterns(patterns: list[Pattern], files: list[ScannedFile]) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in patterns:
        detect_type = pattern.detect.type
        if detect_type == "regex":
            findings.extend(scan_regex(pattern, files))
        elif detect_type == "ast":
            findings.extend(scan_ast(pattern, files))
        else:
            raise EngineError(f"{pattern.id}: detect type {detect_type} is not available")
    return findings
