# BRIEF — Step "Generated decisions index + strict-header gate + mechanical IDs" (BRIEF-0001-b)

Ticket: TICKET-0001-doc-partition. Recon: RECON-0002 (result). Sequence:
runs AFTER BRIEF-0001-a is merged.

## Context

`tooling/standards/ARCHITECTURE_DECISIONS.md` (~210 KB, 47 `## ` records)
has no cheap lookup surface. RECON-0002 Zone B found 20/47 headers deviate
from the nominal pattern in three shapes (no BRIEF ref; extra/reordered
tokens; one multi-BRIEF record at `:1650`) — so the index generator must be
tolerant (G1), while a deterministic gate stops NEW deviations (G3-b). The
archive stays byte-for-byte intact (B1 locked). Separately, ID assignment
moves from human judgment to computation (U1: unified 4-digit ticket ID,
`next_id.py`). Zone E confirmed the verify seam: a check is just a `.py`
under `tooling/verify/checks/` referenced from the ticket's Machine section;
`decisions_index.py` will be the repo's first "regenerate and diff" check.

## Scope IN

1. **Create `tooling/glue/gen_decisions_index.py`** — tolerant generator:
   - Reads `tooling/standards/ARCHITECTURE_DECISIONS.md`. Collects every
     line starting `## ` EXCEPT lines inside fenced code blocks (track
     ``` fences while scanning; RECON found no false positives today, the
     guard is defensive).
   - For each header, extracts: line number, full title text, ALL tokens
     matching `BRIEF-\d{2,4}(-[a-z])?` (zero, one, or many — anywhere in
     the header), ALL tokens matching `v\d+\.\d+`. Empty fields allowed.
   - Writes `tooling/standards/DECISIONS_INDEX.md`, deterministic output
     (same input → identical bytes), one table row per record:
     `| line | title | briefs | versions |`, preceded by this exact header:

     ```
     # DECISIONS_INDEX — generated file, DO NOT EDIT
     Regenerate: python tooling/glue/gen_decisions_index.py
     Source: tooling/standards/ARCHITECTURE_DECISIONS.md (byte-intact archive)
     ```
   - The script only ever writes `DECISIONS_INDEX.md`. It never modifies
     the archive.

2. **Snapshot the grandfather baseline** — create
   `tooling/verify/baselines/decisions_headers.baseline`: the verbatim
   text of every `## ` header line existing at execution time (the 47),
   one per line. Header TEXT, not line numbers (append-only growth shifts
   lines; text is stable). Do this BEFORE step 5.

3. **Create `tooling/verify/checks/decisions_index.py`** (exit 0/1, no DB):
   - (a) Regenerates the index in memory and compares with the committed
     `DECISIONS_INDEX.md`; any difference → exit 1, message
     `index stale: regenerate gen_decisions_index.py`.
   - (b) Every header NOT present in the baseline file must match, in
     full, verbatim regex:

     ```
     ^## .+ \(BRIEF-\d{4}(-[a-z])?(, BRIEF-\d{4}(-[a-z])?)*, (schema v\d+\.\d+|no schema change)\)$
     ```

     Any new header failing → exit 1, message quoting the offending header.
   - Baseline headers are never validated against the pattern
     (grandfathered, byte-intact).

4. **Create `tooling/glue/next_id.py`** — mechanical ID counter:
   - Scans filenames in `tooling/tickets/`, `tooling/recon/`,
     `tooling/briefs/` for `(TICKET|RECON|BRIEF)-(\d{4})` (exactly 4
     digits; legacy two-digit `BRIEF-NN` names are a distinct namespace,
     invisible to the counter).
   - Prints max+1, zero-padded to 4 digits, and NOTHING else. Never
     creates, renames, or writes any file. Current repo state must yield
     `0003` (max of TICKET-0001, RECON-0002).

5. **Append the consolidated decision record** to
   `tooling/standards/ARCHITECTURE_DECISIONS.md` (append-only; placed with
   the other records, before the `## Deferred decisions` section), header
   exactly:

   ```
   ## DOCUMENTATION PARTITION — hot/cold split, generated index, mechanical numbering (BRIEF-0001-a, BRIEF-0001-b, no schema change)
   ```

   Body: summarize locked decisions A1, A1-guard, N1, B1, G1/G3-b, U1,
   V1, U-now, with the one-line reasoning for each as stated in the ticket
   and this brief. This record post-dates the baseline, so it MUST pass
   the strict gate — that is the point.

6. **Regenerate the index** after step 5 and commit it.

7. **CLAUDE.md — add a `Numbering & decisions governance` block** (verbatim):

   ```
   ## Numbering & decisions governance
   - IDs are computed, never chosen: next ID = python tooling/glue/next_id.py
     (max over tickets/recon/briefs, 4 digits). A ticket, its recon, and its
     brief(s) share one number: TICKET-NNNN / RECON-NNNN / BRIEF-NNNN-a, -b.
   - Legacy two-digit BRIEF-NN identifiers are a closed, grandfathered
     namespace: never reused, never renumbered.
   - New decision records in tooling/standards/ARCHITECTURE_DECISIONS.md use
     the header form: ## TITLE (BRIEF-NNNN[-x][, BRIEF-NNNN[-x]...], schema vX.YY | no schema change)
     — enforced by verify/checks/decisions_index.py against the baseline.
   - tooling/standards/DECISIONS_INDEX.md is generated; never edit by hand.
   ```

8. **Append to `.claude/commands/close-step.md`** (after the changelog
   step), verbatim:

   ```
   **Decisions index** — if a decision record was added to
   tooling/standards/ARCHITECTURE_DECISIONS.md, run
   python tooling/glue/gen_decisions_index.py and commit the regenerated
   DECISIONS_INDEX.md.
   ```

9. **Update `tooling/tickets/TICKET-0001-doc-partition.md`** — add under
   `### Machine-checkable`:

   ```
   - [ ] index ≡ headers, new headers strict  -> verify/checks/decisions_index.py
   ```

## Scope OUT

- No normalization, rewording, or renumbering of ANY existing header or
  record — the 20 deviant headers stay exactly as they are, forever.
- No retroactive renaming of TICKET-0001 / RECON-0002 / legacy BRIEF-NN
  files.
- The `/pipeline` orchestration command (Q1/R1/S1) — later ticket, after
  concrete checks exist (order O1).
- The stale-references sweep — separate ticket.
- Decision H — untouched.
- No B3 `DOCTRINES.md`.
- `gen_decisions_index.py` gains no options, no CLI flags, no config file
  (minimal first: one input, one output).

## Invariants to defend

- **History is sacred / archive byte-intact**: the only write to
  `ARCHITECTURE_DECISIONS.md` is the appended record of step 5.
- **No second source of truth**: the index is a derived artifact, proven
  derived by check (a); the baseline freezes the past instead of editing it.
- **Model proposes, code judges**: header discipline for the future is
  enforced by exit code, not by instruction alone.

## Done means

- [ ] `python tooling/glue/gen_decisions_index.py` produces
      `DECISIONS_INDEX.md` with 48 rows (47 + the new record); running it
      twice yields identical bytes.
- [ ] Baseline file contains exactly the 47 pre-existing headers.
- [ ] `python tooling/verify/checks/decisions_index.py` exits 0; manually
      appending a malformed test header (then reverting) makes it exit 1
      naming the header.
- [ ] `python tooling/glue/next_id.py` prints `0003`.
- [ ] `/verify TICKET-0001` green on both checks (this one +
      `schema_partition.py`).
- [ ] Live gate (Nia): pick any decision by topic in `DECISIONS_INDEX.md`
      and jump to it in the archive by line; ask Claude Code for the next
      ticket number → it runs `next_id.py`, answers `0003`.

## Docs to update

Step 5 IS the ARCHITECTURE_DECISIONS update; steps 7–8 ARE the governance
updates. No schema change, no changelog entry. `/review-step` +
`/close-step` required.
