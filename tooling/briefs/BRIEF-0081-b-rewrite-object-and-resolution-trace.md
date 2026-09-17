# BRIEF — Step "rewrite object and resolution trace"

TICKET-0081, brief b of c. Decisions A2', B2/J2. Depends on BRIEF-0081-a
being landed: the trace records the verdict buckets that brief a defines.

## Context

Today the plan is emitted from the player's RAW declaration, with a French prose
summary of the concordance appended to the end of the user message. The
resolution itself is thrown away — `ConcordanceResult` never outlives the call
that builds it, and the resolve path re-runs the three extraction model calls on
the same text, so a day's plan and its narration can be built on two different
readings of one declaration.

This step makes the rewrite the load-bearing artifact Nia asked for: the plan is
emitted from a rendering that names the participants, that rendering is stored as
the literal input the model received, and the facts behind it are stored as rows
with real foreign keys. Nothing in this step is authored by a model.

## Mini-RECON

All [M] unless marked, same tarball, `Current schema version: v1.96`.

- **Full enumeration of `declared_action` consumers** (`grep -rn declared_action
  --include=*.py src/`, models excluded):

  | site | call | this brief |
  |---|---|---|
  | `routes/day.py:432-434` | the three `extract_*` at plan | stays raw (it IS the input to the rewrite) |
  | `routes/day.py:483` | `feasibility_veto(...)` | Scope OUT |
  | `routes/day.py:495` | `title = declared_action...` | untouched (a title, not a model input) |
  | `routes/day.py:571` | `day_plan_select.select_plan(...)` | SWAPPED |
  | `routes/day.py:580` | `emit_plan(...)` | SWAPPED |
  | `routes/day.py:700-702` | the three `extract_*` at resolve | DELETED |
  | `routes/day.py:719` | `narrate(...)` | Scope OUT |
  | `day_reconcile_apply.py:98` | `emit_plan(...)`, modify path | SWAPPED |
  | `day_reconcile_apply.py:141` | `emit_plan(...)`, replace path | SWAPPED |
  | `day_reconcile_apply.py:160` | `reconcile(...)` | Scope OUT |
  | `writes/pipeline.py:61-79` | `write_pass_play` | untouched |

- **Full enumeration of `plan_context` callers**: `routes/day.py:581`,
  `day_reconcile_apply.py:99`, `day_reconcile_apply.py:142`. Three, and no
  others. All three disappear in this step.
- `emit_plan` (`day_plan.py:446-506`) takes `declaration` plus three optional
  summary strings appended verbatim to the user message (`:474-481`).
  `concordance_summary` is one of them.
- `select_plan` (`day_plan_select.py:75-118`) takes `declaration` and renders it
  into `{declaration}`. The model answers with an ORDINAL into a Python-owned
  list, never an id.
- `_concord_declaration` (`routes/day.py:691-704`) re-runs extraction and
  concordance at resolve time. Its docstring states the reason: the result is
  never persisted, so `freeze_facts` needs a fresh one.
- `freeze_facts` (`day_resolve.py:386-399`) receives a `ConcordanceResult` and
  documents the re-run as a "durable-enough substitute".
- `_concordance_dict` (`routes/day.py:~390-420`) builds the API payload with
  `matched` / `ambiguous` / `unmatched` / `skipped_rungs` blocks; brief a adds
  `cast`.
- `PassPlay` lives in `models/pipeline.py:62-97`. `declared_action` is
  write-once by construction (`writes/pipeline.py:65-67`).
- `writes/pipeline.py` idiom: validate-then-construct, all-or-nothing, raise
  `ValueError` before any row exists.
- Changelog convention (`world-engine-schema-changelog.md:1-30`): newest entry
  first; the version number lives ONLY in `world-engine-schema.md`'s
  `Current schema version:` line and in
  `schema_version.EXPECTED_STATIC_SCHEMA_VERSION`, kept equal by
  `verify/checks/schema_version_agreement.py`.
- Known trap [M, from prior work]: `single_canon_write.py`'s AST resolver has a
  blind spot for `db.execute(sa_insert(...))`; and assigning a FK in memory
  causes an invisible implicit UPDATE at the next query (autoflush).

## Scope IN

1. **Two new tables in `src/world_engine/models/pipeline.py`.**

   `day_rewrite` — one row per generation of one declaration.
   - `id` (uuid pk), `world_id` FK `world.id`, `pass_play_id` FK `pass_play.id`
   - `generation: int`, `rendered_text: str`, `created_at: datetime`
   - `Index("idx_day_rewrite_pass_generation", "pass_play_id", "generation",
     unique=True)`
   - `CheckConstraint("generation >= 1", name="ck_day_rewrite_generation")`

   `day_mention_resolution` — N rows per rewrite, the facts behind it.
   - `id` (uuid pk), `world_id` FK `world.id`, `rewrite_id` FK `day_rewrite.id`
   - `ordinal: int`, `category: str`, `surface_form: str`, `kind: str`
   - `role_hint: Optional[str]`, `verdict: str`
   - `entity_id: Optional[str]` FK `entity.id`, `rung: Optional[str]`,
     `cast_basis: Optional[str]`
   - `Index("idx_day_mention_resolution_rewrite", "rewrite_id", "ordinal",
     unique=True)`
   - `CheckConstraint("category IN ('place','person','faction')", ...)`
   - `CheckConstraint("kind IN ('named','inferred')", ...)`
   - `CheckConstraint("verdict IN ('matched','cast','unmatched')",
     name="ck_day_mention_resolution_verdict")` — note verbatim, to be written
     into the schema doc: **`ambiguous` is deliberately not a storable verdict.
     An ambiguous mention 409s the request before any write, so a stored
     ambiguity would mean a guard was bypassed.**
   - `CheckConstraint(` shape guard, verbatim:
     ```
     "(verdict NOT IN ('matched','cast') OR (entity_id IS NOT NULL AND rung IS NOT NULL)) "
     "AND (verdict <> 'cast' OR cast_basis IS NOT NULL) "
     "AND (verdict <> 'unmatched' OR entity_id IS NULL)"
     ```
     named `ck_day_mention_resolution_shape`.

2. **New module `src/world_engine/day_rewrite.py`.** Pure: no model call, no
   write, no canon-model construction.
   - `render(declaration: str, result: ConcordanceResult, db: Session) -> str`
     — deterministic assembly. The declaration's own words are carried through;
     each resolved mention contributes a participant line naming the entity.
     Iteration order is the mention order, never a set iteration. Given the same
     declaration and the same `ConcordanceResult`, the output is
     character-identical.
   - `resolutions(result: ConcordanceResult) -> list[dict]` — the row payloads,
     in mention order, with `ordinal` assigned by position.
   - `render` must NOT emit any `entity_id`, any `cast_basis`, or any discarded
     candidate. The model sees names.
   - `render` raises `ValueError` if `result.ambiguous` is non-empty (the same
     fail-closed shape brief a gave `plan_context`).

3. **`writes/pipeline.py` gains `write_day_rewrite`**, following the module's
   validate-then-write idiom: validate every resolution dict against the check
   shapes BEFORE constructing the first row; raise `ValueError` on any violation;
   return the `DayRewrite`. `generation` is computed by the caller, not guessed
   here. Construct rows with the SQLModel constructors — never
   `db.execute(sa_insert(...))` (`single_canon_write.py` cannot see through it).

4. **Plan-route wiring, `routes/day.py`.** After brief a's 409 guard and inside
   the same transaction that already commits the plan and the germs:
   - compute `generation` as `max(existing) + 1` for this `pass_play_id`, or 1;
   - build `rendered = day_rewrite.render(pass_play.declared_action,
     concordance_result, db)`;
   - stage the `day_rewrite` and its `day_mention_resolution` rows;
   - pass `rendered` to `select_plan` at `:571` in place of
     `pass_play.declared_action`;
   - pass `rendered` to `emit_plan` at `:580` in place of
     `pass_play.declared_action`, and DELETE the `concordance_summary=` keyword
     argument from that call.

5. **Reconcile-path wiring, `cockpit/day_reconcile_apply.py`.** The same swap at
   `:98` and `:141`: `rendered` in, `concordance_summary=` out. The caller passes
   the already-rendered text down; do not re-render inside these functions.

6. **Retire `plan_context`.** Delete it from `day_concordance.py` once all three
   call sites are gone. Its behavior is absorbed by `render`. Delete the
   `concordance_summary` parameter from `emit_plan`'s signature
   (`day_plan.py:447`) and the corresponding append at `:476-477`. The other two
   summary parameters (`standing_steps_summary`, `held_subjects_summary`) stay
   exactly as they are.

7. **The resolve path reads instead of re-deriving.** Replace
   `_concord_declaration` (`routes/day.py:691-704`) with a reader that loads the
   latest `day_rewrite` for the `pass_play` and rebuilds a `ConcordanceResult`
   from its `day_mention_resolution` rows. Delete the three `extract_*` calls at
   `:700-702` and their imports if they become unused at that site. **Fail-closed**:
   if no `day_rewrite` row exists for the `pass_play`, raise
   `HTTPException(409, ...)` naming the missing trace. Never silently
   re-derive, never return an empty `ConcordanceResult`. Remove brief a's
   item-9 interim clause and its comment.

8. **Generation on modify/replace.** The reconcile paths that re-emit a plan
   append a NEW `day_rewrite` at `generation + 1` with its own resolution rows.
   No row on either table is ever UPDATEd or DELETEd, for any reason.

9. **API return.** `_concordance_dict` gains a `rewrite` block:
   `{"generation": int, "rendered_text": str, "resolutions": [...]}` where each
   resolution carries `ordinal`, `category`, `surface_form`, `kind`,
   `role_hint`, `verdict`, `entity_id`, `entity_name`, `rung`, `cast_basis`.
   This is the V1 surface Nia asked for: an enriched API return, not a new
   frontend view.

10. **New check `tooling/verify/checks/day_rewrite.py`**, following the
    `FAILURES` / `fail()` / `_rel` / `_parse` / `ROOT = parents[3]` idiom of
    `verify/checks/day_concordance.py:30-80` and its `main()` shape at
    `:325-345`.
    - W1: `day_rewrite.py` imports no `ollama_client` and constructs no model
      from a named forbidden set (`Entity`, `Character`, `NpcSchedule`,
      `ProposedMutation`). Vacuous-proof: fail if the module has zero function
      definitions.
    - W2: no assignment anywhere in `src/` targets an attribute of a
      `DayRewrite` or `DayMentionResolution` instance, and neither name appears
      as the argument of a `db.delete(`. Vacuous-proof: fail if zero
      constructions of either model are found in the tree.
    - W3: `plan_context` has no remaining caller and no remaining definition.
    - W4: `emit_plan`'s signature no longer names `concordance_summary`.
    - W5: every `select(` in `day_rewrite.py` carries a world scope at query
      construction. Vacuous-proof: fail if zero `select(` calls are found and
      the module reads the DB at all.
    - W6: the resolve-path reader contains no call to `extract_places`,
      `extract_persons` or `extract_factions`.

11. **Golden cases as FAILING inputs**, exact set equality, in the same fixture
    module brief a created:
    - a `ConcordanceResult` with a non-empty `ambiguous` must make `render`
      raise; deleting the guard must make this case fail;
    - two `render` calls over the same inputs must produce byte-identical output;
      introducing any set iteration into `render` must make this case fail;
    - a resolution payload with `verdict="cast"` and `cast_basis=None` must be
      rejected by `write_day_rewrite` before any row is constructed; removing the
      validation must make this case fail;
    - a `pass_play` with no `day_rewrite` row must make the resolve reader raise;
      restoring a silent re-derivation must make this case fail.

12. **Schema doc and changelog.** Add both tables to `world-engine-schema.md`
    with the verbatim NOTE from item 1 about `ambiguous` not being storable, bump
    the `Current schema version:` line and
    `schema_version.EXPECTED_STATIC_SCHEMA_VERSION` together, and append a
    changelog entry naming TICKET-0081 / BRIEF-0081-b and the three readers.
    **Claude Code owns the version number** — do not ask for one.

## Scope OUT

- **`feasibility_veto` (`routes/day.py:483`) keeps the raw declaration.** It
  judges plausibility against the world, and widening its input widens the blast
  radius of this step past one coherent chantier. Deferred; reactivation: a
  measured case where feasibility misjudges because a participant was unnamed.
- **`narrate` (`routes/day.py:719`) keeps the raw declaration.** The narration
  judge (TICKET-0079) compares prose against what the player actually wrote;
  feeding it the rewrite would change what the judge is judging, silently.
  Deferred; reactivation: an explicit decision about what the judge's reference
  text is.
- **`reconcile` (`day_reconcile_apply.py:160`) keeps the raw declaration.**
  Same reason as feasibility: separate chantier.
- **Structural plan deduplication by reference set.** This step swaps
  `select_plan`'s INPUT to the rendered text; it does NOT replace the
  model-ordinal mechanism with a structural comparison of resolved reference
  sets. That is the eventual payoff of the trace and it needs its own decision.
  Reactivation: two or more open plans coexisting regularly, plus a measured
  `select_plan` misfire.
- **An Observation surface for the rewrite.** V1 is the enriched API return.
- **Storing raw LLM responses or prompt text for the extraction calls.** Only
  the rendered plan input is stored.
- **Backfilling rewrites for past `pass_play` rows.** History is sacred; days
  resolved before this ships have no trace and get none.
- **Touching `pass_play.declared_action`.** It stays write-once.
- **Anything in `day_extract.py`**, including adding examples to its prompts
  (standing rule: no prompt examples).
- **Brief a's and brief c's contents.**

## Invariants to defend

- **History is sacred.** Both new tables are append-only. W2 is the structural
  guard, not a convention.
- **Single canon-write authority.** These are pipeline tables, not canon, and
  the write goes through `writes/pipeline.py`. Do not route them through
  `_apply_mutation`, and do not use `db.execute(sa_insert(...))`.
- **The autoflush trap.** Assigning `rewrite_id` on a resolution row in memory
  before the parent is flushed will fire an implicit UPDATE at the next query.
  Construct the parent, flush once, then the children — or construct all rows and
  add them in one `db.add_all` before any read.
- **WAL + `busy_timeout`.** Unchanged; this step adds writes inside an existing
  transaction and must not open a nested session.
- **The model never receives a canon id.** `render` emits names only.
- **No structure without a reader.** `day_rewrite.rendered_text` is read by the
  API block (item 9) and by post-hoc diagnosis; `day_mention_resolution` is read
  by the resolve-path reader (item 7). If either loses its reader during
  implementation, that is a STOP.
- **Module budget and the 80-line function ceiling.** `routes/day.py` is the
  file most at risk; extraction into a helper is expected, not exceptional.

## STOP conditions

- If the full-tree enumeration of `plan_context` callers finds a fourth site not
  listed in the Mini-RECON, STOP: the table above is the brief's coverage claim,
  and an incomplete enumeration invalidates it.
- If the same enumeration for `declared_action` finds a model-facing site not in
  the table, STOP.
- If `generation` cannot be made unique per `pass_play_id` under the existing
  single-commit transaction shape, STOP — do not fall back to a timestamp.
- If deleting `concordance_summary` from `emit_plan` would break a caller
  outside the three enumerated sites, STOP.
- If a golden case cannot be made to FAIL against the pre-change code, STOP.
- If the schema doc's `Current schema version:` line and
  `EXPECTED_STATIC_SCHEMA_VERSION` disagree before this step begins, STOP and
  report — do not reconcile them as a side effect.

## Done means

### Machine-checkable

- [ ] `python tooling/verify/checks/day_rewrite.py` exits 0 and its PASS line
      names W1 through W6.
- [ ] `python tooling/verify/checks/day_concordance.py` still exits 0.
- [ ] `python tooling/verify/checks/schema_version_agreement.py` exits 0.
- [ ] `grep -rn "plan_context" src/` returns nothing.
- [ ] `grep -rn "concordance_summary" src/` returns nothing.
- [ ] `grep -n "extract_places\|extract_persons\|extract_factions" src/world_engine/cockpit/routes/day.py`
      returns exactly the three plan-time call sites and no resolve-time ones.
- [ ] Introducing a set iteration into `render` makes the determinism golden
      case exit non-zero.
- [ ] Deleting the `ambiguous` guard in `render` makes its golden case exit
      non-zero.
- [ ] Emptying the golden fixture makes it exit non-zero (vacuous guard).
- [ ] `module_budget.py` and `function_length.py` exit 0.
- [ ] `/review-step` and `/close-step` run clean.

### Live -> human gate (Nia)

- [ ] Planning a day returns a `rewrite` block whose `rendered_text` reads as
      the declaration with the participants named.
- [ ] Declaring the same intent twice produces the same `rendered_text`,
      character for character.
- [ ] Resolving that day makes three fewer Ollama calls than before (no
      extraction at resolve).
- [ ] Modifying a plan appends `generation: 2`; `generation: 1` is still present
      and unchanged in the DB.
- [ ] `SELECT * FROM day_mention_resolution WHERE verdict = 'ambiguous'` returns
      zero rows and cannot be made to return one.

## Docs to update

- `world-engine-schema.md`: both tables, both indexes, all four check
  constraints, and the verbatim NOTE about `ambiguous`. Bump the
  `Current schema version:` line.
- `src/world_engine/schema_version.py`: `EXPECTED_STATIC_SCHEMA_VERSION` to the
  same value.
- `world-engine-schema-changelog.md`: one newest-first entry naming TICKET-0081,
  BRIEF-0081-b, both tables, and the three readers by name.
- `CLAUDE.md`: only if a pointer is genuinely stale afterward; respect the
  500-line / 38,000-character budget and the archaeology ban on the File
  structure section.
