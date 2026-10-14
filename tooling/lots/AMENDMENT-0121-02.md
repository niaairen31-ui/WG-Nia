# AMENDMENT-0121-02 — corpus gate failures surfaced after brief G

Ticket: TICKET-0121   Lot: LOT-0121 (header authoritative)
Brief in flight: G (done, `e03f761`)   Escalation answered: E-01 (`a69664d`)
Branch: `ticket/0121`. Base for every comparison: `origin/main`; local `main`
is stale at `3e64554` and is not used.

## Precondition (added 2026-10-14)

TICKET-0123 merges first. Before FX-1: `git fetch`, then rebase `ticket/0121`
onto `origin/main` containing that merge. Expected conflicts, and their only
resolution:
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: keep both entries, each above
  the footer (`---` / `*Co-built…*`);
- `tooling/standards/DECISIONS_INDEX.md`: regenerate it, never hand-merge;
- `tooling/standards/FILE_MAP.md`: union of both sides.
Any other conflict is a STOP. After the rebase, U12c is expected green at any
hour: the U12c exclusions below no longer apply, and a red U12c is a STOP.

## What deviated

The lot's gate (e) did not enumerate the existing checks that the lot must
merely pass. Eight full-corpus failures followed, none of them in brief G:

- six checks still read `QuestOffers.svelte` after brief F moved the editor
  into `OfferEditor.svelte`;
- `function_length`: `_finalize_plan` (grown by brief D) and `execute_plan`
  (grown by brief C) exceed 80 lines;
- `name_index` R5: `quest_designer.py` and `quest_lore.py` import the creator
  name regime without being on its allow-list, although H2 and INV-01 name them.

A ninth failure, `lore_usage` U12c, is **excluded** from this amendment. It is
red on `origin/main` between 20:00 and 24:00 America/Toronto regardless of this
ticket, and is owned by TICKET-0123. It is not a defect of this lot.

Decision recorded for E-01: neither (a) nor (b) as written. The
`function_length` baseline does not exist (R-A02-03), so "record in the
baseline" would resurrect a file retired at TICKET-0028. Both functions are
split. The other fixes follow (a).

## Amended RECON (new findings)

### R-A02-01 — the six checks pinned to `QuestOffers.svelte`
Opened: each check's implementation, lines given.
Finding:

| Check file | Rule | Pattern asserted | in OfferEditor | in QuestOffers |
|---|---|---|---|---|
| `attribute_interpreter.py:431,441` | AE1 | `unsaved={draft.unsavedAttributes}`, `.count(...) != 4` fails | 4 | 0 |
| `condition_interpreter.py:1160-1163` | NE1 | exactly one `<ConditionEditor[^>]*role="<role>"` per eligibility, prerequisite, completion | 1/1/1 | 0/0/0 |
| `conditions.py:948-952` | CD1 | `<ConditionEditor cond={draft.eligibility}`, `…{step.prerequisite}`, `…{step.completion}` | 1/1/1 | 0/0/0 |
| `debts.py:1005-1008` | DC3 | `choices?.members?.[draft.giver_entity_id]`, `draft.contact_entity_id = ''` | 1/1 | 0/0 |
| `event_conditions.py:356` | EE6 | `role="failure"` | 1 | 0 |
| `quest_rewards.py:984-985` | RD2 | `<QuestTermRow` | 1 | 0 |

Consequence: each rule is retargeted to `OfferEditor.svelte`, patterns and
counts unchanged. Retargeting alone would let an orphaned component pass, so
one assertion is added that `QuestOffers.svelte` still mounts it.

### R-A02-02 — brief F's move (`f499a4a`)
Opened: line diff of removed vs added lines, indentation ignored.
Finding: markup moved verbatim. Wiring differences only: `refreshValue()`
became the `onchange()` prop; `addTerm` moved into the component; the CSS lost
its `.quest-editor` prefix; `giverMembers` dropped its `draft ?` guard
(`draft` is now a required prop).
Consequence: no check pattern lives in moved wiring; the pattern table above
is complete.

### R-A02-03 — `function_length`
Opened: `tooling/verify/checks/function_length.py`; `git log` for the baseline.
Finding: `tooling/verify/baselines/function_length.json` exists neither on
`ticket/0121` nor on `origin/main`; retired at TICKET-0028 (`1455ff9`). A
missing baseline is an empty exemption set: every function is ≤ 80 lines.

| Function | `ticket/0121` | `origin/main` | Grown by |
|---|---|---|---|
| `_finalize_plan` | `cockpit/day_plan_finalize.py:64`, 95 lines | `cockpit/routes/day.py:549`, 69 | `7a2c6ff` (D, inquiry band): 69 → 95 |
| `execute_plan` | `lore_query.py:157`, 81 lines | `lore_query.py:141`, 77 | `69f9baa` (C): 77 → 81 |

Consequence: both are new debt from this ticket and are split, not exempted.

### R-A02-04 — `name_index` allow-list
Opened: `tooling/verify/checks/name_index.py:57`.
Finding: `CREATOR_ALLOWED` is a set of paths, each addition preceded by a
comment naming its ticket and decision (precedent: TICKET-0112, ID1a). R5
flags `from .name_index import CREATOR` at `quest_designer.py:27` and
`quest_lore.py:22`; the uses are `resolve_named(..., scope=CREATOR)` at
`quest_designer.py:189` and `quest_lore.py:50`.
Consequence: both paths are added, with a comment citing H2 and INV-01.

### R-A02-05 — player-reachable output of the designer
Opened: `quest_designer.py`, `quest_lore.py`, `prose_guard.py`.
Finding: the designer's output reaches a player only after Nia approves the
proposal and the applier writes the offer. `prose_guard.flags` checks title,
summary and objectives against `secret_ids`. Terms (fact, item, counterparty)
and condition lines are not checked by `prose_guard`; condition lines are
filtered by what the character may know (INV-62).
Consequence: REPORT-ONLY item 1 below. No change in this amendment.

## Fix commits (on `ticket/0121`, in this order, one commit each)

**FX-1 — retarget the six checks.**
In each of the six files of R-A02-01, the rule listed reads
`frontend/src/creation/OfferEditor.svelte` instead of
`frontend/src/creation/QuestOffers.svelte`. Patterns, counts and failure
messages' substance unchanged; any string in those rules naming
`QuestOffers.svelte` as the pattern's location now names `OfferEditor.svelte`.
In `conditions.py`, rule CD1 additionally fails unless
`frontend/src/creation/QuestOffers.svelte` contains exactly one `<OfferEditor`.
Mutation, then revert: rename `<OfferEditor` in `QuestOffers.svelte` → CD1 red.

**FX-2 — split `_finalize_plan`** (`cockpit/day_plan_finalize.py`).
Extract the lines added by `7a2c6ff` (the inquiry band) into one private
module-level function in the same module. Pure extraction: same behavior, no
new branch, no reordering. `_finalize_plan` ≤ 80 lines after.

**FX-3 — split `execute_plan`** (`lore_query.py`).
Same rule, for the lines added by `69f9baa`. If those lines alone cannot be
extracted, extract the smallest self-contained block that contains them.
`execute_plan` ≤ 80 lines after. The helper stays in `lore_query.py`, already
in `CREATOR_ALLOWED`.

**FX-4 — allow-list.** In `tooling/verify/checks/name_index.py`, add to
`CREATOR_ALLOWED`, after the TICKET-0112 entry, verbatim:

```python
    # TICKET-0121 (H2, INV-01): the quest designer reads all lore, secrets
    # included; prose_guard flags a secret repeated in a player field.
    "src/world_engine/quest_designer.py",
    "src/world_engine/quest_lore.py",
```

## Anchors to confirm before FX-1

- The six rules and line ranges of R-A02-01 still read `QuestOffers.svelte`.
- `_finalize_plan` is 95 lines and `execute_plan` 81 on `ticket/0121`.
- `CREATOR_ALLOWED` is at `name_index.py:57` with the content of R-A02-04.

A moved anchor is a STOP.

## Decision rights

STOP: an anchor moved. FX-2 or FX-3 would need a control-flow change
(an early `return`, `break` or shared mutable state crossing the extraction
boundary). After FX-4, any corpus failure other than U12c. U12c red outside
20:00–24:00 America/Toronto.
ADAPT: a seventh check reading `QuestOffers.svelte` for a pattern now in
`OfferEditor.svelte` (found by grep) → retarget it as in FX-1, same commit,
and report it.
REPORT-ONLY:
1. Whether `term_line` hides, on a player surface, a fact term whose fact the
   character does not know. Paste the code path.
2. The dropped `draft ?` guard in `giverMembers`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Gate re-run

- (a) Property trace: add one line per R-A02-01 … R-A02-05.
- (e) The six rules now name `OfferEditor.svelte` as their satisfying module;
  `function_length` is satisfied by FX-2/FX-3; R5 by FX-4.

## Done means

- [ ] Four commits FX-1 … FX-4, in order, each separate.
- [ ] CD1 mutation red, then green after revert.
- [ ] `function_length` reports both functions ≤ 80 lines.
- [ ] `corpus_gate.py` green, run outside 20:00–24:00 America/Toronto, or
      green except U12c inside that window, named in the report.
- [ ] Two REPORT-ONLY answers in the report.
- [ ] Ticket amendment log row added; E-01 closed with this amendment's id.

## Ticket amendment log row

| AMENDMENT-0121-02 | G (done) | gate (e) missed 8 existing corpus checks (6 pinned to a moved file, 2 function lengths, 1 allow-list) | none (fix-up commits only) |
