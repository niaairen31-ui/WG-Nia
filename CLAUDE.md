# World Engine — Project Instructions

## What this is

A local, single-player-first engine for running a persistent RPG world. A creator keeps structural control over how the world evolves. Two modes of play feed the same world: asynchronous **pass-plays** and real-time **live sessions** (a player enters a location, sees the NPCs present, talks to them, learns things, builds relationships).

Full context lives in:
- `world-engine-schema.md` — the authoritative database schema.
- `ARCHITECTURE_DECISIONS.md` — the design decisions and the v1 scope.

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
  schema-touching) and keeps `ARCHITECTURE_DECISIONS.md` and this file
  consistent with the code. Use the `/close-step` command.

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
  roster is deferred (see "Deferred decisions" in `ARCHITECTURE_DECISIONS.md`).
- **Two sanctioned canon-write paths, no others:** `_apply_mutation` (AI
  proposals, after creator approval) and the creator CRUD (direct creator
  authority). No code path may ever write canon in response to an AI
  proposal outside `_apply_mutation`.
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
  "Deferred decisions" in `ARCHITECTURE_DECISIONS.md`). Downgrades,
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
│       │                    #   entity's context
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
│       │                    #   _mutation_match_key (money leg accumulates)
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
│       └── cockpit/         # creator review web UI (FastAPI sub-app)
│           ├── __init__.py
│           ├── app.py       # JSON endpoints + HTML route; _apply_mutation;
│           │                # MJ narration layer (_load_mj_narration_template);
│           │                # MJ interpretation layer (ResponseMode incl. join,
│           │                #   physical — BRIEF-11/v1.23),
│           │                #   _interpret_mode → (mode, reference, used_object),
│           │                #   _build_mj_user (verdict_band + search_rubric
│           │                #   params for the physical branch),
│           │                #   _load_mj_interpret_template);
│           │                # physical resolution (BRIEF-11, schema v1.23):
│           │                #   _load_mj_arbiter_template, _arbitrate (pt-mj-
│           │                #   arbiter v2, usage='mj_arbitration', classifies
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
│           │                #   by design, see ARCHITECTURE_DECISIONS.md);
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
│           │                #   filters) — INSERT-only, no PUT/DELETE route exists
│           └── index.html   # single-page UI; MJ narration rendering;
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
│                            #   char-player; Création sub-tabs NPC / Personnage
│                            #   joueur / Lieux / Factions / Objets / Artefacts
│                            #   (read-only scaffold) / Review Queue (review queue
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
│                            #   NPC sub-tab
├── scripts/
│   ├── init_db.py           # creates the SQLite file with every table + index
│   ├── seed_pilot.py        # seeds Verkhaal world data + prompt templates (idempotent)
│   ├── talk.py              # live CLI conversation with an NPC via Ollama
│   ├── analyze_conversation.py  # extract proposed mutations from a closed conversation
│   ├── migrate_v1_24.py     # add conversation.scene_state column (BRIEF-12, idempotent)
│   ├── migrate_v1_26.py     # add discoverable_detail table + indexes (BRIEF-13, idempotent)
│   ├── migrate_v1_30.py     # add discoverable_detail.signpost_group + index (BRIEF-17, idempotent)
│   ├── migrate_v1_31_ledger.py  # add the ledger table + indexes (BRIEF-18, idempotent)
│   └── cockpit.py           # launch the review cockpit (uvicorn, 127.0.0.1 only)
├── pyproject.toml           # src-layout package metadata
├── requirements.txt
├── .env.example
└── world_engine.db          # local SQLite file (gitignored)
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
  `sqlite:///world_engine.db`). Switching to PostgreSQL/Supabase changes only
  this variable, never code.
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
  `pt-mj-speaker`, `pt-mj-initiative`, `pt-npc-initiative-act`, `pt-mj-arbiter`, and
  `pt-mj-establishment` — re-running the seed converges the DB to the latest
  wording without losing other data.

---

*Co-built with Claude, June 2026.*
