"""Human-readable scan report."""

from collections import Counter

from badscan.models import Finding, ScanResult


def render_text(result: ScanResult) -> str:
    findings = _ordered(result.findings)
    lines = [f"scanned {result.files_scanned} files", ""]
    if not findings:
        lines.append("no findings")
        return "\n".join(lines) + "\n"
    for finding in findings:
        lines.append(
            f"{finding.severity.upper()}  {finding.rule_id}  {finding.path}:{finding.start_line}"
        )
        lines.append(f"  {finding.message}")
        lines.append(f"  {finding.confidence:.2f} confidence")
        lines.append("")
    lines.append(_summary(findings))
    return "\n".join(lines) + "\n"


def _ordered(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: (finding.path, finding.start_line, finding.rule_id))


def _summary(findings: list[Finding]) -> str:
    counts = Counter(finding.severity for finding in findings)
    parts = [f"{counts[name]} {name}" for name in ("high", "medium", "low") if counts[name]]
    noun = "finding" if len(findings) == 1 else "findings"
    return f"{len(findings)} {noun} ({', '.join(parts)})"
