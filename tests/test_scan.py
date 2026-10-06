import json
from pathlib import Path

from typer.testing import CliRunner

from badscan.cli import app

FIXTURE = Path(__file__).parent / "fixtures" / "sloppy"
RUNNER = CliRunner()

EXPECTED = {
    "ai.residue.assistant-voice",
    "stub.not-implemented",
    "insecure.subprocess-shell",
    "insecure.dynamic-exec",
    "insecure.requests-verify-false",
    "secret.placeholder",
}


def test_scan_fixture_json_matches_schema(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    result = RUNNER.invoke(
        app,
        ["scan", str(FIXTURE), "--format", "json", "-o", str(report)],
    )
    assert result.exit_code == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["files_scanned"] == 3
    assert {item["rule_id"] for item in payload["findings"]} == EXPECTED
    finding = payload["findings"][0]
    assert set(finding) == {
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
    skipped = ("tests/", "docs/", "node_modules/")
    assert all(not item["path"].startswith(skipped) for item in payload["findings"])


def test_clean_tree_exits_zero(tmp_path: Path) -> None:
    source = tmp_path / "src" / "ok.py"
    source.parent.mkdir()
    source.write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")
    result = RUNNER.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "no findings" in result.stdout


def test_min_severity_hides_stubs() -> None:
    result = RUNNER.invoke(
        app,
        ["scan", str(FIXTURE), "--format", "json", "--min-severity", "high"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert "stub.not-implemented" not in {item["rule_id"] for item in payload["findings"]}
    assert "secret.placeholder" in {item["rule_id"] for item in payload["findings"]}


def test_include_tests_scans_docs_and_tests() -> None:
    result = RUNNER.invoke(app, ["scan", str(FIXTURE), "--format", "json", "--include-tests"])
    assert result.exit_code == 1
    paths = {item["path"] for item in json.loads(result.stdout)["findings"]}
    assert "docs/guide.md" in paths
    assert "tests/client_check.py" in paths


def test_bad_target_exits_two() -> None:
    result = RUNNER.invoke(app, ["scan", "not a repository"])
    assert result.exit_code == 2
