---
id: TICKET-0069
title: Play surface migration — the last surface out of the legacy document
type: feature
status: paused
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: large
brief_ids: []
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Pour la réactivation du 3D, ce sera dans longtemps (1ans et +, à ma
> demande).

Opened by TICKET-0061 (decision A3) as the named successor that
`frontend/src/legacy/registry.js` points at. It is deposited in `paused`
deliberately: `legacy_mount.py` rule 3b asserts that this file exists and
is not `done` for as long as `LEGACY_MOUNTS` declares `play`.

## Reactivation condition

**A HUMAN GATE, recorded as such and not disguised as a structural one.**
This ticket moves to `intake` when Nia opens it, and not before. Nia's
stated horizon is one year or more, tied to the Play 3D rewrite decision.

The project's standing rule is that named deferrals carry verifiable
reactivation conditions and never qualitative ones. This is the declared
exception, of the same class as the live-gate statuses: the trigger
genuinely is the creator's decision, and pretending otherwise by inventing
a measurable proxy would be the dishonest option. What the rule does still
require, and what is discharged here, is that the deferral be *findable*:
the registry names this file, and rule 3b makes the pointer structurally
true rather than a well-formed sentence.

## Scope (sketch — not a specification)

Report-only shape as measured on `main` at 2026-08-20. Every anchor below
will have drifted by the time this ticket opens and **a full RECON must be
redone from scratch** against a fresh tarball.

- **The surface.** `src/world_engine/cockpit/legacy.html` (renamed from
  `index.html` by TICKET-0061): 2 762 lines — 420 of inline `<style>`, 177
  of markup, 2 145 of `<script>` holding 73 top-level functions. 30 inline
  handlers, 36 top-level globals (~30 of them `_spatial*`, plus `WORLD_ID`
  and `PLAYER_ID`).
- **The four coupling points to unwind.** The iframe
  (`LegacyFrame.svelte`), `showSurface('play')` (`App.svelte` →
  `bridge.js`), `hideLegacyHeader()`, and `initCreationMount(legacyDocument())`
  — the last being the one genuinely cross-document signal
  (`mutations:proposed`, emitted by Play's `analyzeConv`, consumed by the
  Review Queue filter).
- **What retires with it.** `frontend/src/legacy/` entirely (registry,
  bridge), `LegacyFrame.svelte`, `GET /legacy` and `_INDEX_HTML` in
  `app.py`, `legacy_mount.py`, `legacy_call.py` and their two baselines,
  and `stylesheet_partition.py`'s rule7 (legacy) half — whose own
  retirement alarm fires on an empty `LEGACY_MOUNTS` and names itself.
- **What breaks and must be re-homed, measured on an experimental tree.**
  Deleting the legacy document turns six checks RED:
  `legacy_mount.py`, `stylesheet_partition.py`, `graph_primitive.py`,
  `review_component.py`, `faction_roster_panel.py`, `schema_0024.py`.
  Each holds a NEGATIVE assertion (a retired symbol is absent from that
  document); each needs a locus that survives the document's death, not a
  deletion.
- **What becomes available.** D-0063-scoped-component-styles reactivates
  (`creation.css`'s rules descend into per-component scoped `<style>`);
  `shared.css`/`creation.css` may take content-hashed names, which
  TICKET-0066 excluded only because the legacy document links them by fixed
  path; the two budget checks stop having an exempt file.

## Prerequisites

- **TICKET-0068** (Play's stale `WORLD_ID`) should be `done`. If it is
  not, this ticket inherits the bug rather than migrating around it.
- A fresh RECON. The anchors above are `main`-as-of-2026-08-20 and are
  expected to be stale.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] To be authored at intake. Do not treat this section as pre-agreed.

### Live  ->  human gate (Nia)

- [ ] To be authored at intake.
