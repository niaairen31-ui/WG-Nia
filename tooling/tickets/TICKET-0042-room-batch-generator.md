---
id: TICKET-0042
title: Room batch generator
type: feature
status: live-gate
created: 2026-07-23
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0042-a, BRIEF-0042-b, BRIEF-0042-c, BRIEF-0042-d, BRIEF-0042-e]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Troisieme et dernier ticket du chantier. Le generateur lui-meme : depuis le
browse Lieux, generer un lot de lieux (3 a 25 pieces) sous un lieu ancre
existant, coherentes avec ce qui existe, reliees entre elles et a l'ancre, avec
des tailles derivees du type et des portes materialisees au commit.

Manifeste editable en Phase A, une fiche par piece en Phase B, squelette
d'adjacence garanti connexe, aretes supplementaires proposees puis resolues par
nom, revue via le composant 0041 et commit atomique qui materialise les portes.

## Clarifications resolved (intake)

Decisions locked before this ticket (ticket-level, unchanged):

- **Q0-a** Semantic and topological coherence ONLY. No shared coordinate space
  between sibling locations; `bounds` + `obstacle_vertex` are a LOCAL space per
  location. A geometric floor plan (Q0-b) is a later, named, out-of-scope
  chantier.
- **A1** The model produces NO number. `bounds` come from the type template.
- **C1** No parent/child envelope constraint. Write-time geometry validation is
  proscribed (it cannot stay true across later edits).
- **I1** Generator context = anchor fiche + `location_subculture` with
  `is_hidden = FALSE` FILTERED AT QUERY CONSTRUCTION + canon siblings (name,
  type, one line) + existing `connects_to` edges among them. No hidden rows, no
  `discoverable_detail`, no NPC.
- **J1** Two phases. Phase A = manifest (name + one-liner + `location_type` +
  attachment + proposed edges), creator-editable. Phase B = one full fiche per
  room, one model call each, each call seeing the whole manifest.
- **K1** The manifest carries a `parent_room` per room (a manifest room name, or
  the anchor). THIS is the spanning tree: model-proposed, code-validated (name
  resolution, cycle detection, forced attach to the anchor on failure).
- **D3** Over the skeleton, the model proposes SUPPLEMENTARY edges, resolved by
  name against (a) the current batch, (b) canon siblings already under the
  anchor. (Timing relocated at intake -> see P/S below.)
- **L1** Naming a non-existent location NEVER creates it. An edge to an
  unresolved name falls to an unresolved note. DEFERRAL L2 (named): flip to
  "unknown name becomes a batch room" if unresolved notes routinely name rooms
  Nia ends up creating by hand.
- **F1 (transitive)** The anchor is chosen by the creator before generation,
  never by the model. Reaching the anchor directly OR indirectly is valid.
- **E2** Islands are advisory, not blocking. With K1 an island can only come
  from the creator's own review rejects; the cascade reparents to the anchor.
- **M2** Review goes through the TICKET-0041 generic component, with
  `fallbackParentId` = the anchor.
- **N1** Doors are placed on the perimeter (TICKET-0040), never at the center,
  never proposed by the model.
- **O1** Pre-commit graph reused from region: skeleton solid, supplementary
  edges dashed, anchor as a visually distinct, non-editable root node. O2
  (nodes as bounds-scaled rectangles) REJECTED until Q0-b.

Decisions resolved THIS intake (2026-07-23):

- **P1** The manifest is the sole authority for `location_type`. It is validated
  against `location_type_catalog` (the real vocabulary carrying classification
  AND size template), NEVER against the frozen `_LOCATION_TYPES` enum. The batch
  path never routes type through `entity_author._validate_location_type` (which
  would repli-fall "room" to "other" and lose its template). A manifest type
  absent from the catalog -> a note; the creator resolves it in Phase A editing
  via the existing classification affordance.
- **P-a** The Phase A type field is BOTH a catalog-backed datalist AND an
  add-new-type affordance (interior/exterior + optional template), reusing
  `_authorPromptLocationTypeClassification` (`index.html:8430`) verbatim.
- **Q1** The anchor enters the review descriptor as a SYNTHETIC node:
  always-accepted, non-toggleable, root (`parentId = null`). Rooms attached to
  the anchor hang beneath it naturally in tree and graph; O1's distinct
  non-editable root falls out with no change to the shared component's core.
- **R** A Phase B fiche failure retries ONCE, then the room drops into
  `skipped`; its children reparent to the anchor via the existing cascade at
  review time (R1). No new mechanism -- a failed internal node is exactly a
  rejected node.
- **S** Count shortfall (model returns 8 for 25) is handled by Phase A editing
  (creator adds rows), NOT a code clamp. Phase C is the heaviest token call
  (sees all fiches); measure at 25, compact peer context only if it overflows.
- **T1** An anchor with NULL bounds or NULL classification NEVER blocks the
  batch. `door_placeholder_point` degrades to the origin (0,0) for a NULL-bounds
  endpoint (`placement.py:68`); rooms still get their own template bounds. A note
  surfaces; the batch commits regardless (consistent with C1).
- **U** Two base templates, mirroring region: Phase A = new `pt-*`
  `room_batch_manifest`; Phase B reuses the atomic location author's model call
  (no new template). Phase C adds a third `pt-*` `room_batch_coherence`. NO
  single combined template.
- **Phase C (D3 relocation, drafting decision this intake)** D3 runs AFTER Phase
  B as a coherence pass, informed by the generated fiches, not blind in the
  manifest.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `room_batch_author.py` performs NO canon write: no `_apply_mutation`, no
      `write_relation`, no `_create_entity_core`, no `db.commit()` in the
      generation module -> verify/checks/room_batch_report_only.py
- [ ] The batch commit route holds exactly one `db.commit()`, wrapped in a
      try/except that rolls back on any exception, and writes every
      `connects_to` edge through `spatial_author.connect_locations` (or
      `write_relation` + a single `materialize_doors` sweep) -> extend
      verify/checks/canon_write_policy AST allow-list + a commit-shape check
- [ ] New author + route modules respect R1 (80-line functions) and R5 (module
      budget 1000 lines / 40 functions) -> existing checks
- [ ] The manifest and coherence parsers route through `llm_parse` (R2) ->
      existing check

### Live  ->  human gate (Nia)
- [ ] From the Lieux browse, descended into an anchor, "Generer un lot ici"
      generates a manifest of the requested count (3..25); at root the button is
      disabled.
- [ ] The manifest is editable: rename, change one-liner, change type via the
      catalog datalist (incl. adding a new classified type), change parent_room.
- [ ] A parent_room naming a cycle or an unknown name force-attaches to the
      anchor (K1); the review tree shows it under the anchor with the reparented
      badge.
- [ ] Phase B produces one fiche per manifest room; a deliberately failing fiche
      retries once then drops to `skipped`, and its children reparent to the
      anchor at review.
- [ ] The coherence pass proposes at least one supplementary edge on a batch
      that warrants one; an edge to an unknown name lands as an unresolved note,
      never a new room (L1).
- [ ] Review via the 0041 component: anchor is the distinct non-editable root;
      skeleton solid, supplementary edges dashed in the graph.
- [ ] Commit is atomic: reject a room mid-batch, commit; the rejected room and
      its edges are absent, no half-batch is observable, and committed rooms
      carry template bounds and materialized perimeter doors on both sides.
- [ ] Committing under an anchor with NULL bounds succeeds; the anchor-side door
      sits at the origin and a note says so (T1).
