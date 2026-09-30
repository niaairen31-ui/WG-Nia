# LOT — TICKET-0098 "Lore writing path — prose to confirmed facts"

## Objective and cut

The creator writes lore in French prose in the Lore shell. The tool asks at
most one round of clarification questions, drafts a structured proposal
(entities, facts, who knows them, memberships, possessions), lets her correct
every part of it from lists, and writes it in one transaction, keeping the
text and everything it produced (B2 + M1). Every write method of the cockpit
is first closed to non-local origins (I1), because this lot adds a route that
turns free prose into canon.

The lot stops before injecting lore into play (A2, the next ticket, with N6a
still behind it), before bulk undo of a story (M2), and before social
relations, events and world laws from prose (R2).

## Briefs in this lot

- **A — origin guard** (no schema change): `cockpit/origin_guard.py`, one
  middleware for every POST/PUT/PATCH/DELETE; five checks post from a local
  base URL; `origin_guard.py` O1-O4; `lore_write.py` created with its census
  (L0). Closes TICKET-0097 first, in its own commit.
- **B — the source record** (schema v2.11): `lore_entry`, `lore_entry_row`,
  `migrate_v2_11_lore_entry.py`, the world cascade. `lore_write.py` W1-W2.
- **C — apply a proposal** (no schema change): `writes/facets.py::add_lore_fact`,
  `writes/lore_entries.py`, `lore_write_apply.py` (C-02, C-03, C-04).
  `lore_write.py` C1-C2.
- **D — draft a proposal** (no schema change): `prompt_load.py` (N1),
  `lore_write_draft.py` (C-05), two prompts in the seed, their registry
  entries, `apply_ticket_0098_lore_write_prompts.py`; `lore_isolation.py` R15
  retargeted and R17's panel list extended; `name_index.py` R5 allow-list.
  `lore_write.py` D1-D2.
- **E — routes** (no schema change): `cockpit/routes/lore_write.py`,
  `lore_write_read.py` (C-06); the CLAUDE.md invariant. `lore_write.py` E1-E2.
- **F — the Écrire tab** (no schema change): `WritePanel.svelte`,
  `writePanel.svelte.js`, the tab in `Lore.svelte`, the rebuilt `static/`.
  `lore_write.py` F1.

## Dependency graph

Strictly sequential, A → B → C → D → E → F.

- **A first: an order from a locked decision (I1), not a dependency.** The
  guard must exist before the writing route (E) ships; nothing in B-D needs
  it. An executor who finds B-D independent of A is not finding a defect.
  A also creates `lore_write.py` because every Machine arrow of the ticket
  must resolve from `brief` status on (`pipeline_state.py`).
- C writes `lore_entry` rows (B's tables, C-04).
- D's draft is validated by C's `validate` (D1e) and D extends
  `lore_isolation.py`'s panel list with C's `lore_write_apply.py`.
- E wires C (`apply_proposal`) and D (`draft_*`) and relies on A's guard
  (E1d).
- F calls E's routes (C-06).
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/lore_write.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`.

## RECON

Opened on `main` at `3e64554` (merge of PR #128, `ticket/0097`; tree equal
to the 0097 prototype). Then prototyped on a copy (branch `proto/0098`):
every brief's commit ran the full corpus green (128/128 from A on, 126/126 on
`main`), and the six diffs replayed in order on a clean worktree reproduce
the prototype byte for byte (generated files regenerated, not diffed).
Findings tagged [M] were measured, [I] inferred from code read in full.

### R-01 — the cockpit's exposure [M]
Opened: `src/world_engine/cockpit/app.py:28-34` (Security docstring),
`:118` (`app = FastAPI(...)`); `scripts/cockpit.py:31-32` (`HOST =
"127.0.0.1"`, `PORT = 8000`); `.claude/launch.json:7-8` (port 8001).
Finding: loopback binding, no authentication, no middleware of any kind
(enumeration E2, gate (c)). The cockpit runs on 8000 and 8001.
Consequence: I1 is a new module with nothing to reuse; its rule is
hostname-only, never port.

### R-02 — checks that post through `TestClient` [M]
Opened: the five files of enumeration E1 (gate (c)).
Finding: `client = TestClient(app)` at `spatial_door_travel.py:164`,
`scene_join_target.py:190`, `name_resolution.py:446`, `choice_review.py:561`,
`prompt_model_write.py:171`; each file then posts (counts in E1). Starlette's
default base URL sends `Host: testserver`.
Consequence: A passes `base_url="http://127.0.0.1"` in those five lines;
the guard learns no exception. `origin_guard.py` O4 keeps it that way.

### R-03 — schema version plumbing [M]
Opened: `src/world_engine/schema_version.py:15` (`"v2.10"`),
`world-engine-schema.md:3`, `world-engine-schema-changelog.md` (newest entry
first), `scripts/migrate_v2_07_day_mention_choice.py` (whole file: env
guard, per-object idempotence, post-checks, `schema_meta` convergence).
Finding: the constant, the doc header and the newest changelog entry move
together (`schema_version_agreement.py`).
Consequence: B bumps all three to v2.11 and copies the v2.07 script's
structure; it adds a refusal below v2.10.

### R-04 — the world cascade [M]
Opened: `src/world_engine/writes/worlds.py:39-78` (the two table lists);
`tooling/verify/checks/world_cascade.py:1-35` (W1-W6), `:60-110` (`_FIXTURE`).
Finding: every world-reaching table must be named in
`_DIRECT_WORLD_SCOPED_DELETES` or as a child in `_SUBQUERY_SCOPED_DELETES`,
and once in `_FIXTURE` (W1, W3).
Consequence: B adds `lore_entry` (direct) and `("lore_entry_row",
"entry_id", "lore_entry")` (subquery), and two fixture rows.

### R-05 — where non-canon tables live [M]
Opened: `src/world_engine/models/pipeline.py:1-15` (module docstring),
`:200-315`; `tooling/verify/canon_write_policy.txt` `[CANON_TABLES]`.
Finding: `pipeline.py` holds the non-canon record tables (`day_mention_*`,
`skill_resolution`); none is in `[CANON_TABLES]`. `json_ui_boundary.py`
forbids UI-visible data in JSON.
Consequence: `LoreEntry` / `LoreEntryRow` go in `pipeline.py`, before
`skill_resolution`; questions and answers are plain TEXT, not JSON.

### R-06 — the entity-fact writer [M]
Opened: `src/world_engine/writes/facets.py:1-147` (docstring,
`SCOPE_TYPES` at 44, `_check_scope` 73, `_bloc_exists` 83, `add_entity_fact`
93-146), `:266-300`; `tooling/verify/checks/fact_facets.py:1-40` (R2, R3).
Finding: `add_entity_fact` writes one DESCRIPTIVE fact about ONE entity
with one scope; it tokenizes (`names_only` for an appellation, owner
excluded) and records unresolved names. R3: a `create_fact(` whose facet is
descriptive or non-literal appears only in `writes/facets.py`.
Consequence: a lore fact (several participants, `information`, zero
participants, several defaults) needs a new function IN `writes/facets.py`
(C-03), reusing `_check_scope`, `_bloc_exists`, `tokenize`,
`record_unresolved`.

### R-07 — fact rows [M]
Opened: `src/world_engine/writes/facts.py:50-215`.
Finding: `create_fact` validates the facet (`_check_facet`), refuses NULL,
unknown, and typed-on-free; `attach_participants` refuses a typed fact and
does not read before writing; `create_fact_default` writes with no
duplicate guard; `update_fact_content` appends history. None commits.
Consequence: C reads existing participants and defaults before writing
(`idx_fact_participant_unique` would abort the transaction).

### R-08 — knowledge rows [M]
Opened: `src/world_engine/writes/knowledge.py:65-74` (levels, ladder),
`:180-260` (`_build_knowledge_update`, `write_knowledge`);
`src/world_engine/fact_refs.py:57-76` (`find_held`);
`models/canon_knowledge.py:198-212` (`idx_knowledge_entity_fact` UNIQUE).
Finding: `write_knowledge` accepts a `fact_id` alone for a new row; an
unknown `level` falls back SILENTLY to `rumor`; it adds the row itself.
Consequence: C validates `level` against `KNOWLEDGE_LEVEL_LADDER` before
writing, and calls `find_held` first.

### R-09 — memberships [M]
Opened: `src/world_engine/writes/factions.py:61-120`;
`src/world_engine/models/canon_faction.py:95-110`.
Finding: `write_membership(mode="open")` adds the row itself (`:108`); the
model declares `idx_membership_unique_active` on `(entity_id, faction_id)`
(`:104`, partial on active rows), so a second active membership aborts the
transaction.
Consequence: C reads for an active membership first and never `db.add`s the
returned row again.

### R-10 — `controls` [M]
Opened: `src/world_engine/writes/relations.py:1-40` (docstring), `:242-310`.
Finding: `controls` is structural; `_birth_typed_fact` (`:144-158`) creates
a `lien` fact for a social type and for `connects_to`, and returns None for
any other structural type, `controls` included.
Consequence: P1 — possession is the relation (for A2) plus a `statut` fact
(learnable).

### R-11 — creating an entity [M]
Opened: `src/world_engine/cockpit/crud/entities.py:123-215`
(`ENTITY_TYPE_REGISTRY`), `:525-560` (`_create_entity_core`,
`_write_body_facets`), `:562-630` (static core); `cockpit/routes/regions.py:135-220`.
Finding: static types are exactly `character`, `location`, `faction`,
`item` (enumeration E4); the core never commits, flushes, raises
`HTTPException(422)` on a missing name, and is called from routes by
region, NPC agent and room batch (enumeration E5). `character_type`
defaults to `npc` in the registry fields.
Consequence: G3 is exactly the static registry; the route injects a
creator wrapping `_crud._create_entity_core` (C-02's `create_entity`), and
re-raises its `HTTPException` after a rollback.

### R-12 — name resolution [M]
Opened: `src/world_engine/lore_resolve.py:30-60`, `:135-176`
(`resolve_named`), `:178-228` (`near_candidates`);
`tooling/verify/checks/name_index.py:17-20`, `:53-58` (R5 `CREATOR_ALLOWED`).
Finding: categories `place/person/faction/object/other` map to
`location/character/faction/item/(none)`; `resolve_named` returns
`matched/ambiguous/unmatched`, never picks; `near_candidates` is creator
only. R5 pins the files allowed to use the creator regime.
Consequence: D resolves names there and adds `lore_write_draft.py` to R5's
list in the same commit.

### R-13 — fact codes [M]
Opened: `src/world_engine/fact_refs.py` (whole, 115 lines).
Finding: `code_facts(db, ids)` codes in order (`f1 — <rendered text>`),
`resolve(code)` tolerates brackets and case, returns None off-list.
Consequence: D codes the L1 list and resolves every model code; an unlisted
code is dropped (CLAUDE.md invariant).

### R-14 — tokens and creator-only facts [M]
Opened: `src/world_engine/prose_render.py:27` (`TOKEN_RE`),
`src/world_engine/prose_tokens.py:194-225` (`tokenize`, read-only, regimes
`prose`/`names_only`); `src/world_engine/facet_reads.py:42-61`
(`creator_only_fact_ids`).
Finding: `tokenize` writes nothing and returns tokenized text; a creator-only
fact is one whose participant holds an `unaware` `is_secret` row on it.
Consequence: D finds the named entities with `tokenize` + `TOKEN_RE` and
excludes creator-only facts from the model's list.

### R-15 — prompt loading and shipping [M]
Opened: `src/world_engine/lore_prompt.py` (whole, 64 lines);
`tooling/verify/checks/lore_isolation.py:57-66` (R17), `:85-95`
(`PANEL_FILES`, `PIPELINE_FILES`), `:662-692` (R15, vacuity-guarded);
`tooling/verify/checks/prompt_registry.py:1-80` (`USAGE_LINE`,
`WIRED_FILES`); `src/world_engine/prompt_registry.py:246-275`;
`scripts/seed_pilot.py:132-175` (`upsert_prompt_template`, S2), `:2182`
(`DAY_PROMPT_HEADS`); `scripts/apply_ticket_0094_mention_choice_seed.py`.
Finding: the only loader for authoring prompts on the Lore shell is
`lore_prompt.load` (callers: enumeration E3), and R17 forbids a panel module
to import it; R15 fails on zero `select(` in its target. The seed ships new
heads through a module-level tuple read by an `apply_ticket_*` script.
`lore_plan.py` calls `chat(model=spec.model)` and is not in `WIRED_FILES`.
Consequence: N1 — `prompt_load.py` holds the loader verbatim, `lore_prompt.py`
re-exports it, R15 targets `prompt_load.py` and also forbids `select(` in the
re-export; the writing heads ship as `LORE_WRITE_PROMPT_HEADS`.

### R-16 — defaults cannot carry a secret [M]
Opened: `src/world_engine/models/canon_knowledge.py:163-196` (`FactDefault`:
`scope_type`, `scope_id`, `level`, `created_by`; CHECKs on scope);
`src/world_engine/knowledge_resolve.py:140-215` (tiers).
Finding: `fact_default` has no `is_secret` column; resolution reads
`level` only.
Consequence: a secret or a false belief is always a stored `knowledge` row
for a checked entity (E1); a default never mints one.

### R-17 — the Lore shell [M]
Opened: `frontend/src/lore/Lore.svelte` (whole, 218 lines; tabs at 94-101);
`frontend/src/lore/namesPanel.svelte.js:1-60`;
`frontend/src/creation/sheetRequest.svelte.js:30-35` (`api`);
`src/world_engine/cockpit/crud/entities.py:474-483` (`GET /api/entities`);
`src/world_engine/lore_mentions_read.py:30-33` (`active_world_id`).
Finding: two tabs (`question`, `names`); panels keep state in a
`*.svelte.js` module; `api()` throws `Error(detail)`; `/api/entities` lists
the active world's entities with `type`, `name`, `status`.
Consequence: F adds a third tab and a state module in the same shape.

### R-18 — occupations as factions [M]
Opened: `src/world_engine/models/canon_faction.py:20-40`.
Finding: `faction.faction_type` is free text; `parent_faction_id` exists.
Consequence: F1 needs nothing: « dockers » (type métier) and « Syndicat des
quais » (type organisation) are two factions.

### R-19 — prod canon size (Nia's machine, 2026-09-29, `mode=ro`) [M]
Opened: Nia's run of `measure_0098.py` on `~/.world_engine/world_engine.db`.
Finding (excerpts): largest active world Silka 297 facts / 186 free /
17 028 characters of free non-reserved facts; per participant entity p90 ≤ 7
facts, max 16 (Valnir), max 1 424 characters; world-level facts with no
participant 2-32 per world; `(entity, bloc facet)` pairs with >1 fact: 0 in
every world; legacy slugs up to 32 (Verkhaal, no longer played).
Consequence: L1 (named entities' facts + world-level facts) stays in the
low thousands of characters; the cap `MAX_CODED_FACTS = 200` is never hit on
measured data; Q19d holds, so a `bloc` edit is a rewrite.

### R-20 — CLAUDE.md budget [M]
Opened: `CLAUDE.md` (35 980 characters), `tooling/verify/checks/claude_md_contract.py:10-20`.
Finding: 38 000-character budget, 100-character lines, File structure at
its 80-line cap (`:447` Lore line, `:450` prompt_store line).
Consequence: D edits two existing lines (no new one); E adds one invariant
(3 lines). Final size 36 280.

## Contract sheet

Families first: the proposal's item family (C-02) is written before its
members' writers (C-03, C-04); the route family (C-06) before its four
members. Both re-read after the last member (gate (d)).

### C-01 — origin guard
Produced by: A   Consumed by: E (E1d), `origin_guard.py`
- `cockpit/origin_guard.py`: `LOCAL_HOSTNAMES = {"127.0.0.1", "localhost",
  "::1"}`; `WRITE_METHODS = {"POST","PUT","PATCH","DELETE"}`;
  `REFUSED_MESSAGE` (French, fixed); `host_name(host) -> str | None`;
  `verdict(method, host, origin) -> str | None` (None = proceed);
  `origin_guard(request, call_next)` (HTTP middleware, 403
  `{"detail": REFUSED_MESSAGE}`).
- Registered once: `app.middleware("http")(origin_guard)` right after
  `app = FastAPI(...)`.

### C-02 — the proposal (family: entities, facts, memberships, controls)
Produced by: F (client), D (as a draft, C-05)   Consumed by: C (`validate`,
`apply_proposal`), E (`write_commit`)
```
{"statement": str (non-empty), "questions": str|null, "answers": str|null,
 "entities": [{"ref", "action": "create", "name", "type": character|location|faction|item}
            | {"ref", "action": "existing", "entity_id"}],
 "facts": [{"ref", "action": "create", "content", "facet" (non-typed), "aspect"?,
            "participants": [ref], "defaults": [scope], "knowers": [knower],
            "mentions"?: [{"name","category"}]}
         | {"ref", "action": "existing", "fact_id", "participants", "defaults", "knowers"}
         | {"ref", "action": "rewrite", "fact_id" (a bloc descriptive fact), "content",
            "participants", "defaults", "knowers"}],
 "memberships": [{"entity_ref" (character), "faction_ref" (faction)}],
 "controls": [{"owner_ref", "location_ref" (location)}]}
scope  = {"scope_type": "world"} | {"scope_type": faction|location|rencontre, "scope_ref": ref}
knower = {"entity_ref", "level" (ladder), "is_secret": bool, "is_incorrect": bool}
```
- `lore_write_apply.validate(db, world_id, proposal) -> refs` raises
  `ProposalError` (French message) on: missing statement; an entity ref
  twice; an entity action outside `create|existing`; a created type outside
  `ENTITY_TYPES`; an existing id that is not an ACTIVE entity of the world;
  a fact ref twice; a fact action outside `FACT_ACTIONS`; a ref to no
  entity; a typed or unknown facet; a `bloc` or `appellation` fact without
  exactly one participant; a fact id outside the world; participants on a
  typed fact; a rewrite of a non-bloc fact; an unknown scope, a world scope
  with a ref, a scope ref of the wrong type, the same scope twice; a knower
  twice on one fact, an unknown level, a non-bool flag; a membership whose
  sides are not character/faction; a control whose target is not a
  location; nothing to write.
- `apply_proposal(db, world_id, proposal, create_entity) -> ApplyResult`
  (`entry_id`, `written` {"table:action": n}, `skipped` [French notes]).
  Never commits. Order: entry, entities (flushed), facts, memberships,
  controls. Skips (and reports) a knower already holding the fact, a
  participant already attached, an identical default, an active
  membership, an existing `controls` pair. A write-site `ValueError`
  becomes `ProposalError`.
- `create_entity(name, type) -> Entity` is injected by the caller.
- `CREATED_BY = "creator_lore"`.

### C-03 — `add_lore_fact`
Produced by: C   Consumed by: C (`apply_proposal`)
`writes/facets.py::add_lore_fact(db, *, world_id, facet, content,
created_by, participant_ids, aspect=None, scopes=(), mentions=None) ->
LoreFactRows(fact, participants, defaults)`. `ValueError` on an unknown or
typed facet, empty content, a participant outside the world or twice, a
`bloc`/`appellation` fact without exactly one participant, a second `bloc`
fact (same aspect), a `none`/malformed scope, a scope twice. Tokenizes
(`names_only` without the owner for an appellation), records unresolved
names and declared mentions, writes `knows` defaults. Never commits.

### C-04 — the source record
Produced by: B (tables), C (writer)   Consumed by: C, E (`lore_write_read`)
- `lore_entry(id, world_id FK, statement NOT NULL, questions, answers,
  created_at)`, index `idx_lore_entry_world(world_id, created_at)`.
- `lore_entry_row(id, entry_id FK, row_table CHECK in
  LORE_ENTRY_ROW_TABLES, row_id, action CHECK in created|updated)`, UNIQUE
  `idx_lore_entry_row_entry(entry_id, row_table, row_id)`.
- `writes/lore_entries.py`: `write_lore_entry(db, *, world_id, statement,
  questions=None, answers=None)` (empty statement -> ValueError, blanks ->
  NULL); `record_entry_row(db, *, entry_id, row_table, row_id,
  action="created")` (values outside the CHECK lists -> ValueError).
- `migrate_v2_11_lore_entry.py`: refuses below v2.10; creates both tables;
  idempotent; zero rows; converges `schema_meta` to v2.11.

### C-05 — the draft
Produced by: D   Consumed by: E, F
- `lore_write_draft`: `QUESTIONS_USAGE = "lore_statement_questions"`,
  `PROPOSAL_USAGE = "lore_statement_to_proposal"`, `MAX_QUESTIONS = 3`,
  `MAX_CODED_FACTS = 200`, `WRITE_UNAVAILABLE_MESSAGE` (French),
  `CATEGORY_TYPE`.
- `draft_context(db, world_id, statement) -> DraftContext(entity_lines,
  coded)`; `draft_questions(db, world_id, statement) -> list[str]`;
  `draft_proposal(db, world_id, statement, answers="") -> dict` with keys
  `statement, answers, entities, facts, memberships, controls, notes,
  facets`. Each entity carries `status`: `matched` (`action: existing`,
  `entity_id`, `name`, `type`), `ambiguous` (`action: null`, `candidates`
  [{entity_id,name,type}]) or `new` (`action: create`, `type` from the
  category or null, `near` [{entity_id,name,type,score}]). Facts follow
  C-02 with `fact_id` resolved from the model's `code`. `facets` =
  [{name, label}] of the non-typed `FACETS`. `OllamaError` and
  `LlmParseError` propagate.
- Prompt variables: questions `statement, entities, facts`; proposal
  `facets, entities, facts, statement, answers`.

### C-06 — the writing routes (family)
Produced by: E   Consumed by: F
- `POST /api/lore/write/questions` `{statement}` -> `{"questions": [...]}`.
- `POST /api/lore/write/draft` `{statement, answers?}` -> C-05's draft.
- `POST /api/lore/write/commit` `{proposal}` -> `{"ok": true, "entry_id",
  "written", "skipped"}`; 422 `{detail}` on a refused proposal (rolled
  back).
- `GET /api/lore/write/entries` -> `{"entries": [{id, statement, questions,
  answers, created_at, rows: [{row_table, action, label}]}]}` (newest 50).
- Common: 400 with no active world; 422 on an empty statement; 503 with
  `WRITE_UNAVAILABLE_MESSAGE` when Ollama is down; 502 on an unparseable
  model reply; 403 from C-01 for a non-local writer.

### C-07 — the shared prompt loader
Produced by: D   Consumed by: `lore_prompt` (re-export), `lore_write_draft`
`prompt_load.RenderSpec(system_prompt, user_template, model)`;
`prompt_load.load(db, usage) -> RenderSpec` (body moved verbatim from
`lore_prompt.load`; raises `LlmParseError` on a missing head);
`lore_prompt.py` = `from .prompt_load import RenderSpec, load`.

## Gate output

### (a) Property trace

| Property the lot asserts | Finding | Declaring file opened |
|---|---|---|
| no middleware exists; loopback, no auth | R-01 | `cockpit/app.py` |
| cockpit ports 8000 and 8001 | R-01 | `scripts/cockpit.py`, `.claude/launch.json` |
| five checks post through a default `TestClient` | R-02 | the five check files |
| schema at v2.10; constant, header, changelog move together | R-03 | `schema_version.py`, schema doc, `schema_version_agreement.py` |
| cascade lists and fixture coverage rules | R-04 | `writes/worlds.py`, `world_cascade.py` |
| record tables are non-canon, in `pipeline.py` | R-05 | `models/pipeline.py`, `canon_write_policy.txt` |
| only `writes/facets.py` may pass a non-literal facet | R-06 | `fact_facets.py` (R3 implementation, `check_call_sites`, lines 150-192) |
| `add_entity_fact` is one descriptive fact, one participant | R-06 | `writes/facets.py` |
| `attach_participants` refuses typed facts, no read guard | R-07 | `writes/facts.py` |
| `(fact_id, entity_id)` participant is unique | R-07 | `models/canon_knowledge.py:135` |
| unknown level falls back to `rumor` | R-08 | `writes/knowledge.py:199` |
| `(entity_id, fact_id)` knowledge is unique | R-08 | `models/canon_knowledge.py:209` |
| `write_membership` adds its row; one active per faction | R-09 | `writes/factions.py`, `models/canon_faction.py` |
| `controls` births no fact | R-10 | `writes/relations.py` (`_birth_typed_fact`) |
| static types = character, location, faction, item | R-11 | `cockpit/crud/entities.py` |
| `_create_entity_core` commit-free, raises `HTTPException` | R-11 | `cockpit/crud/entities.py` |
| creator regime allow-list | R-12 | `name_index.py` check (R5 implementation) |
| `resolve_named` never picks | R-12 | `lore_resolve.py` |
| unlisted code resolves to None | R-13 | `fact_refs.py` |
| `tokenize` writes nothing | R-14 | `prose_tokens.py` |
| creator-only definition | R-14 | `facet_reads.py` |
| R15 fails on zero `select(`; R17 panel rule | R-15 | `lore_isolation.py` (implementations) |
| `lore_plan` is not in `WIRED_FILES` | R-15 | `prompt_registry.py` check |
| `fact_default` has no secret column | R-16 | `models/canon_knowledge.py` |
| Lore shell tabs and panel shape | R-17 | `Lore.svelte`, `namesPanel.svelte.js` |
| `faction_type` is free text | R-18 | `models/canon_faction.py` |
| CLAUDE.md budgets | R-20 | `claude_md_contract.py` |

### (b) Case tables

**`verdict(method, host, origin)`** — the full table is `origin_guard.py`'s
`_CASES` (18 rows): reads with any Host/Origin proceed; writes proceed only
with a local Host hostname (any port, IPv6 bracketed) and an absent or local
http(s) Origin; `testserver`, a missing Host, a lookalike
(`127.0.0.1.evil.example`), `Origin: null` and `file://` are refused.

**Entity decision (draft -> proposal)**

| draft status | default decision | panel choices | proposal |
|---|---|---|---|
| matched | existing | re-pick from lists, create, keep as text | existing / create / dropped + mention |
| ambiguous | none (commit blocked) | pick a candidate or any entity, create, text | same |
| new, category typed | create (type preset) | pick near/any entity, create, text | same |
| new, `other` | none until a type or another choice (commit blocked) | same | same |

**Fact action × what is allowed**

| action | content | facet | participants | defaults | knowers | fact_id |
|---|---|---|---|---|---|---|
| create | required | non-typed; bloc/appellation ⇒ 1 participant | any, in refs | any valid | any valid | — |
| existing | ignored | — | added if absent; none on a typed fact | added if absent | added if not held | required, same world |
| rewrite | required | fact must be descriptive bloc | same as existing | same | same | required |

### (c) Enumerations (raw, on `3e64554`)

E1 — `git grep -n "TestClient(app" -- tooling/verify/checks`:
```
tooling/verify/checks/choice_review.py:40:through `fastapi.testclient.TestClient(app)` with `world_engine.cockpit.app`
tooling/verify/checks/choice_review.py:561:    client = TestClient(app)
tooling/verify/checks/name_resolution.py:446:    client = TestClient(app)
tooling/verify/checks/prompt_model_write.py:171:    client = TestClient(app)
tooling/verify/checks/scene_join_target.py:190:    client = TestClient(app)
tooling/verify/checks/spatial_door_travel.py:164:    client = TestClient(app)
```
write calls (`client.(post|put|patch|delete)(`) per file: choice_review 1,
name_resolution 4, prompt_model_write 6, scene_join_target 6,
spatial_door_travel 9. Line 40 is a docstring.

E2 — `git grep -n "middleware\|CORSMiddleware" -- src/world_engine`: no
output.

E3 — importers of `lore_prompt` in `src/`:
```
src/world_engine/cockpit/routes/lore.py:23:from ... import lore_prompt as _lore_prompt
src/world_engine/lore_plan.py:14:from . import llm_parse, lore_prompt
src/world_engine/lore_render.py:15:from .lore_prompt import RenderSpec
```

E4 — `ENTITY_TYPE_REGISTRY` keys (`cockpit/crud/entities.py`):
```
124:    "character": {
140:    "location": {
164:    "faction": {
190:    "item": {
```

E5 — `git grep -n "_create_entity_core(" -- src`:
```
src/world_engine/cockpit/crud/entities.py:525:def _create_entity_core(body: EntityWriteBody, db: DbSession) -> Entity:
src/world_engine/cockpit/crud/entities.py:695:        entity = _create_entity_core(body, db)
src/world_engine/cockpit/routes/npc_agent.py:220:    npc_entity = _crud._create_entity_core(npc_body, db)
src/world_engine/cockpit/routes/regions.py:164:        fac_entity = _crud._create_entity_core(fac_body, db)
src/world_engine/cockpit/routes/regions.py:212:            loc_entity = _crud._create_entity_core(loc_body, db)
src/world_engine/cockpit/routes/room_batch.py:151:            room_entity = _crud._create_entity_core(room_body, db)
```

E6 — R19 (bloc duplicates): M6 = 0 in all twelve worlds (Nia's report).

### (d) Families
- [x] C-02 written before C-03/C-04 and re-read after `controls` was added.
- [x] C-06 written before its four routes and re-read after `entries`.

### (e) Gates and the module that satisfies each

| Gate | Proposed / passed | Satisfied by | What it forbids that the module needs |
|---|---|---|---|
| `origin_guard.py` O1-O4 | proposed (A) | `cockpit/origin_guard.py`, `app.py` registration, the five checks' `base_url` | a test Host — solved by `base_url`, never by an exception |
| `lore_write.py` L0 | proposed (A) | the census, extended by C, D, E | a lore-write module no brief named |
| `lore_write.py` W1-W2 | proposed (B) | `models/pipeline.py`, `migrate_v2_11_lore_entry.py` | — |
| `lore_write.py` C1-C2 | proposed (C) | `writes/facets.py::add_lore_fact`, `lore_write_apply.py`, `writes/lore_entries.py` | a model or cockpit import — the entity creator is injected |
| `lore_write.py` D1-D2 | proposed (D) | `lore_write_draft.py`, `seed_pilot.LORE_WRITE_PROMPT_HEADS`, `apply_ticket_0098_lore_write_prompts.py`, `prompt_load.py` | a writer call in the draft module |
| `lore_write.py` E1-E2 | proposed (E) | `cockpit/routes/lore_write.py`, `lore_write_read.py` | a query or model call in the route — moved to the read/draft modules |
| `lore_write.py` F1 | proposed (F) | `WritePanel.svelte`, `writePanel.svelte.js`, `Lore.svelte` | a literal facet list — served by the draft |
| `lore_isolation.py` R15, R17 | passed (D, E) | `prompt_load.py` (R15), `PANEL_FILES` extended | importing `lore_prompt` — the loader moved (N1) |
| `name_index.py` R5 | passed (D) | `CREATOR_ALLOWED` + `lore_write_draft.py` | — |
| `fact_facets.py` R2-R3 | passed (C) | `add_lore_fact` lives in `writes/facets.py` | a non-literal facet elsewhere |
| `prompt_registry.py` | passed (D) | two `PROMPT_REGISTRY` entries, `usage="..."` lines in the seed | — |
| `world_cascade.py` W1-W4 | passed (B) | `writes/worlds.py` lists, `_FIXTURE` | — |
| `schema_version_agreement.py` | passed (B) | constant + doc header v2.11 | — |
| `single_canon_write.py` | passed (C, E) | writes through the chokepoints; `lore_entry*` non-canon | — |
| `json_ui_boundary.py` | passed (B) | plain TEXT columns | JSON for UI data |
| `identity_tokens.py` | passed (C, D, E) | reads through `prose_render` only | `content_raw` outside the allow-list |
| `claude_md_contract.py` | passed (D, E) | two edited lines, one new invariant (36 280 chars) | a new File structure line |
| `frontend_build_fresh.py` | passed (F) | rebuilt `static/` | — |
| `module_budget.py`, `function_length.py` | passed | every new module < 400 lines, functions < 80 | — |
| `decisions_index.py` | passed | one lowercase-letter header per brief, index regenerated | — |
| `pipeline_state.py` | passed (A) | `lore_write.py` and `origin_guard.py` exist from A | an arrow to a missing file |
| `corpus_gate.py` | passed (every brief) | 128/128 | — |

## Amendments

(none)
