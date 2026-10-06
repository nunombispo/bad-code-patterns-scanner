"""Dispatch patterns onto scanned files.

Phase 1 runs regex patterns. AST and registry detectors arrive in phase 2.
"""

from badscan.engine.regex import scan_regex
from badscan.models import Finding, Pattern, ScannedFile


class EngineError(ValueError):
    """A loaded pattern cannot be executed."""


def run_patterns(patterns: list[Pattern], files: list[ScannedFile]) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in patterns:
        if pattern.detect.type != "regex":
            raise EngineError(f"{pattern.id}: detect type {pattern.detect.type} is not available")
        findings.extend(scan_regex(pattern, files))
    return findings
