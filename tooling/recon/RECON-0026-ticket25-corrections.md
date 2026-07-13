# RECON-0026 — TICKET-0025 fallout: unclassified config tables + dead region-roles block

Report only. No action taken. Fetched fresh from `main`
(`codeload.github.com/niaairen31-ui/WG-Nia`), schema **v1.79** (TICKET-0025
tail: BRIEF-0025-a/-b/-c). All findings cite `file:line` against that tree.

---

## Finding 1 — three TICKET-0025 config tables are in NO K1 stratum, so their full-replace hard-deletes are structurally invisible

### 1a. The reference case (`faction_role`) is fully governed
- `faction_role` is in `[CANON_TABLES]` — `tooling/verify/canon_write_policy.txt:2`.
- Its write chokepoint is allowlisted — `canon_write_policy.txt` line
  `src/world_engine/writes.py::write_faction_role    faction_role`.
- Its hard-delete is named in the closed list — `CLAUDE.md:277`
  (`write_faction_role(mode="delete")`).

### 1b. The three new tables are in neither section
`[CANON_TABLES]` (`canon_write_policy.txt:2-4`) lists 21 tables ending
`... agenda agenda_step goal_agenda_link`. **`npc_price`,
`location_subculture`, `world_law` do not appear.** `[ALLOWED_SITES]`
(`canon_write_policy.txt:7+`) has no entry for any of them.

### 1c. Each does a full-replace hard-delete, all inside a `writes.py` chokepoint
- `write_npc_prices` -> `DELETE FROM npc_price WHERE entity_id` then re-insert
  — `src/world_engine/writes.py:781,808,811`.
- `write_location_subculture` -> `DELETE FROM location_subculture WHERE location_id`
  then re-insert — `src/world_engine/writes.py:817,854,859`.
- `write_world_laws` -> `DELETE FROM world_law WHERE world_id` then re-insert
  — `src/world_engine/writes.py:865,882,885`.

Schema confirms these are deliberate no-`change_history` config tables written
ONLY via their helper: `world_law` — `world-engine-schema.md:50`; `npc_price`
— `world-engine-schema.md:148`.

### 1d. Why the check does not see them
`single_canon_write.py` (docstring, lines 1-13): it attributes every
`.execute()`/`.exec()` and `.add()/.delete()` site to its table and fails
only when a **CANON** table is written from a `path::function` outside
`[ALLOWED_SITES]`; "Sites on non-canon (ephemeral/pipeline) tables are
ignored." Because the three tables are absent from `[CANON_TABLES]`, the
scan treats them exactly like ephemeral tables: their `DELETE FROM` is
ignored. A stray `DELETE FROM npc_price` added anywhere in `src/` today
passes `/verify` silently.

### 1e. Callers (for allowlist attribution — writes are function-grain inside the helper)
- `write_npc_prices`: `crud.py:985` (`set_npc_prices`, creator Tarifs editor).
- `write_location_subculture`: `crud.py:1007` (`set_location_subculture`).
  NOTE: also imported at `app.py:124` but **never called there** — dead import.
- `write_world_laws`: `app.py:2225` (`create_world`, world bootstrap, creator).

All three DELETE + re-insert sites are lexically inside the `writes.py`
helper, so a single `writes.py::<helper>` allowlist entry per table covers
both the delete and the insert (same function-grain rule that makes
`write_faction_role`'s single entry sufficient).

### 1f. Broader instance of the same gap (report only — beyond the three named)
- `goal_prerequisite`: `DELETE FROM goal_prerequisite` at
  `writes.py:956` inside `write_npc_goal_prerequisites`. That helper IS
  allowlisted, but attributed to `npc_goal` (the change_history snapshot);
  `goal_prerequisite` itself is NOT in `[CANON_TABLES]`, so its delete +
  insert are ignored. Introduced BRIEF-0024-a, predates TICKET-0025.
- `event_entity`: `DELETE FROM event_entity` at `writes.py:1403`. Not in
  `[CANON_TABLES]`. Introduced BRIEF-0025-c.
- `prompt_variable`: `DELETE FROM prompt_variable` at `writes.py:1481`.
  Child of `prompt_template` (pipeline-internal); ignoring it is
  doctrinally correct, but it is classified in no stratum explicitly.

### 1g. Root cause
K1 (ARCHITECTURE_DECISIONS, "CANON-WRITE DOCTRINE") requires every table to
fall into exactly one of canon / ephemeral / pipeline-internal, but there is
NO machine-checkable completeness guarantee. The only structural signal is
membership in `[CANON_TABLES]`; a new table that SHOULD be canon but is left
unlisted is silently downgraded to "ignored." The K1 prose figure of "15
canon tables" is itself already stale (the policy file lists 21).

---

## Finding 2 — dead role-list block in `commit_region` Stage 1 is genuinely dead; both commit paths already discard drafted roles

### 2a. The block is still present in live code
`app.py:720-727` (inside `commit_region`, Stage 1 factions):
```
roles = [ {"name": r["name"].strip(), "description": r.get("description") or ""}
          for r in (pub.get("roles") or [])
          if isinstance(r, dict) and (r.get("name") or "").strip() ]
if roles:
    entity_data["metadata"] = {"roles": roles}
```
BRIEF-0025-a did NOT touch it (contrary to the Claude Code note's assumption).

### 2b. The key it sets is read by no one — no error, silent discard
`_create_entity_core` (`crud.py:771`) applies base fields via
`_apply_base_fields` (`crud.py:609`), which iterates ONLY over
`ENTITY_BASE_FIELDS` (`crud.py:181-230`). `metadata` is not among them
(dropped by BRIEF-0025-a). `EntityWriteBody.entity` is a free `dict[str,Any]`
(`crud.py:626-627`), so the extra key is accepted and ignored. The commit
succeeds; the roles vanish. Not a crash — a silent drop.

### 2c. `_create_entity_core` never writes `faction_role`
Full read of `_create_entity_core` (`crud.py:771-846`): base fields,
extension row, optional primary `faction_membership` — no `faction_role`
write anywhere.

### 2d. NO accept/create path persists drafted roles — the two paths are symmetric
`write_faction_role` callers, exhaustive (`grep` over `src/`):
- `crud.py:1842,1871,1892,1893,1911` — the dedicated faction-role CRUD editor
  (creator manages roles AFTER the faction exists).
- `app.py:1456` — the `role_change` mutation consequence (NPC declares/occupies
  a role in play; L2 declare-and-occupy).
Neither `create_entity` (`crud.py:874`, single-entity accept) nor
`commit_region` (region accept) calls it. `pub.get("roles")` appears at
exactly one site in `app.py`: line 722, the dead block. The single-entity
faction accept path does not reference drafted roles at all.

**Net current behavior:** both the single-entity accept path and the
region-commit path DISCARD AI-drafted faction roles; the creator re-enters
them via the roles editor. The `commit_region` block writes a key nobody
reads; removing it changes no observable behavior.

### 2e. Consequence for the proposed fix
"Write drafted roles to `faction_role` in region-commit" would NOT restore
parity — it would CREATE an asymmetry (region persists, single-entity does
not). A consistent persist requires wiring BOTH paths (cleanest: the faction
branch of the shared `_create_entity_core`), which is a feature, not a
correction, and needs its own decisions (position from the AI's ranked list,
`max_holders` default, `changed_by`, casefold dedup vs the roles editor's
guarded unique index). It also touches the "AI never authors canon directly"
doctrine: drafted roles pass through no granular review.

---

## Docs cross-check
- Schema at HEAD: `world-engine-schema.md` — `Current schema version: v1.79`.
- Changelog tail: `world-engine-schema-changelog.md:11` (v1.79, BRIEF-0025-c),
  `:41` (v1.78, -b), `:81` (v1.77, -a), `:99` (v1.76, BRIEF-0024-d).
- Neither correction requires a schema change.
