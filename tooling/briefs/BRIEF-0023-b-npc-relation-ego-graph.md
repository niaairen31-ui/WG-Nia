# BRIEF — Step "NPC relation ego-graph (display-only, on-demand)"

## Context

BRIEF-0023-a delivered the `display: 'on_demand'` slot contract and a
loadable vendored cytoscape. This brief builds the feature Nia asked for: an
ego-graph of the selected character's relations — depth 1, characters only,
edges colored by intensity bucket with per-bucket toggles, manipulable
(zoom / pan / click info / double-click recenter), and strictly display-only.
The relation data is fully in place (`Relation`, models.py:255; resolved
relations already served per entity, crud.py:482/894); what is missing is one
read composition (the graph endpoint) and its rendering.

Two standing guards frame this brief: the schema's exclusion rule for
structural relation types (`connects_to`, `controls` — meaningless
intensity=50), and the contrast with the Lieux graph, which is an EDITOR
(`index.html:7780` edge delete, `:7793` relation POST). The NPC graph writes
nothing, ever.

Locked: A1, B1, C1, D1, E1, G1, I1, J1 (ticket).

## Scope IN

1. **`GET /api/characters/{entity_id}/relation-graph`** (`cockpit/crud.py`,
   beside the locations graph route, response shape mirroring crud.py:2105):

   ```json
   { "center": "<entity_id>",
     "nodes": [ { "id", "name", "character_type", "description" } ],
     "edges": [ { "id", "source", "target", "type", "intensity",
                  "direction" } ] }
   ```

   Query contract:
   - 404 if `entity_id` is not an active `entity` of `type='character'` in
     the active world.
   - Neighbor set = every ACTIVE character entity linked to the center by at
     least one qualifying relation row (either endpoint).
   - Edge set = every qualifying relation row whose BOTH endpoints are in
     `{center} ∪ neighbors` — inter-neighbor edges included (A1).
   - Qualifying = `world_id` matches AND `type NOT IN
     ('connects_to','controls')` **in the WHERE clause** (G1) AND both
     endpoints resolve to active `type='character'` entities.
   - One edge object per relation row — no merging, no aggregation (B1).
   - `description` truncated server-side (~200 chars) for the info card.
   - Read-only handler: no `db.add`, no write helper, no query params.

2. **NPC tab slot** — `npc.slots` gains
   `{ id: 'relgraph', containerId: 'creation-npc-relgraph',
      loader: relGraphLoad, onSelect: relGraphOnSelect,
      display: 'on_demand', toggleLabel: 'Voir le graphe' }`.
   `onSelect` (the seam `pj.fiche` already uses) keeps the graph in sync
   with the selected character: if the panel is open, selecting another
   character refetches centered on it; if closed, nothing loads.
   With no character selected, the toggle shows a "select a character"
   empty state, fetches nothing.

3. **Rendering (`relGraph*` functions, index.html)** — a cytoscape instance
   in `#creation-npc-relgraph`:
   - Center node visually distinct (size + border).
   - Edge color by intensity bucket: 1-25 `#e5534b` (rouge), 26-50
     `#d29922` (orange), 51-75 `#58a6ff` (bleu), 76-100 `#3fb950` (vert) —
     final hexes may align with existing cockpit palette vars at exec.
   - `direction='mutual'` → plain edge; `a_to_b` / `b_to_a` → arrowed edge
     (arrow toward the target of the row's semantic direction).
   - Parallel edges between the same pair rendered with curve separation
     (cytoscape `curve-style: bezier` handles this natively).
   - Layout: `concentric` (center + ring) or `cose`; zoom/pan = cytoscape
     defaults.
   - Single click on node → info card (name, character_type, description,
     and that node's relation rows to the CENTER: type, intensity,
     direction). Rendered in a side strip of the panel, not a browser
     alert.
   - Double-click (cytoscape `dbltap`) on node → refetch with that node as
     center; toggle states persist across recenters.
   - Four bucket checkboxes above the canvas, all checked by default;
     toggling sets cytoscape element visibility client-side — no refetch
     (C1).

4. **Resets (J1)** — `npc.state.onTabEnter` / `onWorldSwitch` extended to
   clear: fetched graph data, current center, bucket toggle states (back to
   all-on), open/closed panel state, and destroy the cytoscape instance.

5. **New verify check `verify/checks/relation_graph.py`** — the ticket's
   machine-checkable criteria: route registered and write-free; WHERE-clause
   exclusion of `connects_to`/`controls`; vendored file + route present
   (from -a); no POST/PUT/DELETE fetch in the `relGraph*` code path; Lieux
   graph component functions byte-identical to `main`.

## Scope OUT

1. Non-character nodes (factions, magic, concepts) — v2.
2. Whole-world graph, depth > 1, path finding.
3. Any relation create/edit/delete through the graph — permanent posture
   (E1). The sheet's relation table (`authorRenderRelations`) is untouched.
4. Server-side filtering or query params on the endpoint.
5. Persisting node positions, toggle preferences, or any graph state.
6. Graph slots on other tabs.
7. Touching the Lieux graph in any way.

## Invariants

- The endpoint is the ONLY new server surface; it reads and never writes.
- `connects_to` / `controls` are excluded at query construction, never
  post-filtered (G1; the J3-of-0022 doctrine on filter placement).
- Bucket filtering is a pure client-side visibility concern; the fetched
  data is always the complete ego-graph.
- One relation row = one edge, always.
- The slot participates in the page contract exclusively through its
  declared entry — no tab-id branch anywhere.

## Done means

- Select an NPC, click « Voir le graphe » : the ego-graph renders, colored
  by bucket; zoom/pan work; click = info card; double-click recenters;
  toggles filter instantly; directional pairs with differing intensities
  show two arrows; parallel types show as distinct curved edges.
- Nothing on the graph can modify a relation.
- World switch / tab re-entry fully resets the panel.
- `/verify` green including `relation_graph.py`.

## Docs to update

- CLAUDE.md File structure section: `vendor/` + new check, if budget
  allows.
- No schema changelog (no schema touch). ARCHITECTURE_DECISIONS additions
  were made in -a; -b adds a short entry only if exec diverges from this
  brief.
