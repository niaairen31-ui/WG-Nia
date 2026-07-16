<!-- slug: baseline-retirement-and-closure -->
# BRIEF-0028-f — Baseline retirement, harness deletion, ticket closure

Ticket: TICKET-0028 | Danger: none — deletions of transition artifacts
whose emptiness stages b–e already proved | Blast radius: small |
Depends on: BRIEF-0028-e merged (`main` @ post-e, verify green, both
baselines empty)

## Context

Decision I2's death date. The transition baselines were frozen at
0027's close as a shrink-only residual owned by this ticket; stages a–e
emptied them. This brief deletes the artifacts, flips R1/R5 to
exemption-free operation, deletes the four disposable harnesses whose
ownership ends with the ticket, and performs the `code_standards.md`
closure edit.

Harness census at RECON (post-a `main`, re-verify at execution):
`scripts/harness_say_replay.py`, `scripts/harness_mutation_apply.py`,
`scripts/harness_tick_replay.py`,
`scripts/harness_entity_author_replay.py` — the fourth was created
during 0027 stage e and inherits the same disposal clause (transferred
ownership, deleted at 0028's close, same as the say/mutation pair per
the handover).

## Scope IN

1. **Baseline deletion.** Delete `baselines/function_length.json` and
   `baselines/module_budget.json`. Verify `function_length.py` and
   `module_budget.py` handle baseline ABSENCE as exemption-free
   operation (not as an error, not as a vacuous pass — the fail-closed
   doctrine applies: if either check currently errors on a missing
   baseline file, amend it to treat absence as the empty exemption set,
   with a recorded fail-closed proof: plant one over-cap function on a
   scratch branch, observe FAIL with no baseline present, revert).

2. **Harness deletion.** Delete the four harness scripts AND their
   fixture directories/manifests. Pre-deletion census: grep `src/`,
   `tooling/`, `CLAUDE.md`, and `scripts/` for references to the four
   filenames; zero references may survive (docs excepted where they are
   historical records: tickets, briefs, RECONs, ARCHITECTURE_DECISIONS
   are append-only history and keep their mentions).

3. **`code_standards.md` closure edit** (the one doctrine edit of the
   ticket): in R1 and R5, replace the transition-artifact sentences
   ("reduced at TICKET-0027 stage g to a frozen residual owned by
   TICKET-0028, and deleted at TICKET-0028's close, after which the
   check runs with no exemptions" — `code_standards.md:48-50`, `:91-93`)
   with past-tense closure ("transition baseline retired at
   TICKET-0028's close; the check runs with no exemptions"); same edit
   to the I2 paragraph (`code_standards.md:189-194`). Assertions and
   caps untouched — this is historical tense, not rule change. Bump the
   doc's version line per its own convention (v1 -> v1.01 unless the
   doc's header prescribes otherwise; follow the file, record the
   choice).

4. **Ticket bookkeeping.** `TICKET-0028` front-matter: append
   `BRIEF-0028-f`, set `status: live-gate`. The `live-gate -> done`
   flip rides the first commit of the NEXT ticket, mirroring the 0027
   precedent (G1 pattern) — note this in the ticket's Notes section.

5. **`ARCHITECTURE_DECISIONS.md`**: append-only entry recording I2's
   completion: residual emptied across stages a–e, baselines and
   harnesses deleted, R1/R5 exemption-free as of this brief's merge.

## Scope OUT

- Any code change in `src/` beyond zero (unless item 1's absence-
  handling amendment is needed — checks only, never `src/`).
- Any new check, any cap change, any advisory-rule promotion.
- The spatial / Play mode stream, Tier 4 propagation, Tier 3 C2,
  TICKET-0023 — next horizon, separate intake.

## Invariants to defend

- Fail-closed on absence: zero baselines must mean zero exemptions,
  proven, not assumed.
- History is sacred: tickets, briefs, RECONs, ARCHITECTURE_DECISIONS
  keep every historical mention of the deleted artifacts.
- Full suite green with both baselines gone.

## Done means

### Machine-checkable
- [ ] Both baseline files absent; `function_length.py` and
      `module_budget.py` green, exemption-free, with recorded
      fail-closed absence proof.
- [ ] Four harnesses + fixtures deleted; reference census clean.
- [ ] `code_standards.md` closure edit applied; `claude_md_contract.py`
      and `decisions_index.py` green (regenerate `DECISIONS_INDEX.md`
      from `gen_decisions_index.py` after the ARCHITECTURE_DECISIONS
      append — never hand-edit).
- [ ] Full suite (30 checks) green.

### Live gate (Nia)
- [ ] `python tooling/verify/run.py` end-to-end on her machine: green.
- [ ] One cockpit smoke pass (boot, world load, one `/say`) — closure
      confidence, not a behavior claim (nothing in `src/` changed).

## Docs to update

- `code_standards.md` (item 3), `ARCHITECTURE_DECISIONS.md` (item 5),
  `DECISIONS_INDEX.md` (regenerated), `TICKET-0028` (item 4).
