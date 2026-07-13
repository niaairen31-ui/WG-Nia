# BRIEF — Step "Classify TICKET-0025 config tables into the canon stratum"

TICKET-0026 · variant F1 (three named tables). Cites RECON-0026.

## Context

TICKET-0025 added three full-replace config tables — `npc_price`,
`location_subculture`, `world_law` — each with a `DELETE FROM ... WHERE
<parent>` + re-insert hard-delete living in a `writes.py` chokepoint
(RECON-0026 §1c). None was added to `[CANON_TABLES]`, `[ALLOWED_SITES]`, or the
CLAUDE.md closed hard-delete list, unlike the analogous `faction_role`
(RECON-0026 §1a-1b). Because `single_canon_write.py` ignores non-canon tables
by construction, a stray `DELETE FROM npc_price` anywhere in `src/` passes
`/verify` silently today (RECON-0026 §1d). This closes that hole — the fix is
structural (the check now watches these tables), not disciplinary.

## Scope IN

1. **`tooling/verify/canon_write_policy.txt` — `[CANON_TABLES]`.** Append the
   three table names to the canon list (any existing line; keep the section's
   whitespace-separated format):
   `npc_price location_subculture world_law`

2. **`tooling/verify/canon_write_policy.txt` — `[ALLOWED_SITES]`.** Add exactly
   these three entries (path::function, then table), aligned with the existing
   `write_faction_role` entry style:
   ```
   src/world_engine/writes.py::write_npc_prices              npc_price
   src/world_engine/writes.py::write_location_subculture     location_subculture
   src/world_engine/writes.py::write_world_laws              world_law
   ```
   These are the sole write sites: the `DELETE FROM` and the re-insert both sit
   lexically inside each helper (RECON-0026 §1c, §1e), so one entry per table
   covers both — the same function-grain rule that makes `write_faction_role`'s
   single entry sufficient. Do NOT allowlist the callers (`set_npc_prices`,
   `set_location_subculture`, `create_world`); they hold no write site.

3. **`CLAUDE.md` — closed hard-delete list.** Immediately after the existing
   `write_faction_role(mode="delete")` sentence in the "Hard deletes are a
   closed, named list" invariant, add this sentence VERBATIM:

   > Full-replace config deletes (whole-set replace, not single-row
   > correction): `write_npc_prices`, `write_location_subculture`, and
   > `write_world_laws` each `DELETE FROM` their table scoped to one parent
   > (NPC / location / world) then re-insert the submitted set, in one
   > transaction — creator-CRUD and world-bootstrap only (`set_npc_prices`,
   > `set_location_subculture`, `create_world`), never reachable from any AI or
   > play path. These tables carry no `change_history` by design
   > (metadata-config category); the full-replace IS their write shape.

4. **`tooling/standards/ARCHITECTURE_DECISIONS.md` — append-only record.** Add a
   new dated subsection at the end of the CANON-WRITE DOCTRINE section (do NOT
   edit K1 in place — the registry is append-only):

   > **CANON STRATUM EXTENSION (TICKET-0026).** `npc_price`,
   > `location_subculture`, `world_law` join the canon stratum, allowlisted at
   > their `writes.py` chokepoints. The authoritative canon enumeration is
   > `canon_write_policy.txt`'s `[CANON_TABLES]`, not the frozen "15 tables"
   > figure in the K1 record above — that figure predates `faction_role`,
   > `npc_goal`, `agenda`, `agenda_step`, `goal_agenda_link`, and now these
   > three. Read K1's count as illustrative-at-time-of-writing; the policy file
   > is the single source of truth.

5. Regenerate the decisions index if it derives from ARCHITECTURE_DECISIONS:
   `python tooling/glue/gen_decisions_index.py` (only if that script exists and
   the new subsection would surface in `DECISIONS_INDEX.md`).

## Scope OUT

- **`goal_prerequisite` and `event_entity`** (RECON-0026 §1f) share the identical
  gap but are OUT of this brief — Nia scoped issue 1 to three tables (decision
  F1). Do not touch them.
- **`prompt_variable`** — child of `prompt_template` (pipeline-internal); leave
  it exactly as is. Do not add it to `[CANON_TABLES]`.
- **No completeness check** (`table_stratum_coverage.py` or similar). The
  anti-recurrence guard that would fail on any unclassified `table=True` model
  was considered (decision F3) and is deferred, not rejected. Do not build it.
- **No change to write semantics.** Full-replace stays full-replace. Do NOT
  convert these deletes to soft-archival / status flags.
- **The dead-import cleanup** of `write_location_subculture` at `app.py:124`
  (RECON-0026 §1e) is OUT — it is BRIEF-0026-b's neighbourhood, not this one.
- No new `writes.py` helpers, no new routes, no schema change.

## Invariants to defend

This brief DEFENDS two CLAUDE.md invariants that are currently holed:
- "Exclusion is structural, never disciplinary" — the three deletes were
  invisible to the gate; after this brief the gate watches them.
- "Hard deletes are a closed, named list … never added silently" — three were
  added silently in TICKET-0025; this names them.

Threat to avoid: weakening the check to accommodate the new entries. The check
logic is untouched; only the policy DATA grows. If adding the tables to
`[CANON_TABLES]` surfaces any OTHER now-visible canon write that was previously
ignored, that is a real finding — REPORT it, do not allowlist it to force green.

## Done means

- [ ] `[CANON_TABLES]` contains `npc_price`, `location_subculture`, `world_law`.
- [ ] `[ALLOWED_SITES]` contains the three `writes.py::write_*` entries from
      Scope IN item 2, exactly.
- [ ] `python -m tooling.verify.run` (or the single_canon_write invocation) is
      GREEN.
- [ ] **Negative proof (one-off):** temporarily insert `db.execute(text("DELETE
      FROM npc_price WHERE 1=0"))` into any `src/` function NOT in
      `[ALLOWED_SITES]`; re-run the check; it reports RED naming that
      file::function and `npc_price`; then REVERT the temporary line and confirm
      GREEN again. Record both verdicts.
- [ ] CLAUDE.md shows the verbatim sentence from Scope IN item 3 in the closed
      hard-delete list.
- [ ] ARCHITECTURE_DECISIONS ends the CANON-WRITE DOCTRINE section with the
      Scope IN item 4 subsection.
- [ ] `/review-step` and `/close-step` run (policy + standards edits; no engine
      code, but the verify gate is touched).

## Docs to update

- `CLAUDE.md` (Scope IN 3) and `ARCHITECTURE_DECISIONS.md` (Scope IN 4) ARE the
  doc updates. No schema changelog entry (no schema change).
