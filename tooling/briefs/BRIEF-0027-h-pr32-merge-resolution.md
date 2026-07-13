<!-- slug: pr32-merge-resolution -->
# BRIEF-0027-h — Resolve PR #32 merge conflict; encode generated-file merge rule

Ticket: TICKET-0027 | Danger: none (merge housekeeping + one CLAUDE.md
rule; no `src/` logic change) | Blast radius: small

## Context

PR #32 (`ticket/0027` -> `main`) cannot merge: `main` advanced with
TICKET-0026 (PR #31) after the branch was cut. Diagnosis (verified by
reproducing the merge on a clone, 2026-07-13):

- `ARCHITECTURE_DECISIONS.md` auto-merges cleanly: `main` edited ~10 lines
  inside an existing record (0026 canon-classify amendment, no new `## `
  record), the branch appended 2 records (86 = 84 + 2, header-diff proven).
- `CLAUDE.md` and `src/world_engine/cockpit/app.py` auto-merge cleanly:
  the 0026-b `commit_region` dead-block removal and the 0027-b `say`
  extraction touch disjoint regions (line-level verified).
- The ONLY conflict is `tooling/standards/DECISIONS_INDEX.md`. It is a
  GENERATED file encoding line numbers into the archive; `main`'s 10-line
  edit shifted every line number (+10), so every table row diverges.

The resolution is mechanical: merge, then regenerate the index from the
merged archive with the sanctioned generator. Never hand-edit this file
(its own header says so; `decisions_index.py` fails any index that does
not match a regeneration byte-for-byte).

## Scope IN

1. **Resolve the merge on `ticket/0027`:**
   - `git fetch origin`
   - `git merge origin/main` (expect exactly one conflict:
     `tooling/standards/DECISIONS_INDEX.md`; any other conflicting file is
     an ESCALATION — stop and report, do not improvise)
   - `python tooling/glue/gen_decisions_index.py`
   - `git add tooling/standards/DECISIONS_INDEX.md`
   - `git commit` (default merge message)
   - Run the ticket verify:
     `python tooling/verify/run.py --ticket TICKET-0027-code-standards-seeding-and-remediation`
     -> all PASS required. Also run standalone:
     `python tooling/verify/checks/decisions_index.py` and
     `python tooling/verify/checks/claude_md_contract.py` -> PASS.
   - `git push origin ticket/0027` (PR #32 becomes mergeable; do NOT merge
     the PR — Nia accepts it after her live gate).

2. **Encode the standing rule in `CLAUDE.md`** (keep
   `claude_md_contract.py` green — respect section whitelist and line
   budgets; place under the existing conventions/merge-adjacent section):

   > Generated files are never hand-resolved in a merge conflict:
   > regenerate from source and stage the result. Known instance:
   > `tooling/standards/DECISIONS_INDEX.md` ->
   > `python tooling/glue/gen_decisions_index.py`. Any merge conflict
   > outside the expected set for the branch is an escalation, not an
   > improvisation.

   Wording may be compacted to fit the line budget; the three elements
   (never hand-resolve generated files, the named instance + command, the
   escalation clause) must all survive.

## Scope OUT

- Merging PR #32 itself (Nia's action, after her live gate).
- Any change to `tooling/verify/` — the structural gate
  (`decisions_index.py`) already covers the outcome; no new check.
- Any rebase or history rewrite of `ticket/0027`.
- Any `src/` change beyond what the merge itself produces.

## Invariants to defend

- `ARCHITECTURE_DECISIONS.md` stays append-only: the merged archive must
  contain both `main`'s 0026 in-record amendment and the branch's two 0027
  records; 86 `## ` records total.
- `DECISIONS_INDEX.md` is committed only as generator output.
- No conflict resolution outside `DECISIONS_INDEX.md` occurs; anything
  else halts the brief with a report.

## Done means

### Machine-checkable
- [ ] Merge commit on `ticket/0027` contains `origin/main`; the only
      manually staged conflict file is `DECISIONS_INDEX.md`, produced by
      `gen_decisions_index.py` (86 records).
- [ ] `run.py --ticket TICKET-0027-...` all PASS on the merged branch;
      `decisions_index.py` and `claude_md_contract.py` PASS standalone.
- [ ] `grep "def say" src/world_engine/cockpit/app.py` -> 1 thin
      orchestrator; `play.py`, `play_stream.py`, `play_physical.py`
      present; `commit_region` contains no reintroduced 0026-b dead block.
- [ ] CLAUDE.md contains the generated-file merge rule;
      `claude_md_contract.py` PASS.

### Live gate (Nia)
- [ ] PR #32 shows "no conflicts"; one live `/say` round-trip on the
      merged branch behaves identically (app.py now combines 0026-b and
      0027-b — this is the case the live gate exists for); then accept
      the PR.

## Docs to update

- `CLAUDE.md` only (Scope IN 2). No schema docs, no decision record — this
  is procedure, not architecture; the doctrine lives in the rule itself.
