"""G1 check: effect_self_write (TICKET-0062, BRIEF-0062-a commit 2).

The rule: inside a `$effect` (or `$effect.pre`) body, a `$state` binding
that is ASSIGNED in that body must not be READ afterwards in the same
body. Local functions called from the body (`function <name>(...) { ... }`
declared in the same <script> block) are inlined one level deep, since
that is exactly how DoorsEditor.svelte's `resetFromProps` hid the pattern:
the effect body itself only called `resetFromProps(...)`; the
assign-then-read of `neighbours` lived inside that function.

A "read" is narrowly `<name>.` or `<name>[` — property/index access —
not a bare identifier reference. This is deliberate, not an
approximation: `RelationsEditor.svelte`'s `newOther` effect reads that
binding (`e.id === newOther`, a bare comparison) and then conditionally
assigns it under a converging guard. Widening "read" to any identifier
use, or dropping the "after the first assignment" ordering, would flag
that legitimate pattern. The ordering is the whole rule.

Unlike most checks in this directory, zero findings is the GOAL state,
not a vacuity signal — the fixed tree is supposed to report clean. The
vacuity guard therefore sits on the SCAN, not on the finding count:
zero .svelte files collected, zero $effect bodies parsed, or zero
$state bindings found are each a FAIL (a scan that silently found
nothing to look at, not a codebase with nothing wrong). A future
reader must not "fix" this check by making zero findings a failure.

AST-free: Svelte's compiler isn't invoked here, so this is a textual
brace-matching scan, not a real parser. It is intentionally narrow
(single-level function inlining, simple assignment/read regexes) to
match exactly the failure mode this ticket diagnosed, not to be a
general-purpose Svelte effect analyzer.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"

FAILURES: list[str] = []

STATE_DECL_RE = re.compile(r"\blet\s+(\w+)\s*=\s*\$state\b")
EFFECT_START_RE = re.compile(r"\$effect(?:\.pre)?\s*\(")
FUNCTION_DECL_RE = re.compile(r"\bfunction\s+(\w+)\s*\([^)]*\)\s*\{")


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(files: int, effects: int, state_bindings: int) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: effect_self_write — {files} .svelte file(s), {effects} $effect "
        f"bod(y/ies), {state_bindings} $state binding(s) scanned, zero "
        f"assign-then-read findings"
    )
    sys.exit(0)


def _brace_match(text: str, open_index: int) -> int | None:
    """`text[open_index]` must be '{'. Returns the index of the matching
    '}', or None if the braces never close (malformed/unsupported syntax)."""
    depth = 0
    for i in range(open_index, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _find_effect_bodies(text: str) -> list[str]:
    """Every `$effect(...)`/`$effect.pre(...)` body's literal source text."""
    bodies = []
    for m in EFFECT_START_RE.finditer(text):
        brace_idx = text.find("{", m.end())
        if brace_idx == -1:
            continue
        close_idx = _brace_match(text, brace_idx)
        if close_idx is None:
            continue
        bodies.append(text[brace_idx + 1 : close_idx])
    return bodies


def _function_bodies(text: str) -> dict[str, str]:
    """name -> body text, for every top-level `function name(...) { ... }`
    in the file (one <script> block; no nested-scope resolution needed)."""
    out: dict[str, str] = {}
    for m in FUNCTION_DECL_RE.finditer(text):
        name = m.group(1)
        brace_idx = m.end() - 1  # FUNCTION_DECL_RE consumes up to and including '{'
        close_idx = _brace_match(text, brace_idx)
        if close_idx is None:
            continue
        out[name] = text[brace_idx + 1 : close_idx]
    return out


def _inline_one_level(effect_body: str, functions: dict[str, str]) -> str:
    """Append the body of every locally-declared function CALLED from
    effect_body, one level deep (no recursion into what those bodies
    themselves call)."""
    called = set()
    for name in functions:
        if re.search(rf"\b{re.escape(name)}\s*\(", effect_body):
            called.add(name)
    if not called:
        return effect_body
    return effect_body + "\n" + "\n".join(functions[name] for name in sorted(called))


def _assign_then_read(effective_body: str, state_name: str) -> str | None:
    """Returns the offending read expression if `state_name` is assigned
    and then later read (`.` or `[` access) in `effective_body`; else None."""
    escaped = re.escape(state_name)
    assign_re = re.compile(rf"(?<![.\w]){escaped}\s*=(?![=>])")
    assign_m = assign_re.search(effective_body)
    if assign_m is None:
        return None

    read_re = re.compile(rf"(?<![.\w]){escaped}(\.\w+|\[)")
    read_m = read_re.search(effective_body, assign_m.end())
    if read_m is None:
        return None
    return effective_body[read_m.start() : read_m.start() + 40].splitlines()[0]


def main() -> None:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        _report_and_exit(0, 0, 0)
        return

    svelte_files = sorted(FRONTEND_SRC.rglob("*.svelte"))
    if not svelte_files:
        fail("vacuous scan: no components — zero .svelte files under frontend/src/")
        _report_and_exit(0, 0, 0)
        return

    total_effects = 0
    total_state_bindings = 0

    for path in svelte_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()

        state_names = STATE_DECL_RE.findall(text)
        total_state_bindings += len(state_names)
        if not state_names:
            continue

        effect_bodies = _find_effect_bodies(text)
        total_effects += len(effect_bodies)
        if not effect_bodies:
            continue

        functions = _function_bodies(text)

        for effect_body in effect_bodies:
            effective = _inline_one_level(effect_body, functions)
            for state_name in state_names:
                offender = _assign_then_read(effective, state_name)
                if offender is not None:
                    fail(
                        f"{rel}: '{state_name}' assigned then READ later in "
                        f"the same $effect body (reading expression: "
                        f"{offender!r})"
                    )

    if total_effects == 0:
        fail("vacuous scan: no effects parsed — brace matcher found zero $effect bodies")
    if total_state_bindings == 0:
        fail("vacuous scan: zero $state bindings found across all files")

    _report_and_exit(len(svelte_files), total_effects, total_state_bindings)


if __name__ == "__main__":
    main()
