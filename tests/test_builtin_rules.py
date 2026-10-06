from pathlib import Path

import pytest

from badscan.engine.runner import run_patterns
from badscan.library.loader import load_patterns
from badscan.models import ScannedFile

EXPECTED = {
    "ai.residue.assistant-voice",
    "stub.not-implemented",
    "secret.placeholder",
    "insecure.requests-verify-false",
    "insecure.subprocess-shell",
    "insecure.dynamic-exec",
}


def test_builtin_library_loads_outside_the_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert {pattern.id for pattern in load_patterns()} == EXPECTED


def test_builtin_library_loads_and_examples_agree() -> None:
    patterns = load_patterns()
    assert {pattern.id for pattern in patterns} == EXPECTED
    for pattern in patterns:
        assert pattern.examples is not None
        assert pattern.examples.reject
        language = "python" if "*" in pattern.languages else pattern.languages[0]
        match = ScannedFile(
            relative_path="src/match.py",
            language=language,
            text=pattern.examples.match,
        )
        reject = ScannedFile(
            relative_path="src/reject.py",
            language=language,
            text=pattern.examples.reject,
        )
        assert run_patterns([pattern], [match]), pattern.id
        assert run_patterns([pattern], [reject]) == [], pattern.id
