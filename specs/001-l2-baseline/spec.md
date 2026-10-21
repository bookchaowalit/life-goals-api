# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/life-goals-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, the only tests were the generic contract suite, and the API stored goal metrics and productivity goals whose period_end is before period_start; a failed inline publish was logged but never reached Sentry; integers above 2147483647 end in a server error and NaN or Infinity in a real field is stored and read back as null.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — A metric period cannot end before it starts

- **Given** a goal and an owner with write permission
- **When** they create a metric with `period_start` 2026-10-31 and `period_end` 2026-10-01
- **Then** the API answers 422 `invalid_value` naming both fields; the same day for both is accepted
- **Test:** `tests/test_goals_validation.py::test_a_metric_period_cannot_end_before_it_starts` · level: integration (API + throwaway PostgreSQL)

### AC-02 — Moving a metric period end before its start is refused

- **Given** a metric whose period starts 2026-10-10
- **When** a patch sets `period_end` to 2026-10-01
- **Then** the API answers 422 and the stored `period_end` stays empty; a patch that touches neither date still succeeds
- **Test:** `tests/test_goals_validation.py::test_moving_a_metric_period_end_before_its_start_is_refused_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-03 — A productivity period cannot end before it starts

- **Given** an owner with write permission
- **When** they create a productivity goal with `period_start` 2026-11-01 and `period_end` 2026-10-01, or patch the end before the start
- **Then** the API answers 422 `invalid_value` naming both fields and leaves the stored record unchanged; the same day is accepted
- **Test:** `tests/test_goals_validation.py::test_a_productivity_period_cannot_end_before_it_starts` · level: integration (API + throwaway PostgreSQL)

### AC-04 — References must resolve inside the workspace

- **Given** tasks, metrics, mappings and links that point at a goal or task
- **When** the id is missing or belongs to another workspace
- **Then** the API answers 422 `reference_not_found`; deleting a goal or task that is still referenced answers 409 `has_dependents`
- **Test:** `tests/test_goals_validation.py::test_a_task_cannot_belong_to_a_goal_of_another_workspace` · level: integration (API + throwaway PostgreSQL)

### AC-05 — Bounds and lengths are enforced

- **Given** goals, tasks, mappings and links
- **When** progress is outside 0-100, attention cost outside 0-5, a link weight is 0, or a title exceeds 500 characters
- **Then** the API answers 422; the boundary values are accepted
- **Test:** `tests/test_goals_validation.py::test_goal_progress_is_between_0_and_100` · level: integration (API + throwaway PostgreSQL)

### AC-06 — Metric keys, mappings and links are unique

- **Given** a goal with a metric `mrr`, a mapping and a project link
- **When** the same metric key, a second mapping, or the same project link is created for that goal
- **Then** each answers 409; the same key on another goal, another project, or another goal's link is still allowed
- **Test:** `tests/test_goals_defaults.py::test_a_metric_key_is_unique_within_a_goal` · level: integration (API + throwaway PostgreSQL)

### AC-07 — Imported goals keep their old ids

- **Given** a goal created with `legacy_id` 501 and a mapping with `legacy_id` 777 for goal 777
- **When** a task points at goal 501 and the legacy routes are read
- **Then** ids equal the legacy ids, the task resolves its goal, and a repeated legacy id answers 409
- **Test:** `tests/test_goals_defaults.py::test_an_imported_goal_keeps_its_old_id_and_tasks_can_point_at_it` · level: integration (API + throwaway PostgreSQL)

### AC-08 — Tasks are listed by sort order and stats follow the filters

- **Given** tasks with sort_order 3, 1, 2, 2
- **When** the owner lists tasks and asks for stats by `status` or by a non-filter field
- **Then** tasks come back by sort_order then id, stats count per status, and a non-filter field is refused with 422
- **Test:** `tests/test_goals_queries.py::test_tasks_are_listed_by_sort_order_then_id` · level: integration (API + throwaway PostgreSQL)

### AC-09 — A failed inline publish reaches Sentry

- **Given** a resource with graph events and a publisher token, and a publisher that raises
- **When** a record is created
- **Then** the request still succeeds (the cron sweep retries) and the error is passed to Sentry `capture()`; before the fix it was only logged
- **Test:** `tests/test_contract.py::test_inline_publish_failure_is_reported` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `POST /v1/goal-metrics`, `PATCH /v1/goal-metrics/{id}`, `POST /v1/productivity-goals`, `PATCH /v1/productivity-goals/{id}` | changed | `period_end` before `period_start` → `422 {"error": "invalid_value", "fields": ["period_end", "period_start"]}` |
| `cell.yaml` | changed | new resource key `ranges: [[period_start, period_end]]` on `goal-metric` and `productivity-goal` |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "60"` (measured 62.96% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_goals_validation.py::test_a_metric_period_cannot_end_before_it_starts` | 39637d3 · `.venv/bin/pytest -q tests/test_goals_validation.py::test_a_metric_period_cannot_end_before_it_starts` · `assert 201 == 422` | CI run of the pushed tip | none |
| AC-02 | `tests/test_goals_validation.py::test_moving_a_metric_period_end_before_its_start_is_refused_on_update` | 39637d3 · `.venv/bin/pytest -q tests/test_goals_validation.py::test_moving_a_metric_period_end_before_its_start_is_refused_on_update` · `assert 200 == 422` | CI run of the pushed tip | none |
| AC-03 | `tests/test_goals_validation.py::test_a_productivity_period_cannot_end_before_it_starts` | 39637d3 · `.venv/bin/pytest -q tests/test_goals_validation.py::test_a_productivity_period_cannot_end_before_it_starts` · `assert 201 == 422` | CI run of the pushed tip | none |
| AC-04 | `tests/test_goals_validation.py::test_a_task_cannot_belong_to_a_goal_of_another_workspace` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_goals_validation.py::test_goal_progress_is_between_0_and_100` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_goals_defaults.py::test_a_metric_key_is_unique_within_a_goal` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_goals_defaults.py::test_an_imported_goal_keeps_its_old_id_and_tasks_can_point_at_it` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_goals_queries.py::test_tasks_are_listed_by_sort_order_then_id` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-09 | `tests/test_contract.py::test_inline_publish_failure_is_reported` | 35cf9e7 (origin/main) + this test only · `.venv/bin/pytest -q -k inline_publish tests/test_contract.py` · `assert captured` → `AssertionError` (nothing captured) | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |
