# AMENDMENT-0121-01 — the designer's drafts, the `subject` census, two contract corrections

Ticket: TICKET-0121 "Journée proposes a quest"   Lot: LOT-0121-journee-quest-designer.md
Brief in flight: none -- BRIEF-0121-E committed on `ticket/0121` (`645ea1a`, `0d74341`, `3fd2c35`), BRIEF-0121-F not started
Trigger: Claude Code's close report on BRIEF-0121-E (four departures from the brief, one skipped review)
Decision: Nia, 2026-10-13 -- AC1; the other items as recommended in the planning chat

Executed in one session on `ticket/0121`, BEFORE BRIEF-0121-F, as one commit
(step 2) after one review catch-up (step 1). No schema change.

## What deviated

1. **Commit 2 of BRIEF-0121-E (`0d74341`) skipped `/review-step` and
   `/close-step`.** CLAUDE.md: every commit goes `/review-step` then
   `/close-step`. Its checks ran and its decision entry is in place.
2. **The designer's drafts and `mark_draft_saved`.** C-10 said the save
   marks the designer's `proposed` drafts `saved` through `_mark_drafts`.
   `mark_draft_saved` only moves an `inserted` draft. The applier now first
   moves to `inserted` "each draft this request wrote", then saves. That
   reaches too far: a draft of a first answer the retry replaced (QD5), and
   a draft the creator already inserted from the card (BRIEF-0121-F), are
   both "drafts this request wrote".
3. **`SUBJECT_FIELD`.** `knowledge_identity.py` K3 counts every `subject`
   reference of `src/world_engine` against `_SUBJECT_CENSUS` -- « a new
   reference is red until someone decides it belongs ». BRIEF-0121-B and
   BRIEF-0121-E derive the column name at run time (`SUBJECT_FIELD`) so
   the census does not see it. That evades the rule instead of satisfying
   it.
4. **`knowers_note`.** C-11 lists it among the `quest_design` values; the
   verbatim template has no `{knowers_note}`. A lot defect: who knows each
   fact is already in `{lore}`, and « Personne ne sait encore » is a note
   written by code.
5. **A condition that proposes a state, an event type or a sorte** is kept
   in `pending_drafts` even when its interpretation is `proposed`. Correct
   and necessary: the payload's `unsaved_attributes` is empty, so the save
   would refuse a tree naming a `new:` attribute. C-10 said pending meant
   `needs_choice` or `refused` only.

## Decisions

- **D-01 (item 1)** -- run `/review-step` then `/close-step` on `0d74341`
  now. A VIOLATION verdict is a STOP, as for any commit.
- **D-02 (item 2)** -- the applier marks ONLY the drafts the approved
  payload names in its `eligibility_draft_id` and `steps[i].*_draft_id`
  fields: such a draft still `proposed` is moved to `inserted`, then saved;
  one already `inserted` is saved; one `discarded` or `saved` is left
  alone. Every other draft of the request -- a first answer the retry
  replaced -- stays as written (it records what the model first said).
- **D-03 (item 3, AC1)** -- no indirection: the field is written `subject`,
  plainly, and every file that holds it gains its entry in
  `_SUBJECT_CENSUS`, with a comment in the existing style:
  `# TICKET-0121, BRIEF-0121-<B|E>: a quest request's subject (what the player seeks) -- never a knowledge key.`
- **D-04 (item 4)** -- C-11 no longer lists `knowers_note`; nothing changes
  in code.
- **D-05 (item 5)** -- accepted as executed; C-10 reads as below.
- **Follow-up, not in this amendment** -- the dashboard's « Interprète de
  conditions » now counts the designer's drafts too (their `attempt_id` is
  a `quest_request.id`). Separating them is noted in the ticket's « Carried
  forward ».

## Contract corrections (the lot header carries the same text)

C-10, `pending_drafts`, now reads:
`"pending_drafts": [{"where": ..., "answer": ...}]` -- a condition whose
interpretation is `needs_choice` or `refused`, or `proposed` while it
proposes a state, an event type or a sorte (`definitions` or `vocabulary`
non-empty): the creator confirms those in the card before it enters the
offer.

C-10, the applier, gains after « writes the offer through
`save_offer_body` »: « the drafts it marks are exactly those of D-02 ».

C-11, step 4: `knowers_note` removed from the values list.

## Scope IN

**Step 1 -- review catch-up (no change).** `/review-step` then
`/close-step` on `0d74341`. Report the verdicts.

**Step 2 -- one commit.**

1. The applier (`cockpit/quest_offer_save.py`, or wherever BRIEF-0121-E
   put the marking): mark the drafts per D-02. Read the ids from the
   approved payload, not from a query on `attempt_id`.
2. Remove `SUBJECT_FIELD` (and any other run-time derivation of the name
   `subject`) from every file of `ticket/0121` that has one; write
   `subject` plainly. Run `knowledge_identity.py`, read the counts it
   reports for those files, and add each to `_SUBJECT_CENSUS` with D-03's
   comment. The count of every file already in the census must not move.
3. `tooling/verify/checks/quest_designer.py`:
   - QD3 gains: a draft the payload names that is already `inserted`
     before approval ends `saved`; a draft of the same request NOT named by
     the payload keeps its outcome.
   - QD5 gains: after approving the proposal from the second answer, the
     first answer's drafts are neither `inserted` nor `saved`.
   - QD2 gains: a scripted condition that defines a new state is in
     `pending_drafts` with `answer.outcome == "proposed"`, its tree `null`.
4. `tooling/standards/ARCHITECTURE_DECISIONS.md`: one entry above the footer,
   `## THE DESIGNER'S DRAFTS ARE SAVED ONLY AS THE APPROVED OFFER NAMES THEM; A REQUEST'S SUBJECT IS COUNTED (TICKET-0121) -- AMENDMENT-0121-01 (BRIEF-0121-e, no schema change)`
   -- D-02, D-03, D-05. Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.
5. The ticket's Amendment log: the row given below. The lot header: the
   contract corrections above, in place, and the line under « Amendments ».

## Scope OUT

- BRIEF-0121-F and G (unchanged by this amendment).
- The dashboard's separation of designer drafts (follow-up).
- `lore_usage.py` U12c: TICKET-0123, its own chat.

## Invariants to defend

- **INV-20** -- `ConditionDraft.payload` is still never read back; the ids
  come from the proposal's payload (its listed exemption).
- **INV-63** -- unchanged; QD3's existing assertions stay.

## Decision rights

STOP:
- step 1 returns VIOLATION;
- removing `SUBJECT_FIELD` changes a stored column name or a payload key;
- a file already in `_SUBJECT_CENSUS` would need its count changed.
ADAPT:
- the marking lives in another module than named: change it there, report.
REPORT-ONLY:
- the census counts added, file by file.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Step 1: `/review-step` and `/close-step` verdicts on `0d74341` reported.
- [ ] `quest_designer.py` PASS (QD1-QD8 with the additions); `knowledge_identity.py` PASS with the new census entries; `quest_requests.py`, `condition_interpreter.py`, `quests.py` PASS.
- [ ] Named mutations, red then reverted: mark every draft whose `attempt_id` is the request (QD5); put `SUBJECT_FIELD` back in one file (K3 red: that file then counts fewer references than its census entry).
- [ ] `grep -rn "SUBJECT_FIELD" src tooling` finds nothing.
- [ ] `/review-step` then `/close-step` on the commit.

## Amendment log row (TICKET-0121)

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0121-01 | none (after E, before F) | E: drafts marked beyond the approved payload; `SUBJECT_FIELD` evading K3; `knowers_note` unused; pending conditions also cover proposed definitions; commit 2 unreviewed | none (F and G unchanged) |
