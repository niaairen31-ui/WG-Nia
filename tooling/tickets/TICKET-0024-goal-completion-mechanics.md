---
id: TICKET-0024
title: Goal/agenda completion mechanics — prerequisites, effects, role capacities
type: feature
status: live-gate
created: 2026-07-10
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0024-a, BRIEF-0024-b, BRIEF-0024-c]
schema_version_touched: v1.75
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> On a des évènements, des buts et des agendas, tout est là pour les NPC ai
> des objectifs. Cela fait des entrées comme "faire un accord commercial" qui
> peut être réalisé. Je veux qu'on réfléchisse aux implications sur le monde
> et comment cela se reflète concrètement et mécaniquement. Autre exemple :
> gagné la confiance de … ou obtenir le poste X, il faut qu'il y ait une
> contrepartie mécanique pour que cela soit cohérent non ?

Nia's own taxonomy (design intake): (1) **prerequisite mechanics** — "to say
you gained someone's trust, the relation must be 65+, resolved in code";
(2) **consequence mechanics** — contracts, transfers; (3) some
events/objectives legitimately **live in prose only**.

## Clarifications resolved (intake)

- **A1** — Effects are optional-but-solicited on completion. A completion
  with zero prerequisites and zero effects is legitimate (Nia's type 3) and
  is tagged `no_footprint` in `change_history` (creator-visible).
- **B1** — Effect vocabulary v1, closed, three types: `relation_delta`,
  `ledger_transfer`, `role_change`. One type per concrete named case;
  expand at the second concrete case.
- **G1** — Prerequisites: optional `prerequisites` JSON on `npc_goal`, one
  type in v1: `relation_gte` (target entity + threshold on the 1–100
  intensity scale). Creator-CRUD authored only. Checked in code at
  `goal_change complete`; unmet → whole-mutation reject with the measured
  gap. The per-NPC tick briefing MUST show prerequisite state (code
  resolves, injects a single line) so the model does not loop on doomed
  completions.
- **H1** — Anti-double-count, *strip* style: a `relation_delta` effect
  targeting the same entity pair as a **satisfied** `relation_gte`
  prerequisite is silently removed; the rest of the mutation applies; a
  note is recorded. This is the project's FIRST sanctioned partial
  application of a mutation — a named, documented exception to the
  all-or-nothing doctrine (0020 precedent). Strictly bounded: any other
  validation failure remains a whole-mutation reject.
- **I1** — `role_change` requires an ACTIVE membership of the subject NPC
  in the named faction. Joining/leaving a faction is NOT an effect in v1
  (`membership_change` deferred, named in Scope OUT).
- **C2 / J1** — Role capacities: JSON column `role_capacities` on
  `faction`, edited via a line editor in the Faction tab (number field +
  role name per line). Empty limit = unlimited. Capacity counts ACTIVE
  memberships bearing the true `role` (never `cover_role`). Full → reject,
  never evict. Editor pre-fills lines from distinct roles on active
  memberships (empty limits, zero canon writes until save).
- **K1** — The declared role list is a CLOSED vocabulary for the AI path:
  a `role_change` naming an undeclared role is rejected (exact
  case-insensitive resolution, gathering precedent). Creator CRUD stays
  free-form.
- **L2** — The model may declare-and-occupy a NEW role in one completion
  via an explicit `declare: true` flag on the `role_change` effect.
  Invariant: **a role is never created without a holder** — declaration
  (JSON update on `faction.role_capacities`, dict-reassignment rule) and
  occupation (close+reopen membership) are atomic in the same SAVEPOINT.
  A newly declared role's capacity is always empty (unlimited); only the
  creator sets limits. Undeclared role WITHOUT the flag remains a K1
  reject (a typo never silently creates a role).
- **M1** — Ledger rows written by completion effects carry
  `source_type='tick'` (new enum value, documented).
- **N1** — Max 3 effects per completion; more → whole-mutation reject.
- **E1** — Nothing declared at goal creation; effects are decided at
  completion time. (Structured stakes-at-creation deferred.)
- **F** — Both surfaces: `goal_change complete` AND
  `agenda_step_change complete` carry effects.
- Effects apply on `complete` ONLY — never on `fail` or `abandon`.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `faction` table has nullable JSON `role_capacities`; `npc_goal` has nullable JSON `prerequisites`  -> verify/checks/schema_0024.py
- [ ] `_apply_mutation` `goal_change complete` branch rejects when a `relation_gte` prerequisite is unmet, error string contains current and required values  -> verify/checks/prereq_judge.py
- [ ] Effects vocabulary is a closed frozenset {relation_delta, ledger_transfer, role_change}; unknown type -> whole reject  -> verify/checks/effects_vocab.py
- [ ] `role_change` apply path resolves the role against `role_capacities` keys case-insensitively; undeclared without `declare` -> reject  -> verify/checks/role_closed_vocab.py
- [ ] Ledger rows from effects have `source_type == 'tick'`  -> verify/checks/effects_ledger_source.py
- [ ] H1 strip is the only partial-application path; a stripped delta leaves a note  -> verify/checks/h1_strip_bounded.py

### Live  ->  human gate (Nia)

- [ ] Faction tab shows the capacity line editor, pre-filled from active membership roles; saving writes `role_capacities`; empty limit behaves as unlimited
- [ ] A goal with `relation_gte` prerequisite shows its live state in the per-NPC tick briefing preview
- [ ] A tick-proposed completion carrying a valid `ledger_transfer` moves money on approval (both legs visible in the ledger)
- [ ] A `role_change` into a full role is rejected with a readable reason; with `declare: true` on a new role, the role appears in the faction editor with an empty limit and the NPC holds it
- [ ] A prose-only completion (no prereq, no effects) applies normally and is tagged `no_footprint`
