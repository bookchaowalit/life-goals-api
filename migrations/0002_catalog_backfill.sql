-- platform-empire SPEC-002 rollout step 4: classify the goals written before the producer existed.
-- For every existing goal this queues, in the cell outbox, a lifecycle `.updated` event (node data from the row:
-- the cell.yaml `graph` fields title, status, type, category, domain) followed by the `in-domain` set event
-- (`mode: replace`) under the cell.yaml category mapping, both at the row's current version. The publisher
-- (goals-api inline or the goals publisher cron) delivers them; the graph keeps the highest set_version, so a goal
-- that already sent its set event, or that is edited later, turns these into `stale` (rollout AC-23: a second run
-- adds no edges).
--
-- goals and outbox FORCE row level security and the migrator binds no workspace, so FORCE is lifted for these
-- statements only (same transaction). ALTER TABLE takes ACCESS EXCLUSIVE on both, so no write can land between
-- reading a goal's version and queueing its events. Keep the CASE in step with cell.yaml (tests compare them).
ALTER TABLE goals.goals NO FORCE ROW LEVEL SECURITY;
ALTER TABLE goals.outbox NO FORCE ROW LEVEL SECURITY;

INSERT INTO goals.outbox (workspace_id, type, subject, classification, payload, occurred_at)
SELECT g.workspace_id, e.type, 'empire:goals:goal:' || g.id, 'confidential', e.payload,
       now() + e.n * interval '1 microsecond'
FROM goals.goals g
CROSS JOIN LATERAL (VALUES
    (0, 'goals.goal.updated', jsonb_build_object(
        'title', g.title, 'status', g.status, 'type', g.type, 'category', g.category, 'domain', g.domain,
        'version', g.version, 'deleted', false)),
    (1, 'goals.goal.linked', jsonb_build_object(
        'relation', 'in-domain',
        'mode', 'replace',
        'targets', jsonb_build_array('empire:platform:domain:' || CASE g.category
            WHEN 'tech' THEN 'skills'
            WHEN 'business' THEN 'work'
            WHEN 'creative' THEN 'aesthetics-rest'
            WHEN 'financial' THEN 'finance'
            WHEN 'health' THEN 'health'
            ELSE 'unclassified' END),
        'set_version', g.version,
        'version', g.version))
) AS e(n, type, payload)
ORDER BY g.workspace_id, g.id, e.n;

ALTER TABLE goals.goals FORCE ROW LEVEL SECURITY;
ALTER TABLE goals.outbox FORCE ROW LEVEL SECURITY;
