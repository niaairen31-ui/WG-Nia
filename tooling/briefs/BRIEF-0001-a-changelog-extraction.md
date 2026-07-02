# BRIEF — Step "Schema changelog extraction + single version source" (BRIEF-0001-a)

Ticket: TICKET-0001-doc-partition. Recon: RECON-0002 (result). Sequence:
this brief runs BEFORE BRIEF-0001-b.

## Context

`world-engine-schema.md` mixes hot truth (TABLES/INDEXES/RELATIONS/MIGRATION)
with cold history (a 1,200-line CHANGELOG), so every reader pays for both.
Worse, RECON-0002 found THREE disagreeing version assertions in the file
(intro `1.25` at :3, newest entry `v1.66` at :987, footer `1.16` at :2223)
and two contradicting governance instructions (`CLAUDE.md:59-60` names a
changelog file that does not exist; `close-step.md:5-6` appends to the
schema file directly). Locked decisions: A1 (extract), A1-guard (single
`Current schema version:` header line), N1 (new file name/location), V1
(version numbers computed, never chosen).

RECON anchors below were valid at recon time; re-verify each anchor before
editing (content match over line number).

## Scope IN

1. **Create `world-engine-schema-changelog.md` at repo root** with this
   exact header, then the CHANGELOG entries moved verbatim:

   ```
   # world-engine-schema — CHANGELOG

   Append-only history of `world-engine-schema.md`, extracted verbatim
   (BRIEF-0001-a, no schema change). Newest entry first. The current
   version number lives ONLY in `world-engine-schema.md`
   (`Current schema version:` line); this file is the log, never the
   source of "what version are we at".
   ```

   Move lines `world-engine-schema.md:985–2221` (the `## CHANGELOG` heading
   and every entry, `v1.66` down to `v1.1`) byte-for-byte. No entry is
   reworded, reordered, merged, or dropped.

2. **In `world-engine-schema.md`:**
   - Delete the moved CHANGELOG section (heading included).
   - Delete the stale footer line (`:2223` — `*Version 1.16 — Co-built
     with Claude, June 2026*`). It is not moved to the changelog file.
   - Replace the stale intro line (`:3` — `*Version 1.25 — Local phase
     (SQLite → Supabase)*`) with these two plain-text lines (no italics,
     no bold — the first line is a machine-parsed grep target):

     ```
     Current schema version: v1.66
     Append-only history: world-engine-schema-changelog.md (repo root)
     ```

3. **Rewrite the same-file cross-reference** at `world-engine-schema.md:809`:
   the phrase `see CHANGELOG` becomes
   `see world-engine-schema-changelog.md`. No other inline pointer among
   the 27 listed in RECON-0002 Zone A3 is touched.

4. **Repoint `CLAUDE.md:59-60`** (currently: Claude Code owns schema version
   numbers, recorded in `tooling/standards/schema_changelog.md` — a file
   that has never existed). Replace the sentence with, verbatim:

   ```
   Schema versions are computed, never chosen: on any schema-touching step
   closure, new version = the `Current schema version:` line in
   `world-engine-schema.md`, minor + 1 (v1.66 -> v1.67). That header line
   is the single source for the current number; the append-only log lives
   in `world-engine-schema-changelog.md` (repo root). If the minor part
   reaches 99, stop and escalate (D1-c).
   ```

5. **Fix the phantom filename at `CLAUDE.md:63`**: the "where things live"
   list entry `schema_changelog.md` becomes
   `world-engine-schema-changelog.md (repo root)`.

6. **Rewrite `.claude/commands/close-step.md:5-6`** (the changelog step)
   with, verbatim:

   ```
   **Changelog** — if the schema was touched: read the
   `Current schema version: vX.YY` line in `world-engine-schema.md`,
   compute the new version (minor + 1), prepend the new entry to
   `world-engine-schema-changelog.md`, and update the header line to the
   new version. If the schema was not touched, confirm no entry is needed.
   ```

7. **Create `tooling/verify/checks/schema_partition.py`** (plain Python,
   exit 0 pass / 1 fail, last stdout line = message; runs with no DB):
   - `world-engine-schema.md` contains exactly one line matching
     `^Current schema version: v\d+\.\d+$`.
   - `world-engine-schema.md` contains no `## CHANGELOG` heading and no
     line matching `^- \*\*v\d+\.\d+\*\*`.
   - `world-engine-schema-changelog.md` exists and contains both boundary
     entries (`- **v1.66**` and `- **v1.1**`).
   - The version in the header line equals the version of the FIRST entry
     line in the changelog file (newest-first invariant).

8. **Update `tooling/tickets/TICKET-0001-doc-partition.md`**: front-matter
   `brief_ids: [BRIEF-0001-a, BRIEF-0001-b]`,
   `schema_version_touched: none`; add under `### Machine-checkable`:

   ```
   - [ ] hot/cold partition holds  -> verify/checks/schema_partition.py
   ```

## Scope OUT

- The decisions index, baseline, strict-header gate, `next_id.py`, and all
  CLAUDE.md numbering governance — that is BRIEF-0001-b.
- The stale-references sweep (`README.md:24` project tree, bare-filename
  mentions inventoried in RECON-0002 Zone C) — separate ticket.
- The root `CHANGELOG.md` (French application-level changelog): do not
  touch, rename, or merge it. It is unrelated to the schema changelog.
- No rewording, normalization, or "cleanup" of any changelog entry or any
  other part of `world-engine-schema.md` beyond the lines named above.
- Decision H (backup hook): untouched.
- No schema version bump: this step is documentation-only
  (`no schema change`).

## Invariants to defend

- **History is sacred**: the CHANGELOG moves byte-for-byte; deleting the
  two stale version assertions (intro/footer) is the ONLY destruction
  authorized, and only because each is a false duplicate of a fact now
  stated once.
- **Single source**: after this step, exactly one place in the repo asserts
  the current schema version.
- **Model proposes, code judges** (extended by V1): the next version number
  becomes an arithmetic fact, not a judgment.

## Done means

- [ ] `world-engine-schema-changelog.md` exists at repo root, header as
      specified, entries v1.66→v1.1 present verbatim.
- [ ] `world-engine-schema.md`: no CHANGELOG section, no `1.25`/`1.16`
      assertions, header lines present as specified, `:809` rewritten.
- [ ] `CLAUDE.md` and `close-step.md` carry the exact replacement wording.
- [ ] `python tooling/verify/checks/schema_partition.py` exits 0
      (PowerShell, venv active, `$env:PYTHONPATH="src"`).
- [ ] `/verify TICKET-0001` green on this check.
- [ ] Live gate (Nia): asked "what is the current schema version?", Claude
      Code answers from the header line without opening the changelog file.

## Docs to update

This step IS the doc update. The consolidated decision record for the whole
ticket is written in BRIEF-0001-b (after the baseline snapshot, so it passes
the new strict-header gate). `/review-step` + `/close-step` required (repo
governance touched, no engine code).
