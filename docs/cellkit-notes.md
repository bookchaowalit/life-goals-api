# cellkit notes

`src/cellkit/` is this service's own framework code. It was first generated from `cell.yaml` by the shared generator (solo-cell-kit, retired 2026-10-12), and it is changed here only. Nothing upstream is synced; other cells keep their own copies (owner decision 2026-10-21).

## Before Wave 2

At `35cf9e7` this copy was the life copy: a failed inline publish was only logged (no Sentry `capture`); other differences were comment wording only. In a comparison of all 24 cell copies (AST, comments and formatting ignored) there were only two behaviours: with or without Sentry `capture` on a failed inline publish.

## Changed in Wave 2 (2026-10-22)

- Strict typing (mypy strict on `cellkit.*` except the contract suite) and Ruff fixes; no behaviour change.
- `ranges` resource key: a write that leaves `[start, end]` both set must keep start <= end (422 `invalid_value`); only a patch that changes one of them is checked. No schema change.
- Integers are bounded to their column (`int` = 32-bit, `bigint`/`ref` = 64-bit) and real fields refuse NaN/Infinity: 422 instead of a 500 or a silent NULL. The 422 handler makes such inputs JSON-safe.
- A failed inline publish is passed to Sentry `capture()` as well as logged.
- Contract tests for each of these (`src/cellkit/contract.py`).

Commits touching `src/cellkit/` or `cell.yaml`:

- `e7979b3 fix: refuse integers past their column and NaN/Infinity reals with 422`
- `1f1cefc test: integers past their column and non-finite reals must be refused with 422 (red)`
- `5088683 chore: L2 baseline; goal periods must not end before they start; inline publish failures reach Sentry`

## Fixes per need of this cell

| Fix | Does this cell need it? | Evidence |
|---|---|---|
| Inline publish failure → Sentry | yes: graph events on `goal`, `goal-task` | 35cf9e7 (origin/main) + this test only · `.venv/bin/pytest -q -k inline_publish tests/test_contract.py` · `assert captured` → `AssertionError` (nothing captured) |
| `ranges` rule | yes: `goal-metric` period_start..period_end, `productivity-goal` period_start..period_end | 39637d3 · `.venv/bin/pytest -q tests/test_goals_validation.py::test_a_metric_period_cannot_end_before_it_starts` · `assert 201 == 422` |
| Column limits / finite reals | yes: `goal-portfolio-mapping.attention_cost`, `goal-task.priority`, `goal-task.progress_percent`, `goal-task.sort_order`, `goal.priority`, `goal.progress_percent`, `goal-context-link.weight`, `goal-metric.baseline_value` … | 1f1cefc · `.venv/bin/pytest -q -k numbers_fit` · `psycopg.errors.NumericValueOutOfRange: integer out of range` |

## Deliberately not applied

- Range not declared: `goal.start_date`/`due_date`: 415 rows were imported and some may already be inverted; left for an owner decision.
- No other fix was skipped: no cell copy had a fix this one lacks after Wave 2, and there were no domain-specific differences to keep (the other differences were comments and formatting).

Change this code here, with a failing test first (ADR-0004). Records: `specs/` (SPEC-001 red/green log).
