---
paths:
  - "scripts/migrate_*.py"
  - "scripts/rollback_quarantine.py"
  - "src/world_engine/schema_*.py"
  - "src/world_engine/writes/schema.py"
  - "src/world_engine/cockpit/app.py"
---

# Schema, migrations and the boot guard

## Invariants

- **INV-60** The app refuses to boot when `schema_meta.static_version` !=
  `EXPECTED_STATIC_SCHEMA_VERSION`, OR when a physical table is neither a
  static model table nor a registered `entity_type.physical_table`
  (`schema_reconcile.unaccounted_tables`, in the same `cockpit/app.py`
  startup hook; `_orphan_ext_*` quarantine tables are pattern-accounted).
  `schema_meta` is migration-only infra, never canon, never written outside
  a migration script. [no check]
- **INV-61** Rollback contract: once a runtime type exists, rolling code back
  past the constructor version requires running
  `scripts/rollback_quarantine.py` first, after a backup. `--restore` is
  potentially lossy, bounded to rows whose `entity` row was deleted during
  the rollback window; every lost row is kept in `_orphan_lost_*` and
  reported, never silently dropped. The contract is SQLite-scoped.
  [no check]
