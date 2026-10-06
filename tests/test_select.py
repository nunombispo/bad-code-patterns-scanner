from badscan.learn.select import select_chunks
from badscan.models import Finding, ScannedFile


def _finding(path: str, confidence: float) -> Finding:
    return Finding(
        rule_id="ai.residue.assistant-voice",
        category="ai-residue",
        severity="high",
        confidence=confidence,
        path=path,
        start_line=1,
        end_line=1,
        snippet="x",
        message="explained",
    )


def test_skips_files_already_explained() -> None:
    explained = ScannedFile(
        relative_path="src/known.py",
        language="python",
        text="def known():\n    return 1\n",
        kind="source",
    )
    fresh = ScannedFile(
        relative_path="src/new.py",
        language="python",
        text="def fresh():\n    return 2\n",
        kind="source",
    )
    chunks = select_chunks([explained, fresh], [_finding("src/known.py", 0.9)])
    assert [chunk.path for chunk in chunks] == ["src/new.py"]
    assert chunks[0].text.startswith("def fresh")


def test_python_file_splits_on_functions() -> None:
    source = ScannedFile(
        relative_path="src/app.py",
        language="python",
        text="def one():\n    return 1\n\ndef two():\n    return 2\n",
        kind="source",
    )
    chunks = select_chunks([source], [])
    assert [chunk.start_line for chunk in chunks] == [1, 4]


def test_low_confidence_match_still_selects_the_file() -> None:
    source = ScannedFile(
        relative_path="src/app.py",
        language="python",
        text="def run():\n    return 1\n",
        kind="source",
    )
    chunks = select_chunks([source], [_finding("src/app.py", 0.5)])
    assert len(chunks) == 1


def test_limit_caps_chunks() -> None:
    files = [
        ScannedFile(
            relative_path=f"src/f{index}.py",
            language="python",
            text=f"def f{index}():\n    return {index}\n",
            kind="source",
        )
        for index in range(5)
    ]
    assert len(select_chunks(files, [], limit=2)) == 2
