"""The single writer of a ticket's `## Escalations` section. Stdlib only, UTF-8.

An escalation lives in the ticket it stops, never in a separate file: a
`### E-NN — <trigger> — <brief>` entry appended at the end of the ticket's
`## Escalations` section, the section created at the end of the file if
the ticket has none. Entries are appended and answered, never rewritten or
deleted -- history is sacred.

The machine definition of an open escalation: the text after the entry's
`**Response:**` marker, up to the next entry header or the end of the file,
strips to "". `/pipeline` derives `status: escalated` from it and
`pipeline_state.py` imports it -- neither restates it.

CLI (the only way /pipeline writes the section):
    python tooling/glue/escalation.py open TICKET-NNNN D1-x <brief>  < body.json
    python tooling/glue/escalation.py answer TICKET-NNNN E-NN          < text
    python tooling/glue/escalation.py list
`body.json` holds `context`, `question` and `options`, each a string.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TICKETS = ROOT / "tooling" / "tickets"

SECTION_HEADER = "## Escalations"
RESPONSE_MARKER = "**Response:**"
TRIGGERS = ("D1-a", "D1-b", "D1-c", "D1-d")
ENTRY_RE = re.compile(r"^### (E-(\d{2})) — (.+)$")


class EscalationError(Exception):
    """A refused write: unknown ticket or entry, bad trigger, filled response."""


def _section_start(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if line.strip() == SECTION_HEADER:
            return i
    return None


def entries(text: str) -> list[dict]:
    """Every entry of the section, in file order: `id`, `title`, `response`.

    `response` is the stripped text after the marker up to the next entry
    header or the end of the file; "" when the marker is absent."""
    lines = text.splitlines()
    start = _section_start(lines)
    if start is None:
        return []
    found: list[dict] = []
    current: dict | None = None
    body: list[str] = []
    for line in lines[start + 1:]:
        m = ENTRY_RE.match(line)
        if m:
            if current is not None:
                current["response"] = _response(body)
                found.append(current)
            current, body = {"id": m.group(1), "title": m.group(3)}, []
        elif current is not None:
            body.append(line)
    if current is not None:
        current["response"] = _response(body)
        found.append(current)
    return found


def _response(body: list[str]) -> str:
    for i, line in enumerate(body):
        if line.startswith(RESPONSE_MARKER):
            rest = [line[len(RESPONSE_MARKER):]] + body[i + 1:]
            return "\n".join(rest).strip()
    return ""


def open_entries(text: str) -> list[str]:
    """The ids of the entries whose response is empty."""
    return [e["id"] for e in entries(text) if e["response"] == ""]


def ticket_path(ticket_id: str) -> pathlib.Path:
    matches = sorted(TICKETS.glob(f"{ticket_id}-*.md"))
    if len(matches) != 1:
        raise EscalationError(f"{ticket_id}: {len(matches)} ticket files match, expected 1")
    return matches[0]


def append_entry(path: pathlib.Path, trigger: str, brief: str, body: dict) -> str:
    """Appends one open entry and returns its id (E-01, E-02, ...)."""
    if trigger not in TRIGGERS:
        raise EscalationError(f"trigger {trigger!r} is not one of {TRIGGERS}")
    for key in ("context", "question", "options"):
        if not str(body.get(key, "")).strip():
            raise EscalationError(f"body has no {key!r}")
    text = path.read_text(encoding="utf-8")
    numbers = [int(e["id"][2:]) for e in entries(text)]
    entry_id = f"E-{(max(numbers) if numbers else 0) + 1:02d}"
    block = [
        f"### {entry_id} — {trigger} — {brief}",
        "",
        "**Context:**",
        str(body["context"]).strip(),
        "",
        "**Question:**",
        str(body["question"]).strip(),
        "",
        "**Options:**",
        str(body["options"]).strip(),
        "",
        RESPONSE_MARKER,
    ]
    out = text.rstrip("\n") + "\n\n"
    if _section_start(text.splitlines()) is None:
        out += SECTION_HEADER + "\n\n"
    path.write_text(out + "\n".join(block) + "\n", encoding="utf-8", newline="\n")
    return entry_id


def write_response(path: pathlib.Path, entry_id: str, answer: str) -> None:
    """Writes `answer` after the marker of an open entry; nothing else moves."""
    if not answer.strip():
        raise EscalationError("empty answer")
    text = path.read_text(encoding="utf-8")
    known = {e["id"]: e for e in entries(text)}
    if entry_id not in known:
        raise EscalationError(f"{path.name}: no entry {entry_id}")
    if known[entry_id]["response"]:
        raise EscalationError(f"{path.name}: {entry_id} is already answered")
    lines = text.splitlines()
    start = _section_start(lines)
    in_entry = False
    for i in range(start + 1, len(lines)):
        m = ENTRY_RE.match(lines[i])
        if m:
            in_entry = m.group(1) == entry_id
        elif in_entry and lines[i].startswith(RESPONSE_MARKER):
            lines[i] = RESPONSE_MARKER
            lines.insert(i + 1, answer.strip())
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["list"] and len(argv) == 1:
            for path in sorted(TICKETS.glob("TICKET-*.md")):
                for entry_id in open_entries(path.read_text(encoding="utf-8")):
                    print(f"{path.name} {entry_id}")
            return 0
        if argv[:1] == ["open"] and len(argv) == 4:
            print(append_entry(ticket_path(argv[1]), argv[2], argv[3], json.load(sys.stdin)))
            return 0
        if argv[:1] == ["answer"] and len(argv) == 3:
            write_response(ticket_path(argv[1]), argv[2], sys.stdin.read())
            return 0
    except (EscalationError, json.JSONDecodeError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("usage: escalation.py list | open TICKET-NNNN D1-x <brief> | answer TICKET-NNNN E-NN",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
