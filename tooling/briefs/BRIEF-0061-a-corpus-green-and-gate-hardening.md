# BRIEF — Step "corpus back to green, and the gate that keeps it there"

Ticket: TICKET-0061 · Brief: BRIEF-0061-a · Branch: `ticket/0061`

## Context

TICKET-0067 returned `npc_goal_read.py` and `prompt_model_write.py` to green.
One failure remains on `main` — `pipeline_state.py` — and it belongs here by
decision B2.

TICKET-0067 also exposed a hole this brief closes. `prompt_model_write.py`
carried two independent defects; the first crashed the process before
`main()` reached its `if FAILURES` block, so the second was **invisible in
the corpus gate's own report**. That is not specific to one check: any check
in the corpus that raises an uncaught exception silently discards whatever
its earlier rules already appended to `FAILURES`. The gate reported "this
check failed" and could not report "and it holds another failure you cannot
see."

Three Scope IN items, one commit each. After the third, `corpus_gate.py`
exits 0 and this ticket's remaining two briefs can be gated on it.

---

## Mini-RECON — anchors measured on `main`, 2026-08-20, post-TICKET-0067

Tree-specific claims. **Verify each locally.** If any has drifted, STOP.

| Anchor | Measured |
|---|---|
| `corpus_gate.py` on `main` | exits 1 — exactly ONE failure, `pipeline_state.py` |
| `pipeline_state.py` failures | 3: `TICKET-0036-npc-link-agent.md`, `TICKET-0048-canon-faction-stratum-extraction.md`, `TICKET-0062-location-sheet-effect-cycle.md` |
| `pipeline_state.py:39-42` | `STATUS_ENUM`; the field must be a **literal** member — a trailing `# comment` breaks it |
| `corpus_gate.py:44` | `MODULE_RE`; `:81-91` `_classify`; `:113` `main`; `:123-126` the `subprocess.run` |
| `corpus_gate.py:85` | ENVIRONMENT is detected by `"ModuleNotFoundError" in combined or "ImportError" in combined` |
| Third-party imports across the corpus (AST scan) | `fastapi` (5 checks), `pyflakes` (1), `sqlalchemy` (5), `sqlmodel` (14); `httpx` is a runtime requirement of `fastapi.testclient` |
| The classification gap | A check that handles its own missing dependency gracefully emits a plain FAIL. Measured: with `httpx` and `pyflakes` absent, four such failures were reported as `0 environment … 6 other` |
| `stylesheet_partition.py:127` | `import legacy_mount` — a **sibling import** that depends on the checks directory being `sys.path[0]` |
| `TICKET-0069/-0070/-0071` | **not on `main`** as of this fetch |

### Hard STOP conditions

STOP and report; do not proceed, do not work around:

1. `corpus_gate.py` reports anything other than exactly one failure
   (`pipeline_state.py`) before this brief's first commit. A different
   baseline means the tree drifted after TICKET-0067.
2. `pipeline_state.py` reports a fourth ticket, or a failure that is not the
   `status:` enum. A different failure is a different defect.
3. The AST import scan finds a third-party module outside
   `{fastapi, httpx, pyflakes, sqlalchemy, sqlmodel}`. `REQUIRED_TOOLS` must
   be measured on the live tree, never copied from this brief.
4. Any check other than `stylesheet_partition.py` turns out to depend on
   `sys.path[0]` in a way the harness does not reproduce. Item 2 below is
   the whole reason the harness restores it; a second, different
   assumption means the harness shape is wrong.
5. Running the corpus under the harness changes ANY check's verdict other
   than by the intended reclassification. The harness must be
   behaviour-preserving.

---

## Scope IN

### Commit 1 — `pipeline_state.py` back to green (B2)

Three ticket front-matters carry an inline comment on their `status:` field.
The comment text is real history and must not be lost — move it, do not
delete it.

For each of `TICKET-0036-npc-link-agent.md`,
`TICKET-0048-canon-faction-stratum-extraction.md` and
`TICKET-0062-location-sheet-effect-cycle.md`:

- `status:` carries the bare enum value and nothing else.
- The comment text moves verbatim into the ticket **body**, appended as a
  short `## Status note` section at the end of the file. History is sacred:
  the note is appended, no existing body text is edited.

`TICKET-0048`'s comment is the enum list itself (a stray copy of
`TEMPLATE.md`'s own inline hint) and carries no history — that one is
deleted rather than relocated. Confirm this on the live tree before
deciding; if it turns out to carry substance, relocate it like the others.

Do not touch `TEMPLATE.md`'s own `status: intake        # intake|recon|...`
line — the check excludes it by glob, measured.

### Commit 2 — `corpus_gate.py`: the crash class and the recovered failures (C3, part 1)

This is the TICKET-0067 hole. A check that raises has not *failed* — its
verdict is **unknown**, which is strictly worse, and the failures it had
already accumulated are recoverable if the harness owns the globals dict.

**2.1 — Add to the imports:** `import importlib.util` alongside `import re`.

**2.2 — Add below `MODULE_RE` (`:44`), verbatim:**

```python
# TICKET-0061 (C3). Measured on this tree by AST import scan across
# tooling/verify/checks/*.py. Re-measure rather than trusting this tuple:
# a check that grows a new third-party dependency belongs here, and a
# missing tool must be ENVIRONMENT before execution, not a wall of
# ambiguous FAILs afterwards.
REQUIRED_TOOLS = ("fastapi", "httpx", "pyflakes", "sqlalchemy", "sqlmodel")

# TICKET-0061 (C3). TICKET-0067 found prompt_model_write.py holding TWO
# defects: the first raised before main() reached its `if FAILURES` block,
# so the second never printed. The gate could say "this check failed" and
# could not say "and it holds another failure you cannot see". Running each
# check through a harness that OWNS the globals dict makes the accumulated
# FAILURES list survivable across an uncaught exception, and gives the
# crash its own verdict class: not failed, UNKNOWN.
CRASH_EXIT = 70
_HARNESS = """
import os, sys, traceback
p = sys.argv[1]
# Replicate direct script execution: `python3 path/check.py` puts the
# script's own directory on sys.path[0]. Sibling imports depend on it
# (stylesheet_partition.py does `import legacy_mount`).
sys.path.insert(0, os.path.dirname(os.path.abspath(p)))
g = {"__name__": "__main__", "__file__": p}
code = 0
try:
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), g)
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
except BaseException:
    traceback.print_exc()
    code = 70
    fs = g.get("FAILURES")
    if isinstance(fs, list) and fs:
        print("CRASH-RECOVERED-FAILURES: %d" % len(fs))
        for f in fs:
            print("    " + str(f))
    else:
        print("CRASH-RECOVERED-FAILURES: 0")
sys.exit(code)
"""
```

The `sys.path.insert` line is load-bearing and was found by running the
corpus under the harness without it: `stylesheet_partition.py` crashed on
`import legacy_mount`. Do not drop it.

**2.3 — Add `_check_required_tools` immediately above `_classify`,
verbatim:**

```python
def _check_required_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if importlib.util.find_spec(t) is None]
    for tool in missing:
        fail(f"ENVIRONMENT: required tool {tool!r} is not installed -- the corpus cannot be evaluated")
```

**2.4 — `_classify` gains a `returncode` parameter and the CRASH branch,
placed BEFORE the existing ENVIRONMENT branch** (a crashed check's traceback
may itself mention an import, and the crash verdict is the more specific
one):

```python
def _classify(name: str, stdout: str, stderr: str, timed_out: bool, returncode: int = 1) -> str:
    if timed_out:
        return f"TIMEOUT: {name} exceeded {TIMEOUT_SECONDS}s"
    combined = f"{stderr}\n{stdout}"
    if returncode == CRASH_EXIT:
        recovered = ""
        for line in combined.splitlines():
            if line.startswith("CRASH-RECOVERED-FAILURES:"):
                recovered = line.split(":", 1)[1].strip()
        return (
            f"CRASH: {name} raised before reporting -- verdict UNKNOWN, not merely failed "
            f"({recovered} failure(s) recovered from its FAILURES list)"
        )
```

The rest of `_classify` is unchanged.

**2.5 — `main()` runs each check through the harness and reports the
recovered failures.** The subprocess invocation becomes
`[sys.executable, "-c", _HARNESS, str(path)]`; the non-zero branch passes
`returncode=proc.returncode` to `_classify` and, when the return code is
`CRASH_EXIT`, appends each recovered line as its own indented failure so it
appears in the report rather than only in the count.

**2.6 — `main()` calls `_check_required_tools()` first**, and reports and
exits immediately if it produced anything. A corpus that cannot be
evaluated must say so before running 83 checks that will each fail for the
same reason.

**2.7 — `_report_and_exit` counts CRASH separately.** The summary line
becomes `({env} environment, {crash} crash, {timeout} timeout, {other} other)`
and `other` subtracts `crash` as well. Recovered-failure lines are indented
and must not be counted as checks — count `CRASH:`-prefixed entries only.

**2.8 — Amend the module docstring's property 2** to name four verdicts
(ENVIRONMENT / CRASH / TIMEOUT / FAIL) instead of three, and record why
CRASH is not FAIL. Append; do not rewrite the existing paragraphs.

### Commit 3 — the corpus gate becomes a gate (C1)

**3.1 — This ticket's own Machine-checkable section links
`corpus_gate.py`.** TICKET-0061's acceptance criteria already contain the
bullet; confirm the arrow is present and correct.

**3.2 — `CLAUDE.md` records the standing law.** One sentence, in the
Ticket-pipeline section, stating that every ticket's Machine-checkable
section links `tooling/verify/checks/corpus_gate.py`. **Net-neutral or
reducing**: the file is at 498 lines (`wc -l`) against a 500-line cap. If
one line cannot be found by tightening an adjacent sentence, STOP and
report rather than spending the last of the budget.

---

## Scope OUT

REPORT ONLY on any of these:

- **Everything in briefs -b and -c.** No registry repoint, no rule 3b, no
  rename, no doctrine repair beyond the single line in 3.2.
- **Re-running or repairing any other check.** If a check goes red under the
  harness, that is STOP condition 5, not a repair opportunity.
- **Adding a guard to the 83 sibling checks so they flush `FAILURES` before
  dying.** The harness makes that unnecessary; a mechanical edit across 83
  files does not belong in a seal ticket. Named deferral: reactivates if a
  check is ever found whose failures the harness cannot recover — i.e. one
  that does not use the `FAILURES` list idiom.
- **`TIMEOUT_SECONDS`.** Running under the harness adds a compile step per
  check; if any check now approaches 15s, report the measurement, do not
  raise the constant.
- **`TICKET-0069/-0070/-0071` deposits.** Nia's, and a prerequisite of
  brief -b, not of this one.
- **Backend, frontend, schema, canon-write.** Untouched.

---

## Invariants to defend

- **ENVIRONMENT and CRASH stay FAILURES, never skips.** `corpus_gate.py:79`
  already says it: any edit that turns a classification into a warning
  reopens the hole the gate exists to close. The new classes are for the
  READER; the verdict is red either way.
- **The harness is behaviour-preserving.** It changes how a check is
  launched, never what it asserts. Every check's verdict before and after
  must be identical apart from the intended reclassification.
- **Subprocess isolation survives.** Checks mutate `sys.modules` and
  `os.environ` (`prompt_model_write.py::_fresh_engine`). The harness runs
  inside the subprocess; it must never become an in-process exec.
- **Vacuous-proof.** `_discover`'s floor and the coverage re-glob are
  untouched.
- **History is sacred.** Relocated status comments are appended to ticket
  bodies; no existing body text is edited.

---

## Done means

- [ ] `python tooling/verify/checks/pipeline_state.py` exits 0.
- [ ] The three tickets carry a bare enum `status:`, and each relocated
      comment appears verbatim in its ticket's appended `## Status note`.
- [ ] `python tooling/verify/checks/corpus_gate.py` exits **0**, with a
      summary reading `0 environment, 0 crash, 0 timeout, 0 other`.
- [ ] **Red-test A (crash recovery), recorded in commit 2's message.** Drop
      a synthetic check into `tooling/verify/checks/` whose first rule
      appends to `FAILURES` and whose second raises. The gate must print
      `CRASH: … verdict UNKNOWN, not merely failed (1 failure(s) recovered …)`
      **and** the recovered failure text. Delete the synthetic file.
      (Verified on a simulated tree: it reproduces the TICKET-0067 shape and
      recovers the masked failure.)
- [ ] **Red-test B (tool contract), recorded in commit 2's message.** Add a
      nonexistent name to `REQUIRED_TOOLS`; the gate must exit 1 with
      `ENVIRONMENT: required tool '…' is not installed` and run no checks.
      Revert. (Verified.)
- [ ] Every check's verdict is unchanged under the harness — diff the
      per-check pass/fail set before and after commit 2.
- [ ] `claude_md_contract.py` exits 0 and `CLAUDE.md` is within its
      500-line cap.
- [ ] Three commits on `ticket/0061`, each green on its own.
- [ ] `/review-step` and `/close-step` run.

---

## Docs to update

- `CLAUDE.md` — one sentence only (3.2). Everything else is brief -c.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — **nothing here.** The
  whole TICKET-0061 entry is written once, in brief -c, as a single
  appended supplement. Splitting it across three briefs would produce three
  partial records of one decision.
