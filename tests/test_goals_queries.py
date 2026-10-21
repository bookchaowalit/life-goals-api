"""Listing, grouping and lifecycle of the goals resources."""

from datetime import UTC, datetime

from goals_helpers import (
    CONTEXT_LINKS,
    GOALS,
    MAPPINGS,
    METRICS,
    PRODUCTIVITY,
    PROJECT_LINKS,
    TASK_PROJECT_LINKS,
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


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def listed(client, owner, path, **params):
    return ids(client.get(path, headers=owner, params=params))


# --- goals --------------------------------------------------------------------------------------


def test_goals_filter_by_status_type_category_domain_and_priority(client, owner):
    plan = create_goal(
        client, owner, type="yearly", category="business", domain="income", priority=1
    ).json()
    habit = create_goal(
        client, owner, type="weekly", category="health", status="active", domain="body"
    ).json()
    assert listed(client, owner, GOALS, status="active") == [habit["id"]]
    assert listed(client, owner, GOALS, type="yearly") == [plan["id"]]
    assert listed(client, owner, GOALS, category="health") == [habit["id"]]
    assert listed(client, owner, GOALS, domain="income") == [plan["id"]]
    assert listed(client, owner, GOALS, priority=1) == [plan["id"]]
    assert listed(client, owner, GOALS, status="active", category="business") == []


def test_goals_cannot_be_listed_by_a_field_that_is_not_a_filter(client, owner):
    refused = client.get(GOALS, headers=owner, params={"title": "x"})
    assert refused.status_code == 422
    assert refused.json()["detail"]["error"] == "unknown_filter"


def test_a_filter_with_an_unknown_enum_value_is_refused(client, owner):
    assert (
        client.get(GOALS, headers=owner, params={"status": "done"}).status_code == 422
    )


def test_stats_count_goals_per_status_and_per_category(client, owner):
    create_goal(client, owner, category="tech")
    create_goal(client, owner, category="tech", status="active")
    create_goal(client, owner, category="life", status="active")
    by_status = client.get(
        f"{GOALS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert by_status.status_code == 200, by_status.text
    assert by_status.json()["groups"] == {"planning": 1, "active": 2}
    by_category = client.get(
        f"{GOALS}/stats", headers=owner, params={"group_by": "category"}
    )
    assert by_category.json()["groups"] == {"tech": 2, "life": 1}


def test_stats_can_be_narrowed_by_another_filter(client, owner):
    create_goal(client, owner, category="tech", status="active")
    create_goal(client, owner, category="life", status="active")
    stats = client.get(
        f"{GOALS}/stats",
        headers=owner,
        params={"group_by": "status", "category": "tech"},
    )
    assert stats.json()["groups"] == {"active": 1}


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    for path in (
        GOALS,
        TASKS,
        METRICS,
        MAPPINGS,
        PRODUCTIVITY,
        PROJECT_LINKS,
        CONTEXT_LINKS,
        TASK_PROJECT_LINKS,
    ):
        stats = client.get(
            f"{path}/stats", headers=owner, params={"group_by": "version"}
        )
        assert stats.status_code == 422, path


def test_goals_are_listed_oldest_first_and_newest_first_on_request(client, owner):
    first = create_goal(client, owner, title="First").json()
    second = create_goal(client, owner, title="Second").json()
    assert listed(client, owner, GOALS) == [first["id"], second["id"]]
    assert listed(client, owner, GOALS, order="desc") == [second["id"], first["id"]]


def test_a_goal_progresses_through_its_life(client, owner):
    goal = create_goal(client, owner, title="Launch").json()
    path = f"{GOALS}/{goal['id']}"
    started = client.patch(
        path, headers=owner, json={"status": "active", "progress_percent": 40}
    )
    assert started.status_code == 200, started.text
    assert started.json()["version"] == 2
    finished = client.patch(
        path,
        headers=owner,
        json={
            "status": "completed",
            "progress_percent": 100,
            "completed_at": "2026-10-20T10:00:00+00:00",
        },
    )
    assert finished.json()["version"] == 3
    assert finished.json()["title"] == "Launch"
    assert (
        client.patch(path, headers=owner, json={"progress_percent": 101}).status_code
        == 422
    )
    assert client.get(path, headers=owner).json()["version"] == 3


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    goal = create_goal(client, owner, status="active").json()
    path = f"{GOALS}/{goal['id']}"
    same = client.patch(path, headers=owner, json={"status": "active", "priority": 3})
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1
    assert same.json()["updated_at"] == goal["updated_at"]


def test_a_stale_expected_version_is_refused(client, owner):
    goal = create_goal(client, owner).json()
    path = f"{GOALS}/{goal['id']}"
    assert client.patch(path, headers=owner, json={"priority": 1}).status_code == 200
    stale = client.patch(
        path, headers=owner, json={"priority": 2, "expected_version": 1}
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == {"error": "version_conflict", "version": 2}


def test_a_deleted_goal_is_gone(client, owner):
    goal = create_goal(client, owner).json()
    path = f"{GOALS}/{goal['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.delete(path, headers=owner).status_code == 404


# --- tasks --------------------------------------------------------------------------------------


def test_tasks_are_listed_by_sort_order_then_id(client, owner):
    third = create_task(client, owner, title="Third", sort_order=3).json()
    first = create_task(client, owner, title="First", sort_order=1).json()
    tie_a = create_task(client, owner, title="Tie A", sort_order=2).json()
    tie_b = create_task(client, owner, title="Tie B", sort_order=2).json()
    assert listed(client, owner, TASKS) == [
        first["id"],
        tie_a["id"],
        tie_b["id"],
        third["id"],
    ]
    newest_first = listed(client, owner, TASKS, order="desc")
    assert newest_first == [third["id"], tie_b["id"], tie_a["id"], first["id"]]


def test_tasks_filter_by_goal_status_and_priority(client, owner):
    goal = create_goal(client, owner).json()
    mine = create_task(
        client, owner, goal_id=goal["id"], status="in_progress", priority=1
    ).json()
    create_task(client, owner, status="done", priority=2)
    assert listed(client, owner, TASKS, goal_id=goal["id"]) == [mine["id"]]
    assert listed(client, owner, TASKS, status="in_progress") == [mine["id"]]
    assert listed(client, owner, TASKS, priority=1) == [mine["id"]]
    assert (
        client.get(TASKS, headers=owner, params={"priority": "high"}).status_code == 422
    )


def test_tasks_without_a_goal_can_be_listed(client, owner):
    goal = create_goal(client, owner).json()
    create_task(client, owner, goal_id=goal["id"])
    loose = create_task(client, owner, title="Loose").json()
    orphans = client.get(TASKS, headers=owner, params={"null": "goal_id"})
    assert ids(orphans) == [loose["id"]]


def test_stats_count_tasks_per_status_and_per_goal(client, owner):
    goal = create_goal(client, owner).json()
    create_task(client, owner, goal_id=goal["id"], status="done")
    create_task(client, owner, goal_id=goal["id"], status="done")
    create_task(client, owner, goal_id=goal["id"])
    by_status = client.get(
        f"{TASKS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert by_status.json()["groups"] == {"done": 2, "todo": 1}
    by_goal = client.get(
        f"{TASKS}/stats", headers=owner, params={"group_by": "goal_id"}
    )
    assert by_goal.json()["groups"] == {str(goal["id"]): 3}


def test_a_task_is_completed_with_a_timestamp(client, owner):
    task = create_task(client, owner).json()
    path = f"{TASKS}/{task['id']}"
    done = client.patch(
        path,
        headers=owner,
        json={
            "status": "done",
            "progress_percent": 100,
            "completed_at": "2026-10-21T09:30:00+00:00",
        },
    )
    assert done.status_code == 200, done.text
    assert done.json()["version"] == 2
    completed = datetime.fromisoformat(done.json()["completed_at"])
    assert completed == datetime(2026, 10, 21, 9, 30, tzinfo=UTC)


def test_a_goal_with_tasks_cannot_be_deleted(client, owner):
    goal = create_goal(client, owner).json()
    task = create_task(client, owner, goal_id=goal["id"]).json()
    refused = client.delete(f"{GOALS}/{goal['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == {"error": "has_dependents"}
    assert client.delete(f"{TASKS}/{task['id']}", headers=owner).status_code == 204
    assert client.delete(f"{GOALS}/{goal['id']}", headers=owner).status_code == 204


# --- metrics ------------------------------------------------------------------------------------


def test_metrics_filter_by_goal_status_and_type(client, owner):
    goal = create_goal(client, owner).json()
    other = create_goal(client, owner, title="Other").json()
    kpi = create_metric(
        client, owner, goal["id"], metric_key="a", metric_type="kpi"
    ).json()
    guard = create_metric(
        client,
        owner,
        other["id"],
        metric_key="b",
        metric_type="guardrail",
        status="at_risk",
    ).json()
    assert listed(client, owner, METRICS, goal_id=goal["id"]) == [kpi["id"]]
    assert listed(client, owner, METRICS, metric_type="guardrail") == [guard["id"]]
    assert listed(client, owner, METRICS, status="at_risk") == [guard["id"]]
    stats = client.get(
        f"{METRICS}/stats", headers=owner, params={"group_by": "metric_type"}
    )
    assert stats.json()["groups"] == {"kpi": 1, "guardrail": 1}


def test_a_metric_reading_moves_it_to_achieved(client, owner):
    goal = create_goal(client, owner).json()
    metric = create_metric(
        client, owner, goal["id"], baseline_value=0, target_value=50
    ).json()
    path = f"{METRICS}/{metric['id']}"
    reading = client.patch(
        path, headers=owner, json={"current_value": 50, "status": "achieved"}
    )
    assert reading.status_code == 200, reading.text
    assert reading.json()["version"] == 2
    assert reading.json()["baseline_value"] == 0
    assert reading.json()["current_value"] == 50


def test_a_goal_with_metrics_cannot_be_deleted(client, owner):
    goal = create_goal(client, owner).json()
    metric = create_metric(client, owner, goal["id"]).json()
    refused = client.delete(f"{GOALS}/{goal['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert client.delete(f"{METRICS}/{metric['id']}", headers=owner).status_code == 204
    assert client.delete(f"{GOALS}/{goal['id']}", headers=owner).status_code == 204


# --- portfolio mappings -------------------------------------------------------------------------


def test_mappings_filter_by_bucket_class_season_group_and_goal(client, owner):
    goal = create_goal(client, owner).json()
    other = create_goal(client, owner, title="Other").json()
    focus = create_mapping(client, owner, goal["id"]).json()
    option = create_mapping(
        client,
        owner,
        other["id"],
        portfolio_bucket="option_portfolio",
        attention_class="option",
        collision_group="side",
        canonical_goal="Try things",
        current_season="2027-Q1",
    ).json()
    assert listed(client, owner, MAPPINGS, goal_id=goal["id"]) == [focus["id"]]
    assert listed(client, owner, MAPPINGS, portfolio_bucket="option_portfolio") == [
        option["id"]
    ]
    assert listed(client, owner, MAPPINGS, attention_class="focus") == [focus["id"]]
    assert listed(client, owner, MAPPINGS, current_season="2027-Q1") == [option["id"]]
    assert listed(client, owner, MAPPINGS, collision_group="income") == [focus["id"]]
    assert listed(client, owner, MAPPINGS, canonical_goal="Try things") == [
        option["id"]
    ]
    stats = client.get(
        f"{MAPPINGS}/stats", headers=owner, params={"group_by": "portfolio_bucket"}
    )
    assert stats.json()["groups"] == {"active_bet": 1, "option_portfolio": 1}


def test_a_mapping_can_name_another_goal_as_the_canonical_one(client, owner):
    goal = create_goal(client, owner).json()
    canonical = create_goal(client, owner, title="Canonical").json()
    mapping = create_mapping(
        client, owner, goal["id"], canonical_goal_id=canonical["id"]
    )
    assert mapping.status_code == 201, mapping.text
    assert mapping.json()["canonical_goal_id"] == canonical["id"]
    refused = client.delete(f"{GOALS}/{canonical['id']}", headers=owner)
    assert refused.status_code == 409, refused.text


def test_a_mapping_is_reviewed_and_its_confidence_raised(client, owner):
    goal = create_goal(client, owner).json()
    mapping = create_mapping(client, owner, goal["id"]).json()
    path = f"{MAPPINGS}/{mapping['id']}"
    reviewed = client.patch(path, headers=owner, json={"mapping_confidence": "high"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["version"] == 2
    assert (
        client.patch(path, headers=owner, json={"mapping_confidence": "high"}).json()[
            "version"
        ]
        == 2
    )


# --- productivity goals -------------------------------------------------------------------------


def test_productivity_goals_filter_by_type_and_active_flag(client, owner):
    daily = create_productivity_goal(client, owner, goal_type="daily_time").json()
    retired = create_productivity_goal(
        client, owner, goal_type="streak", is_active=False
    ).json()
    assert listed(client, owner, PRODUCTIVITY, goal_type="streak") == [retired["id"]]
    assert listed(client, owner, PRODUCTIVITY, is_active="false") == [retired["id"]]
    assert listed(client, owner, PRODUCTIVITY, is_active="true") == [daily["id"]]
    assert (
        client.get(PRODUCTIVITY, headers=owner, params={"is_active": "no"}).status_code
        == 422
    )
    stats = client.get(
        f"{PRODUCTIVITY}/stats", headers=owner, params={"group_by": "goal_type"}
    )
    assert stats.json()["groups"] == {"daily_time": 1, "streak": 1}


def test_a_productivity_goal_tracks_its_current_value(client, owner):
    goal = create_productivity_goal(client, owner, target_value=3).json()
    path = f"{PRODUCTIVITY}/{goal['id']}"
    progress = client.patch(path, headers=owner, json={"current_value": 2.5})
    assert progress.status_code == 200, progress.text
    assert progress.json()["current_value"] == 2.5
    assert progress.json()["version"] == 2
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404


# --- links --------------------------------------------------------------------------------------


def test_links_filter_by_goal_project_and_relation(client, owner):
    goal = create_goal(client, owner).json()
    delivery = create_goal_project_link(client, owner, goal["id"], 9001).json()
    supporting = create_goal_project_link(
        client, owner, goal["id"], 9002, relation_type="supporting"
    ).json()
    assert listed(client, owner, PROJECT_LINKS, goal_id=goal["id"]) == [
        delivery["id"],
        supporting["id"],
    ]
    assert listed(client, owner, PROJECT_LINKS, project_id=9002) == [supporting["id"]]
    assert listed(client, owner, PROJECT_LINKS, relation_type="delivery") == [
        delivery["id"]
    ]
    stats = client.get(
        f"{PROJECT_LINKS}/stats", headers=owner, params={"group_by": "relation_type"}
    )
    assert stats.json()["groups"] == {"delivery": 1, "supporting": 1}


def test_context_links_filter_by_goal_context_and_relation(client, owner):
    goal = create_goal(client, owner).json()
    primary = create_goal_context_link(client, owner, goal["id"], 7001).json()
    supporting = create_goal_context_link(
        client, owner, goal["id"], 7002, relation_type="supporting"
    ).json()
    assert listed(client, owner, CONTEXT_LINKS, context_id=7001) == [primary["id"]]
    assert listed(client, owner, CONTEXT_LINKS, relation_type="supporting") == [
        supporting["id"]
    ]
    assert listed(client, owner, CONTEXT_LINKS, goal_id=goal["id"]) == [
        primary["id"],
        supporting["id"],
    ]


def test_task_project_links_filter_by_task_project_and_relation(client, owner):
    task = create_task(client, owner).json()
    link = create_task_project_link(client, owner, task["id"], 9001).json()
    create_task_project_link(
        client, owner, task["id"], 9002, relation_type="supporting"
    )
    assert listed(client, owner, TASK_PROJECT_LINKS, goal_task_id=task["id"]) == [
        link["id"],
        link["id"] + 1,
    ]
    assert listed(client, owner, TASK_PROJECT_LINKS, project_id=9001) == [link["id"]]
    assert (
        len(listed(client, owner, TASK_PROJECT_LINKS, relation_type="supporting")) == 1
    )


def test_a_link_weight_can_be_changed(client, owner):
    goal = create_goal(client, owner).json()
    link = create_goal_project_link(client, owner, goal["id"]).json()
    path = f"{PROJECT_LINKS}/{link['id']}"
    heavier = client.patch(path, headers=owner, json={"weight": 2.5})
    assert heavier.status_code == 200, heavier.text
    assert heavier.json()["weight"] == 2.5
    assert heavier.json()["version"] == 2
    assert client.patch(path, headers=owner, json={"weight": 0}).status_code == 422


def test_deleting_a_link_leaves_the_goal_and_task(client, owner):
    goal = create_goal(client, owner).json()
    task = create_task(client, owner, goal_id=goal["id"]).json()
    project_link = create_goal_project_link(client, owner, goal["id"]).json()
    task_link = create_task_project_link(client, owner, task["id"]).json()
    assert (
        client.delete(
            f"{PROJECT_LINKS}/{project_link['id']}", headers=owner
        ).status_code
        == 204
    )
    assert client.get(f"{GOALS}/{goal['id']}", headers=owner).status_code == 200
    refused = client.delete(f"{TASKS}/{task['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert (
        client.delete(
            f"{TASK_PROJECT_LINKS}/{task_link['id']}", headers=owner
        ).status_code
        == 204
    )
    assert client.delete(f"{TASKS}/{task['id']}", headers=owner).status_code == 204
