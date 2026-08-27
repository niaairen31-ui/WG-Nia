# AMENDMENT 1 — BRIEF-0074-a, "npc_schedule table, the world phase, and the two reads"

TICKET-0074. Amends BRIEF-0074-a; does not replace it. The original brief is
unedited and stays on disk — read both together. Nothing outside the sections
named below changes.

Raised by: Claude Code, mini-RECON item 13 STOP, before any commit.
Decided by: Nia, code `R-A4`.
Measured against `main`, schema v1.91, 2026-08-23.

## Why this amendment exists

BRIEF-0074-a's mini-RECON item 13 carried a STOP: verify that `AgendaStep`
reaches a location, and escalate if it does not. It does not, and the STOP
fired correctly before any code was written.

- **[M]** `AgendaStep` (`models/canon.py:822-850`): `id`, `agenda_id`,
  `step_order`, `objective`, `status`, `outcome`, `visibility_trace`,
  `created_at`, `updated_at`, `change_history`. No location column.
- **[M]** `Agenda` (`models/canon.py:799-819`): `id`, `world_id`,
  `owner_entity_id`, `title`, `status`, `created_at`, `updated_at`,
  `change_history`. No location column.
- **[M]** `NpcGoal` (`models/canon.py:495-521`): no location column.

The finding is not a missing column. It is that decision C1 named
`agenda_step` as a POSITIONAL SOURCE, and an agenda is not one. An agenda
states an OBJECTIVE — a target — never a place. This amendment corrects C1
rather than deferring a piece of it.

## The correction, in doctrine terms

TICKET-0073 established the taxonomy this ticket builds on: `standing` is
background disposition, `volition` is foreground intent (J1). A schedule is the
POSITIONAL EXPRESSION of a standing disposition. A volition has no positional
expression. Giving one to an agenda would create a SECOND positional authority
competing with the very table this ticket ships.

Nothing is lost by removing the term, on either branch:

- **Present branch.** An agenda's positional consequence already reaches
  `where_is`. The tick moves the NPC, `_mutation_apply_npc_move`
  (`cockpit/mutations.py`) writes `current_location_id` through
  `write_character_location`, and the present branch reads that term ABOVE the
  schedule. The `agenda_step` term was redundant: it would have read an
  INTENTION where a FACT was already read one rank higher.
- **Future branch.** There the term tried to PREDICT where an NPC will be.
  That is the day-resolution chain's work (plan emission, the Python knapsack),
  explicitly Scope OUT of TICKET-0074. An agenda term in the future branch is
  that chain leaking into a pure read.

**There is no reactivation condition on `agenda_step`.** Amendment 0 of this
decision, superseded here, offered one ("a ticket has given `AgendaStep` an
authored location") — it is WITHDRAWN, because it invited building the wrong
thing later. If positional prediction is ever needed, it arrives as a NEW named
term fed by whatever the resolution chain emits, never from an agenda.

## Amended Scope IN item 7

The two precedence tuples in `src/world_engine/schedule_reads.py` replace the
version in the original brief, verbatim:

```python
# C1 -- time-relative precedence. TWO branches, ONE accessor. The present
# is a set of FACTS (a roster, a stored location); a future phase is a set
# of PREDICTIONS, where a stored `current_location_id` is only a last
# known position and must NOT beat the schedule. A single total order
# (rejected C2) lets a stale fact win a phase three days out -- the exact
# failure this table exists to fix.
#
# C1 also named an `agenda_step` term in both branches. It is ABSENT here
# BY DESIGN, not deferred. An agenda states an OBJECTIVE, never a place --
# measured 2026-08-23: no location column on `AgendaStep`
# (models/canon.py:822), `Agenda` (:799) or `NpcGoal` (:495). That is the
# J1 taxonomy holding, not an omission. The schedule is the positional
# expression of a STANDING disposition; a volition has no positional
# expression, and giving it one would create a second positional
# authority competing with this table.
#
# An agenda's positional consequence already reaches this accessor: the
# tick moves the NPC, `_mutation_apply_npc_move` (cockpit/mutations.py)
# writes `current_location_id` through `write_character_location`, and
# the present branch reads that one term ABOVE the schedule. Predicting a
# FUTURE position from an agenda is the day-resolution chain's job (plan
# emission), explicitly Scope OUT of TICKET-0074 -- an agenda term in the
# future branch would be that chain leaking into a pure read.
#
# There is no reactivation condition on `agenda_step`. If positional
# prediction is ever needed, it comes from whatever the resolution chain
# emits, as a NEW named term -- never from an agenda.
#
# These tuples are the ONLY place a source may be named. `where_is`
# iterates them and dispatches through `_SOURCE_LOOKUPS`; it performs no
# lookup of its own. verify/checks/npc_schedule.py asserts the bijection
# between these names and that table's keys, and that `where_is`'s body
# contains no `select(` call.
PRESENT_PRECEDENCE: tuple[str, ...] = (
    "gathering", "current_location", "schedule", "unknown",
)
FUTURE_PRECEDENCE: tuple[str, ...] = (
    "schedule", "last_known", "unknown",
)
```

`_SOURCE_LOOKUPS` has no `"agenda_step"` key. R3's bijection holds at 4 names
and 3 names.

Everything else in Scope IN item 7 is unchanged, including `Resolution`'s
shape, the `"unknown"` terminal (T-D2), and `where_is`'s `is_present`
argument.

## Amended Scope OUT

Three items are added, verbatim. Each is a plausible way to "keep" the term,
and each builds the wrong thing:

1. **Adding `location_id` to `AgendaStep` or `Agenda`.** Both carry
   `change_history` — they are narrative artifacts, not curated config.
   Storing a position there makes the STORY the authority on where an NPC
   stands, in competition with `npc_schedule` and
   `character.current_location_id`.
2. **A `_SOURCE_LOOKUPS["agenda_step"]` that always returns `None`.** The
   tuple would lie about what the accessor consults, and R3's bijection would
   pass on a fiction. A term that cannot resolve is not a term.
3. **Inferring a location from `objective`, `title` or `visibility_trace`** —
   by string match or by model call. `where_is` is a pure read; a model call
   inside it makes canon read differently on every invocation.

## Amended mini-RECON

- **Item 13 is reclassified from STOP to a recorded finding.** The STOP is
  consumed. Report the three shapes as measured; do not re-escalate.
- **Item 8 is answered by the escalation report:** 28 is the highest registered
  site ordinal in `tooling/verify/canon_write_policy.txt` (117 lines), so
  `write_npc_schedule` is the **29th** site. Use that number in its
  `[ALLOWED_SITES]` comment.
- **Items 1, 3, 4, 6, 7, 9, 10, 12 confirmed clean** against current `main`.
- **Still unverified, and required before any code is written:** item 2 (the
  `models/canon.py` budget STOP — the OTHER gate, and it has NOT fired yet:
  draft the `World` change and count the added physical lines before touching
  anything), item 5, item 11, and items 14-20. Item 20's grep is REPORT ONLY
  and still wanted.

## Branch

`ticket/0074` was cut from `ticket/0073`'s tip. TICKET-0073 is merged and `main`
measures v1.91. Confirm `ticket/0074` sits at `main`'s tip, or rebase onto it,
before the first commit.

## Unchanged

Scope IN items 1-6 and 8-14, the Invariants section, Done means, and Docs to
update all stand as written in BRIEF-0074-a. In particular: `who_is_at`,
`unresolved_npcs`, the migration, the CLI companion, and check rules R1-R7 are
unaffected — R3's bijection simply counts fewer names.

BRIEF-0074-b and BRIEF-0074-c are unaffected. Neither referenced the agenda
term.
