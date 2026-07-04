<!-- slug: claude-md-contract -->
# BRIEF-0010-a — Replace CLAUDE.md + ship its structural contract check

Ticket: TICKET-0010 · Schema: **none** · danger_class: []

## Context

CLAUDE.md grew to 1366 lines / 107 KB, 67% of it a brief-by-brief annotated
file tree duplicating `tooling/standards/ARCHITECTURE_DECISIONS.md` and the
schema changelog — a per-session ~25K-token tax and a staleness machine.
The replacement file (467 lines) was authored chat-side at content-constant
law: all 33 invariants preserved (rewritten law-only), stale paths
corrected (`verify/checks/` -> `tooling/verify/checks/`), the tree rebuilt
bare from the real repo, TICKET-0009's shipped facts integrated, and the
filename-is-law artifact convention recorded. The freshness rule was
disciplinary and failed; this brief makes it structural.

## Scope IN

### 1. Replace `CLAUDE.md`

Replace the repo-root `CLAUDE.md` with the delivered file, byte-for-byte
(it accompanies this brief in the same deposit). No editorial changes
during execution: wording issues found at review are escalated, not fixed
inline (the file is a locked design artifact of this ticket).

**Content-constancy review (required before commit).** Diff old vs new and
confirm every invariant survives. Checklist of the 33+2 laws that MUST
each be present in the new file (title-level check, not verbatim):
per-NPC gathering uniqueness; dissolve-before-create in caller;
relation_change window ownership; new_knowledge/status_change idempotency;
structural secret exclusion (incl. overhearing); relation_change ids from
payload; two canon-write paths; change_history on both paths; commit
before canon paths; MJ perception boundary; knowledge-level monotonicity;
scene_state ephemeral third path; engine proposals via review queue;
structural constraint gating; condition-ladder monotonicity; frozen scene
no-model; discoverable_detail exclusion + subculture["hidden"] trap;
connects_to topology-only; ledger append-only; resource_change SAVEPOINT
exception; price_list seller-only injection; read_public_memberships +
cover_role; commit-free creator cores; region commit atomic/
server-authoritative; PC knowledge is_secret=False + normalizer split; PC
co-presence exclusion by character_type; close_open_memberships on
location/status edits + roster gating; closed hard-delete list; custom
skill skill_definition_id filter; skill_definition delete semantics;
skill_definition backfill/rename/re-base semantics; base-domain name ban;
effective_model single resolver + PROMPT_REGISTRY entry rule; prompt-model
write path (PATCH, fail-closed, seed-NULL, env channel, no empty-list
masquerade); _npc_dialogue_system_prompt single construction.
Any law found in the old file and absent from the new one -> escalate
(D1-a), do not silently re-add.

### 2. `tooling/verify/checks/claude_md_contract.py`

Deterministic, stdlib-only, same harness conventions as the sibling
checks. Asserts, against repo-root `CLAUDE.md`:

- **Section whitelist, exact and ordered.** H2 set: `What this is`,
  `Stack`, `Working rules`, `Ticket pipeline (governance)`,
  `Numbering & decisions governance`,
  `Invariants (verified at every review)`, `Local model notes`,
  `Conventions`. H3 set under Conventions: `File structure`, `Naming`,
  `Schema fidelity rules`, `How to run / test`. Any missing, extra, or
  reordered heading fails.
- **Budgets.** Total file <= 500 lines; `### File structure` section
  (heading to next heading) <= 80 lines.
- **Archaeology ban, File structure section only.** Zero matches for
  `BRIEF-` or `schema v` or `v\d+\.\d+` within the section. (Governance
  sections legitimately reference `BRIEF-NNNN` forms; the ban is scoped.)
- **Pointer freshness.** Every `tooling/...` path mentioned anywhere in
  CLAUDE.md exists on disk (split on whitespace/backticks, test
  `Path.exists()`); a reference to a deleted/moved file fails the check.
  This is the structural "stays up to date" lever: rot becomes a red
  verify, not a discovery.

Wire it into `tooling/verify/run.py` the same way the existing checks are
discovered (if discovery is automatic by directory, no wiring needed —
confirm at execution).

### 3. `tooling/standards/ARCHITECTURE_DECISIONS.md` — one appended entry

Header form per governance:
`## CLAUDE.MD CONTRACT + ARTIFACT CONVENTION (BRIEF-0010-a, no schema change)`
Body records: (a) CLAUDE.md is law-only, budgeted, contract-checked by
`claude_md_contract.py`; history lives in this registry and the schema
changelog, never in CLAUDE.md; (b) artifact convention — the filename is
law: tickets/RECONs/briefs arrive with final real IDs in filename and
content, deposited manually by Nia; (c) the pipeline cockpit's deposit
flow is dormant (format too strict, docs not visible at deposit); the app
stays in-tree, unmaintained; reopening is a future ticket with these
friction facts as its intake.

Regenerate `DECISIONS_INDEX.md` via `tooling/glue/gen_decisions_index.py`
and refresh the decisions baseline if the harness requires it.

## Scope OUT (named deferrals)

- Any change to the *laws themselves* — this is a format/pointer/freshness
  chantier; behavior and doctrine are untouched.
- Any change to `ARCHITECTURE_DECISIONS.md` beyond the one appended entry.
- Automation of CLAUDE.md generation from source — no generator without a
  second concrete case of drift the contract check fails to catch.
- Repairing or removing the pipeline cockpit — dormancy is recorded, not
  acted on.
- Prose-truth verification of every CLAUDE.md sentence against code — the
  contract checks structure and pointers; semantic drift remains covered
  by `/review-step`'s invariant review.

## Invariants to defend

- **No law lost** (the checklist above is the gate; absence -> escalate).
- **Append-only registries:** the ADR entry is appended, never inserted;
  `DECISIONS_INDEX.md` is regenerated, never hand-edited.
- **No schema change; no version bump.**
- **`/verify` stays green end-to-end** — every pre-existing check must
  still pass against the new CLAUDE.md (some checks grep this file; if one
  greps for text the rewrite moved, escalate rather than weakening the
  check).

## Done-means checklist

### Machine-checkable -> G1
- [ ] `claude_md_contract.py` exists and is green (whitelist, budgets,
      scoped archaeology ban, pointer freshness)
- [ ] Full `/verify` green
- [ ] `DECISIONS_INDEX.md` regenerated; decisions-index check green

### Live -> human gate (Nia)
- [ ] Fresh Claude Code session, no other file open: it can state the
      per-NPC B1 invariant, the two canon-write paths, and how to run
      `/verify`
- [ ] `git show` of the CLAUDE.md diff: nothing but format, pointers, and
      the TICKET-0009 facts changed

## Docs to update

Covered by Scope IN item 3. CHANGELOG.md: one line, no schema change.
