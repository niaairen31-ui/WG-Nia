# AMENDMENT 1 — BRIEF-0061-a

Appended, not a rewrite. Nothing above this line in `BRIEF-0061-a` is edited.
Commits 1, 2 and 3 stand as written. This amendment adds **commit 4** and two
Scope OUT entries.

## Why

Claude Code escalated on item 3.1 and was right to. `TICKET-0061` was
authored with `## Done means` — the *brief* template's section name — instead
of `## Acceptance criteria` + `### Machine-checkable  ->  G1 deterministic
gate`. `run.py`'s `machine_checks()` turns `in_machine` on only at a line
starting `### machine`, so the ticket would have parsed to zero arrows and
`run.py` would have fail-closed on it. A corrected acceptance-criteria
section is deposited separately.

The authoring error is isolated — measured, **62 of 63** tickets parse
correctly. What is *not* isolated is that nothing catches this shape of
defect at deposit time. `pipeline_state.py` validates front-matter only:
required fields, the status enum, `retry_count`, and the QUESTION file for
`escalated`. It validates **zero section structure** (grep: no occurrence of
`Machine`, `Acceptance` or `###`). A malformed ticket is invisible until
`run.py` is invoked on it, which is after execution has already started.

That matters more since C1. A standing law reading "every ticket links
`corpus_gate.py`" is unenforceable on a ticket whose section does not parse,
and its only symptom is a red `run.py` mid-execution — exactly what happened
here, by hand, on the ticket that introduces the law.

Decision **E1**.

## Scope IN — commit 4

### 4.1 — A section-shape rule in `pipeline_state.py`

New rule, named in its own failure messages, over every
`tooling/tickets/TICKET-*.md` (`TEMPLATE.md` is already excluded by the
module's glob — do not add a second exclusion):

1. **Exactly one** line whose stripped, lowercased form starts with
   `### machine`. Zero is a FAILURE. More than one is a FAILURE: the section
   boundary becomes ambiguous.
2. **Exactly one** line starting `### live`. Zero is a FAILURE **and the
   message must say why** — without a terminator, `in_machine` never turns
   off and arrows are collected from the entire remainder of the file.
3. The `### live` line appears **after** the `### machine` line. Reversed,
   the parser yields garbage.
4. **If `status` is one of `brief`, `exec`, `verify`, `live-gate`, `done`:**
   `machine_checks()` yields at least one arrow, and every arrow resolves to
   an existing file under `tooling/verify/checks/`. Statuses `intake`,
   `recon`, `paused` and `escalated` are exempt from the arrow floor — a
   ticket that has not been briefed has no criteria yet, and forcing a
   placeholder arrow would be a lie the check then blesses. The **headers**
   are required at every status; only the floor is conditional.
5. **Vacuous-proof:** zero `TICKET-*.md` files collected is a FAILURE.

**Reuse `run.py`'s parser; do not reimplement it.** The whole value of this
rule is that it asserts what `run.py` will actually do. A second copy of
`machine_checks()` or of `LINK` would drift, and two implementations of one
rule is the divergence this project's doctrine exists to prevent. Import it:

```python
sys.path.insert(0, str(ROOT / "tooling" / "verify"))
import run  # noqa: E402 -- reuse run.py's machine_checks/LINK, never a second copy
```

Verified importable: `run.py` builds its `ArgumentParser` inside `main()` and
guards on `__name__`, so importing it is side-effect free. This mirrors
`stylesheet_partition.py`'s existing sibling import of `legacy_mount`.

Amend `pipeline_state.py`'s docstring to name the new rule and state that its
parser is borrowed from `run.py` by design. Append; do not rewrite.

### 4.2 — Repair the one ticket that fails it

Measured: `tooling/tickets/TICKET-0001-doc-partition.md` (status `done`) has
`### Machine-checkable` at `:73` and **no `### Live` section at all** — the
file ends at `:76`. Its two arrows (`schema_partition.py`,
`decisions_index.py`) both resolve, so the only defect is the missing
terminator.

Append a `### Live  ->  human gate (Nia)` section at the end of the file with
one explicit criterion recording that this ticket had no live gate — a
tooling/doc partition with nothing for a human to play-test. Do not invent a
retroactive criterion, and do not edit a single character above it. It is a
`done` ticket; its body is history.

Confirm on the live tree that it is still the only failure before writing
anything. If a second ticket fails, STOP and report — a second instance means
the defect is a pattern, not an artifact, and the repair is a different
conversation.

### 4.3 — Red-tests, recorded in commit 4's message

1. Delete the `### Live` header from any ticket → FAIL naming the terminator
   consequence. Revert.
2. Add a second `### Machine-checkable` header to any ticket → FAIL naming
   the ambiguity. Revert.
3. Point an arrow in a `live-gate` ticket at `verify/checks/nonexistent.py`
   → FAIL naming the unresolved path. Revert.
4. Set a `paused` ticket's status to `exec` while it has zero arrows → FAIL
   on the floor; set it back → PASS. (This is what proves the conditional
   floor is real rather than decorative. If no `paused` ticket is on the
   tree yet, use a temporary copy and delete it.)

## Scope OUT — additions

- **E2 — asserting that `corpus_gate.py` is among each ticket's arrows.**
  Named deferral. It would make C1 structural rather than textual, but it
  turns all 62 existing tickets red at once, so it needs either a
  shrink-style baseline or a "tickets created after TICKET-0061" clause —
  neither of which belongs in a seal ticket. **Reactivation condition:** the
  first ticket authored after TICKET-0061 merges, at which point the
  post-cutoff clause has exactly one member and the baseline is trivial.
- **Restructuring any other ticket's sections.** 4.2 repairs one measured
  defect, by appending. No ticket's existing text is touched, no criteria are
  reclassified, no `## Done means` heading elsewhere is renamed.
- **`run.py` itself.** Commit 4 imports it. It does not modify it. Its
  fail-closed branch at `:44` is correct as written and is the behaviour this
  rule front-loads.

## Done means — additions

- [ ] `python tooling/verify/checks/pipeline_state.py` exits 0 across all
      63 tickets.
- [ ] `TICKET-0001-doc-partition.md` carries an appended
      `### Live  ->  human gate (Nia)` section; everything above it is
      byte-identical to before.
- [ ] `pipeline_state.py` imports `run.machine_checks` — `grep -c "def machine_checks" tooling/verify/checks/pipeline_state.py`
      returns 0.
- [ ] All four red-tests recorded in commit 4's message and reverted.
- [ ] `python tooling/verify/run.py --ticket TICKET-0061-legacy-decommission-and-doctrine-seal`
      collects `corpus_gate.py` among its checks (this is item 3.1's amended
      form; it runs after the corrected acceptance section lands).
- [ ] `python tooling/verify/checks/corpus_gate.py` exits **0**.
- [ ] Four commits on `ticket/0061`, each green on its own.

## Docs to update — unchanged

Still nothing in `ARCHITECTURE_DECISIONS.md` here. The whole TICKET-0061
entry is written once, in brief -c. Brief -c's supplement gains one item:
E1, the section-shape rule, why `pipeline_state.py` borrows `run.py`'s
parser rather than copying it, and E2's deferral with its reactivation
condition.
