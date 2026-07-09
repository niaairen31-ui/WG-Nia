# RECON-0018 — faction-agendas (structured intrigues in the tick)

Date: 2026-07-08
Branch inspected: `main` (post TICKET-0017 merge; schema head v1.71,
world-engine-schema.md:3; 0015/0016/0017 closed, live-gates validated)
Mode: report-only. No actions taken.

Locked decisions in force: A1 (faction owners only), B2 (creator CRUD +
tick-proposed creation), model-references-agenda-by-title /
code-derives-the-step, advancement logic in code at apply.

---

## F1 — NpcGoal is the exact table-shape precedent, change_history included

`models.py:338-359` — CheckConstraint enums (`ck_npc_goal_horizon`,
`ck_npc_goal_status`), composite status index, `change_history` JSON
column `NOT NULL server_default '[]'`, created/updated timestamps, and
paired write helpers `write_npc_goal` (writes.py:559) /
`write_npc_goal_status` (writes.py:592 — appends the previous state to
change_history before overwriting; history is sacred). `agenda` and
`agenda_step` follow this shape verbatim, INCLUDING change_history on
both (status transitions are overwrites; the NpcGoal precedent settles
the earlier hesitation — snapshots, not bare updates).

## F2 — The one-active-step invariant has a structural precedent

`models.py:218-221` — `idx_membership_one_primary`: partial unique index
`sqlite_where text("is_primary = 1 AND left_at IS NULL")`. The agenda
equivalent: unique partial index on `agenda_step.agenda_id` where
`status = 'active'` — at most one active step per agenda, enforced by
SQLite itself, not by discipline. Same pattern gives "at most one ACTIVE
agenda per (owner, normalized title)"? NO — titles are prose; the
duplicate guard handles that at propose/apply time (F6), not the schema.

## F3 — The faction briefing has an exact insertion point and the scope
## call an exact extension seam

- `assemble_faction_event_context` (tick.py:449-533) renders LA FACTION /
  POSTURE / MEMBRES / TRÉSORERIE / ÉVÉNEMENTS RÉCENTS via `_section`.
  AGENDA EN COURS slots between POSTURE and MEMBRES (the plan belongs
  with the posture, before the means). Placeholder discipline applies
  (T1): header always present, `(aucune intrigue en cours)` when none.
- The scope call (tick.py:985-1075): faction branch already builds a
  member `roster` and a `locations_index`; it gains an
  `agendas_index` (title.casefold() -> agenda_id for ACTIVE agendas of
  the faction, ambiguous duplicate titles removed — the `_build_roster`
  ambiguity idiom, tick.py:285-326). `_normalize_scope_event`
  (tick.py:535+) receives it and grows two branches; the location branch
  passes an EMPTY index, making agenda types structurally unresolvable
  for location scopes (drop with note) — cheaper and stronger than a
  scope_type conditional alone, though the explicit conditional should
  gate too (belt and braces both machine-checkable).

## F4 — Emit-side identity: the model names the agenda, code derives the step

The briefing shows each active agenda's TITLE + its single active step.
The model's `agenda_step_change` payload carries
`{"agenda": <title>, "action": "complete"|"fail", "outcome": "..."}`.
Normalization: title resolved via `agendas_index` (unresolved -> drop
with note); the STEP is then loaded code-side — the agenda's unique
active step (F2 index guarantees uniqueness; none-active -> drop with
note: the agenda shown has since closed). Emitted payload:
`{"agenda_id": <resolved>, "step_id": <derived>, "action", "outcome"}`.
`step_id` must never be readable from the model payload —
`.get("step_id")`/`.get("agenda_id")` join the rule-3 ban surface
(verify/checks/world_tick.py:118-147 walker; `_FORCED_FIELDS` mechanics
extend, though these are derived-not-forced: the ban is on payload
reads, the dict-value shape stays a bare Name either way).

## F5 — Apply-side: advancement is code; the multi-write is one aggregate

- `agenda_step_change` apply: load the step; STALE GUARD (0014 doctrine,
  canon-existence): step no longer `active` -> error string, Needs
  attention, nothing written (covers duplicate approval, cross-run
  re-proposal, and creator-moved-since — the 0015 stale-from shape).
  Then `write_agenda_step_status(step, action-mapped status, outcome)`;
  then code advances: `complete` -> next `pending` by `step_order`
  becomes `active` (write helper), none left -> agenda `completed`;
  `fail` -> agenda `failed`. All inside the existing per-row SAVEPOINT.
- `agenda_creation` apply: writes ONE agenda + N steps — a parent-child
  aggregate in one SAVEPOINT. This is NOT a one-branch-one-table
  exception of the resource_change kind (two canon DOMAINS,
  cockpit/app.py:930-936): agenda_step has no existence outside its
  agenda; document the distinction rather than invoking the exception.
  Step 1 is born `active` (the creator's approval IS the activation).
- Duplicate guard (`_find_applied_duplicate` tick branch):
  `agenda_creation` duplicate iff an agenda with status `active` exists
  for the same owner with the same normalized title
  (`_normalize_goal_text` reuse, tick.py:913 in cockpit/app.py has its
  own copy — cite whichever the executor touches);
  `agenda_step_change` needs no guard clause — the apply-side stale
  guard is strictly stronger (the 0015 F6 argument, verbatim).

## F6 — Prompt: a new VERSION of pt-world-tick-events, not a new head

The scope call loads `usage="world_tick_events"` (tick.py:1033). The
contract grows from one type to three for faction scopes; location
scopes keep event_creation only. One head, one version bump — the
version text enumerates the agenda types as FACTION-SCOPE-ONLY
(ergonomics; the normalizer enforces). Delivery:
`apply_ticket_0018_prompt_updates.py`, append-version branch (0015/0016
shape — the head exists). Rules to encode: advance ONLY an agenda named
in AGENDA EN COURS; `fail` requires evidence from the briefing (an
event, a member lost, a leak — never boredom); `outcome` is one line of
what happened; at most ONE agenda_creation, 2-5 steps, only when POSTURE
implies a plan no current agenda covers; pair a completed step with an
event_creation materializing its visibility_trace when it would be
publicly perceivable.

## F7 — Creator CRUD: no goal-CRUD route precedent exists; the surface is new

Grep over cockpit routes finds no `/api/npc-goals` CRUD (goals are
managed through gameplay + backfill only, cockpit/app.py:978
`backfill_npc_goals` being the only route). Agendas therefore get the
FIRST dedicated non-entity CRUD surface: `GET /api/agendas` (list with
steps, world-scoped), `POST /api/agendas` (title, owner_entity_id
[validated faction], ordered objectives + optional visibility traces —
step 1 active at creation? NO: creator-authored agendas are born with
step 1 `active` too, symmetric with the applied creation; flagged),
`PATCH /api/agendas/{id}` (status override: abandon/reactivate),
`PATCH /api/agenda-steps/{id}` (edit objective/visibility_trace of
PENDING steps only; status override complete/fail/re-activate —
creator supremacy, all through the writes.py helpers so change_history
is appended). UI: an "Intrigues" panel — executor follows the cockpit's
HTMX idioms; keep it a list + create form + per-step status buttons,
nothing more.

## F8 — Migration v1.72

Two CREATE TABLEs + indexes (incl. the partial unique of F2), idempotent
inspector shape (`scripts/migrate_v1_69_npc_goal.py` precedent, cited by
BRIEF-0016-a and reused for v1.71). No backfill — the world has no
intrigues until Nia or the tick writes one.

---

## Notes for the brief

1. The location scope's empty `agendas_index` + the explicit
   scope_type gate = double structural lock on A1.
2. AGENDA EN COURS shows: per active agenda — title, active step
   objective, its visibility_trace, and the last 2 completed steps'
   outcomes (continuity without full history dump; context stays lean).
3. `fail` fails the WHOLE agenda this step (no branching) — reversible
   creator-side via PATCH reactivate; flagged as drafting decision.
