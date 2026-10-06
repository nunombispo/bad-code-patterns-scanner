from badscan.engine.runner import run_patterns
from badscan.library.schema import parse_pattern
from badscan.models import ScannedFile

BARE = """\
id: ast.bare-except
status: confirmed
severity: medium
confidence: 0.8
category: error-handling
languages: [python]
message: Bare or blanket Exception handler hides the failure.
detect:
  type: ast
  predicate: bare-except
"""


def _rule(predicate: str, rule_id: str) -> str:
    return BARE.replace("bare-except", predicate).replace("ast.bare-except", rule_id)


def _scan(predicate: str, rule_id: str, source: str) -> list[int]:
    pattern = parse_pattern(_rule(predicate, rule_id), source="rule.yaml")
    file = ScannedFile(relative_path="src/app.py", language="python", text=source)
    return [finding.start_line for finding in run_patterns([pattern], [file])]


def test_bare_except_and_blanket_exception() -> None:
    source = "try:\n    run()\nexcept:\n    pass\ntry:\n    run()\nexcept Exception:\n    log()\n"
    assert _scan("bare-except", "ast.bare-except", source) == [3, 7]


def test_bare_except_ignores_typed_handler() -> None:
    source = "try:\n    run()\nexcept ValueError:\n    raise\n"
    assert _scan("bare-except", "ast.bare-except", source) == []


def test_eval_exec_call() -> None:
    source = "value = eval(payload)\nexec(script)\nmodel.eval()\n"
    assert _scan("eval-exec", "ast.eval-exec", source) == [1, 2]


def test_shell_and_verify_keywords() -> None:
    source = "subprocess.run(cmd, shell=True)\nrequests.get(url, verify=False)\n"
    assert _scan("subprocess-shell", "ast.subprocess-shell", source) == [1]
    assert _scan("requests-verify-false", "ast.requests-verify-false", source) == [2]


def test_syntax_error_is_skipped() -> None:
    assert _scan("eval-exec", "ast.eval-exec", "def (\n") == []
