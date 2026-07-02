# World Engine — Project Instructions

## What this is

A local, single-player-first engine for running a persistent RPG world. A creator keeps structural control over how the world evolves. Two modes of play feed the same world: asynchronous **pass-plays** and real-time **live sessions** (a player enters a location, sees the NPCs present, talks to them, learns things, builds relationships).

Full context lives in:
- `world-engine-schema.md` — the authoritative database schema.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — the design decisions and the v1 scope.

Read both before making any structural change.

## Stack

- **Language:** Python
- **Web:** FastAPI
- **ORM / DB:** SQLModel over SQLite (Supabase/PostgreSQL-compatible later)
- **UI:** two modes — server-rendered HTML with HTMX for the player-facing app
  (not yet built); single-page HTML + vanilla `fetch()` for the creator cockpit
  (no framework, no CDN, no build step, works fully offline).
- **Local models:** Ollama. Current target model: `huihui_ai/qwen3-abliterated:8b-v2` (see Local model notes below).

## Working rules

- Work in small, scoped steps. Do **only** what the current task asks. Do not anticipate or build future steps unprompted — if a next step seems useful, suggest it and stop.
- The database schema is authoritative. Match `world-engine-schema.md` exactly: same tables, columns, types, defaults, and foreign keys.
- **Creator control is structural.** Nothing mutates world state without passing through `proposed_mutation` and explicit creator approval. Dialogue is free; its consequences are not.
- **Injected context depends on the active role, never the account.** In player mode, never expose an NPC's secrets, others' secrets, or anything the player character is not meant to know.
- Keep the database engine URL in an environment variable (default to a local SQLite file) so switching to PostgreSQL/Supabase needs no code change.
- History is sacred: prefer preserving successive states over overwriting them.
- **`--force` only deletes `proposed` rows.** Any `proposed_mutation` row with
  status `applied`, `approved`, or `rejected` is reviewed history and must never
  be deleted — not by the CLI `--force` flag, not by the cockpit re-analyze
  endpoint. A forced re-analysis regenerates proposals alongside existing
  reviewed rows.
- **Language convention:** design conversation happens in French; all code,
  schema, comments, commit messages, and documentation are in English.
- **Step closure:** every closed step updates the schema changelog (if
  schema-touching) and keeps `tooling/standards/ARCHITECTURE_DECISIONS.md` and
  this file consistent with the code. Use the `/close-step` command.

## Ticket pipeline (governance)

- **Git (C1):** never push to `main`. Work on a `ticket/NNNN` branch and open
  a PR. Merge only after a green `/verify` AND Nia's live gate.
- **Danger classes (D1):** destructive_data | migration | permanent deletion
  -> human gate, no auto-merge (Nia decides). No automated backup exists;
  backup.py is a manual, deliberate step. db_write alone triggers nothing.
- **Escalate to Nia only on:** (a) an unspecified user-visible behavior
  change, (b) a destructive/irreversible data operation, (c) an architecture
  change above the ticket's stated `blast_radius`, (d) two consecutive
  `/verify` failures.
- **Model lanes (E1):** Opus for intake and escalated architecture
  decisions; Sonnet for RECON, execution, and verify. `/model opusplan` =
  plan on Opus, execute on Sonnet.
- **Protocol gate:** RECON before every brief (report-only, never acts on a
  finding); briefs are English, `BRIEF-NN`, Nia assigns the number; every
  commit touching the engine runs `/review-step` then `/close-step`; a
  ticket ends with `/verify`. Schema versions are computed, never chosen: on
  any schema-touching step closure, new version = the `Current schema
  version:` line in `world-engine-schema.md`, minor + 1 (v1.66 -> v1.67).
  That header line is the single source for the current number; the
  append-only log lives in `world-engine-schema-changelog.md` (repo root).
  If the minor part reaches 99, stop and escalate (D1-c).
- **Where things live:** `tooling/tickets`, `tooling/recon`, `tooling/briefs`,
  `tooling/verify/checks`, `tooling/standards`
  (`ARCHITECTURE_DECISIONS.md`, `world-engine-schema-changelog.md` (repo root), `code_standards.md`),
  `tooling/improvement/bug_log.jsonl`.
- This section governs the ticket pipeline itself (process, gating,
  escalation). It does not replace or relax any invariant below — those
  still apply to every change regardless of how it was ticketed.

## Invariants (verified at every review)

- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
  gathering. The invariant is per-NPC, NOT per-location (multiple open
  gatherings in one location are legal). Defended on every join/migrate path.
- **Dissolve-before-create lives in the caller** (`enter_location`), never
  inside `generate_gatherings` — preserves the multiplayer upgrade path.
- **`relation_change` is owned by window analysis** (`analyze_window`,
  `proposed_by='local_ai_window'`): the `pt-conversation-analysis` v3
  anti-inflation rubric targets at most one `relation_change` per NPC pair
  per window, proportionate to what happened in that window. Not covered by
  `_mutation_match_key` — each window's deltas are independent, never
  deduplicated against prior windows.
- **`new_knowledge` / `status_change` are idempotent facts:** identity-based
  dedup (`entity_id` + `subject`; `entity_id`) via `_mutation_match_key`,
  same conversation required.
- **Secrets are structurally excluded** from every assembled context — never
  "guarded by instruction". `character.secrets` is creator meta-narrative
  (notes ABOUT the character: true nature, planned arcs) and is NEVER read
  by any context assembler. What an NPC knows-but-conceals lives in
  `knowledge` rows with `is_secret = TRUE`, excluded by the assembler. This
  exclusion extends to every propagation path, not just context assembly:
  `analyze_overhearing` (Tier 4) never sources a proposal from a
  `knowledge` row with `is_secret = TRUE`.
- **`relation_change`'s `entity_a_id`/`entity_b_id` come from the model's
  payload.** If either is missing, the item is skipped and logged
  (`_normalize_to_schema` returns `None`) — never attributed via a
  conversation-level default. Per-item resolution against the gathering
  roster is deferred (see "Deferred decisions" in `tooling/standards/ARCHITECTURE_DECISIONS.md`).
- **Two sanctioned canon-write paths, no others:** `_apply_mutation` (AI
  proposals, after creator approval) and the creator CRUD (direct creator
  authority). No code path may ever write canon in response to an AI
  proposal outside `_apply_mutation`. The AI entity-authoring assistant's
  `POST /api/entities/generate` (BRIEF-24) is explicitly NOT one of these
  two paths — it writes no canon; the creator's accept reuses the creator
  CRUD path unchanged.
- **History is sacred on BOTH write paths:** any edit to `relation` or
  `knowledge` (either write path — `_apply_mutation` or creator CRUD)
  appends the previous state to `change_history`; states are preserved,
  never silently overwritten.
- **Commit before touching any canon-writing path** (`_apply_mutation`, the
  creator CRUD, the analyzers, and everything they call) — a hard invariant.
  Recommended (not hard): also commit before touching the `/say` flow or the
  interpretation phase — playability-critical. (Between BRIEF-07 and
  BRIEF-08/D2a.1, the interpretation phase was itself a mutation producer via
  auto-applied `item_update`; that producer is now removed, but the
  recommendation stands on playability alone.)
- **The MJ context assembler is scoped to the player's perception
  boundary:** only what the player may perceive (current location, public
  co-presents, public/confirmed events) or already knows (the player
  character's own knowledge). Never NPC-private knowledge, secrets,
  internal names, non-public entities, or invisible relations. Enforced
  by query construction, never by instruction.
- **Knowledge levels never decrease through the mutation pipeline:** the
  ladder `unaware < rumor < suspicious < partial < knows <
  fully_understands` is monotone for every `knowledge_change` apply
  (`_apply_mutation`'s "level already >= proposed" guard). At detection,
  `analyze_overhearing` additionally caps the acquired/upgraded level at
  `knows` in code (`_KNOWLEDGE_LEVEL_DOWNGRADE`); `analyze_window` applies no
  such ceiling — a model-proposed `knowledge_change` is bounded only by the
  monotonicity guard and creator approval, not a structural cap (see
  "Deferred decisions" in `tooling/standards/ARCHITECTURE_DECISIONS.md`). Downgrades,
  forgetting, and `is_incorrect` correction remain creator CRUD only.
- **`scene_state` is a third, explicitly ephemeral write path** (BRIEF-12).
  `_write_scene_state` archives the previous state snapshot to `history[]`
  before every write — history is sacred even for ephemeral state. `scene_state`
  is cleared to `{}` when a conversation closes. It is never canon: durable
  consequences require a `proposed_mutation`.
- **`proposed_by='engine'`** (BRIEF-12/13): deterministic engine proposals —
  `_propose_engine_injury` (injury on `injured`/`neutralized`) and
  `_propose_engine_discovery` (discovery on a successful perception search).
  Both follow the same review queue as AI proposals — never auto-applied.
- **Constraint gating is structural, not instructional** (BRIEF-12): gagged /
  restrained / blindfolded effects are enforced in Python before any model call
  (`_stream` in `app.py`). Blindfolded exclusion is a data exclusion in the
  context assembler (`assemble_mj_context`), never a "don't describe" prompt.
- **Condition ladder is monotone for engine writes** (BRIEF-12): `unharmed →
  bruised → injured → neutralized` — only moved forward by violent-verdict
  code; only moved backward by creator CRUD. Never decremented by the engine.
- **Frozen scene yields no model calls** (BRIEF-12): when `scene_state.frozen
  = True`, `/say` short-circuits with a fixed MJ message. No model is invoked.
  Only the creator panel can set `frozen=False`.
- **`discoverable_detail` is structurally excluded from every assembler, with
  one consciously narrowed exception** (BRIEF-13, narrowed BRIEF-17):
  `assemble_mj_context`, `assemble_npc_context`, and all prompt-building paths
  never read this table. `hidden` content is absent from every prompt by data
  exclusion, not instruction — it reaches a model ONLY via the post-selection
  `{detail_content}` injection in `_stream()` on a partial/success perception
  search (`domain="perception"`, `opposed_npc_id=None`). `ambient` content
  (the signpost layer, schema v1.30) IS read, but only via the pure code
  predicate `active_signposts` (context.py) — never through an assembler,
  never a `subject`/`signpost_group`, only the surviving `content` strings,
  passed directly into the MJ establishment call (`enter_scene`).
  `subculture["hidden"]` is a TRAP — do not add it to `_SAFE_SUBCULTURE_KEYS`
  or use it as discoverable content; discoverable content lives ONLY in
  `discoverable_detail`.
- **`connects_to` is location map topology, never a social/relational signal**
  (BRIEF-15, schema v1.28): its `intensity=50` is a meaningless structural
  default. No world-wide relation scan may treat it as one. Every gameplay
  reader of `relation` that is keyed on a character/player id is structurally
  blind to `connects_to` rows (which have two location endpoints). The sole
  intentional gameplay reader of `connects_to` is `_location_neighbours`
  (BRIEF-16), which reads it for topology, not social signal. Any new
  world-wide relation scan added to the codebase MUST explicitly exclude
  `type='connects_to'`.
- **The `ledger` is append-only** (BRIEF-18, schema v1.31). INSERT-only on
  both sanctioned canon-write paths; a mistake is corrected by a new
  compensating line, never by editing or deleting an existing row. No
  UPDATE/DELETE endpoint or code path may touch a `ledger` row.
- **`resource_change` writes two canon tables** (`ledger` + optional
  `knowledge`) inside one `_apply_mutation` SAVEPOINT — the single sanctioned
  exception to one-branch-one-table, justified by atomicity (BRIEF-19, schema
  v1.32). Its money leg accumulates (never deduped, like `relation_change`);
  its knowledge leg is idempotent and guarded only at apply time (block-whole
  → Needs attention). The money leg targets the player only (A1) until
  tracked NPC purses are introduced.
- **`entity.metadata.price_list` is seller configuration** (BRIEF-20, schema
  v1.33), injected ONLY into that seller's own dialogue context — never into
  `assemble_mj_context` (player perception) or any other entity's context. A
  quoted price is free dialogue and writes no canon; the money movement is a
  `resource_change` through the checkpoint. Catalogue prices are firm and
  universal; only uncatalogued quotes are relation-modulated.
- **Membership reaches a model prompt only via `read_public_memberships`**
  (BRIEF-29, no schema change); `is_secret` rows never enter any prompt,
  including the holder's own. The filter is structural (`is_secret = FALSE`
  in the query), not instructional, with no parameter to override it.
  Espionage rides on `goals` prose, never a confessable affiliation label.
  The true `role` behind a `cover_role` never enters any prompt either
  (BRIEF-30, schema v1.41): `read_public_memberships` resolves
  `cover_role ?? role`, so a double agent's true role stays creator-only
  while the façade is what every prompt reader — own-context today, any
  future third-party reader — actually sees.
- **Creator-direct create helpers never commit in their core; the commit
  boundary belongs to the caller** (BRIEF-35, no schema change).
  `create_entity`, `create_knowledge`, and `open_entity_membership`
  (`cockpit/crud.py`) each split into a commit-free core (does the write up
  to `db.add`/`db.flush()`, never `db.commit()`/`db.refresh()`, returns the
  ORM row) plus a thin route wrapper owning the single commit. The seam is
  structural, not a `commit:` flag — a batch caller (e.g. a future region
  commit) calls the cores directly against a shared session and commits or
  rolls back once for the whole batch.
- **Region generation writes no canon; commit is atomic; curation and link
  resolution are server-authoritative.** The full region path (chantiers
  1-3, BRIEF-34/35/36/37) is closed end-to-end. `region_author.py`'s
  `generate_region_draft` only ever proposes names — no entity, relation, or
  membership row is written anywhere in its call path. `POST
  /api/regions/commit` (`commit_region` in `cockpit/app.py`) is the single
  write point: entities + the structural skeleton (`parent_location_id`,
  primary public `faction_membership`, `current_location_id`) + the
  creator-confirmed judgment links (`sensed_links` kind=`connection` ->
  `connects_to`, kind=`faction` -> `controls` faction->location
  `direction="a_to_b"`) all commit in **one transaction, all-or-nothing**
  via the commit-free cores (`_create_entity_core`, `_create_knowledge_core`)
  and `write_relation` — any failure rolls back the whole batch. The model
  only ever proposes names; the creator confirms (entity accept/reject,
  link confirm/discard); the code resolves names to ids and wires — no
  model-emitted id ever reaches a canon row. Resolution is
  server-authoritative throughout: the accept/reject cascade and the
  confirmed-link target lookup are both re-derived from raw untrusted
  client state, never trusted from the client's rendering, and a
  rejected/uncommitted/unresolved/self-referential target writes nothing
  rather than a dangling or wrong-typed reference.
- **PC knowledge is written `is_secret=False`; `_normalize_knowledge` is
  NPC-only and forces `is_secret=True` — never reuse it for a PC**
  (BRIEF-52, schema v1.60). A PC's own knowledge is never secret from the
  player who *is* that knowledge — the opposite default from an NPC's. The
  PC creation assistant (`entity_author.generate_player_draft`) normalizes
  its `knowledge[]` with a dedicated `_normalize_player_knowledge` helper
  that emits no `is_secret` key at all; `is_secret=False` is applied at
  write time by the accept route (`create_player_character`, via
  `writes.write_knowledge`), never by the generator.
- **A PC is excluded from NPC co-presence by a `character_type` filter, by
  construction** (BRIEF-52 H1, schema v1.60). The `H_COMPANY` query inside
  `assemble_npc_context` (`context.py`) carries
  `Character.character_type != "player"` — a PC's `appearance`/
  `description` can never reach an NPC's "AVEC QUI TU TE TROUVES" list
  through this query, regardless of whether a caller correctly passes the
  player as `interlocutor_id`. Do not widen this filter, and do not repoint
  it at a future Tier-3 NPC-to-NPC observation feature without a deliberate
  decision — an onlooking PC's representation to NPCs there is a separate
  question, decided via a dedicated path reading `description`, not this
  `appearance`-first co-presence default.
- **Creator-CRUD edits that change a character's `current_location_id`, or set
  an entity's `status` to a non-active value, MUST close that entity's open
  `gathering_member` rows via `close_open_memberships` (gatherings are not
  canon — no `_apply_mutation`, no `change_history`). Roster and co-present
  reads (`_active_members`, `assemble_npc_context` H_COMPANY,
  `assemble_mj_context` co-presents) gate on `entity.status='active' AND
  vital_status='alive'` in addition to `gathering_member.left_at IS NULL`.
- World block deletion (delete_world_cascade) is the broadest sanctioned hard-delete of canon and the original exception to "History is sacred" — it removes every row scoped to a world, the world row included. `skill_definition` deletion (BRIEF-56, see below) is a second, narrower named exception, scoped to one definition and its dependent `skill` rows only. No other delete-side helper exists; any new hard-delete path must be named here, not added silently.
- **Custom skill lookups filter `skill_definition_id`, by construction**
  (BRIEF-55, schema v1.63). A base-domain `skill` row lookup MUST include
  `AND skill_definition_id IS NULL` (e.g. `app.py`'s arbiter resolution) so
  it never accidentally hits a custom-skill row sharing the same `domain`
  string. A custom skill resolves via its `skill_definition.base_domain` —
  never its own `domain` column treated as a fifth base domain — and that
  resolved `base_domain` is what every base-domain-keyed downstream branch
  (2d6 bands, the perception-discovery gate) keys off, not the raw
  arbiter-returned name. `skill_definition` and custom `skill` rows are
  PC-only and MJ-narration-only this phase: no NPC-side read, no NPC
  dialogue injection (deferred to a future decision, not built).
- **A `skill_definition` delete always succeeds and is never blocked by
  `ON DELETE RESTRICT`; it carries no `change_history` snapshot of the
  deletion** (BRIEF-56, no schema change — D2-delete-cascade, locked
  decision). `DELETE /api/skill-definitions/{id}` (`cockpit/crud.py`)
  deletes every dependent PC `skill` row, then the definition, in one
  transaction. The creator-side type-"Oui" confirmation modal is the sole
  safeguard — the same idiom and the same deliberate exception to "History
  is sacred" as world block deletion, scoped to one row instead of a whole
  world.
- **A new `skill_definition` backfills a tier-0 `skill` row onto every
  existing player character of its world, in the same transaction as the
  create** (BRIEF-56, no schema change — D2-backfill-yes, locked decision).
  `POST /api/skill-definitions` (`cockpit/crud.py`) never leaves the
  catalogue<->PC alignment partial — every PC always has every world skill,
  the invariant the arbiter's `skill_definition_id`-keyed lookup depends on
  being total. Renaming a `skill_definition` touches no `skill` row
  (FK-by-id); re-basing one (`base_domain` change) updates the `domain`
  column on every dependent `skill` row in the same write, so the 2d6 band
  lookup and the `domain` CHECK stay consistent.
- **A `skill_definition.name` can never equal a base-domain literal**
  (BRIEF-56, no schema change — closes the named risk from BRIEF-55/schema
  v1.63). Both write paths — the creator-CRUD `POST`/`PUT
  /api/skill-definitions` and `entity_author.generate_skill_catalogue_draft`'s
  `_normalize_skill_catalogue` — reject/drop a name that case-insensitively
  matches `physical`/`agility`/`perception`/`composure`, so the arbiter's
  `world_skill_defs_by_name.get(domain)` lookup can never be shadowed by a
  custom row claiming a base-domain name.

## Local model notes

Target local model for NPC dialogue and analysis: **`huihui_ai/qwen3-abliterated:8b-v2`**, run via Ollama. Relevant when wiring the model (not before — context assembly is model-agnostic):

- **Abliterated** = refusal mechanisms removed. Will not refuse, and is generally more compliant to *any* instruction — including a player pushing it to reveal. This makes it the strictest possible test of the "concealed knowledge / under guard" mechanism: if secrets hold here, they hold anywhere. The creator checkpoint remains the real safety net regardless.
- **Thinking mode:** Qwen3 emits a `<think>...</think>` reasoning block before its answer. `ollama_client.strip_think()` handles this robustly (complete block, unclosed tag, orphan closing tag). Three policies apply depending on the call site:
  - **NPC dialogue** (`talk.py` CLI): disable thinking with `/no_think` in the user message — deterministic, faster, and the reasoning block must never reach the player.
  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` with the built-in `_StreamThinkFilter` — thinking is left enabled, the filter suppresses the block before any token is yielded. The NPC reply is buffered internally; the player never sees it raw.
  - **MJ narration** (cockpit `/say`, MJ phase): `chat_stream` + `/no_think` appended to the user message — same filter as a backstop, `/no_think` for speed. What streams to the player is narration prose only.
  - **MJ interpretation** (cockpit `/say`, phase 0): `chat()` non-streaming + `/no_think` + `format="json"`. Classifies the player's input into `dialogue` / `physical` / `npc_reaction` / `scene` / `join` / `travel`. Fallback to `dialogue` on any error — a misclassification must never break a turn.
  - **MJ arbitration** (cockpit `/say`, physical turns only — between phase 0 and the NPC phase): `chat()` non-streaming + `format="json"` + `/no_think` appended at call time. Classifies domain + optional NPC opposition + constraint + violent flag; falls back to `("physical", None, None, False)` on any failure — a misclassification must never break a turn.
  - **NPC initiative vote** (cockpit `/say`, Tier 3 C1): `chat()` non-streaming + `format="json"` + `/no_think` — same policy as MJ interpretation. Failure is silent (initiative simply doesn't fire).
  - **NPC initiative act** (cockpit `/say`, Tier 3 C2): `chat()` non-streaming + `format="json"`, **no** `/no_think` — the JSON schema already constrains output, and leaving thinking on helps the small model follow the two-field contract (`act_text`, `move`). Falls back to `_NPC_INITIATIVE_ACT_FALLBACK` if `pt-npc-initiative-act` isn't seeded; any error → silent skip.
  - **Conversation analysis** (`analyze_conversation.py`, `analyzer.py`): leave thinking enabled — the reasoning helps the model follow format instructions; `strip_think` removes the block before JSON parsing.
- **French quality:** multilingual but not Mistral-grade idiomatic French. Acceptable for validating logic; if narrative quality disappoints, that's a model-selection signal, not a code defect.

## Conventions

### File structure

```
World-genrator/
├── src/
│   └── world_engine/        # the importable package
│       ├── __init__.py
│       ├── db.py            # engine + session; URL from env var
│       ├── models.py        # all SQLModel table classes (the schema)
│       ├── context.py       # NPC context assembly (secret-exclusion + relation-gating;
│       │                    #   gathering co-presence injection, contract D1);
│       │                    #   H1 co-presence hardening (BRIEF-52, schema
│       │                    #   v1.60): the H_COMPANY query inside
│       │                    #   assemble_npc_context gained
│       │                    #   Character.character_type != "player" —
│       │                    #   excludes a PC from any NPC's co-presence list
│       │                    #   by construction, not by interlocutor_id
│       │                    #   convention; no-op today, every existing
│       │                    #   call site already excludes the player there;
│       │                    #   MJ context assembler (assemble_mj_context,
│       │                    #   format_mj_context — player's perception
│       │                    #   boundary, scope D-b3);
│       │                    #   format_inventory_line — player's static
│       │                    #   inventory line, read fresh per turn (BRIEF-06,
│       │                    #   schema v1.18; equip split dropped, BRIEF-08/
│       │                    #   D2a.1);
│       │                    #   format_item_list_for_interpretation — player's
│       │                    #   items for {item_list}, fed to pt-mj-interpretation
│       │                    #   (BRIEF-07, schema v1.19; delegates to
│       │                    #   format_inventory_line since BRIEF-08/D2a.1);
│       │                    #   active_signposts — signpost layer silence
│       │                    #   predicate (BRIEF-17, schema v1.30): pure
│       │                    #   DB-read, sibling to assemble_mj_context, never
│       │                    #   called from inside it; returns only surviving
│       │                    #   ambient `content` strings (E1 cluster rule);
│       │                    #   seller tariffs (BRIEF-20, schema v1.33):
│       │                    #   assemble_npc_context injects a verbatim "TES
│       │                    #   TARIFS" block from the NPC's OWN
│       │                    #   metadata.price_list only, absent when empty —
│       │                    #   never read by assemble_mj_context or another
│       │                    #   entity's context;
│       │                    #   read_public_memberships (BRIEF-29, no schema
│       │                    #   change; cover-role resolution BRIEF-30,
│       │                    #   schema v1.41): the single structural choke-
│       │                    #   point for faction_membership reaching any
│       │                    #   prompt — is_secret = FALSE enforced in the
│       │                    #   query, no override param, AND the returned
│       │                    #   role is always cover_role ?? role (the true
│       │                    #   role behind a cover never crosses this
│       │                    #   boundary); assemble_npc_context injects
│       │                    #   its result as a "TES AFFILIATIONS" block (own
│       │                    #   public/active memberships only, primary
│       │                    #   first), placed just before TES TARIFS, absent
│       │                    #   when empty — no secret self-include, even for
│       │                    #   the holder's own membership;
│       │                    #   custom skill vocabulary (BRIEF-55, schema
│       │                    #   v1.63): assemble_mj_context/format_mj_context
│       │                    #   gained a "COMPÉTENCES PROPRES À CE MONDE"
│       │                    #   section — the active world's skill_definition
│       │                    #   names only (no description, no tier, no
│       │                    #   per-PC data), world-scoped at query
│       │                    #   construction, omitted entirely when empty;
│       │                    #   MJ narration only, never assemble_npc_context
│       ├── gathering.py     # initial NPC clustering (generate_gatherings,
│       │                    #   enter_location, contracts A2/B1/C1) + migrate_npc
│       │                    #   (idempotent NPC migration between gatherings,
│       │                    #   auto-dissolve emptied source — B1 repair);
│       │                    #   enter_location and migrate_npc's dissolve paths
│       │                    #   call analyze_window on each open conversation
│       │                    #   before dissolving (trigger c, BRIEF-09/v1.21)
│       ├── ollama_client.py # HTTP client for local Ollama; strips <think> blocks
│       ├── analyzer.py      # mutation analysis; _normalize_to_schema; _validate_item;
│       │                    # load_analysis_prompt (usage param, world-specific preferred);
│       │                    # _mutation_match_key (write-time dedup: new_knowledge on
│       │                    #   entity_id+subject, status_change on entity_id);
│       │                    # analyze_window (window analysis — reads unanalyzed
│       │                    #   turns past conversation.last_analyzed_turn, proposes
│       │                    #   all mutation types incl. relation_change, write-time
│       │                    #   dedup, advances last_analyzed_turn atomically,
│       │                    #   proposed_by='local_ai_window', BRIEF-09/v1.21);
│       │                    # analyze_overhearing (Tier 4, acquire or upgrade:
│       │                    #   gathering-roster receivers, closed-list subject
│       │                    #   classification, K2/secret/dedup guards,
│       │                    #   deterministic level-ladder downgrade for
│       │                    #   acquisition, knowledge_change for monotone
│       │                    #   upgrades (v1.17), proposed_by='local_ai_overhearing');
│       │                    # resource_change normalization (BRIEF-19, schema
│       │                    #   v1.32): two-leg payload (money + optional
│       │                    #   knowledge), entity_id defaults to conv.player_id
│       │                    #   (A1), dropped (skip+log) if entity_id or amount
│       │                    #   can't be resolved — same discipline as
│       │                    #   relation_change; excluded from
│       │                    #   _mutation_match_key (money leg accumulates);
│       │                    # player-detection de-hardcoded (BRIEF-45, no schema
│       │                    #   change): _normalize_to_schema's new_knowledge
│       │                    #   player_hints set drops the literal "char-player"
│       │                    #   in favour of _resolve_player_id(db, conv.world_id)
│       │                    #   (character_type='player' scoped to conv's world)
│       ├── resolution.py    # physical-action dice resolution (BRIEF-11, schema
│       │                    #   v1.23): pure 2d6 + tier, no DB/model access;
│       │                    #   Verdict {domain, dice, modifier, total, band};
│       │                    #   resolve_physical(domain, player_tier, npc_tier=0)
│       │                    #   — bands <=6 failure, 7-9 partial, >=10 success;
│       │                    #   player-roll rule (verbatim in module docstring)
│       ├── ledger.py        # ledger read helpers (BRIEF-18, schema v1.31):
│       │                    #   get_balance (SUM(amount) per entity_id, no
│       │                    #   stored balance), list_entries (entity_id /
│       │                    #   session_id optional filters, newest first)
│       ├── entity_author.py # AI entity-authoring assistant (BRIEF-24/25/32,
│       │                    #   schema v1.36/v1.37/v1.43): generate_entity_draft(
│       │                    #   entity_type, brief, db) — writes no canon,
│       │                    #   ever; calls the local Ollama wrapper with
│       │                    #   model=AUTHOR_MODEL ("llama3.1:8b", a
│       │                    #   one-line-change constant, decision E1),
│       │                    #   format="json"; parses the public/secret
│       │                    #   two-block contract per entity_type and runs
│       │                    #   deterministic post-processing;
│       │                    #   "character": physical_tier clamp, knowledge
│       │                    #   level validation + forced is_secret=TRUE,
│       │                    #   case-insensitive faction_name resolution, no
│       │                    #   auto-create on a miss;
│       │                    #   "location" (BRIEF-25): location_type/
│       │                    #   access_level enum validation (access_level
│       │                    #   left blank, never defaulted permissive, on a
│       │                    #   miss); _filter_subculture_public — the B1
│       │                    #   intra-JSON public/secret segregation, reads
│       │                    #   the LIVE _SAFE_SUBCULTURE_KEYS constant
│       │                    #   (imported from context.py) so the public
│       │                    #   region can never include "hidden" or any
│       │                    #   other non-allow-listed key; secret.
│       │                    #   subculture_hidden is the ONLY path to
│       │                    #   subculture["hidden"]; sensed_links are
│       │                    #   display-only (no parent_location_id/
│       │                    #   connects_to/discoverable_detail write);
│       │                    #   magic_status never proposed; no knowledge
│       │                    #   rows generated for locations;
│       │                    #   "faction" (BRIEF-32): faction_type enum
│       │                    #   validation (falls back to "other"); roles
│       │                    #   normalization (_normalize_roles — ordered
│       │                    #   {name,description} list, nameless rows
│       │                    #   dropped with a note) lands in
│       │                    #   draft.public.roles for client-side
│       │                    #   population into entity.metadata['roles'];
│       │                    #   internal_tensions/goals passthrough to
│       │                    #   secret block (typed columns, no per-row
│       │                    #   store); magic_knowledge_level/scope/
│       │                    #   parent_faction_id never proposed;
│       │                    #   _TYPE_FIELDS is the config seam for entity
│       │                    #   types ("character", "location", "faction"
│       │                    #   populated; item/artifact not); never raises —
│       │                    #   returns {"ok": false, "error": ...} on any
│       │                    #   failure;
│       │                    #   generate_world_draft(brief, db) (BRIEF-47, no
│       │                    #   schema change): sibling propose function, NOT
│       │                    #   a _TYPE_FIELDS entry — World has no entity_id
│       │                    #   FK, never touches _create_entity_core; db is
│       │                    #   read-only (sole use: the pt-world-generation
│       │                    #   template lookup); prompts the model for
│       │                    #   fundamental_laws as a JSON array, then
│       │                    #   flattens it in Python to a numbered
│       │                    #   newline-joined string before returning —
│       │                    #   the draft's fundamental_laws is ALWAYS a flat
│       │                    #   str; returns the same {"ok","draft","notes"}
│       │                    #   envelope shape as generate_entity_draft, with
│       │                    #   draft = {"public": {"name","description",
│       │                    #   "fundamental_laws"}, "secret": {}};
│       │                    #   generate_player_draft(brief, db) (BRIEF-52,
│       │                    #   schema v1.60): standalone sibling, NOT a
│       │                    #   _TYPE_FIELDS entry — parses a SINGLE
│       │                    #   top-level JSON object {"name","description",
│       │                    #   "appearance","backstory","knowledge"}, no
│       │                    #   public/secret blocks (D1/G1); never calls
│       │                    #   _create_entity_core, emits no world_id/
│       │                    #   current_location_id/faction/entity_id
│       │                    #   (location stays creator-picked, C1); db is
│       │                    #   read-only (sole use: the pt-player-generation
│       │                    #   template lookup); knowledge normalized by
│       │                    #   _normalize_player_knowledge (NOT
│       │                    #   _normalize_knowledge, which forces
│       │                    #   is_secret=True — wrong for a PC) — emits no
│       │                    #   is_secret key at all, caps at 5 rows;
│       │                    #   generate_skill_catalogue_draft(brief, db)
│       │                    #   (BRIEF-56, no schema change): standalone
│       │                    #   sibling, NOT a _TYPE_FIELDS entry — parses a
│       │                    #   SINGLE top-level JSON object {"skills": [...]},
│       │                    #   each entry {"name","base_domain","description"};
│       │                    #   never emits a tier or a structural id; db is
│       │                    #   read-only (sole use: the pt-skill-catalogue
│       │                    #   template lookup); _normalize_skill_catalogue
│       │                    #   drops nameless rows, rows whose base_domain
│       │                    #   doesn't case-insensitively resolve against
│       │                    #   BASE_SKILL_DOMAINS, and rows whose name
│       │                    #   collides with a base-domain literal
│       ├── region_author.py # Region orchestrator, chantier 1 (BRIEF-34,
│       │                    #   schema v1.45), split into a two-phase
│       │                    #   creator checkpoint (BRIEF-38, schema v1.49):
│       │                    #   generate_region_manifest(brief, db) — Phase
│       │                    #   A, the Stage-0 model call via
│       │                    #   pt-region-manifest, usage='region_manifest',
│       │                    #   returns the manifest for the creator to edit
│       │                    #   one-liners on; generate_region_draft(manifest,
│       │                    #   db) — Phase B, re-runs _normalize_manifest on
│       │                    #   the re-sent manifest first (server-
│       │                    #   authoritative, client edit is advisory) then
│       │                    #   composes the existing generate_entity_draft
│       │                    #   across Factions → Locations (root first) →
│       │                    #   NPCs; writes no canon, ever, in either phase;
│       │                    #   each composite brief is built ONLY from the
│       │                    #   manifest's public one-liners — a drafted
│       │                    #   entity's own secret block is never read by
│       │                    #   this module, never fed into a downstream
│       │                    #   generation prompt; resolves the manifest's
│       │                    #   by-name relationships into draft-local id
│       │                    #   pointers (fac-N/loc-N/npc-N) WITHIN the
│       │                    #   returned tree only — no Entity lookup, no
│       │                    #   faction_membership/parent_location_id/
│       │                    #   relation row; a failed/empty manifest aborts
│       │                    #   the whole run, a failed per-entity
│       │                    #   sub-generation drops just that entity into
│       │                    #   region.skipped and the run continues;
│       │                    #   NPC top-up clamp (BRIEF-40, schema v1.51):
│       │                    #   generate_region_manifest, after parsing,
│       │                    #   computes the NPC shortfall against
│       │                    #   MIN_NPCS_PER_FACTION/MIN_FACTIONLESS (=4/=4,
│       │                    #   must stay in sync with the
│       │                    #   REGION_MANIFEST_SYSTEM_PROMPT prose floor)
│       │                    #   and, if short, issues ONE targeted re-prompt
│       │                    #   to AUTHOR_MODEL (pt-region-manifest-topup),
│       │                    #   merges + re-normalizes, then returns — one
│       │                    #   pass only, residual shortfall noted not
│       │                    #   retried; bounded add-only floor, amends K1
│       │                    #   (manifest is no longer the *sole* density
│       │                    #   determinant — see tooling/standards/ARCHITECTURE_DECISIONS.md);
│       │                    #   premise reader (BRIEF-44, schema v1.55):
│       │                    #   generate_region_manifest loads the active
│       │                    #   world (_active_world, local is_active==True
│       │                    #   query — not imported from cockpit.crud, to
│       │                    #   avoid a core-depends-on-UI-layer inversion)
│       │                    #   and renders world.description /
│       │                    #   fundamental_laws as two independently-
│       │                    #   optional labeled blocks ahead of {brief} in
│       │                    #   pt-region-manifest's user_template; each is
│       │                    #   "" when the corresponding field is empty, so
│       │                    #   a B1-style empty-premise world degrades to
│       │                    #   the original brief-only prompt; reads
│       │                    #   World.description/fundamental_laws — public
│       │                    #   world config, not a secret-accessor path;
│       │                    #   generate_region_draft renders no template
│       │                    #   (only composes entity_author prompts), so it
│       │                    #   needed no change
│       └── cockpit/         # creator review web UI (FastAPI sub-app)
│           ├── __init__.py
│           ├── app.py       # JSON endpoints + HTML route; _apply_mutation;
│           │                # world selection (BRIEF-43, schema v1.54):
│           │                #   GET /api/worlds (list, with is_active),
│           │                #   POST /api/worlds/{id}/activate (activate_world —
│           │                #   one transaction: deactivate all, flush, activate
│           │                #   target; 404 on unknown id; rollback + {"ok":false}
│           │                #   on any other failure); deliberately in app.py, not
│           │                #   crud.py — flips a selection flag, not narrative canon;
│           │                # World block deletion (BRIEF-54, schema v1.62):
│           │                #   DELETE /api/worlds/{world_id} (delete_world) — one
│           │                #   atomic transaction: 404 on unknown id; captures
│           │                #   was_active, then delete_world_cascade(world_id, db)
│           │                #   (writes.py — the sole sanctioned hard-delete of
│           │                #   canon, see CLAUDE.md Invariants); if no worlds
│           │                #   remain, commits and returns remaining=0,
│           │                #   active_world_id=None; if the deleted world was
│           │                #   active and survivors remain, re-activates the
│           │                #   most-recently-created survivor via
│           │                #   _activate_world_core (G1); otherwise the still-
│           │                #   active survivor is untouched; rollback +
│           │                #   {"ok":false} on any exception; deliberately in
│           │                #   app.py, not crud.py — same reasoning as the other
│           │                #   world routes, despite this one actually being
│           │                #   narrative-canon-shaped (the named exception);
│           │                #   _activate_world_core(world_id, db) (E1): commit-
│           │                #   free extraction of the existing deactivate-all →
│           │                #   flush → activate-one logic, used by the delete
│           │                #   route ONLY — activate_world/create_world keep
│           │                #   their own inline duplication (named deferral);
│           │                # generic world bootstrap (BRIEF-44, schema v1.55):
│           │                #   POST /api/worlds (WorldCreateBody — name +
│           │                #   optional description/fundamental_laws,
│           │                #   create_world) inserts one fresh-UUID World row
│           │                #   (default_factory _uuid, never pattern-matched
│           │                #   to "verkhaal") then auto-activates it by
│           │                #   reusing activate_world's deactivate-all-then-
│           │                #   activate-target logic in the SAME transaction,
│           │                #   one db.commit(); rollback + {"ok":false} on any
│           │                #   exception; deliberately in app.py, not crud.py,
│           │                #   same reasoning as the activate route; the
│           │                #   created world is empty by construction (the
│           │                #   route does only the one World insert);
│           │                # World-bible generator (BRIEF-47, no schema
│           │                #   change): POST /api/worlds/generate
│           │                #   (WorldGenerateBody — brief) delegates ONLY to
│           │                #   entity_author.generate_world_draft; writes
│           │                #   nothing; deliberately beside
│           │                #   POST /api/entities/generate, not in crud.py,
│           │                #   same no-canon-write reasoning;
│           │                # Création world scoping (BRIEF-48, no schema
│           │                #   change): list_mutations (GET /api/mutations, the
│           │                #   review-queue resolution — lives here, not crud.py)
│           │                #   gained `.where(ProposedMutation.world_id ==
│           │                #   _crud._world_id(db))`; proposed_mutation.world_id
│           │                #   already existed on the table, so this is a plain
│           │                #   clause, not a join;
│           │                # De-hardcode char-player (BRIEF-45, no schema
│           │                #   change): GET /api/bootstrap (read-only, opens
│           │                #   no session) returns {world_id, player_id,
│           │                #   current_location_id} — player_id resolved via
│           │                #   crud._player_character_id (character_type=
│           │                #   'player' scoped to the active world), fed to
│           │                #   the static cockpit JS since index.html has no
│           │                #   server-side templating; every other
│           │                #   "char-player" default in app.py (start_conversation,
│           │                #   get_scene, enter_scene, scene_join, scene_leave,
│           │                #   travel) now resolves the same way instead of a
│           │                #   literal;
│           │                # Create-PC path (BRIEF-46, schema v1.57): POST
│           │                #   /api/characters/player (PlayerCharacterCreateBody —
│           │                #   name + current_location_id) validates the location
│           │                #   is a `location` entity in the active world (400, no
│           │                #   write, on a miss) then creates entity + `character`
│           │                #   row (bound to the lone role='creator' User) + the
│           │                #   four `skill` rows at tier=0, mirroring seed_pilot.py's
│           │                #   char-player creation, PLUS one `skill` row per
│           │                #   `skill_definition` of the PC's world (BRIEF-55,
│           │                #   schema v1.63: B1 flat tier-0 seed, never a
│           │                #   model-proposed tier); one db.commit(); IntegrityError
│           │                #   from idx_character_one_pc_per_user_world surfaces as
│           │                #   {"ok": false, "error": ...}, not a 500;
│           │                #   get_bootstrap bugfix (same brief): no longer raises
│           │                #   when the active world has no PC yet — catches
│           │                #   _player_character_id's HTTPException and returns
│           │                #   player_id/current_location_id as None, so world_id
│           │                #   still resolves for a freshly created empty world
│           │                #   (needed by the create-PC form's location dropdown);
│           │                # PC creation assistant (BRIEF-52, schema v1.60):
│           │                #   POST /api/characters/player/generate
│           │                #   (PlayerGenerateBody — brief) delegates ONLY to
│           │                #   entity_author.generate_player_draft; writes
│           │                #   nothing; deliberately beside
│           │                #   POST /api/worlds/generate, not in crud.py, same
│           │                #   no-canon-write reasoning; PlayerCharacterCreateBody
│           │                #   (the create_player_character accept route, BRIEF-46)
│           │                #   gained description/appearance/backstory/knowledge
│           │                #   (all optional) — description set on Entity,
│           │                #   appearance/backstory on Character, knowledge written
│           │                #   through writes.write_knowledge with is_secret=False
│           │                #   (never POST /api/entities/{id}/knowledge, which 422s
│           │                #   on a bad level instead of defaulting to "rumor"); the
│           │                #   4-skill seed and the single try/db.commit() block
│           │                #   stay untouched (B1, byte-identical seed);
│           │                # POST /api/skill-definitions/generate (BRIEF-56,
│           │                #   no schema change): SkillCatalogueGenerateBody —
│           │                #   brief — delegates ONLY to
│           │                #   entity_author.generate_skill_catalogue_draft;
│           │                #   writes nothing; deliberately beside
│           │                #   POST /api/characters/player/generate, not in
│           │                #   crud.py, same no-canon-write reasoning; the
│           │                #   creator accepts/edits through the existing
│           │                #   creator-CRUD POST /api/skill-definitions
│           │                #   (crud.py), never written here;
│           │                # MJ narration layer (_load_mj_narration_template);
│           │                # MJ interpretation layer (ResponseMode incl. join,
│           │                #   physical — BRIEF-11/v1.23),
│           │                #   _interpret_mode → (mode, reference, used_object),
│           │                #   _build_mj_user (verdict_band + search_rubric
│           │                #   params for the physical branch),
│           │                #   _load_mj_interpret_template);
│           │                # physical resolution (BRIEF-11, schema v1.23):
│           │                #   _load_mj_arbiter_template, _arbitrate (pt-mj-
│           │                #   arbiter v3, usage='mj_arbitration', classifies
│           │                #   domain + opposed_npc_id + applies_constraint +
│           │                #   violent, fallback ("physical",None,None,False));
│           │                #   resolve_physical call in _stream's physical
│           │                #   branch — player_tier from Skill, npc_tier from
│           │                #   entity.metadata.physical_tier; verdict sent as
│           │                #   SSE `{"verdict": {...}}` before narration;
│           │                #   opposed NPC called like npc_reaction with the
│           │                #   verdict band appended, npc row written
│           │                #   canonically; unopposed turns behave like scene
│           │                #   (no NPC call, no npc row);
│           │                #   world-scoped custom skill catalogue (BRIEF-55,
│           │                #   schema v1.63): _arbitrate's candidate set and
│           │                #   domain clamp widen to BASE_SKILL_DOMAINS plus
│           │                #   the active world's skill_definition.name
│           │                #   values, filled into pt-mj-arbiter's
│           │                #   {custom_skill_names} placeholder; a returned
│           │                #   custom name resolves to its skill_definition's
│           │                #   base_domain (resolved_base_domain) — the PC's
│           │                #   skill row is then looked up by
│           │                #   skill_definition_id, not domain; the
│           │                #   base-domain lookup path gained
│           │                #   `AND skill_definition_id IS NULL`;
│           │                #   resolve_physical and the perception-discovery
│           │                #   gate both key off resolved_base_domain, never
│           │                #   the raw arbiter-returned string;
│           │                # possession check, binary (BRIEF-08/D2a.1,
│           │                #   schema v1.19): _find_player_item,
│           │                #   _build_refusal_instruction ([ACTION REFUSÉE],
│           │                #   one-shot, integrates NPC reaction), 
│           │                #   _GESTE_RATE_INSTRUCTION ([GESTE RATÉ], one-shot
│           │                #   to the responding NPC on a refused turn);
│           │                #   _apply_mutation item_update branch (sets
│           │                #   item.equipped, requires owner_id) — dormant,
│           │                #   no live producer since BRIEF-08/D2a.1, kept for
│           │                #   the cockpit equip toggle;
│           │                # _apply_mutation resource_change branch (BRIEF-19,
│           │                #   schema v1.32): the ONE branch writing two canon
│           │                #   tables (ledger always, knowledge when a leg
│           │                #   survives) inside the existing SAVEPOINT;
│           │                #   non-negative balance guard (ledger.get_balance);
│           │                #   _knowledge_leg_already_applied (block-whole
│           │                #   guard 4c, scans applied new_knowledge +
│           │                #   resource_change knowledge legs — one-directional
│           │                #   by design, see tooling/standards/ARCHITECTURE_DECISIONS.md);
│           │                #   excluded from _find_applied_duplicate (money
│           │                #   leg accumulates like relation_change);
│           │                # multi-NPC scenes (_open_gatherings, _active_members,
│           │                #   _gathering_brief, _player_gathering,
│           │                #   _render_gathering_status, _resolve_join_target (A2),
│           │                #   _join_gathering, _load_mj_speaker_template,
│           │                #   _select_group_speaker (A3), _build_join_narration_user;
│           │                #   POST .../join endpoint, JoinBody);
│           │                # NPC initiative (Tier 3): _load_mj_initiative_template,
│           │                #   _load_npc_initiative_act_template, _npc_initiative_vote
│           │                #   (two-section signal list, non_member_ids, cadence E1),
│           │                #   _build_initiative_trigger, _build_initiative_mj_user;
│           │                #   structural move=True override for non-member winners (C3)
│           │                # _find_applied_duplicate (new_knowledge + status_change only);
│           │                # MJ context wiring (_build_mj_user mj_context param,
│           │                #   assemble_mj_context calls in start_conversation,
│           │                #   scene_join, say — scope D-b3);
│           │                # _build_mj_user inventory_line param — player's
│           │                #   static inventory, read fresh per turn via
│           │                #   format_inventory_line (BRIEF-06, schema v1.18);
│           │                # travel (BRIEF-16, schema v1.29): _perform_travel
│           │                #   (shared helper — creator POST /api/travel + in-fiction
│           │                #   /say travel branch + picker callback; NOT a canon
│           │                #   mutation; rejects inactive dest C-a);
│           │                #   _location_neighbours (active connects_to neighbours,
│           │                #   distinct from GET /api/locations/graph — D1);
│           │                #   _resolve_travel_target (exact-ish match, A2);
│           │                #   travel branch in _stream (zero-neighbours→scene,
│           │                #   resolved→traveled SSE+_perform_travel,
│           │                #   unresolved→travel_candidates SSE);
│           │                #   restrained gating extended to travel (E1);
│           │                #   POST /api/conversations/{id}/travel (in-fiction
│           │                #   picker callback, neighbour-restricted, ConvTravelBody);
│           │                #   creator POST /api/travel (TravelBody — god-mode)
│           │                # cockpit batch review (POST /api/mutations/batch-review,
│           │                #   BatchReviewBody, _append_note, _BATCH_REVIEW_MARKER —
│           │                #   loops _apply_mutation / unit-reject fields per row,
│           │                #   skip-if-not-proposed, "batch-review" creator_notes marker)
│           │                # overhearing analysis (sync-after-stream, dialogue
│           │                #   turns only): analyze_overhearing call after the
│           │                #   NPC/MJ phases, silent-failure wrapping;
│           │                # window analysis (BRIEF-09, v1.21): analyze_window
│           │                #   called at scene-boundary triggers — conversation
│           │                #   close (end_conversation, travel) and location
│           │                #   transition (enter_scene) — plus the manual
│           │                #   Analyze endpoint (analyze_conversation_endpoint;
│           │                #   force resets last_analyzed_turn to 0 and deletes
│           │                #   only 'proposed' rows);
│           │                # scene_state (BRIEF-12, schema v1.24): ephemeral
│           │                #   combat/constraint state on conversation; cleared
│           │                #   on close; NOT canon; _default_scene_state,
│           │                #   _get_scene_state, _write_scene_state (archives
│           │                #   snapshot to history[] before every write);
│           │                #   _propose_engine_injury (proposed_by='engine',
│           │                #   injured/neutralized auto-proposal); constraint
│           │                #   gating in _stream: gagged→composure physical,
│           │                #   restrained→escape physical; frozen shortcircuit
│           │                #   (fixed MJ message, no model calls); condition
│           │                #   ladder writes on violent verdicts; GET/PATCH
│           │                #   /api/conversations/{id}/scene-state endpoints;
│           │                # perception & discovery (BRIEF-13, schema v1.26):
│           │                #   _propose_engine_discovery (proposed_by='engine',
│           │                #   discovery new_knowledge on partial/success
│           │                #   perception search); discovery gating in _stream
│           │                #   physical branch (domain=perception, no NPC
│           │                #   opposition — selects oldest undiscovered hidden
│           │                #   detail, injects rubric into MJ user message);
│           │                #   _build_mj_user search_rubric param;
│           │                #   discovered flip in _apply_mutation new_knowledge
│           │                #   branch on creator approval;
│           │                # signpost layer (BRIEF-17, schema v1.30):
│           │                #   _load_mj_establishment_template,
│           │                #   _build_establishment_user, _build_establishment_narration
│           │                #   (non-streamed chat() call, try/except-wrapped, never
│           │                #   blocks scene entry); wired into enter_scene on EVERY
│           │                #   entry (G1), before _scene_response — which gains the
│           │                #   `establishment: str | None` field
│           │                # AI entity-authoring assistant (BRIEF-24, schema v1.36):
│           │                #   POST /api/entities/generate (EntityGenerateBody) —
│           │                #   delegates to entity_author.generate_entity_draft and
│           │                #   nothing else; deliberately NOT on the crud.py router
│           │                #   (crud.py IS a canon-write path; this route writes
│           │                #   none, kept legible by living elsewhere)
│           │                # Region orchestrator (BRIEF-34, schema v1.45),
│           │                #   split into a two-phase creator checkpoint
│           │                #   (BRIEF-38, schema v1.49): POST
│           │                #   /api/regions/manifest (RegionGenerateBody) —
│           │                #   Phase A, delegates to
│           │                #   region_author.generate_region_manifest and
│           │                #   nothing else; POST /api/regions/generate
│           │                #   (RegionBuildBody, `{manifest}`) — Phase B,
│           │                #   delegates to region_author.generate_region_draft
│           │                #   and nothing else; both in the same no-canon-
│           │                #   write neighbourhood as /api/entities/generate,
│           │                #   not on the crud.py router; Phase B returns the
│           │                #   region draft as JSON only — review/commit UI
│           │                #   and draft-local-id-to-canon-id wiring live in
│           │                #   chantiers 2/3 below
│           │                # Region review + atomic commit, chantier 2 (BRIEF-36,
│           │                #   no schema change): POST /api/regions/commit
│           │                #   (RegionCommitBody, commit_region) — outside crud.py
│           │                #   like /api/regions/generate, but DOES write canon;
│           │                #   takes the re-sent region draft + a raw accept/reject
│           │                #   map (both untrusted), re-derives the cascade
│           │                #   server-side (_region_resolve_location_parent), and
│           │                #   calls crud._create_entity_core / _create_knowledge_core
│           │                #   directly in dependency order against one shared
│           │                #   session — one db.commit() at the end, db.rollback()
│           │                #   on any exception; only parent_location_id / primary
│           │                #   public faction_membership / current_location_id are
│           │                #   wired in this stage; judgment-link wiring (chantier 3,
│           │                #   BRIEF-37, no schema change) extends the SAME function
│           │                #   with phase 4, run after stages 1-3 and before the one
│           │                #   db.commit(): for each CONFIRMED sensed_links suggestion
│           │                #   (kind=connection / kind=faction only — parent/other/
│           │                #   shared_with stay display-only), resolves the target via
│           │                #   _region_resolve_link_target (intra-region by committed
│           │                #   name, then DB exact-match scoped to the world, S1 — never
│           │                #   auto-create) and calls write_relation directly
│           │                #   (commit-free, joins the same transaction): connection ->
│           │                #   connects_to (direction="mutual"); faction -> controls
│           │                #   (entity_a_id=faction, entity_b_id=location,
│           │                #   direction="a_to_b" mandatory); a rejected/uncommitted
│           │                #   source or target, or a self-link, writes nothing and is
│           │                #   recorded in the response's links.unresolved list instead;
│           │                #   RegionCommitBody gains confirmed_links (client confirm
│           │                #   flags are advisory only, resolution is server-side)
│           ├── crud.py      # Author CRUD — direct canonical writes (no proposed_mutation
│           │                #   checkpoint): entity/character/location/faction sheets,
│           │                #   relation/knowledge row editors, skill tier editor
│           │                #   (BRIEF-10, v1.22), discoverable_detail CRUD (BRIEF-13,
│           │                #   v1.26; signpost_group field BRIEF-17/v1.30):
│           │                #   GET/POST /locations/{id}/discoverable-details,
│           │                #   PUT/DELETE /discoverable-details/{id}; creator mode only;
│           │                #   location map graph (BRIEF-15, schema v1.28):
│           │                #   GET /api/locations/graph — read-only, returns active
│           │                #   location nodes (id, name, coordinates) + connects_to
│           │                #   edges (both endpoints must be active locations);
│           │                #   ledger (BRIEF-18, schema v1.31): POST /api/ledger
│           │                #   (creator-direct write, world_id derived from the
│           │                #   target entity, source_type in {creator,correction}),
│           │                #   GET /api/entities/{id}/ledger (balance + entries),
│           │                #   GET /api/ledger (global journal, entity_id/session_id
│           │                #   filters) — INSERT-only, no PUT/DELETE route exists;
│           │                #   skill catalogue CRUD (BRIEF-56, no schema change):
│           │                #   GET/POST/PUT/DELETE /api/skill-definitions, the
│           │                #   skill/discoverable_detail/ledger dedicated-router
│           │                #   shape (NOT the generic composite entity editor —
│           │                #   skill_definition has no entity_id), all world-scoped
│           │                #   via _world_id(db); POST validates base_domain ∈
│           │                #   BASE_SKILL_DOMAINS, name not a base-domain literal,
│           │                #   and UNIQUE(world_id,name) (409 on conflict), then
│           │                #   backfills a tier-0 skill row onto every existing PC
│           │                #   of the world in the same transaction (D2-backfill-yes);
│           │                #   PUT re-validates the same way and, when base_domain
│           │                #   changes, also updates domain on every dependent
│           │                #   skill row (skill_definition_id match); DELETE removes
│           │                #   every dependent skill row then the definition in one
│           │                #   transaction — always possible (never RESTRICT-blocked),
│           │                #   no change_history snapshot of the deletion
│           │                #   (D2-delete-cascade, the creator's type-"Oui" confirm
│           │                #   modal is the sole safeguard, same idiom as world
│           │                #   block deletion);
│           │                #   faction roles vocabulary (BRIEF-31, schema v1.42):
│           │                #   GET /api/entities/{faction_id}/roles — read-only,
│           │                #   returns entity.metadata['roles'] (ordered list of
│           │                #   {name, description}), no secret filtering (public
│           │                #   org vocabulary); the list itself is written through
│           │                #   the EXISTING composite entity PUT/POST (no new write
│           │                #   code — `roles` rides the generic `metadata` JSON base
│           │                #   field already coerced by _apply_base_fields);
│           │                # _player_character_id (BRIEF-45, no schema change):
│           │                #   structural PC resolver, sibling to _world_id —
│           │                #   `character_type='player'` scoped to the active
│           │                #   world; raises "No player character in the active
│           │                #   world." on a miss, never order-and-guesses;
│           │                #   consumed by app.py's bootstrap route and every
│           │                #   former "char-player" default;
│           │                # _create_entity_core (BRIEF-46, schema v1.57): when
│           │                #   entity_type == "character", auto-sets
│           │                #   ext_kwargs["world_id"] = entity.world_id —
│           │                #   character.world_id is denormalized from
│           │                #   entity.world_id (mirrors relation.world_id),
│           │                #   system-managed, never a registry-exposed field;
│           │                #   _entity_summary gains world_id (additive), read by
│           │                #   the cockpit's create-PC location dropdown to scope
│           │                #   to the active world
│           │                # Création world scoping (BRIEF-48, no schema change):
│           │                #   list_entities (the single chokepoint feeding 6
│           │                #   Création sub-tabs) and list_skill_player_characters
│           │                #   each gained a `.where(... .world_id == _world_id(db))`
│           │                #   clause; get_ledger_journal passes _world_id(db) into
│           │                #   ledger.list_entries' new optional world_id param —
│           │                #   the per-entity ledger route stays unchanged
│           │                #   (transitively scoped via entity_id already)
│           └── index.html   # single-page UI; MJ narration rendering;
│                            # loadBootstrap (BRIEF-45, no schema change):
│                            #   awaited FIRST in DOMContentLoaded, calls GET
│                            #   /api/bootstrap and stores WORLD_ID/PLAYER_ID
│                            #   module-level JS state; every former literal
│                            #   'char-player' (member-list/knowledge filters,
│                            #   /api/entities/... paths) now reads PLAYER_ID;
│                            # header world selector (BRIEF-43, schema v1.54):
│                            #   loadWorldSelector / activateWorld — lists all
│                            #   worlds, active one marked; selection (activateWorld,
│                            #   on success, BRIEF-48: nulls the Création list caches
│                            #   — authorAllEntities, playerCharIds, skillCharacters,
│                            #   _registreEntitiesLoaded — then re-invokes
│                            #   showCreationSubTab(currentCreationSubTab) if the
│                            #   Création view is visible, so the open sub-tab
│                            #   refreshes immediately and the rest re-fetch fresh
│                            #   on next view; a failed activation touches no cache),
│                            #   plus a
│                            #   "+ Monde" create form (BRIEF-44, schema v1.55:
│                            #   worldCreateOpen / worldCreateSubmit, POST
│                            #   /api/worlds with name + optional description/
│                            #   fundamental_laws, then refreshes the selector
│                            #   — the new world is already active server-side);
│                            #   delete control added BRIEF-54 (see below);
│                            #   "Générer avec l'IA" seed panel
│                            #   (BRIEF-47, no schema change), mounted INSIDE
│                            #   the same modal, above the name/description/
│                            #   laws fields: worldGenerateDraft() POSTs
│                            #   {brief} to /api/worlds/generate, then
│                            #   worldApplyDraft() pre-fills the SAME
│                            #   world-create-name/-description/-laws inputs
│                            #   worldCreateSubmit() already reads — that
│                            #   submit function and POST /api/worlds are
│                            #   unchanged; regenerating just re-runs
│                            #   worldGenerateDraft(), overwriting the fields
│                            #   in place (no separate discard step);
│                            #   per-modal backdrop dismiss (BRIEF-50, no schema
│                            #   change): genericModalOpen(title, bodyHtml, options)
│                            #   gains an options.dismissOnBackdrop flag (default
│                            #   true), stored on generic-modal-backdrop's dataset
│                            #   and re-set on every open (no stale leak across
│                            #   modals); the backdrop's outside-click handler
│                            #   checks it before calling genericModalClose() — ×
│                            #   and Escape are untouched and always close. Form-
│                            #   bearing modals should pass { dismissOnBackdrop:
│                            #   false }; worldCreateOpen does so (outside-click no
│                            #   longer destroys unsaved input); regionRenderSheet
│                            #   keeps the default (click-away dismissal);
│                            # Création → Personnage joueur "Créer un personnage
│                            #   joueur" form (BRIEF-46, schema v1.57): minimal —
│                            #   name + starting-location dropdown
│                            #   (pcCreateLoadLocations, filters GET
│                            #   /api/entities?type=location to WORLD_ID);
│                            #   pcCreateSubmit POSTs /api/characters/player, then
│                            #   re-calls loadBootstrap + loadPlayerName so the
│                            #   "Tu incarnes" banner and PLAYER_ID pick up the new
│                            #   PC, and refreshes the Fiche selector + entity list;
│                            #   no character builder — skills start flat at tier 0;
│                            #   PC creation assistant (BRIEF-52, schema v1.60):
│                            #   concept textarea #pc-generate-brief + "Générer le
│                            #   brouillon" button (pcGenerateDraft, POSTs {brief} to
│                            #   /api/characters/player/generate); pcApplyDraft
│                            #   pre-fills the SAME #pc-create-name/-description/
│                            #   -appearance/-backstory fields pcCreateSubmit() already
│                            #   reads, and sets module-scope pcDraftKnowledge, rendered
│                            #   READ-ONLY into #pc-draft-knowledge (I1 — no inline
│                            #   knowledge editing); pcCreateSubmit extends its POST
│                            #   payload with description/appearance/backstory/
│                            #   knowledge: pcDraftKnowledge; never touches
│                            #   #pc-create-location (C1); regenerating re-runs
│                            #   pcGenerateDraft, overwriting the fields/knowledge in
│                            #   place — no separate discard step (mirrors the
│                            #   world-bible generator);
│                            #   "Compétences" Création sub-tab (BRIEF-56, no
│                            #   schema change): AI-generate panel (concept
│                            #   textarea + "Générer le brouillon",
│                            #   competencesGenerateDraft POSTs {brief} to
│                            #   /api/skill-definitions/generate) renders an
│                            #   editable draft list (competencesDraft —
│                            #   name/base_domain/description per row,
│                            #   accept-individually via competencesAcceptDraftRow
│                            #   which POSTs /api/skill-definitions, or discard);
│                            #   "+ Ajouter une compétence" (competencesAddManualRow)
│                            #   pushes a blank row onto the same draft list — no
│                            #   separate manual-add form; existing-definitions list
│                            #   (competencesLoadList/_competencesRenderTable)
│                            #   supports inline rename/re-base/re-word
│                            #   (competencesSaveRow, PUT) and delete
│                            #   (competencesDeleteOpen/-Confirm — type-"Oui"
│                            #   confirm modal, same idiom as worldDeleteOpen);
│                            # NPC raw audit annotation; speaker-target selector
│                            #   (contract C2) + join-candidates picker;
│                            #   scene-view Travel control ("Voyager" — E1);
│                            #   in-fiction travel SSE handlers (BRIEF-16b):
│                            #     traveled → showSceneView() (mirrors Voyager);
│                            #     travel_candidates → _renderTravelCandidates
│                            #     picker → POST /api/conversations/{id}/travel
│                            #     → showSceneView() (mirrors join_candidates);
│                            #   two-mode shell (BRIEF-14, schema v1.27): Play
│                            #   sub-tabs Discussion / Historique / Mes savoirs +
│                            #   persistent "Tu incarnes : {name}" banner for
│                            #   the resolved player character (de-hardcoded
│                            #   from the char-player literal, BRIEF-45 — see
│                            #   loadBootstrap below); Création sub-tabs NPC / Personnage
│                            #   joueur / Lieux / Factions / Objets / Compétences
│                            #   (BRIEF-56) / Région / Artefacts
│                            #   (read-only scaffold) / Registre / Review Queue (review queue
│                            #   batch selection — per-row checkboxes on 'proposed'
│                            #   rows, select all/none, batch approve/reject);
│                            #   Création → Personnage joueur embeds Fiche skill
│                            #   sheet (BRIEF-10, schema v1.22): creator-mode
│                            #   inline tier editor (direct write via crud.py, no
│                            #   proposed_mutation, change_history archived),
│                            #   player-mode read-only ("Mode joueur" toggle)
│                            #   (inline CSS/JS, zero external deps)
│                            #   physical resolution audit: verdict annotation
│                            #   (domain · dice → total, band coloured by outcome),
│                            #   b-physical mode badge (BRIEF-11, schema v1.23);
│                            #   scene_state creator panel (BRIEF-12, schema
│                            #   v1.24): condition dot + frozen badge, constraint
│                            #   checkboxes, condition dropdown, save button;
│                            #   shown on conversation select, hidden on scene
│                            #   view; auto-refreshes after each /say turn;
│                            #   frozen annotation in npc-raw audit line;
│                            #   discoverable details panel on location sheet
│                            #   (BRIEF-13, schema v1.26): creator mode only —
│                            #   list/add/edit/delete details; player mode hidden;
│                            #   cluster-native signpost display (BRIEF-17,
│                            #   schema v1.30): rows sharing a signpost_group
│                            #   render together under a group header with
│                            #   per-row ambient/hidden badges; signpost_group
│                            #   editable on create + edit forms;
│                            #   location adjacency graph panel in Lieux sub-tab
│                            #   (BRIEF-15, schema v1.28): hand-rolled SVG, zero
│                            #   deps; graphLoad / graphRender / graphAutoPlace
│                            #   (deterministic circle for null coordinates);
│                            #   drag-to-position (read-merge-write via entity PUT,
│                            #   coordinates-only); click-to-connect (creates
│                            #   connects_to relation, undirected dedup guard);
│                            #   click-to-delete-edge; "Ajouter un lieu" reuses
│                            #   existing creationNewEntity() flow;
│                            #   Création → Registre sub-tab (BRIEF-18, schema
│                            #   v1.31): global ledger journal (GET /api/ledger),
│                            #   entity/session filters, creator credit/debit
│                            #   form (POST /api/ledger) — read-only history,
│                            #   no edit/delete UI (append-only); per-character
│                            #   "Solde" block on the character sheet (NPC and
│                            #   Personnage joueur), read-only, GET
│                            #   /api/entities/{id}/ledger;
│                            #   Création → NPC "Tarifs" editor (BRIEF-20, schema
│                            #   v1.33): add/edit/remove entity.metadata.price_list
│                            #   entries; creator-direct read-merge-write through
│                            #   the existing entity PUT (GET fresh, set only
│                            #   metadata.price_list, no clobber of other metadata
│                            #   keys), no proposed_mutation; shown only on the
│                            #   NPC sub-tab;
│                            #   Création → NPC "Générer avec l'IA" panel (BRIEF-24,
│                            #   schema v1.36): one-shot brief → POST
│                            #   /api/entities/generate → pre-fills the SAME new-NPC
│                            #   form (authorGenerateEntity), incl. a pendingDraftKnowledge
│                            #   in-memory list (the entity doesn't exist yet, so secret
│                            #   knowledge rows can't be POSTed until accept) rendered by
│                            #   authorRenderPendingKnowledge / edited via
│                            #   _syncPendingKnowledgeFromDom; "Notes de l'assistant"
│                            #   read-only block (notes + shared_with); accepting
│                            #   (authorSave) creates the entity via the EXISTING
│                            #   composite POST then flushes pendingDraftKnowledge
│                            #   through the EXISTING POST .../knowledge endpoint — no
│                            #   new write code; a second "Générer" discards the draft
│                            #   (F2 conversational refine out of scope);
│                            #   Création → Lieux "Générer avec l'IA" panel (BRIEF-25,
│                            #   schema v1.37): same one-shot panel
│                            #   (authorRenderGeneratePanel, shared with NPC), routed by
│                            #   authorGenerateEntity through entity_type derived from
│                            #   currentCreationSubTab; authorApplyLocationDraft pre-fills
│                            #   name/description/location_type/access_level and merges
│                            #   draft.public.subculture (allow-listed keys) with
│                            #   draft.secret.subculture_hidden into the existing
│                            #   subculture JSON textarea — the merge reads two
│                            #   already-segregated draft fields, never a single
│                            #   model-controlled key (B1); magic_status/coordinates
│                            #   untouched; sensed_links + the full subculture render in
│                            #   the read-only "Notes de l'assistant" block
│                            #   (authorRenderGenNotes, shared with NPC); accepting goes
│                            #   through the EXISTING composite POST only — no knowledge
│                            #   rows for locations, no new write code;
│                            #   Création → Factions "Roles" editor (BRIEF-31, schema
│                            #   v1.42): structured list of {name, description} rows
│                            #   (add/remove/reorder ↑↓, no raw-JSON textarea) on the
│                            #   faction create/edit form, held in
│                            #   authorFactionRolesDraft and merged into
│                            #   entityData.metadata.roles by authorSave — rides the
│                            #   EXISTING composite entity PUT/POST, no new backend
│                            #   write code; name-less rows dropped on save; NPC
│                            #   "Appartenances" membership form's free-text role
│                            #   input is now a `<select>` (authorMembershipFactionChanged)
│                            #   populated from GET /api/entities/{faction_id}/roles in
│                            #   stored order, plus an always-present "autre" option
│                            #   that reveals the original free-text input — selecting
│                            #   "autre" never mutates faction.metadata.roles;
│                            #   Création → Factions "Générer avec l'IA" panel
│                            #   (BRIEF-32, schema v1.43): same one-shot panel
│                            #   (authorRenderGeneratePanel, shared with NPC/Lieux),
│                            #   routed by authorGenerateEntity when
│                            #   currentCreationSubTab === 'factions';
│                            #   authorApplyFactionDraft pre-fills name/description/
│                            #   faction_type/philosophy/internal_structure (public)
│                            #   and internal_tensions/goals (secret), and populates
│                            #   authorFactionRolesDraft from draft.public.roles,
│                            #   re-rendering the SAME roles editor the BRIEF-31
│                            #   structured list owns — no new store; accepting goes
│                            #   through the EXISTING composite POST only, same as
│                            #   the manual roles editor;
│                            #   Création → Région sub-tab (BRIEF-36, chantier 2, no
│                            #   schema change), now fronted by a two-phase manifest
│                            #   checkpoint (BRIEF-38, schema v1.49, C1 — one-liner
│                            #   text editing only): brief → POST /api/regions/manifest
│                            #   → manifest held client-side (regionManifest) →
│                            #   checkpoint screen (regionRenderManifest — Factions/
│                            #   Lieux/PNJ flat lists, entity name read-only, one-liner
│                            #   editable textarea bound straight onto regionManifest;
│                            #   name/parent_name/location_name/faction_name shown for
│                            #   context only, never editable) → "Générer les fiches"
│                            #   (regionBuild) → POST /api/regions/generate with
│                            #   {manifest: regionManifest} (server re-normalizes before
│                            #   use, client edit is advisory) → region draft held
│                            #   client-side (regionDraft/
│                            #   regionAccepted, the pendingDraft* pattern at tree
│                            #   scale) → D1 spatial review tree (regionRenderTree —
│                            #   root location top, children/NPCs nested, faction
│                            #   badges, faction panel with member counts, skipped[]
│                            #   list, per-node generation notes via regionEntityNotes)
│                            #   → B1 soft cascade preview, advisory only
│                            #   (regionCascade — mirrors the server's re-derivation,
│                            #   never sent as a precomputed result) → E1 commit
│                            #   (regionCommit → POST /api/regions/commit); "Recommencer"
│                            #   discards the held manifest AND draft (regionRestart);
│                            #   no inline editing of the post-generation review tree
│                            #   itself (C1 there is still OUT — only the Phase-A
│                            #   one-liner checkpoint above is editable);
│                            #   judgment-link confirm/discard toggles (BRIEF-37, chantier
│                            #   3): each location node's wirable sensed_links rows
│                            #   (kind=connection/faction only) render a per-row toggle
│                            #   via regionRenderLinkToggles, default UNCONFIRMED
│                            #   (regionConfirmedLinks, opt-in — inverse of B1's default-
│                            #   accept); parent/other rows keep rendering as plain notes
│                            #   via regionEntityNotes; regionCommit now also sends
│                            #   confirmed_links, and the commit-result panel renders the
│                            #   response's links.written/links.unresolved
│                            #   World block deletion (BRIEF-54, schema v1.62):
│                            #   delete button next to #world-selector
│                            #   (worldDeleteOpen) reads the selected option's id/
│                            #   name and opens a B2′ click-away-protected confirm
│                            #   modal (genericModalOpen(..., { dismissOnBackdrop:
│                            #   false }), same shape as worldCreateOpen) with a
│                            #   type-`Oui`-exactly gate (oninput handler) before
│                            #   "Supprimer définitivement" enables; worldDeleteConfirm
│                            #   sends DELETE /api/worlds/{id}; on remaining===0
│                            #   force-opens worldCreateOpen() (C2-c, client-side
│                            #   only — no redirect mechanism exists in this app);
│                            #   on remaining>=1, refreshes loadWorldSelector +
│                            #   loadBootstrap (WORLD_ID/PLAYER_ID repoint), the
│                            #   same Création-cache invalidation activateWorld
│                            #   already does, and re-renders Play (loadScene,
│                            #   loadPlayerName) for the now-active world; ok===false
│                            #   leaves the modal open with the error shown
├── scripts/
│   ├── init_db.py           # creates the SQLite file with every table + index
│   ├── seed_pilot.py        # seeds Verkhaal world data + prompt templates (idempotent)
│   ├── talk.py              # live CLI conversation with an NPC via Ollama
│   ├── analyze_conversation.py  # extract proposed mutations from a closed conversation
│   ├── migrate_v1_24.py     # add conversation.scene_state column (BRIEF-12, idempotent)
│   ├── migrate_v1_26.py     # add discoverable_detail table + indexes (BRIEF-13, idempotent)
│   ├── migrate_v1_30.py     # add discoverable_detail.signpost_group + index (BRIEF-17, idempotent)
│   ├── migrate_v1_31_ledger.py  # add the ledger table + indexes (BRIEF-18, idempotent)
│   ├── migrate_v1_54.py     # add world.is_active + idx_world_one_active, auto-activate
│   │                        #   the sole world row on a single-world DB (BRIEF-43, idempotent)
│   ├── migrate_v1_57.py     # add character.world_id (backfilled from entity.world_id)
│   │                        #   + idx_character_world + idx_character_one_pc_per_user_world
│   │                        #   partial-unique (BRIEF-46, idempotent)
│   ├── migrate_v1_65_pc_skill_backfill.py
│   │                        #   no new tables/columns; backfills the four base
│   │                        #   skill rows (tier=0) for every player character
│   │                        #   missing them — retrofits PCs predating the
│   │                        #   create-route seed (BRIEF-59, idempotent)
│   └── cockpit.py           # launch the review cockpit (uvicorn, 127.0.0.1 only)
├── pyproject.toml           # src-layout package metadata
├── requirements.txt
├── .env.example
└── world_engine.db          # legacy in-tree DB location (gitignored); default
                              #   moved to ~/.world_engine/world_engine.db
                              #   (BRIEF-21, schema v1.34) — may still appear
                              #   here only via an env override
```

`src` layout: the package lives under `src/world_engine`. Scripts in `scripts/`
prepend `src` to `sys.path`, so they run without an editable install.

### Naming

- **Tables:** every model sets `__tablename__` explicitly to the exact schema
  name (`pass_play`, `conversation_message`, `proposed_mutation`, …). Class
  names are PascalCase (`PassPlay`, `ConversationMessage`).
- **Primary keys:** TEXT/UUID strings. Top-level tables auto-generate via a
  `_uuid()` `default_factory`; entity-extension tables (`character`, `location`,
  `faction`, `artifact`) take their PK as the `entity.id` foreign key.
- **Reserved name:** `entity.metadata` maps to the Python attribute `metadata_`
  (SQLAlchemy reserves `metadata`).

### Schema fidelity rules

- DB-level `DEFAULT` clauses are preserved with `server_default` so the generated
  DDL matches the schema; Python-side defaults keep the ORM ergonomic.
- Columns that carry a default are also `NOT NULL` (a value is always present) —
  a deliberate strengthening over the literal SQL.
- JSON columns use SQLAlchemy `JSON` (becomes `JSONB` on PostgreSQL).
- Foreign keys are declared on every column the schema references; SQLite FK
  enforcement is turned on via a `PRAGMA foreign_keys=ON` connect listener.

### How to run / test

- **Install:** `python -m venv .venv`, activate, `pip install -r requirements.txt`.
- **Database URL:** from `WORLD_ENGINE_DATABASE_URL` (defaults to
  `~/.world_engine/world_engine.db`, outside the git working tree since
  BRIEF-21/v1.34). Switching to PostgreSQL/Supabase changes only this
  variable, never code.
- **Initialize the DB:** `python scripts/init_db.py` — idempotent; prints the
  tables and index counts it created.
- **Seed pilot data:** `python scripts/seed_pilot.py` — inserts Verkhaal world,
  NPCs, relations, knowledge, and prompt templates. Idempotent.
- **Live conversation:** `python scripts/talk.py` — opens a terminal conversation
  with Maelis. Requires Ollama running (`ollama serve`).
- **Analyse a conversation:** `python scripts/analyze_conversation.py <conversation_id>`
  — reads unanalyzed turns (`turn_order > conversation.last_analyzed_turn`),
  calls Ollama locally, writes `proposed_mutation` rows
  (`proposed_by='local_ai_window'`) and advances `last_analyzed_turn`
  atomically. Prints "Nothing new to analyze." if there are no unanalyzed
  turns. Use `--force` to delete existing *proposed* rows for this
  conversation, reset `last_analyzed_turn` to 0, and re-run over the full
  transcript (reviewed rows are never deleted — see Working rules).
- **Creator cockpit:** `python scripts/cockpit.py` — starts the local review UI
  at http://127.0.0.1:8000. Enter a location (scene view in Play → Discussion),
  join a gathering, then type turns live. Each turn:
  NPC reply is generated internally (buffered), MJ narration is streamed to the
  player; both are persisted (`speaker='npc'` canonical, `speaker='mj'`
  presentation). Raw NPC line appears as a muted annotation for creator audit.
  Overhearing proposals (Tier 4, `proposed_by='local_ai_overhearing'`)
  accumulate silently each turn for `dialogue` mode; no other
  `proposed_mutation` rows are written during a turn. Window analysis
  (`analyze_window`, `proposed_by='local_ai_window'`) fires automatically at
  scene boundaries — conversation close, the player leaving a location, and
  gathering dissolution — and can also be run manually via **Analyze**, which
  reports "nothing new to analyze" if there are no unanalyzed turns since the
  last run. **Force** is a debug path: it deletes this conversation's
  `proposed` rows, resets `last_analyzed_turn` to 0, and re-analyzes the full
  transcript (may re-propose already-applied relation deltas — review
  manually). Approve / reject proposals in the queue individually, or select
  several `proposed` rows via checkboxes and use **Approve selected** /
  **Reject selected** (`POST /api/mutations/batch-review`) — sequential, per
  row, through the same `_apply_mutation` / unit-reject paths; stale or
  already-reviewed rows are skipped. Binds to loopback only. Requires Ollama
  for all AI calls (NPC, MJ, analysis). The scene view's **Voyager** control
  (`POST /api/travel`) lets the creator move the player to any location: a
  silent, clean transition (runs window analysis on, then closes, the open
  conversation and the player's gathering membership, then updates
  `current_location_id`); the existing scene-entry flow generates the new
  location's gatherings on next entry.
- **Re-seeding prompts:** `python scripts/seed_pilot.py` uses `upsert_prompt_template`
  for `pt-npc-dialogue`, `pt-mj-narration`, `pt-mj-interpretation`, `pt-mj-gathering`,
  `pt-mj-speaker`, `pt-mj-initiative`, `pt-npc-initiative-act`, `pt-mj-arbiter`,
  `pt-mj-establishment`, `pt-entity-generation`, `pt-world-generation`,
  `pt-region-manifest`, `pt-region-manifest-topup`, `pt-player-generation`, and
  `pt-skill-catalogue` — re-running the seed converges the DB to the latest
  wording without losing other data.

---

*Co-built with Claude, June 2026.*
