---
id: TICKET-0030
title: Server-side collision endpoint
type: feature
status: exec
created: 2026-07-16
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []              # read-only feature; no migration, no canon write
blast_radius: small           # one new pure module + one new route module; play.py untouched
brief_ids: [BRIEF-0030-a, BRIEF-0030-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Ticket 0030 — Server-side collision endpoint (C2). Purpose: a single
server authority that judges transient player movement against the
persistent obstacle geometry, and never writes position to canon."

Second of four tickets in the spatial / Play mode workstream:
0029 obstacle geometry schema (merged, v1.80) → **0030 collision
authority** → 0031 NPC spatial presence + proximity gate → 0032
canvas/WASD surface.

## Clarifications resolved (intake)

- **D1** — The algorithm lives in a pure module,
  `src/world_engine/geometry.py`: zero DB, zero FastAPI, zero `cockpit/`
  imports. "Sole collision authority" holds by construction — one
  importable module contains the math; the route is a caller only.
  Rejected: math in the route module (logic/interface fusion). The pure
  module is exactly the piece a future client-side C3 would reuse.
  Placement forced by RECON: `routes/play.py` sits at exactly 1000 lines,
  the G1 module-budget cap — the endpoint lands in a new
  `routes/spatial.py` (which 0031's proximity endpoint will join).
- **D2** — `POST /api/spatial/move-check`, body
  `{location_id, origin: {x, y}, destination: {x, y}}`, response
  `{x, y, blocked}`. The server structurally verifies `location_id`
  matches the player's `current_location_id` (409 otherwise) — role
  doctrine: a player client must not probe geometry of a location the PC
  is not in. Errors: 404 unknown location; 409 wrong location; 409 no
  spatial mode (NULL bounds); 422 non-finite coordinates. Rejected: free
  `location_id` (geometry probing by segment dichotomy).
- **D3** — Hard-stop semantics: the server returns the clipped stop point
  (pulled back 1 mm along the segment); slide-along-wall EMERGES
  client-side in 0032 via axis-component re-submission. Server-computed
  slide (option B) is recorded as a compatible evolution — same endpoint,
  same response shape — kept in mind, not built.
- **D4** — The player is a point; the 0032 circle radius is purely
  visual. Rejected: polygon inflation / radius parameter (premature, same
  doctrine as the rejected C3). Degenerate origin (inside an obstacle or
  outside bounds) returns `(origin, blocked=true)` — the judge never
  rescues the player; unblocking is a creator act.
- **D5** — Named third register: **transient adjudication** (read
  persistent geometry, judge transient position, persist NOTHING) —
  neither `_apply_mutation` (AI proposal) nor creator CRUD. Recorded in
  `ARCHITECTURE_DECISIONS.md` (BRIEF-0030-b writes the single block
  covering both briefs) and stated verbatim in both module docstrings.
- **Bounds enforcement is IN scope** — 0029 explicitly deferred "clamping
  movement inside bounds" to this ticket: bounds edges are judged as
  walls seen from inside, uniformly with obstacle edges.
- **Regression guard** — the algorithm's unit cases live as a permanent
  deterministic verify check (`tooling/verify/checks/geometry_unit.py`,
  no DB), so the sole-authority module is gate-guarded on every future
  ticket, not defended by convention. Fallback `scripts/test_geometry.py`
  documented in BRIEF-0030-a if runner conventions resist.
- Locked upstream (workstream doc): movement transient, never persisted
  (Q1); collisions judged server-side only, no parallel client collision
  (Q2, C3 rejected); segment-based judging (C2); the segment↔polygon
  algorithm is generic from day one — rectangles and future real polygons
  share one code path (B2).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Geometry unit cases green (free move, rectangle hit, triangle hit,
      bounds clip, degenerate origins, zero-length, on-edge destination,
      parallel graze)  -> verify/checks/geometry_unit.py
- [ ] New modules within budget; `routes/play.py` untouched at its cap
      -> verify/checks/module_budget.py
- [ ] Zero canon writes: policy file unchanged, no new write site
      -> verify/checks/single_canon_write.py
- [ ] CLAUDE.md contract holds if the File structure section is touched
      -> verify/checks/claude_md_contract.py

### Live gate (Nia)
- [ ] Smoke against the 0029 demo location (bounds 40×30, block
      (5, 5, 10, 2)): free move returns destination `blocked: false`;
      segment crossing the block's top edge stops at y ≈ 5 − ε
      `blocked: true`; segment leaving bounds clips at the edge
      `blocked: true`; origin inside the block returns origin
      `blocked: true`.
- [ ] Guards: another location's id → 409; NULL-bounds location → 409;
      unknown id → 404; NaN coordinate → 422.
- [ ] `ARCHITECTURE_DECISIONS.md` TICKET-0030 block present (D1–D5 +
      register naming), `DECISIONS_INDEX.md` regenerated.
- [ ] No schema change anywhere: `world-engine-schema.md` version line
      unchanged, no migration script added.
