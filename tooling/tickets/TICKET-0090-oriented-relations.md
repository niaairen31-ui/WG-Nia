---
id: TICKET-0090
title: Perceiver-oriented relations
type: feature
status: brief
created: 2026-09-22
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write, destructive_data]
blast_radius: large
lot_id: LOT-0090-oriented-relations.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched: v2.04
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> "Aussi lorsque je crée des relations, ce n'Est pas clair qui est A et qui
> est B."

> "C3: je suis a l'aise avec un migration" — "Je suis a l'aise avec C3"

## Clarifications resolved (intake)

- Prod, 2026-09-21: social relations `a_to_b` 92, `b_to_a` 14, `mutual` 67.
  Two unordered pairs hold two rows each, both legitimately asymmetric and
  stored as `a_to_b` with the endpoints swapped: Joran Vey <-> Reike,
  Reike <-> Senna.
- `connects_to` and `controls` are structural relations
  (`context.RELATION_GRAPH_EXCLUDED_TYPES`). They are not touched by this
  ticket's orientation rule.
- Prod, 2026-09-22 (Q1), social relations by direction and `visible_to_b`:
  `a_to_b` 52 FALSE / 40 TRUE, `b_to_a` 8 FALSE / 6 TRUE, `mutual`
  67 TRUE / 0 FALSE.
- Prod, 2026-09-22 (Q2): 2 `connects_to` edges have no typed fact.

## Decisions locked (do not re-litigate without Nia)

- C3 — every social relation row has exactly one perceiver (`entity_a`).
  A `mutual` row becomes two rows. A migration is accepted.
- N1 — one typed `lien` fact per oriented social relation. The relation row
  keeps its mechanical state. `visible_to_b` is replaced by knowledge on
  that fact.
- L2 — the lien facts of existing relations are created by this ticket's
  migration. No prose is rewritten.
- Editor — a relation reads "who feels -> what -> toward whom". No
  direction select. "Reciprocal" creates two independent rows.
- Sequence (I2') — first ticket of: this -> "lore en faits" (G2 + F1) ->
  names (B) -> H2 + K1 -> injection.
- O1 — `direction` is kept. Every social row is `a_to_b` with `entity_a` =
  perceiver. `write_relation` refuses anything else for a social type.
  No CHECK constraint.
- P1 — at most one social row per oriented pair, enforced by a partial
  unique index on `(entity_a_id, entity_b_id)` where
  `type NOT IN ('connects_to','controls')` (RECON-0090 E-2).
- T1 — deleting a relation removes its typed fact, that fact's knowledge
  rows and its scoped defaults, in one transaction.
- V1 — the lien fact's content is a generated statement. `notes` stays on
  the relation row as the perceiver's own view (amends N1's detail; reason:
  RECON-0090 R-11).
- W1 — the write chokepoint creates the typed fact for every relation it
  creates, social or `connects_to`. The migration also backfills the 2
  `connects_to` edges found without one (Q2).
- U3 — inherited `visible_to_b` converts in part: the 40 `a_to_b` TRUE rows
  become the target's knowledge row on the lien fact; the 67 `mutual` rows
  and every FALSE convert to nothing; the 6 `b_to_a` TRUE rows are listed
  in the migration report and left to the new sheet control. Reason: Q1 met
  the reactivation condition recorded for the rejected U2, and RECON-0090
  R-19/R-20 traced where those values came from.

## Carried forward / open

Ordered by how much they block. Full options live in RECON-0090 section 9.

- (none blocking) — U closed as U3 below.
- For ticket "lore en faits", not this one: R-a amended — NPCs learn from
  encounters too, and a relation between two NPCs means they know each
  other. Open nuance there: a one-directional relation (A secretly watches
  B) and whether B then "knows" A.
- Named deferral of this ticket: drop `relation.visible_to_b`. The column
  stays, dead, until a ticket removes it.

## Acceptance criteria

<!-- Final: every decision is locked. One arrow per line — run.py follows
     the first arrow on a line only (RECON-0088 S-1). -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] No social relation is written with a direction other than `a_to_b`  -> verify/checks/relation_orientation.py
- [ ] Every social relation written through the chokepoint has exactly one lien fact  -> verify/checks/relation_orientation.py
- [ ] A delta applied to B->A never moves A->B  -> verify/checks/relation_orientation.py
- [ ] The fact spine still holds with an oriented fixture  -> verify/checks/fact_spine.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Module line budget holds  -> verify/checks/module_budget.py
- [ ] Schema version agrees across constant, doc and changelog  -> verify/checks/schema_version_agreement.py
- [ ] Frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] `set_target_knows` is idempotent both ways  -> verify/checks/relation_orientation.py
- [ ] Known-reachability stays fail-closed on an edge with no fact  -> verify/checks/known_reachability.py
- [ ] Every canon write site is declared, cascade included  -> verify/checks/single_canon_write.py
- [ ] The link stratum still writes only through the chokepoints  -> verify/checks/link_agent_strata.py
- [ ] The Lore surface is still read-only  -> verify/checks/lore_isolation.py
- [ ] Build output committed and fresh  -> verify/checks/static_asset_freshness.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] On Maelis's sheet, each relation reads as a sentence that names who feels what toward whom, from either sheet.
- [ ] "Reciprocal" creates two rows; editing one leaves the other unchanged.
- [ ] After the migration, Reike -> Joran (`méfiance`) and Joran -> Reike (`indifference`) are two rows, each on its own perceiver.
- [ ] A relation deletes from the sheet without error.
- [ ] The Lore dossier shows relations by perceiver, never a raw `a_to_b`.
- [ ] The link agent's staged rows show who feels, and commit as oriented rows.
- [ ] Ticking "<target> le sait" survives a reload; unticking it survives a reload.
- [ ] The migration report lists the 6 `b_to_a` rows whose visibility was not converted.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
