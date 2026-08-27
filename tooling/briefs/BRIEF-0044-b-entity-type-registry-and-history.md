# BRIEF — Step "entity_type registry + entity_type_history (A1, Dgov1)"

## Context

The socle needs the governed manifest that plane-2 reconciliation (BRIEF-0044-d),
the runtime-DDL writer (BRIEF-0044-c), and B1 quarantine (BRIEF-0044-e) all read.
This step ships the two static tables ONLY: `entity_type` (the per-world runtime-type
registry, with Dgov1 governance columns reserved) and `entity_type_history` (A1: the
append-only DDL-event log). No writer, no DDL emission, no traits — those land in the
same ticket at BRIEF-0044-c/onward.

## Mini-RECON (Claude Code, pre-implementation — verify live before coding)

Report-only; confirm, then implement.
1. World-scoped config precedent (NOT the entity-extension shape): `LocationTypeCatalog`
   (`src/world_engine/models/canon.py:246`) — `id, world_id, name, ...` with a
   `UNIQUE (world_id, name COLLATE NOCASE)` index. `entity_type` mirrors this shape,
   not the `character`/`location` extension shape.
2. Append-only history precedent: `Ledger` (`canon.py:662`) and the "rows ARE the
   history" note on `FactionMembership`/`FactionRole` (`canon.py:471`). `entity_type_history`
   has NO `change_history` column — the rows are the history.
3. Closed-vocab-via-CHECK precedent: confirm how existing closed vocabularies are
   enforced (e.g. `role_closed_vocab` check + any CHECK constraints) so the `event`
   and `status` vocabularies use the same idiom.
4. Extension PK shape for the FUTURE runtime tables (context only, not built here):
   `id: str = Field(primary_key=True, foreign_key="entity.id")` at `canon.py:155`
   (Character), `:213` (Location), `:763` (Item). BRIEF-0044-c will reproduce this
   for `ext_*`; this brief only needs to know the target shape.

## Scope IN

1. **Table `entity_type`** in `src/world_engine/models/canon.py` (world-domain,
   `LocationTypeCatalog` family):
   - `id TEXT PRIMARY KEY` (uuid default, existing `_uuid` factory).
   - `world_id TEXT FK world.id NOT NULL`.
   - `name TEXT NOT NULL` — display name, e.g. `"Grimoire"`.
   - `slug TEXT NOT NULL` — validated identifier stem, e.g. `"grimoire"` (validation
     itself lives in the writer, BRIEF-0044-c; here it is a plain column).
   - `physical_table TEXT NOT NULL` — e.g. `"ext_grimoire"`, with
     `CHECK (physical_table GLOB 'ext_*')` (Dname1 belt-and-suspenders; the full
     identifier validation is the writer's job).
   - `status TEXT NOT NULL DEFAULT 'active'` with
     `CHECK (status IN ('active','retired','quarantined'))` — Ddrop1 soft-retire;
     `'quarantined'` is reserved for BRIEF-0044-e (present in the CHECK now so that
     brief needs no ALTER).
   - **Dgov1 reserved governance columns (unpopulated at socle, reader is 0047/F1'):**
     - `write_authorities JSON NOT NULL DEFAULT '[]'` — reserved: which authorities
       may write ROWS of this type.
     - `ai_proposable BOOLEAN NOT NULL DEFAULT 0` — reserved: the `mutable_by_ai`
       trait wires this in 0045.
   - `created_by TEXT`, `created_at TIMESTAMP`.
   - `__table_args__`: `Index("idx_entity_type_world", "world_id")`, plus
     `UNIQUE (world_id, slug COLLATE NOCASE)` and `UNIQUE (physical_table)`.

2. **Table `entity_type_history`** in `canon.py` (append-only, `Ledger` family — no
   `change_history` column):
   - `id TEXT PRIMARY KEY` (uuid).
   - `world_id TEXT FK world.id NOT NULL`.
   - `entity_type_id TEXT FK entity_type.id NOT NULL`.
   - `event TEXT NOT NULL` with
     `CHECK (event IN ('type_created','trait_added','type_retired','type_quarantined','type_restored'))`
     — only `'type_created'` is produced at the socle; the rest are reserved (in the
     CHECK now so 0045/0044-e need no ALTER).
   - `definition_snapshot JSON NOT NULL` — full definition at the instant of the event.
   - `physical_table TEXT NOT NULL`.
   - `ddl_text TEXT` — the exact DDL emitted for this event (auditable, replayable).
   - `changed_by TEXT`, `created_at TIMESTAMP`.
   - `__table_args__`: `Index("idx_entity_type_history_type", "entity_type_id")`.

3. **Export** both classes from `src/world_engine/models/__init__.py` (canon block),
   preserving alphabetical order and the existing re-export surface.

4. **Migration `scripts/migrate_vX_YY_entity_type.py`** (guarded, idempotent, two
   independent guards; `migrate_v1_84` structure). Create both tables + their indexes
   if absent. NO seeding — no runtime types exist yet. Bump the version constant/row/
   doc per BRIEF-0044-a's rule (Claude Code assigns the number).

## Scope OUT

- The governed runtime-DDL writer and any `CREATE TABLE ext_*` emission
  (BRIEF-0044-c). This brief ships tables with NO writer; the write site + the
  `[CANON_TABLES]`/`[ALLOWED_SITES]` policy edits land in BRIEF-0044-c (same ticket).
  Do not add `entity_type`/`entity_type_history` to `canon_write_policy.txt` here.
- Slug/identifier validation logic, the `ext_` prefix constant, the closed column-type
  enum — all BRIEF-0044-c.
- POPULATING `write_authorities` / `ai_proposable` — reserved, stay at their defaults.
  Do not wire any reader (that is 0047).
- Reconciliation (BRIEF-0044-d), quarantine status transitions (BRIEF-0044-e beyond
  reserving the enum values here).
- Traits / `entity_trait` (TICKET-0045), UI (0046), AI dispatch (0047).

## Invariants to defend

- **History is sacred, now at the schema grain.** `entity_type_history` is
  append-only by construction (no update path, no `change_history` column). State the
  extension explicitly in the ARCHITECTURE_DECISIONS entry.
- **Named exception to "no structure without a reader" (Dgov1).** The two governance
  columns ship with no reader until 0047. This is a deliberate, ticket-spanning
  exception (unlike `location_type_catalog`'s same-ticket reader) taken to avoid an
  ALTER on the chantier's central table every subsequent ticket. Record it as a named
  exception in ARCHITECTURE_DECISIONS; do not "helpfully" add a reader.
- Schema fidelity: the model DDL and the schema doc must match (existing CLAUDE.md
  rule).

## Done means

- [ ] `entity_type` exists with all columns, the three CHECK constraints
      (`physical_table GLOB 'ext_*'`, `status IN (...)`, and the singleton-free
      uniqueness constraints), and both UNIQUE constraints.
- [ ] `entity_type_history` exists with the `event` CHECK covering all five reserved
      values and no `change_history` column.
- [ ] Both classes importable via `from world_engine.models import EntityType, EntityTypeHistory`.
- [ ] `python scripts/migrate_vX_YY_entity_type.py` creates both tables + indexes;
      re-running is a clean no-op.
- [ ] `python scripts/init_db.py` on a virgin DB creates both tables (they are model-
      declared, so `create_all` covers them).
- [ ] Existing verify suite stays green (no writer yet -> `single_canon_write.py`
      unaffected).
- [ ] `/review-step` then `/close-step` run.

**Deployment sequence (danger_class: migration):**
backup -> `python scripts/migrate_vX_YY_entity_type.py` -> verify.

## Docs to update

- Schema changelog (`vX.YY`): `entity_type` (with the Dgov1 reserved columns called
  out as reserved) + `entity_type_history` (A1 append-only DDL log), the closed
  `event`/`status` vocabularies.
- `ARCHITECTURE_DECISIONS.md`: section "ENTITY-TYPE CONSTRUCTOR — socle registry +
  schema-birth history (A1, Dgov1)"; document the append-only-at-schema-grain
  extension and the named Dgov1 reader-deferral exception.
- `CLAUDE.md`: schema-fidelity note for the two new tables; the "history sacred"
  invariant line extended to `entity_type_history`.
