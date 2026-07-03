"""The single QUESTION writer (N1). Stdlib only, UTF-8.

Defines the machine contract for "empty `## Response`": stripped content
after the `## Response` header, up to the next `## ` header or EOF, equal
to `""`. Every consumer — the pipeline cockpit's Questions surface and the
inline in-session escalation flow — points here; neither writes a
QUESTION file's `## Response` section any other way.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "tooling" / "questions"

RESPONSE_HEADER = "## Response"


class ResponseAlreadyFilled(Exception):
    """Raised when write_response targets a QUESTION file whose
    `## Response` section is not empty."""


class MalformedQuestion(Exception):
    """Raised when a QUESTION file has no `## Response` header."""


def _response_header_index(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if line.strip() == RESPONSE_HEADER:
            return i
    return None


def response_section(text: str) -> str:
    """Returns the content after the `## Response` header line, up to the
    next `## ` header or EOF. Empty string if no `## Response` header."""
    lines = text.splitlines()
    start = _response_header_index(lines)
    if start is None:
        return ""
    body_lines = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body_lines.append(line)
    return "\n".join(body_lines)


def is_open(path: pathlib.Path) -> bool:
    """True iff response_section(path) strips to the empty string. This IS
    the machine definition of "empty `## Response`"."""
    return response_section(path.read_text(encoding="utf-8")).strip() == ""


def list_open_questions(root: pathlib.Path = ROOT) -> list[pathlib.Path]:
    """Every tooling/questions/QUESTION-*.md where is_open is True, sorted
    by name."""
    questions_dir = root / "tooling" / "questions"
    if not questions_dir.exists():
        return []
    return sorted(
        p for p in questions_dir.glob("QUESTION-*.md") if is_open(p)
    )


def write_response(path: pathlib.Path, text: str) -> None:
    """Inserts `text` (stripped, plus trailing newline) immediately after
    the `## Response` header line. Nothing above `## Response` is ever
    modified.

    Raises ResponseAlreadyFilled if the file's `## Response` section is
    not empty; raises MalformedQuestion if no `## Response` header exists.
    """
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    header_index = _response_header_index(lines)
    if header_index is None:
        raise MalformedQuestion(f"{path}: no '## Response' header found")
    if not is_open(path):
        raise ResponseAlreadyFilled(f"{path}: '## Response' is already filled")

    new_lines = lines[: header_index + 1] + [text.strip()] + lines[header_index + 1:]
    new_text = "\n".join(new_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text, encoding="utf-8")


def _cli_list() -> int:
    for path in list_open_questions():
        print(path)
    return 0


def _cli_answer(file_arg: str) -> int:
    path = pathlib.Path(file_arg)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        print(f"MalformedQuestion: {path} does not exist", file=sys.stderr)
        return 2
    text = sys.stdin.read()
    try:
        write_response(path, text)
    except ResponseAlreadyFilled as e:
        print(f"ResponseAlreadyFilled: {e}", file=sys.stderr)
        return 1
    except MalformedQuestion as e:
        print(f"MalformedQuestion: {e}", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: question_response.py list|answer <file>", file=sys.stderr)
        return 2
    if sys.argv[1] == "list":
        return _cli_list()
    if sys.argv[1] == "answer":
        if len(sys.argv) < 3:
            print("usage: question_response.py answer <file>", file=sys.stderr)
            return 2
        return _cli_answer(sys.argv[2])
    print(f"usage: unknown subcommand '{sys.argv[1]}'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
