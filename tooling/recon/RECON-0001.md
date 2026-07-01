# RECON-0001 — bootstrap anchors for Phase 1

Report-only. For each item give the exact `path:line` in the LIVING code, or
state "does not exist". Do not act on anything.

## 1. WORLD DELETE CASCADE
Real table names for: world, and every table with a FK/reference to a world
(npc, region, session, others). For each: table + the column referencing the
world id. Defines the delete cascade and the no-orphans check.

## 2. CANON-WRITE PATHS
- Exact location of `_apply_mutation` (path:line).
- Enumerate EVERY current DB-write site (add/delete/merge/commit or SQLModel
  equivalent) OUTSIDE `_apply_mutation`, each as path:line. This calibrates the
  single_canon_write invariant check so it does not flag legitimate exceptions.

## 3. DB-TOUCH / MIGRATION SIGNATURE
- How does a schema change / migration manifest here? (migrations dir?
  metadata.create_all? manual DDL?) path:line.
- What code paths open the DB for writing at runtime? Defines the
  pre-db-backup hook predicate — what counts as a db_write.

## 4. DELETE ENTRY POINT
Does any world-deletion function/route/command already exist? path:line, or
"does not exist" (the delete brief will create it).

## 5. BACKUP SIGNATURE
`backup.py`: how invoked (module? script? args?), where it writes. Confirm
rotation-keep-2 and the `~/.world_engine/backups/` target.

## 6. STRUCTURAL INVARIANT SITES (for reusable checks)
- Query-level secret exclusion enforced where? (path:line)
- B1 per-NPC uniqueness enforced where? (path:line)

## 7. CANON-WRITE SURFACE
Confirm `src/world_engine/cockpit/` is the SOLE surface that writes world state
(entry point `world_engine.cockpit.app:app` is already known).
