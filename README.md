# bad-code-patterns-scanner

badscan scans a public GitHub repository or a local tree for bad code patterns that show up when generated code is merged without review.

Saved rules live in this repository under `rules/`. A scan applies `rules/builtin` and `rules/learned` locally.

```bash
pip install -e .
badscan scan ./path
badscan scan owner/repo
badscan scan https://github.com/owner/repo --format json -o report.json
```

`--learn` sends the selected source chunks to the model named by `BADSCAN_MODEL` (a Pydantic AI `provider:name` string, such as `openai:gpt-4.1` or `anthropic:claude-sonnet-4-5`). That is the only command that sends source code to a model provider.

```bash
export BADSCAN_MODEL=openai:gpt-4.1
badscan scan ./path --learn
badscan patterns review
```

Confirm opens a pull request that adds `rules/learned/<id>.yaml`. Reject opens a pull request that adds `rules/rejected/<id>.yaml`. Later scans use a confirmed rule, and later learn passes skip a rejected id, after the pull request is merged. This needs a GitHub `origin` and an authenticated `gh` command. `--no-network` skips PyPI and npm lookups.

Exit `0` when nothing meets the threshold, `1` when a finding does, and `2` when the target or the rules cannot be read.

The architecture and the three-phase build plan are in [docs/architecture.md](docs/architecture.md).
