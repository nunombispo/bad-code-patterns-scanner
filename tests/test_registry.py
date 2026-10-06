from badscan.engine.registry import dependencies_in, scan_registries
from badscan.models import ScannedFile


def _file(path: str, text: str, language: str) -> ScannedFile:
    return ScannedFile(relative_path=path, language=language, text=text, kind="config")


def test_parses_python_and_npm_manifests() -> None:
    requirements = _file(
        "requirements.txt",
        "flask>=2\n# comment\n-r other.txt\nflask-async-utils\n",
        "text",
    )
    package = _file(
        "package.json",
        '{"dependencies": {"left-pad": "1.0.0", "express": "4.0.0"}}\n',
        "json",
    )
    project = _file(
        "pyproject.toml",
        '[project]\ndependencies = ["requests>=2"]\n',
        "toml",
    )
    assert [item[1] for item in dependencies_in(requirements)] == ["flask", "flask-async-utils"]
    assert [item[1] for item in dependencies_in(package)] == ["left-pad", "express"]
    assert [item[1] for item in dependencies_in(project)] == ["requests"]


def test_missing_package_is_a_finding() -> None:
    source = _file("requirements.txt", "flask\nmissing-pkg\n", "text")

    def exists(ecosystem: str, name: str) -> bool:
        return name != "missing-pkg"

    findings = scan_registries([source], exists)
    assert len(findings) == 1
    assert findings[0].rule_id == "supply.hallucinated-dependency"
    assert findings[0].start_line == 2
    assert 'Dependency "missing-pkg" was not found on PyPI.' == findings[0].message


def test_registry_error_does_not_invent_a_finding(monkeypatch) -> None:
    import httpx

    source = _file("package.json", '{"dependencies": {"left-pad": "1"}}\n', "json")

    def explode(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("badscan.engine.registry.httpx.get", explode)
    assert scan_registries([source]) == []
