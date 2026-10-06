"""Inventory a tree and keep the files a scan should read."""

import os
from pathlib import Path
from typing import Literal

import pathspec

from badscan.models import ScannedFile

FileKind = Literal["source", "test", "config", "docs"]

DEFAULT_MAX_FILES = 5000
DEFAULT_MAX_FILE_BYTES = 1_000_000

SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "target",
}

_SUFFIX_LANGUAGE = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".rs": "rust",
    ".php": "php",
    ".sh": "shell",
    ".bash": "shell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".ini": "ini",
    ".cfg": "ini",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".html": "html",
    ".css": "css",
    ".vue": "vue",
}

_NAME_LANGUAGE = {
    "dockerfile": "docker",
    "makefile": "make",
    ".env": "env",
    ".env.example": "env",
    ".env.sample": "env",
}

_TEST_SEGMENTS = {"test", "tests", "__tests__", "spec", "specs"}
_DOC_SEGMENTS = {"doc", "docs"}
_LOCKFILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
}


def walk_tree(
    root: Path,
    *,
    include_tests: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> list[ScannedFile]:
    """Return source and config files, optionally including tests and docs."""

    root = root.resolve()
    if root.is_file():
        scanned = _read_file(root, root.parent, max_file_bytes)
        if scanned is None:
            return []
        if scanned.kind in {"test", "docs"} and not include_tests:
            return []
        return [scanned]

    ignored = _gitignore(root)
    found: list[ScannedFile] = []
    for path in sorted(_iter_files(root, ignored), key=lambda item: item.as_posix()):
        scanned = _read_file(path, root, max_file_bytes)
        if scanned is None:
            continue
        if scanned.kind in {"test", "docs"} and not include_tests:
            continue
        found.append(scanned)
        if len(found) >= max_files:
            break
    return found


def _iter_files(root: Path, ignored: pathspec.PathSpec | None):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SKIP_DIRECTORIES and not name.startswith(".")
        )
        current = Path(dirpath)
        for name in sorted(filenames):
            path = current / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if ignored is not None and ignored.match_file(relative):
                continue
            yield path


def _gitignore(root: Path) -> pathspec.PathSpec | None:
    path = root / ".gitignore"
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _read_file(path: Path, root: Path, max_file_bytes: int) -> ScannedFile | None:
    if path.name in _LOCKFILES or path.stat().st_size > max_file_bytes:
        return None
    relative = path.relative_to(root).as_posix()
    language = _language(path)
    if language is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    if "\0" in text:
        return None
    return ScannedFile(
        relative_path=relative,
        language=language,
        text=text,
        kind=_kind(path, relative),
    )


def _language(path: Path) -> str | None:
    special = _NAME_LANGUAGE.get(path.name.lower())
    if special is not None:
        return special
    return _SUFFIX_LANGUAGE.get(path.suffix.lower())


def _kind(path: Path, relative: str) -> FileKind:
    parts = set(Path(relative).parts[:-1])
    name = path.name
    if parts & _DOC_SEGMENTS or path.suffix.lower() in {".md", ".rst", ".adoc"}:
        return "docs"
    if parts & _TEST_SEGMENTS or _looks_like_test(name):
        return "test"
    config_suffix = path.suffix.lower() in {".ini", ".cfg", ".toml"}
    config_name = name in {".env", ".env.example", ".env.sample"}
    if config_name or config_suffix:
        return "config"
    if name in {"package.json", "requirements.txt", "pyproject.toml"}:
        return "config"
    return "source"


def _looks_like_test(name: str) -> bool:
    lower = name.lower()
    stem = Path(lower).stem
    return (
        stem.startswith("test_")
        or stem.endswith("_test")
        or ".test." in lower
        or ".spec." in lower
    )
