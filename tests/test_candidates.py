from pathlib import Path

from badscan.learn.candidates import delete_candidate, read_candidates, write_candidate
from badscan.library.schema import parse_pattern

RULE = """\
id: learned.placeholder-token
status: confirmed
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


def test_candidate_roundtrip_stays_outside_rules(tmp_path: Path) -> None:
    pattern = parse_pattern(RULE, source="rule.yaml")
    path = write_candidate(pattern, tmp_path)
    assert path.parent == tmp_path
    stored = read_candidates(tmp_path)
    assert len(stored) == 1
    assert stored[0].id == "learned.placeholder-token"
    assert stored[0].status == "candidate"
    delete_candidate(stored[0].id, tmp_path)
    assert read_candidates(tmp_path) == []
