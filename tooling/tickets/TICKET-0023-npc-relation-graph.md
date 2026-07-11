---
id: TICKET-0023
title: NPC relation ego-graph (on-demand) + on-demand graph-slot contract + cytoscape vendoring
type: feature
status: live-gate
created: 2026-07-10
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []              # read-only feature; no migration, no canon write
blast_radius: medium          # page-contract change + first vendored JS dependency
brief_ids: [BRIEF-0023-a, BRIEF-0023-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

« Est-ce qu'on peut voir un graphique de relation entre mes NPC me permettant
de voir qui a une relation avec qui. Je veux l'option de choisir lesquelles je
veux affiché (0-25 rouge, 25-50 orange, 50-75 bleu, 75-100 vert). Je le veux
en affichage seulement. On va devoir modifié le contrat de page des entités
parce que je ne veux pas qu'il soit affiché de façons permanante (pour les
lieux non plus), cela doit être une option que click pour voir. »

Plus, en intake : ego-graph centré (double-click recentre, simple click =
carte d'info, zoom molette + pan) ; deux arêtes si les scores directionnels
diffèrent ; multi-sélection des tranches, tout coché par défaut ; le graphe
Lieux existant (parents/enfants) passe au même contrat on-demand SANS toucher
son contenu ; rendu « manipulable » via lib vendorée (cytoscape) car « les
graphes se complexifieront dans le futur » ; personnages seulement en v1 ;
une arête par ligne de relation.

## RECON findings (fresh clone of `main`, 2026-07-10)

1. `Relation` (`models.py:255`): `intensity` CHECK **1–100** (not 0–100),
   `direction` = `mutual | a_to_b | b_to_a`. A directional pair is TWO rows.
   Bucket boundaries must therefore be 1-25 / 26-50 / 51-75 / 76-100.
2. Standing schema guard (`world-engine-schema.md`, relation NOTE): any
   world-wide relation scan MUST exclude `type='connects_to'` and
   `type='controls'` — structural rows carrying a meaningless `intensity=50`.
3. Page contract: `CREATION_TABS` slots seam (`index.html:3174` entry
   contract; lieux graph slot declared at `index.html:3328`). Slots load
   unconditionally on tab activation (`_creationActivateTab`,
   `index.html:3452`) — this is the exact line of contract that "on-demand"
   changes. ARCHITECTURE_DECISIONS.md:3601 ("Graph-as-slot posture") states
   the slot mechanism generalizes only on a second concrete reader; the NPC
   graph IS that second reader.
4. The existing Lieux graph is a hand-rolled SVG **editor** (BRIEF-15,
   `index.html:7642+`): edge delete at `:7780`, relation POST at `:7793`. The
   NPC graph is display-only by request — the two must not share write paths.
5. `GET /api/locations/graph` (`cockpit/crud.py:2105`) returns
   `{ nodes, edges }` — the response-shape precedent for the new endpoint.
6. Entity detail already resolves relations: `_list_relations`
   (`crud.py:482`), `GET /api/entities/{entity_id}/relations` (`crud.py:894`).
   The graph endpoint is a new read composition, not a new capability.
7. **No `StaticFiles` mount anywhere in `src/`.** `index.html` is served
   inline (`app.py:1868`). Vendoring cytoscape requires a new serving path.
8. CLAUDE.md: "no new dependencies without a decision" — cytoscape vendoring
   is that decision; it must be recorded in ARCHITECTURE_DECISIONS.md.
9. `character.character_type` = `player | npc` (`world-engine-schema.md`,
   `character` table); "characters only" scope = entity.type='character',
   both character_types included.
10. RECON caveat: read-only clone inspection; the cockpit was not run. The
    slot-visibility conclusion (finding 3) is from reading
    `_creationActivateTab`, to be confirmed trivially at exec.

## Clarifications resolved (intake)

- **A1 — Scope: ego-graph, depth 1, characters only.** Center = the selected
  NPC/PJ. Nodes = the center plus every `entity.type='character'` linked to
  it by at least one qualifying relation row. Edges include **inter-neighbor
  edges** (relations between two neighbors of the center), otherwise "qui a
  une relation avec qui" is unanswerable; this is a locked default, vetoable
  at live gate. Factions / magic / concepts as nodes: Scope OUT, v2.
- **B1 — One edge per relation row.** `direction='mutual'` = one plain edge;
  `a_to_b` / `b_to_a` rows = one arrowed edge each (so a directional pair
  with differing intensities naturally shows two arrows). Parallel edges
  between the same pair (multiple types, e.g. `ally` + `debt`) render curved
  and distinct. No aggregation.
- **C1 — Color buckets on `intensity`:** 1-25 rouge, 26-50 orange, 51-75
  bleu, 76-100 vert. Conscious consequence, acted: neutral (50) renders
  orange. Filters = four multi-select toggles (one per bucket), all ON by
  default, applied **client-side** per relation row (no refetch on toggle).
- **D1 — Interactions:** wheel zoom, drag pan (cytoscape built-ins);
  single click on a node = info card (name, character_type, short
  description, and its relations to the center: type, intensity, direction);
  double-click on a node = that node becomes the new center (refetch, new
  depth-1 ego-graph).
- **E1 — Display-only, structurally.** The NPC graph code path performs no
  POST/PUT/DELETE — contrast with the Lieux SVG editor (RECON finding 4).
  Relation editing stays exclusively on the entity sheet.
- **F1 — On-demand is a slot-contract field, not a branch.** Slots gain a
  declared `display: 'always' | 'on_demand'` (default `'always'`, zero
  behavior change for undeclared slots). `on_demand` slots render a toggle
  button in the standard shell instead of auto-loading; `loader` fires on
  first click. Lieux's graph slot is declared `on_demand`; its
  component/content is byte-untouched (its cytoscape migration is a future
  ticket, explicitly deferred by Nia).
- **G1 — Structural exclusion of `connects_to` and `controls`** in the
  endpoint's WHERE clause (RECON finding 2), not post-filtered in Python.
- **H1 — Cytoscape.js is vendored, not CDN'd** (locally-hosted, offline
  cockpit; no build step). Single minified file committed under
  `cockpit/vendor/`, served by one dedicated GET route (`FileResponse`), no
  `StaticFiles` mount (minimal-first; a mount is warranted on a second
  vendored asset, not before). The dependency decision is recorded in
  ARCHITECTURE_DECISIONS.md with version pinned in the file name.
- **I1 — Endpoint:** `GET /api/characters/{entity_id}/relation-graph` →
  `{ center, nodes, edges }`, mirroring the `/api/locations/graph` shape
  precedent (RECON finding 5). Read-only; no query params in v1 (filtering
  is client-side per C1).
- **J1 — World-switch / tab-enter resets** cover all new graph state
  (loaded data, current center, toggle states, open/closed panel), via the
  existing `state.onTabEnter` / `onWorldSwitch` contract (G1 of
  TICKET-0005).

## Brief decomposition

- **BRIEF-0023-a — `on-demand-graph-slot-and-vendoring`**
  Slot contract `display` field + shell toggle rendering + dispatcher change
  (`_creationActivateTab` honors `on_demand`) · Lieux graph slot declared
  `on_demand`, component untouched · vendored `cytoscape.min.js` +
  `GET /vendor/cytoscape.min.js` route · ARCHITECTURE_DECISIONS.md entry for
  the dependency + the contract change · `page_contract.py` extended.
  **No migration. No schema touch.**

- **BRIEF-0023-b — `npc-relation-ego-graph`**
  `GET /api/characters/{entity_id}/relation-graph` in `cockpit/crud.py` ·
  NPC tab `slots` entry (`display: 'on_demand'`, `onSelect` wired to the
  selected character) · cytoscape rendering (bucket colors, curved parallel
  edges, arrows on directional rows) · four bucket toggles · info card ·
  double-click recenter · resets (J1) · new verify check
  `relation_graph.py`. **No migration. No schema touch.**

## Scope OUT (both briefs)

1. Non-character nodes (factions, magic, concepts) — v2, on demand.
2. Any whole-world relation graph (only the depth-1 ego-graph exists).
3. Migrating the Lieux graph component to cytoscape (future ticket, Nia).
4. Any edit capability through the NPC graph (E1 is permanent posture).
5. Server-side filtering, pagination, or query params on the endpoint.
6. A `StaticFiles` mount (H1 — one route, one file).
7. Graph on any other tab (factions etc.) — the slot mechanism remains the
   extension point, nothing speculative is added (0005-a doctrine).
8. Touching `authorRenderRelations` (the sheet's relation table) or any
   relation CRUD path.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] CREATION_TABS `npc` entry has a graph slot with `display: 'on_demand'`; `lieux` graph slot declares `display: 'on_demand'`  ->  verify/checks/page_contract.py
- [ ] `showCreationSubTab` / `_creationActivateTab` bodies contain no tab-id string literal; `on_demand` handling reads slot data only  ->  verify/checks/page_contract.py
- [ ] `cockpit/vendor/cytoscape.min.js` exists and a GET route serves it  ->  verify/checks/relation_graph.py
- [ ] Route `GET /api/characters/{entity_id}/relation-graph` registered; handler contains no `db.add`, no write call  ->  verify/checks/relation_graph.py
- [ ] The relation-graph query excludes `connects_to` and `controls` in its WHERE clause (not post-filtered)  ->  verify/checks/relation_graph.py
- [ ] The NPC-graph JS code path contains no `fetch` with method POST/PUT/DELETE  ->  verify/checks/relation_graph.py
- [ ] Lieux graph component functions (`graphLoad`/`graphRender`/drag/edge handlers) byte-identical to `main`  ->  verify/checks/relation_graph.py

### Live  ->  human gate (Nia)
- [ ] NPC tab: no graph is visible by default; a « Voir le graphe » control appears; clicking it loads the ego-graph of the selected character
- [ ] Lieux tab: the parents/enfants graph is no longer permanently displayed; same click-to-view control; once opened, it looks and behaves exactly as before
- [ ] Ego-graph: center highlighted; every linked character shown; inter-neighbor relations visible; edges colored by bucket (1-25 rouge, 26-50 orange, 51-75 bleu, 76-100 vert)
- [ ] A directional pair with different intensities shows two distinct arrows; multiple relation types between the same pair show as separate curved edges
- [ ] Wheel zoom and drag pan work; single click opens the info card; double-click recenters the graph on that character
- [ ] Four bucket toggles, all ON by default; toggling hides/shows matching edges instantly, no reload
- [ ] No control anywhere on the graph creates, edits, or deletes a relation
- [ ] Switching world or leaving/re-entering the tab fully resets the graph (no stale center, no stale toggles)
