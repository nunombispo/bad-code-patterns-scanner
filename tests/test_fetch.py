from pathlib import Path

import pytest

from badscan.fetch import acquire, parse_github_target
from badscan.fetch.github import FetchError, clone_repository


def test_parse_slug_and_url() -> None:
    slug = parse_github_target("nunombispo/bad-code-patterns-scanner")
    assert slug.owner == "nunombispo"
    assert slug.repo == "bad-code-patterns-scanner"
    assert slug.branch is None
    assert slug.clone_url == "https://github.com/nunombispo/bad-code-patterns-scanner.git"

    url = parse_github_target("https://github.com/nunombispo/bad-code-patterns-scanner.git")
    assert (url.owner, url.repo, url.branch) == ("nunombispo", "bad-code-patterns-scanner", None)

    branched = parse_github_target(
        "https://github.com/nunombispo/bad-code-patterns-scanner/tree/main"
    )
    assert branched.branch == "main"


def test_rejects_non_github_and_odd_urls() -> None:
    with pytest.raises(FetchError):
        parse_github_target("https://gitlab.com/owner/repo")
    with pytest.raises(FetchError):
        parse_github_target("https://github.com/owner/repo/blob/main/README.md")
    with pytest.raises(FetchError):
        parse_github_target("owner/repo/extra")
    with pytest.raises(FetchError):
        parse_github_target("../etc/passwd")


def test_acquire_local_path_is_not_deleted(tmp_path: Path) -> None:
    source = tmp_path / "src" / "app.py"
    source.parent.mkdir()
    source.write_text("print('ok')\n", encoding="utf-8")
    with acquire(str(tmp_path)) as root:
        assert root == tmp_path.resolve()
        assert (root / "src" / "app.py").is_file()
    assert tmp_path.is_dir()


def test_clone_command_is_shallow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def fake_run(command, capture_output, text):
        commands.append(command)
        destination = Path(command[-1])
        destination.mkdir(parents=True)
        (destination / "README.md").write_text("ok\n", encoding="utf-8")

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr("badscan.fetch.github.run", fake_run)
    monkeypatch.setattr("badscan.fetch.github.tempfile.mkdtemp", lambda prefix: str(tmp_path))
    spec = parse_github_target("owner/repo")
    checkout = clone_repository(spec)
    assert checkout == tmp_path / "repo"
    assert commands[0][:4] == ["git", "clone", "--depth", "1"]
    assert "https://github.com/owner/repo.git" in commands[0]
    assert "--recurse-submodules" not in commands[0]
