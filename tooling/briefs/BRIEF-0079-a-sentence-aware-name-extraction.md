# BRIEF — Step "Sentence-aware name extraction"

## Context

TICKET-0079. `judge_narration` rejected a live day with
`unauthorised name(s) not in authorised_names: Dirigeants, Sans, Serviteurs`.
`sans` is in `_FUNCTION_WORD_STOPWORDS` (`day_narration_guard.py:72`), so it
can only have been reported through the `len(run) > 1` bypass at `:120`. The
cause is measured: `_TOKEN_RE` (`:55`) captures `[.!?]+` as tokens, but `:99`
filters them out before the run loop, so the punctuation branch is dead and a
run spans full stops. `"... les Serviteurs. Sans Dirigeants ..."` becomes the
single run `"Serviteurs Sans Dirigeants"`.

This step fixes only what the extractor gets provably wrong. It does NOT
address capitalised common nouns (`Dirigeants`, `Serviteurs` still report after
this step) -- that is BRIEF-0079-b's prompt and repair work. Decision `A2`.

## Scope IN

1. **`src/world_engine/day_narration_guard.py` -- split tokenisation from run
   building.** Introduce a module-level helper:

   ```
   def _sentences(prose: str) -> list[list[str]]:
   ```

   It strips `[MARKER]` tags with `_MARKER_RE` exactly as `extract_names` does
   today (`:98`), tokenises with `_TOKEN_RE`, and returns a list of
   word-token lists: a token whose first character is in `.!?` terminates the
   current list and is itself discarded. A terminator that produces an empty
   list contributes nothing (no empty lists in the returned value).

2. **`extract_names` builds runs per sentence.** `extract_names` calls
   `_sentences(prose)` and runs the existing run-building loop (`:102-122`)
   once per returned token list, unioning the results. `extract_names` must
   contain no `_TOKEN_RE` reference and no `_MARKER_RE` reference of its own
   after this change -- both move into `_sentences`. The loop body itself is
   otherwise unchanged: same capitalisation test, same `_CONNECTORS` bridging.

3. **`src/world_engine/day_narration_guard.py` -- function-word edge
   stripping.** Introduce:

   ```
   def _strip_stopword_edges(run: list[str]) -> list[str]:
   ```

   It removes words from the FRONT of the run while the first word's
   `casefold()` is in `_FUNCTION_WORD_STOPWORDS`, then from the BACK while the
   last word's `casefold()` is in `_FUNCTION_WORD_STOPWORDS`, and returns what
   remains (possibly empty). Interior words are never touched: a connector
   inside a run (`"Joran de Vey"`) must survive, and an interior oddity
   (`"Serviteurs Sans Dirigeants"`, if one is ever built inside a single
   sentence) must still be reported rather than silently trimmed.

4. **Apply the strip before the keep decision.** In `extract_names`, each built
   run passes through `_strip_stopword_edges` before line `:120`'s test. An
   empty result is discarded. A result of length 1 is kept (it is a non-
   stopword by construction after stripping). A result of length > 1 is kept.
   `_strip_stopword_edges` is called exactly once in the module.

5. **Update the module docstring** (`day_narration_guard.py:18-42`) to state the
   new rule. Two points must be written explicitly, because they are the
   invariants a future reader is most likely to break:
   - runs are built per sentence and never span a sentence-final `.`, `!` or `?`;
   - **position gating remains rejected**: a single capitalised word that opens
     a sentence is still a candidate, and is still discarded only by the
     `_FUNCTION_WORD_STOPWORDS` test, at any position. Restate that this was
     live-tested wrong (the existing text at `:29-36` is the source; keep its
     substance).

6. **New check `tooling/verify/checks/day_name_extraction.py`.** A behavioural
   unit check on the precedent of `geometry_unit.py` and `placement_unit.py`:
   `ROOT`/`SRC` bootstrap, `sys.path.insert(0, str(SRC))`, then
   `from world_engine.day_narration_guard import extract_names`. Same
   `FAILURES`/`fail()`/summary-`PASS` idiom. Golden cases, each a hard
   assertion:

   - **G1 sentence break.** `"[BLOQUE] Kaela franchit la cour et croise les serviteurs. Sans invitation, elle repart."`
     -- no returned run contains more than one of the words `serviteurs`,
     `Sans`, `Kaela` (case-sensitively as returned); specifically, no returned
     run's word list contains `"Sans"` at all, since `Sans` here is a lone
     sentence-opening stopword.
   - **G2 edge strip.** `"Les Serviteurs la renvoient."` -- the union of all
     returned runs' words does not contain `"Les"`.
   - **G3 no position gating.** `"Lorian entre. Kaela le suit."` -- both
     `"Lorian"` and `"Kaela"` are returned as runs.
   - **G4 non-vacuity.** `"Kaela parle a Joran Vey au Marche aux Cendres."` --
     the returned set contains `"Kaela"` and `"Joran Vey"`, and at least one
     run whose words include `"Marche"`.
   - **G5 connector interior.** `"Joran de Vey ecoute."` -- `"Joran de Vey"` is
     returned as a single run.

   Vacuity guard: the check counts the golden cases it actually executed; a
   count of zero is a FAILURE, not a pass. Exit non-zero on any failure with
   one `FAIL:` line per failing case; exit zero with one summary `PASS:` line.

7. **Register the check.** No change to `tooling/verify/run.py` is needed --
   it resolves checks from the ticket's `->  verify/checks/<name>.py` arrows.
   Confirm `TICKET-0079`'s Machine-checkable arrows resolve by running
   `run.py --ticket TICKET-0079` (see Done means).

## Scope OUT

- **The capitalised common-noun class.** After this step, `Dirigeants` and
  `Serviteurs` STILL report as unauthorised. Do not add a French common-noun
  lexicon, a determiner exemption, a plural heuristic, a
  lowercase-elsewhere-in-the-prose test, or any other widening of what the
  extractor discards. Decisions `B1` and `B3` were considered and rejected in
  TICKET-0079; reopening them here reverses `day_resolve.py:141-146`.
- **Position gating.** Do not discard a candidate because it opens a sentence.
  The new `_sentences` helper makes sentence position knowable for the first
  time, which makes this temptation newly available; it is still forbidden.
- **The prompt.** `scripts/seed_pilot.py` is untouched by this brief.
  BRIEF-0079-b owns every prompt and seed change.
- **The repair pass.** No `repair` function, no `MAX_REPAIR_ATTEMPTS`, no
  second model call. BRIEF-0079-b owns it.
- **`JudgeVerdict`.** Do not add `offending_words` here. BRIEF-0079-b owns the
  dataclass change and the 422 body.
- **`freeze_facts` and factions.** `day_resolve.py:409-411` and `:413` drop
  matched faction entities. This is a known hole, deferred as `E2'` in
  TICKET-0079. Do not widen `freeze_facts`.
- **`_missing_band_markers` and the step checks.** Untouched.
- **Refactoring `judge_narration`'s three-check sequence.** Untouched.

## Invariants to defend

- **Anti-vacuity (R5, `day_narration_guard.py:157-162`).** Edge stripping can
  empty a run. If a whole prose reduces to zero candidates, the existing
  zero-names guard must still fire as a FAILURE. Do not add a "no candidates
  means nothing to check" early return anywhere.
- **`day_narration` R4 (the judge is Python).** No `chat(` may appear in
  `day_narration_guard.py`.
- **Module budget.** `day_narration_guard.py` is 193 lines; the cap is 1000 and
  no function may exceed 80 lines. `extract_names` gains a nesting level --
  keep it under 80 by extracting `_sentences` and `_strip_stopword_edges` as
  specified rather than inlining them.
- **The rejected alternative is load-bearing.** `day_narration_guard.py:29-36`
  documents that position gating was tried and live-tested wrong. That text
  must survive this rewrite in substance.

## Done means

- [ ] `_sentences` and `_strip_stopword_edges` exist as module-level functions
      in `day_narration_guard.py`; `extract_names` calls each, and contains no
      `_TOKEN_RE` or `_MARKER_RE` reference of its own.
- [ ] `python tooling/verify/checks/day_name_extraction.py` exits 0 and prints
      one `PASS:` line naming the five golden cases.
- [ ] Deliberately breaking the sentence split (reverting step 2) makes G1 FAIL
      and the script exit non-zero -- run this once and record the output in the
      execution notes. A check that cannot fail is the outcome to avoid.
- [ ] `python tooling/verify/checks/day_narration.py` still exits 0 (R1-R18
      unbroken).
- [ ] `python tooling/verify/run.py --ticket TICKET-0079` runs and reports
      `day_name_extraction.py` as PASS. Other checks linked by the ticket may
      FAIL at this point -- BRIEF-0079-b has not run yet. Record the verdict
      JSON as-is; do not edit the ticket to make it green.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `day_narration_guard.py`'s module docstring -- Scope IN item 5. This is the
  primary doc surface for this step; the extraction heuristic is documented
  nowhere else.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- append one entry recording
  that the extractor is sentence-scoped and edge-stripped, that position gating
  stays rejected, and that the capitalised common-noun class is handled by the
  prompt and the repair pass rather than by a looser judge (naming
  `day_resolve.py:141-146` as the upheld precedent).
- No schema change. `world-engine-schema.md` is untouched and no version number
  is consumed.
