"""Defaults, uniqueness and imports of the goals cell."""

from datetime import UTC, datetime

from goals_helpers import (
    GOALS,
    MAPPINGS,
    METRICS,
    TASKS,
    create_goal,
    create_goal_context_link,
    create_goal_project_link,
    create_mapping,
    create_metric,
    create_productivity_goal,
    create_task,
    create_task_project_link,
)

# --- defaults -----------------------------------------------------------------------------------


def test_a_new_goal_is_planning_with_priority_3_and_no_progress(client, owner):
    response = create_goal(client, owner, title="Learn Rust")
    assert response.status_code == 201, response.text
    goal = response.json()
    assert goal["status"] == "planning"
    assert goal["priority"] == 3
    assert goal["progress_percent"] == 0
    assert goal["type"] is None
    assert goal["category"] is None
    assert goal["version"] == 1


def test_a_new_task_is_todo_and_does_not_need_a_goal(client, owner):
    response = create_task(client, owner, title="Loose task")
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["status"] == "todo"
    assert task["priority"] == 3
    assert task["sort_order"] == 0
    assert task["progress_percent"] == 0
    assert task["goal_id"] is None
    assert task["version"] == 1


def test_a_new_metric_is_a_manual_key_result_that_should_increase(client, owner):
    goal = create_goal(client, owner).json()
    response = create_metric(client, owner, goal["id"])
    assert response.status_code == 201, response.text
    metric = response.json()
    assert metric["metric_type"] == "key_result"
    assert metric["direction"] == "increase"
    assert metric["unit"] == "count"
    assert metric["status"] == "no_data"
    assert metric["source_type"] == "manual"
    assert metric["current_value"] is None
    assert metric["target_value"] == 1000.0


def test_a_new_mapping_is_provisional_with_no_attention_cost(client, owner):
    goal = create_goal(client, owner).json()
    response = create_mapping(client, owner, goal["id"])
    assert response.status_code == 201, response.text
    mapping = response.json()
    assert mapping["mapping_confidence"] == "provisional"
    assert mapping["mapping_source"] == "goal-portfolio-rule-v1"
    assert mapping["attention_cost"] == 0
    assert mapping["canonical_goal_id"] is None


def test_a_new_productivity_goal_is_active_and_starts_at_zero(client, owner):
    response = create_productivity_goal(client, owner)
    assert response.status_code == 201, response.text
    goal = response.json()
    assert goal["is_active"] is True
    assert goal["current_value"] == 0
    assert goal["period_start"] is None


def test_new_links_are_full_weight_manual_links(client, owner):
    goal = create_goal(client, owner).json()
    task = create_task(client, owner).json()
    project_link = create_goal_project_link(client, owner, goal["id"]).json()
    context_link = create_goal_context_link(client, owner, goal["id"]).json()
    task_link = create_task_project_link(client, owner, task["id"]).json()
    assert project_link["relation_type"] == "delivery"
    assert context_link["relation_type"] == "primary"
    assert task_link["relation_type"] == "delivery"
    for link in (project_link, context_link, task_link):
        assert link["weight"] == 1
        assert link["source"] == "manual"


# --- uniqueness ---------------------------------------------------------------------------------


def test_a_metric_key_is_unique_within_a_goal(client, owner):
    goal = create_goal(client, owner).json()
    other = create_goal(client, owner, title="Other goal").json()
    assert create_metric(client, owner, goal["id"], metric_key="mrr").status_code == 201
    assert create_metric(client, owner, goal["id"], metric_key="mrr").status_code == 409
    assert create_metric(client, owner, goal["id"], metric_key="arr").status_code == 201
    assert (
        create_metric(client, owner, other["id"], metric_key="mrr").status_code == 201
    )


def test_a_metric_cannot_take_a_key_its_goal_already_uses(client, owner):
    goal = create_goal(client, owner).json()
    create_metric(client, owner, goal["id"], metric_key="mrr")
    second = create_metric(client, owner, goal["id"], metric_key="arr").json()
    taken = client.patch(
        f"{METRICS}/{second['id']}", headers=owner, json={"metric_key": "mrr"}
    )
    assert taken.status_code == 409


def test_a_goal_has_at_most_one_portfolio_mapping(client, owner):
    goal = create_goal(client, owner).json()
    other = create_goal(client, owner, title="Other goal").json()
    assert create_mapping(client, owner, goal["id"]).status_code == 201
    assert (
        create_mapping(client, owner, goal["id"], collision_group="other").status_code
        == 409
    )
    assert create_mapping(client, owner, other["id"]).status_code == 201


def test_a_goal_is_linked_to_a_project_only_once(client, owner):
    goal = create_goal(client, owner).json()
    other = create_goal(client, owner, title="Other goal").json()
    assert create_goal_project_link(client, owner, goal["id"], 9001).status_code == 201
    assert create_goal_project_link(client, owner, goal["id"], 9001).status_code == 409
    assert create_goal_project_link(client, owner, goal["id"], 9002).status_code == 201
    assert create_goal_project_link(client, owner, other["id"], 9001).status_code == 201


def test_a_goal_is_linked_to_a_context_only_once(client, owner):
    goal = create_goal(client, owner).json()
    other = create_goal(client, owner, title="Other goal").json()
    assert create_goal_context_link(client, owner, goal["id"], 7001).status_code == 201
    assert create_goal_context_link(client, owner, goal["id"], 7001).status_code == 409
    assert create_goal_context_link(client, owner, goal["id"], 7002).status_code == 201
    assert create_goal_context_link(client, owner, other["id"], 7001).status_code == 201


def test_a_task_is_linked_to_a_project_only_once(client, owner):
    task = create_task(client, owner).json()
    other = create_task(client, owner, title="Other task").json()
    assert create_task_project_link(client, owner, task["id"], 9001).status_code == 201
    assert create_task_project_link(client, owner, task["id"], 9001).status_code == 409
    assert create_task_project_link(client, owner, task["id"], 9002).status_code == 201
    assert create_task_project_link(client, owner, other["id"], 9001).status_code == 201


def test_goals_tasks_and_productivity_goals_may_share_titles(client, owner):
    assert create_goal(client, owner, title="Same").status_code == 201
    assert create_goal(client, owner, title="Same").status_code == 201
    assert create_task(client, owner, title="Same").status_code == 201
    assert create_task(client, owner, title="Same").status_code == 201
    assert create_productivity_goal(client, owner, name="Same").status_code == 201
    assert create_productivity_goal(client, owner, name="Same").status_code == 201


# --- imports keep their old ids -----------------------------------------------------------------


def test_an_imported_goal_keeps_its_old_id_and_tasks_can_point_at_it(client, owner):
    goal = create_goal(client, owner, title="Old goal", legacy_id=501)
    assert goal.status_code == 201, goal.text
    assert goal.json()["id"] == 501
    task = create_task(client, owner, title="Old task", legacy_id=9001, goal_id=501)
    assert task.status_code == 201, task.text
    assert (task.json()["id"], task.json()["goal_id"]) == (9001, 501)
    found = client.get(f"{GOALS}/legacy/501", headers=owner)
    assert found.status_code == 200
    assert found.json()["title"] == "Old goal"
    assert client.get(f"{TASKS}/legacy/9001", headers=owner).json()["goal_id"] == 501
    assert create_goal(client, owner, legacy_id=501).status_code == 409


def test_a_mapping_is_imported_under_the_id_of_its_goal(client, owner):
    goal = create_goal(client, owner, title="Mapped goal", legacy_id=777).json()
    mapping = create_mapping(client, owner, goal["id"], legacy_id=777)
    assert mapping.status_code == 201, mapping.text
    assert mapping.json()["id"] == 777
    found = client.get(f"{MAPPINGS}/legacy/777", headers=owner)
    assert found.status_code == 200
    assert found.json()["goal_id"] == 777


def test_old_timestamps_are_accepted_only_on_import(client, owner):
    stamped = create_goal(client, owner, created_at="2024-01-02T03:04:05+00:00")
    assert stamped.status_code == 422, stamped.text
    imported = create_goal(
        client, owner, legacy_id=502, created_at="2024-01-02T03:04:05+00:00"
    )
    assert imported.status_code == 201, imported.text
    kept = datetime.fromisoformat(imported.json()["created_at"])
    assert kept == datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_a_priority_above_the_integer_range_is_refused_not_a_server_error(
    client, owner
):
    assert create_goal(client, owner, priority=2**31).status_code == 422
