---
id: TICKET-0031
title: NPC spatial presence + proximity endpoint
type: feature
status: exec
created: 2026-07-16
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []              # read-only feature; no migration, no canon write, no schema change
blast_radius: small           # one new pure module + one new assembler module + additions to routes/spatial.py
brief_ids: [BRIEF-0031-a, BRIEF-0031-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Ticket 0031 — NPC spatial presence + proximity endpoint (E2). Purpose:
Give NPCs a position the canvas can draw and the server can measure
distance against, WITHOUT introducing persistent NPC coordinates, then
expose a proximity endpoint that gates existing NPC dialogue."

Third of four tickets in the spatial / Play mode workstream:
0029 obstacle geometry schema (merged, v1.80) → 0030 collision authority
(merged) → **0031 NPC spatial presence + proximity gate** → 0032
canvas/WASD surface.

## Clarifications resolved (intake)

- **A — Transient NPC positions are a deterministic pure derivation,
  stored NOWHERE.** Position = pure function of (location geometry, open
  gatherings + rosters, stable ids). Each gathering gets a centroid
  derived from `sha256(gathering.id)` projected into bounds outside
  obstacles; each member gets an offset derived from `sha256(entity.id)`
  around its gathering centroid. Same inputs → same outputs, on every
  request, F5 and server restart included (sha256, never Python's
  salted `hash()`). Lifecycle resolved by construction: gatherings
  dissolve/regenerate on genuine location entry → new ids → new
  positions; `migrate_npc` moves an NPC's circle to its new cluster with
  zero additional spatial code. Rejected: prose extraction (B —
  non-deterministic, model-call cost, fragile against the resilience
  doctrine); client placement (C — server-side proximity authority
  evaporates; the rejected-C3 anti-pattern, NPC edition); authored
  spawn layout (D — persistent config nobody reads yet; recorded as a
  compatible refinement of A, not built).
- **A-i — Placement math lives in a new pure module
  `src/world_engine/placement.py`** (zero DB, zero FastAPI, zero
  `cockpit/` imports — geometry.py's sibling in the TRANSIENT
  ADJUDICATION register; imports `geometry.point_in_polygon`, nothing
  else non-stdlib). The DB-reading assembler
  `cockpit/spatial_presence.py::npc_positions` is the SINGLE site that
  turns a location into named NPC positions — reuses `_open_gatherings`,
  `_active_members`, `_location_geometry_dict`; excludes
  `character_type == "player"` explicitly (RECON: `_active_members`
  rosters include the player).
- **E2 — Two endpoints, one derivation** (locked upstream: distinct
  proximity endpoint, never piggybacked on move-check).
  `GET /api/spatial/presence` returns the drawable NPC circles;
  `POST /api/spatial/proximity` judges a transient player position
  against the same recomputed NPC positions. Both are callers of the
  single assembler. Rejected: one merged endpoint (draw cadence ≠
  interaction cadence; 0032 would call "proximity" to draw).
- **G-A — Advisory dialogue gate.** The proximity result enables the
  client-side "Parler" affordance for in-range NPCs; the existing
  dialogue flow (`POST /api/conversations/start`, `/api/scene/join`) is
  untouched. Rationale: player position is client-held (Q1
  workstream-wide), so a structural gate would judge client-supplied
  data anyway — no added guarantee; and non-spatial locations / creator
  flows must keep working unchanged. G-B (optional `position` in
  start_conversation, re-judged server-side when the location has
  spatial mode) is recorded as a compatible evolution, not built.
- **Threshold — `INTERACTION_RANGE = 2.0` world-meters,** a named
  constant in `placement.py`. Calibrated at live gate; a per-location
  column is a trivial additive change later, not built now.
- **Earshot rail guard —** `placement.distance` + the
  `npc_positions` assembler are the SOLE spatial-distance site.
  Interaction proximity and future audibility (who-hears-what) are one
  distance family: any future earshot reader imports this site, never
  recomputes. Named in ARCHITECTURE_DECISIONS (BRIEF-0031-b), mirroring
  the gate-guarded "sole collision authority" discipline of 0030.
  Nothing of earshot itself ships in this ticket.
- Locked upstream (workstream doc): movement transient, never persisted
  (Q1); proximity judged server-side (single source of truth); no
  persistent NPC coordinates, ever, in this ticket.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Placement unit cases green (determinism across calls, obstacle
      avoidance, bounds containment, member ring around centroid,
      pathological all-wall fallback never raises, player-exclusion at
      assembler level via injected roster)
      -> verify/checks/placement_unit.py
- [ ] New modules within budget; `routes/play.py` untouched at its cap
      -> verify/checks/module_budget.py
- [ ] Zero canon writes: policy file unchanged, no new write site
      -> verify/checks/single_canon_write.py
- [ ] CLAUDE.md contract holds if the File structure section is touched
      -> verify/checks/claude_md_contract.py
- [ ] Decisions block header well-formed, index regenerated
      -> verify/checks/decisions_index.py
- [ ] Full verify suite green

### Live  ->  human gate (Nia)
- [ ] Against the 0029 demo location (bounds 40×30, block (5,5,10,2))
      with NPCs present: `GET /api/spatial/presence` returns one circle
      per present NPC, none inside the block, all inside bounds,
      visibly clustered by gathering; the player never appears.
- [ ] F5 refresh AND a server restart both return byte-identical
      coordinates while the same gatherings stay open.
- [ ] `POST /api/spatial/proximity` with a position within 2.0 of a
      circle returns that npc_id with its distance, sorted ascending;
      a far position returns an empty `in_range`; `threshold: 2.0`
      echoed in every response.
- [ ] Guards on both endpoints: another location's id → 409;
      NULL-bounds location → 409; unknown ids → 404; non-finite
      position → 422 (proximity).
- [ ] Dialogue unchanged: `POST /api/conversations/start` works exactly
      as before, spatial mode or not.
- [ ] `ARCHITECTURE_DECISIONS.md` TICKET-0031 block present (A, A-i,
      E2, G-A, threshold, earshot rail), `DECISIONS_INDEX.md`
      regenerated.
- [ ] No schema change anywhere: `world-engine-schema.md` version line
      unchanged, no migration script added.
