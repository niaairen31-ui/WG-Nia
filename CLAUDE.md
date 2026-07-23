# World Engine — Project Instructions

## What this is

A locally-hosted AI-powered tabletop RPG world engine (Verkhaal is the pilot
world). A creator cockpit (world-building + play surface) drives local models
through structured prompts; every AI-proposed change to world canon passes a
creator checkpoint before it is applied. This file is the standing contract
for Claude Code sessions: conventions, invariants, and how to run things.
History and rationale live in `tooling/standards/ARCHITECTURE_DECISIONS.md`
and `world-engine-schema-changelog.md` — never here.

## Stack

- Python, FastAPI, SQLModel, SQLite (Supabase/PostgreSQL migration path
  preserved via the env-var DB URL).
- Frontend: single-page HTMX/vanilla-JS `cockpit/index.html`. No build step,
  no new dependencies without a decision.
- Local models via Ollama; Claude API reserved for heavy lore-coherence work.
- Runtime: Windows / PowerShell — `.venv\Scripts\Activate.ps1`,
  `$env:PYTHONPATH = "src"`.

## Working rules

- Work in small, scoped steps. Do **only** what the current task asks. Do not
  anticipate or build future steps unprompted — if a next step seems useful,
  suggest it and stop.
- The database schema is authoritative. Match `world-engine-schema.md`
  exactly: same tables, columns, types, defaults, and foreign keys.
- **Creator control is structural.** Nothing mutates world state without
  passing through `proposed_mutation` and explicit creator approval. Dialogue
  is free; its consequences are not.
- **Injected context depends on the active role, never the account.** In
  player mode, never expose an NPC's secrets, others' secrets, or anything
  the player character is not meant to know.
- Keep the database engine URL in an environment variable (default to a local
  SQLite file) so switching to PostgreSQL/Supabase needs no code change.
- History is sacred: prefer preserving successive states over overwriting them.
- **`--force` only deletes `proposed` rows.** Any `proposed_mutation` row
  with status `applied`, `approved`, or `rejected` is reviewed history and
  must never be deleted — not by the CLI `--force` flag, not by the cockpit
  re-analyze endpoint. A forced re-analysis regenerates proposals alongside
  existing reviewed rows.
- **Language convention:** design conversation happens in French; all code,
  schema, comments, commit messages, and documentation are in English.
- **Step closure:** every closed step updates the schema changelog (if
  schema-touching) and keeps `tooling/standards/ARCHITECTURE_DECISIONS.md`
  and this file consistent with the code. Use the `/close-step` command.
  This file is contract-checked: `tooling/verify/checks/claude_md_contract.py`
  enforces its section whitelist, line budgets, and the ban on brief/schema
  archaeology in the File structure section.
- **Every Création page is a `CREATION_TABS` registry entry** rendered by the
  generic dispatcher (`showCreationSubTab`, `cockpit/index.html`) under the
  standard shell; no page or tab-specific branch may exist outside the
  registry, and a page's primary action exists only as its registry
  `primaryAction` (`tooling/verify/checks/page_contract.py` enforces). A
  slot may declare `display: 'on_demand'` to stay hidden and unloaded until its shell toggle is clicked (default `'always'`, today's behavior).
- **The review tree** (`review*`, `index.html`) is a generic accept/reject component driven by a registered descriptor, never by consumer globals: a consumer calls `reviewRegister(key, descriptor)` and every DOM-reachable entry point takes that key as its first argument (inline `onclick` handlers are strings and cannot carry a closure). `reviewCascade` is PURE and re-attaches an orphan to `descriptor.fallbackParentId` — region passes its draft root, the room batch generator (TICKET-0042) passes its synthetic anchor; that fallback is never recomputed inside the component. No `review*` body may name `region`, and outside the component only `regionRenderAll`, `regionReviewDescriptor`, `regionRenderFactionsPanel`, `_sheetEntityOptions`, `batchRenderAll` and `batchReviewDescriptor` may name a `review*` symbol — both directions enforced fail-closed by `tooling/verify/checks/review_component.py`. `index.html` remains a single file with no build step; splitting it is a doctrine change, not a refactor.

## Ticket pipeline (governance)

- **Git (C1):** never push to `main`. Work on a `ticket/NNNN` branch and open
  a PR. Merge only after a green `/verify` AND Nia's live gate.
- **Danger classes (D1):** destructive_data | migration | permanent deletion
  -> human gate, no auto-merge (Nia decides). No automated backup exists;
  `scripts/backup.py` is a manual, deliberate step. db_write alone triggers
  nothing.
- **Escalate to Nia only on:** (a) an unspecified user-visible behavior
  change, (b) a destructive/irreversible data operation, (c) an architecture
  change above the ticket's stated `blast_radius`, (d) two consecutive
  `/verify` failures.
- **Model lanes (E1):** Opus for intake and escalated architecture decisions;
  Sonnet for RECON, execution, and verify. `/model opusplan` = plan on Opus,
  execute on Sonnet.
- **Protocol gate:** RECON before every brief (report-only, never acts on a
  finding); every commit touching the engine runs `/review-step` then
  `/close-step`; a ticket ends with `/verify`. Schema versions are computed,
  never chosen: on any schema-touching step closure, new version = the
  `Current schema version:` line in `world-engine-schema.md`, minor + 1.
  That header line is the single source for the current number; the
  append-only log lives in `world-engine-schema-changelog.md` (repo root).
  If the minor part reaches 99, stop and escalate (D1-c). RECON lesson:
  "RECON: trace every UI-visible field to its storage, including
  `entity.metadata` JSON keys — grepping columns is not sufficient."
- **Artifact convention — the filename is law.** Tickets, RECONs, and briefs
  arrive as `.md` files carrying their final real IDs in both filename and
  content (`TICKET-0010.md`, `RECON-0010.md`, `BRIEF-0010-a.md`); no
  placeholder resolution step. Nia deposits artifacts into
  `tooling/tickets|recon|briefs` manually. Tickets keep a `slug:`
  front-matter field; recon specs and briefs keep a line-1
  `<!-- slug: ... -->` comment. The pipeline cockpit's deposit flow is
  dormant (see ARCHITECTURE_DECISIONS.md) — never route artifacts through
  it.
- **Where things live:** `tooling/tickets`, `tooling/recon`,
  `tooling/briefs`, `tooling/questions` (pipeline escalations),
  `tooling/glue` (`next_id.py`, `gen_decisions_index.py`,
  `question_response.py`), `tooling/verify` (`run.py`, `checks/`,
  `baselines/`, `results/`), `tooling/standards`
  (`ARCHITECTURE_DECISIONS.md`, generated `DECISIONS_INDEX.md`,
  `code_standards.md`), `tooling/improvement/bug_log.jsonl`,
  `tooling/pipeline_cockpit/` (separate app, port 8100, never imports
  `src/world_engine/`; deposit flow dormant).
- **Orchestration:** `/pipeline TICKET-NNNN` chains exec -> verify -> PR to
  the next human gate; `tooling/questions/` is where it escalates (D1) for
  Nia's response. Recon results are pushed at recon time; everything else
  publishes at Step 3.
- This section governs the ticket pipeline itself (process, gating,
  escalation). It does not replace or relax any invariant below — those
  still apply to every change regardless of how it was ticketed.

## Numbering & decisions governance

- IDs are computed, never chosen: next ID = `python tooling/glue/next_id.py`
  (max over tickets/recon/briefs, 4 digits). A ticket, its recon, and its
  brief(s) share one number: TICKET-NNNN / RECON-NNNN / BRIEF-NNNN-a, -b.
  Artifacts are authored with the final ID already in place (filename is
  law, above).
- Legacy two-digit BRIEF-NN identifiers are a closed, grandfathered
  namespace: never reused, never renumbered.
- New decision records in `tooling/standards/ARCHITECTURE_DECISIONS.md` use
  the header form
  `## TITLE (BRIEF-NNNN[-x][, ...], schema vX.YY | no schema change)` —
  enforced by `tooling/verify/checks/decisions_index.py` against baseline.
- `tooling/standards/DECISIONS_INDEX.md` is generated; never edit by hand.
  Generated files are never hand-resolved in a merge conflict: regenerate
  (`python tooling/glue/gen_decisions_index.py`) and stage the result. A
  conflict outside a branch's diagnosed set is an escalation, not an improvisation.

## Invariants (verified at every review)

Law only. Rationale, chantier history, and deferred alternatives live in
`tooling/standards/ARCHITECTURE_DECISIONS.md`.

- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
  gathering. Per-NPC, NOT per-location (multiple open gatherings in one
  location are legal). Defended on every join/migrate path.
- **Dissolve-before-create lives in the caller** (`enter_location`), never
  inside `generate_gatherings`.
- **`relation_change` is owned by window analysis** (`analyze_window`,
  `proposed_by='local_ai_window'`): at most one `relation_change` per NPC
  pair per window, proportionate to that window. Never deduplicated against
  prior windows (not covered by `_mutation_match_key`).
- **`new_knowledge` / `status_change` are idempotent facts:** identity-based
  dedup (`entity_id` + `subject`; `entity_id`) via `_mutation_match_key`,
  same conversation required.
- **Secrets are structurally excluded** from every assembled context — never
  "guarded by instruction". `character.secrets` is creator meta-narrative
  and is NEVER read by any context assembler. What an NPC
  knows-but-conceals lives in `knowledge` rows with `is_secret = TRUE`,
  excluded by query construction at every assembler AND every propagation
  path (`analyze_overhearing` never sources a proposal from an `is_secret`
  row).
- **`relation_change`'s `entity_a_id`/`entity_b_id` come from the model's
  payload.** Missing -> skip and log (`_normalize_to_schema` returns
  `None`); never attributed via a conversation-level default. Per-item
  roster resolution is a named deferral.
- **Two sanctioned canon-write paths for canon ROWS:** `_apply_mutation` (AI
  proposals, post-approval) and the creator CRUD, never elsewhere for an AI proposal
  (`POST /api/entities/generate` accept reuses creator CRUD). A THIRD, creator-only
  authority covers canon STRUCTURE: `writes/schema.py::create_entity_type`, closed
  by `single_canon_write.py` + `runtime_ddl_guard.py`.
- **History is sacred on BOTH write paths:** any edit to `relation` or
  `knowledge` appends the previous state to `change_history`; states are
  preserved, never silently overwritten. `entity_type_history` extends this to the schema grain: append-only by construction, no `change_history` column — the rows ARE the history.
- **Commit before touching any canon-writing path** (`_apply_mutation`, the
  creator CRUD, the analyzers, and everything they call) — hard.
  Recommended: also commit before touching the `/say` flow or the
  interpretation phase (playability-critical). On SQLite, DDL participates in the surrounding transaction — a structural guarantee of the shared engine (`db.py`), never a per-site precaution.
- **The MJ context assembler is scoped to the player's perception
  boundary:** only what the player may perceive or already knows. Never
  NPC-private knowledge, secrets, internal names, non-public entities, or
  invisible relations. Enforced by query construction, never by instruction.
- **Knowledge levels never decrease through the mutation pipeline:**
  `unaware < rumor < suspicious < partial < knows < fully_understands` is
  monotone for every `knowledge_change` apply (`_apply_mutation`'s
  "level already >= proposed" guard). `analyze_overhearing` additionally
  caps acquired/upgraded levels at `knows` in code; `analyze_window` has no
  structural cap (named deferral). Downgrades, forgetting, and
  `is_incorrect` correction are creator CRUD only.
- **`scene_state` is a third, explicitly ephemeral write path.**
  `_write_scene_state` archives the previous snapshot to `history[]` before
  every write; cleared to `{}` on conversation close; never canon — durable
  consequences require a `proposed_mutation`.
- **`proposed_by='engine'` deterministic proposals**
  (`_propose_engine_injury`, `_propose_engine_discovery`) follow the same
  review queue as AI proposals — never auto-applied.
- **Constraint gating is structural, not instructional:** gagged/restrained/
  blindfolded effects are enforced in Python before any model call
  (`_stream` in `app.py`). Blindfolded exclusion is a data exclusion in
  `assemble_mj_context`, never a "don't describe" prompt.
- **Condition ladder is monotone for engine writes:** `unharmed -> bruised
  -> injured -> neutralized` — forward only by violent-verdict code; backward only by creator CRUD.
- **Frozen scene yields no model calls:** `scene_state.frozen = True` ->
  `/say` short-circuits with a fixed MJ message. Only the creator panel
  unfreezes.
- **`discoverable_detail` is structurally excluded from every assembler,
  with one consciously narrowed exception:** no assembler or prompt-building
  path reads the table. `hidden` content reaches a model ONLY via the
  post-selection `{detail_content}` injection in `_stream()` on a
  partial/success perception search (`domain="perception"`,
  `opposed_npc_id=None`). `ambient` content is read only via the pure code
  predicate `active_signposts` (context.py), passed directly into the MJ
  establishment call. A `location_subculture` row with `key = "hidden"`
  is a TRAP — never add `"hidden"` to `_SAFE_SUBCULTURE_KEYS`, and every
  reader filters `is_hidden = FALSE` at query construction; discoverable
  content lives ONLY in `discoverable_detail`.
- **`connects_to` is location map topology, never a social signal.** Its
  `intensity=50` is meaningless. Every gameplay reader of `relation` keyed
  on a character/player id is structurally blind to `connects_to` rows; the
  sole intentional gameplay reader is `_location_neighbours`. Any new
  world-wide relation scan MUST exclude `type='connects_to'`.
- **The `ledger` is append-only.** INSERT-only on both canon-write paths;
  corrections are new compensating lines. No UPDATE/DELETE endpoint or code
  path may touch a `ledger` row.
- **`resource_change` writes two canon tables** (`ledger` + optional
  `knowledge`) inside one `_apply_mutation` SAVEPOINT — the single
  sanctioned exception to one-branch-one-table. Money leg accumulates
  (never deduped) and targets the player only, until tracked NPC purses
  exist; knowledge leg is idempotent, guarded at apply time.
- **Tick-sourced `proposed_mutation` rows have `source_type='world_tick'`,
  `proposed_by='local_ai_tick'`, NULL `pass_play_id`/`conversation_id`, and
  a mandatory `tick_id`** (one UUID per `run_world_tick` invocation).
  `_find_applied_duplicate`'s tick branch (`cockpit/routes/mutations.py`) is
  canon-existence-based, never a `tick_id`-scoped history comparison, and
  must never be extended to `relation_change` (accumulating deltas, never
  guarded).
- **`npc_price` rows are seller configuration,** injected ONLY into that
  seller's own dialogue context — never into `assemble_mj_context` or any
  other entity's context. A quoted price writes no canon; money moves via
  `resource_change` through the checkpoint. Catalogue prices are firm and
  universal; only uncatalogued quotes are relation-modulated.
- **Membership reaches a model prompt only via `read_public_memberships`;**
  `is_secret` rows never enter any prompt, including the holder's own —
  structural filter, no override parameter. The true `role` behind a
  `cover_role` never enters any prompt: the accessor resolves
  `cover_role ?? role`. Espionage rides on `goals` prose, never a
  confessable affiliation label. Declared faction roles live in
  `faction_role` (relational, never JSON; case-uniqueness is the index's job).
- **Creator-direct create helpers never commit in their core; the commit
  boundary belongs to the caller.** `create_entity`, `create_knowledge`,
  `open_entity_membership` each split into a commit-free core plus a thin
  route wrapper owning the single commit — a structural seam, not a
  `commit:` flag.
- **Region generation writes no canon; commit is atomic; resolution is
  server-authoritative.** `generate_region_draft` proposes factions and
  locations only — characters retired to the group agent (TICKET-0037 A1).
  `POST /api/regions/commit` is the single write point: entities, skeleton
  (`parent_location_id`, faction role vocabulary via `write_faction_role`)
  and creator-confirmed links commit in one transaction, all-or-nothing,
  via the commit-free cores and `write_relation`. No model-emitted id ever
  reaches a canon row; the accept/reject cascade and link targets are
  re-derived server-side from raw client state; rejected/uncommitted/
  unresolved/self-referential targets write nothing.
- **PC knowledge is written `is_secret=False`; `_normalize_knowledge` is
  NPC-only and forces `is_secret=True` — never reuse it for a PC.**
  `_normalize_player_knowledge` emits no `is_secret` key; `False` is
  applied at write time by the accept route (`create_player_character` via
  `writes.write_knowledge`), never by the generator.
- **A PC is excluded from NPC co-presence by construction:** the
  `H_COMPANY` query in `assemble_npc_context` carries
  `Character.character_type != "player"`. Do not widen this filter, and do
  not repoint it at a future NPC-to-NPC observation feature without a
  deliberate decision.
- **Creator-CRUD edits that change a character's `current_location_id`, or
  set an entity's `status` to a non-active value, MUST close that entity's
  open `gathering_member` rows via `close_open_memberships`** (gatherings
  are not canon — no `_apply_mutation`, no `change_history`). Roster and
  co-present reads gate on `entity.status='active' AND
  vital_status='alive'` in addition to `gathering_member.left_at IS NULL`.
- **Hard deletes are a closed, named list** — enforced by
  `tooling/verify/checks/single_canon_write.py`; any new hard-delete path
  must be named here, never added silently. The list:
  `delete_world_cascade` (broadest — every row scoped to a world, world row
  included); `skill_definition` delete (one definition + its dependent
  `skill` rows); creator-correction deletes `delete_relation`,
  `delete_knowledge` (each discards the row's `change_history` with the
  row), `delete_discoverable_detail`, and `write_faction_role(mode=
  "delete")` (S1, blocked while an active membership holds the role) —
  creator-CRUD-only, never reachable from any AI or play path. Full-replace config deletes (whole-set replace, not single-row correction): `write_npc_prices`, `write_location_subculture`, `write_world_laws`, `write_location_obstacles`, and `write_location_doors` each `DELETE FROM` their table(s) scoped to one parent (NPC / location / world / location / location) then re-insert the submitted set, in one transaction — creator-CRUD and world-bootstrap only (`set_npc_prices`, `set_location_subculture`, `create_world`, `set_location_geometry`, `set_location_doors`), never reachable from any AI or play path. These tables carry no `change_history` by design (metadata-config category); the full-replace IS their write shape. No table may take a foreign key on `door.id` (A1 escalation guard, TICKET-0034) — enforced by `door_terminal.py`. `cockpit/spatial_doors.py` orchestrates door resolution and implements no math: distances, thresholds and spawn offsets belong to `placement.py`, the sole placement/distance authority (K1, TICKET-0034) — enforced by `door_terminal.py`. `_perform_travel` has three callers, all in `routes/play.py`: conversation-bound (in-fiction), creator god-mode, and door-gated (`/api/spatial/travel`, TICKET-0034). The neighbour restriction is a property of the in-fiction callers (C1, BRIEF-16); the door-gated caller carries it through `door_id`. `/api/spatial/travel` lives in `routes/play.py`, not `routes/spatial.py`, because it writes. `location_type_catalog` reaches the creator surface through exactly two routes, both `cockpit/crud/locations.py`: `GET /api/location-types` (active-world scoped list) backs the Creation-mode type picker's datalist (never a hardcoded vocab); `POST /api/location-types` (`upsert_location_type`) is the classification-prompt persist step — a location save gates on it whenever the chosen type is uncataloged or `classification IS NULL` (Interieur/Exterieur, once, TICKET-0039); it also carries `default_width`/`default_height`, a per-type size template applied ONCE at a location's creation and never retroactive to an existing location (TICKET-0040). `PUT /api/entities/{id}/geometry` distinguishes a bounds key OMITTED from the request body (preserved) from one sent as explicit `null` (cleared), via `body.model_fields_set` — the one route in the codebase where full-replace does not govern every field; the `obstacle` set beneath it stays full-replace (F1, TICKET-0040, BRIEF-0040-c). `spatial_author._catalog_row` is the single catalog read path (J1, TICKET-0040) — both `location_classification` and the size-template reader resolve a `location_type` through it — and a location's birth bounds come from that template ONLY at `cockpit/crud/entities.py::_create_entity_core` (E1), never from the update path. `LOCATION_TYPE_ORDER` (index.html) stays the browse-tree bucket order only, never the vocabulary. Every creator path that creates a `connects_to` edge flows through `connect_locations` (`spatial_author.py`, J1, TICKET-0039) — write the edge then `materialize_doors` both endpoints: region commit takes the bulk equivalent (`commit_region` collects touched location ids from `written_links` and calls `materialize_doors` once before its single commit); the manual adjacency route (`crud/relations.py::create_relation`, `type == "connects_to"`) calls `connect_locations` directly; the room batch atomic commit (`cockpit/routes/room_batch.py::commit_room_batch`, TICKET-0042, report-only generation enforced by `room_batch_report_only.py`) calls it once per edge (K1 tree + confirmed supplementary), re-deriving each room's `parent_room` against the accepted set server-side (never a client cascade) and degrading a NULL-bounds/classification anchor's door(s) to the origin (T1) rather than blocking. `write_relation` itself stays a pure relation writer — never embeds materialization. Door kind (interior-interior / boundary / exterior-exterior) is DERIVED, never stored: `spatial_author.location_classification` is the ONLY interior/exterior reader, resolving a location's `location_type` against `location_type_catalog` case-insensitively. `commit_region`'s E1 street-access note (a BUILDING SHELL — interior with an exterior parent, or an interior root — with no live exterior neighbour) is purely advisory: appended to the response's `notes` list, never blocking the commit and never mutating. Door coverage, door distinct-points, and type-vocab classification are fail-closed G1 gates: `tooling/verify/checks/door_coverage.py` (every active connects_to edge between active locations carries both directed door rows), `tooling/verify/checks/door_distinct_points.py` (within one active location carrying non-NULL, positive bounds, no two `door` rows share the same `(x, y)`; NULL-bounds locations excluded), and `tooling/verify/checks/location_type_classified.py` (every active location's `location_type` is catalogued with a non-NULL classification). `materialize_doors` re-derives a door still sitting at the exact H1 bounds center (`placement.is_legacy_center`, G1, TICKET-0040) onto the perimeter on its next run; every other existing point, hand-placed or already-perimeter, is reused verbatim.
- **Custom skill lookups filter `skill_definition_id`, by construction:** a
  base-domain `skill` lookup MUST include `AND skill_definition_id IS NULL`.
  A custom skill resolves via its `skill_definition.base_domain` — never
  its own `domain` column — and that resolved `base_domain` is what every
  base-domain-keyed downstream branch keys off. `skill_definition` and
  custom `skill` rows are PC-only and MJ-narration-only this phase: no
  NPC-side read (named deferral).
- **A `skill_definition` delete always succeeds** (no `ON DELETE RESTRICT`,
  no `change_history` snapshot): dependent PC `skill` rows then the
  definition, one transaction. The type-"Oui" modal is the sole safeguard —
  a named exception to "History is sacred", scoped to one row.
- **A new `skill_definition` backfills a tier-0 `skill` row onto every
  existing PC of its world, in the create's own transaction** — the
  catalogue<->PC alignment is never partial. Renaming touches no `skill`
  row (FK-by-id); re-basing (`base_domain` change) updates `domain` on
  every dependent `skill` row in the same write.
- **A `skill_definition.name` can never equal a base-domain literal**
  (`physical`/`agility`/`perception`/`composure`, case-insensitive) — both
  write paths (creator CRUD and `_normalize_skill_catalogue`) reject/drop
  it.
- **All templated model calls resolve through
  `prompt_registry.effective_model`** — the single model resolver. New
  prompt usages must add a `PROMPT_REGISTRY` entry
  (`tooling/verify/checks/prompt_registry.py` enforces).
- **`prompt_template.model` is written ONLY via
  `PATCH /api/prompts/{id}/model`,** validated fail-closed against the live
  Ollama tag list (503 when Ollama is unreachable, 422 when the name is
  absent; NULL always accepted with no ping). Seeded rows stay NULL — the
  `WORLD_ENGINE_OLLAMA_MODEL` env override must keep showing through
  NULL-model templates. `GET /api/ollama/models` is a thin `ping()`
  wrapper: explicit 503 on failure, never an empty-list masquerade.
  (`tooling/verify/checks/prompt_model_write.py` enforces.)
- **`_npc_dialogue_system_prompt(system_prompt, context)` in `cockpit/play.py`
  is the single npc_dialogue system-prompt construction:** every live call
  site and the Prompts tab's assembled preview call it — never a duplicated
  inline concatenation.
- **Prompt text lives ONLY in the append-only `prompt_version` table**
  (`prompt_template` is a head/identity row); "current" = `MAX(version_number)`
  per head, no pointer column, no UPDATE/DELETE ever on `prompt_version`.
  **`prompt_store.current_prompt`/`get_version`/`list_versions` is the sole
  read path; `writes.write_prompt_version` is the sole write path**
  (`PATCH /api/prompts/{id}/text`, the restore route, and the seed's
  virgin-head path all route through it) — C1 fail-closed placeholder
  validation on every write, restore included. The seed never touches text
  once a head has any version (S2) — creator edits are never silently
  superseded by a re-seed. One substitution mechanic repo-wide: every
  call site uses chained `.replace()`, never `.format()` (H1).
  (`tooling/verify/checks/prompt_version.py` enforces.)
- Affinity tiers are resolved in code (`context.py::_affinity_tier`); prompt templates never carry the tier table.
- **UI-visible data never lives in JSON** — relational only; enforced
  fail-closed by `json_ui_boundary` (exceptions justified in that file).
- **The app refuses to boot when `schema_meta.static_version` != `EXPECTED_STATIC_SCHEMA_VERSION`** (fail-closed, `cockpit/app.py` startup); `schema_meta` is migration-only infra, never canon, never writable outside a migration script.

## Local model notes

Default game model for NPC dialogue and analysis:
**`huihui_ai/qwen3-abliterated:8b-v2`** via Ollama; authoring model:
`llama3.1:8b`. Per-template overrides exist (`prompt_template.model`,
cockpit Prompts tab, live dropdown from `GET /api/ollama/models`); NULL
resolves to the registry's `default_model` at read time, so env overrides
show through. `prompt_registry.effective_model` is the sole resolver.

- **Abliterated** = refusal mechanisms removed; maximally compliant,
  including to a player pushing for reveals. This makes it the strictest
  test of concealed knowledge: if secrets hold here, they hold anywhere.
  The creator checkpoint remains the real safety net.
- **Thinking mode:** Qwen3 emits `<think>...</think>` before answering;
  `ollama_client.strip_think()` handles all malformed variants. Policies by
  call site:
  - **NPC dialogue** (`talk.py`): `/no_think` in the user message.
  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` +
    `_StreamThinkFilter`; thinking on, filtered before any token is
    yielded; reply buffered, never raw to the player.
  - **MJ narration** (`/say`, MJ phase): `chat_stream` + `/no_think` +
    filter as backstop; narration prose only streams to the player.
  - **MJ interpretation** (`/say`, phase 0): `chat()` + `/no_think` +
    `format="json"`; fallback to `dialogue` on any error — a
    misclassification must never break a turn.
  - **MJ arbitration** (`/say`, physical turns): `chat()` +
    `format="json"` + `/no_think`; falls back to
    `("physical", None, None, False)` on any failure.
  - **NPC initiative vote:** `chat()` + `format="json"` + `/no_think`;
    failure is silent.
  - **NPC initiative act:** `chat()` + `format="json"`, **no** `/no_think`
    (thinking helps the two-field contract `act_text`/`move`); falls back
    to `_NPC_INITIATIVE_ACT_FALLBACK` if the template isn't seeded; any
    error -> silent skip.
  - **Conversation analysis** (`analyzer.py`): thinking enabled;
    `strip_think` before JSON parsing.
- **French quality:** multilingual but not idiomatic-Mistral-grade;
  acceptable for validating logic. If narrative quality disappoints, that's
  a model-selection signal, not a code defect.

## Conventions

### File structure

One line per file: its role. History lives in the decision registry and the
schema changelog, never in this tree.

```
WG-Nia/
├── .claude/                 # Claude Code session config
│   ├── commands/            # /pipeline /recon /brief-exec /verify /review-step /close-step
│   ├── hooks/               # session-start, block-main-push, block-db-in-git (PowerShell)
│   ├── skills/              # recon, brief, verify-authoring skills
│   └── settings.json        # permissions allowlist
├── src/world_engine/        # the importable package (PYTHONPATH=src)
│   ├── db.py                # engine + session; URL from env var
│   ├── schema_version.py    # code-side expected-version constant for the static schema, checked at cockpit boot
│   ├── models/               # all SQLModel table classes (the schema), split by canon/canon_faction/ephemeral/pipeline stratum; models/__init__.py re-exports the whole surface
│   ├── context.py           # NPC + MJ context assembly; structural exclusions; signposts
│   ├── tick*.py             # world-tick: tick.py orchestrates, tick_context.py assembles, tick_normalize.py normalizes; call sites allowlisted by verify/checks/world_tick.py
│   ├── gathering.py         # initial NPC clustering into gatherings
│   ├── ollama_client.py     # local Ollama HTTP client; think-stripping; ping()
│   ├── analyzer.py          # window + overhearing analysis -> proposed_mutation rows
│   ├── resolution.py        # physical-action dice resolution (2d6 bands)
│   ├── ledger.py            # ledger read helpers
│   ├── writes/               # shared canon-write helpers, split by canon domain; writes/__init__.py re-exports the whole surface; schema.py is the third structural-write authority (governed runtime-DDL writer for ext_* tables)
│   ├── prompt_registry.py   # prompt wiring registry; effective_model resolver
│   ├── prompt_store.py      # prompt_version read accessor (current_prompt et al.)
│   ├── entity_author.py     # AI authoring assistant (entities, PC, skill catalogue, agendas, events)
│   ├── region_author.py     # region generation orchestrator (proposes names, no canon)
│   ├── spatial_author.py    # Creation-side door materialization from live connects_to (TICKET-0039)
│   ├── room_batch_author.py # Room batch orchestrator: Phase A manifest, Phase B fiches, Phase C coherence edges (TICKET-0042)
│   └── cockpit/             # creator web UI (FastAPI + HTMX, port 8000, loopback)
│       ├── app.py           # app factory + router mounting + fail-closed schema-version boot guard + link-batch retention purge (startup); routes/ holds the routers
│       ├── play*.py         # say() decomposition: routing, physical branch, narration/initiative
│       ├── crud/            # creator CRUD routes, split by domain (entities, relations, ...)
│       ├── index.html       # single-page UI; CREATION_TABS registry + dispatcher
│       └── vendor/          # vendored JS deps (cytoscape-*.min.js); one whitelisted GET route
├── scripts/
│   ├── init_db.py           # create tables + indexes (idempotent)
│   ├── seed_pilot.py        # seed Verkhaal world + prompt templates (idempotent)
│   ├── talk.py              # CLI conversation with an NPC
│   ├── analyze_conversation.py  # manual window analysis of a conversation
│   ├── cockpit.py           # launch the world cockpit
│   ├── pipeline_cockpit.py  # launch the pipeline cockpit (port 8100; deposit dormant)
│   ├── backup.py            # manual DB backup, 2-file rotation
│   └── migrate_*.py         # one idempotent migration per schema step
├── tooling/
│   ├── tickets/, recon/, briefs/  # pipeline artifacts (filename is law)
│   ├── questions/           # pipeline escalations awaiting Nia
│   ├── glue/                # next_id.py, gen_decisions_index.py, question_response.py
│   ├── standards/           # ARCHITECTURE_DECISIONS.md, DECISIONS_INDEX.md (generated), code_standards.md
│   ├── verify/              # run.py, checks/, baselines/, results/
│   ├── improvement/         # bug_log.jsonl
│   └── pipeline_cockpit/    # deposit UI app (dormant; never imports src/world_engine/)
├── world-engine-schema.md   # single authoritative schema; header = current version
├── world-engine-schema-changelog.md  # append-only schema log
├── CHANGELOG.md             # project changelog
├── CLAUDE.md                # this file (contract-checked)
├── pyproject.toml           # src-layout package metadata
├── requirements.txt
└── .env.example
```

### Naming

- **Tables:** every model sets `__tablename__` explicitly to the exact
  schema name (`pass_play`, `conversation_message`, `proposed_mutation`, …).
  Class names are PascalCase (`PassPlay`, `ConversationMessage`).
- **Primary keys:** TEXT/UUID strings. Top-level tables auto-generate via a
  `_uuid()` `default_factory`; entity-extension tables (`character`,
  `location`, `faction`, `artifact`) take their PK as the `entity.id`
  foreign key.

### Schema fidelity rules

- DB-level `DEFAULT` clauses are preserved with `server_default` so the
  generated DDL matches the schema; Python-side defaults keep the ORM
  ergonomic.
- Columns that carry a default are also `NOT NULL` — a deliberate
  strengthening over the literal SQL.
- JSON columns use SQLAlchemy `JSON` (becomes `JSONB` on PostgreSQL).
- Foreign keys are declared on every column the schema references; SQLite
  FK enforcement is on via a `PRAGMA foreign_keys=ON` connect listener.

### How to run / test

- **Install:** `python -m venv .venv`, activate, `pip install -r requirements.txt`.
- **Database URL:** from `WORLD_ENGINE_DATABASE_URL` (defaults to
  `~/.world_engine/world_engine.db`, outside the git working tree).
  Switching to PostgreSQL/Supabase changes only this variable, never code.
- **Initialize:** `python scripts/init_db.py` — idempotent.
- **Seed:** `python scripts/seed_pilot.py` — Verkhaal world, NPCs,
  relations, knowledge, prompt templates; idempotent; `upsert_prompt_template`
  writes prompt text (`prompt_version` v1) only on a virgin head — re-running
  never touches text once a version exists (S2), and still converges
  non-text head fields (name, variables, destination, notes, is_active)
  without losing other data.
- **Backup:** `python scripts/backup.py` — manual, SQLite online backup API, 2-file rotation to `~/.world_engine/backups/`.
- **CLI conversation:** `python scripts/talk.py` (requires `ollama serve`).
- **Analyze a conversation:**
  `python scripts/analyze_conversation.py <conversation_id>` — reads
  unanalyzed turns, writes `proposed_mutation` rows
  (`proposed_by='local_ai_window'`), advances `last_analyzed_turn`
  atomically. `--force` deletes *proposed* rows only, resets the cursor,
  re-analyzes the full transcript (reviewed rows are never deleted).
- **World cockpit:** `python scripts/cockpit.py` -> http://127.0.0.1:8000,
  loopback only; requires Ollama for all AI calls. Per turn: NPC reply is
  generated internally (buffered), MJ narration streams to the player; both
  persist (`speaker='npc'` canonical, `speaker='mj'` presentation); the raw
  NPC line shows as a muted creator-audit annotation. Overhearing proposals
  (`proposed_by='local_ai_overhearing'`) accumulate silently on `dialogue`
  turns; no other `proposed_mutation` writes during a turn. Window analysis
  fires automatically at scene boundaries (conversation close, player
  leaving, gathering dissolution) or manually via **Analyze**; **Force** is
  the debug path described above. Review proposals individually or via
  checkbox batch (**Approve/Reject selected**,
  `POST /api/mutations/batch-review`) — sequential, per row, through the
  same `_apply_mutation`/unit-reject paths; stale rows are skipped.
  **Voyager** (`POST /api/travel`) moves the player cleanly: window
  analysis on, then close of, the open conversation and gathering
  membership, then `current_location_id` update.
- **Pipeline cockpit:** `python scripts/pipeline_cockpit.py` -> port 8100. Deposit flow dormant; artifacts are deposited manually.
- **Verify:** `python tooling/verify/run.py` (or `/verify`) runs every check under `tooling/verify/checks/`.

---

*Co-built with Claude, June 2026.*
