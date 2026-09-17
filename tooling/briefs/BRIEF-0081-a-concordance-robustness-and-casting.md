# BRIEF — Step "concordance robustness and casting"

TICKET-0081, brief a of c. Decisions G2, C2-partition, F1, E2c.

## Context

`day_concordance.concord()` resolves the mentions pulled from a day declaration
against canon rows. Two opposite failure modes were measured against a fresh
tarball of `main` at schema v1.96, and they need opposite remedies.

Recall is too low on the named path: `_rung_named_exact` is a `casefold()`
equality on the whole surface form, so a qualified or article-prefixed name
misses. Recall is adequate but unranked on the inferred path: a role reference
matching twelve NPCs is classified `ambiguous`, and TICKET-0081 makes ambiguity
fail-closed, so without this step every role reference would block a day.

The partition that dissolves the second problem already exists in the schema:
`Mention.kind` is `named` or `inferred`, and the rungs are already disjoint on
it. A multi-candidate INFERRED mention is a role reference — any member of the
set satisfies it, and choosing is casting, not resolving. A multi-candidate
NAMED mention is a genuine identity collision and stays fail-closed.

## Mini-RECON

All [M] unless marked, against `codeload.github.com/niaairen31-ui/WG-Nia/tar.gz/refs/heads/main`,
`Current schema version: v1.96`.

- `src/world_engine/day_concordance.py` is 278 lines. `concord` spans
  `:172-215` (~44 lines). Module budget is comfortable; the 80-line function
  ceiling on `concord` is the constraint this step must respect.
- `MATCHING_RUNGS` at `:47` is `("named_exact", "named_alias", "occupation",
  "presence")`; `_RUNG_LOOKUPS` at `:152` is its bijective dispatch dict.
  `verify/checks/day_concordance.py` R6 (`:271-299`) enforces the bijection and
  compares against a hardcoded `EXPECTED_RUNGS` at `:55`.
- `_rung_named_exact` (`:95-108`): returns None unless `mention.kind ==
  "named"`; fetches all active `Entity` of the mapped type in the world, then
  compares `e.name.casefold() == mention.surface_form.casefold()`.
- `_rung_named_alias` (`:111-117`): unconditionally returns None. Decision D1 of
  BRIEF-0075-c — a permanent structural no-op, not a stub.
- `_rung_occupation` (`:119-140`): returns None unless `category == "person"`
  and `kind == "inferred"` and `role_hint` is set. Joins `NpcSchedule` to
  `NpcGoal` on `standing_goal_id`, world-scoped, `kind == "standing"`,
  `status == "active"`; matches `_role_keywords` substrings against
  `NpcGoal.description`. **No proximity scope of any kind.**
- `_rung_presence` (`:142-149`): returns None unless `category == "person"` and
  `kind == "inferred"` and `ctx.place_candidate_ids` is non-empty. Sweeps all
  four `SCHEDULE_PHASES` through `schedule_reads.who_is_at`.
- `_resolve_place_candidates` (`:160-169`): builds `place_candidate_ids` from
  `_rung_named_exact` alone. So a place mention that is INFERRED never enters
  the presence context.
- `ConcordanceResult` (`:77-81`): `matched`, `ambiguous`, `unmatched`,
  `skipped_rungs`.
- `concord` (`:186-201`): first rung returning a non-None list wins; a
  single-element list is `matched`, anything longer is `ambiguous`.
- `plan_context` (`:259-278`): renders `matched` as resolved names and
  person-only `unmatched` as roles. It renders `ambiguous` NOWHERE — an
  ambiguous mention silently disappears from the context handed to the plan
  model.
- `day_plan._day_reachable_ids` (`day_plan.py:213-241`): a day-local
  `connects_to` BFS, unbounded, origin included, both column orders, filtering
  to `Entity.type == "location"` and `status == "active"`. Its module docstring
  restates the standing rule (D1, BRIEF-19; BRIEF-0075-b-amendment-1): every new
  `connects_to` consumer gets its OWN reader. That amendment counted roughly
  seven existing readers.
- `NpcSchedule` (`models/schedule.py:40-64`): one row per `(npc_id, phase)`,
  carrying `location_id` (FK `entity.id`) and optional `standing_goal_id`.
- `Character.current_location_id` (`models/canon.py:169`) is `Optional[str]`.
- `Relation` (`models/canon.py:405-425`): `entity_a_id`, `entity_b_id`, `type`,
  `direction`, `intensity` (1..100, default 50).
- `Knowledge.subject` (`models/canon.py:455`) is a free string, not an entity
  FK. `NpcGoal` (`:503-529`) has NO secrecy column. This is why E2c is scoped by
  reachability rather than by knowledge.
- Route wiring: `_extract_and_concord` (`routes/day.py:423-441`) stages germs
  with `db.add(germ)` but does NOT commit; the commit happens later in the
  request. `_concord_declaration` (`routes/day.py:691-704`) re-runs extraction
  and concordance at resolve time.

## Scope IN

1. **`_normalize_surface(text: str) -> str`**, new module-level helper in
   `day_concordance.py`. In order: casefold; NFKD-decompose and drop combining
   marks; strip a leading token drawn from a named module-level frozenset
   `_LEADING_TOKENS`; collapse internal whitespace runs to one space; strip.
   `_LEADING_TOKENS` is exactly, and only:

   ```
   {"chez", "le", "la", "les", "l", "du", "de", "des", "au", "aux", "a"}
   ```

   Strip repeatedly while the first token is in the set, bounded at three
   iterations. Applied to BOTH sides of every named comparison — never to one
   side only.

2. **`_rung_named_exact` uses `_normalize_surface` on both sides.** Behavior is
   otherwise unchanged: still `kind == "named"` only, still world-scoped and
   type-scoped at query construction, still returns a list or None.

3. **New rung `named_token`, inserted immediately after `named_exact` in
   `MATCHING_RUNGS`.** New order, verbatim:

   ```python
   MATCHING_RUNGS: tuple[str, ...] = (
       "named_exact", "named_token", "named_alias", "occupation", "presence",
   )
   ```

   `_rung_named_token` returns None unless `kind == "named"`. It tokenizes both
   the normalized entity name and the normalized surface form on whitespace, and
   matches when the entity-name token set is a non-empty SUBSET of the surface
   form token set AND at least one entity-name token has length >= 3. Add
   `"named_token": _rung_named_token` to `_RUNG_LOOKUPS`.

4. **E2c — reachability scope on `_rung_occupation`.**
   4a. New day-local traversal `_concord_reachable_ids(origin_location_id: str,
   db: Session) -> frozenset[str]` in `day_concordance.py`. It is a NEW reader,
   written fresh in this module. Do NOT import or call
   `day_plan._day_reachable_ids`, and do not extract a shared one: standing rule
   D1 (BRIEF-19), restated in `day_plan.py`'s module docstring and in
   BRIEF-0075-b-amendment-1. A real dedup opportunity is REPORTED, never acted
   on. Shape: unbounded BFS over `Relation.type == "connects_to"`, both column
   orders, origin INCLUDED, filtered to `Entity.type == "location"` and
   `Entity.status == "active"`.
   4b. `_ConcordContext` gains `reachable_location_ids: frozenset[str]`,
   computed ONCE per `concord` call from `character.current_location_id`.
   4c. `_rung_occupation` filters its candidate NPCs to those having at least one
   `npc_schedule` row whose `location_id` is in `reachable_location_ids`. The
   filter is applied at query construction (join and `WHERE ... IN`), never as a
   post-fetch list comprehension.
   4d. **Fail-closed**: if `character.current_location_id` is None, or if
   `reachable_location_ids` is empty, `_rung_occupation` returns None. It does
   NOT fall back to a world-wide search.

5. **The verdict partition.** `ConcordanceResult` gains a fourth field, and a
   new frozen dataclass:

   ```python
   @dataclass(frozen=True)
   class CastMention:
       mention: Mention
       entity_id: str
       rung: str
       basis: str
       candidate_ids: tuple[str, ...]
   ```

   `ConcordanceResult` becomes `(matched, cast, ambiguous, unmatched,
   skipped_rungs)`. In `concord`, when a rung returns a list:
   - length 1 -> `matched`, unchanged.
   - length > 1 and `mention.kind == "named"` -> `ambiguous`, unchanged.
   - length > 1 and `mention.kind == "inferred"` -> `cast`, via `_cast_one`.

   Extract this classification into its own function
   (`_classify(mention, result, ctx, character, db)`) so `concord` stays under
   the 80-line ceiling.

6. **F1 — `_cast_one`.** Declared precedence, as a module-level tuple and a
   bijective dispatch dict, mirroring the `MATCHING_RUNGS`/`_RUNG_LOOKUPS`
   idiom:

   ```python
   CAST_PRECEDENCE: tuple[str, ...] = ("presence", "relation", "stable")
   ```

   Each criterion narrows the candidate list; the first that narrows it to
   exactly one wins and names the basis.
   - `presence` — candidates present at any `ctx.place_candidate_ids` location
     in any phase.
   - `relation` — candidates holding the unique maximum `Relation.intensity` on
     a row linking `character.id` and the candidate in either column order.
   - `stable` — the lexicographically lowest `entity_id`. This criterion is
     TOTAL: it always yields exactly one, so `_cast_one` can never return
     nothing.

   `_cast_one` returns `(entity_id, basis)`.

7. **`plan_context` renders cast mentions**, in the same shape as matched ones,
   with no mention of the basis or of the discarded candidates (the model gets a
   resolved name, nothing more). Additionally, `plan_context` becomes
   fail-closed: if `result.ambiguous` is non-empty it raises `ValueError` rather
   than rendering. It is structurally unreachable with ambiguity present (item
   8), and this makes that structural, not conventional.

8. **The 409 at the plan route.** In `routes/day.py`, immediately after
   `_extract_and_concord` returns and BEFORE any further work, if
   `concordance_result.ambiguous` is non-empty, raise `HTTPException(409, ...)`
   whose detail names each ambiguous surface form and the NAMES (not the ids) of
   its candidates. Nothing is committed — the staged germs die with the
   transaction. Do not commit before raising.

9. **Interim behavior at the resolve path, to be removed in BRIEF-0081-b.**
   `_concord_declaration` (`routes/day.py:691`) still re-derives. If its result
   carries a non-empty `ambiguous`, do NOT 409 there: log at INFO and treat those
   mentions as unresolved for `freeze_facts`. Reason: the extraction pass is an
   LLM call, so the resolve-time mention set can differ from the plan-time one,
   and a 409 at resolve would strand a planned day. BRIEF-0081-b deletes this
   re-derivation entirely; this clause exists so that brief a is independently
   shippable and is expected to be short-lived.

10. **Update `tooling/verify/checks/day_concordance.py`.**
    - `EXPECTED_RUNGS` gains `"named_token"`.
    - New R8: `CAST_PRECEDENCE` and `_CAST_LOOKUPS` are located, non-empty, and
      in bijection; and `"stable"` is the last element of `CAST_PRECEDENCE`.
    - New R9: `day_concordance.py` defines a function whose body contains a
      `connects_to` string constant, AND the module's import list does not name
      `_day_reachable_ids`. Fail on either half.
    - New R10: `_rung_occupation`'s body contains a reference to the context's
      reachable-ids attribute. Fail if absent (this is the E2c tripwire).
    - Every new check fails on a zero-item collection rather than passing
      vacuously, matching the existing `_report_and_exit`/`FAILURES` idiom at
      `:60-70` and `:325-345`.

11. **Golden cases as FAILING inputs.** Add a fixture module under
    `tooling/verify/` holding concordance scenarios that the PRE-change code
    gets wrong, each asserted with exact set equality on the four verdict
    buckets — not a substring check, not a count. Minimum set:
    - a named mention with a leading article that must now match;
    - a named mention with a trailing qualifier that must now match via
      `named_token`;
    - an inferred person mention with three candidates that must land in `cast`
      with basis `"stable"` and MUST NOT appear in `ambiguous`;
    - two same-named active entities that must land in `ambiguous` and MUST NOT
      be cast;
    - an inferred person mention whose only occupation candidates are outside
      the reachable set, which must land in `unmatched`.

    Each case names the mutation it detects: removing the `kind` guard from the
    classification must flip case 3 to `ambiguous` and fail; removing the E2c
    filter must flip case 5 to `matched` or `cast` and fail; removing
    `_normalize_surface` from either side must flip cases 1-2 to `unmatched` and
    fail. State these mutations in the fixture's docstring so a future reader can
    re-verify sensitivity without re-deriving them.

## Scope OUT

Named explicitly because they are adjacent and were discussed:

- **Inferred places and factions.** They resolve to nothing and are reported
  nowhere. Do not add a rung, a type-catalog match, or a germ path for them.
  Carry the consequence in a comment on `_resolve_place_candidates`: F1's
  `presence` criterion is inert whenever the place was inferred rather than
  named, because `place_candidate_ids` comes only from `_rung_named_exact`.
- **G3, the alias table.** `_rung_named_alias` stays an unconditional `None` and
  keeps its `_ALIAS_SKIP_NOTE`. Do not build an `entity_alias` table, do not
  repurpose `faction_membership.cover_role`.
- **G4, edit distance / fuzzy matching.** Rejected without a reactivation
  condition.
- **E2d.** Do not add `is_secret` to `npc_goal`.
- **F2 and F3.** No model call decides a casting. No role-shaped requirement
  target. `agenda_step_requirement` is not touched.
- **The trace tables, the rewrite object, the renderer.** All of that is
  BRIEF-0081-b. This brief persists nothing new and adds no table.
- **Germ emission.** `emit_germs` is not touched here. Its collision guard and
  quota are BRIEF-0081-c.
- **`day_extract.py` and its three prompts.** Not touched. In particular: no
  examples are added to any prompt (standing rule — examples become vocabulary
  reservoirs that tint unrelated output).
- **Swapping the model input at `feasibility_veto`, `narrate` or `reconcile`.**
  BRIEF-0081-b's business, and partly its Scope OUT too.
- **Deduplicating the `connects_to` readers.** Report the count if you like;
  do not act.

## Invariants to defend

- **R1, purity of `day_concordance.py`.** The module gains reads
  (`Relation`, `NpcSchedule`, the BFS) and must still contain no `db.add(` and
  no `.commit(`. `verify/checks/day_concordance.py:147` enforces this; the new
  code is the most likely place to break it.
- **World scoping at query construction.** Every new `select(` — the BFS, the
  reachability join, the relation lookup — carries its world scope in the query,
  never as a post-fetch filter. `_ConcordContext.world_id` is the source.
- **Structural exclusion, not instructional.** E2c is a `WHERE` clause. Nothing
  about scope is ever expressed to a model.
- **D1, one reader per `connects_to` consumer.** The new BFS is written fresh in
  this module.
- **The model never receives a canon id.** `plan_context` renders names; the new
  `cast` rendering must not leak `entity_id`, `basis`, or the discarded
  candidates.
- **Function-length ceiling, 80 lines.** `concord` is at ~44 and this step adds
  branching. The classification extraction (item 5) is not optional.
- **Module budget, 1000 lines.** `day_concordance.py` is at 278; this step
  should land well under the cap. If it does not, that is a STOP.

## STOP conditions

Escalate rather than guess:

- If `concord` cannot be kept under 80 lines after extracting `_classify`.
- If `day_concordance.py` would exceed 800 lines.
- If any existing `select(` in `day_concordance.py` is found to lack a
  world scope at query construction — report it, do not fix it in this commit.
- If the `MATCHING_RUNGS` / `_RUNG_LOOKUPS` bijection cannot be preserved with
  `named_token` inserted.
- If `verify/checks/day_concordance.py` R6's hardcoded expectations cannot be
  updated without weakening the check.
- If a golden case cannot be made to FAIL against the pre-change code — that
  means the case is a desired output, not a failing input, and the fixture is
  worthless as written.

## Done means

### Machine-checkable

- [ ] `python tooling/verify/checks/day_concordance.py` exits 0 and its PASS
      line names the casting bijection and the E2c tripwire.
- [ ] Reverting the `kind` guard in `_classify` makes the golden fixture exit
      non-zero, naming case 3.
- [ ] Reverting the E2c filter in `_rung_occupation` makes the golden fixture
      exit non-zero, naming case 5.
- [ ] Reverting `_normalize_surface` on either side makes the golden fixture
      exit non-zero, naming cases 1 and 2.
- [ ] Emptying the golden fixture makes it exit non-zero (vacuous guard).
- [ ] `grep -n "db.add(\|\.commit(" src/world_engine/day_concordance.py` returns
      nothing.
- [ ] `grep -n "_day_reachable_ids" src/world_engine/day_concordance.py` returns
      nothing.
- [ ] `python tooling/verify/checks/function_length.py` and
      `module_budget.py` exit 0.
- [ ] `/review-step` and `/close-step` run clean (engine code is touched).

### Live -> human gate (Nia)

- [ ] A declaration naming a person with a leading article or a trailing
      qualifier resolves, where it did not before.
- [ ] A declaration referring to a role held by several NPCs plans without a
      409, and the API return names which NPC was chosen.
- [ ] Two active entities of the same type sharing a name produce a 409 naming
      both, and no `proposed_mutation` row is created by that request.
- [ ] A declaration referring to an occupation held only by a distant NPC no
      longer resolves to that NPC — it germinates instead.

## Docs to update

- No schema change; no changelog entry, no version bump. If a schema change
  turns out to be needed, that is a STOP, not a silent bump.
- `CLAUDE.md`: only if the `named_token` rung or the casting precedence belongs
  in a pointer already there. Respect the 500-line / 38,000-character budget
  enforced by `claude_md_contract.py`; if the addition would breach it, report
  and do not trim something else to make room.
- Add the new fixture path to whatever index `corpus_gate.py` expects, if any.
