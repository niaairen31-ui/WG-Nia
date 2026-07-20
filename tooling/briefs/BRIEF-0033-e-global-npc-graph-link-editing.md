# BRIEF — Step "Global NPC relation graph + link editing" (BRIEF-0033-e)

## Context

The NPC tab has a cytoscape ego-graph, on_demand, display-only
(BRIEF-0023-a/b: `relGraph*`, `index.html:9034-9200`; endpoint
`GET /characters/{id}/relation-graph`, `crud/relations.py:174`). Full
relation CRUD already exists (`POST /entities/{id}/relations`,
`PUT /relations/{id}`, `DELETE /relations/{id}` — `crud/relations.py:109,
137, 160`) with type/intensity/direction/notes. Locked D1+E1: a GLOBAL mode
(all active characters of the world) inside the same on-demand panel, with
link add/edit/remove wired to the existing CRUD; tap = info card; double-tap
enlarges the node in global mode (ego mode keeps double-tap = recenter).
Post-commit only. The panel stays collapsible — already guaranteed by the
existing on_demand slot; global mode adds no always-visible surface.

## Scope IN

1. Backend — new route in `cockpit/crud/relations.py`:
   `GET /api/relation-graph` (path deliberately outside
   `/characters/{entity_id}/...` to avoid the `{entity_id}` route
   swallowing a literal segment). Returns `{ "nodes": [...], "edges":
   [...] }` with the SAME node and edge shapes as the ego endpoint, no
   `center` key. Nodes: ALL entities of the active world with
   `type='character'` AND `status='active'` (join `Character` for
   `character_type`, description truncated to 200 chars — reuse the ego
   endpoint's row-building; extract a small shared helper
   `_relation_graph_nodes(rows)` if useful, domain-local, no new module).
   Isolated characters (zero edges) ARE included — required so links can
   be created toward them. Edges: every Relation row of the world with
   `type NOT IN _RELATION_GRAPH_EXCLUDED_TYPES` (same structural
   exclusion in the WHERE clause, never post-filtered) and both endpoints
   in the node set. Read-only, no writes.
2. Frontend — mode state: `let relGraphMode = 'ego';` (`'ego' |
   'global'`). In the relgraph head (`index.html:1269`), add a "Global"
   toggle button next to the bucket checkboxes; clicking flips the mode
   and refetches (`relGraphFetch(authorEntityId)` for ego,
   `relGraphFetchGlobal()` for global). Global mode requires no selected
   character; the empty-state message only applies in ego mode. Mode
   resets to `'ego'` in `_relGraphReset()`.
3. Global rendering: same cytoscape style sheet and bucket coloring;
   layout `cose` (concentric needs a center). `isCenter` false for all
   nodes.
4. E1 interactions (global mode only; ego mode behavior untouched):
   - `tap` node -> info card (reuse `relGraphRenderInfoCard`; the
     "Relations avec le centre" section is replaced in global mode by the
     node's direct relations list — same edge rows, labeled "Relations").
   - `dbltap` node -> toggle a `followed` class on that node (cytoscape
     style: width/height 56, border-width 3) — enlarge to follow; second
     dbltap shrinks back. At most cosmetic state, not persisted.
   - Link creation: a "Lier" toggle button in the relgraph head, visible
     only in global mode. When armed, the next two node taps select
     source A then target B (A highlighted); on B, open the edge panel
     (see 5) in CREATE mode; disarm after create/cancel. While armed,
     taps do not update the info card.
   - `tap` edge -> edge panel in EDIT mode.
5. Edge panel: rendered inside the info-card column (`relgraph-info-card`)
   — fields type (input), intensity (number 1-100), direction (select:
   mutual / a_to_b / b_to_a), notes (textarea), plus Save and, in EDIT
   mode, Delete (with `confirm()`; hard delete matches the existing
   DELETE route's posture). CREATE -> `POST
   /api/entities/{A}/relations` with `{ other_entity_id: B, type,
   intensity, direction, notes }`; EDIT -> `PUT /api/relations/{id}`;
   DELETE -> `DELETE /api/relations/{id}`. After any success: refetch the
   current mode's data and re-render (bucket visibility preserved).
6. `visible_to_b` is NOT surfaced in the panel (defaults preserved by the
   routes: true on create, unchanged on edit).

## Scope OUT

- No pre-commit / region-review NPC graph, no draft-staged links — that is
  D2, the NAMED DEFERRAL, opening as the next ticket immediately after
  0033 closes. Nothing of it is built here.
- No change to the ego endpoint's shape or the ego mode's interactions
  (dbltap recenter stays).
- No aggregation of parallel edges (B1 of 0023 stands: one edge per row).
- No pagination/virtualization of the global graph — full world load is
  accepted at current scale; performance work is report-only.
- No `visible_to_b` UI, no relation `change_history` display.
- No node position persistence (cytoscape layout recomputes per open).

## Invariants to defend

- Single canon-write paths: all writes go through the EXISTING relation
  CRUD routes -> `write_relation` chokepoint; the new GET route writes
  nothing.
- Exclusion is structural: `connects_to`/`controls` excluded in the WHERE
  clause of the new route, same as the ego route (G1 of 0023) — never
  filtered client-side.

## Done means

- [ ] Live: NPC tab -> "Voir le graphe" -> "Global" shows every active
      character including isolated ones; buckets filter; tap shows the
      info card with the node's relations; dbltap enlarges, dbltap again
      shrinks.
- [ ] Live: "Lier" -> tap A -> tap B -> fill type/intensity/direction/
      note -> Save -> the edge appears with the right bucket color; tap
      the edge -> change intensity across a bucket boundary -> color
      updates; Delete removes it; the relations list in the entity editor
      reflects all three operations.
- [ ] Live: ego mode unchanged (select a character, dbltap recenters);
      switching tabs and back resets to ego mode, panel closed.
- [ ] `/review-step` and `/close-step` run.
- [ ] All verify checks pass.

## Docs to update

- ARCHITECTURE_DECISIONS.md, TICKET-0033 section: D1 + E1 recorded —
  global mode reuses the ego panel and relation CRUD; structural type
  exclusion duplicated in the global route's WHERE; D2 explicitly
  deferred to the next ticket.
