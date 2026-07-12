# BRIEF — Step "Corrective: faction_role relational table replaces role_capacities JSON + metadata.roles" (TICKET-0024, BRIEF-0024-d)

## Context

TICKET-0024 is merged and live. RECON-after-the-fact found that BRIEF-0024-a
built `faction.role_capacities` (JSON map) UNAWARE of a pre-existing
declared-role structure: `entity.metadata['roles']` (BRIEF-31, schema
v1.42) — the "ROLES" editor on the faction sheet, already consumed by the
membership role select (`GET /entities/{id}/roles`, crud.py:1654). The
faction sheet now shows TWO disconnected role vocabularies. Creator
decision: fix by promoting roles to a **relational table** — no JSON on
either side ("informations in columns and tables"; UI fields living in
metadata blobs will be hunted globally in a separate future ticket; this
brief corrects the roles case only). Locked: S1 (guarded hard delete),
T1 (rename realigns active memberships via close+reopen).

## Scope IN

1. **New model `FactionRole`** (models.py, next to `Faction`):
   `id` (str pk, uuid idiom), `world_id` (FK), `faction_id` (FK
   `faction.id`), `name` (str, non-empty), `description` (str, nullable),
   `max_holders` (int, nullable — NULL = unlimited; NOT named "limit"),
   `position` (int, display order), `created_at`, `created_by` (str).
   Comment block: "Declared role vocabulary of a faction. Public by
   construction (BRIEF-31 lineage) — safe to expose to prompts and
   player-facing reads. Closed vocabulary for the AI path (K1)."
2. **Structural invariant**: unique index
   `CREATE UNIQUE INDEX idx_faction_role_name ON faction_role (faction_id, name COLLATE NOCASE)`
   — case-duplicate role names become schema-impossible; delete the
   equivalent casefold-collision check from the old writer when it is
   removed (item 5).
3. **Migration script** `scripts/migrate_vX_YY_faction_role_table.py`
   (Claude Code assigns version; idempotent, v1_74 idiom), in ONE
   transaction:
   a. Create `faction_role` + index.
   b. For every faction entity: copy `metadata['roles']` entries in array
      order -> rows (`position` = array index, `description` preserved,
      `max_holders` NULL, `created_by='migration:0024-d'`).
   c. Merge `faction.role_capacities` limits INTO those rows by
      casefold name match; a capacity key with NO matching metadata role
      becomes a NEW row (appended after the metadata ones,
      `description` NULL).
   d. Case-collision inside a single faction's sources -> ABORT the whole
      migration with a readable list (faction name + colliding names);
      nothing written. Creator fixes in the live UI and re-runs.
   e. Strip the `roles` key from `entity.metadata` (dict REASSIGNMENT on
      `metadata_`) — single source of truth. Destructive transform on the
      blob: data moved, not lost, but backup is mandatory first
      (danger_class below).
   f. Drop column `faction.role_capacities` (SQLite `ALTER TABLE ... DROP
      COLUMN`, supported ≥3.35; guard with a version check, abort with
      instructions otherwise).
4. **Writers (writes.py)** — replace `write_faction_role_capacities`
   (writes.py:604) entirely with the `faction_role` family, sole
   chokepoints:
   - `write_faction_role(mode="create", ...)`: validates non-empty name,
     `max_holders` NULL or int >= 1; `position` = max+1 unless given.
     Uniqueness is the INDEX's job — catch IntegrityError and re-raise as
     the readable ValueError idiom.
   - `mode="update"`: description / max_holders / position. Renames go
     through `mode="rename"` ONLY.
   - `mode="rename"` (T1): update `name`; then close+reopen every ACTIVE
     membership of this faction whose true `role` casefold-equals the OLD
     name (`changed_by="creator:rename"`), preserving `cover_role`,
     `is_primary`, `is_secret`. Closed membership rows keep the old
     string untouched — history is never rewritten. `cover_role` strings
     are narrative masks: NEVER realigned.
   - `mode="delete"` (S1): hard delete, BLOCKED if any active membership
     bears the role (casefold) -> ValueError
     `"faction_role: {n} active member(s) still hold {name!r}"`.
     No change_history: this table is curated config (faction_type
     family), not event canon — the history of role TENURE already lives
     in closed membership rows.
5. **Remove the parallel structure** (all merged 0024-a surfaces):
   - models.py:201-207 column + comment — gone (migration item 3f).
   - writes.py:604-646 old writer + its header note (writes.py:63) — gone.
   - crud.py:1670-1708 GET/PATCH `/api/factions/{id}/role-capacities` —
     replaced by `faction_role` CRUD routes: GET list (ordered by
     `position`), POST create, PATCH update/rename, DELETE, PATCH reorder
     (full ordered id list). All through the writers.
   - index.html: delete the "Rôles & capacités" section (5921-5922), its
     renderer/draft (6572+) and CSS note (3120-3126).
6. **Rewire the surviving ROLES editor** (index.html 5912-5916, renderer
   6528+, flush at 6165 / authorSave merge into `metadata.roles`): it now
   reads/writes the `faction_role` routes (no longer part of the generic
   entity PUT payload). Each line gains the numeric limit field LEFT of
   the name: `Limite | Rôle | Description`, hint "vide = illimité".
   Reorder arrows drive the reorder route. Rename in-place triggers the
   rename writer (confirm dialog naming the count of active memberships
   that will be realigned). Delete blocked shows the writer's readable
   error.
7. **Undeclared-borne-roles adoption** (the -a pre-fill, translated): on
   sheet load, distinct true `role` values on ACTIVE memberships that
   match NO declared row (casefold) render as a dim hint line with a
   one-click "+ déclarer" (creates a row, limit empty). Zero writes until
   click.
8. **Rewire AI-path readers** (app.py role_change effect branch,
   1415-1448): step (ii) resolves against
   `SELECT ... FROM faction_role WHERE faction_id = ? AND name = ? COLLATE NOCASE`;
   capacity check reads `max_holders`; L2 declare INSERTs a `faction_role`
   row (`description` NULL, `max_holders` NULL,
   `created_by=f"mutation:{mutation_id}"`) via the create writer, same
   SAVEPOINT as the occupation — the "role never exists without a holder"
   invariant is unchanged. Reject strings unchanged (verify checks depend
   on them).
9. **Rewire `list_faction_roles`** (crud.py:1654): reads the table,
   ordered by `position`, returns `{name, description}` (same shape — the
   membership role select keeps working unmodified; add `max_holders` to
   the payload only if the select needs nothing else — it does not:
   names-only contract stands, do not leak counts here).
10. **Verify checks**: update `schema_0024.py` (table + index exist;
    `role_capacities` column ABSENT; no `metadata.roles` key on any
    faction) and `role_closed_vocab.py` (resolution reads `faction_role`).
    `effects_vocab.py`, `effects_ledger_source.py`, `h1_strip_bounded.py`,
    `prereq_judge.py` untouched — they must stay green (regression gate).

## Scope OUT

- NO change to prerequisites (0024-b) or to the other two effect types —
  `relation_delta` / `ledger_transfer` code paths untouched.
- NO prompt changes, NO apply-prompt script — the rubric never listed
  roles (by design) and the declare flow is semantically identical.
- NO global "UI fields out of metadata blobs" hunt — that is Nia's next
  ticket (she assigns the number); this brief corrects ROLES only. Do not
  touch other `metadata` keys even if spotted: REPORT ONLY.
- NO role uniqueness/eviction beyond `max_holders` counting; NO
  `membership_change`; NO soft-delete/`retired_at` (S2 rejected).
- NO change_history table/column for `faction_role` (curated config).
- NO renaming of the `role` free-text column on `faction_membership` and
  no FK from membership to `faction_role` — membership keeps the string
  (closed rows are history; an FK would forbid deleting renamed-away
  roles). Creator CRUD on memberships stays free-form (K1: closed
  vocabulary constrains the AI path only).

## Invariants to defend

- **History is sacred**: T1 rename never edits closed membership rows;
  realignment of active ones is close+reopen; metadata.roles strip is the
  documented destructive-transform exception of THIS migration (data
  moved into the table, backup first).
- **Structural over disciplinary**: the case-collision check moves from
  code (old writer) into the unique index — note this explicitly in the
  ARCHITECTURE_DECISIONS record.
- **Single canon-write paths**: only the `write_faction_role` family
  touches the table; routes and the L2 declare branch call it.
- **Exclusion is structural**: `faction_role` is public-by-construction
  (BRIEF-31 lineage) — no secret filtering needed, but true `role` /
  `cover_role` semantics on MEMBERSHIPS are unchanged; capacity counting
  still reads true `role`, never `cover_role`.
- **JSON reassignment rule**: the metadata strip (migration 3e) reassigns
  `metadata_`.

## Done means

- [ ] Migration on a copy of live: `faction_role` rows match old `metadata.roles` order + merged limits; `role_capacities` column gone; no faction retains a `metadata.roles` key; second run = no-op
- [ ] Migration with a planted case-collision -> aborts listing faction + names; DB unchanged
- [ ] Faction sheet shows ONE roles section: `Limite | Rôle | Description` lines, reorder works, "vide = illimité" hint present; "Rôles & capacités" section gone
- [ ] Setting limit 1 on "Le Président du Conseil" persists (row `max_holders=1`)
- [ ] Creating a role whose name differs only by case from an existing one -> readable 422 (index-backed)
- [ ] Renaming a role held by 2 active members -> confirm names the count; after confirm, both active memberships closed+reopened with the new string, `changed_by='creator:rename'`; their CLOSED rows keep the old string
- [ ] Deleting a role with an active holder -> blocked with the count; without holders -> row gone
- [ ] Undeclared borne role shows the dim "+ déclarer" hint; click declares it (limit empty)
- [ ] Membership role select still lists declared roles (order preserved)
- [ ] `role_change` effect: full role still rejects `is full (n/n)`; undeclared without flag still rejects; `declare:true` INSERTs the row and the NPC holds it — one approval
- [ ] All 0024 verify checks green, including regression on prereq/effects checks; `/review-step` and `/close-step` pass

**Live deployment sequence (danger_class: migration + destructive_data):**
backup (`scripts/backup.py`) -> migration script -> restart cockpit ->
no seed -> no apply-prompt script.

## Docs to update

- `world-engine-schema.md`: `faction_role` table (full column list +
  index + "public by construction" note), `faction.role_capacities`
  REMOVED, `entity.metadata.roles` REMOVED (pointer to the table),
  changelog vX.YY.
- `ARCHITECTURE_DECISIONS.md`: record "0024-d corrective — roles
  promoted from JSON (metadata.roles + role_capacities) to relational
  `faction_role`: creator doctrine 'UI-visible data lives in columns and
  tables, not JSON blobs' (global blob-extraction hunt = future ticket);
  case-uniqueness moved from code check to unique index; S1 guarded hard
  delete; T1 rename realigns active memberships only."
- `CLAUDE.md`: amend the 0024 standing line: declared roles live in
  `faction_role`; add the RECON lesson verbatim:
  "RECON: trace every UI-visible field to its storage, including
  `entity.metadata` JSON keys — grepping columns is not sufficient."
