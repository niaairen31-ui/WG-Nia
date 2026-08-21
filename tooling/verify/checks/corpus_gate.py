"""G1 check: corpus gate -- every check in tooling/verify/checks/ runs, or
this gate is red (TICKET-0060, BRIEF-0060-d, B1).

`tooling/verify/run.py` executes only the checks a ticket's Machine-checkable
section links with a `-> verify/checks/NAME.py` arrow. That is correct as a
per-ticket gate and insufficient as a corpus guarantee: a check no ticket
references is never executed, and its failure is invisible.
`observation_surface.py` was red on `main` from the moment TICKET-0059
merged until BRIEF-0060-a repaired it -- TICKET-0059's Machine section
linked eleven checks and not that one. This module makes "every guard is
live" a property the machinery proves rather than a convention the ticket
author is trusted to maintain by writing enough arrows.

Stdlib only, same FAILURES/fail/main idiom as legacy_mount.py and
observation_surface.py. Three properties, each vacuous-proof:

  1. Discovery: every `*.py` in this directory except this module itself
     (excluded by resolved path, never by name string; the exclusion must
     remove exactly one entry).
  2. Execution: each discovered check runs as a subprocess with the current
     interpreter, inheriting the environment, under a per-check timeout. A
     non-zero exit is classified ENVIRONMENT (unimportable) / TIMEOUT /
     FAIL -- all three are failures, never a skip.
  3. Coverage: the set of executed paths equals the discovered set. A
     directory listing that outran the executed set is a FAIL naming the
     missed files -- not merely "some checks passed".

TICKET-0061 (C3): property 2's verdicts are ENVIRONMENT / CRASH / TIMEOUT /
FAIL. CRASH is a check that raised before it finished reporting -- verdict
UNKNOWN, not merely failed, because whatever rules it had already checked
before the exception are unproven, not disproven. TICKET-0067 found
prompt_model_write.py holding two independent defects where the first
raised before main() reached its `if FAILURES` block, hiding the second
from the report entirely. CRASH is still a failure, same as the other
three -- the new class is for the reader, never a way to make the gate
less red.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHECKS = ROOT / "tooling" / "verify" / "checks"
SELF = Path(__file__).resolve()

# Measured on this tree during BRIEF-0060-d's mini-RECON: the slowest of the
# 82 sibling checks was prompt_version.py at 3.22s. Four times that is
# 12.88s; rounded up with headroom for a slower machine or a cold disk cache.
TIMEOUT_SECONDS = 15

MODULE_RE = re.compile(r"No module named '([^']+)'")

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

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(msg)
        env = sum(1 for m in FAILURES if m.startswith("ENVIRONMENT:"))
        crash = sum(1 for m in FAILURES if m.startswith("CRASH:"))
        timeout = sum(1 for m in FAILURES if m.startswith("TIMEOUT:"))
        recovered = sum(1 for m in FAILURES if m.startswith("    "))
        other = len(FAILURES) - env - crash - timeout - recovered
        print(
            f"SUMMARY: {len(FAILURES)} check(s) failed "
            f"({env} environment, {crash} crash, {timeout} timeout, {other} other)"
        )
        sys.exit(1)
    print(
        f"PASS: corpus_gate — {counts['discovered']} check(s) discovered, "
        f"{counts['executed']} executed, {counts['passed']} passed"
    )
    sys.exit(0)


# TICKET-0060 (BRIEF-0060-d, B1). Three verdicts, one outcome: red.
# The classification is for the READER, never for the gate. A check that
# cannot be imported has not passed -- it has not run, which is strictly
# worse, because a skip looks like silence and silence looks like green.
# RECON-0060-a measured this exactly: in a container without fastapi and
# sqlalchemy, four checks could not be evaluated and one reported a
# subprocess failure indistinguishable from a real one. Any future edit
# that turns ENVIRONMENT into a warning re-opens the hole this gate was
# built to close.
def _check_required_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if importlib.util.find_spec(t) is None]
    for tool in missing:
        fail(f"ENVIRONMENT: required tool {tool!r} is not installed -- the corpus cannot be evaluated")


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
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        m = MODULE_RE.search(combined)
        module = m.group(1) if m else "unknown"
        return f"ENVIRONMENT: {name} could not be imported ({module})"
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    last = lines[-1] if lines else "(no output)"
    return f"FAIL: {name} — {last}"


def _discover() -> list[Path] | None:
    if not CHECKS.is_dir():
        fail(f"FAIL: {CHECKS} is not a directory")
        return None
    all_py = sorted(CHECKS.glob("*.py"))
    excluded = [p for p in all_py if p.resolve() == SELF]
    if len(excluded) != 1:
        fail(
            f"FAIL: self-exclusion removed {len(excluded)} file(s) from the "
            f"discovered set, expected exactly 1"
        )
        return None
    discovered = [p for p in all_py if p.resolve() != SELF]
    if len(discovered) < 2:
        fail(f"FAIL: only {len(discovered)} check(s) discovered -- fewer than two is a failure")
        return None
    return discovered


def main() -> None:
    _check_required_tools()
    if FAILURES:
        _report_and_exit()
        return

    discovered = _discover()
    if discovered is None:
        _report_and_exit()
        return

    executed: list[Path] = []
    passed = 0
    for path in discovered:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", _HARNESS, str(path)],
                capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
            )
            executed.append(path)
            if proc.returncode == 0:
                passed += 1
            else:
                fail(_classify(path.name, proc.stdout, proc.stderr, timed_out=False, returncode=proc.returncode))
                if proc.returncode == CRASH_EXIT:
                    # Recovered failure lines are printed to stdout by the
                    # harness (print()); the traceback is stderr
                    # (traceback.print_exc()) and is also 4-space indented
                    # Python source context -- scanning stdout only keeps
                    # the two apart.
                    for line in proc.stdout.splitlines():
                        if line.startswith("    ") and line.strip():
                            fail(line)
        except subprocess.TimeoutExpired as exc:
            executed.append(path)
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
            fail(_classify(path.name, stdout, stderr, timed_out=True))

    if not executed:
        fail("FAIL: zero checks executed")

    # Independent re-glob, deliberately not reusing `discovered` above --
    # the whole point of this assertion is to catch a discovery bug (an
    # over-narrow glob, a bad exclusion) rather than merely confirm that
    # everything _discover() handed back also got executed, which would be
    # true by construction and prove nothing.
    current_directory_set = {p.resolve() for p in sorted(CHECKS.glob("*.py")) if p.resolve() != SELF}
    executed_set = {p.resolve() for p in executed}
    missed = current_directory_set - executed_set
    if missed:
        names = ", ".join(sorted(p.name for p in missed))
        fail(f"FAIL: coverage gap -- {len(missed)} discovered check(s) never executed: {names}")

    if FAILURES:
        _report_and_exit()
        return

    _report_and_exit({"discovered": len(discovered), "executed": len(executed), "passed": passed})


if __name__ == "__main__":
    main()
