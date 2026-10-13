---
id: TICKET-0115
title: The creator's dashboard -- every review recorded round by round, who proposed it, the metrics in code, the deferrals she watches, the « Suivi » tab and its export
type: feature
status: live-gate
created: 2026-10-13
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0115-creator-dashboard.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched: v2.27
retry_count: 0
slug: creator-dashboard
---

## Request (verbatim, as Nia stated it)

The series request is TICKET-0111's (`tooling/tickets/TICKET-0111-condition-language.md`,
« Request »): H1 locked a creator dashboard -- « un registre de métriques en
code (requête, seuil, code surveillé) », an « Suivi » tab in Création; D1
asked for the acceptance rate of the MJ's proposals; J1 placed it after
0114 and 0119.

In this planning conversation (2026-10-12/13):

> Ticket 0115 de la série. Le ticket 0119 est fait et mergé.

After the RECON and the first decision blocks:

> A3 il me semble très bon pour l'amélioration continue d'avoir des données
> sur ce que je modifie.B2, C1, D1, E2 avec un bouton pour exporter les
> resultats DE date a date (dans le monde réelle) exploitable pour une
> analyse plus poussé par claude code. F2, G1.

> H1, I1, J1, je veux K2 quite a ajouté un brief ou me faire une requête a
> lancé dans claude code pour te fournir une liste.

> L je veux qu'a partir seul les report que je vais nommé comment différé/
> que j'approuve la condition de réactivation sont mis dans la liste. Les
> autres n'y sont pas. H1a

> Je suis en accord avec ta recomandation, mais n'inclus que les Choses des
> autres bloc qui sont clair, structurelle ou claire mesurable

> non, je ne veux pas les clair seul

> 17b, 24c

> 0122 et  M1

## Clarifications resolved (intake)

- **What was lost.** Approving a proposal overwrote its payload with what
  the card sent (`_approve_apply_edited_payload`): « accepted as proposed »
  and « accepted after a correction » could not be told apart. That is the
  measure D2 (auto-applying events) and A1 of 0119 (the tick retyped) wait
  on; A3 keeps it, value by value.
- **Producers.** `proposed_by` already is the producer column; Journée's
  objective event (0119, no model) was stamped `local_ai` like the day
  chain's model output. Production (2026-10-12, Nia's query): 11 proposals
  sit at `approved` -- « Needs attention », an expected state, not a stuck
  apply; 3 typed events in all, so no threshold could speak yet (E2).
- **The deferrals (K2, L).** The decision registry holds 312 lines of
  deferral prose in 150 sections. The candidates were extracted chat-side
  (`CANDIDATS-reports-0115.md`, 121 numbered) and Nia chose: the series'
  deferrals whose condition is not vague, plus, elsewhere, only those
  « claire, structurelle » or « claire, mesurable » -- 20 entries. From now
  on a deferral enters the registry only when a ticket's lot names it.
- **Production.** The migration is additive (one nullable column, two new
  tables); no data is written. A proposal reviewed before v2.27 has no
  review row.

## Decisions locked (do not re-litigate without Nia)

- **A3** -- every review is recorded: the producer's payload kept
  (`original_payload`) and one row per value changed
  (`mutation_review_change`). Rejected: A1 (accepted = applied, edited or
  not: D2 and A1 of 0119 unmeasurable), A2 (an edited flag without what
  changed).
- **H1a** -- a list's elements pair by a natural key per list
  (participants by role, state changes by entity and state, ...); an
  unknown list pairs by position. Rejected: H1b (always by position: a
  reordered list reads as a rewrite), H1c (by every id: a retarget reads as
  removed plus added).
- **B2** -- `proposed_by` is the producer column; Journée's objective event
  becomes `engine`; one closed list, held by a check. Rejected: B1 (a
  separate `producer` column; reactivation: two real producers sharing one
  value that must be told apart).
- **C1** -- the verdict of a step's own condition is recorded at the
  review, before the apply (for M2). Rejected: C2 (deferred: M2's condition
  unverifiable).
- **D1** -- the starting registry: event reviews by producer, the tick
  retyped, step verdicts, the interpreter's outcomes, steps without a day
  NPC (Q2), event leaves under a `not` (absence), what Nia corrects, plus
  encounters (A1'b), lexicon gaps (C3b) and the « Needs attention » queue.
- **E2** -- no threshold: the numbers are shown, Nia judges; plus an export
  from one real-world day to another, for an analysis in Claude Code.
  Rejected: E1 (thresholds with a minimum sample).
- **F2** -- the dashboard lists the deferrals she watches, measured or not.
- **G1** -- 0115 before 0121.
- **I1** -- one JSON document per export. Rejected: I2 (a CSV per table).
- **J1** -- every world or one, the world's name on every exported row.
- **K2, L** -- the deferral registry holds the deferrals Nia named, each
  with its declaring passage; future ones enter by the lot that locks them.
- **M1** -- the tab reads relational columns only; what lives in JSON
  (costs typed into the interpreter, « forme inexistante », a missing
  label) is measured from the export. Rejected: M2 (those signals made
  relational now; reactivation: an analysis of the export shows one of
  them deserves a screen).
- **17b** -- WH3's condition (0114's journal knows the witnesses) is
  reached: TICKET-0122 is reserved for it.
- **24c** -- the payload's relationalization (« First structured UI
  consumer must relationalize »; the review card has edited it field by
  field since 0119) enters the registry as reached, no ticket yet.

## Drafting decisions (made in the lot; Nia may reverse before execution)

1. **A:** a review is one row per call, a « round »: a « Needs attention »
   proposal approved again is round 2; nothing a later round does rewrites
   an earlier one.
2. **A:** `mutation_review` and `mutation_review_change` are world tables:
   the cascade deletes them with their world, like the proposal; the export
   is how an analysis keeps them.
3. **A:** a change's before and after are a scalar's JSON text; a whole
   object or list added or removed carries no value (its path says which).
4. **B:** an empty value equals an absent one (the card writes
   `description: null`); `type_name` and what an apply writes
   (`applied_changes`, `created_entity_id`) are never compared.
5. **B:** a participant pairs by role NAME (the tick names a role, the card
   adds its id); only a unit approve carries an edit.
6. **B:** a faction's agenda has no `doer` to bind: its step verdict is
   `not_judged`, never a guess; `fail` reads the failure condition.
7. **B:** the auto-applied roll (INV-15) records no review: nobody reviewed
   it.
8. **C:** rows Journée's objective event stamped `local_ai` before this
   ticket stay as they are (history).
9. **D:** the days are read on the cockpit's own clock, both included; a
   metric of the world as it stands (conditions, encounters, the queue)
   ignores them and says so (« état actuel »).
10. **D:** a step's verdict counts once per proposal, its first round's,
    against Nia's last decision.
11. **E:** « Suivi » sits before « Review Queue »; no primary action.

## Carried forward / open

- **TICKET-0121** (next): Journée proposes a quest offer from the player's
  day (B-b). Its producer enters `proposal_producers.PRODUCERS` and its
  acceptance shows in « Suivi » from the first day.
- **TICKET-0122** (reserved, 17b): a visible state readable by a player
  about others, now that the journal knows who witnessed a change (WH3).
- **The payload made relational** (24c): reached, no ticket yet.
- **Signals in JSON** (M1): measured from the export; a screen when an
  analysis says so (M2's reactivation).
- **0116** (rank trials), then **0120** (the calendar), per J1.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] v2.27 stores a review round by round  -> verify/checks/mutation_reviews.py
- [ ] Every review path records its round, its changes, a step's verdict  -> verify/checks/review_recording.py
- [ ] Every producer is named; code-made proposals are reviewed  -> verify/checks/proposal_producers.py
- [ ] The metrics, the deferral registry, the export  -> verify/checks/dashboard_registry.py
- [ ] The « Suivi » tab  -> verify/checks/dashboard_tab.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After a backup, `migrate_v2_27_mutation_reviews.py` on a copy of the
      production database, then on production: « Migration v2.27 applied »;
      the cockpit boots.
- [ ] The review queue: a proposal approved unchanged, one edited (a title,
      a participant), one rejected; « Suivi » counts them under their
      producer.
- [ ] A « Needs attention » proposal approved again: the export shows two
      rounds.
- [ ] Journée: an `agenda_step_change` approved; « Objectifs d'étape »
      counts it as confirming or contradicting its condition.
- [ ] « Suivi »: one world, then every world; two days; the reports list
      shows WH3 « atteinte » with TICKET-0122.
- [ ] « Exporter (JSON) » saves a file; opened in Claude Code, it holds the
      proposals with their payloads and rounds, and the interpreter's
      drafts.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
