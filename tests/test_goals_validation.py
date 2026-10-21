"""What the goals cell refuses: bad enums, bounds, oversize text, dangling refs and backwards periods."""

import pytest
from goals_helpers import (
    CONTEXT_LINKS,
    GOALS,
    MAPPINGS,
    METRICS,
    PRODUCTIVITY,
    PROJECT_LINKS,
    TASK_PROJECT_LINKS,
    TASKS,
    another_workspace,
    create_goal,
    create_goal_context_link,
    create_goal_project_link,
    create_mapping,
    create_metric,
    create_productivity_goal,
    create_task,
    create_task_project_link,
)

MISSING = 987654321


# --- goal ---------------------------------------------------------------------------------------


def test_a_goal_needs_a_title(client, owner):
    response = client.post(GOALS, headers=owner, json={"status": "active"})
    assert response.status_code == 422


def test_a_goal_title_is_limited_to_500_characters(client, owner):
    assert create_goal(client, owner, title="x" * 501).status_code == 422
    assert create_goal(client, owner, title="y" * 500).status_code == 201


def test_a_goal_domain_is_limited_to_200_characters(client, owner):
    assert create_goal(client, owner, domain="d" * 201).status_code == 422
    assert create_goal(client, owner, domain="d" * 200).status_code == 201


def test_goal_type_category_and_status_must_be_known_values(client, owner):
    assert create_goal(client, owner, type="decade").status_code == 422
    assert create_goal(client, owner, category="hobby").status_code == 422
    assert create_goal(client, owner, status="done").status_code == 422
    ok = create_goal(client, owner, type="quarterly", category="tech", status="paused")
    assert ok.status_code == 201, ok.text


def test_goal_progress_is_between_0_and_100(client, owner):
    assert create_goal(client, owner, progress_percent=-1).status_code == 422
    assert create_goal(client, owner, progress_percent=101).status_code == 422
    assert create_goal(client, owner, progress_percent=0).status_code == 201
    assert create_goal(client, owner, progress_percent=100).status_code == 201


def test_goal_dates_must_be_calendar_dates(client, owner):
    assert create_goal(client, owner, due_date="end of year").status_code == 422
    assert create_goal(client, owner, start_date="2026-02-30").status_code == 422


def test_goal_priority_must_be_a_whole_number(client, owner):
    assert create_goal(client, owner, priority="high").status_code == 422
    assert create_goal(client, owner, priority=1).status_code == 201


def test_a_goal_title_cannot_be_cleared_on_update(client, owner):
    goal = create_goal(client, owner).json()
    cleared = client.patch(f"{GOALS}/{goal['id']}", headers=owner, json={"title": None})
    assert cleared.status_code == 422
    assert cleared.json()["detail"] == {"error": "invalid_value", "fields": ["title"]}


# --- goal task ----------------------------------------------------------------------------------


def test_a_task_needs_a_title_of_at_most_500_characters(client, owner):
    assert client.post(TASKS, headers=owner, json={"status": "todo"}).status_code == 422
    assert create_task(client, owner, title="").status_code == 422
    assert create_task(client, owner, title="t" * 501).status_code == 422
    assert create_task(client, owner, title="t" * 500).status_code == 201


def test_a_task_status_must_be_a_known_step(client, owner):
    assert create_task(client, owner, status="waiting").status_code == 422
    for status in ("todo", "in_progress", "done", "blocked"):
        assert create_task(client, owner, status=status).status_code == 201, status


def test_a_task_priority_is_a_number_not_a_word(client, owner):
    # low / medium / high exist only in the old SQLite data, which the importer rewrites.
    for word in ("low", "medium", "high"):
        assert create_task(client, owner, priority=word).status_code == 422, word
    assert create_task(client, owner, priority=1).status_code == 201


def test_task_progress_is_between_0_and_100(client, owner):
    assert create_task(client, owner, progress_percent=101).status_code == 422
    assert create_task(client, owner, progress_percent=-5).status_code == 422
    assert create_task(client, owner, progress_percent=100).status_code == 201


def test_a_task_can_only_belong_to_an_existing_goal(client, owner):
    refused = create_task(client, owner, goal_id=MISSING)
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"] == {"error": "reference_not_found"}
    assert create_task(client, owner, goal_id=0).status_code == 422


def test_a_task_cannot_belong_to_a_goal_of_another_workspace(
    client, owner, harness, platform
):
    stranger = another_workspace(harness, platform)
    foreign_goal = create_goal(client, stranger).json()
    refused = create_task(client, owner, goal_id=foreign_goal["id"])
    assert refused.status_code == 422, refused.text


# --- goal metric --------------------------------------------------------------------------------


def test_a_metric_needs_a_goal_a_key_a_name_and_a_target(client, owner):
    goal = create_goal(client, owner).json()
    complete = {
        "goal_id": goal["id"],
        "metric_key": "revenue",
        "name": "Monthly revenue",
        "target_value": 1000.0,
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        response = client.post(METRICS, headers=owner, json=body)
        assert response.status_code == 422, missing


def test_metric_text_fields_have_length_limits(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_metric(client, owner, goal["id"], metric_key="k" * 201).status_code
        == 422
    )
    assert create_metric(client, owner, goal["id"], name="n" * 501).status_code == 422
    assert create_metric(client, owner, goal["id"], unit="u" * 61).status_code == 422
    ok = create_metric(
        client, owner, goal["id"], metric_key="k" * 200, name="n" * 500, unit="u" * 60
    )
    assert ok.status_code == 201, ok.text


def test_metric_enums_must_be_known_values(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_metric(client, owner, goal["id"], metric_type="vanity").status_code
        == 422
    )
    assert (
        create_metric(client, owner, goal["id"], direction="sideways").status_code
        == 422
    )
    assert create_metric(client, owner, goal["id"], status="green").status_code == 422
    assert (
        create_metric(client, owner, goal["id"], source_type="guess").status_code == 422
    )


def test_metric_values_must_be_numbers(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_metric(client, owner, goal["id"], target_value="a lot").status_code
        == 422
    )
    assert (
        create_metric(client, owner, goal["id"], current_value="n/a").status_code == 422
    )


@pytest.mark.xfail(
    strict=True,
    reason="cellkit accepts NaN and Infinity for a real field: the row is stored but read back "
    "with target_value null, so a required target comes back empty (201 instead of 422)",
)
@pytest.mark.parametrize("not_a_number", ["NaN", "Infinity", "-Infinity"])
def test_a_metric_target_that_is_not_a_finite_number_is_refused(
    client, owner, not_a_number
):
    goal = create_goal(client, owner).json()
    raw = (
        f'{{"goal_id": {goal["id"]}, "metric_key": "k", "name": "n", "target_value": '
        + not_a_number
        + "}"
    )
    response = client.post(
        METRICS, headers={**owner, "content-type": "application/json"}, content=raw
    )
    assert response.status_code == 422


def test_a_metric_can_only_belong_to_an_existing_goal(client, owner):
    refused = create_metric(client, owner, MISSING)
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"] == {"error": "reference_not_found"}


def test_a_metric_cannot_belong_to_a_goal_of_another_workspace(
    client, owner, harness, platform
):
    stranger = another_workspace(harness, platform)
    foreign_goal = create_goal(client, stranger).json()
    assert create_metric(client, owner, foreign_goal["id"]).status_code == 422


def test_a_metric_period_cannot_end_before_it_starts(client, owner):
    goal = create_goal(client, owner).json()
    backwards = create_metric(
        client, owner, goal["id"], period_start="2026-10-31", period_end="2026-10-01"
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["period_end", "period_start"],
    }
    one_day = create_metric(
        client, owner, goal["id"], period_start="2026-10-01", period_end="2026-10-01"
    )
    assert one_day.status_code == 201, one_day.text


def test_moving_a_metric_period_end_before_its_start_is_refused_on_update(
    client, owner
):
    goal = create_goal(client, owner).json()
    metric = create_metric(client, owner, goal["id"], period_start="2026-10-10").json()
    path = f"{METRICS}/{metric['id']}"
    refused = client.patch(path, headers=owner, json={"period_end": "2026-10-01"})
    assert refused.status_code == 422, refused.text
    assert client.get(path, headers=owner).json()["period_end"] is None
    # A patch that touches neither date still works.
    renamed = client.patch(path, headers=owner, json={"name": "Revenue per month"})
    assert renamed.status_code == 200, renamed.text


# --- portfolio mapping --------------------------------------------------------------------------


def test_a_mapping_needs_its_goal_bucket_class_group_goal_and_season(client, owner):
    goal = create_goal(client, owner).json()
    complete = {
        "goal_id": goal["id"],
        "portfolio_bucket": "active_bet",
        "attention_class": "focus",
        "collision_group": "income",
        "canonical_goal": "Grow income",
        "current_season": "2026-Q4",
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        response = client.post(MAPPINGS, headers=owner, json=body)
        assert response.status_code == 422, missing


def test_a_mapping_bucket_and_class_must_be_known_values(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_mapping(client, owner, goal["id"], portfolio_bucket="misc").status_code
        == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], attention_class="max").status_code
        == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], mapping_confidence="sure").status_code
        == 422
    )


def test_attention_cost_is_between_0_and_5(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_mapping(client, owner, goal["id"], attention_cost=6).status_code == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], attention_cost=-1).status_code == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], attention_cost=5).status_code == 201
    )


def test_mapping_text_fields_have_length_limits(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_mapping(client, owner, goal["id"], collision_group="c" * 201).status_code
        == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], canonical_goal="g" * 501).status_code
        == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], current_season="s" * 101).status_code
        == 422
    )
    assert (
        create_mapping(client, owner, goal["id"], mapping_source="m" * 201).status_code
        == 422
    )


def test_a_mapping_can_only_point_at_existing_goals(client, owner):
    refused = create_mapping(client, owner, MISSING)
    assert refused.status_code == 422, refused.text
    goal = create_goal(client, owner).json()
    canonical_missing = create_mapping(
        client, owner, goal["id"], canonical_goal_id=MISSING
    )
    assert canonical_missing.status_code == 422, canonical_missing.text
    assert canonical_missing.json()["detail"] == {"error": "reference_not_found"}


def test_a_mapping_cannot_point_at_a_goal_of_another_workspace(
    client, owner, harness, platform
):
    stranger = another_workspace(harness, platform)
    foreign_goal = create_goal(client, stranger).json()
    assert create_mapping(client, owner, foreign_goal["id"]).status_code == 422
    own_goal = create_goal(client, owner).json()
    through_canonical = create_mapping(
        client, owner, own_goal["id"], canonical_goal_id=foreign_goal["id"]
    )
    assert through_canonical.status_code == 422, through_canonical.text


# --- productivity goal --------------------------------------------------------------------------


def test_a_productivity_goal_needs_a_name_a_type_and_a_target(client, owner):
    complete = {
        "name": "Finish tasks",
        "goal_type": "daily_completions",
        "target_value": 5,
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        response = client.post(PRODUCTIVITY, headers=owner, json=body)
        assert response.status_code == 422, missing


def test_a_productivity_goal_type_must_be_a_known_kind(client, owner):
    assert (
        create_productivity_goal(client, owner, goal_type="hourly").status_code == 422
    )
    for kind in (
        "daily_completions",
        "weekly_completions",
        "daily_time",
        "weekly_time",
        "streak",
    ):
        assert (
            create_productivity_goal(client, owner, goal_type=kind).status_code == 201
        ), kind


def test_a_productivity_goal_name_is_limited_to_500_characters(client, owner):
    assert create_productivity_goal(client, owner, name="n" * 501).status_code == 422


def test_a_productivity_period_cannot_end_before_it_starts(client, owner):
    backwards = create_productivity_goal(
        client, owner, period_start="2026-11-01", period_end="2026-10-01"
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["period_end", "period_start"],
    }
    one_day = create_productivity_goal(
        client, owner, period_start="2026-11-01", period_end="2026-11-01"
    )
    assert one_day.status_code == 201, one_day.text


def test_moving_a_productivity_period_end_before_its_start_is_refused_on_update(
    client, owner
):
    goal = create_productivity_goal(client, owner, period_start="2026-11-01").json()
    path = f"{PRODUCTIVITY}/{goal['id']}"
    refused = client.patch(path, headers=owner, json={"period_end": "2026-10-01"})
    assert refused.status_code == 422, refused.text
    assert client.get(path, headers=owner).json()["period_end"] is None
    # A patch that touches neither date still works.
    renamed = client.patch(path, headers=owner, json={"name": "Finish more tasks"})
    assert renamed.status_code == 200, renamed.text


# --- links --------------------------------------------------------------------------------------


def test_a_link_needs_a_goal_and_a_project(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        client.post(
            PROJECT_LINKS, headers=owner, json={"goal_id": goal["id"]}
        ).status_code
        == 422
    )
    assert (
        client.post(PROJECT_LINKS, headers=owner, json={"project_id": 9001}).status_code
        == 422
    )
    assert (
        client.post(
            CONTEXT_LINKS, headers=owner, json={"goal_id": goal["id"]}
        ).status_code
        == 422
    )
    assert (
        client.post(CONTEXT_LINKS, headers=owner, json={"context_id": 7001}).status_code
        == 422
    )
    task = create_task(client, owner).json()
    assert (
        client.post(
            TASK_PROJECT_LINKS, headers=owner, json={"project_id": 9001}
        ).status_code
        == 422
    )
    assert (
        client.post(
            TASK_PROJECT_LINKS, headers=owner, json={"goal_task_id": task["id"]}
        ).status_code
        == 422
    )


def test_link_relation_types_are_per_link_kind(client, owner):
    goal = create_goal(client, owner).json()
    task = create_task(client, owner).json()
    assert (
        create_goal_project_link(
            client, owner, goal["id"], relation_type="primary"
        ).status_code
        == 422
    )
    assert (
        create_goal_project_link(
            client, owner, goal["id"], relation_type="supporting"
        ).status_code
        == 201
    )
    assert (
        create_goal_context_link(
            client, owner, goal["id"], relation_type="delivery"
        ).status_code
        == 422
    )
    assert (
        create_goal_context_link(
            client, owner, goal["id"], relation_type="primary"
        ).status_code
        == 201
    )
    assert (
        create_task_project_link(
            client, owner, task["id"], relation_type="primary"
        ).status_code
        == 422
    )
    assert (
        create_task_project_link(
            client, owner, task["id"], relation_type="delivery"
        ).status_code
        == 201
    )


def test_a_link_weight_must_be_positive(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_goal_project_link(client, owner, goal["id"], weight=0).status_code == 422
    )
    assert (
        create_goal_project_link(client, owner, goal["id"], weight=-1).status_code
        == 422
    )
    assert (
        create_goal_project_link(client, owner, goal["id"], weight=0.0001).status_code
        == 201
    )


def test_a_link_source_is_limited_to_200_characters(client, owner):
    goal = create_goal(client, owner).json()
    assert (
        create_goal_project_link(
            client, owner, goal["id"], source="s" * 201
        ).status_code
        == 422
    )


def test_a_link_can_only_point_at_an_existing_goal_or_task(client, owner):
    for refused in (
        create_goal_project_link(client, owner, MISSING),
        create_goal_context_link(client, owner, MISSING),
        create_task_project_link(client, owner, MISSING),
    ):
        assert refused.status_code == 422, refused.text
        assert refused.json()["detail"] == {"error": "reference_not_found"}


def test_a_link_cannot_point_at_a_goal_or_task_of_another_workspace(
    client, owner, harness, platform
):
    stranger = another_workspace(harness, platform)
    foreign_goal = create_goal(client, stranger).json()
    foreign_task = create_task(client, stranger).json()
    assert (
        create_goal_project_link(client, owner, foreign_goal["id"]).status_code == 422
    )
    assert (
        create_goal_context_link(client, owner, foreign_goal["id"]).status_code == 422
    )
    assert (
        create_task_project_link(client, owner, foreign_task["id"]).status_code == 422
    )
