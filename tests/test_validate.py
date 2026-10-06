from badscan.learn.validate import validate_proposal
from badscan.library.schema import parse_pattern

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


def test_valid_proposal_is_accepted() -> None:
    pattern = parse_pattern(RULE, source="rule.yaml")
    assert validate_proposal(pattern, set()) is None


def test_duplicate_and_bad_examples_are_rejected() -> None:
    pattern = parse_pattern(RULE, source="rule.yaml")
    assert validate_proposal(pattern, {pattern.id}) is not None
    swapped = parse_pattern(
        RULE.replace('match: "token = TOKEN_PLACEHOLDER"', 'match: "token = real"').replace(
            'reject: "token = os.environ[\'TOKEN\']"',
            'reject: "token = TOKEN_PLACEHOLDER"',
        ),
        source="swapped.yaml",
    )
    reason = validate_proposal(swapped, set())
    assert reason is not None
    assert "did not trigger" in reason
