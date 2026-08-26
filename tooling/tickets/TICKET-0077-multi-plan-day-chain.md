---
id: TICKET-0077
title: Multi-plan day chain — parked plans, dedicated plan selection, plan revision
type: feature
status: escalated
created: 2026-08-26
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0077-a-parked-plan-socle, BRIEF-0077-b-verify-gate-retarget, BRIEF-0077-c-plan-selection-and-resume, BRIEF-0077-d-plan-revision]
schema_version_touched: v1.94 -> v1.95
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Ticket 0077, dans la section journee je veux que plusieurs plans puissent etre
> associe a un meme joueur avec un status. Comme cela, le joueur peut commence un
> plan qui n'a rien a faire avec celui de la journee precedente, mais si la
> troisieme journee il veut continue son plan cela fonctionne.

Follow-up decisions, verbatim:

> A1, je veux absolument que le fait de passe d'un plan en pause a un plan actif
> ne bloque pas l'execition de la journee (la mutation est automatiquement
> approuve), B2, C3 dans un appel modele dedie juste a cela). Pas de selection
> direct par le joueur ppour le moment. D2, E3, on reevalue le plan et on le
> modifie en fonction de la nouvelle etat du monde, au besoin. F1 et on voie les
> plans dans l'onglet qui existe deja dans creation. G aucun planfond, H ok.

## Clarifications resolved (intake)

**The scenario, restated as three days.** Day 1: the player declares, plan A is
emitted and becomes their active plan. Day 2: the player declares something
unrelated -> today this returns 409 and demands a manual abandon
(`cockpit/routes/day.py:607-620` [M]); it must instead PARK plan A and open plan
B. Day 3: the player declares a continuation of plan A -> the chain must
recognise A among the player's open plans, park B, and resume A.

**A1 — a parked plan is a new `agenda.status` value.** [M] A player's day plan
IS an `agenda` row owned by the player character plus its `agenda_step` rows
(`writes/goals_agendas.py:578-622`). [M] The status CHECK is currently
`status IN ('active','completed','failed','abandoned')` (`models/canon.py:815-818`)
-- no non-terminal parked state exists. A1 adds `'paused'`.

Rejected: **A2** (relax the one-active-agenda guard for player characters only).
[M] That invariant has four other readers, all NPC-side: `tick.py:103-113`,
`tick_normalize.py:631-637`, `cockpit/routes/mutations.py:199-215`, doctrine
`ARCHITECTURE_DECISIONS.md:5526`. A2 would convert a structural guarantee into a
conditional one that every future reader must remember -- advisory over
fail-closed, the exact inversion of project doctrine. *Reactivation condition:
never for this shape; only if agenda ownership itself is redesigned.*
Rejected: **A3** (a dedicated `day_plan` table separate from `agenda`) --
contradicts the TICKET-0075 locked decision to reuse Agenda/AgendaStep and
duplicates the whole step/requirement/cascade toolchain. *Reactivation
condition: if player plans acquire columns or a lifecycle that NPC agendas
never have.*

**Pause/resume must never block the day.** Nia's requirement is absolute. [M]
`day_mutations.py:12-16` already records the governing precedent: under V1,
creating a plan has no world footprint and stays `write_day_plan`'s direct
write. Parking and activating a plan share that property exactly -- no NPC
sees it, no relation, knowledge or ledger row moves. The transition is
therefore a DIRECT WRITE through `write_agenda_status`, not a queued
proposal: there is nothing to approve, so nothing can block. [M]
`agenda.change_history` is appended on every transition
(`writes/goals_agendas.py:504-514`), so the audit trail is preserved without a
queue row.

**B2 — the day-to-plan link is stored, not derived.** [M] No column ties a
`pass_play` to the agenda it advances; the relation is rederived every time as
"the player's active agenda" (`routes/day.py:464, 717`). Once plans can be
parked, that derivation silently loses which plan a past day advanced. History
is sacred -> `pass_play.agenda_id`, written at plan time.

**C3 — a dedicated model call selects the plan.** Python collects the player's
open plans; ONE model call whose only job is selection cites one of them or
none; Python validates the cited plan is open and belongs to the player. None
cited -> fresh plan. Model proposes, code judges. No player-facing selector for
now.

**D2 — four verdicts.** `continue` (keep going on the currently active plan) and
`resume` (pick a parked plan back up) have different structural effects -- none
versus a two-row status swap -- so they stay distinct verdicts rather than a
branch inside the code.

**E3 — resuming re-evaluates and revises.** A plan parked for N days may have
become partly impossible. On resume the plan is re-emitted against the current
world state and the difference is applied. [M] This needs expressive power the
tree does not have: `_apply_mutation`'s `agenda_step_change` applier accepts
only `complete`/`fail` on the currently active step -- it cannot insert,
reorder or edit a pending one, which is exactly why `_finalize_modify` raises
422 today (`routes/day.py:590-599`). Revision is therefore its own brief.

**F1 + Creation** -- no new Journee UI; the existing Creation intrigues tab
(`frontend/src/creation/Intrigues.svelte`, `intrigues.svelte.js`) is where
plans and their statuses are read and manually driven.

**G** -- no cap on open plans.

**H** -- [M] `cockpit/routes/day.py` is at 946/1000 lines (`module_budget.py`
`MAX_LINES = 1000`). A pure-move commit precedes any addition; new logic lands
in new modules.

**Pre-existing gap this ticket closes.** [M] `PATCH /agendas/{id}` reactivates
to `'active'` through `write_agenda_status` (`cockpit/crud/agendas.py:238-246`),
which does NOT replay `write_agenda`'s one-active-per-character guard -- two
active agendas for one player character are already reachable today. A1 makes
that path routine, so the guard moves to the chokepoint.

**Brief decomposition.**
- **-a (this delivery)** -- parked-plan socle: schema, the chokepoint guard, the
  stored day-to-plan link, `replace` becomes park-and-open, Creation reads and
  drives the parked state. Live-testable on the day-2 case.
- **-b** -- the dedicated selection model call and the `resume` verdict, making
  the day-3 case work from a declaration alone.
- **-c** -- E3: plan revision under `modify`/`resume` against the current world
  state, and the applier expressiveness it requires.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `agenda.status` accepts `'paused'` and rejects any value outside the
      five-value vocabulary  -> verify/checks/parked_plan_guard.py
- [ ] every canon-write site that can set `agenda.status = 'active'` for a
      `character` owner replays the one-active-per-character guard; zero sites
      collected is a FAILURE  -> verify/checks/parked_plan_guard.py
- [ ] `'paused'` is absent from `_AGENDA_GOAL_CASCADE_MAP` (parking a plan never
      cascades a linked goal)  -> verify/checks/parked_plan_guard.py
- [ ] `pass_play.agenda_id` exists and has at least one reader outside
      `models/`  -> verify/checks/parked_plan_guard.py
- [ ] no module in `src/world_engine/` exceeds the 1000-line budget after the
      move commit  -> verify/checks/module_budget.py
- [ ] no function exceeds 80 lines  -> verify/checks/function_length.py
- [ ] `canon_write_policy.txt` gains no new site for table `agenda`
      -> verify/checks/single_canon_write.py
- [ ] schema doc, changelog and live DB agree on the new version
      -> verify/checks/schema_version_agreement.py
- [ ] the day chain's prompt usages are all delivered (regression guard from
      TICKET-0076)  -> verify/checks/day_prompt_delivery.py
- [ ] the reconciliation finalizers are located in day_reconcile_apply.py
      and TICKET-0075's plan-path guards are intact
      -> verify/checks/day_plan.py
- [ ] every check in tooling/verify/checks/ runs and passes
      -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] Day 1: declare, emit a plan, resolve. Unchanged behaviour end to end.
- [ ] Day 2: declare something unrelated. The chain does NOT return 409; plan A
      shows `paused` in the Creation intrigues tab, plan B is active, and
      `POST /api/day/{batch}/resolve` runs without any proposal blocking it.
- [ ] The review queue contains NO row describing the park/activate transition;
      `agenda.change_history` on plan A shows the `active -> paused` snapshot.
- [ ] Day 3 (manual, until -b): pause plan B and reactivate plan A from the
      Creation intrigues tab; the next declaration resolves against plan A.
- [ ] Attempting to reactivate plan A from Creation while plan B is still active
      is refused with a readable message, not an IntegrityError.
- [ ] `GET` on a resolved day still returns its stored account; a day resolved
      before this ticket still resolves (`agenda_id` NULL fallback).
