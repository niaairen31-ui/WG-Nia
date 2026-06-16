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

## Local model notes

Target local model for NPC dialogue and analysis: **`huihui_ai/qwen3-abliterated:8b-v2`**, run via Ollama. Relevant when wiring the model (not before — context assembly is model-agnostic):

- **Abliterated** = refusal mechanisms removed. Will not refuse, and is generally more compliant to *any* instruction — including a player pushing it to reveal. This makes it the strictest possible test of the "concealed knowledge / under guard" mechanism: if secrets hold here, they hold anywhere. The creator checkpoint remains the real safety net regardless.
- **Thinking mode:** Qwen3 emits a `<think>...</think>` reasoning block before its answer. `ollama_client.strip_think()` handles this robustly (complete block, unclosed tag, orphan closing tag). Three policies apply depending on the call site:
  - **NPC dialogue** (`talk.py` CLI): disable thinking with `/no_think` in the user message — deterministic, faster, and the reasoning block must never reach the player.
  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` with the built-in `_StreamThinkFilter` — thinking is left enabled, the filter suppresses the block before any token is yielded. The NPC reply is buffered internally; the player never sees it raw.
  - **MJ narration** (cockpit `/say`, MJ phase): `chat_stream` + `/no_think` appended to the user message — same filter as a backstop, `/no_think` for speed. What streams to the player is narration prose only.
  - **MJ interpretation** (cockpit `/say`, phase 0): `chat()` non-streaming + `/no_think` + `format="json"`. Classifies the player's input into `dialogue` / `npc_reaction` / `scene`. Fallback to `dialogue` on any error — a misclassification must never break a turn.
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
│       │                    #   format_inventory_line since BRIEF-08/D2a.1)
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
│       │                    #   upgrades (v1.17), proposed_by='local_ai_overhearing')
│       ├── resolution.py    # physical-action dice resolution (BRIEF-11, schema
│       │                    #   v1.23): pure 2d6 + tier, no DB/model access;
│       │                    #   Verdict {domain, dice, modifier, total, band};
│       │                    #   resolve_physical(domain, player_tier, npc_tier=0)
│       │                    #   — bands <=6 failure, 7-9 partial, >=10 success;
│       │                    #   player-roll rule (verbatim in module docstring)
│       └── cockpit/         # creator review web UI (FastAPI sub-app)
│           ├── __init__.py
│           ├── app.py       # JSON endpoints + HTML route; _apply_mutation;
│           │                # MJ narration layer (_load_mj_narration_template);
│           │                # MJ interpretation layer (ResponseMode incl. join,
│           │                #   physical — BRIEF-11/v1.23),
│           │                #   _interpret_mode → (mode, reference, used_object),
│           │                #   _build_mj_user (verdict_band param for the
│           │                #   physical branch), _load_mj_interpret_template);
│           │                # physical resolution (BRIEF-11, schema v1.23):
│           │                #   _load_mj_arbiter_template, _arbitrate (pt-mj-
│           │                #   arbiter, usage='mj_arbitration', classifies
│           │                #   domain + optional opposed_npc_id, fallback
│           │                #   ("physical", None) on any failure);
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
│           │                # creator travel control (POST /api/travel, TravelBody — E1)
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
│           │                #   only 'proposed' rows)
│           └── index.html   # single-page UI; MJ narration rendering;
│                            # NPC raw audit annotation; speaker-target selector
│                            #   (contract C2) + join-candidates picker;
│                            #   scene-view Travel control ("Voyager" — E1);
│                            #   review queue batch selection (per-row checkboxes on
│                            #   'proposed' rows, select all/none, batch approve/reject);
│                            #   Author CRUD character sheet — read-only Items
│                            #   section (equipped vs stowed, BRIEF-06)
│                            #   "Fiche" mode tab — player skill sheet
│                            #   (BRIEF-10, schema v1.22): creator-mode inline
│                            #   tier editor (direct write via crud.py, no
│                            #   proposed_mutation, change_history archived),
│                            #   player-mode read-only ("Mode joueur" toggle)
│                            #   (inline CSS/JS, zero external deps)
├── scripts/
│   ├── init_db.py           # creates the SQLite file with every table + index
│   ├── seed_pilot.py        # seeds Verkhaal world data + prompt templates (idempotent)
│   ├── talk.py              # live CLI conversation with an NPC via Ollama
│   ├── analyze_conversation.py  # extract proposed mutations from a closed conversation
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
  at http://127.0.0.1:8000. Select an NPC → Start → play turns live. Each turn:
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
  for `pt-mj-narration`, `pt-mj-interpretation`, `pt-mj-gathering`, `pt-mj-speaker`,
  `pt-mj-initiative`, `pt-npc-initiative-act`, and `pt-mj-arbiter` — re-running
  the seed converges the DB to the latest wording without losing other data.

---

*Co-built with Claude, June 2026.*
