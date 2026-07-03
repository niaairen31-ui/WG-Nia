# BRIEF — Step "single_canon_write check + closed hard-delete list" (BRIEF-0003-b)

Ticket: TICKET-0003. Recon: RECON-0003 (result). Sequence: runs AFTER
BRIEF-0003-a is merged (the allowlist below assumes the post-M1/W1 state).

## Context

Locked decisions: K1 (three-strata table classification), T1 (static AST
scan, `src/` only, function-grain allowlist), L1 (the three unnamed
hard-delete routes in crud.py become NAMED, closed-list exceptions). The
doctrine "two sanctioned canon-write paths" stops being a sentence in
CLAUDE.md and becomes an exit code: any write to a CANON table from a
site not on the policy file fails /verify, naming file, function, table.

## Scope IN

1. **Create `tooling/verify/canon_write_policy.txt`** — the single policy
   file, two sections, exact format:

   ```
   [CANON_TABLES]
   world entity character location faction faction_membership relation
   knowledge ledger item skill skill_definition discoverable_detail
   event artifact

   [ALLOWED_SITES]
   # path::function            tables
   src/world_engine/writes.py::write_relation            relation
   src/world_engine/writes.py::write_knowledge           knowledge
   src/world_engine/writes.py::write_ledger_entry        ledger
   src/world_engine/writes.py::write_membership          faction_membership
   src/world_engine/writes.py::write_skill_tier          skill
   src/world_engine/writes.py::delete_world_cascade      *
   ```

   plus the remaining seed entries derived from RECON-0003 Zone B for
   every site that (i) writes a CANON table, (ii) still exists after
   BRIEF-0003-a, i.e. at minimum: `cockpit/app.py::_apply_mutation`
   (entity, item, discoverable_detail — the three direct branches),
   `cockpit/app.py::activate_world|create_world|_activate_world_core`
   (world), `cockpit/app.py::create_player_character` (entity, character,
   skill), `cockpit/app.py::_perform_travel` (character),
   `cockpit/crud.py::_create_entity_core|update_entity|delete_entity`
   (entity + extension tables), the `discoverable_detail` CRUD routes,
   the `skill_definition` CRUD routes, and the three L1 deletes
   (`delete_relation`, `delete_knowledge`, `delete_discoverable_detail`).
   **Rule: every seeded entry must correspond to a site documented in
   RECON-0003. If running the check reveals a canon-write site NOT in
   RECON-0003, stop-and-report — do not silently allowlist it.**
   Ephemeral and pipeline tables (K1 strata 2-3) do not appear in the
   policy file at all.

2. **Create `tooling/verify/checks/single_canon_write.py`** (exit 0/1,
   no DB, stdlib `ast` only):
   - Walks every `.py` under `src/`. Detects write sites: attribute calls
     `.add(...)` / `.delete(...)` on any receiver, and `.execute(...)` /
     `.exec(...)` whose string argument matches
     `INSERT INTO|UPDATE|DELETE FROM` (raw SQL).
   - Attributes each site to a table: constructor argument
     (`db.add(Skill(...))` → `skill`); else the variable's assignment
     within the same function (from a `Model(...)` construction or a
     query naming the model); raw SQL → regex on the table token.
   - A site attributed to a CANON table is legal iff `path::function`
     appears in `[ALLOWED_SITES]` and covers that table (`*` = all).
   - A canon-table site that CANNOT be attributed statically → failure
     (`unattributable write site`), by design: RECON-0003 D1 confirmed
     zero dynamic-dispatch writes exist in `src/` today, so anything
     unattributable is new and must be made legible before merging.
   - Sites on non-canon tables: ignored entirely.
   - Failure message: `path::function writes <table> — not in
     canon_write_policy.txt`.
   - Deterministic; no options, no config beyond the policy file.

3. **L1 — CLAUDE.md closed hard-delete list**: locate the Invariants
   sentence RECON-0003 quotes ("...No other delete-side helper exists;
   any new hard-delete path must be named here, not added silently.")
   and insert immediately after it, verbatim:

   ```
   Named creator-correction hard-deletes (closed list, BRIEF-0003-b):
   `delete_relation` (crud.py) and `delete_knowledge` (crud.py) — each
   discards the row's `change_history` with the row; `delete_discoverable_detail`
   (crud.py). These exist so the creator can erase a mis-entered row; they
   are creator-CRUD-only, never reachable from any AI or play path. The
   closed list is enforced structurally by verify/checks/single_canon_write.py.
   ```

4. **Append the consolidated decision record** to
   `tooling/standards/ARCHITECTURE_DECISIONS.md` (append-only, before
   `## Deferred decisions`), header exactly:

   ```
   ## CANON-WRITE DOCTRINE — table classification, write normalization, structural gate (BRIEF-0003-a, BRIEF-0003-b, no schema change)
   ```

   Body: K1 strata (list the three, with table membership), M1, W1, L1
   (with the explicit note that soft-archival of the three deletes was
   considered and deferred, not rejected), T1 (function-grain static scan,
   `src/`-scoped; scripts and migrations out of scope by construction —
   none is a live path). Then regenerate `DECISIONS_INDEX.md`
   (close-step covers this).

5. **Update `tooling/tickets/TICKET-0003-single-canon-write.md`**:
   front-matter `brief_ids: [BRIEF-0003-a, BRIEF-0003-b]`; Machine line:

   ```
   - [ ] no canon write outside sanctioned sites  -> verify/checks/single_canon_write.py
   ```

## Scope OUT

- No SQLite triggers (T3 deferred). No DB-level assertions.
- No soft-archival conversion of the three L1 deletes (deferred, would be
  its own ticket).
- No scanning of `scripts/` or `migrate_v1_*.py` — out of scope by
  construction, not by allowlist.
- No new writes.py helpers beyond what a landed in BRIEF-0003-a.
- The `models.py` `__all__` omissions (RECON A1 fact): report-only fact,
  not this ticket.
- No policy entries for ephemeral/pipeline tables — the `proposed_mutation`
  force-delete rule stays governed by its own documented exception, not
  this check.

## Invariants to defend

- **Two sanctioned canon-write paths**: this brief is its structural
  enforcement; the policy file must not quietly widen it — hence the
  stop-and-report rule on undocumented sites.
- **No second source of truth**: the policy file states WHO may write;
  it never restates schema facts.
- **History is sacred / archive byte-intact**: ARCHITECTURE_DECISIONS is
  append-only (one record added); CLAUDE.md gains lines, loses none.

## Done means

- [ ] `python tooling/verify/checks/single_canon_write.py` exits 0 at HEAD
      (PowerShell, venv, `$env:PYTHONPATH="src"`).
- [ ] Red test: add a temporary `db.add(Entity(...))` in an unlisted
      module → check exits 1 naming file, function, table; revert.
- [ ] Red test: remove one line from `[ALLOWED_SITES]` → exit 1; restore.
- [ ] `/verify TICKET-0003` green (this check + the decisions_index and
      schema_partition checks still green).
- [ ] CLAUDE.md carries the closed-list block verbatim; DECISIONS_INDEX
      regenerated with the new record (strict-header gate passes).
- [ ] Live gate (Nia): per the ticket — inject, see red, revert, see green.

## Docs to update

Steps 3-4 ARE the doc updates. No schema change, no changelog entry.
/review-step + /close-step required (governance + tooling).
