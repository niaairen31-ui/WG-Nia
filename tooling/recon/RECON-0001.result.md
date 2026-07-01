# RECON-0001 — result

Report-only. All anchors below are real `path:line` in the code as it stands
today. No code was changed.

---

## 1. WORLD DELETE CASCADE

`world` is `src/world_engine/models.py:52`.

A cascade helper for this already exists and is live:
`delete_world_cascade(world_id, db)` at `src/world_engine/writes.py:438`,
called from the creator route `DELETE /api/worlds/{world_id}`
(`delete_world` at `src/world_engine/cockpit/app.py:1047`). This is NOT a
greenfield item — the spec's framing ("defines the delete cascade") should be
read as "confirm/audit the existing cascade," not "design one."

Tables with a real FK/reference to `world.id`, and the column, as declared in
`models.py`:

| Table | Column | models.py line |
|---|---|---|
| `entity` | `world_id` (NOT NULL) | 87 |
| `character` | `world_id` (NOT NULL, denormalized from `entity.world_id`) | 129 |
| `faction_membership` | `world_id` (NOT NULL) | 230 |
| `relation` | `world_id` (NOT NULL) | 267 |
| `ledger` | `world_id` (NOT NULL) | 343 |
| `session` | `world_id` (NOT NULL) | 364 |
| `gathering` | `world_id` (NOT NULL) | 436 |
| `conversation` | `world_id` (NOT NULL) | 475 |
| `proposed_mutation` | `world_id` (NOT NULL) | 531 |
| `event` | `world_id` (NOT NULL) | 572 |
| `skill_definition` | `world_id` (NOT NULL) | 662 |
| `discoverable_detail` | `world_id` (NOT NULL) | 728 |
| `prompt_template` | `world_id` (**nullable** — global seed templates use `world_id IS NULL`) | 784 |

Tables that reach `world` only *indirectly*, via `entity.id` or another
already-scoped table — no direct `world_id` column:

| Table | Indirect path |
|---|---|
| `location` | PK = `entity.id` |
| `faction` | PK = `entity.id` |
| `artifact` | PK = `entity.id` |
| `item` | PK = `entity.id` |
| `skill` | `character_id` -> `entity.id` |
| `knowledge` | `entity_id` -> `entity.id` (confirm: `models.py:293` class, FK on `entity_id`) |
| `gathering_member` | `gathering_id` -> `gathering.id` |
| `conversation_message` | `conversation_id` -> `conversation.id` |
| `batch` | `session_id` -> `session.id` |
| `pass_play` | `session_id` -> `session.id`, `batch_id` -> `batch.id` |

Tables with NO world scope at all: `user` (`models.py:761`, global accounts).

`delete_world_cascade` (`writes.py:438-531`) already deletes every one of the
above (direct and indirect) in dependency order, under
`PRAGMA defer_foreign_keys = ON` (`writes.py:461`), and deliberately skips
`prompt_template` rows with `world_id IS NULL` and the `user` table
(`writes.py:457-459, 527-528`). No orphan gap found against the schema as
read.

---

## 2. CANON-WRITE PATHS

`_apply_mutation` is at `src/world_engine/cockpit/app.py:691`.

Every DB-write site found OUTSIDE `_apply_mutation`, grouped by what it
actually writes:

**A. Canon tables, via the two sanctioned helper modules (not raw here, but
listed since a caller could bypass them — it doesn't):**
- `write_relation` — `writes.py:216` (mode="delta" new-row path), `writes.py:252` (mode="set" / existing-row path). Called by `_apply_mutation` (`relation_change`, `app.py:751`) and by `crud.py` (`create_relation`/`update_relation`).
- `write_knowledge` — `writes.py:318`. Called by `_apply_mutation` (`new_knowledge`, `resource_change` knowledge leg) and by `crud.py` (`create_knowledge`/`update_knowledge`) and `app.py:create_player_character` (knowledge seed).
- `write_ledger_entry` — `writes.py:358`. Called by `_apply_mutation` (`resource_change`) and `crud.py:create_ledger_entry`.
- `write_membership` — `writes.py:419` (open), `writes.py:430` (close). Called only by `crud.py` (`open_entity_membership`/`close_entity_membership`) — no `_apply_mutation` branch for this table.
- `delete_world_cascade` — `writes.py:465-531` (raw `DELETE`s). Called only by `app.py:delete_world` (line ~1070). Documented exception to "history is sacred" (see item 4).

**B. `_apply_mutation`'s own direct writes (inside the function, but the spec
asked to calibrate what's OUTSIDE it, so noting the branches for completeness):**
`status_change` (`app.py:824`), `item_update` (`app.py:842`), `knowledge_change`
(`app.py:869`), plus the `new_knowledge` discovery-flip side-write on
`discoverable_detail.discovered` (`app.py:801`).

**C. Creator-CRUD direct writes (`cockpit/crud.py`) — the second sanctioned
canon-write path, all entity/extension/skill/discoverable-detail rows:**
- `_create_entity_core` (core, commit-free) `crud.py:589,595`; commit lives in caller `create_entity` `crud.py:621`.
- `update_entity` `crud.py:653,667,678`.
- `delete_entity` `crud.py:700,702`.
- `create_relation` `crud.py:738`, `update_relation` `crud.py:761`, `delete_relation` `crud.py:772-773`.
- `_create_knowledge_core` (core) feeds `create_knowledge` `crud.py:810`; `update_knowledge` `crud.py:836`; `delete_knowledge` `crud.py:847-848`.
- `_open_membership_core` (core) feeds `open_entity_membership` `crud.py:945`; `close_entity_membership` `crud.py:964`.
- `update_skill_tier` `crud.py:1085-1086`.
- `create_skill_definition` `crud.py:1152` (definition) + `crud.py:1165` (backfill loop, one `Skill` row per existing PC) + `crud.py:1172` commit.
- `update_skill_definition` `crud.py:1207` (definition) + `crud.py:1216` (re-base loop updating dependent `skill.domain`) + `crud.py:1219` commit.
- `delete_skill_definition` `crud.py:1247` (dependent skills) + `crud.py:1248` (definition) + `crud.py:1249` commit — the second named hard-delete exception (see CLAUDE.md invariants).
- `create_discoverable_detail` `crud.py:1324-1325`, `update_discoverable_detail` `crud.py:1373-1374`, `delete_discoverable_detail` `crud.py:1387-1388`.
- `create_ledger_entry` `crud.py:1533` (via `write_ledger_entry`, INSERT-only).

**D. `app.py` route-level writes on canon rows (world/PC bootstrap — not
gated behind `proposed_mutation`, by design; these are creator-direct actions):**
- `activate_world` `app.py:983,986-987`; `create_world` `app.py:1012,1016,1019-1020`; `_activate_world_core` `app.py:1039,1043`; `delete_world` `app.py:1070` (calls `delete_world_cascade` then commits).
- `create_player_character` `app.py:1176,1187,1189,1197,1217` (entity + character + 4 base skills + one skill per `skill_definition`).
- `commit_region` `app.py:522` — the one multi-entity atomic commit, already documented as a single transaction.

**E. Non-canon / ephemeral / metadata writes (never gated by `proposed_mutation`
by design — these are session bookkeeping, not world state):**
- `session` (`GameSession`) open — `_get_or_open_session` `app.py:1286-1287`.
- `gathering`/`gathering_member` — `gathering.py:240,242,250` (`generate_gatherings`), `gathering.py:277` (`close_open_memberships`), `gathering.py:317,323` (`migrate_npc` join), `gathering.py:351-352` (`migrate_npc` auto-dissolve); `app.py:1497,1504-1505` (`_join_gathering`); `app.py:3921-3922`/`3991`/`4047`/`4062-4064` (`scene_join`/`scene_leave`); `app.py:4192,4205` (`_perform_travel`); `app.py:4138-4139` (dissolve on scene entry, inside `enter_scene`/`update_scene_state` neighborhood — see item 6 for `enter_location`'s dissolve-before-create at `gathering.py:391-395`).
- `conversation`/`conversation_message` — `app.py:2482-2483` (`start_conversation`), `app.py:2591,2598` and every `persist_db.add(ConversationMessage(...))` inside `say` (`app.py:2675,3043,3297,3515,3555,3577` + matching commits), `app.py:3631-3632` (end of turn), `app.py:3921-3922` (`scene_join`), `app.py:4138-4139`/`4382-4383` (`analyze_conversation_endpoint` — resets `last_analyzed_turn`), `app.py:4209,4211` (`_perform_travel`, char/gm rows), `scripts/talk.py:99-100,151-152,178-187,207-216,223-224` (CLI live-conversation flow — mirrors `say` outside the cockpit process).
- `scene_state` (JSON column on `conversation`, ephemeral) — `app.py:3094-3095` (`_write_scene_state`).
- `proposed_mutation` rows (status='proposed' only — never applied here):
  - engine proposals: `_propose_engine_injury` `app.py:2218`, `_propose_engine_discovery` `app.py:2251`.
  - overhearing: `app.py:3604,3606` (inside `say`, Tier 4).
  - window analysis: `analyzer.py:818,820-821` (`analyze_window`).
  - mutation row *status* updates (not canon) on review: `reject_mutation` `app.py:4468-4469`; `approve_mutation` `app.py:4530-4531` (success) / `4541-4542` (failure) — both wrap a call to `_apply_mutation` inside `db.begin_nested()`; `batch_review_mutations` `app.py:4618-4619,4629-4630,4652-4653` (same per-row pattern, looped).
  - CLI equivalent: `scripts/analyze_conversation.py:83-89` — same `--force` (delete-only-`proposed`, reset `last_analyzed_turn`) contract as `app.py:4367-4383`.
- `world.is_active` flips ride inside D above (not a separate category).

**Conclusion for the `single_canon_write` check:** every write to `relation`,
`knowledge`, `ledger`, `faction_membership`, `entity`+extension tables
(`character`/`location`/`faction`/`artifact`/`item`), `skill`,
`skill_definition`, `discoverable_detail` goes through exactly one of:
`_apply_mutation` (app.py:691) or `cockpit/crud.py`'s routes (categories A–C
above), with the single documented multi-table exception being
`_apply_mutation`'s `resource_change` branch (ledger + knowledge in one
SAVEPOINT, `app.py:872-947`) and `commit_region`'s single atomic
multi-entity commit (`app.py:285-537`). Everything in category E is
non-canon/ephemeral/session bookkeeping or `proposed_mutation` rows still
awaiting review — a checker should NOT flag these as canon-write violations.

---

## 3. DB-TOUCH / MIGRATION SIGNATURE

No migrations directory, no Alembic, no ORM-driven auto-migration tool.
Two distinct mechanisms:

- **Fresh-DB DDL:** `create_db_and_tables()` at `src/world_engine/db.py:55-60`
  — `SQLModel.metadata.create_all(engine)` (`db.py:60`), invoked by
  `scripts/init_db.py:26`. Creates every table currently declared in
  `models.py`; idempotent (`create_all` skips existing tables), but it does
  **not** add new columns to an already-existing table.
- **Schema changes to an existing DB:** one hand-written, one-off script per
  schema version under `scripts/migrate_v1_*.py` (12 found — v1.16, v1.21,
  v1.24, v1.26, v1.30, v1.31, v1.38, v1.39, v1.40, v1.41, v1.44, v1.54, v1.57,
  v1.63, v1.65, v1.8 — exact list via `scripts/migrate_*`). Signature
  confirmed at `scripts/migrate_v1_57.py:32-46`: `sqlalchemy.inspect(engine)`
  to check for existing columns/indexes, then `engine.begin()` +
  raw `text("ALTER TABLE ... ADD COLUMN ...")` / `text("UPDATE ...")`, guarded
  idempotent (no-op print if already applied). Data-only migrations (no DDL)
  use the same `engine.begin()` + raw `text()` INSERT/UPDATE pattern —
  confirmed at `scripts/migrate_v1_65_pc_skill_backfill.py:42-90`.

**Runtime write-opening code paths** (what should count as `db_write` for a
pre-backup hook predicate): every FastAPI route in
`src/world_engine/cockpit/app.py` and `src/world_engine/cockpit/crud.py` that
calls `db.add`/`db.delete`/`db.commit`/raw `DELETE`/`UPDATE`/`INSERT` (full
enumeration in item 2), plus the two CLI scripts `scripts/talk.py` and
`scripts/analyze_conversation.py`, plus every `scripts/migrate_v1_*.py` file,
plus `scripts/seed_pilot.py` (not read in depth here, but known from
CLAUDE.md to use `upsert_prompt_template` — a write path). All of these open
the DB via the shared `engine`/`Session` from `src/world_engine/db.py` — there
is no second engine or connection string in the codebase.

---

## 4. DELETE ENTRY POINT

Already exists — this is not a gap. `DELETE /api/worlds/{world_id}` route
`delete_world` at `src/world_engine/cockpit/app.py:1047`, calling
`writes.delete_world_cascade` (`writes.py:438`). Confirmed live (not a stub):
handles the zero-worlds-remaining case and the re-activate-survivor case
(`app.py:1047-1080` per BRIEF-54, referenced in CLAUDE.md).

---

## 5. BACKUP SIGNATURE

`scripts/backup.py` — standalone script (no CLI args), run as
`python scripts/backup.py`.

- Resolves the live DB path from the shared `engine` (`backup.py:29,42-49`) —
  refuses non-sqlite or in-memory engines.
- Refuses to back up a missing file (`backup.py:64-68`) or a file with zero
  `entity` rows (`backup.py:70-74`), printing entity/location counts first.
- Uses SQLite's native online backup API (`sqlite3.Connection.backup`,
  `backup.py:88-94`), writing to a `.tmp` file then `os.replace` for an
  atomic swap (`backup.py:79-101`).
- Target directory: `~/.world_engine/backups/`, confirmed —
  `DEFAULT_BACKUP_DIR = Path.home() / ".world_engine" / "backups"`
  (`backup.py:38`), overridable via `WORLD_ENGINE_BACKUP_DIR`.
- **Rotation-keep-2 confirmed**: `KEEP = 2` (`backup.py:32`), pruning applied
  at `backup.py:104-112` (`sorted(..., reverse=True)[KEEP:]` unlinked).

**Important finding, not in the RECON spec's assumption:** `backup.py` has
**zero call-sites** anywhere in the codebase (`app.py`, `crud.py`, hooks,
scripts) — grep for `backup` across `.claude/hooks/` finds only
`block-db-in-git.ps1`, `block-main-push.ps1`, `session-start.ps1`, none of
which invoke it. This is corroborated by
`tooling/standards/ARCHITECTURE_DECISIONS.md:3203-3208` ("F2 — no
auto-backup... has zero existing call-sites... BRIEF-54 does not import it or
call it from the delete path... considered and explicitly rejected"). CLAUDE.md's
ticket-pipeline section states "the backup hook runs first" for `db_write` /
`migration` / `destructive_data` danger classes — **this hook does not exist
in the codebase today**. It is a manual, documented pre-session step only. Any
brief that assumes an automated pre-write backup hook is currently wrong
about the living code; that hook would need to be built.

---

## 6. STRUCTURAL INVARIANT SITES

- **Query-level secret exclusion:** `src/world_engine/context.py:242-245` —
  the main NPC-speakable-knowledge filter (`not k.is_secret and intensity >=
  k.share_threshold`), inside the NPC context assembler. A second,
  structurally distinct exclusion for faction membership is at
  `context.py:119` (`FactionMembership.is_secret == False` in the query
  itself, not a post-filter). `discoverable_detail` is excluded from every
  assembler by simply never being queried there (no line to cite — confirmed
  absent from `context.py` entirely; the only reader is the post-selection
  injection in `_stream()`/`say`, per CLAUDE.md).
- **B1 per-NPC uniqueness:** enforced at construction time in
  `generate_gatherings` (`src/world_engine/gathering.py:180-253`, the
  completeness net noted at `gathering.py:127-130,163,192`), and repaired on
  the join/migrate paths by `close_open_memberships`
  (`gathering.py:256-278`) and `migrate_npc` (`gathering.py:281-352`, which
  calls `close_open_memberships` at `gathering.py:314` before inserting the
  new membership at `gathering.py:317`). Dissolve-before-create for the
  single-player entry point lives in the caller, `enter_location`
  (`gathering.py:355-397`), exactly as CLAUDE.md's invariant states — the
  dissolve loop is at `gathering.py:372-395`, strictly separate from
  `generate_gatherings`.

---

## 7. CANON-WRITE SURFACE

Mostly confirmed, with one caveat. `src/world_engine/cockpit/` (`app.py` +
`crud.py`) is the sole surface that ever writes to the canon tables listed in
item 2's conclusion (via `_apply_mutation` or the creator CRUD routes) — no
other module or script calls `write_relation`, `write_knowledge`,
`write_ledger_entry`, `write_membership`, or touches `entity`/extension/
`skill`/`skill_definition`/`discoverable_detail` directly.

Caveat: `scripts/talk.py` and `scripts/analyze_conversation.py` are a second,
CLI-only runtime surface that DOES write to the database — but only to
`session`/`conversation`/`conversation_message` (non-canon, ephemeral/session
bookkeeping) and to `proposed_mutation` with `status='proposed'`
(`scripts/analyze_conversation.py` mirrors `app.py`'s
`analyze_conversation_endpoint` `--force` contract exactly, including
"reviewed rows are never deleted"). Neither script ever calls
`_apply_mutation` or any creator-CRUD function — a proposal made via
`talk.py`/`analyze_conversation.py` can only be approved/applied later
through the cockpit. So the precise statement is: **`cockpit/` is the sole
surface that writes CANON; it is not the only runtime surface that writes to
the database at all.** `entry point world_engine.cockpit.app:app` is confirmed:
`app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)`
at `src/world_engine/cockpit/app.py:98`.
