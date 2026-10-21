"""Shared helpers for the goals domain tests."""

import uuid
from typing import Any

GOALS = "/v1/goals"
TASKS = "/v1/goal-tasks"
METRICS = "/v1/goal-metrics"
MAPPINGS = "/v1/goal-portfolio-mappings"
PRODUCTIVITY = "/v1/productivity-goals"
PROJECT_LINKS = "/v1/goal-project-links"
CONTEXT_LINKS = "/v1/goal-context-links"
TASK_PROJECT_LINKS = "/v1/goal-task-project-links"


def create_goal(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    return client.post(GOALS, headers=owner, json={"title": "Ship the MVP", **fields})


def create_task(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    return client.post(TASKS, headers=owner, json={"title": "Write the spec", **fields})


def create_metric(
    client: Any, owner: dict[str, str], goal_id: int, **fields: Any
) -> Any:
    body = {
        "goal_id": goal_id,
        "metric_key": "revenue",
        "name": "Monthly revenue",
        "target_value": 1000.0,
    }
    return client.post(METRICS, headers=owner, json={**body, **fields})


def create_mapping(
    client: Any, owner: dict[str, str], goal_id: int, **fields: Any
) -> Any:
    body = {
        "goal_id": goal_id,
        "portfolio_bucket": "active_bet",
        "attention_class": "focus",
        "collision_group": "income",
        "canonical_goal": "Grow income",
        "current_season": "2026-Q4",
    }
    return client.post(MAPPINGS, headers=owner, json={**body, **fields})


def create_productivity_goal(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {
        "name": "Finish tasks",
        "goal_type": "daily_completions",
        "target_value": 5.0,
    }
    return client.post(PRODUCTIVITY, headers=owner, json={**body, **fields})


def create_goal_project_link(
    client: Any,
    owner: dict[str, str],
    goal_id: int,
    project_id: int = 9001,
    **fields: Any,
) -> Any:
    body = {"goal_id": goal_id, "project_id": project_id}
    return client.post(PROJECT_LINKS, headers=owner, json={**body, **fields})


def create_goal_context_link(
    client: Any,
    owner: dict[str, str],
    goal_id: int,
    context_id: int = 7001,
    **fields: Any,
) -> Any:
    body = {"goal_id": goal_id, "context_id": context_id}
    return client.post(CONTEXT_LINKS, headers=owner, json={**body, **fields})


def create_task_project_link(
    client: Any,
    owner: dict[str, str],
    goal_task_id: int,
    project_id: int = 9001,
    **fields: Any,
) -> Any:
    body = {"goal_task_id": goal_task_id, "project_id": project_id}
    return client.post(TASK_PROJECT_LINKS, headers=owner, json={**body, **fields})


def another_workspace(harness: Any, platform: Any) -> dict[str, str]:
    """Headers of a second owner in a different workspace, with every permission."""
    actor, workspace = uuid.uuid4(), uuid.uuid4()
    platform.grants[actor] = set(harness.cell.permissions())
    headers: dict[str, str] = harness.token(actor, workspace)
    return headers
