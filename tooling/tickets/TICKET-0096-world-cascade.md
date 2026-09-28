---
id: TICKET-0096
title: World cascade — deleting a world deletes every world-scoped row, or refuses
type: bug
status: exec
created: 2026-09-28
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [destructive_data]
blast_radius: small
lot_id: LOT-0096-world-cascade.md
brief_ids: [A, B]
current_brief: B
schema_version_touched:
retry_count: 0
slug: world-cascade
---

## Request (verbatim, as Nia stated it)

> A1, B2.

(Handover after TICKET-0095, §2: the world cascade defect, measured in 0095
R-05, jumped the queue ahead of Q1b. A1 = make it 0096; B2 = complete the
cascade and add a G1 check that keeps it complete.)

## Clarifications resolved (intake)

- TICKET-0095 passed its live gate: Nia used Lore → « Noms à lier » on prod
  and recorded an appellation (2026-09-28). A closes its front matter. The
  v2.08 migration ran on prod (the boot guard accepted the DB).
- The defect is wider than the handover said. Measured on a fresh seed
  (LOT R-01): no world with a fact can be deleted, pilot included. The route
  rolls back and answers `ok: false`, so nothing is lost today; nothing can
  be deleted either.
- Nia holds one world with runtime entity types; she does not use the
  feature now and accepts that this world stays undeletable (E1). She has
  throwaway worlds for the live gate and no deletion is urgent.

## Decisions locked (do not re-litigate without Nia)

- **A1** — 0096 is the cascade fix; Q1b follows.
- **B2** — complete the hand-written lists and add a G1 check deriving the
  world-scoped tables from the schema metadata; a table the cascade does not
  account for is red.
- **C1** — the cascade deletes the world's append-only tables too
  (`ledger`, `rencontre`, `skill_resolution`, the day-chain tables): the
  BRIEF-54 exception covers them; a deleted world leaves no reader.
- **D1** — a world owning a `prompt_template` is refused before any delete;
  `prompt_version` stays append-only with no exception.
- **E1** — a world holding an `entity_type` is refused before any delete
  (409, types named); Ddrop1 stays intact.
- **F1** — the check's fixture holds one row in every table the delete
  covers, in two worlds; a table with no fixture row is red.
- **G1** — the four staging tables (`link_batch`, `link_batch_row`,
  `npc_batch`, `npc_batch_row`) are deleted by their owning agent modules,
  called by the delete route in the same transaction; no `writes/` module
  names them.
- Rejected, with reactivation conditions:
  - A2 (Q1b first): if the cascade had reduced to the day chain — it did
    not (R-01).
  - B1 (lists only): if the check ever needs judgment to classify a table.
  - B3 (order derived from metadata): if keeping the lists costs more than
    two updates per ticket.
  - C2 (refuse a world with history): if Nia wants to keep a deleted
    world's history — then an "archive before delete" ticket.
  - D2 (delete the versions too): when a writer of world-scoped templates
    ships.
  - E2 (quarantine the `ext_*` tables, then delete): when Nia wants to
    delete a world holding a runtime type — its own ticket (Ddrop1).
  - F2 (pilot seed plus a day chain): if the fixture becomes the main cause
    of red on unrelated tickets.
  - G2 (an exception in both strata checks): if a third staging agent
    appears and the route's call list itself becomes a source of omission.
  - G3 (`ON DELETE CASCADE` on the staging tables): if a migration rebuilds
    those tables for another reason.

## Carried forward / open

- Deleting a world that holds a runtime entity type (E2): its own ticket,
  touches Ddrop1. Nia's world with runtime types waits on it.
- `routes/mutations.py` imports `delete_world_cascade` and never calls it
  (R-10). Left as is.
- The `pipeline_state.py` docstring (« at least one arrow ») still differs
  from its code (every arrow). Not touched here.
- Sequence after 0096: Q1b `knowledge.subject` (Y7b) → N6a day-chain widening
  (Y6b) → the lore injection path.
- Every 0092/0094/0095 reactivation condition in the 0095 handover §3 stands.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every world-scoped table is deleted, guarded or purged; a populated world deletes; refusals delete nothing  -> verify/checks/world_cascade.py
- [ ] Link staging tables stay out of writes/ and narrowly referenced  -> verify/checks/link_agent_strata.py
- [ ] NPC staging tables stay out of writes/ and narrowly referenced  -> verify/checks/npc_agent_strata.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] prompt_version stays append-only  -> verify/checks/prompt_version.py
- [ ] rencontre is never updated outside a sanctioned path  -> verify/checks/encounter_registry.py
- [ ] Batch purges still delete children first  -> verify/checks/purge_fk_ordering.py
- [ ] Runtime DDL stays in its authority  -> verify/checks/runtime_ddl_guard.py
- [ ] No module-level import cycle  -> verify/checks/import_cycle.py
- [ ] No undefined name under src/  -> verify/checks/undefined_names.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Ticket front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, in Création, delete a throwaway world
      that has facts (and, if you have one, a played day): the modal closes,
      the world is gone from the Header list, and the cockpit still starts
      after a restart.
- [ ] Try to delete the world that holds runtime entity types: the modal
      stays open and shows « Suppression refusée : ce monde porte des types
      d'entité personnalisés (…) » naming them; the world is still there.
- [ ] Deleting the active throwaway world leaves another world active.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
