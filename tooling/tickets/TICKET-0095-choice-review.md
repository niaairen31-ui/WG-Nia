---
id: TICKET-0095
title: Choice review (K1) — Nia reviews the model's choices
type: feature
status: brief
created: 2026-09-27
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
lot_id: LOT-0095-choice-review.md
brief_ids: [A, B, C, D]
current_brief:
schema_version_touched: v2.08
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> K1 principles (locked before 0092):
> - A creator review list shows the model's choices.
> - Agreeing proposes a fact: `appellation` if the surface form is a name,
>   otherwise `reputation` or `statut`. The fact gets the visibility of the
>   cited evidence.
> - Disagreeing lets Nia pick the right entity from a selector, never by
>   typing a name.
> - The natural home is the « Noms à lier » panel. It already has the entity
>   selector, the near names and `writes/facets.record_appellation` (a creator
>   CRUD write, `changed_by="creator_crud"`).

(Handover after TICKET-0094, §4; sequence 0093 → 0094 → 0095.)

## Clarifications resolved (intake)

- TICKET-0094 passed its live gate (Nia, 2026-09-25); A closes its front
  matter.
- Nia ran on prod, in order: `migrate_v2_07_day_mention_choice.py`,
  `apply_ticket_0094_mention_choice_seed.py`,
  `apply_ticket_0093_narration_prompt.py` (2026-09-27).
- Every H2 mention is named (LOT R-09): « agree » only ever proposes an
  `appellation` in this ticket.
- `candidate_ids` / `evidence_fact_ids` are JSON in TEXT; K1 is their first
  UI consumer, which the JSON invariant forbids (LOT R-03).

## Decisions locked (do not re-litigate without Nia)

- **A1** — review state in a new append-only table `day_mention_review`
  (schema v2.08); the latest row per choice is authoritative.
- **B1** — « agree » writes through the creator CRUD path
  (`record_appellation`, `changed_by="creator_crud"`); the click is the
  approval.
- **C2** — the appellation's scope is preselected (`world` if the cited fact
  is known to everyone, else `rencontre`; « evidence not found » →
  `rencontre`) and Nia confirms it in the existing three-way select; the
  evidence's real scopes are displayed beside it.
- **D1** — « disagree » picks the right entity from a selector, with an
  optional « also record as appellation »; the past day is never re-planned.
- **E2** — listed: `accepted`, and `rejected` with a chosen entity;
  `declined`/`failed` and `cast` are not listed; choices from a 409 attempt
  are shown, marked « sans plan ».
- **F1** — candidates are displayed by entity name only.
- **G1** — candidates and evidence become relational (two child tables,
  backfilled from the JSON); the JSON columns remain as an audit copy never
  read in `src/`.
- **H2** — « disagree » may pick « aucune entité connue »: a review row with
  no entity, nothing else written.
- **I1** — « agree » carries a « record as appellation » checkbox, checked by
  default.
- **J1** — only pending choices are listed; the route refuses a second review
  (409).
- Rejected, with reactivation conditions:
  - A2 (mutable worklist): if reading the latest review per choice exceeds a
    measured budget.
  - A3 (no state, derived from facts): no reactivation — it cannot represent
    « agree without writing ».
  - B2 (proposal through `_apply_mutation`): if K1 ever writes without a
    creator click.
  - C1 (faithful copy of the evidence's defaults): if Nia picks a location or
    faction scope that the select lacks, or corrects the preselection on more
    than half of the reviews.
  - C3 (always `rencontre`): no reactivation — it contradicts the locked K1
    principle.
  - D2 (record only): if no appellation is written after ten disagreements.
  - D3 (appellation always written): no reactivation.
  - E1 (accepted only): no reactivation — Y4c and Y8b could never fire.
  - E3 (every verdict): if Nia wants to settle `declined` choices by hand.
  - F2 (name plus matched appellation): if Nia cannot tell, on a review, why
    a candidate was there.
  - G2 (justified exception): no reactivation without amending the
    invariant.
  - G3 (show the chosen candidate only): no reactivation.
  - H1 (entity mandatory): no reactivation.
  - I2 (appellation always written on agree): if Nia never unchecks the box
    over ten reviews.
  - J2 (re-review section): if Nia wants to change a verdict already given.

## Carried forward / open

- **World cascade misses the day tables (pre-existing, measured, LOT R-05).**
  `delete_world_cascade` fails on any world holding a planned day
  (`day_rewrite`, `day_mention_resolution`, `day_mention_choice`, and after
  this ticket the three new tables). A destructive path: its own ticket,
  numbered above 0095.
- Reactivation conditions this ticket makes observable (from 0092 and 0094):
  N11b, N14c, N17c (0092); Y2a, Y4c, Y5a / X1c, Y8b, X1a, X2c, X3a (0094).
  Y2c (a contested `cast` row) cannot fire while `cast` rows are unlisted.
- Named deferrals: re-review UI (J2); `cast` rows and the
  `reputation`/`statut` branch; a location/faction scope picker (C1);
  dropping the JSON audit columns (needs a table rebuild); `route
  authentication` (the cockpit has none, bound to `127.0.0.1:8000`).
- Sequence after K1: Q1b `knowledge.subject` (Y7b) → N6a day-chain widening
  (Y6b) → the lore injection path.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Review storage, child rows and writers hold their shapes  -> verify/checks/day_mention_review_store.py
- [ ] Pending list, evidence, preselection and review route hold their tables  -> verify/checks/choice_review.py
- [ ] Choice records are validated, stored and append-only  -> verify/checks/day_mention_choice_store.py
- [ ] Narrowing, judge, call and wiring hold their case tables  -> verify/checks/day_choice.py
- [ ] Rewrite trace and choice tables stay append-only  -> verify/checks/day_rewrite.py
- [ ] The names panels stay outside the Lore pipeline  -> verify/checks/lore_isolation.py
- [ ] Name index regimes stay confined  -> verify/checks/name_index.py
- [ ] Names, near names and scopes resolve as before  -> verify/checks/name_resolution.py
- [ ] Fact text is read only through the render chokepoint  -> verify/checks/identity_tokens.py
- [ ] UI-visible data is never stored in JSON columns  -> verify/checks/json_ui_boundary.py
- [ ] Schema version agrees across code and doc  -> verify/checks/schema_version_agreement.py
- [ ] Schema doc and changelog partition holds  -> verify/checks/schema_partition.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] No module-level import cycle  -> verify/checks/import_cycle.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] The committed frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Ticket front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] On prod, after `python scripts/backup.py`:
      `scripts/migrate_v2_08_choice_review.py` prints the candidate and
      evidence counts it backfilled, equal to its post-check, and
      `'v2.07' -> 'v2.08'`; a second run changes nothing; the cockpit starts.
- [ ] Lore → « Noms à lier » shows « Choix du modèle à revoir » under the names
      list, with every stored `accepted` choice and every `rejected` one that
      names an entity; a choice from a 409 attempt carries « sans plan ».
- [ ] Agree on a near choice (e.g. « Maelys » → Maelis) with the appellation
      at « Tout le monde »: the row leaves the list; Maelis's sheet shows the
      appellation « Maelys »; a new day naming « Maelys » plans with rung
      `named_exact`, with no new `day_mention_choice` row for it.
- [ ] Disagree on a choice with « Aucune entité connue »: the row leaves the
      list; nothing is added to any entity.
- [ ] Disagree on a choice, picking another entity with the appellation: that
      entity's sheet shows the appellation; the reviewed day is unchanged.
- [ ] Posting the same review twice (e.g. double click) leaves one review row.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
