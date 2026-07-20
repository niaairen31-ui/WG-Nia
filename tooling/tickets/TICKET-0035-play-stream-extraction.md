---
id: TICKET-0035
title: Extract the NPC-initiative cluster out of play_stream.py
type: feature
status: live-gate
created: 2026-07-17
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # pure code relocation: no canon write, no schema, no migration
blast_radius: medium
brief_ids: [BRIEF-0035-a]
schema_version_touched: none
retry_count: 1
---

## Request (verbatim, as Nia stated it)

> [Escalation from the TICKET-0034 pipeline, Claude Code:] `play_stream.py`
> was already sitting at exactly the 1000-line `module_budget.py` cap before
> this ticket touched it. The brief's mandated verbatim comment (required for
> the G1 origin capture) pushes it to 1008 lines, and there's no baseline
> file to fall back on — that mechanism was explicitly retired at
> TICKET-0028. How should `play_stream.py` clear the module-budget cap for
> this step?

## Clarifications resolved (intake)

The TICKET-0034 brief-authoring checked the module budget on the wrong file —
`routes/play.py` (649/1000, fine), where the endpoint lands — not
`play_stream.py` (1000/1000, at the cap), where the `origin_location_id`
capture and its mandated verbatim comment actually land. That is a
brief-generation error, not an ambiguity in the check: `module_budget.py` is
doing exactly its job by refusing to let 1008 lines masquerade as 1000, and
its own docstring names "shortening to fit" as the anti-pattern. The cap is
not dodged; the module is split.

Options considered and rejected during intake:
- **Shorten the mandated comment** — rejected: it is the exact check-dodge the
  `module_budget` docstring warns against; the comment carries the G1
  rationale.
- **Re-add a `module_budget.json` baseline entry** — rejected: it reverses a
  retirement decision taken at TICKET-0028's close; a door `db_write` is not
  the occasion to reopen it.
- **Split `play_stream.py` inside TICKET-0034** — rejected: ~350 lines of
  architectural relocation do not belong mixed into a `db_write` endpoint
  commit, and it would blow TICKET-0034's `blast_radius`.

Resolution: a dedicated relocation ticket (this one), sequenced BEFORE
BRIEF-0034-c. Once it lands, `play_stream.py` has headroom and the verbatim
comment fits with no discussion.

**Execution order (recorded here and in TICKET-0034):**
0034-a -> 0034-b -> **0035 (this ticket)** -> 0034-c -> 0034-d.

The BRIEF-0034-c work Claude Code already completed (endpoint, capture,
`spatial_door_travel.py`, red-tests) is correct and stays on the `ticket/0034`
branch unpushed; it re-lands unchanged after this extraction, now comfortably
under the cap.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `module_budget.py` green on BOTH `play_stream.py` and the new
      `play_initiative.py` — neither exceeds 1000 lines / 40 defs
      -> verify/checks/module_budget.py
- [ ] Full verify suite green with NO baseline file re-added and NO entry
      added to any baseline — the split, not an exemption, is what clears the
      cap
      -> verify/checks/module_budget.py
- [ ] `single_canon_write.py` green with ZERO change to
      `canon_write_policy.txt` — this ticket relocates code, it does not add,
      move or remove a sanctioned canon-write site (`_perform_travel` stays in
      `play_stream.py`)
      -> verify/checks/single_canon_write.py
- [ ] No import cycle: `play_initiative.py` imports from `play_stream.py`
      nothing; `play_stream.py` imports the initiative entrypoint from
      `play_initiative.py` (one-way edge)
      -> verify/checks/import_cycle.py (if present; else asserted in the live smoke)

### Live  ->  human gate (Nia)

- [ ] A live Play session where an NPC-initiated turn still fires:
      player says something in a multi-NPC gathering -> the initiative vote
      runs -> an NPC acts on its own initiative -> the MJ narrates it. Byte-
      for-byte the same behavior as before the split.
- [ ] Group speaker selection still works: in a gathering with several NPCs,
      the responder is still chosen (the `_select_group_speaker` path, called
      from `play.py`).
- [ ] The diff is relocation-only: `git diff` shows functions moved and
      import lines repointed, no function BODY changed.
