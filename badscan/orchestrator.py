"""Run a scan, and optionally ask the learn agent for new patterns."""

from dataclasses import dataclass, field

from pydantic_ai.models import Model

from badscan.engine.registry import scan_registries
from badscan.engine.runner import run_patterns
from badscan.fetch import acquire
from badscan.library.loader import load_known_ids, load_patterns
from badscan.models import (
    SEVERITY_RANK,
    Finding,
    Pattern,
    PatternOrigin,
    ScannedFile,
    ScanResult,
)
from badscan.walk import DEFAULT_MAX_FILES, walk_tree


@dataclass
class ScanOptions:
    include_tests: bool = False
    max_files: int = DEFAULT_MAX_FILES
    min_severity: str = "low"
    min_confidence: float = 0.0
    no_network: bool = False


@dataclass
class LearnOutcome:
    result: ScanResult
    candidates: list[Pattern] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def execute_scan(target: str, options: ScanOptions | None = None) -> ScanResult:
    settings = _checked(options)
    files, findings = _detect(target, settings)
    return ScanResult(target=target, files_scanned=len(files), findings=findings)


def execute_learn(
    target: str,
    options: ScanOptions | None = None,
    model: str | Model | None = None,
) -> LearnOutcome:
    """Scan with saved rules, then ask the agent for new pattern proposals.

    ``model`` overrides ``BADSCAN_MODEL``. Tests pass Pydantic AI's TestModel.
    """

    from badscan.learn.agent import build_prompt, propose, resolve_model
    from badscan.learn.candidates import write_candidate
    from badscan.learn.select import select_chunks
    from badscan.learn.validate import validate_proposal

    settings = _checked(options)
    selected = resolve_model(model)
    files, findings = _detect(target, settings)
    result = ScanResult(target=target, files_scanned=len(files), findings=findings)
    chunks = select_chunks(files, findings)
    if not chunks:
        return LearnOutcome(result=result, skipped=["no unexplained source"])
    known = load_known_ids()
    proposed = propose(build_prompt(chunks, known), selected)
    label = selected if isinstance(selected, str) else "test"
    stored: list[Pattern] = []
    skipped: list[str] = []
    for pattern in proposed.patterns:
        reason = validate_proposal(pattern, known)
        if reason is not None:
            skipped.append(reason)
            continue
        origin = pattern.origin.model_copy() if pattern.origin is not None else PatternOrigin()
        if not origin.model:
            origin.model = label
        pattern = pattern.model_copy(update={"origin": origin})
        write_candidate(pattern)
        known.add(pattern.id)
        stored.append(pattern)
    return LearnOutcome(result=result, candidates=stored, skipped=skipped)


def _checked(options: ScanOptions | None) -> ScanOptions:
    settings = options or ScanOptions()
    if settings.min_severity not in SEVERITY_RANK:
        raise ValueError(f"unknown severity: {settings.min_severity}")
    if not 0.0 <= settings.min_confidence <= 1.0:
        raise ValueError("min confidence must be between 0 and 1")
    return settings


def _detect(target: str, settings: ScanOptions) -> tuple[list[ScannedFile], list[Finding]]:
    patterns = load_patterns()
    with acquire(target) as root:
        files = walk_tree(
            root,
            include_tests=settings.include_tests,
            max_files=settings.max_files,
        )
    threshold = SEVERITY_RANK[settings.min_severity]
    detected = run_patterns(patterns, files)
    if not settings.no_network:
        detected.extend(scan_registries(files))
    findings = [
        finding
        for finding in detected
        if SEVERITY_RANK[finding.severity] >= threshold
        and finding.confidence >= settings.min_confidence
    ]
    return files, findings
