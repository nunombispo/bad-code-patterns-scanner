import subprocess
from pathlib import Path

from pydantic_ai.models.test import TestModel
from typer.testing import CliRunner

from badscan.cli import app
from badscan.learn.agent import propose
from badscan.library.schema import parse_pattern
from badscan.models import LearnFinding, LearnResult
from badscan.orchestrator import ScanOptions, execute_learn, execute_scan

RULE = """\
id: learned.placeholder-token
status: candidate
severity: high
confidence: 0.7
category: placeholder-secret
languages: ["*"]
message: Placeholder token left in source.
detect:
  type: regex
  regex: 'TOKEN_PLACEHOLDER'
examples:
  match: "token = TOKEN_PLACEHOLDER"
  reject: "token = os.environ['TOKEN']"
"""

SOURCE = "def load():\n    token = TOKEN_PLACEHOLDER\n    return token\n"
RUNNER = CliRunner()


def _proposal() -> LearnResult:
    pattern = parse_pattern(RULE, source="rule.yaml")
    return LearnResult(
        findings=[
            LearnFinding(
                path="src/app.py",
                start_line=2,
                end_line=2,
                observation="Placeholder token is still assigned.",
                proposed_pattern_id=pattern.id,
            )
        ],
        patterns=[pattern],
    )


def test_test_model_returns_the_proposal() -> None:
    model = TestModel(custom_output_args=_proposal())
    result = propose("source chunk", model)
    assert result.patterns[0].id == "learned.placeholder-token"
    assert result.findings[0].path == "src/app.py"


def test_learn_requires_a_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BADSCAN_MODEL", raising=False)
    target = tmp_path / "app.py"
    target.write_text(SOURCE, encoding="utf-8")
    result = RUNNER.invoke(app, ["scan", str(target), "--learn", "--no-network"])
    assert result.exit_code == 2
    assert "BADSCAN_MODEL" in result.output


def test_learn_confirm_opens_pull_request(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "tool"
    rules = repo / "rules"
    for folder in ("builtin", "learned", "rejected"):
        (rules / folder).mkdir(parents=True)
    _git_init(repo)
    target = tmp_path / "sample"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_text(SOURCE, encoding="utf-8")
    monkeypatch.setenv("BADSCAN_RULES", str(rules))
    monkeypatch.setenv("BADSCAN_CANDIDATES", str(tmp_path / "candidates"))
    monkeypatch.delenv("BADSCAN_MODEL", raising=False)
    published: dict[str, str] = {}

    def fake_publish(checkout: Path, branch: str, base: str, title: str, body: str) -> str:
        published["branch"] = branch
        published["base"] = base
        published["title"] = title
        published["body"] = body
        return "https://github.com/example/badscan/pull/9"

    monkeypatch.setattr("badscan.review.repo_writer.publish_pattern_pr", fake_publish)

    outcome = execute_learn(
        str(target),
        ScanOptions(no_network=True),
        model=TestModel(custom_output_args=_proposal()),
    )
    assert [pattern.id for pattern in outcome.candidates] == ["learned.placeholder-token"]

    reviewed = RUNNER.invoke(app, ["patterns", "review", "--repo", str(repo)], input="confirm\n")
    assert reviewed.exit_code == 0
    assert "https://github.com/example/badscan/pull/9" in reviewed.stdout
    assert published["base"] == "main"
    assert published["branch"] == "learned/learned.placeholder-token"
    assert published["title"] == "Add learned pattern learned.placeholder-token"
    assert "TOKEN_PLACEHOLDER" in published["body"]
    assert not (rules / "learned" / "learned.placeholder-token.yaml").is_file()

    unchanged = execute_scan(str(target), ScanOptions(no_network=True))
    assert unchanged.findings == []

    subprocess.run(
        ["git", "checkout", "learned/learned.placeholder-token"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    merged = execute_scan(str(target), ScanOptions(no_network=True))
    assert [finding.rule_id for finding in merged.findings] == ["learned.placeholder-token"]


def test_reject_opens_pull_request(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "tool"
    rules = repo / "rules"
    for folder in ("builtin", "learned", "rejected"):
        (rules / folder).mkdir(parents=True)
    _git_init(repo)
    target = tmp_path / "sample"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_text(SOURCE, encoding="utf-8")
    monkeypatch.setenv("BADSCAN_RULES", str(rules))
    monkeypatch.setenv("BADSCAN_CANDIDATES", str(tmp_path / "candidates"))
    monkeypatch.delenv("BADSCAN_MODEL", raising=False)
    published: dict[str, str] = {}

    def fake_publish(checkout: Path, branch: str, base: str, title: str, body: str) -> str:
        published["branch"] = branch
        published["base"] = base
        published["title"] = title
        published["body"] = body
        return "https://github.com/example/badscan/pull/10"

    monkeypatch.setattr("badscan.review.repo_writer.publish_pattern_pr", fake_publish)
    execute_learn(
        str(target),
        ScanOptions(no_network=True),
        model=TestModel(custom_output_args=_proposal()),
    )
    reviewed = RUNNER.invoke(app, ["patterns", "review", "--repo", str(repo)], input="reject\n")
    assert reviewed.exit_code == 0
    assert "https://github.com/example/badscan/pull/10" in reviewed.stdout
    assert published["branch"] == "rejected/learned.placeholder-token"
    assert published["title"] == "Reject pattern learned.placeholder-token"
    assert "rules/rejected" in published["body"]
    assert not (rules / "rejected" / "learned.placeholder-token.yaml").is_file()

    subprocess.run(
        ["git", "checkout", "rejected/learned.placeholder-token"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    text = (rules / "rejected" / "learned.placeholder-token.yaml").read_text(encoding="utf-8")
    assert "status: rejected" in text


def test_rejected_id_is_not_proposed_again(tmp_path: Path, monkeypatch) -> None:
    rules = tmp_path / "rules"
    for folder in ("builtin", "learned", "rejected"):
        (rules / folder).mkdir(parents=True)
    rejected = RULE.replace("status: candidate", "status: rejected")
    (rules / "rejected" / "learned.placeholder-token.yaml").write_text(rejected, encoding="utf-8")
    target = tmp_path / "src"
    target.mkdir()
    (target / "app.py").write_text(SOURCE, encoding="utf-8")
    monkeypatch.setenv("BADSCAN_RULES", str(rules))
    monkeypatch.setenv("BADSCAN_CANDIDATES", str(tmp_path / "candidates"))

    outcome = execute_learn(
        str(target),
        ScanOptions(no_network=True),
        model=TestModel(custom_output_args=_proposal()),
    )
    assert outcome.candidates == []
    assert any("already in the pattern library" in note for note in outcome.skipped)


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "rules" / "builtin" / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "rules"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial rules"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
