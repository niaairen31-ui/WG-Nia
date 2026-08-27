# BRIEF — Step "Extraction and concordance"

## Context

BRIEF-0075-b gave a declaration a plan and a budget. The plan is still written
against the player's raw words: "find whoever stole the guild seal" names a
faction and an object, and implies a fence, a district and a contact — none of
which are resolved to canon.

This step resolves them. Three extraction passes read the declaration, a
Python concordance pass matches what they found against the registry, and
anything unmatched becomes a PARKED GERM rather than a new entity.

Decision **C1** is the whole shape: **the resolver never authors.** On a match
it uses the canon id. Failing that, the day names a FUNCTION WITHOUT IDENTITY
("a flower seller set up near the east gate") and emits an `entity_creation`
germ carrying the hint. The NPC becomes canon when Nia realises it in the
Creation tab, and at that moment it was already there — narratively free.

Per AMENDMENT 1, this step runs BEFORE plan emission at runtime, and is
authored after it because it depends on -b's schema.

## Mini-RECON

Measured 2026-08-24 at schema v1.93 unless marked as delegated. Every anchor
is a STOP condition.

- **[M1]** `_approve_entity_creation_shortcircuit` —
  `src/world_engine/cockpit/routes/mutations.py`. Approving an
  `entity_creation` authors NOTHING; it parks the germ for human realization
  in the Creation tab. Verbatim comment in the code: *"I2 forbids any
  synchronous authoring call here."* This brief must leave that behaviour
  byte-identical.
- **[M2]** `ProposedMutation` — `src/world_engine/models/pipeline.py`.
  `source_type` is `pass_play | conversation | world_tick`; `pass_play_id` is
  a nullable FK to `pass_play.id`, and exactly one source anchor is set.
  `payload` is JSON NOT NULL. `status` defaults to `'proposed'`.
  `proposed_by` defaults to `'local_ai'`. Index
  `idx_mutation_passplay` on `pass_play_id` already exists.
- **[M3]** `who_is_at(location_id, phase, db, *, is_present)` and
  `unresolved_npcs(...)` — `src/world_engine/schedule_reads.py`. The only
  sanctioned positional reads. `where_is`'s dispatch is sealed and
  bijection-checked by `tooling/verify/checks/npc_schedule.py`.
- **[M4]** `npc_schedule.standing_goal_id` — nullable FK to `npc_goal.id`,
  landed by TICKET-0074. An `npc_goal` row with `kind='standing'` is a
  background occupation (TICKET-0073, schema v1.91), CHECK-bound to
  `horizon='long'`. **This is the occupation index**: "who is a flower seller"
  is answered by joining a schedule row to its standing goal, not by reading
  free text.
- **[M5]** `llm_parse` — `src/world_engine/llm_parse.py`, `LlmParseError`.
  Sole JSON-extraction chokepoint; domain validation stays with the caller.
- **[M6]** `PROMPT_REGISTRY` / `PromptSpec` —
  `src/world_engine/prompt_registry.py`. Fields per BRIEF-0075-b's M7.
- **[M7]** `routes/day.py` — `_crud._world_id(db)`,
  `_resolve_player_character`, `_day_dict`, and `POST /api/day/{id}/plan`
  from BRIEF-0075-b.
- **[M8]** `day_plan.py` from BRIEF-0075-b — `emit_plan`, `budget_cut`,
  `REQUIREMENT_TYPES`, `_EVALUATORS`, `DAY_BUDGET_SLOTS`.
- **[DELEGATED D1]** The entity/faction/location lookup surface. Locate the
  existing name and type based entity reads (`cockpit/crud/entities.py`,
  `crud/_shared.py`, `crud/locations.py`) and the faction reads. Report the
  exact functions used for matching before writing the concordance pass. Do
  NOT author a new query where one exists.
- **[DELEGATED D2]** The `entity_creation` payload shape. Read what the
  Creation tab actually consumes when realising a parked germ, and match it
  exactly. If the shape cannot be determined from a live example, STOP.

**STOP conditions.**

- S1. `_approve_entity_creation_shortcircuit` no longer parks, or authors
  anything synchronously.
- S2. The `entity_creation` payload shape cannot be determined (D2), or the
  Creation tab reads a field this brief would not populate.
- S3. Any existing writer creates an `Entity` row from a resolution or tick
  path. This brief's premise is that no such path exists.
- S4. A prompt usage key collides with `day_extract_place`,
  `day_extract_person` or `day_extract_faction`.
- S5. Matching an NPC by occupation cannot be expressed through M4's
  schedule-to-standing-goal join — for example if standing goals turn out not
  to be reachable from a schedule row. Report what IS reachable and stop.

## Scope IN

### 1. Three extraction passes — `src/world_engine/day_extract.py` (new)

Three SEPARATE prompts and three separate calls, deliberately. A single
combined pass mixes the categories; keeping them apart is the same discipline
as one prompt per surface elsewhere in the engine.

- `PROMPT_REGISTRY` entries `day_extract_place`, `day_extract_person`,
  `day_extract_faction`. All `surface="play"`, `world_scoped=True`,
  `dry_run_capable=True`, `default_model=_game_model`, with `call_sites`
  naming their function in this module.
- `extract_places(declaration, db) -> list[Mention]`,
  `extract_persons(...)`, `extract_factions(...)`. Each returns mentions with
  `surface_form` (the words the player used), `kind` (`named` or `inferred`)
  and, for inferred mentions, a `role_hint` — the FUNCTION the player needs
  ("a fence", "a flower seller", "someone who knows the guild's ledgers").
- Every output parsed through `llm_parse` (M5), then domain-validated here:
  `surface_form` non-empty, `kind` in the allowed pair, `role_hint` present
  when and only when `kind == "inferred"`.
- Bound: `MAX_MENTIONS_PER_PASS = 8`, a named module constant. Over the bound,
  truncate and report the count.
- **Positive-form prompts only** — the gameplay model is abliterated and does
  not honour negative constraints. Ask for what to emit, never for what to
  avoid. Anything that can only be phrased as a prohibition is enforced in the
  validator instead. Write all three prompt texts out in full in the execution
  notes.
- Each pass sees the declaration and a compact world frame. **It never sees
  the registry** — matching is item 2's job, in Python, against real rows.
  Handing a model the registry invites it to invent a plausible id.

### 2. Concordance — Python, `src/world_engine/day_concordance.py` (new)

No model call in this module. This is the "another AI with the full registry"
role from the design conversation, resolved to code, which is strictly better:
a lookup cannot hallucinate an id.

- `concord(mentions, character, db) -> ConcordanceResult`, returning matched
  mentions (mention plus canon `entity_id`) and unmatched ones.
- Matching order, tried in sequence and stopping at the first hit:
  1. **Named, exact.** `surface_form` against entity names in the active
     world, case-folded (D1's reads).
  2. **Named, alias.** Only if an alias or cover-role surface already exists;
     if it does not, skip this rung and report that it was skipped. Do not
     build one.
  3. **Inferred, by occupation.** `role_hint` against standing goals reached
     through `npc_schedule.standing_goal_id` (M4). This is the flower-seller
     path.
  4. **Inferred, by presence.** For a place-scoped hint, `who_is_at` (M3) on
     the candidate location across the four phases.
- Ambiguity is not resolved by picking. Two or more equally good candidates
  yields an `ambiguous` outcome carrying every candidate id, and the mention
  is treated as unmatched for germ purposes but reported distinctly, so Nia
  can see the engine hesitated rather than failed.
- Scoping at query construction: every lookup filters by the active world in
  the query itself, never after the fetch.
- The module writes NOTHING. It has no `db.add`, no `commit`.

### 3. Germ emission — role, not identity

- `emit_germs(unmatched, pass_play, db) -> list[ProposedMutation]` in
  `day_concordance.py`. One `ProposedMutation` per unmatched mention:
  `source_type='pass_play'`, `pass_play_id` set, `mutation_type='entity_creation'`,
  `status='proposed'`, `proposed_by='local_ai'`.
- `payload` follows D2's measured shape and carries, at minimum, the
  `role_hint`, the `surface_form`, the mention's kind, and the anchoring
  context the concordance pass had (candidate location id when it had one).
  `rationale` states which matching rungs were tried and missed — that string
  is what makes a germ reviewable rather than mysterious.
- **Nothing is authored.** No `Entity` row, no `Character` row, no
  `npc_schedule` row. `_approve_entity_creation_shortcircuit` (M1) stays
  untouched, and approving one of these germs must still park it.
- **Places are out.** Germs are emitted for PERSONS only. An unmatched place
  is reported and the plan works around it. Creating a location drags in the
  location tree, doors, geometry and four fail-closed checks; the ticket
  defers it explicitly.
- Unmatched factions are reported, never germinated: a faction the player
  invents is a misunderstanding to surface, not an entity to create.

### 4. Wiring into the day

- `POST /api/day/{batch_id}/plan` (from -b) gains a preceding stage: extract,
  concord, THEN emit the plan. The plan emission receives the declaration
  plus the concordance result, so a matched mention reaches it as a canon id
  and an unmatched one reaches it as a role.
- The route's response gains a `concordance` block: matched mentions with
  their resolved display names, ambiguous ones with their candidate counts,
  unmatched ones with their role hints and the germ ids emitted. Entity ids
  for MATCHED mentions may appear; germ ids may appear; **no agenda id and no
  step id**, per the ticket's Scope OUT.
- Germs are committed in the same transaction as the plan. A concordance
  failure means no plan is written either — all-or-nothing.
- Extraction and concordance failures report and stop. Neither falls back to
  "resolve without it".

### 5. Verify — `tooling/verify/checks/day_concordance.py` (new)

Stdlib `ast` and text only. Fail-closed, vacuity-guarded, each failure naming
which collection came back empty.

- R1. `day_concordance.py` contains no `db.add(`, no `.commit(`, and no
  `chat(` — it neither writes nor calls a model.
- R2. `day_extract.py` contains no `select(` against `Entity`, `Faction` or
  any location model: the extraction passes never see the registry.
- R3. Every germ constructed in `emit_germs` sets `source_type='pass_play'`,
  `mutation_type='entity_creation'` and `status='proposed'`, and none sets
  `status` to anything else.
- R4. No `Entity(`, `Character(` or `NpcSchedule(` constructor appears
  anywhere in `day_extract.py`, `day_concordance.py` or `day_plan.py`.
- R5. `_approve_entity_creation_shortcircuit` still contains its parking
  branch and no synchronous authoring call — assert the I2 comment and the
  parking behaviour are both still present.
- R6. The three extraction usage keys are in `PROMPT_REGISTRY` with
  `call_sites` naming this module's functions, and the matching rungs in
  `concord` are a named, ordered sequence rather than inline branches, so the
  order is readable by a check.
- R7. `MAX_MENTIONS_PER_PASS` is a named module constant, read by all three
  passes.
- R8. Vacuity guard on every collection above.

## Scope OUT

- **Location germs.** Persons only, v1. Named deferral; reactivation is the
  location-symmetry ticket, which must carry the tree, doors, geometry and the
  four existing fail-closed checks.
- **Faction germs.** Reported, never created.
- **Any authoring.** Realising a germ stays a human act in the Creation tab.
  Do not add a "realise now" affordance anywhere.
- **Alias infrastructure.** If rung 2 has nothing to match against, skip it
  and report; do not build an alias table.
- **Step resolution, dice, narration** — BRIEF-0075-d.
- **Mutation emission beyond germs** — BRIEF-0075-e. No `knowledge_change`,
  no `relation_change`, no `resource_change` here.
- **Reconciliation** — BRIEF-0075-f.
- **`schedule_reads.py`.** Consumed through its public functions only; no new
  precedence term, no new source, no edit to `where_is`'s dispatch.
- **`world.current_phase`.** Not read (P2). Rung 4 sweeps all four phases
  rather than asking what time it is.
- **Prompt-injection filtering.** The declaration still reaches the extraction
  prompts as the player wrote it. The `flagged` status stays unwritten.

## Invariants to defend

- **The resolver never authors** (C1 / I2). R4 and R5 are the tripwires, and
  R5 protects a behaviour this brief does not own.
- **Model proposes, code judges.** Matching is Python against real rows. A
  model that sees the registry and returns an id is the failure mode; R2 is
  the tripwire.
- **Exclusion is structural.** World scoping happens in the query, not after.
- **Secrets stay filtered.** The world frame handed to the extraction passes
  is built from an existing context builder, not assembled ad hoc here — an
  ad-hoc frame is how a secret leaks into a prompt.
- **No structure without a reader.** Every field on the germ payload is read
  by the Creation tab's realisation flow (D2), or it does not go in.

## Done means

- [ ] A declaration naming a real NPC by name resolves to that entity's id,
      and no germ is emitted.
- [ ] A declaration needing "a flower seller", with a canon NPC whose standing
      goal is flower-selling and a schedule row pointing at it, resolves
      through rung 3 to that NPC. No germ.
- [ ] The same declaration with no such NPC emits exactly one
      `entity_creation` germ whose payload carries the role hint, and the
      response reports the mention as unmatched.
- [ ] That germ appears in the review queue and, on approval, is PARKED — no
      `Entity` row is created. Verified by row count before and after.
- [ ] Realising the germ in the Creation tab, then re-running the day, matches
      through rung 1 or 3 and emits no second germ.
- [ ] Two equally good candidates yield `ambiguous` with both ids listed, and
      no germ.
- [ ] An unmatched PLACE emits no germ and is reported.
- [ ] An extraction parse failure stops the day: no plan row, no germ row,
      nothing committed.
- [ ] The response carries no `agenda_id` and no `step_id`.
- [ ] `python tooling/verify/checks/day_concordance.py` green, each of R1–R8
      observed FAILING under a deliberate local mutation before revert.
- [ ] `npc_schedule.py`, `day_plan.py`, `single_canon_write.py`,
      `pipeline_wiring.py`, `corpus_gate.py` all green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a subsection on C1 — the
  resolver names a role, never a person; the four matching rungs and their
  order; why concordance is Python and extraction is a model; and the record
  that `npc_schedule.standing_goal_id` is the occupation index.
- `tooling/standards/DECISIONS_INDEX.md`: C1.
- No schema change, so no changelog entry and no version bump.
- Prompt seeding is data, not doc: record the three prompt texts verbatim in
  the execution notes.
