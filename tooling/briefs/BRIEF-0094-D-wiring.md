# BRIEF 0094-D — "wiring H2 into the plan route"

Lot: LOT-0094-concordance-h2.md (authoritative on conflict)
Depends on: C (`choose`), A (`write_day_mention_choices`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `src/world_engine/cockpit/routes/day.py:480-499` `_extract_and_concord`
  returning `concordance_result, germ_ids`, with `concord(` then
  `emit_germs(concordance_result.unmatched, pass_play, db)`.
- `:612` `def plan_day(`; `:639` the `_extract_and_concord` call inside
  `try/except LlmParseError` → 502; `:648-649` the ambiguity 409.
- `:76` `from ...writes import (` listing `write_day_rewrite`.
- `src/world_engine/day_choice.py` defines `choose` and `ChoiceOutcome`.
- `src/world_engine/writes/__init__.py` re-exports `write_day_mention_choices`.
- `routes/day.py` is ≤ 965 lines.

## Facts carried

#### R-01 — `concord` and the named rungs
Opened: `src/world_engine/day_concordance.py:134-167`, `344-422`
Finding [M]: `concord` builds the perceiver surfaces once
(`name_surfaces(db, world_id, NameScope("perceiver", known_fact_ids=
frozenset(resolve_levels_for_entity(db, character.id))))`), walks
`MATCHING_RUNGS` per mention, and `_classify` returns `MatchedMention` for one
candidate, `AmbiguousMention(candidate_ids=tuple(sorted(...)))` for 2+ on a
named mention, `CastMention` for 2+ on an inferred one. A mention with no hit
is `UnmatchedMention(rungs_tried, candidate_location_id)`. No partial rung, no
near names. The module docstring (lines 34-39) states the C2-partition
"never resolved by picking".
Consequence: `concord` is not modified. H2 runs on its result (`choose`,
C-07). D corrects the docstring to say the pick now happens after `concord`,
in `day_choice.py`.

#### R-03 — the plan route
Opened: `src/world_engine/cockpit/routes/day.py:36`, `480-499`
(`_extract_and_concord`), `502-516` (`_write_declaration_rewrite`), `612-675`
(`plan_day`)
Finding [M]: `_extract_and_concord` runs the three `extract_*`, `concord`,
then `emit_germs(concordance_result.unmatched, ...)` and `db.add`s the germs
(staged). `plan_day` wraps it in `try/except LlmParseError` → 502
`"day extraction failed: ..."`; then `if concordance_result.ambiguous:` →
409 `_ambiguous_detail(...)` with nothing committed; then writes the rewrite,
selects/emits the plan, and returns. `routes/day.py` is 963 lines, 27
top-level functions; `plan_day` is 64 lines, `_extract_and_concord` 20.
Consequence: `choose` goes between `concord` and `emit_germs` (a chosen
person must not also become a germ). The 409 branch gains X1b's write (C-08).
Growth budget: about 12 lines.

#### R-11 — day-chain structural checks
Opened: `tooling/verify/checks/day_concordance.py:1-50`, `74`, `292-317`;
`tooling/verify/checks/day_rewrite.py:1-24`, `42-43`
Finding [M]: day_concordance R1 forbids `chat(` in `day_concordance.py`; R4
forbids `Entity(` / `Character(` / `NpcSchedule(` in extract/concordance/
plan; `EXPECTED_RUNGS` pins `MATCHING_RUNGS`. day_rewrite W2: no attribute
assignment on, and no `db.delete(` of, a `_TRACKED_MODELS = {"DayRewrite",
"DayMentionResolution"}` instance, vacuity-guarded by requiring a
construction of each; W6: `routes/day.py` calls each `extract_*` exactly
once.
Consequence: the model call lives in `day_choice.py` (R1 untouched).
`"model_choice"` is a stored rung, not a `MATCHING_RUNGS` entry
(`EXPECTED_RUNGS` untouched). A adds `"DayMentionChoice"` to
`_TRACKED_MODELS`. W6 stays true.

#### R-15 — the rung pinning in the frontend
Opened: `grep -rn "named_exact\|rung" frontend/src`
Finding [M]: only `frontend/src/lore/Lore.svelte:172` displays a rung, for
the Lore trace. The Journée view shows no rung.
Consequence: no frontend change; `frontend_build_fresh` untouched.

#### R-18 — CLAUDE.md
Opened: `grep -n -i "concord\|ambigu\|model call" CLAUDE.md`
Finding [M]: no invariant says the concordance never calls a model or never
picks; line 439 (file map) says `day_rewrite.py ... no model call`.
Consequence: no CLAUDE.md invariant edit. D adds one file-map line for
`day_choice.py` right after line 438, if the character budget allows (35.8k
of 38k, lines ≤ 100 chars); otherwise REPORT-ONLY.

## Contracts

#### C-02 — `write_day_mention_choices`
Produced by: A   Consumed by: D
Signature: `def write_day_mention_choices(db: Session, *, world_id: str,
pass_play_id: str, records: list[dict]) -> list[DayMentionChoice]` in
`src/world_engine/writes/pipeline.py`.
Record keys (the family shape, every key required):
`category, surface_form, trigger, candidate_ids (list[str]),
evidence_fact_ids (list[str]), verdict, chosen_entity_id (str|None),
excerpt (str|None), reason (str|None), verdict_detail (str|None),
attempts (int)`.
Behaviour: validate every record first (category, trigger, verdict in their
sets; attempts in (1, 2); accepted ⇒ chosen set; declined/failed ⇒ chosen
None; the two lists are lists of str); any violation raises `ValueError`
with nothing built. Then construct one row per record (lists stored with
`json.dumps`), `db.add_all`, return them. No flush, no commit.
Empty `records` → `[]`, nothing added.

#### C-07 — `choose`
Produced by: C   Consumed by: D
Signature: `def choose(result: ConcordanceResult, declaration: str, character:
Character, db: Session) -> ChoiceOutcome`;
`ChoiceOutcome(result: ConcordanceResult, records: tuple[dict, ...])`.
Behaviour: `requests = choice_requests(result, character, db)`; none →
`ChoiceOutcome(result, ())` with no template read. Else load the
`day_mention_choice` template once (missing → `LlmParseError("day_choice: no
active prompt_template for usage='day_mention_choice'")`, never retried).
Per request: up to 2 attempts of {render user message, `chat`,
`parse_answer`}; `OllamaError`/`LlmParseError` on attempt 1 → attempt 2; on
attempt 2 → verdict `failed`. Otherwise `judge_choice`. Accepted: the
mention leaves `ambiguous` (or `unmatched`) and joins `matched` as
`MatchedMention(mention, entity_id, rung="model_choice")`, appended after the
existing matched. Every request yields exactly one record (C-02 shape;
`evidence_fact_ids` = every candidate's `fact_ids`, flattened in display
order; `verdict_detail` = the judge's detail or the last technical error
text for `failed`).

#### C-08 — route wiring
Produced by: D   Consumed by: live play
- `_extract_and_concord` returns `(concordance_result, germ_ids, records)`:
  `outcome = choose(concord(...), pass_play.declared_action, character, db)`
  before `emit_germs(outcome.result.unmatched, ...)`.
- `plan_day`: if `concordance_result.ambiguous`: `db.rollback()`;
  `write_day_mention_choices(db, world_id=world_id, pass_play_id=pass_play.id,
  records=list(records))`; `db.commit()`; raise the existing 409. Else, right
  after `_write_declaration_rewrite(...)`: `write_day_mention_choices(...)`
  staged in the plan's transaction.
- The 502 wrapper around `_extract_and_concord` is unchanged (a missing
  template surfaces as `"day extraction failed: day_choice: no active
  prompt_template ..."`).

## Context

Everything H2 needs exists; nothing calls it. This brief puts `choose`
between `concord` and `emit_germs`, stores the records with the plan, and on
the 409 path stores them in their own transaction (X1b). It also corrects the
docstrings that still say the concordance never picks.

## Scope IN

1. In `src/world_engine/cockpit/routes/day.py`:
   - add `from ...day_choice import choose` next to the `day_concordance`
     import, and `write_day_mention_choices` to the `from ...writes import (`
     list (alphabetical position);
   - `_extract_and_concord`: return annotation
     `tuple[ConcordanceResult, dict[int, str], tuple[dict, ...]]`; replace
     `concordance_result = concord(mentions, character, db)` with:

     ```python
         outcome = choose(concord(mentions, character, db), pass_play.declared_action, character, db)
         concordance_result = outcome.result
     ```
     and return `concordance_result, germ_ids, outcome.records`. Add to its
     docstring: `H2 (TICKET-0094) runs between concordance and germs: a
     mention the model chose and the code accepted is matched, never a germ.`
   - add, immediately above `plan_day`:

     ```python
     def _record_refused_choices(world_id: str, pass_play_id: str, records: tuple[dict, ...], db: Session) -> None:
         """X1b (TICKET-0094): the 409 path discards the plan's staged work,
         germs included, but keeps the H2 choice records in their own
         transaction, so a refused choice stays reviewable (K1)."""
         db.rollback()
         if records:
             write_day_mention_choices(db, world_id=world_id, pass_play_id=pass_play_id, records=list(records))
             db.commit()
     ```
   - in `plan_day`: unpack `concordance_result, germ_ids, choice_records =
     _extract_and_concord(...)`; in the `if concordance_result.ambiguous:`
     branch, before the `raise`, call
     `_record_refused_choices(world_id, pass_play.id, choice_records, db)`
     (read `pass_play.id` into a local before the call if the executor's
     SQLAlchemy session expires it on rollback); replace the comment above
     that branch with `# BRIEF-0081-a item 8, amended by TICKET-0094 (H2,`
     / `# X1b): an ambiguity the model's choice did not settle still blocks`
     / `# the plan. The staged plan work and germs are rolled back; the choice`
     / `# records are committed on their own.`;
   - right after `rendered, rewrite_row = _write_declaration_rewrite(...)`:
     `write_day_mention_choices(db, world_id=world_id,
     pass_play_id=pass_play.id, records=list(choice_records))`.

2. In `src/world_engine/day_concordance.py`, append to the C2-partition
   paragraph of the module docstring (after "never `ambiguous`."): `Since
   TICKET-0094 (H2) a named ambiguity, and a named mention with no hit but
   partial or near candidates, may still be settled after this module
   returns — by `day_choice.choose`, which asks the model and judges its
   answer. This module itself still never picks.`

3. In `CLAUDE.md`, after the `day_concordance.py` file-map line, add
   `│   ├── day_choice.py        # H2: narrows candidates, asks the model, judges; the only pick`
   (≤ 100 characters; if `claude_md_contract.py` fails on budget, remove it
   and REPORT).

4. In `tooling/verify/checks/day_choice.py`, add static rules W1-W5 (AST,
   vacuity-guarded):
   - W1: in `_extract_and_concord`, a `choose(` call exists and precedes
     the `emit_germs(` call; `concord(` appears only as an argument of
     `choose(`.
   - W2: in `plan_day`, inside the `if` whose test is
     `concordance_result.ambiguous`, a `_record_refused_choices(` call
     precedes the `raise`.
   - W3: in `_record_refused_choices`, `db.rollback()` precedes
     `write_day_mention_choices(` which precedes `db.commit()`.
   - W4: `plan_day` calls `write_day_mention_choices(` exactly once, after
     `_write_declaration_rewrite(`.
   - W5: `day_choice.py` contains exactly one `chat(` call, inside `_ask`, and
     no `db.add(` / `.commit(`.

5. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## H2 IN PLAY (TICKET-0094) -- THE PLAN ROUTE ASKS BEFORE IT GERMS OR BLOCKS (BRIEF-0094-D, no schema change)`:
   the order concord → choose → germs, the table (b3) of the lot, X1b's
   transaction, and the corrected docstrings. Regenerate
   `DECISIONS_INDEX.md`.

## Scope OUT

- Showing choices, excerpts or reasons in the plan response or the Journée
  view (K1 surface).
- The resolve path (`/resolve`): it reads the stored trace; nothing changes.
- `_ambiguous_detail`'s wording.
- Any change to `emit_germs`, `concord`, `day_rewrite`.
- The frontend.

## Invariants to defend

- "Two canon-write paths": nothing here writes canon; `day_mention_choice`
  and `day_mention_resolution` are pipeline tables.
- "History is sacred": the 409 path commits only append-only records.
- Fail-closed: a missing template still surfaces as a 502 through the
  existing wrapper; a choice failure never 502s.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `routes/day.py` would exceed 1000 lines, or `plan_day` 80;
- `day_rewrite.py` W6 fails (extraction count changed);
- the 409 path would commit anything besides choice records.

ADAPT:
- `pass_play.id` raises after `db.rollback()` (expired instance): capture it
  in a local before the call, report.

REPORT-ONLY:
- a stale docstring elsewhere claiming the concordance never picks.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_choice.py` → `PASS:` including W1-W5.
- [ ] `day_rewrite.py`, `day_concordance.py`, `day_concordance_golden.py`,
      `module_budget.py`, `function_length.py`, `claude_md_contract.py` → pass.
- [ ] Mutation: moving the `choose(` call after `emit_germs(` makes W1 fail;
      restore.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `CLAUDE.md` file map (item 3); `ARCHITECTURE_DECISIONS.md` +
  `DECISIONS_INDEX.md` (item 5).
