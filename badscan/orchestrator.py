"""Run a deterministic scan. The learn path is not part of phase 1."""

from dataclasses import dataclass

from badscan.engine.runner import run_patterns
from badscan.fetch import acquire
from badscan.library.loader import load_patterns
from badscan.models import SEVERITY_RANK, ScanResult
from badscan.walk import DEFAULT_MAX_FILES, walk_tree


@dataclass
class ScanOptions:
    include_tests: bool = False
    max_files: int = DEFAULT_MAX_FILES
    min_severity: str = "low"
    min_confidence: float = 0.0


def execute_scan(target: str, options: ScanOptions | None = None) -> ScanResult:
    settings = options or ScanOptions()
    if settings.min_severity not in SEVERITY_RANK:
        raise ValueError(f"unknown severity: {settings.min_severity}")
    if not 0.0 <= settings.min_confidence <= 1.0:
        raise ValueError("min confidence must be between 0 and 1")

    patterns = load_patterns()
    with acquire(target) as root:
        files = walk_tree(
            root,
            include_tests=settings.include_tests,
            max_files=settings.max_files,
        )
    threshold = SEVERITY_RANK[settings.min_severity]
    findings = [
        finding
        for finding in run_patterns(patterns, files)
        if SEVERITY_RANK[finding.severity] >= threshold
        and finding.confidence >= settings.min_confidence
    ]
    return ScanResult(target=target, files_scanned=len(files), findings=findings)
