# BRIEF — Step "Requirement anchoring and the subject index"

## Context

The day plan's `knowledge` requirements are invented by the model and enforced
by Python against nothing: the seeded prompt asks for a free-form
`target_key`, `_validate_requirement` checks only the `type`, and a step-1 gate
on a key no canon row defines empties the entire day. This step makes a
`knowledge` gate legitimate only when the subject exists, in this world, on
some entity other than the player, on a non-secret row -- and drops it
otherwise. It also tells the emission model which subjects the player already
holds, adds the index the anchoring lookup needs, and widens `Verdict` with the
requirement `type` that BRIEF-0078-b and -c both consume. Rendering a blocked
step as prose (BRIEF-0078-b) and proposing the rumor (BRIEF-0078-c) are NOT in
this step: after this brief, an anchored-but-unmet step 1 still produces the
old one-liner.

## Mini-RECON (measured against the fresh tarball, `main`)

All anchors verified against the tree. **If any of these contradicts what you
find, STOP and escalate -- do not adapt the brief yourself.**

- [M] `day_plan.py` -- 398 physical lines. `REQUIREMENT_TYPES` at 70,
  `MAX_PLAN_STEPS` at 74, `RequirementSpec` at 80-85, `PlanStep` at 88-93,
  `Verdict` at 96-101 (four fields: `met`, `current`, `required`, `reason`),
  `_eval_knowledge` at 127-139, `_eval_relation_gte` at 142-164,
  `_eval_resource` at 167-176, `_eval_location_reachable` at 179-188,
  `_EVALUATORS` at 191-196, `evaluate_requirements` at 229-248, `budget_cut`
  at 251-275, `_validate_requirement` at 298-314, `_validate_step` at 317-337,
  `emit_plan` at 340-397.
- [M] `day_plan.py:365-374` -- `emit_plan` appends `concordance_summary` and
  `standing_steps_summary` VERBATIM to the user message after the template
  substitution, never as a template placeholder; both default to `""`.
- [M] All four `Verdict(...)` constructions use keyword arguments only
  (`day_plan.py:139, 164, 176, 188`).
- [M] `day_resolve.py:70-78` -- imports `Verdict as RequirementVerdict` from
  `day_plan`; `resolution.Verdict` is a DIFFERENT class imported at line 88.
- [M] `cockpit/routes/day.py` -- 834 physical lines. `_finalize_plan` at
  460-510; `evaluated_steps` built at 463-465; `budget_cut` at 467; the
  feasibility veto at 471; `write_day_plan` at 476-483; the response dict at
  498-510 with `first_excluded_index` at 505.
- [M] `models/canon.py:442-472` -- `Knowledge`; fields include `entity_id`,
  `subject`, `is_secret`; `__table_args__` holds
  `CheckConstraint("share_threshold BETWEEN 1 AND 100", name="ck_knowledge_share_threshold")`
  and `Index("idx_knowledge_entity", "entity_id")`. There is NO `world_id`
  column and NO index on `subject`.
- [M] `world-engine-schema.md:3` -- `Current schema version: v1.95`.
  `world-engine-schema.md:2001` -- `CREATE INDEX idx_knowledge_entity ON knowledge(entity_id);`
  is the only knowledge index.
- [M] `scripts/migrate_v1_95_parked_plans.py` -- the most recent migration;
  `scripts/migrate_v1_94_agenda_step_plan.py:23-45` holds the fail-closed env
  preamble every migration carries.
- [M] `scripts/seed_pilot.py:1727-1756` -- `DAY_PLAN_SYSTEM_PROMPT`;
  1743-1748 is the `requires` rule with the two permitted forms.
  `DAY_PLAN_USER_TEMPLATE` at 1758-1763 substitutes `{character_name}` and
  `{declaration}` only.
- [M] `day_concordance.py:259-278` -- `plan_context`; returns resolved
  mentions and role hints only, never a knowledge inventory.
- [M] `tooling/verify/checks/day_plan.py` -- rules R1-R24; `_tuple_assign`,
  `_named_dict`, `_find_function`, `_parse` helpers available; every rule
  carries an anti-vacuity guard except R17.
- [M] `tooling/verify/canon_write_policy.txt:21` --
  `writes/knowledge.py::write_knowledge` is the allow-listed writer of table
  `knowledge`; line 111 holds `crud/knowledge.py::delete_knowledge`.

**STOP conditions.** Stop and escalate, without writing code, if: (1) any
anchor above is materially different; (2) `Verdict` turns out to be
constructed positionally anywhere in the tree -- widening it would then be a
silent breakage rather than an additive change; (3) the live DB already
contains an index named `idx_knowledge_subject`; (4) `emit_plan` has acquired
a call site outside `cockpit/routes/day.py` -- the held-subjects summary would
then need a second construction point this brief does not specify.

## Scope IN

Items 1-2 are one commit (schema + migration). Items 3-7 follow. Item 8 is the
verify commit.

1. **Schema v1.96.** Add `Index("idx_knowledge_subject", "subject")` to
   `Knowledge.__table_args__` (`models/canon.py`), the matching
   `CREATE INDEX idx_knowledge_subject ON knowledge(subject);` line to
   `world-engine-schema.md`, bump `Current schema version:` to `v1.96`, bump
   `EXPECTED_STATIC_SCHEMA_VERSION` in `src/world_engine/schema_version.py`,
   and prepend the changelog entry to `world-engine-schema-changelog.md`.

2. **Migration `scripts/migrate_v1_96_knowledge_subject_index.py`.** Carries
   the fail-closed env preamble verbatim from
   `scripts/migrate_v1_94_agenda_step_plan.py:23-45`. Index-only:
   `CREATE INDEX IF NOT EXISTS idx_knowledge_subject ON knowledge(subject)`
   plus the `schema_meta` version row update, inside one `engine.begin()`.
   **No table rebuild** -- adding an index needs none, and the rebuild dance
   from `migrate_v1_8_gatherings.py` must NOT be copied here.

3. **`Verdict` gains a `type` field** (`day_plan.py:96-101`), placed FIRST in
   the dataclass so a positional construction would fail loudly rather than
   silently shift. Each of the four evaluators sets `type=req.type`. Nothing
   else changes about `Verdict`.

4. **Two anchoring readers in `day_plan.py`**, both single explicitly-filtered
   `select(` statements (enumeration-scope discipline), both called at most
   once per emission (F3):

   - `_held_subjects(character, db) -> frozenset[str]` --
     `select(Knowledge.subject).where(Knowledge.entity_id == character.id).distinct()`.
   - `_anchorable_subjects(character, db) -> frozenset[str]` --
     `select(Knowledge.subject).join(Entity, Entity.id == Knowledge.entity_id)`
     with all three filters: `Entity.world_id == character.world_id`,
     `Knowledge.entity_id != character.id`, `Knowledge.is_secret == False`,
     then `.distinct()`.

   The B3 predicate lives in `_anchorable_subjects` and nowhere else. Add a
   module comment stating, verbatim:

   > B3: a gate is legitimate only on a subject that exists to be learned --
   > held in this world by an entity OTHER than the player, on a non-secret
   > row. `is_secret` is excluded because a gate on a secret is both
   > unsatisfiable and a disclosure: the reject message would reveal that the
   > secret exists.

5. **`anchor_requirements(steps, character, db) -> tuple[list[PlanStep], list[dict]]`**
   in `day_plan.py`. Calls `_anchorable_subjects` ONCE, then rebuilds each
   `PlanStep` with `dataclasses.replace`, keeping every requirement except a
   `knowledge` one whose `target_key` is absent from the anchorable set. It
   drops REQUIREMENTS, never steps -- the returned step count always equals
   the input count. Each drop appends
   `{"step_index": <int>, "objective": <str>, "target_key": <str>}` to the
   report list, and logs one `_log.info` line naming the key. A step whose
   only requirement was dropped becomes an ungated step, which is the intended
   outcome, not a degradation.

6. **`emit_plan` gains `held_subjects_summary: str = ""`**, appended VERBATIM
   to the user message after `standing_steps_summary`
   (`day_plan.py:370-373`'s precedent, same reason: text a Python pass built,
   never a new template placeholder a virgin-head-only seed could not
   retrofit). Default `""` keeps every pre-existing call byte-identical.

   Add `MAX_HELD_SUBJECTS_SHOWN: int = 40` as a module-level constant and a
   builder `held_subjects_summary(character, db) -> str` calling
   `_held_subjects` once, sorting, truncating beyond the bound with an
   `_log.info` reporting the truncated count, and returning `""` when the
   player holds no subject at all. Its text, VERBATIM:

   ```
   Sujets que {character_name} connaît déjà : {liste}.
   Une condition « knowledge » porte sur un sujet absent de cette liste.
   ```

   `{liste}` is the sorted subjects joined by `", "`. Positive form only --
   the gameplay model is abliterated. **No seeded prompt template changes in
   this brief.**

7. **Wiring in `_finalize_plan`** (`cockpit/routes/day.py:460-510`), in this
   order: `anchor_requirements` runs on `raw_steps` BEFORE the
   `evaluated_steps` comprehension at 463-465, so a dropped requirement never
   reaches `evaluate_requirements` and never reaches
   `agenda_step_requirement`. The response dict at 498-510 gains, alongside
   the existing keys:

   ```python
   "anchoring": {"dropped": dropped_report},
   "blocked_at_index": blocked_index,
   "blocked_reason": blocked_text,
   ```

   where `blocked_index` is `budget_result.first_excluded_index` when that
   index's step is unmet and `None` otherwise (a budget-only cut is not a
   block), and `blocked_text` is the joined `reason` of that step's unmet
   verdicts, or `None`. **E2 is reporting, never refusing** -- `/plan` returns
   200 and writes the plan exactly as it does today.

   `emit_plan`'s call site in this file passes
   `held_subjects_summary=held_subjects_summary(character, db)`.

8. **Verify.** Extend `tooling/verify/checks/day_plan.py` with R25-R28,
   continuing that file's own numbering, each anti-vacuity guarded:
   - R25: `Verdict`'s field list starts with `type`, and all four
     `Verdict(` constructions in `day_plan.py` pass a `type=` keyword. Zero
     constructions collected is a FAILURE.
   - R26: `_anchorable_subjects` exists and its body references all three of
     `world_id`, `is_secret` and a `!=`/`is_not` comparison against
     `character.id`; `_held_subjects` exists. Zero located is a FAILURE.
   - R27: `anchor_requirements` is called in `cockpit/routes/day.py` and the
     call appears in `_finalize_plan` BEFORE the first reference to
     `evaluate_requirements` in that function (compare `lineno`).
   - R28: `emit_plan` appends `held_subjects_summary` with `+=` to the user
     message and `held_subjects_summary` appears in NO seeded prompt constant
     in `scripts/seed_pilot.py` -- proving it is appended text, not a
     template placeholder.

## Scope OUT

Do not build, touch or "improve" any of the following. Each was discussed
during planning and deferred deliberately.

- **The blocked band, `[BLOQUÉ]`, and any change to `blocked_reason`,
  `resolve_steps`, `_truncate_on_failure`, `judge_narration`, `StepFact` or
  the zero-outcome branch at `cockpit/routes/day.py:816-832.`** That is
  BRIEF-0078-b in full. After this brief the old one-liner still fires for an
  anchored-but-unmet step 1; that is correct and expected.
- **`new_knowledge` emission, `EMITTED_MUTATION_TYPES`, `_EMITTERS`, or
  anything in `day_mutations.py`.** That is BRIEF-0078-c.
- **Anchoring at resolve time.** `day_resolve.py` must gain no anchoring call.
  A dropped requirement is never persisted, so `resolve_steps`' re-evaluation
  can never see one. Adding a second anchoring site would be a second
  authority for the same rule.
- **`_eval_resource`'s ignored `target_key`** (`day_plan.py:167-176`). Known,
  measured, REPORT ONLY -- it gets its own ticket (E1).
- **Any level check in `_eval_knowledge`.** H1 is locked: `row is not None`
  stays. Do not read `level`, do not consult `KNOWLEDGE_LEVEL_LADDER`, do not
  populate `agenda_step_requirement.threshold` for a `knowledge` row.
- **Subject normalization, an alias table, a canonical-vocabulary table, or a
  merge tool.** G1 is deferred with a numeric reactivation condition recorded
  in the ticket. `writes/knowledge.py` is not touched by this brief.
- **Refusing a plan at `/plan` time**, whether on a dropped requirement or on
  `first_excluded_index == 0`. E2 resolved to reporting.
- **A table, column or JSON field persisting the anchoring drop report.** It
  travels in the HTTP response and the log only -- no structure without a
  reader.
- **Widening `REQUIREMENT_TYPES`** or adding a fifth evaluator.
- **A table rebuild in the migration.** Index-only.

## Invariants to defend

- **"Model proposes, code judges."** This step is the sharpest test of it in
  the tree: the model was proposing the CRITERION, and code was enforcing it.
  Anchoring restores the boundary. The temptation to defend against is
  "helpfully" repairing an unanchored key to its nearest canon neighbour --
  that is the model's vocabulary entering canon by another door, which G1
  explicitly defers.
- **Exclusion is structural, never instructional.** The `is_secret` filter
  belongs in `_anchorable_subjects`' WHERE clause. It must not be a prompt
  instruction, and the reject path must never mention that a secret subject
  was the reason a key failed to anchor.
- **Enumeration scope discipline.** Both new readers are `select(` calls
  outside `models/` and `writes/`; each carries explicit filters. Neither may
  be written as an unfiltered scan with Python-side filtering.
- **Fail-closed with vacuous proof.** R25-R28 each fail when they collect zero
  items. An anchoring check that passes because it found nothing to check is a
  broken check.
- **Schema is authoritative.** The doc line, the code constant and the live
  `schema_meta` row move together in one commit.

## Done means

- [ ] `python -m tooling.verify.checks.day_plan` prints PASS and its message
      names R25-R28.
- [ ] `python -m tooling.verify.checks.schema_version_agreement` prints PASS
      with v1.96.
- [ ] `python -m tooling.verify.checks.module_budget` and
      `function_length` print PASS.
- [ ] `python -m tooling.verify.checks.corpus_gate` prints PASS.
- [ ] `sqlite3 ~/.world_engine/world_engine.db ".indexes knowledge"` lists
      `idx_knowledge_subject`.
- [ ] Live: a declaration whose plan the model gates on an invented key
      returns 200 from `/api/day/{batch}/plan` with a non-empty
      `anchoring.dropped` list naming that key, and
      `SELECT type, target_key FROM agenda_step_requirement WHERE step_id = ...`
      shows the dropped requirement was never written.
- [ ] Live: that same day's `/resolve` produces a normal narrative with dice,
      not "La journée n'a pas pu commencer".
- [ ] Live: a declaration gated on a subject a real NPC holds returns
      `blocked_at_index: 0` and a non-null `blocked_reason` from `/plan`, and
      `/resolve` still returns the old one-liner (BRIEF-0078-b's job).
- [ ] Live: `emit_plan`'s outgoing user message, captured in the log, ends
      with the held-subjects block for a character who holds subjects, and is
      unchanged for one who holds none.
- [ ] `/review-step` and `/close-step` both run and report clean.

## Docs to update

- `world-engine-schema.md` -- `idx_knowledge_subject`, version line to v1.96.
- `world-engine-schema-changelog.md` -- new v1.96 entry naming TICKET-0078 and
  this brief, and stating that the index's sole reader is
  `day_plan._anchorable_subjects`.
- `ARCHITECTURE_DECISIONS.md` -- append two entries: **B3 (knowledge-gate
  anchoring predicate)** with its reasoning, and **G1 (subject-vocabulary
  hygiene deferred)** with the numeric reactivation condition verbatim from
  the ticket.
- `CLAUDE.md` -- no change.
