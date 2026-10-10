"""G1 check for TICKET-0010 (BRIEF-0010-a), extended by TICKET-0117 -- the
instruction corpus: the root CLAUDE.md and every `.claude/rules/*.md`.

CLAUDE.md is a law-only, budgeted, contract-checked file: history and
chantier narrative live in ARCHITECTURE_DECISIONS.md and the schema
changelog, never here. Invariants that hold for one part of the code live
in path-scoped rule files, loaded by Claude Code when a session touches a
matching file (TICKET-0117, D1/G1). This check makes "stays up to date"
structural instead of disciplinary.

1. Section whitelist, exact and ordered -- the root's H2 set and the H3 set
   under Conventions. Any missing, extra, or reordered heading fails.
2. Budgets -- root <= 22 000 characters and each rule file <= 4 000; no line
   of any of them (fenced blocks included) exceeds 100 characters; the
   root's "### File structure" section (heading to next heading) <= 30
   lines. The budget counts characters, not bytes or lines.
3. Archaeology ban -- File structure: zero (case-sensitive) matches for
   `BRIEF-`, `schema v`, or `v\\d+\\.\\d+`. Every Invariants section (the
   root's, and each rule file's `## Invariants`): zero matches for
   `TICKET-\\d` or `BRIEF-\\d`.
4. Pointer freshness, `tooling/...` paths -- every `tooling/...` path in any
   file of the corpus exists on disk; a `path|alt1|alt2` shorthand expands
   each bare alternative as a sibling of the first segment's directory.
5. Pointer freshness, bare `.py` tokens -- every `\\b[a-z0-9_]+\\.py\\b`
   token in the corpus names a file somewhere in the repository (excluding
   `.venv/` and `node_modules/`); zero tokens collected is a FAILURE.
6. Invariant ids (C1, F1) -- every bullet of every Invariants section starts
   `- **INV-NN**` and ends with `-- enforced by` and one or more
   `` `<check>.py` `` naming files under `tooling/verify/checks/`, or with
   `[no check]`. Ids are unique across the corpus; none is listed in
   `tooling/verify/baselines/invariant_ids.retired`; live and retired ids
   together are exactly INV-01 to the highest, so an id is never dropped
   silently. Zero invariants collected is a FAILURE.
7. Rule files (G1) -- `.claude/rules/` holds at least one `*.md`; each opens
   with a front-matter block `---` / `paths:` / one or more `  - "<glob>"`
   lines / `---`; a glob holds no `{` or `[` and matches at least one file
   from the repository root. The file names listed in the root's
   "Path-scoped rules" section equal the files on disk.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CLAUDE_MD = ROOT / "CLAUDE.md"
RULES_DIR = ROOT / ".claude" / "rules"
CHECKS_DIR = ROOT / "tooling" / "verify" / "checks"
RETIRED_IDS = ROOT / "tooling" / "verify" / "baselines" / "invariant_ids.retired"

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
    "Path-scoped rules",
    "Conventions",
]

EXPECTED_H3_UNDER_CONVENTIONS = [
    "File structure",
    "Naming",
    "Schema fidelity rules",
    "How to run / test",
]

ROOT_CHAR_BUDGET = 22_000
RULE_CHAR_BUDGET = 4_000
MAX_LINE_LENGTH = 100
FILE_STRUCTURE_LINE_BUDGET = 30

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
INV_HEAD = re.compile(r"^- \*\*INV-(\d{2})\*\* ")
ENFORCED = re.compile(r"-- enforced by ((?:`[a-z0-9_]+\.py`, )*`[a-z0-9_]+\.py`)$")
NO_CHECK = "[no check]"
GLOB_LINE = re.compile(r'^  - "([^"]+)"$')
RULE_LISTING = re.compile(r"^- `([a-z0-9-]+\.md)` — ")


def section(lines: list[str], heading: str, stop: tuple[str, ...]) -> list[str]:
    """From the line equal to `heading` to the next line starting with any
    of `stop`; [] when the heading is absent."""
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith(stop):
            end = i
            break
    return lines[start:end]


def check_section_whitelist(lines: list[str]) -> None:
    h2 = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
    if h2 != EXPECTED_H2:
        fail(f"H2 section set/order mismatch: got {h2!r}, expected {EXPECTED_H2!r}")
    conventions = section(lines, "## Conventions", ("## ",))
    if not conventions:
        fail("'## Conventions' heading not found — cannot check its H3 subsections")
        return
    h3 = [ln[4:].strip() for ln in conventions if ln.startswith("### ")]
    if h3 != EXPECTED_H3_UNDER_CONVENTIONS:
        fail(
            f"H3 subsection set/order under Conventions mismatch: got {h3!r}, "
            f"expected {EXPECTED_H3_UNDER_CONVENTIONS!r}"
        )


def check_budgets(name: str, text: str, budget: int) -> None:
    if len(text) > budget:
        fail(f"{name} is {len(text)} characters, over the {budget}-character budget")
    for i, line in enumerate(text.splitlines(), start=1):
        if len(line) > MAX_LINE_LENGTH:
            fail(f"{name} line {i} is {len(line)} characters, over the "
                 f"{MAX_LINE_LENGTH}-character ceiling")


def check_file_structure(lines: list[str]) -> None:
    structure = section(lines, "### File structure", ("## ", "### "))
    if not structure:
        fail("'### File structure' heading not found")
        return
    if len(structure) > FILE_STRUCTURE_LINE_BUDGET:
        fail(f"'### File structure' section is {len(structure)} lines, "
             f"over the {FILE_STRUCTURE_LINE_BUDGET}-line budget")
    for offset, line in enumerate(structure):
        for pattern in ARCHAEOLOGY_PATTERNS:
            if pattern.search(line):
                fail(f"'### File structure' line {offset + 1} matches banned "
                     f"pattern {pattern.pattern!r}: {line.strip()!r}")


def invariant_bullets(name: str, block: list[str]) -> list[str]:
    """Each `- ` bullet of an Invariants section, its continuation lines
    joined with single spaces; archaeology-checked on the way."""
    bullets: list[str] = []
    for offset, line in enumerate(block):
        for pattern in INVARIANTS_ARCHAEOLOGY_PATTERNS:
            if pattern.search(line):
                fail(f"{name} Invariants line {offset + 1} matches banned "
                     f"pattern {pattern.pattern!r}: {line.strip()!r}")
        if line.startswith("- "):
            bullets.append(line.strip())
        elif bullets and line.startswith("  ") and line.strip():
            bullets[-1] += " " + line.strip()
    return bullets


def check_invariant(name: str, bullet: str) -> int | None:
    head = INV_HEAD.match(bullet)
    if head is None:
        fail(f"{name}: invariant without an '- **INV-NN**' id: {bullet[:70]!r}")
        return None
    inv_id = f"INV-{head.group(1)}"
    enforced = ENFORCED.search(bullet)
    if enforced:
        for check in re.findall(r"`([a-z0-9_]+\.py)`", enforced.group(1)):
            if not (CHECKS_DIR / check).exists():
                fail(f"{name}: {inv_id} is enforced by {check}, not found in tooling/verify/checks/")
    elif not bullet.endswith(NO_CHECK):
        fail(f"{name}: {inv_id} ends with neither '-- enforced by `<check>.py`' nor '{NO_CHECK}'")
    return int(head.group(1))


def check_invariant_ids(ids: list[tuple[str, int]]) -> None:
    if not ids:
        fail("zero invariants collected across the corpus — an emptied law is a FAILURE")
        return
    seen: dict[int, str] = {}
    for name, number in ids:
        if number in seen:
            fail(f"INV-{number:02d} appears in {seen[number]} and {name}")
        seen[number] = name
    if not RETIRED_IDS.exists():
        fail(f"{RETIRED_IDS.relative_to(ROOT).as_posix()} not found")
        return
    retired = {
        int(m.group(1))
        for line in RETIRED_IDS.read_text(encoding="utf-8").splitlines()
        if (m := re.match(r"^INV-(\d{2})\b", line))
    }
    for number in sorted(retired & set(seen)):
        fail(f"INV-{number:02d} is retired but still live in {seen[number]}")
    issued = set(seen) | retired
    missing = sorted(set(range(1, max(issued) + 1)) - issued)
    if missing:
        fail("ids neither live nor retired: " + ", ".join(f"INV-{n:02d}" for n in missing))


def rule_paths(name: str, lines: list[str]) -> list[str]:
    if not lines or lines[0] != "---" or len(lines) < 3 or lines[1] != "paths:":
        fail(f"{name}: does not open with a '---' / 'paths:' front-matter block")
        return []
    globs: list[str] = []
    for line in lines[2:]:
        if line == "---":
            break
        match = GLOB_LINE.match(line)
        if match is None:
            fail(f"{name}: front-matter line {line!r} is not '  - \"<glob>\"'")
            return []
        globs.append(match.group(1))
    else:
        fail(f"{name}: front-matter block is not closed by '---'")
    if not globs:
        fail(f"{name}: 'paths:' lists no glob")
    return globs


def check_rule_globs(name: str, globs: list[str]) -> None:
    for pattern in globs:
        if "{" in pattern or "[" in pattern:
            fail(f"{name}: glob {pattern!r} uses braces or brackets")
        elif not any(ROOT.glob(pattern)):
            fail(f"{name}: glob {pattern!r} matches no file")


def check_rule_listing(lines: list[str], on_disk: list[str]) -> None:
    block = section(lines, "## Path-scoped rules", ("## ",))
    listed = sorted(m.group(1) for line in block if (m := RULE_LISTING.match(line)))
    if listed != sorted(on_disk):
        fail(f"'## Path-scoped rules' lists {listed}, .claude/rules/ holds {sorted(on_disk)}")


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


def check_pointer_freshness(name: str, text: str) -> None:
    for raw in re.split(r"[\s`]+", text):
        token = raw.strip().rstrip(",.;:)")
        if not token.startswith("tooling/"):
            continue
        for candidate in _expand_pipe_shorthand(token):
            if not (ROOT / candidate).exists():
                fail(f"{name} references {candidate!r} (from token {raw!r}) — not found on disk")


def check_py_pointer_freshness(corpus: dict[str, str]) -> None:
    tokens = {(tok, name) for name, text in corpus.items() for tok in PY_TOKEN_PATTERN.findall(text)}
    if not tokens:
        fail("zero bare '<name>.py' tokens found in the corpus — delegation pointers are gone")
        return
    names_on_disk = {
        p.name
        for p in ROOT.rglob("*.py")
        if ".venv" not in p.parts and "node_modules" not in p.parts
    }
    for token, name in sorted(tokens):
        if token not in names_on_disk:
            fail(f"{name} references {token!r} — no file with that name found on disk")


def load_rules() -> dict[str, str]:
    if not RULES_DIR.is_dir():
        fail(".claude/rules/ not found")
        return {}
    rules = {p.name: p.read_text(encoding="utf-8") for p in sorted(RULES_DIR.glob("*.md"))}
    if not rules:
        fail(".claude/rules/ holds no *.md — zero rule files collected")
    return rules


def main() -> int:
    if not CLAUDE_MD.exists():
        print("FAIL: CLAUDE.md not found")
        return 1
    text = CLAUDE_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    rules = load_rules()
    corpus = {"CLAUDE.md": text} | {f".claude/rules/{n}": t for n, t in rules.items()}

    check_section_whitelist(lines)
    check_budgets("CLAUDE.md", text, ROOT_CHAR_BUDGET)
    check_file_structure(lines)
    blocks = {"CLAUDE.md": section(lines, "## Invariants (verified at every review)", ("## ",))}
    for name, body in rules.items():
        rule_lines = body.splitlines()
        check_budgets(f".claude/rules/{name}", body, RULE_CHAR_BUDGET)
        check_rule_globs(name, rule_paths(name, rule_lines))
        blocks[f".claude/rules/{name}"] = section(rule_lines, "## Invariants", ("## ",))
    check_rule_listing(lines, list(rules))
    ids: list[tuple[str, int]] = []
    for name, block in blocks.items():
        for bullet in invariant_bullets(name, block):
            number = check_invariant(name, bullet)
            if number is not None:
                ids.append((name, number))
    check_invariant_ids(ids)
    for name, body in corpus.items():
        check_pointer_freshness(name, body)
    check_py_pointer_freshness(corpus)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: CLAUDE.md contract — root and {len(rules)} rule file(s): whitelist, "
        f"budgets, archaeology bans, {len(ids)} invariants with ids and markers, "
        "rule globs live, pointers fresh"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
