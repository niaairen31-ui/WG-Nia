# BRIEF — Step "schema reconciliation — every physical table accounted for (C2 plane 2)"

## Context

Plane 2 of the locked C2 design. Once tables can be born at runtime, the guarantee
that keeps the base legible is: every physical table is either a known static table
(plane 1, model/migration-declared) OR a registered runtime table
(`entity_type.physical_table`). Anything else is corruption we must never serve on.
This is inherently a RUNTIME property (it depends on the live DB's actual tables and
the `entity_type` rows), so the accounting runs at boot + as a CLI; a static verify
check guards that the mechanism is present and single-sourced.

## Mini-RECON (Claude Code, pre-implementation — verify live before coding)

Report-only; confirm, then implement.
1. Static-set source: `SQLModel.metadata.tables` enumerates every model-declared
   table (`src/world_engine/db.py` imports models to register them). Derive the
   static set from THIS, never a hardcoded literal list.
2. Physical enumeration: `sqlalchemy.inspect(engine).get_table_names()` (used in
   `scripts/init_db.py`). This is the physical truth.
3. Boot-guard site: the startup hook from BRIEF-0044-a in `cockpit/app.py`. This step
   EXTENDS it (version guard, then reconciliation), fail-closed on both.
4. The `EXT_PREFIX` constant lives in `writes/schema.py` (BRIEF-0044-c). Import it;
   do NOT redefine `"ext_"` (S-norme single-source; `runtime_ddl_guard.py` and this
   check both forbid a second copy).
5. Static-check harness + registration: `tooling/verify/run.py` (arrow-linked checks),
   `single_canon_write.py` as the static-AST precedent (this check's WIRING part is
   static; the ACCOUNTING part is runtime — keep them separate).

## Scope IN

1. **New module `src/world_engine/schema_reconcile.py`** (runtime accounting):
   - `static_table_names() -> set[str]` — from `SQLModel.metadata.tables.keys()`.
   - `registered_runtime_tables(session) -> set[str]` —
     `SELECT physical_table FROM entity_type` for ALL statuses (an `active`,
     `retired`, or `quarantined` type's table still physically exists).
   - `unaccounted_tables(engine, session) -> list[str]` — the accounted set is
     `static ∪ registered_runtime ∪ {t for t in physical if t startswith '_orphan_' + EXT_PREFIX}`
     (quarantined tables from BRIEF-0044-e are `_orphan_ext_*`, pattern-accounted).
     Returns sorted physical tables not in the accounted set. Any `ext_*` table absent
     from `entity_type` is therefore unaccounted (the dangerous case: a runtime table
     with no registry row).
   - `main()` CLI — connect via the app engine, open a session, print each unaccounted
     table, `sys.exit(1)` if any, `sys.exit(0)` if clean. Runnable as
     `python -m world_engine.schema_reconcile` (or a thin `scripts/` wrapper — match
     the repo's script idiom).

2. **Boot wiring** — extend the BRIEF-0044-a startup guard: after the version check
   passes, call `unaccounted_tables(...)`; if non-empty, refuse to start (raise) with:
   `"unaccounted physical tables (not static, not in entity_type): {tables} — a runtime table with no registry row indicates corruption or a failed constructor write; refuse to serve."`

3. **New verify check `tooling/verify/checks/schema_reconciliation.py`** (static, AST,
   fail-closed) — guards the MECHANISM, not the live DB:
   - FAIL if `schema_reconcile.py` is missing or does not define the three functions;
   - FAIL if `static_table_names` does not reference `SQLModel.metadata` (i.e. a
     hardcoded literal set was used instead);
   - FAIL if the `"ext_"` literal appears in `schema_reconcile.py` (it must import
     `EXT_PREFIX` from `writes/schema.py` — single source);
   - FAIL if the boot module (`cockpit/app.py`) does not import `schema_reconcile`;
   - zero parsed assertions -> FAIL (vacuous-proof). Register in `run.py`.

## Scope OUT

- Quarantine creation / the `_orphan_ext_*` tables themselves (BRIEF-0044-e). This
  step only ACCOUNTS for that prefix; it does not create it.
- The `schema_meta` version guard (BRIEF-0044-a) — reuse it, do not reimplement it.
- FIXING any unaccounted table found: report only (CLI exits non-zero, boot refuses).
  No auto-drop, no auto-register.
- The F1' runtime row-write authority check (0047). Reconciliation is about which
  TABLES exist, not who may write their ROWS.
- Per-world scoping of the accounting: physical tables are global; `entity_type` is
  per-world but every runtime table is registered exactly once, so the union is
  world-agnostic at the table level. Do not add world filtering.

## Invariants to defend

- **Fail-closed**, at both boot and CLI. An empty checks parse in the verify check is
  a failure, never a green.
- **Single-source `EXT_PREFIX`** — shared with `writes/schema.py`; no second literal.
- Boot cost: full-table reconciliation on every startup is a cheap `get_table_names()`
  + one `SELECT`; acceptable. (Drafting decision — see delivery note.)

## Done means

- [ ] `python -m world_engine.schema_reconcile` on a clean DB exits 0 and reports
      nothing unaccounted.
- [ ] Hand-create a stray `ext_zzz` table (no `entity_type` row): the CLI exits 1
      naming `ext_zzz`, AND the app refuses to boot with the reconciliation message;
      dropping `ext_zzz` -> CLI exits 0, app boots.
- [ ] A `_orphan_ext_zzz` table is treated as accounted (does not trip the CLI).
- [ ] `schema_reconciliation.py` verify check green; removing a reconcile function, or
      hardcoding the static set, turns it red.
- [ ] `/review-step` then `/close-step` run.

**Deployment sequence:** commit -> implement -> `/review-step` ->
`python -m world_engine.schema_reconcile` on the live DB -> `/verify`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: "SCHEMA VERSION — two-plane governance (C2), plane 2:
  physical-table reconciliation (boot + CLI)"; explain why accounting is runtime, not
  static, and how `_orphan_ext_*` is pattern-accounted.
- `CLAUDE.md`: invariant "the app refuses to boot when a physical table is neither
  static nor registered in `entity_type`"; File-structure pointer for
  `schema_reconcile.py`; new verify check listed.
