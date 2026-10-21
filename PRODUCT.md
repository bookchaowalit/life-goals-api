# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through `life-dashboard-web` (the `/goals` page, `EMPIRE_GOALS_API`), the
  cell's own MCP server (`goals-mcp`, tools `goals.<resource>.list|get|create|update|delete`) and
  the hosted tool hub (`platform-mcp-remote-worker`, which lists this cell's origin).
- Local owner tooling that reads cells through the registry client: `ops-toolkit`
  (`infra/scripts/utils/cell_store.py`) and `mcp-aggregator` (`src/cell-store.ts`).
- Other cells that point at a goal by its id (plain numbers, not foreign keys): `life-projects-api`
  (`goal_id`, `goal_task_id`), `life-operating-cycles-api` (`goal_id` on its goal links) and
  `life-roles-skills-api` (`goal_id`).
- Automations with an `empire-platform` token (for example `owner-mcp`, `solo-web`), within the
  permissions `goals.<resource>:read|write|delete` for each of the eight resources below.

## Product Purpose

The owner's register of goals: goals and their tasks, the metrics that measure a goal, the portfolio
bucket and attention class each goal is mapped to, personal productivity targets, and links from
goals and tasks to the projects and contexts that deliver them (`life-projects-api`).
Work done in projects can then be traced back to a goal.

Success: every active goal exists once with its tasks and measurable key results, each goal has at
most one portfolio mapping, and every link to a project or context is unique.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes. Goals and
goal tasks publish graph events (see below).

## Operating Context

- Production: `https://goals-api-production-c16e.up.railway.app` (`/health`), deployed by merging
  to `main` after CI. A second service, `goals-publisher` (Railway cron, every 15 minutes),
  sweeps the outbox and sends graph events to `empire-platform`.
- Data was imported from the old SQLite tables on 2026-10-10 keeping ids in `legacy_id` (415 rows
  at that time, per the registry); imports through the API keep the old id.
- Monitored by `platform-uptime-worker` (`goals-api`); errors go to Sentry when `SENTRY_DSN` is set.
- Graph events: `goals.goal.*` carries `title`, `status`, `type`, `category`, `domain`;
  `goals.goal-task.*` carries `title`, `status`, `goal_id`. That the events arrive in the graph is
  [ต้องยืนยัน] (the product card lists it as an open check).

## Capabilities and Constraints

- Every resource has list, stats, get, get-by-legacy-id, create (with `Idempotency-Key`), patch
  (with `expected_version`) and delete.
  - `/v1/goals`: filters `status`, `type`, `category`, `domain`, `priority`.
  - `/v1/goal-tasks`: filters `goal_id`, `status`, `priority`; listed by `sort_order`, then id.
  - `/v1/goal-metrics`: filters `goal_id`, `status`, `metric_type`.
  - `/v1/goal-portfolio-mappings`: filters `goal_id`, `portfolio_bucket`, `attention_class`,
    `current_season`, `collision_group`, `canonical_goal`.
  - `/v1/productivity-goals`: filters `goal_type`, `is_active`.
  - `/v1/goal-project-links`, `/v1/goal-context-links`: filters `goal_id`, `project_id` or
    `context_id`, `relation_type`.
  - `/v1/goal-task-project-links`: filters `goal_task_id`, `project_id`, `relation_type`.
- Rules tested:
  - Titles and names are required, not empty and at most 500 characters (goal `domain` 200,
    metric `unit` 60, link `source` 200); enums (`type`, `category`, `status`, metric and mapping
    classes, link relations) are fixed lists, and the link relations differ per link kind.
  - `progress_percent` is 0 to 100 on goals and tasks, `attention_cost` is 0 to 5, a link `weight`
    is above 0; task `priority` is a number (low, medium and high exist only in the importer).
  - A task's `goal_id`, a metric's `goal_id`, a mapping's `goal_id` and `canonical_goal_id`, and
    each link's goal or task must exist in the same workspace (422 `reference_not_found`); a goal or
    task that others still point at cannot be deleted (409 `has_dependents`).
  - Unique: a metric key per goal, one portfolio mapping per goal, and one link per goal and
    project, per goal and context, and per task and project (409). Goals and tasks may share titles.
  - A metric or productivity goal cannot have `period_end` before `period_start` (422
    `invalid_value`, on create and on patch); the same day is allowed.
  - Defaults: a goal is `planning` with priority 3 and progress 0; a task is `todo`; a metric is a
    manual key result that should increase, unit `count`, status `no_data`; a mapping is
    `provisional` with attention cost 0; a productivity goal is active with current value 0; a link
    has weight 1 and source `manual`.
  - `stats` groups only by a filter; any other `group_by` is a 422.
- `project_id` and `context_id` are plain numbers for `life-projects-api` (per the `cell.yaml`
  comment); they are not checked against that cell.
- Goal `start_date` and `due_date` have no ordering rule; `priority` has no range. Two known gaps
  in the shared service code are covered by expected-failure tests: a value above 2147483647 in an
  integer field ends in a server error instead of a 422, and a `NaN` or `Infinity` in a real field
  (for example `target_value`) is accepted and read back as `null`.
- Out of scope: computing progress or metric status from tasks or telemetry, and the projects
  themselves.

## Measures

Proposed (nothing collects them yet):

- Active goals with at least one metric and one linked project.
- Goals without a portfolio mapping (target: 0 for active goals).
- Tasks reaching `done` per week.
- 5xx rate and p95 latency on `/v1/goals` (Sentry and uptime worker); age of the oldest unpublished
  outbox row.
