# BRIEF — Step "corpus gate — every check runs, or the gate is red"

## Context

`tooling/verify/run.py` parses a ticket's `### Machine-checkable` section and
executes only the checks its `-> verify/checks/NAME.py` arrows name. That is
correct as a per-ticket gate and insufficient as a corpus guarantee: a check
no ticket references is never executed, and its failure is invisible.

This is not hypothetical. `observation_surface.py` was red on `main` from the
moment TICKET-0059 merged until `BRIEF-0060-a` repaired it. TICKET-0059's
Machine section links eleven checks and does not link that one. Nothing was
wrong with the gate; the gate simply had nothing to say about a file outside
its ticket's arrow set.

The workstream's cross-cutting rule — *fail-closed guards never lapse* — is
therefore unverifiable by construction today. Decision **B1** closes that:
one check that discovers and executes every sibling check, fails closed on a
check that cannot even be imported, and proves it covered the directory rather
than a subset of it.

A second, measured motivation: RECON-0060-a ran in a stdlib-only container
where `fastapi` and `sqlalchemy` were absent. Four checks could not be
evaluated at all, and `observation_surface.py`'s Rule 5 reported a subprocess
failure that looked exactly like a real failure. A corpus gate without an
explicit environment contract would either drown in that noise or, worse,
learn to swallow it — which is fail-open.

## Mini-RECON — verify before writing

Report `file:line` or a count for each. **If any anchor does not resolve as
described, STOP and escalate — do not adapt.**

1. `tooling/verify/run.py` — report the line ranges of `machine_checks()`, the
   `LINK` regex, the zero-criteria fail-closed branch, and the subprocess
   invocation. Confirm the verdict JSON shape written to
   `tooling/verify/results/`.
2. `tooling/verify/checks/` — report the exact count of `*.py` files and
   whether any is not a runnable check (a shared helper, an `__init__.py`, a
   fixture).
3. Run every check individually with `WORLD_ENGINE_ENV=dev PYTHONPATH=src` and
   report a three-column table: name, exit code, and first PASS/FAIL/Traceback
   line. **This table is a deliverable of the mini-RECON**, not a step toward
   fixing anything.
4. From that table, classify every non-zero exit into exactly one of:
   *genuine failure*, *unimportable (missing dependency)*, *requires a live
   DB*, *requires an environment variable*. Report the classification.
5. Report the wall-clock duration of the slowest check.
6. Confirm no check currently invokes another check as a subprocess except
   `observation_surface.py` Rule 5 (`json_ui_boundary.py`) — report any others
   found, since they will be executed twice under the gate.

## Scope IN

Two commits.

### Commit 1 — `tooling/verify/checks/corpus_gate.py`

A new check, following the same `FAILURES` / `fail()` / `main()` idiom as
`legacy_mount.py` and `observation_surface.py`. Stdlib only.

**Discovery.** Glob `tooling/verify/checks/*.py`. Exclude exactly one file —
this module itself, matched by resolved path, not by name string. Assert the
exclusion removed exactly one entry; zero or more than one is a FAIL.

Exclude nothing else. If mini-RECON item 2 found a non-check file in the
directory, that is a REPORT ONLY finding and an argument for moving it, not a
reason to add a second exclusion here — an exclusion list is the seam through
which a check quietly stops being run, which is the entire failure this gate
exists to prevent.

**Execution.** Run each discovered check as a subprocess with the current
interpreter, inheriting the environment, with a per-check timeout. Set the
timeout to at least four times the slowest duration reported in mini-RECON
item 5, and name the measured figure in a comment beside the constant. A
timeout is a FAIL, never a skip.

**Coverage proof.** After the run, assert that the set of executed paths
equals `sorted(CHECKS.glob("*.py"))` minus this module. This is the property
the gate exists to establish: not *some checks passed* but *every check in the
directory was executed*. A directory listing that outran the executed set is a
FAIL naming the missed files.

**Environment contract.** Classify each non-zero exit before reporting it:

- stderr containing `ModuleNotFoundError` or `ImportError` →
  `ENVIRONMENT: <check> could not be imported (<module>)`
- a timeout → `TIMEOUT: <check> exceeded <n>s`
- anything else → `FAIL: <check> — <last stdout/stderr line>`

**All three are failures.** The classification exists so a reader can tell an
unmet environment prerequisite from a broken invariant, never so one of them
can be tolerated. Add this comment verbatim above the classifier:

```python
# TICKET-0060 (BRIEF-0060-d, B1). Three verdicts, one outcome: red.
# The classification is for the READER, never for the gate. A check that
# cannot be imported has not passed -- it has not run, which is strictly
# worse, because a skip looks like silence and silence looks like green.
# RECON-0060-a measured this exactly: in a container without fastapi and
# sqlalchemy, four checks could not be evaluated and one reported a
# subprocess failure indistinguishable from a real one. Any future edit
# that turns ENVIRONMENT into a warning re-opens the hole this gate was
# built to close.
```

**Vacuity guards.**

- Fewer than two checks discovered → FAIL.
- The checks directory missing or not a directory → FAIL.
- The self-exclusion removing anything other than exactly one file → FAIL.
- Zero checks executed → FAIL.

**Output.** On success, one PASS line naming the number of checks discovered,
executed and passed. On failure, one line per failing check, classified, then
a summary. Write nothing to `tooling/verify/results/` — verdict files belong
to `run.py`.

**Do not recurse.** `corpus_gate.py` never appears in its own executed set. The
self-exclusion assertion above is what proves it.

### Commit 2 — docs

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append to the TICKET-0060
  section. The content is the distinction itself — a per-ticket gate proves
  the checks a ticket names, a corpus gate proves the corpus; TICKET-0059's
  lapse is the worked example; and the reason `ENVIRONMENT` is a failure
  rather than a skip. Record explicitly that this is the *second* instance of
  the same shape in this ticket series: TICKET-0064's rule7 closed
  "non-duplication does not prove coverage" at the stylesheet level, and this
  closes the same gap one level up, at the gate level.
- `CLAUDE.md`: the check corpus is already named in the existing frontend and
  verification law. **The file is under an enforced line budget
  (`claude_md_contract.py`)** — add a clause to the sentence that already
  describes the verify corpus, stating that every check is executed by
  `corpus_gate.py` regardless of which ticket references it. Do not add a
  line. If no existing sentence can carry the clause within budget, STOP and
  escalate rather than exceeding the budget or dropping the doctrine.
- `CHANGELOG.md`: fold into the TICKET-0060 entry opened by `BRIEF-0060-b`;
  do not open a second entry for the same ticket.

### Red tests

Perform, capture the transcript, revert. No mutation is committed.

- **A broken check is caught.** Introduce a deliberate failure into a check
  no current ticket references. `corpus_gate.py` must FAIL naming it. Revert.
- **An unimportable check FAILS, not skips.** Insert `import
  definitely_not_a_module` at the top of a check. The gate must report
  `ENVIRONMENT` and exit non-zero. Revert.
- **Coverage is proven, not assumed.** Temporarily add a trivial always-green
  check to the directory and confirm the executed count rises by one and the
  coverage assertion passes; then make the discovery glob artificially miss
  it and confirm the coverage assertion FAILS naming the missed file. Revert
  both.
- **Self-exclusion is exactly one.** Temporarily add a second exclusion and
  confirm the assertion FAILS. Revert.
- **No recursion.** Confirm the executed set does not contain
  `corpus_gate.py`, and that the gate terminates.

## Scope OUT

1. **Do not fix anything the gate finds.** Mini-RECON item 3 will very likely
   surface red checks unknown to this brief — RECON-0060-a could not evaluate
   `observation_socle.py`, `observation_runner.py`, `observation_metrics.py`,
   `json_ui_boundary.py` or the `schema_*` family. Every one of them is
   **REPORT ONLY**. Report the classified table, escalate, and stop. A brief
   that both builds a gate and repairs whatever the gate finds has no
   reviewable boundary.
2. **Do not modify any existing check** — not to make it pass, not to make it
   faster, not to make it importable. The single exception is the timeout
   constant inside `corpus_gate.py` itself.
3. **Do not modify `tooling/verify/run.py`.** No `--all` flag, no default
   corpus run, no change to `machine_checks()` or the verdict JSON shape. The
   gate is reachable the way every other check is: a ticket links it with an
   arrow. That is deliberate — a runner mode could not be named from a
   `### Machine-checkable` section, because `run.py`'s `LINK` regex only
   recognises `-> verify/checks/*.py`.
4. **Do not add an exclusion list.** One self-exclusion, asserted to be
   exactly one.
5. **Do not add a "this check is linked by some ticket" census.** That proves
   a reference, not a green, and it would let a linked-but-red check pass.
   Executing everything is strictly stronger and this brief builds only that.
6. **Do not introduce a baseline file.** Check counts grow; a shrink-only
   baseline is the wrong shape here, and the coverage assertion already
   proves the directory was covered without one.
7. **Do not parallelise.** Sequential execution, deterministic order. A
   flaky gate teaches people to re-run it.
8. **Do not touch `frontend/`, `src/`, or any product code.**

## Invariants to defend

- **Fail-closed over advisory.** Every ambiguous outcome resolves to red.
  A check that could not run has not passed.
- **Vacuous-proof guards.** Zero discovered, zero executed, or a
  self-exclusion of any size other than one, are failures rather than
  trivially satisfied comparisons.
- **Structural over disciplinary.** The gate makes "every guard is live" a
  property the machinery establishes, not a convention the ticket author is
  trusted to maintain by writing enough arrows.
- **Minimal first.** One check, one directory, one assertion about coverage.
  No scheduler, no tiers, no caching, no selective re-run.
- **No structure without a reader.** The `ENVIRONMENT` / `TIMEOUT` / `FAIL`
  classification has exactly one reader — the person reading the gate's
  output — and changes no control flow.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python tooling/verify/checks/corpus_gate.py`
      runs to completion and reports a count of discovered, executed and
      passed checks.
- [ ] The executed count equals the discovered count equals
      `len(glob("tooling/verify/checks/*.py")) - 1`.
- [ ] `corpus_gate.py` is absent from its own executed set.
- [ ] The mini-RECON's three-column table (name, exit code, first verdict
      line) and the item-4 classification are in the execution report.
- [ ] Every red the gate finds is listed, classified, and **left unfixed**,
      with an explicit escalation line naming what a follow-up ticket would
      need to cover.
- [ ] Five red-test transcripts are in the execution report, each showing the
      expected verdict, with every mutation reverted and `git status` clean.
- [ ] `git diff --stat` lists `corpus_gate.py` in commit 1, and only
      `ARCHITECTURE_DECISIONS.md`, `CLAUDE.md` and `CHANGELOG.md` in commit 2.
- [ ] `claude_md_contract.py` passes after the CLAUDE.md clause is added.
- [ ] The timeout constant names the measured slowest-check duration in a
      comment beside it.

## Docs to update

Covered by commit 2 above: `ARCHITECTURE_DECISIONS.md` (the per-ticket versus
corpus gate distinction, with TICKET-0059's lapse as the worked example and
the explicit link to TICKET-0064's rule7 as the same shape one level down),
`CLAUDE.md` (one clause, within budget), and the existing TICKET-0060
`CHANGELOG.md` entry.

No schema change.
