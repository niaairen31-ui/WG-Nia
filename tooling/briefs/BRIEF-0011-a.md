# BRIEF-0011-a — Prompt version plumbing: `prompt_version` table, head migration, single accessor, single write shape, versioned edit API

Ticket: TICKET-0011. RECON: RECON-0011 (all `file:line` anchors below are
confirmed against main, 2026-07-04). Locked decisions: **A2** (head pointer,
text in version rows), **B1** (version = system_prompt + user_template only;
B2 deferred), **C1** (fail-closed placeholder validation), **D1** (restore =
new version), **F1** (drop head text columns), **G1** (single read accessor),
**S2** (seed writes v1 on virgin heads only, never text afterwards), **H1**
(normalize the 6 `.format()` sites to `.replace()`).

Cockpit UI (edit form, history list, restore button) is **BRIEF-0011-b** —
not this brief. This brief ends at a working, verified API + bit-identical
runtime.

Schema version: Claude Code owns numbering — `vX.YY` placeholders below.

---

## Context

`prompt_template` (models.py:780-804) carries text directly; 15 loader
functions and ~25 attribute-access sites consume it (RECON-0011 §2). No
history exists (`version` column is decorative — nothing increments it).
This brief moves text into an append-only `prompt_version` table, makes the
head a pure identity/wiring row, and threads every read through one
accessor. Runtime prompts must be **byte-identical** before and after this
brief — the first behavioral change happens only when the creator saves an
edit through the new API.

## Scope IN

### 1. Schema — `prompt_version` (vX.YY)

```sql
CREATE TABLE prompt_version (
  id                  TEXT PRIMARY KEY,
  prompt_template_id  TEXT NOT NULL REFERENCES prompt_template(id),
  version_number      INTEGER NOT NULL,
  system_prompt       TEXT NOT NULL,
  user_template       TEXT NOT NULL,
  note                TEXT,          -- optional creator note; restore autofills
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_prompt_version_head_number
  ON prompt_version(prompt_template_id, version_number);
CREATE INDEX idx_prompt_version_head ON prompt_version(prompt_template_id);
```

No UPDATE, no DELETE, ever — append-only by construction. "Current" =
`MAX(version_number)` per head; **no pointer column anywhere** (D1 + A2).

### 2. Migration script (`scripts/migrate_vX_YY_prompt_version.py`)

Idempotent, in this order:
1. Create `prompt_version` if absent.
2. For every `prompt_template` row that has **zero** version rows: insert
   version 1 copying its current `system_prompt` / `user_template`
   (`note = 'migrated from prompt_template (vX.YY)'`).
3. Drop `system_prompt`, `user_template`, `version` from `prompt_template`
   (F1). SQLite ≥ 3.35 `DROP COLUMN`; fall back to the table-rebuild pattern
   of scripts/migrate_v1_40_drop_character_faction_id.py if needed.
4. Post-check inside the script: every head has ≥ 1 version; abort loudly
   before the drop step if not.

### 3. Models (models.py)

- New `PromptVersion` SQLModel mirroring §1.
- `PromptTemplate` loses `system_prompt`, `user_template`, `version`.
  Head keeps: id, world_id, name, usage, variables, destination, model,
  is_active, notes, updated_at.

### 4. Read accessor (G1) — new module `src/world_engine/prompt_store.py`

```python
def current_prompt(db: Session, template: PromptTemplate) -> PromptVersion
def get_version(db: Session, template_id: str, version_number: int) -> PromptVersion
def list_versions(db: Session, template_id: str) -> list[PromptVersion]  # newest first, no-body use is caller's concern
```

- `current_prompt` = highest `version_number`; **raises** (RuntimeError) on
  a versionless head — that state is structurally impossible post-migration
  (migration post-check + S2 + append-only) and must fail loud, never
  fall back.
- Pure reads only. This module and `writes.py` are the **only** places
  allowed to touch `PromptVersion` (plus models.py and the migration) —
  enforced by verify (§9).
- Deliberately separate from `prompt_registry.py`, which stays DB-free
  (its documented contract, prompt_registry.py:1-28).

### 5. Call-site sweep (the full RECON-0011 §2 list)

At every consuming site, fetch once next to the existing template load and
swap attribute reads:

```python
version = current_prompt(db, template)
...version.system_prompt / version.user_template...
```

Sites: region_author.py:321/333/400/409; analyzer.py:464-470/739-745;
entity_author.py:398/407/527/532/616/621/704/709; gathering.py (via its
loader's consumer); cockpit/app.py:157/163 (through
`_npc_dialogue_system_prompt`, def 1396-1400 — the helper's *signature* may
take the resolved text or the version, executor's choice, but it stays the
single shared helper the preview endpoints reuse), 199, 1638-1648,
1825-1833, 1926-1936, 2543, 2570-2572, 2762-2765 (stream-loop locals — keep
the capture-once pattern, capture from the version), 3019-3020, 3539;
cockpit/crud.py:1654-1655.

Loaders themselves keep returning the head (`PromptTemplate`) — their
world-preferred-else-global semantics (app.py:1307-1311 chain,
`_effective_prompt_row` crud.py:1565) are untouched.

### 6. H1 — one substitution mechanic

Convert the 6 `str.format()` sites to chained `.replace("{var}", value)`
with the exact same variable set:
- region_author.py:321, 400
- entity_author.py:398, 527, 616, 704

Output must be byte-identical for the current (brace-free) template texts.
After this, literal `{`/`}` in any edited template is safe by construction
at every call site.

### 7. Single write shape (writes.py) — `write_prompt_version`

```python
def write_prompt_version(
    db, template_id: str, system_prompt: str, user_template: str,
    note: str | None = None,
) -> PromptVersion
```

- Loads the head (404-equivalent error to caller if absent).
- **C1 validation, fail-closed**: extract every match of
  `\{([A-Za-z_][A-Za-z0-9_]*)\}` from BOTH fields; every extracted name
  must be in the head's `variables` list (`variables` NULL/empty ⇒ any
  identifier placeholder is rejected). On failure raise a typed error
  carrying the offending names; **nothing is written**. JSON-example braces
  (`{"…": …}`) do not match the identifier pattern and pass freely.
- Computes `version_number = MAX + 1` for the head, inserts, sets
  `head.updated_at`.
- The ONLY code path that inserts `PromptVersion`. PATCH route, restore
  route, seed, and migration backfill (may share or replicate the raw
  insert — executor's choice, but if the migration bypasses the helper it
  must be listed in the verify allowlist explicitly).

### 8. API (cockpit/crud.py, prompts router)

- `PATCH /api/prompts/{prompt_id}/text` — body
  `{system_prompt, user_template, note?}` → `write_prompt_version`. 404
  unknown head; **422** with offending placeholder names on C1 failure;
  200 → new version summary `{version_number, created_at, note}`.
- `GET /api/prompts/{prompt_id}/versions` — list, newest first, **no
  bodies** (lazy, same D1 rationale as BRIEF-0008-b):
  `[{version_number, created_at, note, is_current}]`.
- `GET /api/prompts/{prompt_id}/versions/{n}` — one version, with bodies.
- `POST /api/prompts/{prompt_id}/versions/{n}/restore` — D1: reads version
  `n` via `get_version`, calls `write_prompt_version` with its text and
  `note = "restored from v{n}"`. C1 re-validates (fail-closed even on
  restore — if `variables` changed since, the restore is refused, not
  silently admitted).
- Rewire existing readers: `GET /api/prompts/{id}` (crud.py:1629) bodies +
  `version` field via accessor; `_prompt_row_summary` (crud.py:1586)
  `version` → current version_number via accessor.
- Preview endpoints (app.py:123, 167) need no route change — they inherit
  the accessor through the shared helpers (fidelity invariant preserved by
  construction).

### 9. Seed (S2) — scripts/seed_pilot.py

`upsert_prompt_template` (seed_pilot.py:125-148) reworked:
- Head absent → create head (no text fields) + `write_prompt_version` v1
  with the seed text.
- Head present with ≥ 1 version → **never touch text**. Non-text head
  fields (name, variables, destination, notes, is_active) keep the existing
  converge-on-diff behavior unchanged.
- Head present with 0 versions (only reachable mid-bootstrap on a pre-drop
  DB that skipped the migration — abort with a clear "run the migration
  first" message rather than guessing).

### 10. Verify checks (tooling/verify/checks/)

- `prompt_version` table exists with the UNIQUE(head, number) index; head
  no longer has the three dropped columns (live-schema check, precedent:
  schema_partition.py style).
- Static AST scan: `PromptVersion` / `"prompt_version"` referenced only in
  models.py, prompt_store.py, writes.py, the migration script (allowlist
  file, precedent single_canon_write.py).
- Static AST scan: no `Session.add` of `PromptVersion` outside
  `writes.py::write_prompt_version` (+ migration if allowlisted); no
  UPDATE/DELETE targeting `prompt_version` anywhere.
- Static scan (H1): no `.format(` call on a `user_template` /
  `system_prompt` attribute anywhere under src/.
- `prompt_registry.py` check untouched; extend `prompt_model_write.py`'s
  pattern for the new text route if it asserts write-route shape.

### 11. Docs to update

- `world-engine-schema.md` — `prompt_version` table + trimmed
  `prompt_template`, single `Current schema version:` header bump.
- `world-engine-schema-changelog.md` — append vX.YY record.
- `CLAUDE.md` Invariants — add: append-only `prompt_version`; single read
  accessor (`prompt_store.current_prompt`); single write shape
  (`writes.write_prompt_version`); seed-touches-text-never (S2); one
  substitution mechanic (H1).
- `ARCHITECTURE_DECISIONS.md` — append TICKET-0011 record locking
  A2/B1/C1/D1/F1/G1/S2/H1 with the S and H arbitration rationale
  (RECON-0011 §5-6).

## Scope OUT (named, per doctrine)

- **Cockpit edit/history/restore UI** → BRIEF-0011-b.
- **B2** — versioning `model` / `variables` / head metadata (explicitly
  deferred by Nia, to be re-opened "just after").
- Editing `variables`, `name`, `usage`, `model`, `destination` through the
  text route — the route writes text only.
- Version diff view, version pruning/deletion (append-only forever).
- `change_history` on creator-CRUD writes (standing exclusion since
  TICKET-0009).
- The `_effective_prompt_row` multi-active-row nondeterminism observation
  (crud.py:1567-1575) — accepted observation, unchanged.
- Any wording change to any template — this brief must be text-neutral.

## Invariants to defend

1. Every head has ≥ 1 version at all times (migration post-check + S2 +
   append-only).
2. Current = MAX(version_number). No pointer state exists.
3. `prompt_version` is append-only: no UPDATE/DELETE path in the codebase.
4. One read accessor; one write shape. Nothing else touches the table.
5. C1 fail-closed on EVERY write path, restore included.
6. Preview fidelity: previews traverse the same accessor + shared helpers
   as live calls — never a duplicate construction path.
7. H1: exactly one substitution mechanic repo-wide after this brief.
8. Runtime prompts are byte-identical pre/post-brief until the first
   creator edit.
9. `prompt_registry.py` stays DB-free; `effective_model` untouched.

## Done means

- [ ] Migration applied to the live DB; every template has a v1 whose text
      equals its pre-migration text (spot-checkable via
      `GET /api/prompts/{id}/versions/1`).
- [ ] Assembled previews (app.py:123, 167) return byte-identical output
      pre/post-migration.
- [ ] `PATCH .../text` → the very next model call / preview uses the new
      text; a second PATCH yields version 3; history lists 1..3.
- [ ] `POST .../versions/1/restore` appends a new version equal to v1's
      text with the auto note.
- [ ] PATCH with `{typo_var}` → 422 naming `typo_var`; version list
      unchanged.
- [ ] Fresh-DB bootstrap: `seed_pilot.py` on an empty DB yields 18 heads,
      each with exactly v1; a second run changes nothing.
- [ ] Full verify suite green, including the new checks in §10.
