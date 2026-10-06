import json

from badscan.models import Finding, ScanResult
from badscan.report import render


def _result() -> ScanResult:
    return ScanResult(
        target="demo",
        files_scanned=2,
        findings=[
            Finding(
                rule_id="secret.placeholder",
                category="placeholder-secret",
                severity="high",
                confidence=0.9,
                path="src/b.py",
                start_line=4,
                end_line=4,
                snippet='api_key = "changeme"',
                message="Placeholder secret is still assigned in this file.",
            ),
            Finding(
                rule_id="stub.not-implemented",
                category="stub",
                severity="medium",
                confidence=0.8,
                path="src/a.py",
                start_line=2,
                end_line=2,
                snippet="raise NotImplementedError",
                message="Stub body was left in place.",
            ),
        ],
    )


def test_text_report_orders_findings_and_summarizes() -> None:
    text = render(_result(), "text")
    assert text.startswith("scanned 2 files\n")
    assert text.index("src/a.py") < text.index("src/b.py")
    assert "MEDIUM  stub.not-implemented  src/a.py:2" in text
    assert "2 findings (1 high, 1 medium)" in text


def test_json_report_matches_finding_schema() -> None:
    payload = json.loads(render(_result(), "json"))
    assert payload["target"] == "demo"
    assert payload["files_scanned"] == 2
    assert [item["rule_id"] for item in payload["findings"]] == [
        "stub.not-implemented",
        "secret.placeholder",
    ]
    assert set(payload["findings"][0]) == {
        "rule_id",
        "category",
        "severity",
        "confidence",
        "path",
        "start_line",
        "end_line",
        "snippet",
        "message",
    }


def test_empty_text_report() -> None:
    result = ScanResult(target="demo", files_scanned=0, findings=[])
    assert render(result, "text") == "scanned 0 files\n\nno findings\n"
