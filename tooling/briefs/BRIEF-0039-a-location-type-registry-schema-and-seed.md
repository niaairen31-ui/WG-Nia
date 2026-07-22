# BRIEF - Step "location_type classified registry (schema + writer + migration/seed)"

## Context
The location type picker is a free-text datalist backed by a frontend constant
(`LOCATION_TYPE_ORDER`, index.html:3131) with no persistence and no notion of
interior vs exterior. TICKET-0039 needs a STRUCTURAL interior/exterior signal per
type so doors can be classified (D1) and street access checked (E1). This step
introduces the classified registry and seeds it; nothing consumes the
classification yet (readers land in c/d/e). `location_type` on `location` stays a
plain string FK-in-spirit to this registry (enforced by the check in BRIEF-0039-e,
not by a DB FK - free-text history predates the registry).

## Scope IN
1. NEW TABLE `location_type_catalog` in `src/world_engine/models/canon.py`, placed
   directly AFTER the `Location` model. Columns:
   - `id: str` primary key, `default_factory=_uuid`
   - `world_id: str = Field(foreign_key="world.id", nullable=False)`
   - `name: str` (the type string, e.g. "building")
   - `classification: Optional[str] = None`  (values: "interior" | "exterior" |
     NULL = not yet classified)
   - `created_at: datetime = _created_ts()`
   - `__table_args__`: a UNIQUE index
     `Index("idx_location_type_catalog_name", "world_id", text("name COLLATE NOCASE"), unique=True)`
     (case-insensitive per-world uniqueness; mirror LocationSubculture's
     COLLATE NOCASE unique index, canon.py:247-251).
2. VERBATIM docstring above the model (copy exactly):
   ```
   # -----------------------------------------------------------------------------
   # location_type_catalog  (classified type registry, schema vX.YY, TICKET-0039,
   # BRIEF-0039-a)
   #
   # One row per location_type string, per world. classification is the ONLY
   # interior/exterior signal in the engine (A1/B1): doors derive their kind from
   # the two endpoints' classification (D1), and street-access (E1) reads it.
   # NULL classification = not yet decided; a NULL-classified type is inert for
   # door derivation and E1 until the creator classifies it (BRIEF-0039-b prompts
   # on next use). This is a per-row upsert catalog, NOT a full-replace config
   # table: types are added one at a time from the picker. exterior-public ==
   # exterior for v1; the public/private split on exterior is a named deferral.
   # -----------------------------------------------------------------------------
   ```
3. NEW WRITER `upsert_location_type` in `src/world_engine/writes/config.py`
   (same module as write_location_doors / write_location_subculture). Signature:
   `upsert_location_type(db, *, world_id: str, name: str, classification: Optional[str], changed_by: str) -> LocationTypeCatalog`.
   Behavior:
   - `name` stripped; reject empty with ValueError.
   - `classification` must be one of {"interior", "exterior", None}; reject any
     other value with ValueError (defense in depth for the closed vocab).
   - Case-insensitive lookup by (world_id, name). If a row exists: update its
     classification ONLY when the incoming classification is non-NULL (never
     overwrite a decided classification with NULL). If none exists: insert.
   - Caller adds/commits (follow write_location_subculture's "caller commits"
     contract).
   This is an upsert-one, NOT full-replace: do NOT `DELETE FROM location_type_catalog`.
4. MIGRATION `scripts/migrate_vX_YY_location_type_catalog.py` on the
   migrate_v1_71_visit.py idiom (additive, idempotent, prints its actions):
   - Create `location_type_catalog` + its unique index if absent.
   - SEED, idempotently (INSERT only where (world_id, name) absent), for EACH world:
     a. The known defaults, with classification:
        - exterior: `city`, `district`, `natural`
        - interior: `building`, `room`, `underground`
        - NULL: `other`
     b. Every DISTINCT non-null `location.location_type` currently present for
        that world that is not already covered by (a): insert with
        classification = NULL.
   - Idempotent: safe to re-run; existing rows are left untouched (never
     downgrade a decided classification to NULL).

## Scope OUT
- NO reader of `classification` in this brief - door derivation (D1), materialization
  (c), hooks (d), checks and E1 note (e) all come later. Ship the table + writer +
  seed ONLY.
- NO frontend change (picker wiring is BRIEF-0039-b).
- NO FK from `location.location_type` to this table. The string column stays as-is;
  the catalog is enforced by the verify check in BRIEF-0039-e, not by a DB FK.
- NO full-replace writer. Do not model this on write_world_laws' DELETE-then-insert.
- NO public/private exterior subdivision - deferred (named in ticket + BRIEF-0039-e).
- Do NOT touch `location_type` values already stored on locations (no reclassifying,
  no renaming). Seed reflects them; it never edits them.

## Invariants to defend
- CLAUDE.md "no structure without a reader": this brief ADDS a table with no reader.
  This is a deliberate, ticket-scoped exception - the reader lands in the SAME
  ticket (BRIEF-0039-c/d/e). State this in the migration docstring so it is not
  mistaken for orphan structure.
- "single canon-write authority": `upsert_location_type` is a new writer in the
  writes/ family (creator direct authority, curated config). It must NOT be reachable
  from `_apply_mutation`. Keep it in writes/config.py alongside the other curated
  writers; single_canon_write.py must stay green.
- "history is sacred": curated config family (npc_price / location_subculture
  precedent) carries NO change_history. Match that - no change_history on the catalog.
- Module budget (R5): writes/config.py is currently 328 lines. Adding
  upsert_location_type (~25 lines) is safe; if it would cross 1000, REPORT before
  extracting.

## RECON needed at exec time (verify before writing)
- Confirm `_uuid`, `_created_ts`, `text`, `Index` are already imported in canon.py
  (LocationSubculture uses all four - canon.py:243-256).
- Confirm the exact seed target: run `SELECT DISTINCT location_type FROM location
  WHERE location_type IS NOT NULL` against the live DB before finalizing the seed,
  and print the discovered set from the migration so the creator sees what got
  classified NULL. Do NOT hardcode a list beyond the 7 defaults.
- Confirm `writes/config.py`'s "caller commits" contract wording on an existing
  writer (write_location_subculture, config.py:82) and match it verbatim in the
  new writer's docstring.

## Done means
- [ ] `python scripts/migrate_vX_YY_location_type_catalog.py` prints table creation
      (or "already present"), prints the DISTINCT types it seeded, and is safe to
      run twice (second run reports no-ops).
- [ ] `location_type_catalog` exists with the unique (world_id, name COLLATE NOCASE)
      index; rows for the 7 defaults exist with the classifications above; `other`
      is NULL.
- [ ] A python one-liner calling `upsert_location_type(..., name="tavern",
      classification="interior")` inserts a row; calling it again with
      classification=None leaves "interior" intact; calling with
      classification="sideways" raises ValueError.
- [ ] `/review-step` clean; single_canon_write.py green.

## Docs to update
- Schema changelog: add the `location_type_catalog` entry with the next version
  number after v1.81 (exec assigns; do a version-number reconciliation ONLY here).
- ARCHITECTURE_DECISIONS.md: append the G decision (classified extensible registry,
  interior/exterior, NULL = lazy classification, upsert-one not full-replace) and
  the exterior-public==exterior v1 simplification with its deferral trigger.
- CLAUDE.md: add `location_type_catalog` to the schema/File-structure pointer if
  that section enumerates tables (pointer-fresh rule).
