---
id: TICKET-0043
title: Post-TICKET-0041 verify-check drift (relation_graph, schema_0024) and review-tree root-fallback bug
type: bug
status: live-gate
created: 2026-07-22
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0043-a, BRIEF-0043-b, BRIEF-0043-c]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Le ticket 0041 est fermé et mergé. Voila deux commentaire de claude code. Je veux
que tu me fasse un mini ticket 0043 pour réglé la situation avant implantation le
ticket 0042 (pas encore commence)

1- Fix stale relation_graph.py and schema_0024.py verify checks
While closing TICKET-0041 (shared review-tree component, cockpit/index.html),
BRIEF-0041-c's Done means asked to confirm the four checks that read index.html
still pass: page_contract.py, relation_graph.py, event_tab.py, schema_0024.py.
Two of those four are currently broken for reasons entirely unrelated to
TICKET-0041 (git diff for this ticket touches only index.html, CLAUDE.md, and
the standards/decisions docs — never crud/relations.py or models/canon.py):
tooling/verify/checks/relation_graph.py fails with "FAIL:
_RELATION_GRAPH_EXCLUDED_TYPES constant not found in crud/relations.py" and
"FAIL: N POST fetch(es) found in relGraph* JS outside
relGraphSaveEdgePanel/relGraphDeleteEdge". tooling/verify/checks/schema_0024.py
fails with "FAIL: npc_goal.prerequisites column missing" — the column was
deliberately relationalized in BRIEF-0025-c and this check was never updated or
retired afterward. Neither should silently stay broken.

2- Fix region tree vanishing on sole-root rejection
Bug found while live-testing TICKET-0041 in src/world_engine/cockpit/index.html:
the region draft review tree. Reproduction: generate a region draft where
location A is the sole root (parent_local_id == null) and locations B and C
both have parent_local_id == A. Reject A (the root). Expected per the ticket's
own acceptance criteria language ("reject the root -> its children fall to
no-parent and render at top level"): B and C should render as top-level nodes.
Actual: B and C vanish from the tree entirely, along with A. Confirmed via
`git show main:...index.html` this predates TICKET-0041 — not a regression from
that refactor. Affects both the region draft review and, per TICKET-0041, the
room-batch generator's review tree in TICKET-0042 too.

## Clarifications resolved (intake)

RECON on the live `main` tarball confirmed both reports and refined one of them:

- **relation_graph.py, constant not found:** `crud/relations.py:18` imports
  `RELATION_GRAPH_EXCLUDED_TYPES` from `context.py:108` (aliased as
  `_RELATION_GRAPH_EXCLUDED_TYPES`) rather than defining it as a local tuple
  literal. **A1** — the check's constant-detection is extended to accept
  either a direct tuple literal or an aliased import resolved back to
  `context.py`.
- **relation_graph.py, POST-fetch miscount:** the real cause is not "a related
  consequence" but a section-boundary problem — the check's comment-anchored
  slice (`"cytoscape, display-only, on-demand"` .. `"Generic modal
  (BRIEF-41)"`) now spans ~60k chars and has come to include ~20 `npcAgent*`
  and ~16 `linkAgent*` functions (unrelated NPC/link-batch generator UI)
  inserted between the two anchors after the check was written. **A1** — the
  section is rebuilt from every function whose name matches `relGraph\w+`
  instead of a comment-anchored slice, immune to future code inserted between
  the old anchors.
- **schema_0024.py, prerequisites column missing:** confirmed deliberate —
  `canon.py:626-651` documents TICKET-0025/BRIEF-0025-c relationalizing
  `npc_goal.prerequisites` into the `goal_prerequisite` table. No
  `schema_0025.py` was ever written (`prereq_judge.py` covers only the judge's
  *behavior*, not the schema shape) — a real coverage gap, not just staleness.
  **B2** — `check_prerequisites_column()` is retired from `schema_0024.py` and
  a new `schema_0025.py` is authored covering `goal_prerequisite`'s real
  shape, including a DDL-text assertion on both CHECK constraints (not just
  column presence), to avoid a vacuous pass on the one invariant that matters
  most here (K1, closed vocabulary).
- **review-tree root-fallback bug:** confirmed line-for-line —
  `reviewCascade` (`index.html:5910`) resolves `effectiveParent[n.id] = null`
  for a child whose parent *and* fallback target are both rejected;
  `reviewTree` (`index.html:5967`) builds `childrenByParent` from
  `cascade.effectiveParent` but filters `roots` (line 5980) from the raw
  `n.parentId` — the mismatch is the bug. Only one consumer,
  `'region'` (registered `index.html:6425`), exists today; TICKET-0042 will
  add a second on this same shared component. **C1** — one-line fix
  (`roots` filtered on `cascade.effectiveParent[n.id] == null` instead of raw
  `parentId`) plus a new G1 check guarding against this regression.
- **Ticket structure:** **D** — three lettered briefs (a: relation_graph.py,
  b: schema_0024.py/schema_0025.py, c: review-tree fix), delivered together,
  each independently testable and committable.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `_RELATION_GRAPH_EXCLUDED_TYPES` is recognized as a direct tuple literal
      OR an aliased import resolved to `context.py`; the relGraph* JS section
      is collected by function name (`relGraph\w+`), not a comment-anchored
      slice  -> verify/checks/relation_graph.py
- [ ] No assertion on `npc_goal.prerequisites` remains anywhere in
      schema_0024.py  -> verify/checks/schema_0024.py
- [ ] `goal_prerequisite` columns present; `ck_goal_prerequisite_type`'s DDL
      text contains `relation_gte`; `ck_goal_prerequisite_threshold`'s DDL
      text contains the 1-100 bound; `idx_goal_prerequisite_unique` is a
      UNIQUE index on `(goal_id, type, target_entity_id)`
      -> verify/checks/schema_0025.py
- [ ] `reviewTree`'s `roots` line references `cascade.effectiveParent`, not a
      bare `n.parentId == null` filter  -> verify/checks/review_root_fallback.py

### Live  ->  human gate (Nia)
- [ ] Region draft: location A is sole root, B and C have
      `parent_local_id == A`; reject A; B and C render as top-level nodes in
      the review tree (not vanished).
- [ ] A normal draft with no rejections still renders its full tree exactly as
      before (zero-behavior-change sanity pass for the unaffected path).
- [ ] Ego relation-graph and global relation-graph tabs still render, stay
      read-only, still exclude `connects_to`/`controls` (sanity pass after the
      check rewrite — no product-code change expected here).
