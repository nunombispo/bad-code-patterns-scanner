from pathlib import Path

from badscan.walk import walk_tree


def _touch(path: Path, text: str = "x = 1\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_walk_skips_vendored_tests_and_docs(tmp_path: Path) -> None:
    _touch(tmp_path / "src" / "app.py", "print('hi')\n")
    _touch(tmp_path / "node_modules" / "pkg" / "index.js", "eval('x')\n")
    _touch(tmp_path / "vendor" / "lib.py", "eval('x')\n")
    _touch(tmp_path / "dist" / "bundle.js", "eval('x')\n")
    _touch(tmp_path / "tests" / "test_app.py", "def test_ok():\n    assert True\n")
    _touch(tmp_path / "docs" / "guide.md", "As an AI, here is the guide.\n")
    _touch(tmp_path / "README.md", "hello\n")
    _touch(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")

    scanned = walk_tree(tmp_path)
    paths = [item.relative_path for item in scanned]
    assert paths == ["pyproject.toml", "src/app.py"]
    kinds = {item.relative_path: item.kind for item in scanned}
    assert kinds["src/app.py"] == "source"
    assert kinds["pyproject.toml"] == "config"
    assert scanned[1].language == "python"


def test_include_tests_keeps_tests_and_docs(tmp_path: Path) -> None:
    _touch(tmp_path / "src" / "app.py")
    _touch(tmp_path / "tests" / "test_app.py")
    _touch(tmp_path / "docs" / "guide.md", "guide\n")
    paths = [item.relative_path for item in walk_tree(tmp_path, include_tests=True)]
    assert paths == ["docs/guide.md", "src/app.py", "tests/test_app.py"]


def test_gitignore_and_max_files(tmp_path: Path) -> None:
    _touch(tmp_path / "src" / "a.py", "a = 1\n")
    _touch(tmp_path / "src" / "b.py", "b = 1\n")
    _touch(tmp_path / "src" / "secret.py", "c = 1\n")
    (tmp_path / ".gitignore").write_text("secret.py\n", encoding="utf-8")

    paths = [item.relative_path for item in walk_tree(tmp_path)]
    assert paths == ["src/a.py", "src/b.py"]

    capped = [item.relative_path for item in walk_tree(tmp_path, max_files=1)]
    assert capped == ["src/a.py"]


def test_skips_oversized_files(tmp_path: Path) -> None:
    _touch(tmp_path / "src" / "small.py", "a = 1\n")
    _touch(tmp_path / "src" / "big.py", "a = 1\n" + ("x" * 50))
    paths = [item.relative_path for item in walk_tree(tmp_path, max_file_bytes=10)]
    assert paths == ["src/small.py"]
