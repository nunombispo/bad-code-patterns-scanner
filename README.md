# bad-code-patterns-scanner

badscan scans a public GitHub repository or a local tree for bad code patterns that show up when generated code is merged without review.

Saved rules live in this repository under `rules/`. Phase 1 applies `rules/builtin` and `rules/learned` locally. Learning new rules is phase 2.

```bash
pip install -e .
badscan scan ./path
badscan scan owner/repo
badscan scan https://github.com/owner/repo --format json -o report.json
```

Exit `0` when nothing meets the threshold, `1` when a finding does, and `2` when the target or the rules cannot be read.

The architecture and the three-phase build plan are in [docs/architecture.md](docs/architecture.md).
