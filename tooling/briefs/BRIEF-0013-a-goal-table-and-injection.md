# BRIEF — Step "NPC goal table + context injection" (BRIEF-0013-a)

## Context

TICKET-0013 (NPC goals — in-scene volition) is fully designed and locked;
this is the first of its three briefs. TICKET-0011 (prompt versioning,
v1.68) and TICKET-0012 (prompt lean rewrite) are closed — all anchors below
are against post-0012 `main`. This step ships the structure (`npc_goal`
table) together with its first reader (the `TES OBJECTIFS` section in
`assemble_npc_context`) plus the creator's manual authority over goals
(CRUD on the character sheet). The generator (BRIEF-0013-b) and the
behaviour loop — vote signal, `goal_change`, dialogue directive
(BRIEF-0013-c) — come after.

## Scope IN

1. **`NpcGoal` model** — `src/world_engine/models.py`, new table class
   placed after `Knowledge` (models.py:292 is the shape reference,
   including its `change_history` JSON idiom at models.py:322-325):

   - `__tablename__ = "npc_goal"`
   - `id: str` — `default_factory=_uuid`, primary key
   - `world_id: str` — FK `world.id`, NOT NULL
   - `npc_id: str` — FK `entity.id`, NOT NULL
   - `description: str` — NOT NULL. **Immutable after insert** (see
     invariants: a "changed" goal is a closed goal plus a new row).
   - `horizon: str` — `CheckConstraint("horizon IN ('short','long')",
     name="ck_npc_goal_horizon")`
   - `status: str` — default `"active"`, server_default `'active'`,
     `CheckConstraint("status IN ('active','completed','abandoned')",
     name="ck_npc_goal_status")`
   - `created_at` / `updated_at` — `_created_ts()` idiom
   - `change_history: list` — JSON, NOT NULL, server_default `'[]'`
   - `Index("idx_npc_goal_npc_status", "npc_id", "status")`

2. **Migration** — `scripts/migrate_v1_69_npc_goal.py`, purely additive:
   `CREATE TABLE npc_goal` (+ both CHECKs + index), no data movement, no
   backfill. Follow the existing migration-script idiom (post-check that
   the table and index exist; idempotent re-run safe). Executor confirms
   v1.69 is still the next number against
   `world-engine-schema.md` (`Current schema version:` line) before
   writing; if the head has moved, renumber and say so in the report.

3. **Write helpers** — `src/world_engine/writes.py`, placed after
   `write_membership` (writes.py:450), mirroring `write_knowledge`
   (writes.py:282) in style and docstring discipline:

   - `write_npc_goal(db, *, world_id, npc_id, description, horizon,
     changed_by) -> NpcGoal` — validates `horizon`, inserts an `active`
     row. Commit-free (caller owns the transaction), consistent with the
     other helpers.
   - `write_npc_goal_status(db, *, goal, new_status, changed_by) ->
     NpcGoal` — allowed transitions are exactly `active → completed` and
     `active → abandoned`. Any other transition (including reopening a
     closed goal) raises `ValueError` — a revived goal is a NEW row, never
     a reopened one. Before mutating, append to `change_history` a
     snapshot `{"status": <previous>, "updated_at": <previous ISO>,
     "changed_by": <changed_by>}` (mirror `_append_knowledge_history`,
     writes.py:140), then set `status` and `updated_at`.
   - These two helpers are the ONLY code paths that insert or update
     `npc_goal` rows. Extend the `single_canon_write.py` function-grain
     allowlist accordingly.

4. **Creator CRUD** — `src/world_engine/cockpit/crud.py`, placed next to
   the knowledge endpoints (crud.py:792/820) and following their idiom
   (active-world scoping via `_world_id(db)`, 404 on cross-world ids):

   - `GET /api/entities/{entity_id}/goals` — all goals for the character,
     active first, then newest first within each status group.
   - `POST /api/entities/{entity_id}/goals` (201) — body
     `{description, horizon}`. 422 if `horizon` invalid, `description`
     empty, or the target entity is not a character with
     `character_type == "npc"` (goals are NPC interiority — no player
     goals this ticket). Writes via `write_npc_goal`
     (`changed_by="creator"`).
   - `POST /api/goals/{goal_id}/status` — body
     `{status: "completed"|"abandoned"}`. 422 on invalid value or invalid
     transition (surface the `ValueError` message). Writes via
     `write_npc_goal_status` (`changed_by="creator"`).

5. **Character-sheet UI** — cockpit character sheet gains an
   « Objectifs » block mirroring the existing knowledge block's HTMX
   idiom: list (horizon tag + description + status pill; closed goals
   dimmed), an add form (horizon select `short`/`long` + description
   textarea), and per-active-goal « Accompli » / « Abandonné » buttons
   hitting the status endpoint. NPC sheets only — the block does not
   render for player characters.

6. **Context injection (Q1/S1)** — `src/world_engine/context.py`:

   - New constant in the section-header block (context.py:48-56):
     `H_GOALS = "TES OBJECTIFS"`.
   - In `assemble_npc_context` (context.py:168): build a `goals_section`
     from two queries constructed as follows — the most recent ACTIVE
     `long` goal (`ORDER BY created_at DESC LIMIT 1`) and the 2 most
     recent ACTIVE `short` goals (`ORDER BY created_at DESC LIMIT 2`),
     both filtered `npc_id == npc_id, status == "active"` at query
     construction. The read-side LIMIT is the S1 bound — no write-side
     cap exists anywhere.
   - Section body, verbatim format, long first then shorts
     (newest first):

     ```
     [LONG TERME] {description}
     [COURT TERME] {description}
     [COURT TERME] {description}
     ```

     No intro sentence, no goal ids, no status text — lean (0012
     discipline). Lines for missing horizons are simply absent.
   - Placement: the section is concatenated immediately AFTER
     `_section(H_IDENTITY, identity)` and before `_section(H_SETTING, …)`
     in the return assembly (context.py:391-404). When the NPC has no
     active goals, the section is omitted entirely (same pattern as
     `company_section`, context.py:346).
   - `assemble_mj_context` (context.py:419) is NOT touched. No `NpcGoal`
     import is reachable from it (see item 7).

7. **N1 verify check** — new `tooling/verify/checks/npc_goal_read.py`,
   same mechanical philosophy as `single_canon_write.py` (AST-based):

   - Rule 1 (module allowlist): the identifier `NpcGoal` may appear only
     in `src/world_engine/models.py`, `src/world_engine/writes.py`,
     `src/world_engine/context.py`, `src/world_engine/cockpit/crud.py`,
     `scripts/migrate_v1_69_npc_goal.py`, and the check itself.
     (BRIEF-0013-b/c will extend this list; keep it minimal now.)
   - Rule 2 (MJ boundary): parse `context.py`, locate the `FunctionDef`
     for `assemble_mj_context` (and any helper functions defined after it
     in the MJ block), and assert no `Name`/`Attribute` node referencing
     `NpcGoal` (or the string `"npc_goal"`) appears within their spans.
   - Wire the check into `tooling/verify/run.py` alongside the existing
     checks.

8. **Docs** — see "Docs to update".

## Scope OUT

- **The goal generator** (`pt-npc-goals` template, `generate_npc_goals`,
  region wiring, creation pre-fill, backfill endpoint, sheet
  « Générer les buts » button) — all of it is BRIEF-0013-b. Do NOT seed
  any new prompt template this step.
- **The behaviour loop** — initiative-vote signal (R1), `goal_change`
  mutation type (emit AND apply sides), the D1 dialogue-template
  directive — all BRIEF-0013-c. `_CANONICAL_TYPES`, `_apply_mutation`,
  `_signal_line`, and every prompt template are untouched this step.
- **`parent_goal_id` / goal hierarchy (F2)** — explicitly deferred with a
  named trigger; do not add the column "while you're here".
- **Per-goal `is_secret` flag (N3)** — deferred; every goal is already
  secret by construction under N1.
- **Player-character goals** — not scoped; the CRUD rejects them.
- **Any TICKET-0014 machinery** (off-screen tick, scoped approval,
  pre-authorization) — different ticket, not designed yet.
- **`assemble_mj_context` and the region manifest contract** — untouched.
- **No edit/reopen endpoints** — description immutability and the
  closed-is-closed rule are design, not omissions.

## Invariants to defend

- **Two sanctioned canon-write paths through `writes.py` helpers** — the
  new table joins the regime on day one: creator CRUD calls
  `write_npc_goal`/`write_npc_goal_status`; nothing else writes.
  `single_canon_write.py`'s allowlist is extended, never bypassed.
- **History is sacred** — status transitions append to `change_history`
  before mutating; descriptions are immutable; no DELETE path exists.
- **Secrets excluded structurally (N1)** — the MJ assembler never gains a
  goal query; enforced by the new AST check, not by convention.
- **No structure without a reader** — the reader (Q1 injection) ships in
  this same brief; the check and the CRUD are not the reader, the
  injection is.
- **Minimal first** — flat table, no hierarchy, no caps, no player goals.

## Done means

- [ ] `python scripts/migrate_v1_69_npc_goal.py` runs on a copy of the live
  DB; `npc_goal` exists with `ck_npc_goal_horizon`, `ck_npc_goal_status`,
  and `idx_npc_goal_npc_status`; re-running it is a no-op.
- [ ] `POST /api/entities/{npc_id}/goals` creates a goal visible in
  `GET /api/entities/{npc_id}/goals`; posting to a player character
  returns 422.
- [ ] `POST /api/goals/{id}/status` with `completed` closes an active
  goal and appends one `change_history` snapshot; a second status change
  on the same goal returns 422.
- [ ] The character sheet shows the « Objectifs » block on an NPC and not
  on the player character.
- [ ] With 1 long + 3 short active goals hand-created on one NPC, the
  assembled-context preview shows exactly the `TES OBJECTIFS` section
  with the long line + the 2 NEWEST short lines, placed between
  `QUI TU ES` and `OÙ TU TE TROUVES`; with zero goals, the section is
  absent.
- [ ] The MJ context preview for the same scene contains no trace of any
  goal.
- [ ] `tooling/verify/run.py` passes, including the new
  `npc_goal_read.py` check and the extended `single_canon_write.py`.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md` — bump `Current schema version:` to v1.69; add
  the `npc_goal` table section (fields, CHECKs, index, immutability NOTE:
  "description is immutable after insert; a changed goal is a closed goal
  plus a new row; status transitions are one-way, active → closed only").
- `world-engine-schema-changelog.md` — prepend the v1.69 entry (table,
  constraints, the two `writes.py` helpers, the N1 read boundary).
- `ARCHITECTURE_DECISIONS.md` — new section "NPC GOALS — in-scene volition
  (TICKET-0013, BRIEF-0013-a, schema v1.69)" recording: F1 flat shape, Q1
  injection + S1 read-side bound, N1 structural MJ exclusion + the AST
  check, immutable-description rule, one-way status transitions. Append to
  "Deferred decisions": **F2** (goal hierarchy — reactivate when a reader
  exploits parentage, e.g. "short completed → model proposes the next step
  of the parent long goal") and **goal-proposal pre-authorization** (a
  conscious future doctrinal exception to *model proposes, code judges*;
  never a drift).
- `CLAUDE.md` — untouched (line budget; the invariant lives in
  ARCHITECTURE_DECISIONS and the mechanical check).
