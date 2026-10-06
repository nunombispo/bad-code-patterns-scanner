# bad-code-patterns-scanner

badscan scans a public GitHub repository or a local tree for bad code patterns that show up when generated code is merged without review.

Saved rules live in this repository under `rules/`. A scan applies those rules locally. With `--learn`, a model proposes new rules. After confirmation, the tool writes the rule back into this repo so later scans use it.

The architecture and the three-phase build plan are in [docs/architecture.md](docs/architecture.md).
