# BRIEF — Step "Blocked band and narration"

## Context

After BRIEF-0078-a a knowledge gate is anchored in canon, but an anchored gate
the player genuinely does not meet still empties the day: `budget_cut` breaks
at the first unmet step, `resolve_steps` returns an empty list, and the account
becomes a code-rendered one-liner because `judge_narration` refuses a zero-step
fact sheet. Nia wants a real narrative for that day. This step gives the
blocked step a fourth band, `blocked`, so it becomes an OUTCOME rather than an
absence: it enters the fact sheet, carries the marker `[BLOQUÉ]`, and goes
through `narrate`/`judge_narration` like every other beat. The zero-outcome
case becomes impossible by construction, which retires the bypass **without
weakening the judge by one line**. Proposing the rumor the player learns from
the block (D3) is NOT in this step -- that is BRIEF-0078-c.

## Mini-RECON (measured against the fresh tarball, `main`)

All anchors verified against the tree. **If any of these contradicts what you
find, STOP and escalate -- do not adapt the brief yourself.**

- [M] `day_resolve.py` -- 402 physical lines. `StepOutcome` at 93-103
  (`band: str  # "success" | "partial" | "failure"`, `requirement_verdicts`,
  `canon_ids`), `StepFact` at 112-118 (`objective`, `band`, `dice`,
  `modifier`, `total`), `FactSheet` at 121-147, `_RolledStep` at 150-156,
  `_step_player_tier` at 159-171, `_TERMINAL_AGENDA_STEP_STATUSES` at 174,
  `_load_evaluated_steps` at 177-208, `_roll_included_steps` at 211-234,
  `_truncate_on_failure` at 237-255, `resolve_steps` at 258-286,
  `blocked_reason` at 289-306, `outcome_line` at 309-319, `freeze_facts` at
  322-380 (the `StepFact` build at 358-367), `fact_sheet_dict` at 383-402.
- [M] `day_resolve.py:283-284` -- the veto truncation:
  `included = included[: max(0, veto_retained)]`.
- [M] `day_narration.py` -- 174 lines. `BAND_MARKERS` at 50
  (`{"success": "[RÉUSSITE]", "partial": "[PARTIEL]", "failure": "[ÉCHEC]"}`),
  `_render_fact_sheet` at 77-93 (the per-step line at 80-82), `narrate` at
  96-119.
- [M] `day_narration_guard.py` -- 193 lines. `_missing_band_markers` at
  126-138 keys off `BAND_MARKERS[band]` and compares `prose.count(marker)`
  against a `Counter` of fact-sheet bands. `judge_narration` at 153-193; the
  zero-steps anti-vacuity is 184-185; the zero-names anti-vacuity is 158-162.
- [M] `resolution.py:26` -- `band: str  # "failure" | "partial" | "success"`;
  `resolve_physical` at 32-43 produces those three only.
- [M] `band` is constrained by NO CHECK constraint and no schema column --
  confirmed absent from `world-engine-schema.md`.
- [M] `cockpit/routes/day.py:816-832` -- the zero-outcome branch;
  `resolve_steps` called at 807; `freeze_facts` at 814;
  `_narrate_and_judge` at 833; `prose` built at 829.
- [M] `day_mutations.py:92-93` -- `_step_action` returns `"fail"` when
  `outcome.band == "failure"` and `"complete"` otherwise;
  `_emit_agenda_step_change` at 96-118; `_emit_knowledge_change` at 121-155
  short-circuits on `_step_action(outcome) != "complete"`.
- [M] `tooling/verify/checks/day_plan.py` R21 asserts
  `_mutation_apply_agenda_step_change`'s action tuple is exactly
  `("complete", "fail")`.
- [M] `scripts/seed_pilot.py:1855-1881` -- `DAY_NARRATION_SYSTEM_PROMPT`; its
  marker rule enumerates the three markers literally
  (`[RÉUSSITE], [PARTIEL] ou [ÉCHEC]`). `DAY_NARRATION_USER_TEMPLATE` at
  1883-1890 substitutes `{declaration}` and `{fact_sheet}`.
- [M] `scripts/apply_ticket_0077_plan_select_seed.py` -- the precedent for
  reseeding a prompt into an already-provisioned world.
- [M] `prompt_store.current_prompt` is the version reader; `prompt_registry`
  holds `day_narration`'s entry with its `call_sites`.

**STOP conditions.** Stop and escalate, without writing code, if: (1) any
anchor above is materially different; (2) `resolve_physical` turns out to be
able to return a band outside the three -- the fourth band would then not be
exclusively Python-assigned; (3) `BAND_MARKERS` has acquired a consumer
outside `day_narration.py`/`day_narration_guard.py`; (4) the live DB's active
`day_narration` prompt version differs from
`scripts/seed_pilot.py:DAY_NARRATION_SYSTEM_PROMPT` -- reseeding would then
overwrite an edit Nia made by hand, and she must be asked first.

## Scope IN

Items 1-5 are one commit. Item 6 (the prompt reseed) is its own commit. Item 7
is the verify commit.

1. **`BLOCKED_BAND: str = "blocked"`** as a module-level constant in
   `day_resolve.py`, placed next to `_TERMINAL_AGENDA_STEP_STATUSES`. It is
   assigned by this module only. `resolution.py` is NOT touched --
   `resolve_physical` keeps its three bands, and the comment on
   `StepOutcome.band` (line 101) is updated to name the fourth as
   Python-assigned, never rolled.

2. **`StepFact` gains `blocked_detail: Optional[str] = None`**
   (`day_resolve.py:112-118`), defaulted so every existing construction stays
   valid. `fact_sheet_dict` (383-402) serializes it in the per-step dict as
   `"blocked_detail"`. A pre-0078 `pass_play.history` entry read back simply
   lacks the key -- do not add a migration for stored history.

3. **`requirement_detail_fr(verdict) -> str`** in `day_resolve.py`: a pure
   function mapping `verdict.type` (the field BRIEF-0078-a added) to
   player-facing French, through a module-level dict whose key set is exactly
   `REQUIREMENT_TYPES`. An unknown type RAISES `ValueError` -- the same
   fail-closed posture `evaluate_requirements` already takes
   (`day_plan.py:245-246`). The four strings, VERBATIM:

   ```python
   _BLOCKED_DETAIL_FR: dict[str, str] = {
       "knowledge": "il lui manque encore ce qu'il faut savoir sur « {required} »",
       "resource": "il ne dispose pas des moyens nécessaires",
       "relation_gte": "ses appuis ne sont pas encore assez solides pour cela",
       "location_reachable": "l'endroit n'est pas accessible depuis là où il se trouve",
   }
   ```

   Only the `knowledge` entry interpolates `{required}`. No English machine
   text from `Verdict.reason` may reach this function's output.

4. **`_append_blocked_step(ordered_steps, evaluated_steps, budget_result, rolled, outcomes) -> None`**
   in `day_resolve.py`: pure (no `db`, `select(`, `chat(`, `datetime`,
   `randint` in its body -- everything it needs is precomputed by
   `resolve_steps`). It appends AT MOST ONE `StepOutcome` and only when ALL
   THREE conjuncts hold:

   1. `budget_result.first_excluded_index is not None` **and**
      `not evaluated_steps[first_excluded_index].met` -- a budget-only cut is
      not a block;
   2. `len(rolled) == budget_result.first_excluded_index` -- the feasibility
      veto did not truncate further; when it did, the veto owns the day's
      reason and no blocked beat is invented;
   3. `len(outcomes) == len(rolled)` -- `_truncate_on_failure` did not fire;
      a step that FAILED mid-day already ends the walk, and the next step's
      gate is not what stopped the day.

   The appended outcome carries `band=BLOCKED_BAND`, `verdict=None`,
   `requirement_verdicts` = that step's full verdict tuple, `canon_ids` built
   the same way `_roll_included_steps` builds them (211-234), and the real
   `agenda_step_id`/`step_order`/`objective`/`domain` from the excluded step.

5. **`resolve_steps` calls it** (`day_resolve.py:258-286`) as the last step,
   after `_truncate_on_failure`. `blocked_reason` (289-306) is DELETED --
   an unused reader is structure without a reader -- along with its import at
   `cockpit/routes/day.py:45` and the zero-outcome branch at 816-832, whose
   body is replaced by a fail-closed guard:

   ```python
   if not outcomes:
       raise HTTPException(
           status_code=500,
           detail="day resolution produced zero outcomes -- the blocked band should make this unreachable",
       )
   ```

   Keep the veto-retained-zero case working: when
   `veto_retained == 0 and python_retained > 0`, conjunct 2 above is false, so
   no blocked beat is appended and `outcomes` is empty -- that path must
   therefore keep its OWN code-rendered prose, moved above the new guard and
   citing `feasibility_entry["reason"]` exactly as it does today at 826-827.
   The guard fires only when neither a step nor the veto explains the
   emptiness.

   `freeze_facts` (358-367) populates `blocked_detail` for a blocked outcome
   by joining `requirement_detail_fr` over that outcome's unmet verdicts with
   `" ; "`, and leaves it `None` for every other band.

   `day_mutations._step_action` (92-93) is widened so a blocked outcome maps
   to neither `"complete"` nor `"fail"`: `_emit_agenda_step_change` returns an
   EMPTY list for it. A blocked step was never attempted, so its `AgendaStep`
   must stay exactly as `pending`/`active` as it was.
   `_mutation_apply_agenda_step_change`'s action vocabulary stays
   `("complete", "fail")` -- R21 must keep passing untouched.

6. **`BAND_MARKERS` gains `BLOCKED_BAND: "[BLOQUÉ]"`**
   (`day_narration.py:50`, importing the constant from `day_resolve`), and
   `_render_fact_sheet`'s per-step line (80-82) appends, when
   `step.blocked_detail` is set, VERBATIM:

   ```
    Le personnage n'a pas pu l'entreprendre : {blocked_detail}.
   ```

   `DAY_NARRATION_SYSTEM_PROMPT` (`scripts/seed_pilot.py:1855-1881`) gains the
   fourth marker in its existing marker rule -- **one clause, no new rule** --
   so the rule reads, VERBATIM:

   ```
   - Pour chaque étape listée, commence sa phrase par le marqueur exact entre \
   crochets correspondant à son issue : [RÉUSSITE], [PARTIEL], [ÉCHEC] ou \
   [BLOQUÉ], puis raconte ce qui s'est passé, dans l'esprit de cette issue. \
   Pour une étape [BLOQUÉ], raconte que le personnage s'y est heurté et ce \
   qu'il en a entrevu, en te servant de la raison donnée sans la recopier.
   ```

   Ship `scripts/apply_ticket_0078_narration_seed.py`, modelled on
   `scripts/apply_ticket_0077_plan_select_seed.py`, writing a NEW prompt
   version for usage `day_narration` -- never editing the existing version row
   in place (history is sacred).

   `judge_narration` is NOT modified. Its zero-step anti-vacuity (184-185) and
   zero-name anti-vacuity (158-162) stay byte-identical;
   `_missing_band_markers` picks the new marker up automatically because it
   keys off `BAND_MARKERS`.

7. **Verify.** Extend `tooling/verify/checks/day_narration.py`, continuing its
   own numbering, each anti-vacuity guarded:
   - `BAND_MARKERS`' key set is exactly the four bands, and `"[BLOQUÉ]"` is
     its value for `BLOCKED_BAND`.
   - `day_narration_guard.judge_narration` still contains a zero-length
     `fact_sheet.steps` branch returning `passed=False`; zero such branches
     located is a FAILURE. Do NOT write a check that permits an empty fact
     sheet -- that would encode the opposite of this brief.
   - `_BLOCKED_DETAIL_FR`'s key set equals `REQUIREMENT_TYPES` in both
     directions, and `requirement_detail_fr` raises on an unknown type.
   - `_append_blocked_step`'s body contains no `db`, `select(`, `chat(`,
     `datetime` or `randint`, and appends inside a branch guarded by three
     conditions.
   - `blocked_reason` is defined nowhere in `src/world_engine/`, and
     `cockpit/routes/day.py` imports it nowhere.
   - `resolution.py` contains no `"blocked"` literal -- the fourth band is
     Python-assigned by the day chain, never rolled.

## Scope OUT

- **`new_knowledge` emission of any kind.** `EMITTED_MUTATION_TYPES`,
  `_EMITTERS` and `_emit_new_knowledge` belong to BRIEF-0078-c. The only
  `day_mutations.py` change here is `_step_action`'s widening and the empty
  return in `_emit_agenda_step_change`.
- **Widening `_mutation_apply_agenda_step_change`'s action vocabulary.** R21
  exists precisely so this never happens. A blocked step proposes nothing.
- **Any change to `judge_narration`'s pass conditions**, to either
  anti-vacuity guard, or to `extract_names`. The judge is not loosened; the
  input is made non-empty instead.
- **A retry loop on judge failure.** `MAX_REWRITE_ATTEMPTS = 1` stands.
- **Rendering `Verdict.reason` (English) anywhere a player can see.** French
  comes exclusively from `requirement_detail_fr`.
- **Anchoring logic.** BRIEF-0078-a owns it. Do not add an anchoring call to
  `day_resolve.py`.
- **A fifth band, a `skipped` band, or a band for the veto's own truncation.**
  The veto keeps its existing code-rendered prose.
- **Migrating stored `pass_play.history` entries** to carry `blocked_detail`.
  Absent key means absent detail; history is append-only and is not rewritten.
- **Editing the existing `day_narration` prompt version row in place.** A new
  version, always.
- **`_eval_resource`'s ignored `target_key`** -- REPORT ONLY (E1).

## Invariants to defend

- **The judge is never weakened to accommodate a caller.** This brief's whole
  shape follows from that: the zero-step case is eliminated, not excused. The
  temptation to defend against is a special case in `judge_narration` for
  "blocked days" -- if you find yourself writing one, the design is wrong,
  stop and escalate.
- **History is sacred.** The prompt reseed writes a new version;
  `pass_play.history` gains entries and rewrites none.
- **Model proposes, code judges.** The band is decided by Python from
  requirement verdicts. The model renders it and must never be asked whether a
  step was blocked.
- **No structure without a reader.** `blocked_reason` loses its only caller in
  this brief and is therefore deleted in the same commit, not left behind.
- **Purity where declared.** `_truncate_on_failure` is pure today;
  `_append_blocked_step` joins it under the same rule.

## Done means

- [ ] `python -m tooling.verify.checks.day_narration` prints PASS naming the
      new rules.
- [ ] `python -m tooling.verify.checks.day_plan` still prints PASS, R21
      included.
- [ ] `python -m tooling.verify.checks.day_prompt_delivery` and
      `prompt_lean` print PASS.
- [ ] `python -m tooling.verify.checks.corpus_gate` prints PASS.
- [ ] `grep -rn "blocked_reason" src/` returns nothing.
- [ ] Live: a day gated on a real, unheld, non-secret subject resolves to a
      narrative containing exactly one `[BLOQUÉ]` beat that reads as prose. No
      English string and no raw subject slug appears verbatim in the account.
- [ ] Live: `SELECT status FROM agenda_step WHERE id = <blocked step>` is
      unchanged after the resolve, and the review queue holds NO
      `agenda_step_change` row for it.
- [ ] Live: a day where step 2 FAILS on the dice ends at step 2 -- no
      `[BLOQUÉ]` beat is appended for step 3.
- [ ] Live: a day cut purely by budget produces no `[BLOQUÉ]` beat.
- [ ] Live: a day whose feasibility veto retained zero steps still renders its
      veto reason, unchanged from before this ticket.
- [ ] Live: a day resolved before this ticket reads back from
      `pass_play.history` without error.
- [ ] `/review-step` and `/close-step` both run and report clean.

## Docs to update

- `world-engine-schema.md` -- no change (no schema surface).
- `ARCHITECTURE_DECISIONS.md` -- append **C2 (a blocked step is an outcome,
  not an absence)**, stating that the zero-step case is eliminated rather than
  excused and that `judge_narration`'s anti-vacuity guards are untouched.
- `CLAUDE.md` -- no change.
- The `day_narration` prompt's changelog entry, wherever seeded prompt
  versions are recorded, naming TICKET-0078 and the new marker.
