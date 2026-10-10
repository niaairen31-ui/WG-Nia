"""G1 check for TICKET-0117 (BRIEF-0117-a, J2-a) -- an escalation lives in
the ticket it stops, written only by `tooling/glue/escalation.py`.

Runs the writer against a scratch ticket in a temporary directory (its
`TICKETS` constant is pointed there), never against a real ticket.

EW1 -- open. The first `append_entry` on a ticket with no section creates
   `## Escalations` at the end of the file and appends `E-01`; a second
   appends `E-02`; everything above the section is byte-identical to the
   ticket before the first write; both entries are open.
EW2 -- answer. `write_response` on `E-01` leaves only `E-02` open and
   stores the answer verbatim; answering `E-01` again, an unknown id, or
   with an empty answer raises `EscalationError` and changes nothing.
EW3 -- refusals. A trigger outside `TRIGGERS`, and a body missing
   `question`, raise `EscalationError` and change nothing.
EW4 -- the one parser. `pipeline_state.py` imports `escalation` and calls
   `open_entries(`; it holds no `**Response:**` literal of its own.

Every rule judges at least one concrete entry or file -- a rule that
collects nothing is a FAILURE.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tooling" / "glue"))
import escalation  # noqa: E402

PIPELINE_STATE = ROOT / "tooling" / "verify" / "checks" / "pipeline_state.py"
TICKET_TEXT = (
    "---\nid: TICKET-9999\nstatus: exec\n---\n\n## Request\n\nA scratch ticket.\n\n"
    "## Acceptance criteria\n\n### Machine-checkable\n- [ ] x  -> verify/checks/x.py\n\n"
    "### Live\n- [ ] y\n"
)
BODY = {"context": "Tried the brief.", "question": "Which one?", "options": "A. this\nB. that"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def refused(call) -> bool:
    try:
        call()
    except escalation.EscalationError:
        return True
    return False


def check_writer(tmp: pathlib.Path) -> None:
    escalation.TICKETS = tmp
    path = tmp / "TICKET-9999-scratch.md"
    path.write_text(TICKET_TEXT, encoding="utf-8")
    first = escalation.append_entry(escalation.ticket_path("TICKET-9999"), "D1-a", "B", BODY)
    second = escalation.append_entry(path, "D1-d", "C", BODY)
    text = path.read_text(encoding="utf-8")
    if (first, second) != ("E-01", "E-02"):
        fail(f"EW1: ids are {(first, second)}, expected ('E-01', 'E-02')")
    if not text.startswith(TICKET_TEXT.rstrip("\n")):
        fail("EW1: the ticket above the section changed")
    if text.count(escalation.SECTION_HEADER) != 1:
        fail(f"EW1: {text.count(escalation.SECTION_HEADER)} section headers, expected 1")
    if escalation.open_entries(text) != ["E-01", "E-02"]:
        fail(f"EW1: open entries are {escalation.open_entries(text)}")

    escalation.write_response(path, "E-01", "  B, with the caveat.  ")
    text = path.read_text(encoding="utf-8")
    if escalation.open_entries(text) != ["E-02"]:
        fail(f"EW2: open entries after an answer are {escalation.open_entries(text)}")
    answered = {e["id"]: e["response"] for e in escalation.entries(text)}
    if answered.get("E-01") != "B, with the caveat.":
        fail(f"EW2: E-01's response is {answered.get('E-01')!r}")
    for label, call in (
        ("a second answer", lambda: escalation.write_response(path, "E-01", "again")),
        ("an unknown id", lambda: escalation.write_response(path, "E-07", "x")),
        ("an empty answer", lambda: escalation.write_response(path, "E-02", "  ")),
        ("an unknown trigger", lambda: escalation.append_entry(path, "D2-a", "B", BODY)),
        ("a body without a question",
         lambda: escalation.append_entry(path, "D1-a", "B", {"context": "x", "options": "y"})),
    ):
        if not refused(call):
            fail(f"EW2/EW3: {label} was not refused")
        if path.read_text(encoding="utf-8") != text:
            fail(f"EW2/EW3: {label} changed the ticket")
            text = path.read_text(encoding="utf-8")


def check_one_parser() -> None:
    if not PIPELINE_STATE.exists():
        fail("EW4: pipeline_state.py not found")
        return
    source = PIPELINE_STATE.read_text(encoding="utf-8")
    if "import escalation" not in source or "open_entries(" not in source:
        fail("EW4: pipeline_state.py does not use escalation.open_entries")
    if "**Response:**" in source:
        fail("EW4: pipeline_state.py restates the response marker")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        check_writer(pathlib.Path(tmp))
    check_one_parser()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: escalation_writer -- an escalation is appended to and answered in its "
          "own ticket, by one writer, and read by one parser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
