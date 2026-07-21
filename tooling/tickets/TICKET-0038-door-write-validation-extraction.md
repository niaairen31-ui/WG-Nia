---
id: TICKET-0038
title: Extract door-payload validation to clear function_length on write_location_doors
type: bug
status: live-gate
created: 2026-07-21
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # pure intra-module extraction: no canon write added or moved, no schema, no migration
blast_radius: small
brief_ids: [BRIEF-0038-a]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> [Escalation from the TICKET-0037 verify gate, Nia:] TICKET-0037 is now 7/8
> green -- the last failure is `function_length.py` failing on
> `write_location_doors` (99 lines) in `src/world_engine/writes/config.py`,
> which belongs to TICKET-0034 and is untouched by anything in TICKET-0037.
> How should I handle it?

Follow-up, same session: TICKET-0034 is merged and closed; TICKET-0035 already
solved a sibling problem (a check surfacing an over-budget code unit with no
baseline to fall back on) and is also closed.

## Clarifications resolved (intake)

`function_length.py` (G1, TICKET-0027 R1) is a baselined check: `MAX_LINES = 80`,
and a function over 80 lines passes only if it is recorded in
`tooling/verify/baselines/function_length.json`. That transition baseline was
retired on purpose at BRIEF-0028-f (2026-07-16); a missing/empty baseline means
zero tolerance. `write_location_doors` landed at 99 physical lines via
BRIEF-0034-a on 2026-07-20 -- after the retirement -- so it was born over the
ceiling. TICKET-0037 runs the first full `verify` since, and the check scans all
of `src/`; it cannot be scoped to one ticket. The check is doing exactly its
job. This is the same class of situation TICKET-0035 already arbitrated (an
over-budget unit, no baseline, surfaced by an adjacent pipeline), and its
resolution is the precedent here.

Options considered and rejected during intake:
- **Re-add a `function_length.json` baseline entry** -- rejected: reverses the
  R1/R5 baseline retirement taken at TICKET-0028's close. This is the exact
  refusal TICKET-0035 recorded for the sibling `module_budget` case; a surfaced
  door defect is not the occasion to reopen it.
- **Shorten `write_location_doors`' docstring / move the NO-GEOMETRY rationale
  out to fit under 80 (option B2)** -- rejected: that comment is load-bearing at
  the write site (it tells a future editor why there is no write-time geometry
  check, and points to the read-time fallback in `spatial_doors.py`). Trimming
  to fit the ceiling is the check-dodge the standards warn against; the note
  stays with the writer.
- **Fold the fix into TICKET-0037** -- rejected: 0037's work does not touch
  doors. Attributing a door-write refactor to it pollutes append-only history;
  this mirrors the `blast_radius` argument TICKET-0035 used to refuse folding
  the extraction into TICKET-0034.
- **Reopen TICKET-0034** -- rejected: 0034 is merged and closed. Append-only
  discipline does not reopen a closed ticket for a defect surfaced later; a
  fresh remediation ticket owns it, exactly as TICKET-0035 (a dedicated ticket)
  owned the sibling budget escalation.

Resolution: a dedicated remediation ticket (this one). BRIEF-0038-a extracts the
per-item validation loop of `write_location_doors` into a private, read-only
helper `_validate_doors_payload` in the same module (option B1). Both the writer
and the helper then land under 80 lines by construction. The split, not an
exemption, clears the ceiling. Intra-module extraction: no new module, no import
edge, no canon-write site added or moved (`write_location_doors` stays the sole
writer; the delete-then-insert stays in it).

**Execution order (recorded here):** TICKET-0038 (this ticket) -> then close
TICKET-0037. The `verify` gate scans all of `src/`, so TICKET-0037 cannot reach
8/8 while `write_location_doors` is at 99. Land 0038, rebase `ticket/0037` onto
`main`, and 0037 goes 8/8 with no further discussion. Same shape as
"0035 before 0034-c", transposed to a post-merge surfacing.

**Root-cause note (process, to close at verify).** Under the same baseline-
retired regime, `module_budget` escalated `play_stream.py` during the TICKET-0034
pipeline, but `function_length` let `write_location_doors@99` land via
BRIEF-0034-a without blocking the merge. Why did that check not fail-closed on
the 0034 merge? Confirm at close and record in ARCHITECTURE_DECISIONS, so the
evasion class does not repeat.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `function_length.py` green on `src/world_engine/writes/config.py` --
      `write_location_doors` and the new `_validate_doors_payload` each <= 80
      physical lines
      -> verify/checks/function_length.py
- [ ] Full verify suite green with NO baseline file re-added and NO entry added
      to any baseline -- the extraction, not an exemption, is what clears the
      ceiling
      -> verify/checks/function_length.py
- [ ] `single_canon_write.py` green with ZERO change to `canon_write_policy.txt`
      -- this ticket adds no canon-write site and moves none;
      `write_location_doors` stays the writer, `_validate_doors_payload` only
      reads
      -> verify/checks/single_canon_write.py
- [ ] `module_budget.py` green on `writes/config.py` -- the +1 def / +1 helper
      stays well under 1000 lines / 40 defs
      -> verify/checks/module_budget.py
- [ ] `undefined_names.py` (R8 / pyflakes F821) clean on `writes/config.py` --
      no undefined name and no unused import introduced (the helper is
      intra-module; no import block changes)
      -> verify/checks/undefined_names.py

### Live  ->  human gate (Nia)

- [ ] A live door-authoring action writes/replaces `door` rows exactly as
      before: authoring a door to a valid, actively `connects_to`-linked target
      inserts the row; a target with no active `connects_to` edge is still
      rejected with the same `ValueError`. Byte-for-byte the same behavior as
      before the split.
- [ ] `git diff` is extraction-only: the validation loop moved verbatim into
      `_validate_doors_payload`, `write_location_doors` calls it; no validation
      logic changed, and the `DELETE` + insert + `return` and the docstring are
      untouched.
- [ ] `ticket/0037` rebased onto `main` post-0038 reports its verify at 8/8 --
      the `write_location_doors` `function_length` failure is gone.
