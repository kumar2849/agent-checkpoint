# Agent Checkpoint

## :zap: Cut CI times by 70%+. Run only tests affected by AI-generated code

AI coding agents generate enough changes to overwhelm CI systems that run a full test suite on every commit. Agent Checkpoint detects AI-authored changed lines from git metadata, looks up the tests that cover those lines, and runs only that subset. It gives teams using Copilot, Cursor, or custom agents faster feedback without silently skipping checks when coverage data is missing.

## Why it matters

Traditional CI treats a one-line agent edit like a repository-wide refactor. Agent Checkpoint makes the decision from line-level provenance and per-test coverage. Changes below a configurable AI contribution threshold can be skipped; qualifying changes get focused tests and optional lightweight linting. If the coverage map is absent or has no matching tests, the MVP safely falls back to the full suite.

The 70% figure is the project's benchmark target for repositories where AI changes affect at most 10% of the codebase; it is not a guarantee for every suite.

## Features

- **AI-line detection** using `git diff`, `git blame`, a configurable commit-message marker, and an optional SHA allowlist
- **Coverage-guided selection** from coverage.py JSON containing pytest per-test contexts
- **Threshold skipping** when the AI-authored share is below 5% by default
- **Optional static analysis** with Ruff for Python and ESLint for JavaScript/TypeScript
- **Deterministic outputs**: `tests-to-run`, `ai-line-count`, and `skipped`
- **Conservative fallback** to the full pytest target when attribution is unavailable

## Install

```bash
pip install agent-checkpoint
```

Or use the Action directly:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: agent-checkpoint/agent-checkpoint@v1
```

Full git history is required for commit-message and blame inspection.

## Quick start

First generate a baseline map with pytest-cov dynamic contexts. Store or download this `coverage.json` before Agent Checkpoint runs:

```bash
pytest --cov=. --cov-context=test
coverage json --show-contexts -o coverage.json
```

Then configure the Action:

```yaml
name: Incremental CI
on: [pull_request]

jobs:
  checkpoint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Restore baseline coverage map
        uses: actions/download-artifact@v4
        with:
          name: coverage-map

      - name: Run Agent Checkpoint
        id: checkpoint
        uses: agent-checkpoint/agent-checkpoint@v1
        with:
          base-ref: ${{ github.event.pull_request.base.sha }}
          ai-marker: "Co-authored-by: GitHub Copilot"
          threshold: "0.05"
          coverage-json: coverage.json
          run-static: "true"

      - name: Show selection
        run: echo '${{ steps.checkpoint.outputs.tests-to-run }}'
```

The Action executes the selected tests by default. Set `execute-tests: "false"` to use its JSON output in a downstream step instead.

## Command-line usage

```bash
agent-checkpoint \
  --repo-path . \
  --base-ref origin/main \
  --ai-marker "Co-authored-by: Cursor" \
  --threshold 0.05 \
  --coverage-json coverage.json \
  --run-static \
  --output-json checkpoint.json
```

Use `--ai-commit SHA` more than once, or `--ai-commits SHA1,SHA2`, for agents that do not add commit-message metadata. Add `--execute-tests` when using the CLI to run the selected pytest targets immediately.

## How selection works

1. Parse the added-side line numbers in `git diff BASE...HEAD`.
2. Attribute those lines to commits with porcelain `git blame`.
3. Match commit messages against `ai-marker` or match their SHA against `ai-commits`.
4. Skip successfully if `AI lines / changed lines` is below `threshold`.
5. Union all pytest node IDs attributed to qualifying lines in the coverage map.
6. Run those tests, or fall back to the configured full-suite target when no safe selection can be made.

Coverage attribution relies on pytest-cov's `--cov-context=test`; ordinary statement-only coverage JSON cannot identify individual tests.

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

## Roadmap

- Coverage fingerprint caching and automatic artifact refresh
- Per-agent thresholds and language-specific coverage adapters
- Parallel test scheduling and benchmark reporting
- Extensible linter and test-runner plugins

## Contributing

Issues and pull requests are welcome. Please include tests for behavioral changes and keep selection deterministic and fail-safe.

## License

MIT
