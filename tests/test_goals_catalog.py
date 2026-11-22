"""platform-empire SPEC-002: a goal's category reaches the graph as an in-domain set event."""


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
    client.patch(
        f"/v1/goals/{goal['id']}", headers=owner, json={"title": "Ship it now"}
    )
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
