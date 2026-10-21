# life-goals-api
The Goals cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `life-goals-api`, service `goals-api` (Serverless) |
| Publisher | service `goals-publisher` (Railway cron, `*/15 * * * *`) |
| Data | Neon project `life-goals-api`, database `goals` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`goals`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `goals.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/goals` | goal | `status`, `type`, `category`, `domain`, `priority` |
| `/v1/goal-tasks` | goal-task | `goal_id`, `status`, `priority` |
| `/v1/goal-metrics` | goal-metric | `goal_id`, `status`, `metric_type` |
| `/v1/goal-portfolio-mappings` | goal-portfolio-mapping | `goal_id`, `portfolio_bucket`, `attention_class`, `current_season`, `collision_group`, `canonical_goal` |
| `/v1/productivity-goals` | productivity-goal | `goal_type`, `is_active` |
| `/v1/goal-project-links` | goal-project-link | `goal_id`, `project_id`, `relation_type` |
| `/v1/goal-context-links` | goal-context-link | `goal_id`, `context_id`, `relation_type` |
| `/v1/goal-task-project-links` | goal-task-project-link | `goal_task_id`, `project_id`, `relation_type` |

## Develop and operate

```bash
uv sync --frozen --all-extras          # Python 3.12 (.python-version): pgserver has no cp313 wheel yet
.venv/bin/pytest -q
.venv/bin/mypy . && uvx ruff@0.17.1 check . && uvx ruff@0.17.1 format --check .   # the same checks CI runs
NEON_API_KEY=... .venv/bin/goals-db provision
npm install && railway config apply   # service settings only; code deploys from GitHub (below)
```

Dependencies are locked in `uv.lock`; the image installs them with `uv sync --frozen`, so
production runs the versions CI tested. Change a dependency with `uv add`/`uv lock` and commit
the lock. Product scope and measures: [PRODUCT.md](PRODUCT.md); change records: `specs/`.

Deploys (CD, since 2026-10-18): `goals-api` and `goals-publisher` are connected to this
repository's `main` with Railway's Wait for CI (`checkSuites`). A merge to `main` deploys only
after the CI and security checks pass; a failing check leaves production on the previous
deployment. Roll back by redeploying an earlier deployment in Railway. `railway up` is no
longer used.

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see
`src/cellkit/_sentry.py`), `GOALS_DB_MODE=hosted`, `GOALS_DB_URL_API`,
`GOALS_JWT_PUBLIC_KEY_PEM`, `GOALS_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`, and for the publisher `GOALS_DB_URL_PUBLISHER` and `GOALS_PUBLISHER_TOKEN`.
