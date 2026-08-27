# BRIEF — Step "entity_trait projection table + migration + seed"

## Context

TICKET-0045 (trait registry). Socle 0044 landed at schema v1.87: `entity_type`
+ `entity_type_history` exist (models/canon.py:882, :925), but `entity_trait`
does NOT exist anywhere — RECON confirmed no table, no model, no code. Decision
A1: the trait DEFINITION lives in code (traits.py, BRIEF-0045-b); this table is
a MATERIALIZED PROJECTION only — which entity_type has checked which trait.
This brief ships the projection table, its migration (schema v1.88), and the
seed of the five canonical trait keys as the closed vocabulary the projection
may reference. No reader logic, no registry module, no check here.

## Scope IN

1. **models/canon.py — new `EntityTrait` model.** Add after `EntityTypeHistory`
   (currently ends models/canon.py:955). It is a projection join row, NOT an
   entity-extension row and NOT a definition. Exact shape:

   ```python
   class EntityTrait(SQLModel, table=True):
       __tablename__ = "entity_trait"
       __table_args__ = (
           Index("idx_entity_trait_type", "entity_type_id"),
           Index(
               "idx_entity_trait_unique", "entity_type_id", "trait_key",
               unique=True,
           ),
       )

       id: str = Field(default_factory=_uuid, primary_key=True)
       entity_type_id: str = Field(foreign_key="entity_type.id", nullable=False)
       trait_key: str
       created_by: Optional[str] = None
       created_at: datetime = _created_ts()
   ```

   No `CheckConstraint` enumerating the trait keys in SQL — the closed
   vocabulary is enforced by the projection check (BRIEF-0045-c,
   trait_registry_projection.py), which cross-references traits.py. A SQL
   CHECK would duplicate the vocabulary across code and DDL (S-norme
   violation) and would need an ALTER every time a trait is added via Claude
   Code. `trait_key` is a plain TEXT column; its legality is a code-plane
   property, verified structurally, never a DDL enum.

2. **models `__init__.py` export.** Add `EntityTrait` to the models package
   `__all__` / re-export list so `models.EntityTrait` resolves (same access
   pattern the migration uses for `models.EntityType`).

3. **scripts/migrate_v1_88_entity_trait.py — migration.** Copy the exact
   idempotent idiom of scripts/migrate_v1_87_entity_type.py verbatim
   (`_ensure_table`, `_index_names`, `_ensure_indexes`, two independent guards
   per table — table existence + index existence, so a partially applied prior
   run completes only the missing part on re-run). Single table this time
   (`models.EntityTrait`). Docstring header states: schema v1.88, TICKET-0045,
   BRIEF-0045-a, projection table for the trait registry; ships table +
   indexes only, seeding is a separate step (Scope IN item 4). Runnable as
   `python scripts/migrate_v1_88_entity_trait.py`.

4. **scripts/seed_trait_keys.py — seed the projection's reference vocabulary.**
   This does NOT seed projection rows (no entity_type has checked a trait yet
   — that is the UI's job, TICKET-0046). It seeds nothing INTO entity_trait.
   Instead it is a verification-and-report script that: connects, confirms the
   `entity_trait` table exists and is empty, and prints the five canonical
   trait keys that traits.py (BRIEF-0045-b) will declare, so the live operator
   can eyeball that the migration landed before traits.py is wired. Exact keys
   to print, in this order: `describable`, `spatial`, `knowable`,
   `secretable`, `mutable_by_ai`. If traits.py does not yet exist at run time,
   the script prints the keys from a local literal and notes "traits.py not
   yet present — keys shown from brief literal"; if traits.py DOES exist, it
   imports and prints the keys from it and asserts the two lists match,
   failing loudly on drift. (This makes the seed script the first live
   cross-check between the migration and the registry module.)

## Scope OUT

- **traits.py / the registry module** — BRIEF-0045-b. This brief must not
  create it. (Item 4's conditional import tolerates its absence.)
- **The reader-exists check (C1) and the projection check** — BRIEF-0045-c.
  No verify/checks/ file is authored here.
- **describable as non-checkable socle wiring** — BRIEF-0045-d. This brief
  ships the trait_key column able to hold "describable", but does NOT make
  describable auto-present on every entity_type.
- **Any SQL CheckConstraint enumerating trait keys** — explicitly rejected in
  Scope IN item 1; the vocabulary is a code-plane property.
- **Runtime DDL / ext_<slug> tables** — TICKET-0044, landed. Untouched.
- **Canon-write dispatch, write_authorities/ai_proposable population** —
  TICKET-0047.
- **Derived / value-conditioned traits** (rideable-if-size, portable-if-size)
  — deferral D-derived, logged in ARCHITECTURE_DECISIONS.md, not built.

## Invariants to defend

- **No structure without a reader.** This table's reader is the projection
  check + the constructor UI (0046). The table ships in the SAME ticket as its
  first structural consumer (the projection check, BRIEF-0045-c), so the
  invariant holds across the ticket, not the brief. State this explicitly in
  the migration docstring so the intent is legible, mirroring the socle's
  documented cross-brief exception.
- **History is sacred.** entity_trait is a projection, not history: it CAN be
  updated/deleted (a creator un-checks a trait) — but every such write is an
  entity_type DDL event and belongs in entity_type_history (`trait_added`
  already reserved in the CHECK, models/canon.py:929). This brief does NOT
  write history rows (no writer ships here); it must not add a `change_history`
  column to entity_trait (the history grain is the log table, not this row).
- **Single canon-write authority.** No writer to entity_trait ships in this
  brief. The creator-CRUD write path is TICKET-0046; the seed script writes
  nothing to the table.
- **S-norme (no duplication).** The trait-key vocabulary must have ONE source
  (traits.py, next brief). This brief's seed script carries a literal ONLY as
  a pre-traits.py fallback and asserts equality once traits.py exists — the
  fallback is a bootstrap, not a second source of truth.

## Done means

- [ ] `python scripts/migrate_v1_88_entity_trait.py` on a fresh backup prints
      table created + indexes created; a second run prints "already present"
      for both guards (idempotent).
- [ ] `entity_trait` exists with columns id, entity_type_id, trait_key,
      created_by, created_at; unique index on (entity_type_id, trait_key);
      FK entity_type_id -> entity_type.id.
- [ ] `python -c "from world_engine import models; models.EntityTrait"`
      resolves.
- [ ] `python scripts/seed_trait_keys.py` prints the five keys in order and
      confirms the table exists and is empty.
- [ ] entity_trait has NO change_history column and NO SQL CHECK enumerating
      trait keys.
- [ ] Live deployment sequence executes clean in order: `python scripts/
      backup.py` -> `python scripts/migrate_v1_88_entity_trait.py` ->
      `python scripts/seed_trait_keys.py` -> (verify deferred to -c).
- [ ] /review-step and /close-step run (engine model code touched).

## Docs to update

- **world-engine-schema.md**: new `### entity_trait` section (place adjacent to
  the entity_type family, after entity_type_history at line ~257). DDL block +
  NOTE stating: projection table, schema v1.88, TICKET-0045 BRIEF-0045-a;
  trait_key legality is a code-plane property verified by
  trait_registry_projection.py, NOT a SQL CHECK; reader is the projection check
  + constructor UI (0046). Bump "Current schema version" to v1.88.
- **world-engine-schema-changelog.md**: v1.88 entry.
- This brief does NOT touch ARCHITECTURE_DECISIONS.md or CLAUDE.md (registry
  doctrine is recorded in BRIEF-0045-b/-d).
