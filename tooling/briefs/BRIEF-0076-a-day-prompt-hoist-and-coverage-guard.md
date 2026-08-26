# BRIEF — Step "Day chain prompt delivery and coverage guard"

Ticket: TICKET-0076. Schema: none touched (no DDL, no new table, no column).

## Context

[M] The day chain's eight `prompt_template` rows exist in `scripts/seed_pilot.py`
but not in the live DB, so `POST /api/day/{batch}/plan` fails at the first model
call with `day_extract: no active prompt_template for usage='day_extract_place'`
(`day_extract.py:108`, wrapped 502 at `routes/day.py:663`). [M] The only creation
path is the seed script -- `cockpit/crud/prompts.py` has no create endpoint. [M]
Nothing links corpus to DB: no boot hook in `cockpit/app.py` reads
`prompt_template`, and every prompt-related check under `tooling/verify/checks/`
is static (none opens a database).

This step delivers the eight rows through a one-shot script that duplicates no
prompt text and no head fields, and closes the detection gap with a coverage
guard at the Journee surface entry.

## Mini-RECON (measured on a fresh `main` tarball, 2026-08-26)

Anchors the executor MUST re-verify before editing. If any of these does not
match the tree, **STOP and escalate** -- do not adapt the plan silently.

- `scripts/seed_pilot.py` is 3649 lines. `seed()` spans `1715-3590`.
- The 14 `DAY_*` constants are assigned INSIDE `seed()` at:
  `DAY_PLAN_SYSTEM_PROMPT` 2384-2413, `DAY_PLAN_USER_TEMPLATE` 2415-2420,
  `DAY_EXTRACT_PLACE_SYSTEM_PROMPT` 2441-2459,
  `DAY_EXTRACT_PERSON_SYSTEM_PROMPT` 2461-2481,
  `DAY_EXTRACT_FACTION_SYSTEM_PROMPT` 2483-2501,
  `DAY_EXTRACT_USER_TEMPLATE` 2503-2508,
  `DAY_NARRATION_SYSTEM_PROMPT` 2560-2585, `DAY_NARRATION_USER_TEMPLATE` 2587-2593,
  `DAY_REWRITE_SYSTEM_PROMPT` 2601-2618, `DAY_REWRITE_USER_TEMPLATE` 2620-2627,
  `DAY_FEASIBILITY_SYSTEM_PROMPT` 2662-2686, `DAY_FEASIBILITY_USER_TEMPLATE` 2688-2698,
  `DAY_RECONCILE_SYSTEM_PROMPT` 2720-2741, `DAY_RECONCILE_USER_TEMPLATE` 2743-2751.
- Every other prompt constant in the file (49 of them, `WORLD_TICK_*`,
  `NPC_DIALOGUE_*`, `MJ_*`, ...) is already module-level. The day block is the
  only exception; this step removes the exception.
- The eight `upsert_prompt_template` calls: 2422-2432 `pt-day-plan`,
  2510-2520 `pt-day-extract-place`, 2522-2532 `pt-day-extract-person`,
  2534-2544 `pt-day-extract-faction`, 2629-2639 `pt-day-narration`,
  2641-2651 `pt-day-rewrite`, 2700-2710 `pt-day-feasibility`,
  2753-2763 `pt-day-reconcile`.
- The contiguous day block runs `2373` (comment `# ----- prompt template: day
  plan emission (TICKET-0075, BRIEF-0075-b) ---`) through `2763` (closing paren
  of the `pt-day-reconcile` call). Line 2372 ends the `conversation_summary`
  block; line 2764 is blank, then `# ----- factions`.
- `upsert_prompt_template(session, id, *, system_prompt, user_template,
  **head_fields)` at `seed_pilot.py:126-180`. S2: head absent -> create + v1;
  head present with >= 1 version -> text NEVER retouched; head present with zero
  versions -> `SystemExit`. Non-text head fields converge on diff.
- `apply_ticket_0024_prompt_updates.py` is the one-shot precedent, but it is an
  APPEND-A-VERSION script against an existing head. It does not exercise the
  create branch and carries no head fields. Do not assume its shape transfers
  whole.
- `PromptSpec` (`prompt_registry.py:54-60`): `surface` ("play" | "authoring"),
  `world_scoped`, `dry_run_capable`, `call_sites`, `default_model`. 37 entries;
  24 are `surface="play"`, of which only 8 are the day chain.
- The 8 day entries at `prompt_registry.py:260-315`, each with exactly one
  call site, each of the form `src/world_engine/day_<x>.py:<function>`.
- `prompt_registry.py` (the check) assertion 2 already validates that every
  `call_sites` entry resolves to an existing file containing that `def`. The
  derivation in this step rides on an already-guarded fact.
- `prompt_registry.py` (the check) assertion 1 scans seed text with
  `USAGE_LINE = re.compile(r'usage\s*=\s*"([a-z_]+)"')` over the WHOLE file, not
  scoped to `seed()`. The hoist does not move `usage=` lines. **If the executor
  finds this regex scoped to a function body, STOP.**
- Missing-template branches: `day_plan.py:360` raise, `day_extract.py:108` raise,
  `day_reconcile.py:108` raise, `day_narration.py:102` raise, `:128` raise,
  `day_feasibility.py:188` `return _unavailable(...)`. Seven raise, one degrades.
- `prompt_store.current_prompt` (`prompt_store.py:19-36`) raises `RuntimeError`
  on a versionless head.
- `declare_day` at `routes/day.py:163-186`; first write is `write_batch` at
  line 170. `routes/day.py` is 934 lines / 31 top-level functions; caps are
  1000 / 40 (`module_budget.py:57-58`). `module_budget.py` scans `src/` and
  `frontend/src/` only -- `scripts/` is exempt.
- `frontend/src/creation/sheetRequest.svelte.js:30-35`: `api()` throws
  `new Error(data.detail)`. `journee.svelte.js:115-117` catches into
  `submitError`; `Journee.svelte:50-51` renders it. A 503 `detail` string
  reaches the screen with no frontend change.
- `tooling/verify/run.py:10` discovers checks by parsing
  `-> verify/checks/<name>.py` out of the ticket. There is no registry file to
  edit.

**STOP conditions.** Escalate rather than improvise if: any `DAY_*` constant is
already module-level; any day `upsert_prompt_template` call carries a head field
not listed in item 2 below; `day_feasibility.py`'s missing-template branch
raises rather than returns; `declare_day` already contains a coverage check;
`routes/day.py` exceeds 990 lines before this step's edits.

## Scope IN

1. **Hoist the 14 `DAY_*` constants to module level** in `scripts/seed_pilot.py`.
   Place them together, immediately before `def seed(`, under the header comment
   `# ----- day chain prompt text (TICKET-0075; hoisted to module level,
   TICKET-0076) -----`. Move the existing explanatory comments with them.
   **The prompt text is byte-identical.** Not a word, not a newline, not an
   accent changes. Remove the in-`seed()` assignments; do not leave aliases.

2. **Add a module-level `DAY_PROMPT_HEADS`** immediately after those constants:
   a tuple of 8 dicts, in the current seeding order, each with exactly the keys
   `id`, `name`, `usage`, `world_id`, `system_prompt`, `user_template`,
   `variables`, `destination`, values copied verbatim from the existing eight
   calls (`world_id=None` and `destination="local"` throughout; `name` strings
   keep their French wording and accents unchanged).

3. **Replace the eight calls in `seed()`** with a single loop over
   `DAY_PROMPT_HEADS` calling `upsert_prompt_template(session, **entry)`. The
   loop stays where the block is today (after the `conversation_summary` block,
   before `# ----- factions`). Behavior is unchanged: same ids, same order, same
   arguments.

4. **Create `scripts/apply_ticket_0076_day_prompt_seed.py`.** Module docstring
   verbatim:

   ```
   """One-shot, idempotent delivery of the TICKET-0075 day chain prompt
   templates onto the live DB (TICKET-0076, BRIEF-0076-a).

   Unlike apply_ticket_0024_prompt_updates.py this is a CREATE-HEAD script:
   the eight heads do not exist yet on a DB seeded before BRIEF-0075-b. It
   embeds NO prompt text and NO head fields -- both come from
   seed_pilot.DAY_PROMPT_HEADS (single source).

   Touches nothing else: no knowledge row, no relation, no other template.
   S2 applies -- a head already present with >= 1 version never has its text
   retouched.

   Safe to re-run.
   """
   ```

   Body: the `sys.path` preamble and `Session(engine)` shape of
   `apply_ticket_0024_prompt_updates.py:17-30`; loop over
   `seed_pilot.DAY_PROMPT_HEADS` calling `seed_pilot.upsert_prompt_template`;
   one `session.commit()`; then print one line per entry from `seed_pilot._created`
   / `_updated` / `_existing`, formatted `created  <table>/<id>` etc. Exit 0.

5. **Create `src/world_engine/prompt_coverage.py`.** Module docstring must state,
   in its own words, the three facts below; the executor writes the prose, these
   are the facts it must contain: (a) `DAY_CHAIN_USAGES` is derived from
   `PROMPT_REGISTRY`, never a literal list; (b) `day_feasibility` is exempt
   because `day_feasibility.py:188` returns `_unavailable(...)` rather than
   raising -- BRIEF-0075-g decision Y1's designed degradation, and requiring it
   would turn a tolerated absence into a refusal; (c) coverage means an active
   template AND at least one `prompt_version` row, because
   `prompt_store.current_prompt` raises on a versionless head outside the plan
   route's 502 wrapper.

   Contents:
   - `_DAY_MODULE = re.compile(r"^src/world_engine/day_[a-z_]+\.py$")` applied to
     the path half of each `call_sites` entry.
   - `DEGRADING_USAGES: frozenset[str] = frozenset({"day_feasibility"})`, with a
     comment carrying the `day_feasibility.py:188` anchor.
   - `DAY_CHAIN_USAGES: tuple[str, ...]` = sorted usages whose `PromptSpec` has
     at least one call site matching `_DAY_MODULE`, minus `DEGRADING_USAGES`.
     No usage string literal appears anywhere in this module other than inside
     `DEGRADING_USAGES`.
   - `missing_usages(usages: Sequence[str], db: Session) -> list[str]` returning,
     in the given order, every usage lacking an active template with at least one
     `PromptVersion` row. One query per side, joined in Python; the
     `PromptTemplate` query carries an explicit `is_active == True` filter.
     Returns `[]` when everything is covered; a usage absent from the DB comes
     back as missing (never assumed present).

6. **Wire the guard into `declare_day`** (`routes/day.py:163`), as the FIRST
   statement of the function body, before `_crud._world_id(db)`:

   ```python
   missing = missing_usages(DAY_CHAIN_USAGES, db)
   if missing:
       raise HTTPException(
           status_code=503,
           detail=(
               "day chain unavailable: no active prompt_template with a version for "
               f"{', '.join(missing)} -- run "
               "python scripts/apply_ticket_0076_day_prompt_seed.py"
           ),
       )
   ```

   Import from `...prompt_coverage`. No other route changes.

7. **Create `tooling/verify/checks/day_prompt_delivery.py`**, stdlib `ast` and
   text only, no DB, following the `FAILURES` / `fail()` / `_parse` / `_rel` /
   `_report_and_exit` idiom of `day_feasibility.py` with `ROOT = parents[3]`:
   - R1: all 14 named `DAY_*` constants are module-level in `seed_pilot.py`, and
     `seed()` contains no `Assign` to any of them.
   - R2: `DAY_PROMPT_HEADS` is module-level with exactly 8 dict entries, each
     carrying the 8 required keys; the 8 `id` values match the anchors in the
     mini-RECON.
   - R3: `seed()` contains no `upsert_prompt_template` call whose `usage` starts
     with `day_` -- the loop is the only seeding path.
   - R4: in `apply_ticket_0076_day_prompt_seed.py`, the only `str` constant
     longer than 200 characters is the module docstring, and the file assigns no
     `DAY_*` name.
   - R5: `prompt_coverage.py` contains no string literal equal to any
     `PROMPT_REGISTRY` key except those inside `DEGRADING_USAGES`.
   - R6: recompute the exempt set by AST -- for each `src/world_engine/day_*.py`,
     find the `no active prompt_template` message and classify its enclosing
     statement as `Raise` or `Return`. The `Return` set MUST equal
     `DEGRADING_USAGES`, and the `Raise` set MUST equal `set(DAY_CHAIN_USAGES)`.
     This is the rule that keeps the exemption honest; it is not a restatement
     of R5.
   - R7: `missing_usages`'s body references `PromptVersion` (E2 depth) and
     `PromptTemplate.is_active`.
   - R8: in `declare_day`, the `missing_usages` call appears strictly before the
     `write_batch` call -- compare statement positions, do not merely assert both
     are present.
   - R9: vacuity guard -- any rule that collected zero items is a FAILURE. State
     it as its own rule so a broken parse cannot report green.

8. **Close TICKET-0075**: in `tooling/tickets/TICKET-0075-day-resolution-chain.md`,
   change `status: escalated` to `status: done`. Front-matter only. Nothing else
   in that file, and nothing in `tooling/questions/`.

## Scope OUT

- **`tooling/questions/QUESTION-TICKET-0075.md` and the `continue` verdict.**
  Answered out of band directly to Claude Code. Do not read it as an open
  instruction, do not widen `agenda_step_change`, do not add an "activate a
  pending step" action, do not close or annotate the file.
- **Any other TICKET-0075 artifact.** Briefs, `ARCHITECTURE_DECISIONS.md`
  sections, changelog entries from that ticket stay exactly as merged. The
  front-matter line in item 8 is the whole of the closure.
- **Prompt text improvements.** The hoist is a move. If a day prompt looks
  wrong, REPORT ONLY.
- **The other 49 prompt constants and the other 29 templates.** Only the 14
  `DAY_*` constants move; only the 8 day heads get a descriptor. Do not
  generalize `DAY_PROMPT_HEADS` into a table for all templates, however
  tempting the symmetry.
- **A boot-time coverage guard (B1).** Rejected at intake. Do not add a hook to
  `cockpit/app.py`.
- **A `chain` field on `PromptSpec` (D3).** Rejected at intake. `PromptSpec`
  gains no field.
- **A prefix-based cross-check against D1.** Explicitly dropped by Nia. R6
  checks the exemption; there is no `startswith("day_")` rule.
- **A create-template endpoint in the cockpit.** Real gap, different ticket.
  `cockpit/crud/prompts.py` is untouched.
- **Frontend changes.** [M] The 503 `detail` already reaches the screen through
  `api()` -> `submitError` -> `Journee.svelte:50-51`. `frontend/` is untouched
  and no rebuild is required by this step.
- **Guarding `/api/day/{batch}/plan` or `/resolve`.** One guard, at declare.
  The 502 wrappers downstream stay as they are.
- **`_apply_mutation`, review queue, agenda, schedule phases, day budget.**
  Not in the blast radius.
- **Any DDL.** No migration script, no schema version bump, no
  `schema_version` row. If the executor concludes a migration is needed, STOP.

## Invariants to defend

- **Single source of prompt text.** The hoist must not leave two copies. The
  one-shot embeds none. R4 defends this; item 1's byte-identical requirement is
  the other half.
- **S2 / creator sovereignty.** Re-running the one-shot must never rewrite an
  existing head's text. It is inherited from `upsert_prompt_template`, not
  reimplemented -- the script must not call `write_prompt_version` directly.
- **Fail-closed over advisory.** The guard refuses; it does not warn and
  proceed. A usage the guard cannot resolve counts as missing.
- **Vacuous-proof checks.** R9. A check collecting zero items fails.
- **Proves X, not Y.** R8 proves call ORDER, not co-presence. R6 proves the
  exemption matches the code's actual failure mode, not that a constant was
  spelled correctly.
- **No structure without a reader.** `DAY_PROMPT_HEADS` has two readers
  (`seed()`, the one-shot); `prompt_coverage.DAY_CHAIN_USAGES` has one
  (`declare_day`). Nothing else is added.
- **Module budget.** `routes/day.py` gains roughly 10 lines against a 66-line
  margin; `declare_day` stays under the 80-line function ceiling.

## Done means

- [ ] `python -c "import ast,pathlib; ast.parse(pathlib.Path('scripts/seed_pilot.py').read_text(encoding='utf-8'))"` succeeds.
- [ ] A diff of the 14 hoisted constants against their pre-hoist text shows zero character changes.
- [ ] `python tooling/verify/checks/day_prompt_delivery.py` exits 0 and prints a PASS line naming all nine rules.
- [ ] `python tooling/verify/checks/prompt_registry.py` exits 0 (bijection survives the hoist).
- [ ] `python tooling/verify/checks/module_budget.py`, `function_length.py`, `undefined_names.py`, `import_cycle.py`, `no_print_in_src.py` each exit 0.
- [ ] On a fresh test DB (`WORLD_ENGINE_ENV=test`), `python scripts/seed_pilot.py` creates the 8 day heads with the same ids as before the change.
- [ ] `python scripts/apply_ticket_0076_day_prompt_seed.py` on that same DB prints 8 `existing` lines and commits no change.
- [ ] On a test DB seeded WITHOUT the day block, the one-shot prints 8 `created` lines; each head has exactly one `prompt_version` row with note `seed v1`.
- [ ] `POST /api/day/declare` returns 503 with `day_extract_place` named in `detail` when `pt-day-extract-place` is `is_active=0`, and 200 when it is restored.
- [ ] `POST /api/day/declare` returns 200 when only `pt-day-feasibility` is `is_active=0`.
- [ ] `/review-step` and `/close-step` run (engine code is touched).

## Docs to update

- `tooling/tickets/TICKET-0075-day-resolution-chain.md`: front-matter status only (Scope IN item 8).
- `ARCHITECTURE_DECISIONS.md`: one new section recording (a) the corpus-vs-live-DB
  detection gap and the surface-entry guard as its structural answer, (b) the D2
  derivation and why `surface` cannot carry it, (c) the `day_feasibility`
  exemption with its `day_feasibility.py:188` anchor and the R6 rule that keeps
  it honest.
- `CLAUDE.md`: no change expected. If the executor believes a line is needed,
  REPORT ONLY -- the 500-line budget and `claude_md_contract.py` make that a
  separate decision.
- Schema changelog: no entry. This step touches no DDL.
