"""G1 check for TICKET-0010 (BRIEF-0010-a) — CLAUDE.md structural contract.

CLAUDE.md is a law-only, budgeted, contract-checked file: history and
chantier narrative live in ARCHITECTURE_DECISIONS.md and the schema
changelog, never here. This check makes "stays up to date" structural
instead of disciplinary.

Five assertions, all against repo-root CLAUDE.md:

1. Section whitelist, exact and ordered — the H2 set and the H3 set under
   Conventions. Any missing, extra, or reordered heading fails.
2. Budgets — total file <= 38 000 characters; no line (fenced blocks
   included, no exemption) exceeds 100 characters; the "### File
   structure" section (heading to next heading) <= 80 lines.
   The budget is a character budget on purpose. A line budget measures a
   quantity that line length defeats: at 499 lines this file held 47 084
   characters, three of its lines exceeding 1 000 each, and reflowed at 80
   columns it would have run 750 lines.
3. Archaeology ban — File structure section: zero (case-sensitive) matches
   for `BRIEF-`, `schema v`, or `v\\d+\\.\\d+` within the section.
   Invariants section: zero matches for `TICKET-\\d` or `BRIEF-\\d`
   anywhere from its heading to the next H2; an Invariants section that
   collects zero `- ` bullets is itself a FAILURE, not a pass.
4. Pointer freshness, `tooling/...` paths — every `tooling/...` path
   mentioned anywhere in CLAUDE.md exists on disk. Tokens are found by
   splitting on whitespace and backticks; a `path|alt1|alt2` shorthand
   (e.g. `tooling/tickets|recon|briefs`) expands each bare alternative as
   a sibling of the first segment's directory before testing.
5. Pointer freshness, bare `.py` tokens — every token matching
   `\\b[a-z0-9_]+\\.py\\b` anywhere in CLAUDE.md resolves to at least one
   file in the repository, found by filename under the repo root,
   excluding `.venv/` and `node_modules/`; zero tokens collected is
   itself a FAILURE.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CLAUDE_MD = ROOT / "CLAUDE.md"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


EXPECTED_H2 = [
    "What this is",
    "Stack",
    "Working rules",
    "Ticket pipeline (governance)",
    "Numbering & decisions governance",
    "Invariants (verified at every review)",
    "Local model notes",
    "Conventions",
]

EXPECTED_H3_UNDER_CONVENTIONS = [
    "File structure",
    "Naming",
    "Schema fidelity rules",
    "How to run / test",
]

TOTAL_CHAR_BUDGET = 38_000
MAX_LINE_LENGTH = 100
FILE_STRUCTURE_LINE_BUDGET = 80

ARCHAEOLOGY_PATTERNS = [
    re.compile(r"BRIEF-"),
    re.compile(r"schema v"),
    re.compile(r"v\d+\.\d+"),
]

INVARIANTS_ARCHAEOLOGY_PATTERNS = [
    re.compile(r"TICKET-\d"),
    re.compile(r"BRIEF-\d"),
]

PY_TOKEN_PATTERN = re.compile(r"\b[a-z0-9_]+\.py\b")


def check_section_whitelist(lines: list[str]) -> None:
    h2 = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
    if h2 != EXPECTED_H2:
        fail(f"H2 section set/order mismatch: got {h2!r}, expected {EXPECTED_H2!r}")

    # H3 headings strictly between the "## Conventions" H2 and the next H2
    # (or EOF) — the whitelisted H3 set applies only there.
    try:
        conv_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "## Conventions")
    except StopIteration:
        fail("'## Conventions' heading not found — cannot check its H3 subsections")
        return
    end_idx = len(lines)
    for i in range(conv_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            end_idx = i
            break
    h3 = [ln[4:].strip() for ln in lines[conv_idx + 1:end_idx] if ln.startswith("### ")]
    if h3 != EXPECTED_H3_UNDER_CONVENTIONS:
        fail(
            f"H3 subsection set/order under Conventions mismatch: got {h3!r}, "
            f"expected {EXPECTED_H3_UNDER_CONVENTIONS!r}"
        )


def _file_structure_section(lines: list[str]) -> list[str]:
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "### File structure")
    except StopIteration:
        fail("'### File structure' heading not found")
        return []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].startswith("### "):
            end = i
            break
    return lines[start:end]


def _invariants_section(lines: list[str]) -> list[str]:
    try:
        start = next(
            i for i, ln in enumerate(lines)
            if ln.strip() == "## Invariants (verified at every review)"
        )
    except StopIteration:
        fail("'## Invariants (verified at every review)' heading not found")
        return []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return lines[start:end]


def check_budgets(text: str, lines: list[str], structure_section: list[str]) -> None:
    if len(text) > TOTAL_CHAR_BUDGET:
        fail(f"CLAUDE.md is {len(text)} characters, over the {TOTAL_CHAR_BUDGET}-character budget")
    for i, line in enumerate(lines, start=1):
        if len(line) > MAX_LINE_LENGTH:
            fail(f"line {i} is {len(line)} characters, over the {MAX_LINE_LENGTH}-character ceiling")
    if len(structure_section) > FILE_STRUCTURE_LINE_BUDGET:
        fail(
            f"'### File structure' section is {len(structure_section)} lines, "
            f"over the {FILE_STRUCTURE_LINE_BUDGET}-line budget"
        )


def check_archaeology_ban(structure_section: list[str]) -> None:
    for offset, line in enumerate(structure_section):
        for pattern in ARCHAEOLOGY_PATTERNS:
            if pattern.search(line):
                fail(
                    f"'### File structure' line {offset + 1} matches banned "
                    f"pattern {pattern.pattern!r}: {line.strip()!r}"
                )


def check_invariants_archaeology(invariants_section: list[str]) -> None:
    bullets = [ln for ln in invariants_section if ln.strip().startswith("- ")]
    if not bullets:
        fail("'## Invariants' section collects zero '- ' bullets — an emptied section is a FAILURE")
        return
    for offset, line in enumerate(invariants_section):
        for pattern in INVARIANTS_ARCHAEOLOGY_PATTERNS:
            if pattern.search(line):
                fail(
                    f"'## Invariants' line {offset + 1} matches banned "
                    f"pattern {pattern.pattern!r}: {line.strip()!r}"
                )


def _expand_pipe_shorthand(token: str) -> list[str]:
    if "|" not in token:
        return [token]
    parts = token.split("|")
    base = parts[0]
    prefix_dir = base.rsplit("/", 1)[0] if "/" in base else ""
    candidates = [base]
    for alt in parts[1:]:
        candidates.append(f"{prefix_dir}/{alt}" if prefix_dir else alt)
    return candidates


def check_pointer_freshness(text: str) -> None:
    tokens = re.split(r"[\s`]+", text)
    for raw in tokens:
        token = raw.strip().rstrip(",.;:)")
        if not token.startswith("tooling/"):
            continue
        for candidate in _expand_pipe_shorthand(token):
            if not (ROOT / candidate).exists():
                fail(f"CLAUDE.md references {candidate!r} (from token {raw!r}) — not found on disk")


def check_py_pointer_freshness(text: str) -> None:
    tokens = sorted(set(PY_TOKEN_PATTERN.findall(text)))
    if not tokens:
        fail("zero bare '<name>.py' tokens found in CLAUDE.md — delegation pointers are gone")
        return
    names_on_disk = {
        p.name
        for p in ROOT.rglob("*.py")
        if ".venv" not in p.parts and "node_modules" not in p.parts
    }
    for token in tokens:
        if token not in names_on_disk:
            fail(f"CLAUDE.md references {token!r} — no file with that name found on disk")


def main() -> int:
    if not CLAUDE_MD.exists():
        fail("repo-root CLAUDE.md not found")
        print("FAIL: CLAUDE.md not found")
        return 1

    text = CLAUDE_MD.read_text(encoding="utf-8")
    lines = text.splitlines()

    check_section_whitelist(lines)
    structure_section = _file_structure_section(lines)
    invariants_section = _invariants_section(lines)
    check_budgets(text, lines, structure_section)
    check_archaeology_ban(structure_section)
    check_invariants_archaeology(invariants_section)
    check_pointer_freshness(text)
    check_py_pointer_freshness(text)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: CLAUDE.md contract — section whitelist, character/line "
        "budgets, File-structure archaeology ban, Invariants archaeology "
        "ban, tooling/ pointer freshness, .py pointer freshness"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
