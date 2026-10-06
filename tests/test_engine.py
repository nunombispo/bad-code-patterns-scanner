from badscan.engine.runner import run_patterns
from badscan.library.schema import parse_pattern
from badscan.models import ScannedFile

RULE = """\
id: insecure.requests-verify-false
status: confirmed
severity: high
confidence: 0.85
category: insecure-default
languages: [python]
message: TLS verification is disabled.
detect:
  type: regex
  regex: 'verify\\s*=\\s*False'
  exclude: ["**/docs/**"]
examples:
  match: "requests.get(url, verify=False)"
  reject: "requests.get(url, verify=True)"
"""


def _pattern():
    return parse_pattern(RULE, source="rule.yaml")


def test_regex_reports_line_and_snippet() -> None:
    source = ScannedFile(
        relative_path="src/client.py",
        language="python",
        text="import requests\n\nrequests.get(url, verify=False)\n",
    )
    findings = run_patterns([_pattern()], [source])
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "insecure.requests-verify-false"
    assert finding.start_line == 3
    assert finding.end_line == 3
    assert "verify=False" in finding.snippet
    assert finding.severity == "high"
    assert finding.confidence == 0.85


def test_language_and_path_exclude_skip_files() -> None:
    pattern = _pattern()
    files = [
        ScannedFile(relative_path="src/client.js", language="javascript", text="verify=False"),
        ScannedFile(relative_path="docs/guide.py", language="python", text="verify=False"),
        ScannedFile(relative_path="pkg/docs/note.py", language="python", text="verify=False"),
    ]
    assert run_patterns([pattern], files) == []


def test_reject_example_does_not_match() -> None:
    pattern = _pattern()
    assert pattern.examples is not None
    match = ScannedFile(relative_path="a.py", language="python", text=pattern.examples.match)
    reject = ScannedFile(
        relative_path="b.py",
        language="python",
        text=pattern.examples.reject or "",
    )
    assert len(run_patterns([pattern], [match])) == 1
    assert run_patterns([pattern], [reject]) == []
