<!-- slug: ticket-close-residual-freeze -->
# BRIEF-0027-g — Close TICKET-0027: residual freeze under successor ticket (I2)

Ticket: TICKET-0027 | Danger: none (baselines, docs, housekeeping) |
Blast radius: small | Depends on: BRIEF-0027-f merged; own branch
`ticket/0027-g`

## Context

Decision I2 (locked by Nia): stages a-f do not bring the whole codebase
under R1/R5 — ~25 `function_length.json` entries (in `tick.py`,
`context.py`, `analyzer.py`, plus handlers moved intact by stage d) and
the `tick.py` / `models.py` `module_budget.json` entries are untouched by
this ticket's scope. Rather than extending 0027 (I1) or relaxing caps
(I3), the residual is FROZEN — shrink-only, owned by successor ticket
TICKET-0028 (residual decomposition; ID to be confirmed by Nia at
deposit), deleted at that ticket's close. This is a bounded transition
with a named owner, not grandfathering. Original stage-g wording
("baselines deleted here") is amended accordingly.

## Scope IN

1. **Baseline audit.** Regenerate both baselines' expected state and
   assert it: every entry belonging to a file/function touched by stages
   b-f is GONE (`say`, `_stream`, `_apply_mutation`, `app.py` and
   `crud.py` module entries, `entity_author.py` if it reached
   compliance); what remains is exactly the residual set. Enumerate the
   residual in the execution notes with `file:qualname:lines`.

2. **Header rewrite, both baseline files:** replace "deleted at
   TICKET-0027 stage g" with "residual owned by TICKET-0028; entries
   shrink-only; file deleted at TICKET-0028 close."

3. **Amend `code_standards.md`** (verbatim edits, Nia pre-approved via
   I2):
   - R1: "...deleted at the close of the remediation ticket (section 4,
     stage g)" -> "...reduced at TICKET-0027 stage g to a frozen residual
     owned by TICKET-0028, and deleted at TICKET-0028's close".
   - R5: same substitution for `module_budget.json`.
   - Section 4 stage g: rewrite to describe the residual freeze +
     successor handoff (this brief).

4. **Decision record.** Append the I2 decision to
   `ARCHITECTURE_DECISIONS.md` (residual freeze, successor ownership,
   rationale: bounded transition vs. ticket sprawl); regenerate
   `DECISIONS_INDEX.md` via `gen_decisions_index.py`.

5. **Harness ownership transfer.** `scripts/harness_say_replay.py` and
   `scripts/harness_mutation_apply.py` (+ fixtures) are NOT deleted:
   TICKET-0028's decompositions (`run_world_tick` 421,
   `assemble_npc_context` 267, `analyze_overhearing` 260) need the same
   record/replay proofs. Re-scope their deletion to TICKET-0028 close;
   note this in each script's header docstring.

6. **Ticket close checklist.** Walk TICKET-0027's Acceptance criteria;
   every machine-checkable box verified on `main` post-merge; ticket
   front-matter -> `status: done` (after Nia's live gate);
   `schema_version_touched` stays empty (whole ticket shipped without a
   schema change — confirm).

## Scope OUT

- Any decomposition of residual entries (that is TICKET-0028's entire
  point).
- Creating TICKET-0028 itself (Nia opens it; this brief only names the
  handoff).
- Any `src/` change whatsoever.

## Invariants to defend

- Residual entries shrink-only remains machine-enforced (checks already
  do this; the freeze changes ownership and wording, not mechanics).
- `code_standards.md` section 4 matches shipped reality exactly (the
  ticket's own live criterion).
- Append-only decision archive; index regenerated, never edited.

## Done means

### Machine-checkable
- [ ] Both baselines contain exactly the enumerated residual; all
      stage-b-f entries absent; `function_length.py` and
      `module_budget.py` green.
- [ ] `decisions_index.py` green after the I2 record append;
      `claude_md_contract.py` green (CLAUDE.md untouched or within
      budget).
- [ ] Full verify suite green on the branch.
- [ ] Harness scripts present with updated ownership docstrings.

### Live gate (Nia)
- [ ] Read the amended `code_standards.md` section 4 against what
      shipped: match confirmed.
- [ ] Merge, mark TICKET-0027 `done`, open TICKET-0028 with the residual
      enumeration from this brief's execution notes as its intake.

## Docs to update

- `code_standards.md` (Scope IN 3), `ARCHITECTURE_DECISIONS.md` +
  `DECISIONS_INDEX.md` (Scope IN 4), baseline headers (Scope IN 2),
  harness docstrings (Scope IN 5).
