# BRIEF — Step "Metadata key extraction: physical_tier column, npc_price table, drop entity.metadata"

## Context

TICKET-0024's duplication bug was caused by a UI field living inside an
`entity.metadata` JSON key that RECON did not trace. BRIEF-0024-d (merged,
schema v1.76) removed the `roles` key. Two keys remain in live use —
`physical_tier` (NPC sheet "Carrure", AI-authoring accept path, opposed-roll
reader) and `price_list` (Tarifs editor BRIEF-20, seller-tariff prompt
injection) — plus the raw "Metadata (JSON)" textarea in the entity form.
This brief extracts both keys to relational storage and drops the
`entity.metadata` column entirely. Standing directive (TICKET-0025): no JSON
storage for UI-visible data — relational tables and columns only.

## Scope IN

1. `src/world_engine/models.py` — add to `Character`:
   `physical_tier: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})`
   with this comment verbatim above it:
   ```
   # Schema vX.YY, TICKET-0025, BRIEF-0025-a: physical resistance tier for
   # opposed rolls (resolution.py). Migrated from entity.metadata
   # ['physical_tier'] — UI-visible data is never stored in JSON
   # (json_ui_boundary). 0 = untrained default.
   ```

2. `src/world_engine/models.py` — new table `NpcPrice`
   (`__tablename__ = "npc_price"`):
   - `id` (uuid pk), `world_id` (FK world.id, not null), `entity_id`
     (FK entity.id, not null), `tag: str`, `amount: int`.
   - Unique index `idx_npc_price_tag` on
     `(entity_id, text("tag COLLATE NOCASE"))` — same structural
     case-duplicate guard as `faction_role`.
   - Header comment verbatim:
   ```
   # npc_price  (seller tariff lines, schema vX.YY, TICKET-0025,
   # BRIEF-0025-a — replaces entity.metadata['price_list'], BRIEF-20)
   #
   # Curated config, same family as faction_role: no change_history column,
   # full-replace writes, hard delete of a line is the sanctioned edit
   # (named doctrine exception — logged in ARCHITECTURE_DECISIONS). Read by
   # the seller-tariff block of assemble_npc_context; written ONLY via
   # writes.write_npc_prices (creator Tarifs editor).
   ```

3. `src/world_engine/writes.py` — new helper `write_npc_prices(db, *,
   entity, prices: dict[str, int], changed_by: str) -> list[NpcPrice]`:
   full-replace semantics (delete this entity's rows, insert one row per
   `(tag, amount)` pair), mirroring the editor's current read-merge-write
   contract. Validate: entity is a character, amounts are ints >= 0, tags
   non-empty after strip. Caller commits.

4. `src/world_engine/cockpit/crud.py`:
   - Remove `{"name": "metadata", "label": "Metadata (JSON)", "kind": "json"}`
     from `ENTITY_BASE_FIELDS`, remove the `attr = "metadata_"` mapping
     (line ~588) and the `"metadata": e.metadata_` line in the entity
     detail serializer (line ~456).
   - Add to the character registry fields:
     `{"name": "physical_tier", "label": "Physical tier (Carrure)", "kind": "number", "min": 0, "default": 0}`.

5. `src/world_engine/cockpit/app.py`:
   - NPC authoring accept path (line ~785): write
     `ext_data["physical_tier"] = pub["physical_tier"]` instead of
     `entity_data["metadata"] = {...}`.
   - Opposed-roll reader (line ~4312): replace
     `(opposed_entity.metadata_ or {}).get("physical_tier", 0)` with a
     `db.get(Character, opposed_npc_id)` read, `.physical_tier` (default 0
     when the character row is missing).
   - New endpoint `PUT /api/entities/{id}/prices` accepting
     `{"prices": {tag: amount}}`, routed through `write_npc_prices`.
     Entity detail response for characters gains `"prices": {tag: amount}`
     assembled from `npc_price` rows (preserves the client shape the Tarifs
     editor expects).

6. `src/world_engine/context.py` (line ~434): seller-tariff block reads
   `npc_price` rows for the NPC (`select(NpcPrice).where(entity_id == ...)`)
   instead of `metadata_.get("price_list")`. Rendered prompt text stays
   byte-identical for the same data.

7. `src/world_engine/cockpit/index.html`:
   - Tarifs editor (line ~6354): `authorRenderPricing` reads
     `detail.prices`; `authorPriceListMutate` becomes a single
     `PUT /api/entities/{id}/prices` of the full dict — the read-merge-write
     dance on metadata is deleted with the metadata field.
   - AI-authoring transfer (line ~6093): fill the new `physical_tier` form
     field instead of splicing JSON into the metadata textarea.
   - Character sheet "Carrure" display: source from the new field.

8. `scripts/seed_pilot.py`: replace the `{"price_list": {...}}` metadata
   seed (line ~2096) with `npc_price` row creation via `write_npc_prices`;
   move any `physical_tier` seeding to the column.

9. Migration script `scripts/migrate_vX_YY_metadata_extraction.py`
   (executor assigns the version number, CLAUDE.md convention), modeled on
   `migrate_v1_76_faction_role_table.py`. In ONE transaction:
   a. Add `character.physical_tier` (server default 0); create `npc_price`
      + unique index.
   b. For every entity: copy `metadata['physical_tier']` (int) into the
      character row; copy `metadata['price_list']` entries into `npc_price`
      rows (`created via 'migration:0025-a'` provenance is NOT a column —
      note it in the migration log output only).
   c. Read-only validation pass BEFORE any write: any entity whose
      `metadata` contains a key OTHER than `physical_tier` / `price_list`
      aborts the WHOLE migration, listing entity id + offending keys.
      Fail-closed: unknown data is never silently dropped.
   d. Drop the `entity.metadata` column (SQLite >= 3.35 guard, same as
      0024-d step f).
   e. Idempotent: skips entirely once `npc_price` exists.

## Scope OUT

- The dedicated JSON columns (`secrets`, `subculture`, `coordinates`,
  `fundamental_laws`) — BRIEF-0025-b.
- `goal_prerequisite`, `event_entity`, `prompt_variable` tables and the
  `json_ui_boundary` verify check — BRIEF-0025-c.
- No `change_history` on `npc_price` (curated config family) — do not add
  one "for safety".
- No per-line price endpoints (add/rename/delete REST verbs) — full-replace
  only, matching the current editor contract. Minimal first.
- No ordering column on `npc_price` — the editor renders key order today
  with no order semantics; do not invent one.
- No currency/unit modeling on prices; `amount` stays a bare int (ledger
  integration is a separate future concern).
- Do not touch `faction_role` or any 0024 surface beyond the two named
  call sites.
- Do not generalize `write_npc_prices` into a generic key-value writer.

## Invariants to defend

- Two sanctioned canon-write paths only: the new prices endpoint and seed
  MUST route through `writes.write_npc_prices` — no bare `NpcPrice(` or
  `db.add` outside writes.py (single_canon_write will be extended in -c;
  respect it now anyway).
- History is sacred: `npc_price` full-replace hard delete is a NAMED
  exception (curated config, faction_role family) — it must be called out
  in the model comment (verbatim text above) and nowhere silently extended
  to other tables.
- Fail-closed migration: unknown metadata keys abort everything (Scope IN
  9c); no partial writes.
- JSON columns require dict reassignment — moot after this brief for
  `entity.metadata`, but the migration's strip/validation pass must read
  the raw column, never mutate in place.

## Done means

- [ ] `python scripts/migrate_vX_YY_metadata_extraction.py` on a copy of the
  live DB completes; re-running it is a no-op (idempotence proven).
- [ ] After migration: `PRAGMA table_info(entity)` shows no `metadata`
  column; `PRAGMA table_info(character)` shows `physical_tier`;
  `SELECT count(*) FROM npc_price` equals the number of seeded tariff lines.
- [ ] A DB fixture with an entity carrying an unexpected metadata key makes
  the migration abort with the entity id and key named, and writes nothing.
- [ ] Cockpit entity form shows no "Metadata (JSON)" field; character form
  shows a numeric "Physical tier (Carrure)" field that persists.
- [ ] Tarifs editor: adding, editing, and removing a tariff line persists
  across a reload; `npc_price` rows match the editor state.
- [ ] Opposed physical resolution against an NPC with `physical_tier = 2`
  uses tier 2 (log line at app.py resolution INFO confirms).
- [ ] Prompt preview for a seller NPC renders the identical tariff block as
  pre-migration for identical data.
- [ ] `python tooling/verify/run.py` green.
- [ ] Live deployment sequence executed in order: `python scripts/backup.py`
  -> migration -> `python tooling/verify/run.py` -> live smoke (Tarifs edit
  + one opposed roll).
- [ ] /review-step and /close-step runs (engine code touched).

## Docs to update

- `world-engine-schema-changelog.md`: new entry (executor assigns version)
  — `character.physical_tier` added, `npc_price` created,
  `entity.metadata` DROPPED.
- `world-engine-schema.md`: bump the `Current schema version:` header only.
- `ARCHITECTURE_DECISIONS.md`: short entry "npc_price hard-delete named
  exception (curated config family)" — the full TICKET-0025 decision record
  lands in BRIEF-0025-c.
- `CLAUDE.md`: no change in this brief (the invariant line lands with the
  check in -c).
