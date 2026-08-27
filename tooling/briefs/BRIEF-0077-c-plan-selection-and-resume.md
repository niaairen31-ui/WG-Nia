# BRIEF — Step "Dedicated plan selection and the resume action"

## Context

After BRIEF-0077-a a player can hold several plans, but the day chain still
looks only at the single ACTIVE one (`_load_standing_agenda`): a declaration
that means "I go back to what I was doing before" cannot find a parked plan, so
resuming is a manual two-step in the Creation intrigues tab. This step adds ONE
model call whose only job is to say which open plan a declaration targets, or
none, and wires the resume transition Python derives from it. It adds no new
verdict to the reconciliation prompt and no schema change.

## Mini-RECON (measured against the fresh tarball, `main`)

- [M] `src/world_engine/day_plans.py` -- `OPEN_PLAN_STATUSES = ("active","paused")`,
  `open_plans`, `active_plan`, `park_active_plan` (which calls
  `write_agenda_status` then `db.flush()`).
- [M] `cockpit/routes/day.py:459-465` -- `_load_standing_agenda`, the single
  `status == 'active'` read that this step replaces at its call site (line 550).
- [M] `cockpit/day_reconcile_apply.py:145-168` -- `_reconcile_and_finalize`
  calls `reconcile(...)` then dispatches through the `handlers` dict.
- [M] `src/world_engine/day_reconcile.py:63` --
  `RECONCILE_VERDICTS = ("continue", "modify", "replace")`;
  `reconcile()` (line 95) is read-only and raises `LlmParseError` on any
  validation failure, never defaulting.
- [M] `tooling/verify/checks/day_plan.py:107` --
  `EXPECTED_RECONCILE_VERDICTS = ("continue","modify","replace")`; R12 compares
  the handlers dict key set against it, both directions.
- [M] `src/world_engine/prompt_coverage.py:41-52` -- `DAY_CHAIN_USAGES` is
  DERIVED: every `PROMPT_REGISTRY` usage whose `call_sites` names a file
  matching `^src/world_engine/day_[a-z_]+\.py$`, minus `DEGRADING_USAGES`.
  A new `day_*.py` module with a registry entry is picked up automatically.
- [M] `cockpit/routes/day.py:165-175` -- `declare_day` calls
  `missing_usages(DAY_CHAIN_USAGES, db)` BEFORE `write_batch` and returns 503
  naming the seed script.
- [M] `scripts/seed_pilot.py:2012-2093` -- `DAY_PROMPT_HEADS`, 8 entries, each a
  `dict(...)` with the 8 keys `id,name,usage,world_id,system_prompt,
  user_template,variables,destination`.
- [M] `tooling/verify/checks/day_prompt_delivery.py:48-65` -- `DAY_CONSTANTS`
  is a 14-name tuple, `EXPECTED_HEAD_IDS` an 8-id set, and line 171 asserts
  `len(heads_node.elts) != 8`. **All three are hard-coded and WILL go red on a
  ninth head unless updated by this brief.**
- [M] `scripts/apply_ticket_0076_day_prompt_seed.py` -- the CREATE-HEAD pattern:
  embeds no prompt text, loops `seed_pilot.DAY_PROMPT_HEADS` through
  `seed_pilot.upsert_prompt_template`, S2 (a head already present with >= 1
  version is never retouched).
- [M] `cockpit/routes/day.py` is 834 lines; `models/config.py`'s AgendaStep
  CHECK is `('pending','active','completed','failed')` -- untouched here.
- [I] Because of S2, changing the text of an ALREADY-SEEDED head on the live DB
  needs a new `prompt_version`, not a head edit -- which is why this brief adds
  a new usage and leaves `day_reconcile`'s seeded text alone.

**STOP conditions.** Stop and escalate if: (1) BRIEF-0077-b has not landed and
`day_plan.py` is red -- do not build on a red gate; (2) `DAY_PROMPT_HEADS` no
longer has 8 entries or `day_prompt_delivery.py`'s anchors differ from the
counts above; (3) `DAY_CHAIN_USAGES` turns out NOT to pick up the new module
automatically -- that would mean the derivation in `prompt_coverage.py` is
narrower than measured and the coverage story must be re-decided; (4) making
`resume` work appears to require editing `DAY_RECONCILE_SYSTEM_PROMPT` -- it
must not, see Scope IN item 4.

## Scope IN

**1. New module `src/world_engine/day_plan_select.py`.** ONE model call. Reads
only: it constructs nothing, calls no `db.add(`, and calls no `_apply_mutation`.
Public surface:

    MAX_SELECTABLE_PLANS  -- absent. G is locked at no cap; every open plan is
                             offered. Do NOT introduce one.

    def select_plan(declaration: str, plans: list[Agenda], db: Session) -> Optional[Agenda]

Behaviour, in order:
  a. `len(plans) == 0` -> return `None` without calling the model.
  b. Load the active `day_plan_select` template with
     `_load_day_plan_template`'s exact precedent (world-specific preferred, then
     `world_id is None`, then first). None found -> raise
     `llm_parse.LlmParseError("day_plan_select: no active prompt_template for usage='day_plan_select'")`.
     **Raise, never degrade** -- `day_prompt_delivery.py` R6 classifies this
     module from that message and requires it to be a `Raise`.
  c. Render the user template, replacing `{declaration}` and `{plans}`. `{plans}`
     is built by a module-local `_render_plans(plans, db)` producing one line per
     plan: `N. <title> (<status>) — <objective of the first non-terminal step>`,
     numbered from 1 in the order `plans` arrives. **Never an id** -- the model
     answers with the ordinal, exactly as `day_reconcile` cites a `step_order`
     rather than a `step_id`.
  d. Append `"\n/no_think"`, call `ollama_client.chat` with `format="json"`,
     `model=effective_model(template, ollama_client.DEFAULT_MODEL)`, and
     `SELECT_OPTIONS = {"repeat_penalty": 1.1, "repeat_last_n": 128}`.
  e. Parse through `llm_parse.extract_object`. Expect
     `{"selected": <int|null>, "rationale": "<...>"}`. `selected` null or 0 ->
     return `None`. `selected` not an int (bools excluded), or outside
     `1..len(plans)` -> raise `LlmParseError` naming the value and the range.
     Never clamp, never default to plan 1.
  f. Return `plans[selected - 1]`.

Module docstring states, verbatim:

    The model PROPOSES a selection; code judges it. The proposal is an ORDINAL
    into a list Python built and Python owns — the model never sees or emits an
    agenda id, so a hallucinated identifier cannot reach canon, and an
    out-of-range ordinal is a parse failure rather than a silent fallback to
    the first plan. Whether the selected plan is parked or active is a fact
    this module never asks about and never reports: `day_plans.active_plan`
    measures it, and `_reconcile_and_finalize` derives the transition from the
    measurement.

**2. Registry entry (`src/world_engine/prompt_registry.py`).** Add, placed
immediately after the `day_reconcile` entry:

    "day_plan_select": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_plan_select.py:select_plan",),
        default_model=_game_model,
    ),

Do NOT add it to `DEGRADING_USAGES`. `DAY_CHAIN_USAGES` picks it up by
derivation; do not restate it anywhere.

**3. Seeded head (`scripts/seed_pilot.py`).** Two new module-level constants,
`DAY_PLAN_SELECT_SYSTEM_PROMPT` and `DAY_PLAN_SELECT_USER_TEMPLATE`, placed
immediately after the `DAY_RECONCILE_*` pair, and a ninth `DAY_PROMPT_HEADS`
entry:

    dict(
        id="pt-day-plan-select",
        name="Journée — sélection du plan visé",
        usage="day_plan_select",
        world_id=None,
        system_prompt=DAY_PLAN_SELECT_SYSTEM_PROMPT,
        user_template=DAY_PLAN_SELECT_USER_TEMPLATE,
        variables=["plans", "declaration"],
        destination="local",
    ),

System prompt, verbatim (French, like every other day head):

    Tu identifies à quel plan en cours se rattache la déclaration du jour d'un \
    joueur. On te donne la liste numérotée de ses plans ouverts (certains sont \
    en pause) et sa déclaration.

    RÈGLES :
    - "selected" : le NUMÉRO du plan auquel la déclaration se rattache, ou null \
    si la déclaration ne se rattache à aucun d'eux et ouvre quelque chose de \
    neuf.
    - Ne choisis un plan que si la déclaration poursuit, reprend ou infléchit \
    CE plan précis. Dans le doute, réponds null.
    - "rationale" : une phrase courte justifiant ton choix.

    Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien \
    d'autre :
    {"selected":<entier ou null>,"rationale":"<...>"}

User template, verbatim:

    Plans ouverts du joueur :
    {plans}

    Déclaration du jour : {declaration}

    À quel plan cette déclaration se rattache-t-elle, s'il y en a un ?

**4. Four code actions, THREE model verdicts
(`src/world_engine/day_reconcile.py`, `cockpit/day_reconcile_apply.py`).**
`RECONCILE_VERDICTS` stays `("continue","modify","replace")` and
`DAY_RECONCILE_SYSTEM_PROMPT` is NOT edited. Add to `day_reconcile.py`, beside
`RECONCILE_VERDICTS`:

    # The dispatch's vocabulary, which is NOT the model's. `resume` is derived
    # by Python from a measured fact (the selected plan's status), never
    # reported by the model: asking a model to restate something a SELECT
    # already knows adds a failure mode and buys nothing. TICKET-0077,
    # BRIEF-0077-c — decision D2, "four verdicts", landed as four ACTIONS.
    PLAN_ACTIONS: tuple[str, ...] = ("continue", "modify", "replace", "resume")

Add a pure function in the same module:

    def plan_action(verdict: str, selected_status: str) -> str:
        """Map a model verdict plus the selected plan's MEASURED status onto a
        dispatch action. Total over RECONCILE_VERDICTS x OPEN_PLAN_STATUSES —
        an unknown pair raises, fail-closed."""

with exactly this mapping and no other branch:

    ("continue", "active")  -> "continue"
    ("continue", "paused")  -> "resume"
    ("modify",   "active")  -> "modify"
    ("modify",   "paused")  -> "resume"     # revision is BRIEF-0077-d; until
                                            # then a paused plan is resumed
                                            # unchanged and `modify`'s 422 is
                                            # not reached from this path
    ("replace",  "active")  -> "replace"
    ("replace",  "paused")  -> "replace"

**5. Wire the transition (`cockpit/day_reconcile_apply.py`).** In
`_reconcile_and_finalize`, in this exact order:
  a. load `steps`, call `reconcile(...)` -- unchanged, still read-only.
  b. `selected_status = agenda.status` -- read BEFORE any write.
  c. `action = plan_action(recon.verdict, selected_status)`.
  d. if `action != "replace"` and `selected_status == "paused"`:
     `day_plans.park_active_plan(character, db)`, then
     `write_agenda_status(db, agenda=agenda, status="active")`, then
     `db.flush()`. Wrap the `write_agenda_status` call in `try/except ValueError`
     -> `HTTPException(409, str(exc))`; the park runs first so this cannot
     normally fire, and if it does the message is the guard's own.
  e. dispatch on `action`. The `handlers` dict gains
     `"resume": lambda: _finalize_continue(pass_play, agenda, recon, db)` --
     the SAME handler object as `continue`, because a resumed plan's content is
     unchanged; the distinct key is what makes the action visible in the
     dispatch and checkable by R12.
  f. add `"action": action` to `_reconciliation_dict`'s returned dict, alongside
     the existing `verdict`. Still no `agenda_id`, still no `step_id`.

**6. Wire the selection (`cockpit/routes/day.py`, `plan_day`).** Replace the
`_load_standing_agenda` call at line 550 with:

    plans = day_plans.open_plans(character, db)
    try:
        selected = day_plan_select.select_plan(pass_play.declared_action, plans, db)
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"plan selection failed: {exc}") from exc
    if selected is not None:
        result = _reconcile_and_finalize(character, pass_play, selected, concordance_result, db)
    else:
        day_plans.park_active_plan(character, db)
        ... existing fresh-plan path, unchanged ...

`_load_standing_agenda` becomes unreferenced -- DELETE it (an unused reader is
structure without a reader). Update `plan_day`'s docstring to describe the
selection stage and name this brief. Keep `plan_day` at or under 80 lines;
extract a `_select_and_finalize(...)` helper into
`cockpit/day_reconcile_apply.py` if it would exceed.

**7. Update `tooling/verify/checks/day_prompt_delivery.py`.** Three anchor
edits, no assertion weakened: append `"DAY_PLAN_SELECT_SYSTEM_PROMPT"` and
`"DAY_PLAN_SELECT_USER_TEMPLATE"` to `DAY_CONSTANTS` (now 16), add
`"pt-day-plan-select"` to `EXPECTED_HEAD_IDS` (now 9), and change the literal
`8` at line 171 to `9`. Add to the file docstring, verbatim:

    Counts updated by TICKET-0077/BRIEF-0077-c (8 -> 9 heads, 14 -> 16
    constants) for the `day_plan_select` usage. The counts are deliberately
    literal and deliberately brittle: a head added to `seed_pilot.py` without
    a matching delivery script is exactly the TICKET-0076 defect, and a check
    that auto-counted whatever it found could never catch it.

**8. One-shot delivery script
`scripts/apply_ticket_0077_plan_select_seed.py`.** Copy
`apply_ticket_0076_day_prompt_seed.py` structurally -- same env refusal, same
`seed_pilot` import, same created/updated/existing reporting, embeds NO prompt
text. It loops `seed_pilot.DAY_PROMPT_HEADS` in full and relies on
`upsert_prompt_template`'s idempotence; the eight existing heads report
`existing`, the ninth reports `created`. Idempotent, safe to re-run. Update
`declare_day`'s 503 message (`routes/day.py:173`) to name THIS script instead
of the 0076 one.

**9. Extend `tooling/verify/checks/day_plan.py` -- R12 widened, R23 new.**
  - R12: compare the handlers dict key set against a new
    `EXPECTED_PLAN_ACTIONS = ("continue","modify","replace","resume")`, and
    keep asserting `RECONCILE_VERDICTS == EXPECTED_RECONCILE_VERDICTS`
    (still the three-value tuple) as a SEPARATE assertion. Both directions,
    both tuples.
  - R23 new, `check_plan_action_total()`: `plan_action`'s body contains a dict
    or mapping literal whose key set is exactly the six
    `(verdict, status)` pairs of `RECONCILE_VERDICTS x OPEN_PLAN_STATUSES`, and
    the function raises on an unknown pair. Zero pairs collected -> FAIL.
    Docstring states it proves the mapping is TOTAL, not that each target is
    the right one.
  - R24 new, `check_select_reads_only()`: `day_plan_select.py` contains no
    `db.add(`, no `Agenda(`/`AgendaStep(` construction, no `_apply_mutation`
    call, and no `ProposedMutation` reference -- R11's shape, applied to the new
    module. Zero nodes walked -> FAIL.

## Scope OUT

- **Plan revision.** `_finalize_modify` keeps its 422 verbatim; do not touch
  `_revised_plan_matches_remaining`, do not widen
  `_mutation_apply_agenda_step_change`'s action vocabulary, do not add a
  `superseded` step status. BRIEF-0077-d.
- **Editing any already-seeded prompt head's text.** S2 holds. If `resume`
  seems to need a sentence in `DAY_RECONCILE_SYSTEM_PROMPT`, the design in
  item 4 is being abandoned -- STOP.
- **A cap on open plans, or truncating the `{plans}` list.** G is locked at
  none.
- **A player-facing selector.** F1 is locked; no Journee UI change.
- **Showing the selection to the player.** No `agenda_id` in any response.
- **Two model calls collapsed into one.** Selection and reconciliation stay
  separate calls: Nia's decision C3, "un appel modele dedie juste a cela".
- **Retiring `_load_active_agenda`'s NULL fallback** in `/resolve`.
- **Touching `day_extract`, `day_concordance`, `day_feasibility`,
  `day_narration`, `day_resolve`** or their prompts.

## Invariants to defend

- **Model proposes, code judges.** The model returns an ordinal into a
  Python-owned list and a three-value classification; every id, every status and
  every transition is Python's. Item 1e's out-of-range raise and item 4's total
  mapping are where this is enforced.
- **Never a silent fallback.** `select_plan` raises on a malformed or
  out-of-range answer, exactly as `reconcile` does -- the brief that built
  `reconcile` called a silent default to `continue` "the worst possible failure
  mode: it looks like inertia and is actually a swallowed error." The same
  applies to defaulting to plan 1.
- **One active agenda per character.** The resume swap parks before it
  activates and flushes between; `write_agenda_status`'s guard is the backstop
  and its `ValueError` must surface as a 409, never a 500.
- **History is sacred.** Both sides of the swap go through
  `write_agenda_status`, which appends before overwriting.
- **Prompt coverage is derived, never restated.** No new literal usage list
  anywhere; `DAY_CHAIN_USAGES` picks the new usage up from `PROMPT_REGISTRY`.
- **A head in `seed_pilot.py` is not a head on the live DB.** Item 8 is the
  TICKET-0076 lesson; a brief that adds a head without a delivery script
  reproduces that ticket exactly.
- **Enumeration scope discipline.** `open_plans` already carries its owner
  filter; add no unfiltered `select(Agenda)`.

## Done means

- [ ] `python scripts/apply_ticket_0077_plan_select_seed.py` prints eight
      `existing` lines and one `created pt-day-plan-select`; a second run prints
      nine `existing`.
- [ ] `sqlite3 ~/.world_engine/world_engine.db "SELECT usage, is_active FROM prompt_template WHERE usage='day_plan_select'"`
      returns one active row, and it has at least one `prompt_version`.
- [ ] `POST /api/day/declare` succeeds (the 503 coverage guard passes with the
      new usage in `DAY_CHAIN_USAGES`); temporarily deactivating the new head
      makes `declare` return 503 naming `day_plan_select` and the new script.
- [ ] Live, three days on one world:
      day 1 declare plan A -> resolve;
      day 2 declare something unrelated -> a NEW plan B, A shows `paused`;
      day 3 declare a continuation of A **in plain French, with no manual
      Creation step** -> the response's `reconciliation.action` is `resume`,
      A is `active`, B is `paused`.
- [ ] On that day-3 response, `pass_play.agenda_id` equals plan A's id.
- [ ] Plan A's `change_history` shows `active -> paused -> active`, and plan B's
      shows `active -> paused`.
- [ ] The review queue holds NO row describing either swap.
- [ ] A declaration matching no open plan produces `selected: null` behaviour:
      the active plan is parked and a fresh plan is created.
- [ ] `python tooling/verify/checks/day_plan.py`,
      `day_prompt_delivery.py`, `parked_plan_guard.py`, `prompt_registry.py`
      and `prompt_lean.py` each exit 0.
- [ ] `python tooling/verify/run.py` is green, `corpus_gate.py` included.
- [ ] `wc -l` on every touched `src/` module is under 1000; no function over 80
      lines.
- [ ] `/review-step` and `/close-step` run and reported.

## Docs to update

- `world-engine-schema-changelog.md` -- **no entry**: no schema change. Say so
  in the execution notes rather than inventing a version bump.
- `world-engine-schema.md` -- no change.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- new subsection: why the
  selection call is separate from reconciliation; why the model answers with an
  ordinal and never an id; and the D2 landing note (four dispatch ACTIONS, three
  model VERDICTS, with the reason a measured fact stays out of the model's
  mouth).
- `CLAUDE.md` -- no change expected; report if the contract check disagrees.
- `tooling/verify/canon_write_policy.txt` -- no new site. If the AST check
  demands one, STOP: `day_plan_select.py` grew a write it must not have.
