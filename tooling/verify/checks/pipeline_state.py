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
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TICKETS = ROOT / "tooling" / "tickets"
QUESTIONS = ROOT / "tooling" / "questions"
PIPELINE_MD = ROOT / ".claude" / "commands" / "pipeline.md"
BRIEF_EXEC_MD = ROOT / ".claude" / "commands" / "brief-exec.md"

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
        for path in sorted(TICKETS.glob("TICKET-*.md")):
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
