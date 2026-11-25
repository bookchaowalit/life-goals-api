"""platform-empire SPEC-002: a goal's category reaches the graph as an in-domain set event."""

from pathlib import Path

from cellkit.publisher import publish_pending


def set_events(harness, goal_id):
    rows = harness.superuser(
        "SELECT payload FROM goals.outbox WHERE subject = %s AND type = 'goals.goal.linked' ORDER BY occurred_at",
        (f"empire:goals:goal:{goal_id}",),
    )
    return [row[0] for row in rows]


def test_category_maps_to_a_domain_on_create_and_change(client, owner, harness):
    goal = client.post(
        "/v1/goals", headers=owner, json={"title": "Ship it", "category": "business"}
    ).json()
    [first] = set_events(harness, goal["id"])
    assert first["targets"] == ["empire:platform:domain:work"]
    assert (first["mode"], first["relation"], first["set_version"]) == (
        "replace",
        "in-domain",
        goal["version"],
    )
    changed = client.patch(
        f"/v1/goals/{goal['id']}", headers=owner, json={"category": "tech"}
    ).json()
    last = set_events(harness, goal["id"])[-1]
    assert (last["targets"], last["set_version"]) == (
        ["empire:platform:domain:skills"],
        changed["version"],
    )
    renamed = client.patch(
        f"/v1/goals/{goal['id']}", headers=owner, json={"title": "Ship it now"}
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "Ship it now"
    assert len(set_events(harness, goal["id"])) == 2  # only category changes emit


def test_every_category_has_a_domain(harness):
    [link] = harness.cell.resource("goal").catalog
    categories = harness.cell.resource("goal").field("category").values
    assert {c: link.targets(c)[0].rsplit(":", 1)[1] for c in categories} == {
        "tech": "skills",
        "business": "work",
        "life": "unclassified",
        "creative": "aesthetics-rest",
        "financial": "finance",
        "health": "health",
    }
    assert link.targets(None) == ["empire:platform:domain:unclassified"]


def test_publisher_retries_then_delivers_the_set_event(
    client, owner, harness, platform
):
    goal = client.post(
        "/v1/goals", headers=owner, json={"title": "Run", "category": "health"}
    ).json()
    token = owner["Authorization"].removeprefix("Bearer ")
    subject = f"empire:goals:goal:{goal['id']}"
    publisher = harness.cell.role("publisher")
    harness.superuser(
        "UPDATE goals.outbox SET published_at = NULL, next_attempt_at = now() WHERE subject = %s RETURNING id",
        (subject,),
    )
    platform.fail_publish = True
    with harness.cluster.connect(publisher) as conn:
        failed = publish_pending(conn, harness.cell.schema, platform, token)
    assert failed["failed"] >= 1
    assert failed["published"] == 0
    [(attempts, error)] = harness.superuser(
        "SELECT attempts, last_error FROM goals.outbox WHERE subject = %s AND type = 'goals.goal.linked'",
        (subject,),
    )
    assert (attempts, error) == (1, "PlatformUnavailable")
    platform.fail_publish = False
    harness.superuser(
        "UPDATE goals.outbox SET next_attempt_at = now() WHERE subject = %s RETURNING id",
        (subject,),
    )
    with harness.cluster.connect(publisher) as conn:
        delivered = publish_pending(conn, harness.cell.schema, platform, token)
    assert delivered["failed"] == 0
    [linked] = [
        e
        for e in platform.published
        if e["subject"] == subject and e["type"] == "goals.goal.linked"
    ]
    assert linked["payload"]["targets"] == ["empire:platform:domain:health"]


def test_platform_url_and_body_guards():
    import httpx
    import pytest
    from cellkit import platform as kit_platform

    assert kit_platform.checked_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    with pytest.raises(ValueError, match="https"):
        kit_platform.checked_url("http://platform.example.com")
    assert kit_platform._json_object(httpx.Response(200)) == {}
    assert kit_platform._json_object(httpx.Response(200, content=b"not json")) == {}
    assert kit_platform._json_object(httpx.Response(200, json=[1])) == {}
    assert kit_platform._json_object(httpx.Response(200, json={"a": 1})) == {"a": 1}


BACKFILL = (
    Path(__file__).resolve().parents[1] / "migrations" / "0002_catalog_backfill.sql"
)


def test_backfill_queues_node_then_domain_set_at_the_goal_version(
    client, owner, harness
):
    """Rollout step 4: goals written before the producer get a node event, then their set event."""
    [link] = harness.cell.resource("goal").catalog
    categories = ("tech", "business", "life", "creative", "financial", "health", None)
    goals = {}
    for category in categories:
        body = {"title": f"Backfill {category}", "domain": "career"}
        if category:
            body["category"] = category
        made = client.post("/v1/goals", headers=owner, json=body)
        assert made.status_code == 201, made.text
        goals[category] = made.json()
    edited = client.patch(
        f"/v1/goals/{goals['tech']['id']}", headers=owner, json={"status": "active"}
    )
    assert edited.status_code == 200, edited.text
    goals["tech"] = edited.json()
    subjects = [f"empire:goals:goal:{g['id']}" for g in goals.values()]
    # as if written before the producer: nothing queued yet
    harness.superuser(
        "DELETE FROM goals.outbox WHERE subject = ANY(%s) RETURNING id", (subjects,)
    )
    with (
        harness.cluster.connect(harness.cell.role("migrator")) as conn,
        conn.transaction(),
    ):
        conn.execute(BACKFILL.read_text(encoding="utf-8"))
    for category, goal in goals.items():
        events = harness.superuser(
            "SELECT type, payload FROM goals.outbox WHERE subject = %s ORDER BY occurred_at",
            (f"empire:goals:goal:{goal['id']}",),
        )
        assert [t for t, _ in events] == ["goals.goal.updated", "goals.goal.linked"]
        assert events[0][1] == {
            "title": goal["title"],
            "status": goal["status"],
            "type": goal["type"],
            "category": category,
            "domain": "career",
            "version": goal["version"],
            "deleted": False,
        }
        assert events[1][1] == {
            "relation": "in-domain",
            "mode": "replace",
            "targets": link.targets(category),
            "set_version": goal["version"],
            "version": goal["version"],
        }
    assert goals["tech"]["version"] == 2
    forced = harness.superuser(
        "SELECT relforcerowsecurity FROM pg_class"
        " WHERE oid IN ('goals.goals'::regclass, 'goals.outbox'::regclass)"
    )
    assert all(force for (force,) in forced)
