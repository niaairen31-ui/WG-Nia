---
id: TICKET-0044-socle-entity-type
title: Socle entity_type — governed runtime DDL foundation
type: feature
status: exec
created: 2026-07-23
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration, destructive_data]
blast_radius: large
brief_ids: [BRIEF-0044-a, BRIEF-0044-b, BRIEF-0044-f, BRIEF-0044-c, BRIEF-0044-d, BRIEF-0044-e]
schema_version_touched: vX.YY-vX.YY  # Claude Code assigns; current head v1.85
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Verkhaal ajoute un constructeur de types d'entites. Ce ticket pose le socle
uniquement : tables `entity_type` et `entity_trait` [voir note P1 ci-dessous],
plus le chemin d'ecriture DDL runtime et ses garanties. Aucune UI, aucun trait
defini, aucune integration IA.

Decisions verrouillees en amont : D2 (materialisation a chaud — le constructeur
cree les tables SQL au runtime, pas via migration Claude Code), E2 (palette de
traits, pas de primitives nues), F1' (fermeture canon-write deplacee du scan AST
statique vers un check runtime fail-closed adosse a une table gouvernee).

Le probleme dur : D2 introduit une troisieme autorite d'ecriture qui modifie la
structure et non le contenu. Trois consequences a trancher :
1. `change_history` snapshot le contenu, pas le schema.
2. un rollback de code trouve des tables qu'il ne connait pas.
3. la version de schema cesse de decrire la base reelle si des tables naissent
   hors migration.

## Clarifications resolved (intake)

**Note P1 — `entity_trait` is NOT in this ticket.** The socle ships the two
registry/history tables `entity_type` + `entity_type_history`, plus the governed
runtime-DDL write path. Trait definitions (`entity_trait` and the five trait
readers) are TICKET-0045 (scope OUT here). The request line naming `entity_trait`
is superseded by this clarification.

**Version delta.** Live `main` head is v1.85 (`world-engine-schema.md:3`), not
v1.81. All version references below use `vX.YY` placeholders; Claude Code owns the
actual numbers and CHANGELOG entries.

**Decision codes locked pre-brief (2026-07-23):**
- **A1** — schema-birth history: dedicated append-only `entity_type_history`
  table (DDL event log carrying `ddl_text` + `definition_snapshot`). Source for
  B1 quarantine and C2 reconciliation.
- **B1** — rollback: quarantine-by-construction. Manifest = `entity_type`; a
  script rebuilds each runtime table WITHOUT its FK to `entity` (SQLite has no
  drop-single-FK), preserving data under `_orphan_ext_*`; roll-forward restore is
  potentially lossy, bounded to rows whose `entity` was deleted during the
  window, and that loss is LOGGED, never silent.
- **C2 (two-plane)** — versioning: a stored `schema_meta` (static-plane version +
  fail-closed boot guard) is kept SEPARATE from the per-world runtime-type
  manifest (`entity_type`). The two planes answer different questions; the
  constructor is structurally forbidden any write path to `schema_meta`.
  Reconciliation ("every physical table in static-set OR entity_type registry")
  is the shared plane-2 reader.
- **Dcol1** — closed, code-owned column-type enum; no free SQL type string ever
  reaches DDL (forced by E2).
- **Dname1** — mandatory `ext_` prefix + identifier validation + collision check;
  the prefix is the structural discriminant for C2 reconciliation and B1.
- **Ddrop1** — CREATE only; destructive `DROP`/`ALTER` forbidden by construction.
  Retire = status flag on `entity_type` (soft-retire), never a `DROP`. Additive
  `ADD COLUMN` is reserved-but-unused at the socle (0045 needs it for add-trait).
- **Dgov1** — reserve the governance columns on `entity_type` NOW, unpopulated
  (reader is 0047/F1'). A named cross-ticket exception to "no structure without a
  reader", accepted to avoid migrating the chantier's central table every
  subsequent ticket.

**Socle scope boundary on the "third authority".** At the socle the constructor
writes STRUCTURE (`CREATE TABLE ext_*`) plus rows into two static
config/history tables (`entity_type`, `entity_type_history`). It performs NO row
write into any `ext_*` table (entities of a runtime type are authored later:
0046 creator CRUD, 0047 AI dispatch). Therefore the F1' runtime write-authority
check for DYNAMIC-table ROW writes is genuinely 0047's concern; the socle does
not yet challenge the canon-write row closure. This boundary is load-bearing and
is asserted in each brief's Scope OUT.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Code-side static schema version constant equals the `world-engine-schema.md`
      `Current schema version:` line  -> verify/checks/schema_version_agreement.py
- [ ] `writes/schema.py` runtime-DDL writer is CREATE-only (no `DROP`/`ALTER`
      token), emits column types only from the closed enum (no free type-string
      interpolation), single-sources the `ext_` prefix, and contains no row write
      to a dynamic table  -> verify/checks/runtime_ddl_guard.py
- [ ] Schema-reconciliation mechanism is present and wired: `schema_reconcile.py`
      defines the accounting functions, derives the static set from
      `SQLModel.metadata` (not a hardcoded literal), single-sources the `ext_`
      prefix, and is imported by the boot guard  -> verify/checks/schema_reconciliation.py
- [ ] Canon-write policy stays closed: `entity_type` + `entity_type_history`
      added to `[CANON_TABLES]`, their only write site is the governed writer
      in `[ALLOWED_SITES]`  -> verify/checks/single_canon_write.py
- [ ] No regression on structure gates  -> verify/checks/function_length.py
- [ ] No regression on structure gates  -> verify/checks/module_budget.py
- [ ] No regression on structure gates  -> verify/checks/import_cycle.py
- [ ] No regression on structure gates  -> verify/checks/undefined_names.py
- [ ] No regression on structure gates  -> verify/checks/no_print_in_src.py

### Live  ->  human gate (Nia)
- [ ] Boot guard: with `schema_meta.static_version` != code constant (or the row
      absent), the app refuses to start with a clear "run migrations" message; on
      match, it starts normally.
- [ ] `create_entity_type(...)` for a throwaway type creates `ext_<slug>`, the
      `entity_type` row, and the `entity_type_history` `type_created` row ATOMICALLY
      — a forced failure mid-operation leaves none of the three.
- [ ] `ext_<slug>` carries `id TEXT PRIMARY KEY REFERENCES entity(id)` and only
      columns drawn from the closed enum.
- [ ] A hand-created stray `ext_zzz` table (no registry row): reconcile CLI exits
      non-zero naming it, and boot refuses; dropping it -> CLI exits 0, boot starts.
- [ ] `scripts/test_rollback_quarantine.py` passes: quarantine produces
      `_orphan_ext_<slug>` without the entity FK, data preserved, original gone,
      history logged; reconciliation stays green; restore re-attaches, and a row
      whose `entity` was deleted during the window is parked in `_orphan_lost_*`
      and reported, never silently dropped.
- [ ] `/review-step` + `/close-step` run for every brief that touches engine code;
      `/verify` green at ticket close.
