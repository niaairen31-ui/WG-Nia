# BRIEF — Step "L1 concordance: the occupation renders only where the schedule puts the NPC"

TICKET-0074, brief -c of three. Depends on BRIEF-0074-a and BRIEF-0074-b being
merged. One commit.

## Context

TICKET-0073 shipped the `POURQUOI TU ES ICI` section unconditionally: any NPC
carrying a `kind='standing'` goal renders its occupation in every scene,
everywhere. That collapses the J1 distinction this ticket exists to hold —
schedule is the background, agenda is the foreground — because an innkeeper met
in a forest at midnight still explains itself as an innkeeper on duty. L1 makes
the render conditional on concordance: the occupation appears only when the
NPC's schedule for the current phase points at where the NPC actually is.
Briefs -a and -b supplied the two things L1 was blocked on — a schedule to read
and a phase to read it at.

## Mini-RECON — verify before writing

Measured against `main` at schema v1.91 on 2026-08-23, before -a and -b landed.
Report `file:line` for each. **STOP and escalate** if any does not hold.

1. **The caller enumeration, and it is the one that has burned this project
   three times.** `_npc_context_standing` is defined at `src/world_engine/
   context.py:274` and called from **exactly ONE site**: `context.py:569`,
   inside `assemble_npc_context`. The only other tree references are a docstring
   mention at `context.py:247` and the check file
   `tooling/verify/checks/standing_goal.py`. **Re-run the enumeration yourself
   across the whole repo, including `scripts/` and `tooling/`. If it returns
   anything other than exactly one call site, STOP and escalate** — this brief
   changes the function's signature and a second caller invalidates its plan.
2. `assemble_npc_context` is defined at `context.py:525` with signature
   `(npc_id, interlocutor_id, location_id, session, gathering_id=None,
   relevance_hint=None, player_condition="unharmed", audience_ids=None)`.
   Confirm. It already receives `location_id` — the scene's location — so no new
   parameter is needed to know where the NPC is.
3. **Report `assemble_npc_context`'s own caller count.** TICKET-0073's rejected
   M2 recorded **seven call sites, two with no notion of a turn**. Confirm the
   count with `file:line` for each. **If any caller passes a `location_id` that
   is not the location the NPC is standing in, STOP and escalate**: L1's
   concordance test would be comparing the wrong thing, and choosing between
   `location_id` and `Character.current_location_id` is a design decision this
   brief does not carry.
4. `context.py` is **916 lines / 29 top-level functions** (caps 1000 / 40) —
   84 lines of margin, bought by BRIEF-0073-a. Confirm; report the count after
   this brief's changes.
5. `H_STANDING = "POURQUOI TU ES ICI"` is at `context.py:53`. Confirm. The
   header text does not change.
6. `_npc_context_standing`'s current body selects the single most recent ACTIVE
   `kind='standing'` `NpcGoal` ordered by `created_at` descending, returns `""`
   when none, and otherwise returns `_section(H_STANDING, body) + "\n"` where
   `body` is the goal description followed by the verbatim French framing
   sentence about the scene taking precedence. Confirm; the framing text is
   preserved verbatim and is NOT rewritten by this brief.
7. `tooling/verify/checks/standing_goal.py` is 332 lines. Its R5 asserts the
   standing section never uses `H_GOALS`; its R6 asserts the section is reachable
   from `assemble_npc_context`. **Both must still pass after this brief.**
   Confirm that neither rule inspects the function's arity — if either does,
   report it; the signature change must not silently red a TICKET-0073 rule.
8. `schedule_reads.where_is(npc_id, phase, session, *, is_present)` and the
   `Resolution` dataclass exist from -a, and `Resolution` carries
   `standing_goal_id`, populated only when `source == "schedule"`. Confirm both.
9. `world.current_phase` exists from -a and `PUT /api/world/phase` from -b.
   Confirm. Report how `context.py` should reach the active world — whether an
   existing helper resolves it or whether this brief must query it.

## Scope IN

1. **`_npc_context_standing` gains two parameters**, becoming
   `_npc_context_standing(npc_id, location_id, session)` plus whatever the
   phase is reached through per mini-RECON item 9. The existing standing-goal
   query is unchanged. Before rendering, it runs the concordance test:

   - Read the active world's `current_phase`.
   - Call `where_is(npc_id, current_phase, session, is_present=True)`.
   - Render the section **only if** the resolution's `location_id` equals
     `location_id`. Otherwise return `""`.

2. **The concordance test is a named function**, not an inline expression:
   `_standing_is_concordant(npc_id, location_id, session) -> bool`, with this
   comment verbatim above it:

   ```python
   # L1 (TICKET-0074). The occupation is BACKGROUND: it explains why an NPC is
   # where it belongs. Rendered unconditionally (TICKET-0073's shipped
   # behaviour) it also explains an innkeeper met in a forest at midnight,
   # which collapses the J1 background/foreground distinction this ticket
   # exists to hold. The test compares the schedule's answer for the CURRENT
   # phase against where the scene actually is.
   #
   # Deliberately NOT `resolution.source == "schedule"` (rejected L3): in a
   # live scene with the player the NPC is in a gathering, so the present
   # branch resolves via `gathering` every time and the test would never fire.
   # It is the LOCATION that must agree, not the winning term.
   ```

3. **Absence is not discordance.** An NPC with a standing goal and NO schedule
   row for the current phase resolves to `source="unknown"` and
   `location_id=None`, which is not equal to the scene's location, so the
   section does not render. **This is a behaviour change against TICKET-0073 for
   every existing NPC**, because B1 is sparse and no NPC has a schedule yet. It
   is intended: L1 says the occupation is earned by concordance, and an
   unscheduled NPC has not earned it. Record it verbatim in the docstring, and
   see the live gate — this is the one criterion most likely to surprise.

4. **`assemble_npc_context` passes the two arguments** at `context.py:569`, from
   parameters it already has. No new parameter on `assemble_npc_context`, so its
   own callers are untouched.

5. **Check amendment — `tooling/verify/checks/npc_schedule.py`.** Add R12, with
   an anti-vacuity guard:
   - `_standing_is_concordant` is defined in `context.py` and its body
     references `where_is`.
   - `_npc_context_standing`'s body calls `_standing_is_concordant`.
   - `assemble_npc_context`'s body calls `_npc_context_standing` with at least
     three positional arguments.
   - `_npc_context_standing` has **exactly one** call site across `src/`.
   - Any of the four not located is a FAILURE. R12 proves the concordance test
     is REACHED, not merely that it exists — the "dispatch-site existence proves
     an event fires but not that a listener hears it" lesson.

6. **`standing_goal.py` stays green untouched.** If mini-RECON item 7 finds that
   R5 or R6 breaks on the signature change, fix the CHECK to match the new
   arity — never the code to match the old check — and say so in the report.

## Scope OUT

- **The framing text.** The `POURQUOI TU ES ICI` header and the French framing
  sentence about the scene taking precedence are TICKET-0073's, verbatim,
  unchanged. This brief gates WHETHER the section renders, never WHAT it says.
- **The initiative fragment.** TICKET-0073's N1 put the standing occupation into
  the initiative vote as its own fragment. **Do not gate it on concordance**,
  and do not touch `play_initiative.py`. The vote asks who speaks up among those
  present; that is a different question, and extending L1 to it is a decision
  nobody made.
- **The tick briefing.** `tick_context.py` is untouched.
- **Any change to `assemble_npc_context`'s signature or its callers.** The
  arguments come from parameters it already holds.
- **`Character.current_location_id` as the comparison target.** The scene's
  `location_id` is the comparand, per mini-RECON item 3. If that turns out to be
  wrong, it is a STOP, not a substitution.
- **A per-scene phase snapshot** (`conversation.phase_snapshot`, T-A3). It stays
  an additive migration for a later ticket.
- **Re-opening `npc_goal`,** the schedule table, the write site, or any brief -a
  or -b artifact.
- **The day-resolution chain,** the tick's model-call vocabulary, and
  `schedule_change`.

## Invariants to defend

- **Enumeration-scope discipline.** Mini-RECON items 1 and 3 are the two
  enumerations this brief rests on. Three times during TICKET-0072 a claimed
  enumeration proved incomplete. Both are STOP conditions, not assumptions.
- **Structural, never disciplinary.** R12 proves the test is reached. A comment
  saying the section is gated proves nothing.
- **Exclusion is structural.** The section is withheld at construction — the
  function returns `""` — never by instructing the model to ignore it.
- **Fail-closed.** Unknown resolution means no render. The failure mode of a
  missing schedule is silence, not a stale occupation.
- **Model proposes, code judges.** The concordance test is code reading canon.
  No model call, no prompt, no inference.

## Done means

- [ ] `python -m tooling.verify.checks.npc_schedule` passes including R12, and
      R12 fails when each of its four targets is deliberately broken in turn
      (report four verdicts; revert every break).
- [ ] `python -m tooling.verify.checks.standing_goal` passes.
- [ ] `corpus_gate.py` is green on the whole corpus.
- [ ] `context.py` is under 1000 lines and 40 functions; report both counts.
- [ ] Report `_npc_context_standing`'s call sites and
      `assemble_npc_context`'s call sites, both with `file:line`, as measured
      after the change.
- [ ] Live: an NPC with a standing occupation AND a schedule row placing it at
      the scene's location for the current phase shows `POURQUOI TU ES ICI` in
      its assembled context (visible via the prompt inspection route).
- [ ] Live: the same NPC, met at a location its schedule does not assign for the
      current phase, does NOT show the section — same NPC, same goal, same
      session.
- [ ] Live: advancing the world phase to one where that NPC is scheduled
      elsewhere makes the section disappear at the same location, with no other
      change to the briefing.
- [ ] Live: an NPC with a standing occupation and NO schedule row does not show
      the section. **This is the intended regression against TICKET-0073's
      behaviour** — confirm it reads as correct rather than as a bug, because
      every pre-existing NPC is in this state until a schedule is authored.
- [ ] Live: the initiative vote still receives the standing fragment for an
      NPC whose section is withheld — L1 gates the dialogue section only.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- No schema change. `world-engine-schema.md`, the changelog and
  `EXPECTED_STATIC_SCHEMA_VERSION` are untouched.
- `ARCHITECTURE_DECISIONS.md`: extend the TICKET-0074 section with L1 — the
  concordance trigger, why L3 (`source == "schedule"`) was rejected as
  stillborn, and the explicit note that an unscheduled NPC loses the section
  TICKET-0073 gave it unconditionally.
- No `CLAUDE.md` change.
