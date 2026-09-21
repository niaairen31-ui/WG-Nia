# AMENDMENT-0087-3 — "Closing repairs before BRIEF-0087-e"

Amends: TICKET-0087-knowledge-subject-participants.md, LOT-0087-knowledge-subject-participants.md, BRIEF-0087-e
Raised by: the TICKET-0088 decision RECON (S-1, S-2, S-3), and the RECON of 2026-09-21 against `main` at `2ae232b` (O-1, O-2 and three defects of BRIEF-0087-e)
Decided by: Nia — `G1` (2026-09-16), deposit clause amended by `H1` (2026-09-17); `L1`, `M1`, `N1`, `P1` (2026-09-21)
Status: applied to the ticket, the lot header and BRIEF-0087-e; deposited on `ticket/0087`, fast-forwarded to `main`, as the first commit of BRIEF-0087-e

## What deviated

Nothing had executed since BRIEF-0087-d. Five things were wrong with what was
about to execute.

1. **The ticket's gate ran six checks, not nine (S-1).** `run.py` keeps only the first arrow of a Machine line, so `function_length.py`, sharing a line with `module_budget.py`, never ran; `corpus_gate.py` was not linked, contrary to `CLAUDE.md:83-84`. The recorded verdict of 2026-09-15 lists exactly six checks (R-22).
2. **BRIEF-0087-e's done-means named a command that does not exist.** `python tooling/run.py`; the runner is `tooling/verify/run.py`, it takes the full slug, and it runs only the checks the ticket links (R-22).
3. **The coverage row could be truncated away.** C-04 put `coverage` last; `execute_plan` truncates a selector's list from the tail at `row_cap` (`lore_query.py:180-181`). From 200 knowers on, the row C-04 calls "exactly one, always" was cut, and the case table's `N > 200` line was unreachable (R-13).
4. **Item 10 of BRIEF-0087-e left a design choice to the executor**: derive `SELECTOR_FUNCTION_NAMES` "if it can". Measured instead: with the literal, a direct reference to the new selector in `lore_query.py` passes R2; with the names read from `SelectorSpec(fn=...)`, it fails (R-27).
5. **BRIEF-0087-e could not start the way its ticket expects.** `ticket/0087` is merged, so `/pipeline TICKET-0087` derives `done` and stops; with commits and no open PR, it would replay briefs a to d (R-21, open point O-1). Several anchors had also moved or pointed at docstrings (R-28, open point O-2).

Two routes gaps found by the TICKET-0088 RECON are recorded, not repaired:
the participant attach route does not read before it writes (S-2) and does
not check the entity's world (S-3). Both are unreachable from the two UI
callers (R-26).

## Decisions

- **G1** — repair the Machine section, regenerate BRIEF-0087-e's done-means, record S-2 and S-3 as named deferrals in LOT-0087. *Rejected:* G2, also fixing the attach route — reactivate when the S-3 query returns more than 0; G3, doing nothing. **H1** moved the deposit to the branch `e` runs from, before `e`.
- **L1** — `e` runs on `ticket/0087` fast-forwarded to `origin/main`, through `/brief-exec` alone; the PR is opened with `/pipeline` Step 3's own commands, `live-gate` in the same way TICKET-0088 did. *Rejected:* L2, a new branch name — it breaks `/brief-exec` step 1 and `/pipeline`'s `--head ticket/NNNN`; L3, deleting and recreating `ticket/0087` — the same end state with a destructive step; L4, carrying `e` in a new ticket — contrary to E2 and K3, and TICKET-0087 could never close.
- **M1** — `coverage` is the first row, on the precedent of `entity_dossier`'s `identity`; `execute_plan` untouched. *Rejected:* M2, sparing context rows in `execute_plan` — reactivate when a selector must emit a context row after its content rows; M3, leaving the row last.
- **N1** — R2 of `checks/lore_selectors.py` reads its names from the `fn=` keyword of every `SelectorSpec(...)`, vacuity-guarded, in its own commit. *Rejected:* N2, adding the name to the literal — the next selector meets the same trap; the corpus-wide sweep stays TICKET-0085 queue item 7.
- **P1** — no prompt change. The secret marker is guaranteed in the formatted line, the template fallback and the trace; whether the model's prose keeps it is reported. *Rejected:* P2, a new `lore_rows_to_prose` prompt version — reactivate when a live answer is seen to drop the marker.

## Edits applied

**TICKET-0087.** The `### Machine-checkable` section is replaced: fifteen
lines, one arrow each, over twelve distinct checks — `fact_spine`,
`subject_resolution` (x3), `lore_selectors` (x2), `lore_isolation`,
`single_canon_write`, `import_cycle`, `undefined_names`, `module_budget`,
`function_length`, `decisions_index`, `pipeline_state`, `corpus_gate`. Two
criteria are restated to what their check proves: "every writer of
`fact_participant` reads before it writes" becomes "`write_knowledge` reads
before it attaches" (`subject_resolution.py` A4 exercises `write_knowledge`,
not the route, R-26); "`SELECTOR_FUNCTION_NAMES` names all three selectors"
becomes "no selector function is named in `lore_query.py`, the names being read
from every `SelectorSpec(fn=...)`" (N1). `run.py`'s parser on the repaired
section returns the twelve checks; `pipeline_state.py` passes. An
`## Amendment log` table is appended, listing the three amendments. Front
matter, request, clarifications and Live section are unchanged.

**LOT-0087.**
- Dependency graph: a note that TICKET-0088 is merged and where `e` starts.
- Brief list, entry `e`: a note that the check learns the name by derivation.
- **R-12** corrected in place (`:38`, not `:37`; the literal is removed under N1), with a line naming this amendment.
- **R-13** extended (tail truncation spares no context row), with a line naming this amendment.
- **R-21 to R-28** added: the base and the branch; what `run.py` runs; render order; silent-canon prose; the planner and the prompts; the attach route and its callers; the prototype; the re-measured anchors.
- **C-04** amended: `coverage` first; the knowers join without `Fact`; `uncounted_rows` defined as an outer join equal to C-06's `row_count` sum; the ladder anchor `:64-74`.
- **C-05**: a note that dict order is documentation only.
- Gate output: (a) re-run as a property trace against declaring files; (b) the `who_knows_about` case table re-walked; (c) three enumerations pasted; (e) the `lore_selectors` entry superseded, and `import_cycle`, `decisions_index`, `pipeline_state`, `corpus_gate` named with their satisfying modules.
- **Named deferrals** section added: `D-0087-attach-duplicate` and `D-0087-attach-cross-world`, with grep- and SQL-verifiable reactivation conditions.
- Amendments section: this entry appended.

**BRIEF-0087-e** regenerated in full: anchors from R-28; facts carried and
contracts re-copied from the header; Scope IN now opens with the fast-forward
start and closes with the PR (L1), makes the R2 derivation a mandatory first
commit (N1), gives every code edit verbatim as run in R-27, rewrites the
section-contract comment of `lore_render.py` from the code, and drops the
`CLAUDE.md` edit (the "TICKET-0070 rule" does not exist); Scope OUT names the
prompts, `execute_plan`, `frontend/src/lore/` and the attach route; done-means
run `python -m tooling.verify.run --ticket TICKET-0087-knowledge-subject-participants`,
two named mutations and a fixture probe kept outside the repository.

BRIEF-0087-a to -d: untouched, executed and merged.

## Gate checks re-run

- **(a)** re-run as a property trace; three presuppositions removed rather than traced (the TICKET-0070 rule, the "existing style" of descriptions, an unnamed R1).
- **(b)** the `who_knows_about` case table re-walked; every row run on a fixture, N = 206 included.
- **(c)** `run.py`'s parse of the old section, the grep of participant-route callers, and the corpus lines before and after, pasted.
- **(d)** C-04 re-read after the change; both sections still carry `section` and a formatter.
- **(e)** every gate the brief must pass names its satisfying module; the corpus measured 111 of 111 with the brief's edits on a copy of `2ae232b`.
