# World Engine — Project Instructions

## What this is

A locally-hosted AI-powered tabletop RPG world engine (Verkhaal is the pilot
world). A creator cockpit (world-building + play surface) drives local models
through structured prompts; every AI-proposed change to world canon passes a
creator checkpoint before it is applied. This file is the standing contract
for Claude Code sessions: conventions, the invariants that hold everywhere,
and how to run things. Invariants that hold for one part of the code live in
`.claude/rules/` (see Path-scoped rules). History and rationale live in
`tooling/standards/ARCHITECTURE_DECISIONS.md` and
`world-engine-schema-changelog.md` — never here.

## Stack

- Python, FastAPI, SQLModel, SQLite (Supabase/PostgreSQL migration path
  preserved via the env-var DB URL).
- Frontend: a built Svelte shell (`frontend/`) serves the cockpit at `/`.
  Creation, Observation, Journée and Lore are shell-native Svelte
  components, mounted directly by `App.svelte`; Play alone stays legacy
  (`/legacy`, one governed iframe, `cockpit/legacy.html`) until its own
  ticket. No new dependency without a decision.
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
- Database URL resolves fail-closed from `WORLD_ENGINE_ENV=prod|test` (no
  implicit default; `WORLD_ENGINE_DATABASE_URL` overrides) —
  PostgreSQL/Supabase needs only a variable change.
- History is sacred: prefer preserving successive states over overwriting them.
- **`--force` only deletes `proposed` rows.** Any `proposed_mutation` row
  with status `applied`, `approved`, or `rejected` is reviewed history and
  must never be deleted — not by the CLI `--force` flag, not by the cockpit
  re-analyze endpoint. A forced re-analysis regenerates proposals alongside
  existing reviewed rows.
- **Language convention:** design conversation happens in French; all code,
  schema, comments, commit messages, and documentation are in English.
- **Step closure:** every closed step updates the schema changelog (if
  schema-touching) and keeps `tooling/standards/ARCHITECTURE_DECISIONS.md`,
  this file and `.claude/rules/` consistent with the code. Use `/close-step`.
  This file and every rule file are contract-checked by
  `tooling/verify/checks/claude_md_contract.py`: section whitelist,
  character budgets, 100-character lines, archaeology bans, invariant ids
  and markers, and every rule's `paths:` still matching a file.

## Ticket pipeline (governance)

- **Git:** never push to `main`, never commit on it (the `block-main-push`
  and `block-commit-on-main` hooks refuse both). Work on `ticket/NNNN`, open
  a PR, merge only after a green `/verify` AND Nia's live gate.
- **Danger classes (D1):** destructive_data | migration | permanent deletion
  -> human gate, no auto-merge (Nia decides). No automated backup exists;
  `scripts/backup.py` is a manual, deliberate step. db_write alone triggers
  nothing.
- **Escalate to Nia only on:** (a) an unspecified user-visible behavior
  change, (b) a destructive/irreversible data operation, (c) an architecture
  change above the ticket's stated `blast_radius`, (d) two consecutive
  `/verify` failures. An escalation is an entry of the ticket's own
  `## Escalations` section, written only by `tooling/glue/escalation.py`.
- **Planning is chat-side, execution is here.** Decisions, the lot RECON and
  the lot are made with Nia in the chat (Opus): a lot header in
  `tooling/lots`, authoritative, plus one brief per commit set in
  `tooling/briefs`, each embedding the findings and contracts it uses.
  Claude Code (Sonnet) executes one brief per session, starting with its
  Mini-RECON; an anchor that does not hold is a STOP.
- **Commands:** `/brief-exec` runs one brief; `/pipeline TICKET-NNNN` runs
  every brief, `/verify`, then opens the PR. Every commit goes `/review-step`
  then `/close-step` in the same turn; commits are pre-authorized and only a
  VIOLATION verdict stops the chain. Every ticket's Machine-checkable section
  links `verify/checks/corpus_gate.py`.
- **Schema version:** `vMAJOR.MINOR`, MINOR two digits, 00-99. Next version:
  MINOR < 99 -> `vMAJOR.(MINOR+1)` zero-padded; MINOR = 99 -> `v(MAJOR+1).00`.
  MAJOR counts MINOR overflows and carries no semantic meaning. Published
  changelog versions are never renumbered.
- **The filename is law.** Tickets, lots, briefs and amendments carry their
  final real ID and slug in filename and content (`TICKET-0117-slug.md`,
  `LOT-0117-slug.md`, `BRIEF-0117-A-slug.md`, `AMENDMENT-0117-01.md`). Nia
  deposits them in `tooling/tickets|lots|briefs` by hand. Tickets keep a
  `slug:` front-matter field; briefs a line-1 `<!-- slug: ... -->` comment.
  An amendment is never named `TICKET-*`, which `pipeline_state.py` globs.
- **Where things live:** `tooling/tickets`, `tooling/lots`, `tooling/briefs`;
  `tooling/recon` (archived RECONs of earlier tickets, none written now);
  `tooling/glue` (`gen_decisions_index.py`, `gen_file_map.py`,
  `escalation.py`); `tooling/verify` (`run.py`, `checks/`, `baselines/`,
  `results/`); `tooling/standards` (`ARCHITECTURE_DECISIONS.md`, generated
  `DECISIONS_INDEX.md` and `FILE_MAP.md`, `code_standards.md`).
- This section governs the ticket pipeline itself (process, gating,
  escalation). It does not replace or relax any invariant below — those
  still apply to every change regardless of how it was ticketed.

## Numbering & decisions governance

- A ticket's number is Nia's: she reserves numbers for a series, and a
  deferral or a sequel always goes to a higher number, never a lower one.
  A ticket, its lot, its briefs and its amendments share that number, and
  every artifact is authored with it already in place (filename is law).
- Legacy two-digit BRIEF-NN identifiers are a closed, grandfathered
  namespace: never reused, never renumbered.
- New decision records in `tooling/standards/ARCHITECTURE_DECISIONS.md` use
  the header form
  `## TITLE (BRIEF-NNNN[-x][, ...], schema vX.YY | no schema change)` —
  enforced by `tooling/verify/checks/decisions_index.py` against baseline.
- `tooling/standards/DECISIONS_INDEX.md` and `FILE_MAP.md` are generated;
  never edit them by hand. A generated file is never hand-resolved in a
  merge conflict: regenerate it (`gen_decisions_index.py`,
  `gen_file_map.py`) and stage the result. A conflict outside a branch's
  diagnosed set is an escalation, not an improvisation.

## Invariants (verified at every review)

Law only; rationale lives in `tooling/standards/ARCHITECTURE_DECISIONS.md`.
Each invariant has a permanent id `INV-NN`, never reused; a retired id is
listed in `tooling/verify/baselines/invariant_ids.retired`. Each ends with
`-- enforced by <check>.py`, whose docstring holds the full law, or with
`[no check]`: no enforcing check has been established for it yet.

- **INV-01** Secrets are structurally excluded from every assembled context,
  by query construction, never by instruction. What an NPC knows but conceals
  is a `knowledge` row with `is_secret = TRUE`, excluded at every assembler
  AND every propagation path (`analyze_overhearing` never sources a proposal
  from one). The creator's note on an entity (a `histoire` fact whose entity
  holds an `unaware` `is_secret` row on it) is excluded from `facet_reads`;
  only the Lore dossier opts in, plus the `creator` regime of `name_index`
  (Lore question, names panel, writing panel, condition interpreter). Token
  posing never indexes a creator-only or unscoped appellation. [no check]
- **INV-02** The MJ context assembler is scoped to the player's perception
  boundary: only what the player may perceive or already knows. Never
  NPC-private knowledge, secrets, internal names, non-public entities, or
  invisible relations. [no check]
- **INV-03** Membership reaches a model prompt only via
  `read_public_memberships`; `is_secret` rows never enter any prompt,
  including the holder's own, with no override parameter. The true `role`
  behind a `cover_role` never enters a prompt: the accessor resolves
  `cover_role ?? role`. Espionage rides on `goals` prose, never a confessable
  affiliation label. Declared faction roles live in `faction_role`
  (relational, never JSON). [no check]
- **INV-04** `npc_price` rows are seller configuration, injected ONLY into
  that seller's own dialogue context — never into `assemble_mj_context` or
  any other entity's context. A quoted price writes no canon; money moves via
  `resource_change` through the checkpoint. [no check]
- **INV-05** `discoverable_detail` is read by no assembler or prompt-building
  path. `hidden` content reaches a model ONLY via the post-selection
  `{detail_content}` injection in `_stream()` on a partial/success perception
  search (`domain="perception"`, `opposed_npc_id=None`); `ambient` content
  only via the pure predicate `active_signposts` (`scene_format.py`), passed
  into the MJ establishment call. A hidden `coutume` fact is a TRAP: never
  add `"hidden"` to `FACETS["coutume"].aspects`; every play reader filters
  `notorious_at_location` at query construction. [no check]
- **INV-06** `connects_to` and `borde` are location map topology, never a
  social signal; their `intensity` means nothing. Every gameplay reader of
  `relation` keyed on a character/player id is blind to them; the sole
  gameplay reader is `_location_neighbours`. A new world-wide relation scan
  MUST exclude both (`MAP_TOPOLOGY_TYPES`). [no check]
- **INV-07** PC knowledge is written `is_secret=False`; `_normalize_knowledge`
  is NPC-only and forces `is_secret=True` — never reuse it for a PC.
  `_normalize_player_knowledge` emits no `is_secret` key; `False` is applied
  at write time by the accept route (`create_player_character` via
  `writes.write_knowledge`), never by the generator. [no check]
- **INV-08** Two canon-write paths for rows: `_apply_mutation` and creator
  CRUD. A third covers canon STRUCTURE. -- enforced by
  `single_canon_write.py`, `runtime_ddl_guard.py`
- **INV-09** `scene_state` is a third, explicitly ephemeral write path:
  `_write_scene_state` archives the previous snapshot to `history[]` before
  every write; cleared to `{}` on conversation close; never canon — durable
  consequences require a `proposed_mutation`. [no check]
- **INV-10** History is sacred on BOTH write paths: any edit to `relation` or
  `knowledge` appends the previous state to `change_history`.
  `entity_type_history` is append-only by construction, with no
  `change_history` column — the rows ARE the history. [no check]
- **INV-11** Commit before touching any canon-writing path (`_apply_mutation`,
  the creator CRUD, the analyzers, and everything they call) — hard.
  Recommended before the `/say` flow or the interpretation phase. On SQLite,
  DDL participates in the surrounding transaction — a guarantee of the shared
  engine (`db.py`), never a per-site precaution. [no check]
- **INV-12** Hard deletes are a closed, named list; a new hard-delete path is
  named there, never added silently. -- enforced by `single_canon_write.py`
- **INV-13** The `ledger` is append-only: INSERT-only on both canon-write
  paths, corrections are new compensating lines, and no UPDATE/DELETE
  endpoint or code path touches a `ledger` row. [no check]
- **INV-14** `proposed_by='engine'` deterministic proposals
  (`_propose_engine_injury`, `_propose_engine_discovery`) follow the same
  review queue as AI proposals — never auto-applied. [no check]
- **INV-15** `skill_progress` is the one live auto-applied mutation: a roll's
  point (`proposed_by='engine_roll'`) applied through `_apply_mutation` at
  proposal time; `write_skill_progress` moves the rank. -- enforced by
  `skill_progression.py`
- **INV-16** A `knowledge` row is identified by its fact: `(entity_id,
  fact_id)` is unique. -- enforced by `knowledge_identity.py`
- **INV-17** A `fact_participant` row is the aboutness claim for every
  `knowledge` row on that fact. `role` is descriptive only, never a filter or
  a discriminator; `(fact_id, entity_id)` is unique, so every writer reads
  before it writes. [no check]
- **INV-18** Creator-direct create helpers never commit in their core; the
  commit boundary belongs to the caller. `create_entity`, `create_knowledge`,
  `open_entity_membership` each split into a commit-free core plus a thin
  route wrapper owning the single commit — never a `commit:` flag. [no check]
- **INV-19** All templated model calls resolve through
  `prompt_registry.effective_model`, the single model resolver; a new prompt
  usage adds a `PROMPT_REGISTRY` entry. -- enforced by `prompt_registry.py`
- **INV-20** UI-visible data never lives in JSON — relational only
  (exceptions justified in the check). -- enforced by `json_ui_boundary.py`
- **INV-21** A location with an active child is a zone, derived, never stored
  (`zone_rules.py`). Only `connects_to` is traversable and it never touches a
  zone; a link touching a zone is `borde`. A geographic link's type is
  derived from its endpoints (`link_locations`), never chosen. No being,
  item or discoverable detail is placed in a zone (`require_visitable`, at
  every placement write). -- enforced by `zone_placement.py`,
  `zone_map_links.py`
- **INV-22** A model names a fact only by a code from a
  `fact_refs.code_facts` list; code resolves it. [no check]

## Path-scoped rules

Invariants and notes that hold for one part of the code live in
`.claude/rules/<topic>.md`. Claude Code loads a rule file when a session
reads or edits a file matching its `paths:`; `/review-step` and
`/close-step` read every one on every commit. An invariant that must hold
wherever new code lands stays in this file. Invariant ids run on across all
of them.

- `gatherings.md` — gathering membership, encounters, passages.
- `mutation-pipeline.md` — analyzers, the world tick, appliers.
- `context-assembly.md` — NPC and MJ context, the play surface.
- `skills.md` — skills, definitions, skill gaps.
- `prompts.md` — prompt text and per-template models.
- `frontend.md` — the Svelte shell, Création registries, the build.
- `authoring-lore.md` — region generation, the Lore surface.
- `schema-migrations.md` — migrations, the boot guard, rollback.
- `local-models.md` — the local models and their thinking modes.
- `verify-checks.md` — how a verify check is written.

## Conventions

### File structure

The top level only. Every Python module, with its role, is listed in the
generated `tooling/standards/FILE_MAP.md`.

```
WG-Nia/
├── .claude/        # commands/, hooks/, rules/ (path-scoped), settings.json
├── frontend/       # Svelte + Vite sources; the build writes cockpit/static/
├── src/world_engine/  # the importable package (PYTHONPATH=src)
│   ├── models/     # SQLModel table classes
│   ├── writes/     # canon-write helpers by domain; schema.py is the DDL authority
│   └── cockpit/    # creator web UI (FastAPI, port 8000, loopback)
├── scripts/        # init, seed, backup, CLI tools, one migrate_*.py per schema step
├── tooling/
│   ├── tickets/, lots/, briefs/  # pipeline artifacts (filename is law); recon/ archived
│   ├── glue/       # gen_decisions_index.py, gen_file_map.py, escalation.py
│   ├── standards/  # decision registry; generated DECISIONS_INDEX.md, FILE_MAP.md
│   └── verify/     # run.py, checks/, baselines/, results/
├── world-engine-schema.md            # single authoritative schema; header = current version
├── world-engine-schema-changelog.md  # append-only schema log
├── CLAUDE.md       # this file (contract-checked)
└── pyproject.toml, requirements.txt, .env.example
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
- **Database URL:** `WORLD_ENGINE_ENV=prod|test` resolves the SQLite file
  (`docs/launch-procedure.md`); `WORLD_ENGINE_DATABASE_URL` overrides, else
  refuses to start. Every test/seed script guards the env pre-import (`env_guard.py`).
- **Initialize:** `python scripts/init_db.py` — idempotent.
- **Seed:** `python scripts/seed_pilot.py` — Verkhaal world, NPCs,
  relations, knowledge, prompt templates; idempotent; `upsert_prompt_template`
  writes prompt text (`prompt_version` v1) only on a virgin head — re-running
  never touches text once a version exists (S2), and still converges
  non-text head fields (name, variables, destination, notes, is_active)
  without losing other data.
- **Backup:** `python scripts/backup.py` — manual, SQLite online backup
  API, 2-file rotation to `~/.world_engine/backups/`.
- **CLI conversation:** `python scripts/talk.py` (requires `ollama serve`).
- **Analyze a conversation:**
  `python scripts/analyze_conversation.py <conversation_id>` — reads
  unanalyzed turns, writes `proposed_mutation` rows
  (`proposed_by='local_ai_window'`), advances `last_analyzed_turn`
  atomically. `--force` deletes *proposed* rows only, resets the cursor,
  re-analyzes the full transcript (reviewed rows are never deleted).
- **World cockpit:** `python scripts/cockpit.py` -> http://127.0.0.1:8000,
  loopback only; requires Ollama for all AI calls. Turn mechanics, overhearing
  accumulation, window-analysis triggers, batch review and Voyager ordering
  are documented in `tooling/standards/ARCHITECTURE_DECISIONS.md`.
- **Frontend build:** `cd frontend`, `npm ci`, `npm run build` -> writes the
  committed output under `src/world_engine/cockpit/static/`. The output is
  versioned on purpose; rebuild and commit after any `frontend/` edit.
  Node is needed to BUILD only -- a prod launch requires none.
- **Module map:** `python tooling/glue/gen_file_map.py` regenerates
  `tooling/standards/FILE_MAP.md` from module docstrings; `file_map.py`
  fails while it is stale or a module has no docstring.
- **Verify:** `python tooling/verify/run.py --ticket TICKET-NNNN` runs the
  checks that ticket links in its Machine-checkable section;
  `tooling/verify/checks/corpus_gate.py` runs every check in the directory,
  regardless of which ticket references it.

---

*Co-built with Claude, June 2026.*
