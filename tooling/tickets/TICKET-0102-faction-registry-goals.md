---
id: TICKET-0102
title: Factions cannot be created, opened or edited — the registry still declares the dropped `goals` column
type: bug
status: live-gate
created: 2026-10-01
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
lot_id: LOT-0102-faction-registry-goals.md
brief_ids: [A]
current_brief:
schema_version_touched:
retry_count: 0
slug: faction-registry-goals
---

## Request (verbatim, as Nia stated it)

> ticket 0102 :Lorsque je veux créer les factions, j'ai un erreur. ensuite,
> quand je rafraichis la page, les factions sont créer, mais je ne peux pas
> y accedé, il est écrit :/api/entities/3d294fd1-4556-4f36-b9b8-120a7e37455f
> -> 500

Planning answers, in order:

> A Si je retire la ligne goal, est-ce que j'aurai encore des faits de type
> Goal pour les factions? B1, C1. Depuis la fiche .

> A1

## Clarifications resolved (intake)

- **Reproduced on a fresh seeded database at `main` `3eda315`:** every
  faction answers 500 on `GET /api/entities/{id}`, the seed's included;
  `POST` and `PUT` answer 500 too. Root cause in LOT R-01..R-03.
- **The flow Nia used is the fiche** (Création → Factions → Enregistrer),
  not the region commit.
- **A faction keeps its goals.** They are `visee` facts since TICKET-0091
  (schema v2.06), offered by the sheet's facts editor under « Visées »;
  every reader (tick context, NPC goal generation, the faction generator)
  reads `visee`, none reads `faction.goals` (LOT R-04). Removing the
  registry line removes only a dead form field.
- **Side effects of the defect, outside the code:** a sheet create commits
  before its response raises, so the faction exists; the role drafts the
  sheet posts after the response were never sent; a retried save created a
  duplicate. Text typed into « Goals » was never stored anywhere — nothing
  to recover.

## Decisions locked (do not re-litigate without Nia)

- **A1** — remove the `goals` field from `ENTITY_TYPE_REGISTRY["faction"]`.
  Rejected: A2, restoring the column (undoes TICKET-0091's lore-as-facts
  decision; reactivates only if that decision is reopened).
- **B1** — a new G1 check, `registry_model_columns.py`: every field of every
  `ENTITY_TYPE_REGISTRY` entry is a column of its model; zero collected is a
  failure. Rejected: B2, a live create/read/update per static type
  (reactivates on a second 500 on an entity route that B1 would not have
  caught); B3, the fix alone (disciplinary).
- **C1** — no data repair in this ticket: Nia deletes the duplicates and
  re-enters the lost roles through the fiche. Rejected: C2, a script
  listing roleless factions created since 2026-09-23.

## Carried forward / open

- None.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every registry field is a column of the model it writes  -> verify/checks/registry_model_columns.py
- [ ] The governed-runtime create/read/update path still round-trips  -> verify/checks/dynamic_ext_crud.py
- [ ] No JSON field spec survives in the CRUD registry  -> verify/checks/json_ui_boundary.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Every ticket's front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus runs green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] Création → Factions → « + Nouveau »: the form shows no « Goals »
      field; with a role in draft and a « Visées » fact, « Enregistrer »
      shows « Saved. », the fiche opens, and both the role and the visée
      are on it.
- [ ] Every existing faction of the Aestia world opens from the list
      without an error; editing its scope and saving shows « Saved. ».
- [ ] Nia has deleted the duplicates and re-entered the roles lost to the
      failed saves (C1; not a code criterion).

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
