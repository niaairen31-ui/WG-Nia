<!-- slug: selector-registry-and-plan-execution -->
# BRIEF — Step "Selector registry and plan execution"

## Context

TICKET-0085's architecture is a declarative plan: the model names selectors from
a whitelist, and code validates, resolves, executes and classifies. This step
builds the whole deterministic half — whitelist, two selectors, plan validation,
bounded execution, and the three empty verdicts — with no model anywhere in it.
BRIEF-0085-a delivered the name resolver this step calls.

## RECON required before execution

Report-only. Do not act on any finding; report and stop if a stop condition
fires.

- **R-a** Confirm `lore_resolve.resolve_named` exists with signature
  `(surface_form, category, world_id, db) -> NamedResolution` and that
  `NamedResolution.verdict` is one of `matched | ambiguous | unmatched`.
  *Stop condition:* the signature differs — BRIEF-0085-a's Scope IN item 5 was
  not executed as written, and this brief's Scope IN is built on it.
- **R-b** Measure, for a `character`-type entity in a live world, every canon
  table reachable from `entity.id` that a "who is this person" answer would
  draw on: `character`, `relation` (both directions), `knowledge`,
  `faction_membership`, `npc_goal`, `entity_trait`, `discoverable_detail`,
  `event_entity`, `item`, `skill`, `npc_price`, `ledger`. For each, record the
  FK column and whether the table carries `world_id` directly.
  *Report* the list. Scope IN item 4 fixes which of them enter the dossier; the
  RECON exists to catch a table the brief did not name.
- **R-c** Confirm `knowledge` has no `world_id` column and that the only path
  from a knowledge row to a world is `knowledge.entity_id -> entity.world_id`.
  *Stop condition:* a `world_id` column exists — the scoping rule in Scope IN
  item 6 would then be written wrong.
- **R-d** List every column on `faction` and `faction_membership` carrying a
  `DORMANT` comment in the model source. *Report* them; Scope IN item 5
  excludes them and the list must match.
- **R-e** Confirm `discoverable_detail` is excluded from every existing
  assembler in `context.py`, and record the mechanism used.
  *Report* the mechanism; this step must use the same one, not a new one.
- **R-f** Record the registration idiom used by `tooling/verify/run.py` for
  check modules, and whether `tooling/verify/checks/lore_resolve.py` is
  registered there. *Stop condition:* it is not registered — BRIEF-0085-a is
  incomplete and this step's checks would silently never run.

## Scope IN

1. **New module `src/world_engine/lore_selectors.py`.** Docstring states,
   verbatim:

   > The model names a selector; it never writes a query. Every selector is a
   > code-owned function with a declared row cap, reached only through
   > `SELECTOR_LOOKUPS`. A plan naming anything outside `SELECTORS` is rejected
   > before a single row is read. Coverage grows by adding a selector, never by
   > adding a question type.

2. **`SELECTORS: tuple[str, ...] = ("entity_dossier", "world_factions")`** and
   `_SELECTOR_LOOKUPS: dict[str, SelectorSpec]` in bijection with it. Two
   selectors, no more. `SelectorSpec` is a frozen dataclass
   `(fn: Callable[..., list[dict]], arity: int, row_cap: int, arg_kinds:
   tuple[str, ...])` where `arg_kinds` entries are `"entity_id"` or
   `"world_id"`.

3. **`world_factions(world_id, db) -> list[dict]`**, `row_cap = 200`. Returns
   one dict per active faction in the world: `entity.id`, `entity.name`,
   `entity.description`, `faction.faction_type`, `faction.philosophy`,
   `faction.internal_structure`, `faction.internal_tensions`,
   `faction.magic_knowledge_level`. Joined `entity` -> `faction` on
   `faction.id == entity.id`, `entity.world_id == world_id`,
   `entity.status == "active"`.

4. **`entity_dossier(entity_id, world_id, db) -> list[dict]`**, `row_cap = 400`
   total across sections. Returns a flat list of row dicts, each carrying a
   `"section"` key so the renderer and the trace can group them. Five
   sections, and nothing beyond them in this step:
   - `identity` — the `entity` row plus, when the entity is a character, the
     `character` row's non-secret descriptive columns.
   - `relations` — every `relation` row where the entity is `entity_a_id` or
     `entity_b_id`, with `type`, `direction`, `intensity`, `notes`, and the
     other party's id and name. Each row records which side the subject is on.
   - `knowledge` — every `knowledge` row for the entity, carrying `subject`,
     `level`, `content`, `source`, `is_incorrect`, `is_secret`. `is_incorrect`
     is carried verbatim and is never used to filter.
   - `memberships` — faction memberships reached through
     `context.read_public_memberships`, never by a fresh `select(` on
     `faction_membership`.
   - `goals` — `npc_goal` rows for the entity: `description`, `status`,
     `horizon`, `kind`. (Corrected at execution, RECON R-b: `npc_goal` has no
     `priority` column — confirmed against `world-engine-schema.md`, never
     added in any migration. `horizon`/`kind` are the columns that actually
     exist and are descriptively relevant; the schema is authoritative over
     this brief's field list, per CLAUDE.md.)
   - ~~`traits` — `entity_trait` rows.~~ **Dropped at execution (RECON R-b).**
     `entity_trait` is keyed by `entity_type_id`, not `entity_id` — it is a
     runtime-custom-entity-type projection (TICKET-0045/BRIEF-0045-a: "which
     entity_type has checked which trait"), never an entity-instance row. No
     `entity_type` row exists for built-in types (`character`, `location`,
     `faction`) — only for constructor-created `ext_*` types — so this
     section would be structurally empty for every entity this ticket's
     selectors can reach, and even where it could resolve it would present
     type-level schema configuration as if it were entity-specific canon.
     REPORT-ONLY per RECON discipline, not re-keyed and not substituted with
     an `entity.type -> entity_type.slug` join — see
     ARCHITECTURE_DECISIONS.md for the full record.
   If the RECON (R-b) surfaces a table that clearly belongs and is not listed
   here, REPORT ONLY — do not add a section.

5. **Dormant columns are excluded by name.** No column the RECON's R-d step
   reports as DORMANT appears in any selector's output. A dormant column
   presented in a dossier reads as canon to the creator and is not.

6. **World scoping at construction.** Every `select(` in `lore_selectors.py`
   carries the world constraint in its `.where(`. For `knowledge`, which has no
   `world_id` (RECON R-c), the constraint is a join to `entity` with
   `Entity.world_id == world_id` — never a post-fetch filter on the returned
   rows.

7. **New module `src/world_engine/lore_query.py`** holding plan validation,
   execution and verdict classification.
   - `LorePlan` — frozen dataclass `(mentions: tuple[PlanMention, ...],
     calls: tuple[PlanCall, ...])`; `PlanMention` is `(ref: str, surface_form:
     str, category: str)`; `PlanCall` is `(selector: str, args: tuple[str, ...])`
     where each arg is either a mention `ref` or the literal `"$world"`.
   - `validate_plan(plan, db) -> PlanValidation` — rejects, BEFORE any selector
     runs: a selector name not in `SELECTORS`; an arg count not matching the
     spec's `arity`; an arg referencing an unknown mention ref; an `arg_kinds`
     mismatch. Returns the rejection reason naming the offending selector.
   - `execute_plan(plan, world_id, db) -> LoreResult` — resolves every mention
     through `lore_resolve.resolve_named`, then dispatches each call through
     `_SELECTOR_LOOKUPS`, truncating at each spec's `row_cap` and recording the
     truncation in the trace rather than dropping it silently.

8. **The verdicts, as a closed set.** `LoreResult.verdict` is one of:
   - `"answered"` — at least one row returned.
   - `"ambiguous_mention"` — one or more mentions resolved `ambiguous`. Carries
     every ambiguous mention's ref and `candidate_ids`. No selector runs in this
     case; a question whose referent is unsettled is not executed.
   - `"unknown_entity"` — one or more mentions resolved `unmatched`, none
     ambiguous. Carries the unmatched surface forms.
   - `"silent_canon"` — every mention resolved, every call ran, zero rows.
   - `"unsupported_selector"` — validation rejected the plan.
   These are the ticket's three empty messages plus the ambiguity round-trip.
   There is no sixth verdict and no `"error"` catch-all.

9. **Trace.** `LoreResult.trace` is a list of dicts: one entry per resolved
   mention (`surface_form`, `verdict`, `rung`, `entity_id`), one per executed
   call (`selector`, `args`, `row_count`, `truncated`).

10. **New G1 check `tooling/verify/checks/lore_selectors.py`**, stdlib `ast` and
    text only:
    - R1 (bijection): `SELECTORS` and `_SELECTOR_LOOKUPS` are in bijection.
    - R2 (no dispatch outside the table): every call to a selector function
      inside `lore_query.py` goes through `_SELECTOR_LOOKUPS[...]`; no selector
      function is named directly there.
    - R3 (caps declared): every `SelectorSpec` construction sets a non-zero
      integer `row_cap`, and `execute_plan` references `row_cap`.
    - R4 (validation precedes execution): in `execute_plan`'s AST, no call to
      `_SELECTOR_LOOKUPS` appears on a path that does not first return on a
      failed validation.
    - R5 (closed verdicts): the set of string literals assigned to `verdict` in
      `lore_query.py` equals the five in Scope IN item 8.

11. **New G1 check `tooling/verify/checks/lore_isolation.py`**, stdlib `ast` and
    text only:
    - R1: `lore_selectors.py` and `lore_query.py` contain no `chat(`, no
      `db.add(`, no `.commit(`.
    - R2: every `select(` in `lore_selectors.py` has a world constraint among
      its `.where(` arguments, or joins `Entity` with one.
    - R3: no `discoverable_detail` identifier appears in `lore_selectors.py`.

12. **Register both checks** in `tooling/verify/run.py`.

## Scope OUT

- **No model, no prompt, no `prompt_registry` entry, no `llm_parse` call.** The
  plan arrives as a Python object built by hand or by a test script in this
  step. BRIEF-0085-c builds it from a question.
- **No prose.** `execute_plan` returns rows and a verdict. Rendering is
  BRIEF-0085-d. Do not add a `__str__`, a summary line, or a "human readable"
  field.
- **No route and no frontend.** BRIEF-0085-c and -e.
- **No third selector.** `location_contents`, `faction_roster`,
  `region_locations`, `who_knows_about` are each their own later ticket, and
  `who_knows_about` additionally depends on a schema change this ticket does not
  make. Adding one because it is "two lines" defeats the point of the whitelist
  being small enough to audit.
- **No `knowledge.subject` FK, no migration, no schema version bump.**
- **No secret filtering policy.** The creator is omniscient in this ticket, so
  `is_secret` rows are carried. Do NOT add a viewpoint parameter, a filter flag,
  or a "for later" hook — the day a non-creator reader exists, that is a design
  conversation, not a parameter someone guessed at.
- **No caching, no memoization, no query optimization.**
- **No widening of `read_public_memberships`.** Item 4 calls it as it is.
- **No new `ProposedMutation`, no write of any kind.**

## Invariants to defend

- **Secrets are structurally excluded from every assembled context — never
  instructionally.** This is the invariant this step is most likely to damage.
  The dossier deliberately carries `is_secret` knowledge because the reader is
  the creator; the danger is that the same assembler is later reused for an NPC
  prompt. Guard: `lore_selectors.py` is named in no `context.py` assembler, and
  check R3 keeps `discoverable_detail` out entirely, because that one is
  structurally excluded from *every* assembler without exception.
- **UI-visible data never lives in JSON; relational only.** The dossier returns
  dicts built from columns. It must not read `entity.metadata` JSON keys or any
  other JSON blob as a source of displayed fields.
- **Creator control is structural.** Read-only step; check R1 is the guard.
- **All templated model calls resolve through `effective_model`.** No model call
  exists here; if one appears, the step is wrong.

## Done means

- [ ] `tooling/verify/checks/lore_selectors.py` exits 0
- [ ] `tooling/verify/checks/lore_isolation.py` exits 0
- [ ] `tooling/verify/checks/corpus_gate.py`, `import_cycle.py`,
      `function_length.py`, `no_print_in_src.py` exit 0
- [ ] A script run against a live DB, with a hand-built plan calling
      `entity_dossier` on an existing NPC, prints rows in the five sections
      with verdict `answered`
- [ ] The same script with a plan calling `world_factions` prints the world's
      factions with verdict `answered`, no mention resolved
- [ ] A plan naming `who_knows_about` returns verdict `unsupported_selector`
      naming that selector, and the DB log shows no selector query ran
- [ ] A plan whose mention is a name absent from the world returns verdict
      `unknown_entity` carrying that surface form
- [ ] A plan on an entity with no knowledge, no relations, no memberships and
      no goals returns verdict `silent_canon`, with its `identity` row still
      present in `rows` (corrected at execution, RECON: `identity` is
      unconditional once a mention resolves — `SelectorSpec.context_sections`
      excludes it from the answered/silent_canon count without suppressing
      it from the payload; see ARCHITECTURE_DECISIONS.md)
- [ ] A plan whose mention matches two same-named entities returns verdict
      `ambiguous_mention` with both ids, and no selector query ran
- [ ] `trace` lists one entry per mention and one per executed call, with
      `row_count`
- [ ] `/review-step` then `/close-step` run clean

## Docs to update

No schema change, no changelog entry. Add an
`tooling/standards/ARCHITECTURE_DECISIONS.md` section for the chantier stating
the whitelist rule in one line — *the model names a selector, never a query;
coverage grows by adding selectors* — and recording that the creator-omniscient
scope is a deliberate current state, not an oversight. CLAUDE.md gets one new
invariant only once BRIEF-0085-d closes and the full path is live; not here.
