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

## Local model notes

Target local model for NPC dialogue and analysis: **`huihui_ai/qwen3-abliterated:8b-v2`**, run via Ollama. Relevant when wiring the model (not before — context assembly is model-agnostic):

- **Abliterated** = refusal mechanisms removed. Will not refuse, and is generally more compliant to *any* instruction — including a player pushing it to reveal. This makes it the strictest possible test of the "concealed knowledge / under guard" mechanism: if secrets hold here, they hold anywhere. The creator checkpoint remains the real safety net regardless.
- **Thinking mode:** Qwen3 emits a `<think>...</think>` reasoning block before its answer. `ollama_client.strip_think()` handles this robustly (complete block, unclosed tag, orphan closing tag). Three policies apply depending on the call site:
  - **NPC dialogue** (`talk.py` CLI): disable thinking with `/no_think` in the user message — deterministic, faster, and the reasoning block must never reach the player.
  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` with the built-in `_StreamThinkFilter` — thinking is left enabled, the filter suppresses the block before any token is yielded. The NPC reply is buffered internally; the player never sees it raw.
  - **MJ narration** (cockpit `/say`, MJ phase): `chat_stream` + `/no_think` appended to the user message — same filter as a backstop, `/no_think` for speed. What streams to the player is narration prose only.
  - **MJ interpretation** (cockpit `/say`, phase 0): `chat()` non-streaming + `/no_think` + `format="json"`. Classifies the player's input into `dialogue` / `npc_reaction` / `scene`. Fallback to `dialogue` on any error — a misclassification must never break a turn.
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
│       ├── context.py       # NPC context assembly (secret-exclusion + relation-gating)
│       ├── ollama_client.py # HTTP client for local Ollama; strips <think> blocks
│       ├── analyzer.py      # mutation analysis; _normalize_to_schema; _validate_item;
│       │                    # analyze_conversation (final pass, filters relation_change);
│       │                    # analyze_single_turn (per-turn immediate flags,
│       │                    #   proposed_by='local_ai_immediate', within-turn collapse)
│       └── cockpit/         # creator review web UI (FastAPI sub-app)
│           ├── __init__.py
│           ├── app.py       # JSON endpoints + HTML route; _apply_mutation;
│           │                # MJ narration layer (_load_mj_narration_template);
│           │                # MJ interpretation layer (ResponseMode,
│           │                #   _interpret_mode, _build_mj_user,
│           │                #   _load_mj_interpret_template);
│           │                # _find_applied_duplicate (new_knowledge + status_change only);
│           │                # _mutation_match_key (idempotent types only)
│           └── index.html   # single-page UI; MJ narration rendering;
│                            # NPC raw audit annotation (inline CSS/JS, zero external deps)
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
  — reads the closed transcript, calls Ollama locally, writes `proposed_mutation`
  rows. Use `--dry-run` to preview without writing; `--force` to replace existing
  *proposed* rows and re-run (reviewed rows are never deleted — see Working rules).
- **Creator cockpit:** `python scripts/cockpit.py` — starts the local review UI
  at http://127.0.0.1:8000. Select an NPC → Start → play turns live. Each turn:
  NPC reply is generated internally (buffered), MJ narration is streamed to the
  player; both are persisted (`speaker='npc'` canonical, `speaker='mj'`
  presentation). Raw NPC line appears as a muted annotation for creator audit.
  Per-turn `proposed_mutation` rows (`proposed_by='local_ai_immediate'`) are
  written silently after each turn. Use **Analyze** to run the final pass (which
  filters `relation_change` and deduplicates against the per-turn flags). Approve
  / reject proposals in the queue. Binds to loopback only. Requires Ollama for
  all AI calls (NPC, MJ, analysis).
- **Re-seeding prompts:** `python scripts/seed_pilot.py` uses `upsert_prompt_template`
  for `pt-mj-narration` and `pt-mj-interpretation` — re-running the seed converges
  the DB to the latest wording without losing other data.

---

*Co-built with Claude, June 2026.*
