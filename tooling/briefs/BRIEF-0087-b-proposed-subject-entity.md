# BRIEF 0087-B — "The model names the subject; the code checks it"

Lot: LOT-0087-knowledge-subject-participants.md (authoritative on conflict)
Depends on: BRIEF-0087-a (consumes C-01 and C-02)
Regenerated after AMENDMENT-0087-1 (code `J2`): the `role="subject"` discriminator
is dropped; `fact_participant` is uniquely keyed on `(fact_id, entity_id)`.

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/cockpit/mutations.py:361-398` -> `_mutation_apply_new_knowledge(mut, payload, db)` reads `payload.get("entity_id") or mut.target_id`, returns the string `"new_knowledge: payload must contain entity_id (or set target_id)"` when absent, and calls `write_knowledge` with no `fact_id`.
- `src/world_engine/cockpit/routes/mutations.py:461` -> `"new_knowledge": _mutations._mutation_apply_new_knowledge` in the dispatch table.
- `src/world_engine/cockpit/routes/mutations.py:294-311` -> the conversation-sourced duplicate guard's `new_knowledge` key is `conversation_id` + `entity_id` + `subject`.
- `src/world_engine/analyzer_transcript.py:283-301` -> `_build_payload_new_knowledge` sets `"subject": _content_to_subject_slug(content)` and uses the model's `"subject"`/`"entity"` field to infer the LEARNER, not the topic.
- `src/world_engine/analyzer_transcript.py:241-247` -> `_content_to_subject_slug` joins the first five lowercased words with underscores, truncated at 50 characters.
- `src/world_engine/day_mutations.py:214-259` -> `_emit_new_knowledge` takes `subject` from `v.required` on an unmet knowledge verdict, and constructs `ProposedMutation(... mutation_type="new_knowledge", payload=payload ...)`.
- `src/world_engine/models/pipeline.py:129` -> `payload: Any = Field(sa_column=Column(JSON, nullable=False))`.
- `src/world_engine/models/canon_knowledge.py:119-122` -> `idx_fact_participant_unique` on `(fact_id, entity_id)`, unique; `role` is outside that key.
- `CLAUDE.md:214-217` -> `_apply_mutation` runs its writes inside one SAVEPOINT.
- `src/world_engine/prompt_registry.py` -> prompt templates live in the DB (`prompt_template` head + `prompt_version` rows); `current_prompt()` is the sole read accessor and `write_prompt_version` the sole write shape.
- `tooling/verify/checks/fact_spine.py:103-205` -> the DB-fixture idiom: fresh temp-file SQLite with `WORLD_ENGINE_DATABASE_URL` set before any `world_engine` import, fixture built through the real sanctioned writers, one case broken on purpose to prove the FAIL path names it, then healed to prove PASS returns.

## Facts carried

**R-05** — two producers construct a `new_knowledge` payload.
`analyzer_transcript._build_payload_new_knowledge` sets `subject` to
`_content_to_subject_slug(content)` — the first five words of the content,
lowercased, non-word characters stripped, joined by underscores, truncated at
50 characters (`analyzer_transcript.py:241-247`). The model's own `"subject"`
/ `"entity"` field is read for a different purpose entirely: to infer **who
learned** the fact (`analyzer_transcript.py:287-293`). The model is never
asked what the knowledge is about.
`day_mutations._emit_new_knowledge` takes `subject` from `v.required`
(`day_mutations.py:231`). `ProposedMutation.payload` is a JSON column
(`models/pipeline.py:129`), so a new payload key is not a schema change.

**R-06** — replaying `lore_resolve`'s rungs over production: 69 of 312
distinct subjects match (22.1%), 98 of 615 rows (15.9%); 0 ambiguous; 243
subjects and 517 rows unmatched.

**R-09** — not one subject string in the production database resolves to two
or more candidate entities, in any category, in any world.

**R-10** — 12 of 615 knowledge rows carry a `session_id`; 15 of 310 distinct
subjects contain an underscore; 295 rows carry a NULL `source`. The creator
CRUD, not the analyzer, is the dominant producer of existing rows.

**R-02** — `fact_participant` carries `idx_fact_participant_unique` on
`(fact_id, entity_id)`, unique (`canon_knowledge.py:119-122`), with `role`
outside that key. `attach_participants` performs a plain `db.add` with no
duplicate check of its own, so a collision raises `IntegrityError` at commit.
On this path that matters more than elsewhere: `_apply_mutation` runs its
writes inside one SAVEPOINT (`CLAUDE.md:214-217`), so a tripped constraint
would abort the whole mutation apply, not just the participant write. `C-01`'s
read-before-write guard is what prevents it.

**R-15** — `CLAUDE.md:143-145`, verbatim: *"`new_knowledge` / `status_change`
are idempotent facts: identity-based dedup (`entity_id` + `subject`;
`entity_id`) via `_mutation_match_key`, same conversation required."* And
`CLAUDE.md:157-158`: *"Two canon-write paths for rows: `_apply_mutation`,
creator CRUD."*

## Contracts

Consumes **C-01** and **C-02** (verbatim copies in BRIEF-0087-a; do not
re-describe them). Produces **C-03**.

### C-03 — the `new_knowledge` payload key `subject_entity_id`

`ProposedMutation.payload` gains one optional key on `mutation_type ==
"new_knowledge"`:

```
"subject_entity_id": "<entity id>" | null | absent
```

- Absent and `null` are identical and mean "no subject". Every payload written before this lot is therefore valid unchanged.
- The value is untrusted input, whether it came from the model or from a client. `_mutation_apply_new_knowledge` re-looks it up: it must name an `entity` row with `status = "active"` and `world_id == mut.world_id`.
- A value failing that check is a returned error string from the apply branch — the same shape as the branch's existing `"new_knowledge: payload must contain entity_id (or set target_id)"` — so the mutation stays unapplied and visible in the queue. It is never dropped, and never written as a null subject.
- `payload["subject"]` keeps its exact current meaning and its exact current role in `_mutation_match_key`. The dedup key does not change.

## Context

The measurement behind decision B2: subjects are propositions, not names
("Les véritables objectifs de La Société des Entrepreneurs"), because nothing
in either producer ever tries to name an entity — one derives a slug from
content, the other copies a requirement string. Resolver rungs alone would
fill 16% of rows and no more. So the model is asked the question directly,
and the code checks the answer: model proposes, code judges.

This brief changes a `db_write` path. It is the reason the ticket carries
`danger_class: [db_write]`.

## Scope IN

1. **`src/world_engine/analyzer_transcript.py`** — in `_build_payload_new_knowledge`, read an optional topic field from the model item and put it in the payload as `subject_entity_id`. Read it with the existing `_first_of` helper, from the keys `"subject_entity_id"`, `"about_entity_id"`, `"about"`, in that order, default `None`. Omit the key from the payload entirely when the value is falsy — never write `"subject_entity_id": null`.

2. Do **not** change what `"subject"` means in that function, and do not change the learner inference at `analyzer_transcript.py:287-293`. `_content_to_subject_slug` stays exactly as it is.

3. **`src/world_engine/day_mutations.py`** — in `_emit_new_knowledge`, resolve the requirement string through `C-02`: `resolve_subject(subject, world_id, db)`. On `matched`, add `"subject_entity_id": resolution.entity_id` to the payload. On `ambiguous` or `unmatched`, omit the key. There is no model in this path, so the rungs are the only source available here and a null is the honest state.

4. **`src/world_engine/cockpit/mutations.py`** — in `_mutation_apply_new_knowledge`, before the `write_knowledge` call:
   - read `payload.get("subject_entity_id")`;
   - when falsy, call `write_knowledge` exactly as today, with no `subject_entity_ids` argument;
   - when set, look it up: an `Entity` with that id, `status == "active"`, `world_id == mut.world_id`. World scoping goes in the `select(...).where(...)`, never as a post-fetch comparison.
   - when the lookup finds nothing, `return` the error string `f"new_knowledge: subject_entity_id {subject_entity_id!r} is not an active entity of this world"` and write nothing at all;
   - when it finds the entity, call `write_knowledge(..., subject_entity_ids=[subject_entity_id])`.

5. The validation must precede every write in that branch, including the `discoverable_detail` flip at `cockpit/mutations.py:391-397`. A refused subject leaves the detail available for re-selection, exactly as a refused proposal does today.

6. **The prompt.** The `new_knowledge` proposal prompt lives in the DB (`prompt_template` / `prompt_version`), edited from the cockpit and read through `current_prompt()`. Add to its instruction text a field asking the model, when the knowledge is about a named entity of the world, to give that entity's id in `subject_entity_id`, and to omit the field otherwise. Write it as a new `prompt_version` row through `write_prompt_version` — never an in-place edit of a live row. Add **no example values**: examples in prompt templates tint NPC vocabulary (established in TICKET-0079). Ship it as `scripts/apply_ticket_0087_subject_prompt.py`, following the `apply_ticket_NNNN_<slug>.py` convention of `apply_ticket_0078_narration_seed.py` (R-16). It is not a migration and takes no `migrate_` name.

7. **`tooling/verify/checks/subject_resolution.py`** — new G1 check, following `fact_spine.py`'s fixture idiom exactly (fresh temp-file SQLite, `WORLD_ENGINE_DATABASE_URL` set before any `world_engine` import, never touching the real database, `FAILURES` list, print FAIL lines, `sys.exit(1)`). Four assertions, every one vacuity-guarded — zero items collected is a FAIL, never a silent pass:
   - **A1 (AST, purity):** `src/world_engine/subject_resolve.py` contains no `chat(` call and no `db.add(`.
   - **A2 (AST, no re-implemented rung):** every `select(` in `subject_resolve.py` is world-constrained among its `.where(` arguments, in the shape `lore_isolation.py`'s R2 already uses for `lore_selectors.py`.
   - **A3 (behavioural, refusal):** build a fixture with two worlds; call `_mutation_apply_new_knowledge` with a `subject_entity_id` naming an active entity of the *other* world; assert it returns a non-`None` error string and that zero `fact_participant` rows were written. Then heal it with an in-world id and assert exactly one `fact_participant` row appears, with `role IS NULL`, and the return is `None`.
   - **A4 (behavioural, idempotency):** apply the same in-world `subject_entity_id` against the same fact twice; assert exactly one `fact_participant` row.

8. Place A3 and A4 in `subject_resolution.py` rather than extending `fact_spine.py`: `fact_spine.py` asserts spine invariants over any fixture, and teaching it about mutation payloads would be the exception-making a G1 gate must never require.

## Scope OUT

- **The dedup guard.** `_find_applied_duplicate_conversation_sourced` (`routes/mutations.py:294-311`), `_dup_tick_new_knowledge` (`routes/mutations.py:281-282`) and `_knowledge_leg_already_applied` (`cockpit/mutations.py:73-108`) keep matching on `entity_id` + `subject`. `subject_entity_id` never enters a dedup key. Decision A1 was rejected to keep this true.
- **The known accepted gap** documented at `cockpit/mutations.py:85-90` — the one-directional guard between `resource_change` knowledge legs and `new_knowledge`. Do not close it. `ARCHITECTURE_DECISIONS.md` records it as a deferred decision.
- **`resource_change`'s knowledge leg** (`cockpit/mutations.py:688-760`). It calls `write_knowledge` too, and it gets no `subject_entity_id` in this brief. Named deferral; reactivation is a second concrete case asking for it.
- **`knowledge_change`** (`cockpit/mutations.py:453-487`). It is `mode="level_change"` and `C-01` ignores subjects there.
- **Backfill.** No existing row is touched here.
- **The creator CRUD.** `cockpit/crud/knowledge.py` is BRIEF-0087-d.
- **The selector.** `lore_*` modules are BRIEF-0087-e.
- **An ambiguity review surface.** Rejected at intake on R-09: zero cases exist. When `resolve_subject` returns `ambiguous` in the `day_mutations` path, the key is omitted and nothing is recorded anywhere.
- **Any new mutation type**, and any change to `_MUTATION_TYPE_MAP` or `_TARGET_TABLE_MAP` (`analyzer_transcript.py:102-140`).

## Invariants to defend

- **Model proposes, code judges** — the payload value is re-looked-up against canon before it is used, world-scoped at query construction. This is the invariant this brief is most likely to threaten, because a `subject_entity_id` arriving from the model looks authoritative and is not.
- **`new_knowledge` dedup is identity-based on `entity_id` + `subject`** (`CLAUDE.md:143-145`). Adding a payload key must not shift that key. If `_mutation_match_key` turns out to hash the whole payload rather than named fields, that is a STOP.
- **Two canon-write paths for rows** (`CLAUDE.md:157-158`). `_apply_mutation` stays one of exactly two; this brief adds no third.
- **Commit before touching any canon-writing path** (`CLAUDE.md:163`). `cockpit/mutations.py` is one. Commit before the first edit.
- **No examples in prompt templates** (TICKET-0079). The added prompt field is described, never demonstrated.
- **Prompts are written as new versions**, never edited in place (`write_prompt_version` is the sole write shape).

## Decision rights

**STOP:**
- Any anchor above has moved.
- `_mutation_match_key` hashes the whole payload rather than named fields, so adding a key would change the dedup identity.
- The `new_knowledge` proposal prompt template cannot be located in `prompt_template` / `prompt_version`, or has no owning registry entry in `prompt_registry.py`.
- `prompt_coverage.py` or `prompt_lean.py` fails on the new field and the failure cannot be resolved without changing what those checks assert.
- `_mutation_apply_new_knowledge` exceeds the 80-line ceiling after the change and cannot be brought back under it by extracting a helper into the same module.

**ADAPT:**
- The model item's topic key is present but not a string: treat as absent, proceed, report.
- `Entity` is not currently imported in `cockpit/mutations.py`: add it to the existing import, proceed, report.
- `day_mutations.py` has no `world_id` in scope at the `_emit_new_knowledge` payload construction: it is a parameter of that function (`day_mutations.py:215`); use it, proceed, report.
- The new check file needs a helper already written in `fact_spine.py`: copy it rather than import across check files, proceed, report — check files are independently executable by `corpus_gate.py`.
- A docstring-coverage or module-budget count shifts: adapt, proceed, report.

**REPORT-ONLY:**
- The observed rate at which the model actually fills `subject_entity_id` during any manual test.
- Any `resource_change` knowledge leg noticed while working, and what a subject would have been for it.
- Any prompt template whose text already mentions a subject entity.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Commit exists on the branch before the first edit to `cockpit/mutations.py`.
- [ ] A `new_knowledge` payload with no `subject_entity_id` applies exactly as before: one `knowledge` row, one free-standing `fact`, zero `fact_participant`.
- [ ] A payload whose `subject_entity_id` names an active entity of the mutation's world applies and produces exactly one `fact_participant` row, with `role IS NULL`.
- [ ] A payload whose `subject_entity_id` names an entity of a *different* world returns an error string, applies nothing, writes zero `fact_participant`, and leaves the mutation un-applied in the queue.
- [ ] A payload whose `subject_entity_id` names an entity with `status != "active"` is refused the same way.
- [ ] A payload whose `subject_entity_id` names a non-existent id is refused the same way.
- [ ] Applying a `new_knowledge` twice with the same `subject_entity_id` against the same fact yields one `fact_participant` row, raises no `IntegrityError`, and does not abort the `_apply_mutation` SAVEPOINT.
- [ ] `_find_applied_duplicate_conversation_sourced` returns the same verdict for two payloads differing only in `subject_entity_id` as it did before this brief — the dedup key is unchanged.
- [ ] A new `prompt_version` row exists for the `new_knowledge` proposal template; the previous version row is intact and unedited.
- [ ] The new prompt text contains no example entity name and no example id.
- [ ] `python tooling/run.py` — `subject_resolution.py` PASSES, and its FAIL path was demonstrated by breaking one assertion on purpose and observing it named in the output before healing it.
- [ ] `python tooling/run.py` — `fact_spine.py`, `single_canon_write.py`, `prompt_version.py`, `prompt_model_write.py`, `prompt_lean.py`, `prompt_coverage.py`, `corpus_gate.py`, `module_budget.py`, `function_length.py` all PASS.
- [ ] `/review-step` and `/close-step` run; engine code is touched.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: one entry for B2 — the `new_knowledge` payload carries an optional untrusted `subject_entity_id`, re-validated at apply against active entities of the mutation's world. Record the rejected alternative (resolver rungs only, B1) with its measured yield (16% of rows, R-06) and the rejected ambiguity journal with its reactivation condition (a measured ambiguity count above zero, R-09). Record the named deferral of `resource_change`'s knowledge leg.
- `CLAUDE.md`: one line stating that `subject_entity_id` is untrusted payload input, validated at apply, and that it is never part of a dedup key.
- No schema changelog entry. `ProposedMutation.payload` is a JSON column; a new key is not DDL.
