"""Check manifest dependencies against PyPI and npm.

These detectors stay in code. A YAML rule cannot express an HTTP lookup.
"""

import json
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

import httpx

from badscan.models import Finding, ScannedFile

RULE_ID = "supply.hallucinated-dependency"
Exists = Callable[[str, str], bool]

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_NPM_NAME = re.compile(r"^(@[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+$")


def scan_registries(
    files: list[ScannedFile],
    exists: Exists | None = None,
) -> list[Finding]:
    lookup = exists or default_exists
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for source in files:
        for ecosystem, name, line in dependencies_in(source):
            key = (ecosystem, name.lower())
            if key in seen:
                continue
            seen.add(key)
            if lookup(ecosystem, name):
                continue
            registry = "PyPI" if ecosystem == "pypi" else "npm"
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    category="hallucinated-dependency",
                    severity="high",
                    confidence=0.98,
                    path=source.relative_path,
                    start_line=line,
                    end_line=line,
                    snippet=_snippet(source.text, line),
                    message=f'Dependency "{name}" was not found on {registry}.',
                )
            )
    return findings


def dependencies_in(source: ScannedFile) -> list[tuple[str, str, int]]:
    filename = Path(source.relative_path).name
    if filename == "requirements.txt" or (
        filename.startswith("requirements") and filename.endswith(".txt")
    ):
        return [("pypi", name, line) for name, line in _requirements(source.text)]
    if filename == "pyproject.toml":
        return [("pypi", name, line) for name, line in _pyproject(source.text)]
    if filename == "package.json":
        return [("npm", name, line) for name, line in _package_json(source.text)]
    return []


def default_exists(ecosystem: str, name: str) -> bool:
    """Return True when the package exists or the registry cannot be reached."""

    if ecosystem == "pypi":
        url = f"https://pypi.org/pypi/{quote(name)}/json"
    else:
        url = f"https://registry.npmjs.org/{quote(name, safe='@')}"
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
    except httpx.HTTPError:
        return True
    return response.status_code != 404


def _requirements(text: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        name = _requirement_name(raw)
        if name is not None:
            found.append((name, line_number))
    return found


def _requirement_name(raw: str) -> str | None:
    text = raw.split("#", 1)[0].strip()
    if not text or text.startswith(("-", ".")) or "://" in text:
        return None
    name = re.split(r"[<>=!~;\s\[]", text, maxsplit=1)[0]
    if not _NAME.fullmatch(name):
        return None
    return name


def _pyproject(text: str) -> list[tuple[str, int]]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    project = data.get("project")
    if not isinstance(project, dict):
        return []
    declared: list[str] = []
    dependencies = project.get("dependencies")
    if isinstance(dependencies, list):
        declared.extend(str(item) for item in dependencies)
    optional = project.get("optional-dependencies")
    if isinstance(optional, dict):
        for group in optional.values():
            if isinstance(group, list):
                declared.extend(str(item) for item in group)
    found: list[tuple[str, int]] = []
    for item in declared:
        name = _requirement_name(item)
        if name is None:
            continue
        found.append((name, _line_containing(text, name)))
    return found


def _package_json(text: str) -> list[tuple[str, int]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    found: list[tuple[str, int]] = []
    for field in ("dependencies", "devDependencies", "optionalDependencies"):
        block = data.get(field)
        if not isinstance(block, dict):
            continue
        for name in block:
            if not isinstance(name, str) or not _NPM_NAME.fullmatch(name):
                continue
            found.append((name, _line_containing(text, name)))
    return found


def _line_containing(text: str, name: str) -> int:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if name in line:
            return line_number
    return 1


def _snippet(text: str, line: int) -> str:
    lines = text.splitlines()
    if line < 1 or line > len(lines):
        return ""
    return lines[line - 1].strip()
