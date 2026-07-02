"""Structural gate for ticket front-matter conformity (pipeline glue, BRIEF-0004).

No DB. Every tooling/tickets/TICKET-*.md (TEMPLATE.md excluded, its glob
pattern doesn't match) must carry a parseable YAML front-matter block
containing every TEMPLATE.md field; `status` must be a literal member of
TEMPLATE.md's enum; `retry_count` an integer in 0-2; and a
`status: escalated` ticket must have a matching QUESTION file.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TICKETS = ROOT / "tooling" / "tickets"
QUESTIONS = ROOT / "tooling" / "questions"

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


def check_ticket(path: pathlib.Path) -> None:
    block = extract_front_matter(path.read_text(encoding="utf-8"))
    if block is None:
        fail(f"{path.name}: no parseable YAML front-matter block")
        return

    for field in REQUIRED_FIELDS:
        if field_value(block, field) is None:
            fail(f"{path.name}: missing field '{field}'")

    status = field_value(block, "status")
    if status is not None and status not in STATUS_ENUM:
        fail(f"{path.name}: field 'status' has out-of-enum value '{status}'")

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


def main() -> None:
    if not TICKETS.exists():
        fail(f"{TICKETS} not found")
    else:
        for path in sorted(TICKETS.glob("TICKET-*.md")):
            check_ticket(path)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: every ticket front-matter conforms to TEMPLATE.md")
    sys.exit(0)


if __name__ == "__main__":
    main()
