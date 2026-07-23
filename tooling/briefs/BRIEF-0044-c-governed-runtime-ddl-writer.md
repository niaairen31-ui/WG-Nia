# BRIEF — Step "governed runtime-DDL writer (Dcol1, Dname1, Ddrop1, A1 atomicity)"

## Context

The core of the socle: the single governed path that materializes a runtime type.
It composes a constrained `CREATE TABLE ext_*` from a closed column-type enum
(Dcol1), a validated identifier with a mandatory `ext_` prefix (Dname1), CREATE-only
with destructive DDL forbidden by construction (Ddrop1), and it writes the
`entity_type` row + the `entity_type_history` `type_created` row in the SAME
transaction as the DDL (A1 atomicity). This is the third structural-write authority
(D2) — but at the socle it writes STRUCTURE plus two static config/history tables,
and performs NO row write into any `ext_*` table (that is 0046/0047).

## Mini-RECON (Claude Code, pre-implementation — verify live before coding)

Report-only; confirm, then implement.
1. Governed-writer chokepoint idiom: `src/world_engine/writes/config.py:1-33`
   (curated-config full-replace family). The new module joins the `writes/` package;
   R7 domain-prefixed naming applies.
2. SQLite transactional DDL: confirm on this SQLite build that `CREATE TABLE` inside
   an open transaction commits/rolls back atomically with the row INSERTs (it does;
   verify the session/engine transaction boundary so a mid-operation failure rolls
   back ALL THREE writes). Anchor: `src/world_engine/db.py` engine + session.
2b. FK enforcement: `db.py:44` sets `PRAGMA foreign_keys=ON`. The `ext_*` table's
   `id ... REFERENCES entity(id)` FK is live from birth — relevant to BRIEF-0044-e.
3. Canon-write checker semantics: `tooling/verify/checks/single_canon_write.py:1-13`
   — it matches ROW writes (`.add`/`.delete`, and raw SQL only for
   `INSERT INTO|DELETE FROM|UPDATE`). Confirm `CREATE TABLE` is NOT matched (so the
   DDL execute is invisible to it), and that the two INSERTs into `entity_type` /
   `entity_type_history` are attributable and must be allow-listed.
4. Extension PK shape to reproduce: `id TEXT PRIMARY KEY REFERENCES entity(id)`
   (`canon.py:155/213/763`). Every `ext_*` table gets this exact PK first.

## Scope IN

1. **New module `src/world_engine/writes/schema.py`** (R7 domain-prefixed). Single
   governed entry:
   `create_entity_type(session, *, world_id, name, slug, columns, changed_by) -> str`
   returning the new `entity_type.id`. `columns` is a list of `(col_name, col_type)`
   pairs where `col_type` is a member of the closed enum (item 2). At the socle the
   only caller is the B1 test (BRIEF-0044-e); production callers arrive in 0045/0046.

   The function, in ONE transaction (A1 — see the invariant wording below), in order:
   a. validate `slug` and each `col_name` via the identifier validator (item 3);
   b. derive `physical_table = EXT_PREFIX + slug`;
   c. collision check: `inspect(engine).has_table(physical_table)` is False AND no
      `entity_type` row exists with that `slug` (case-insensitive) or `physical_table`;
      on collision, raise a clear `ValueError` and let the transaction roll back;
   d. build the `CREATE TABLE` text via the constrained generator (item 4);
   e. `execute` the DDL;
   f. INSERT the `entity_type` row (Dgov1 columns left at their defaults);
   g. INSERT the `entity_type_history` row: `event='type_created'`,
      `definition_snapshot={name, slug, physical_table, columns}`,
      `physical_table`, `ddl_text=<the exact CREATE text>`, `changed_by`.

2. **Closed column-type enum (Dcol1)** — a module-level mapping, the ONLY source of
   SQL type fragments. No raw type string ever reaches the DDL. Members and their SQL:
   - `TEXT` -> `"TEXT"`
   - `INTEGER` -> `"INTEGER"`
   - `REAL` -> `"REAL"`
   - `BOOLEAN` -> `"INTEGER"` with `CHECK (<col> IN (0,1))`
   - `JSON` -> `"TEXT"` (SQLite JSON is TEXT; note it)
   - `TIMESTAMP` -> `"TIMESTAMP"`
   - `FK_ENTITY` -> `"TEXT NOT NULL REFERENCES entity(id)"`
   - `FK_ENTITY_NULLABLE` -> `"TEXT REFERENCES entity(id)"`
   A `col_type` outside this set raises before any DDL. The mandatory shared PK
   `id TEXT PRIMARY KEY REFERENCES entity(id)` is emitted FIRST, always, and is not
   part of the caller-supplied `columns`.

3. **Identifier validator (Dname1)** — `_validate_identifier(name) -> None|raise`:
   regex `^[a-z][a-z0-9_]{0,62}$`; reject a closed SQL reserved-word set
   (at minimum: `select insert update delete drop alter table index from where join
   entity` — write the full list verbatim in the module); reject leading/trailing
   underscore. `slug` and every `col_name` pass through it. The `ext_` prefix is a
   single module constant `EXT_PREFIX = "ext_"` — the ONLY definition of the literal
   (BRIEF-0044-d's reconciliation imports THIS constant; no second copy anywhere).

4. **Constrained `CREATE TABLE` generator** — builds the DDL string ONLY from
   validated identifiers and enum fragments; no f-string ever interpolates a
   caller-supplied value except through the validated path. It emits the PK line,
   then one line per `(col_name, enum_fragment)`. It has NO branch that can emit
   `DROP` or `ALTER`. The module exposes no drop/alter/rename function at all
   (Ddrop1). Additive `ADD COLUMN` is NOT implemented here — reserved for 0045.

5. **A1 atomicity invariant (embed this wording verbatim in the module docstring):**
   `"(CREATE TABLE ext_*) + (INSERT entity_type) + (INSERT entity_type_history 'type_created') are one transaction: all three commit together or none do. A runtime type never exists physically without its registry row and its birth record, and vice versa."`

6. **Canon-write policy edits** (`tooling/verify/canon_write_policy.txt`):
   - add `entity_type` and `entity_type_history` to `[CANON_TABLES]`;
   - add to `[ALLOWED_SITES]`:
     `src/world_engine/writes/schema.py::create_entity_type   entity_type entity_type_history`
   with a comment noting this is the governed structural-write authority (D2), a new
   sanctioned site, and that its `CREATE TABLE ext_*` DDL is not a row write (so it is
   invisible to the row-write attribution) — not a broadening of row-write authority.

7. **New verify check `tooling/verify/checks/runtime_ddl_guard.py`** (static, AST,
   fail-closed) over `writes/schema.py`:
   - FAIL if any `DROP` or `ALTER` token appears in the module;
   - FAIL if any SQL type string is interpolated outside the closed enum mapping
     (assert the enum is the only place SQL type fragments are literalized);
   - FAIL if the `ext_` literal appears anywhere other than the single `EXT_PREFIX`
     constant (single-source / S-norme);
   - FAIL if a row write (`.add`/`.execute` with INSERT/UPDATE/DELETE) targets a
     dynamic table name (the socle writes rows only to the two static tables);
   - zero parsed assertions -> FAIL (vacuous-proof). Register in `run.py`.

## Scope OUT

- Any ROW write into an `ext_*` table (0046 creator CRUD, 0047 AI dispatch). The
  socle constructor writes structure + the two static tables ONLY. Do not add an
  insert-entity-of-runtime-type path.
- The F1' RUNTIME write-authority check for dynamic-table row writes — that guards
  0047's row writes and is out of scope. `runtime_ddl_guard.py` here is a STATIC
  guard on the DDL writer, not the F1' runtime check.
- Columns-from-traits (0045): `columns` is supplied by the caller; who computes it
  from traits is 0045. Do not read `entity_trait` (it does not exist yet).
- `ADD COLUMN` / add-trait (0045). Retiring/quarantine (0044-e). UI (0046).
- Populating Dgov1 columns.

## Invariants to defend

- **"Two sanctioned canon-write paths."** This step adds a THIRD write authority. It
  is CREATOR-authority structural, invoked only by explicit creator action (never by
  an AI proposal), and is allow-listed. Amend the CLAUDE.md invariant to name the
  structural-write authority (D2) explicitly, stating it never writes canon ROWS in
  response to an AI proposal (that clause is unchanged and still holds). Flag this
  amendment at delivery.
- **A1 atomicity** (item 5) — the load-bearing invariant of this step.
- **Commit before touching any canon-writing path** (hard) — commit before creating
  `writes/schema.py` and editing the policy file.
- Module budget / function length (R1, R5): keep `create_entity_type` under the
  80-line ceiling; extract the generator/validator as separate functions.

## Done means

- [ ] `writes/schema.py` exists; `create_entity_type` imported and callable.
- [ ] Calling it for a throwaway type creates `ext_<slug>` with `id TEXT PRIMARY KEY
      REFERENCES entity(id)` + the enum-typed columns, the `entity_type` row, and the
      `entity_type_history` `type_created` row (with non-empty `ddl_text`).
- [ ] Forcing a failure between the DDL and the second INSERT leaves NONE of the three
      (atomicity) — demonstrated in a throwaway REPL/script during the live gate.
- [ ] A `col_type` outside the enum, a bad `slug`, or a collision each raises before
      any partial write.
- [ ] `canon_write_policy.txt` lists both tables + the one new site;
      `single_canon_write.py` stays green.
- [ ] `runtime_ddl_guard.py` green; adding a `DROP` line or a duplicate `"ext_"`
      literal turns it red.
- [ ] `/review-step` then `/close-step` run.

**Deployment sequence:** commit -> implement -> `/review-step` -> verify. No migration
(no static table added); if Claude Code deems the policy/writer a schema-doc touch,
log it as an applicatif addendum, no version bump.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: "ENTITY-TYPE CONSTRUCTOR — governed runtime-DDL writer
  (Dcol1/Dname1/Ddrop1, A1 atomicity)"; state the socle boundary (structure + two
  static tables, no dynamic row write) and that F1' runtime row-authority is 0047.
- `CLAUDE.md`: the canon-write invariant amended to name the D2 structural-write
  authority; File-structure pointer for `writes/schema.py`; new verify check listed.
- `canon_write_policy.txt`: as in Scope IN item 6 (this file IS part of the doc).
- Schema changelog: applicatif addendum (no version bump) recording the runtime-DDL
  write path and its guarantees.
