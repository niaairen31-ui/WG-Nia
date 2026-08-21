"""Structural gate for ticket front-matter conformity (pipeline glue, BRIEF-0004),
extended by BRIEF-0006-b (TICKET-0006) with two grep-grade sentinel checks:
`.claude/commands/pipeline.md` must contain both the no-recon-spec
derivation clause and the post-recon push clause within its Step 1 recon
branch text, and `.claude/commands/brief-exec.md` must contain the CA1
relay wiring.

No DB. Every tooling/tickets/TICKET-*.md (TEMPLATE.md excluded, its glob
pattern doesn't match) must carry a parseable YAML front-matter block
containing every TEMPLATE.md field; `status` must be a literal member of
TEMPLATE.md's enum; `retry_count` an integer in 0-2; and a
`status: escalated` ticket must have a matching QUESTION file.

TICKET-0061 (E1). TICKET-0061 itself was authored with `## Done means` --
the brief template's section name -- instead of the ticket template's
`## Acceptance criteria` + `### Machine-checkable`, so `run.py`'s
`machine_checks()` parsed it to zero arrows and would have fail-closed on
it regardless of content. This module now asserts the section SHAPE every
ticket needs for `run.py` to parse it at all: exactly one `### Machine`
header, exactly one `### Live` header in that order, and -- once a ticket
has actually been briefed (`status` in brief/exec/verify/live-gate/done)
-- at least one arrow resolving to a real file under
`tooling/verify/checks/`. The parser is imported from `run.py`, never
reimplemented: this rule's whole value is asserting what `run.py` will
actually do, and a second copy of `machine_checks()`/`LINK` would drift
from the original the same way this ticket's own malformed section drifted
from the template.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TICKETS = ROOT / "tooling" / "tickets"
QUESTIONS = ROOT / "tooling" / "questions"
PIPELINE_MD = ROOT / ".claude" / "commands" / "pipeline.md"
BRIEF_EXEC_MD = ROOT / ".claude" / "commands" / "brief-exec.md"

sys.path.insert(0, str(ROOT / "tooling" / "verify"))
import run  # noqa: E402 -- reuse run.py's machine_checks/LINK, never a second copy

ARROW_FLOOR_STATUSES = {"brief", "exec", "verify", "live-gate", "done"}
MACHINE_HEADER_RE = re.compile(r"^###\s*machine")
LIVE_HEADER_RE = re.compile(r"^###\s*live")

PIPELINE_MD_SENTINELS = [
    "A ticket with NO recon spec on disk is not an error",
    "git push origin ticket/NNNN",
]
BRIEF_EXEC_MD_SENTINEL = "unattended mode (CA1)"

REQUIRED_FIELDS = [
    "id", "title", "type", "status", "created", "model_lane",
    "danger_class", "blast_radius", "brief_ids", "schema_version_touched",
    "retry_count",
]
STATUS_ENUM = {
    "intake", "recon", "brief", "exec", "verify", "live-gate", "done",
    "paused", "escalated",
}
TICKET_ID_RE = re.compile(r"^(TICKET-\d{4})")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def extract_front_matter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i]
    return None


def field_value(block_lines, field: str):
    pattern = re.compile(rf"^{re.escape(field)}:\s*(.*)$")
    for line in block_lines:
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return None


def check_section_shape(path: pathlib.Path, text: str, status: str | None) -> None:
    lines = text.splitlines()
    machine_idx = [i for i, line in enumerate(lines) if MACHINE_HEADER_RE.match(line.strip().lower())]
    live_idx = [i for i, line in enumerate(lines) if LIVE_HEADER_RE.match(line.strip().lower())]

    if len(machine_idx) == 0:
        fail(f"{path.name}: no '### Machine-checkable' header found -- run.py's machine_checks() never turns on, so the section parses to zero arrows regardless of content")
    elif len(machine_idx) > 1:
        fail(f"{path.name}: {len(machine_idx)} '### Machine-checkable' headers found -- the section boundary is ambiguous")

    if len(live_idx) == 0:
        fail(f"{path.name}: no '### Live' header found -- without a terminator, run.py's in_machine flag never turns off and arrows are collected from the entire remainder of the file")
    elif len(live_idx) > 1:
        fail(f"{path.name}: {len(live_idx)} '### Live' headers found -- the section boundary is ambiguous")

    if len(machine_idx) == 1 and len(live_idx) == 1 and live_idx[0] < machine_idx[0]:
        fail(f"{path.name}: '### Live' header appears before '### Machine-checkable' -- run.py's parser would yield garbage")

    if status in ARROW_FLOOR_STATUSES:
        arrows = run.machine_checks(text)
        if not arrows:
            fail(f"{path.name}: status '{status}' has zero Machine-checkable arrows -- a ticket that has been briefed must have criteria")
        for rel in arrows:
            check_path = run.CHECKS / pathlib.Path(rel).name
            if not check_path.exists():
                fail(f"{path.name}: Machine-checkable arrow '{rel}' does not resolve to an existing file under tooling/verify/checks/")


def check_ticket(path: pathlib.Path) -> None:
    text = path.read_text(encoding="utf-8")
    block = extract_front_matter(text)
    if block is None:
        fail(f"{path.name}: no parseable YAML front-matter block")
        return

    for field in REQUIRED_FIELDS:
        if field_value(block, field) is None:
            fail(f"{path.name}: missing field '{field}'")

    status = field_value(block, "status")
    if status is not None and status not in STATUS_ENUM:
        fail(f"{path.name}: field 'status' has out-of-enum value '{status}'")

    check_section_shape(path, text, status)

    retry_raw = field_value(block, "retry_count")
    if retry_raw is not None:
        if not re.fullmatch(r"-?\d+", retry_raw):
            fail(f"{path.name}: field 'retry_count' is not an integer ('{retry_raw}')")
        elif not (0 <= int(retry_raw) <= 2):
            fail(f"{path.name}: field 'retry_count' out of range 0-2 ({retry_raw})")

    if status == "escalated":
        m = TICKET_ID_RE.match(path.stem)
        if m is None:
            fail(f"{path.name}: cannot derive TICKET-NNNN id from filename")
        else:
            question_path = QUESTIONS / f"QUESTION-{m.group(1)}.md"
            if not question_path.exists():
                fail(
                    f"{path.name}: field 'status' is 'escalated' but "
                    f"{question_path.relative_to(ROOT).as_posix()} does not exist"
                )


def check_pipeline_md_sentinels() -> None:
    if not PIPELINE_MD.exists():
        fail(f"{PIPELINE_MD} not found")
        return
    text = PIPELINE_MD.read_text(encoding="utf-8")
    for sentinel in PIPELINE_MD_SENTINELS:
        if sentinel not in text:
            fail(f"{PIPELINE_MD.relative_to(ROOT).as_posix()}: missing sentinel phrase {sentinel!r}")


def check_brief_exec_md_sentinel() -> None:
    if not BRIEF_EXEC_MD.exists():
        fail(f"{BRIEF_EXEC_MD} not found")
        return
    text = BRIEF_EXEC_MD.read_text(encoding="utf-8")
    if BRIEF_EXEC_MD_SENTINEL not in text:
        fail(f"{BRIEF_EXEC_MD.relative_to(ROOT).as_posix()}: missing sentinel phrase {BRIEF_EXEC_MD_SENTINEL!r}")


def main() -> None:
    if not TICKETS.exists():
        fail(f"{TICKETS} not found")
    else:
        tickets = sorted(TICKETS.glob("TICKET-*.md"))
        if not tickets:
            fail(f"{TICKETS}: zero TICKET-*.md files collected -- vacuous scan")
        for path in tickets:
            check_ticket(path)

    check_pipeline_md_sentinels()
    check_brief_exec_md_sentinel()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: every ticket front-matter conforms to TEMPLATE.md")
    sys.exit(0)


if __name__ == "__main__":
    main()
