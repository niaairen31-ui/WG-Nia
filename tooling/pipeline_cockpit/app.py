"""Pipeline Cockpit — local review web UI for the ticket-management pipeline.

Endpoints
---------
GET  /                        serve index.html (two surfaces: Soumettre, Questions)
POST /api/submit              paste an artifact body; type/slug/number detected
                               and the file written to the correct path (I1)
GET  /api/questions           list open QUESTION files (D2)
POST /api/questions/answer    write a Response to an open QUESTION file (D2)
POST /api/upload               upload one or more .md files; type/number/slug
                                detected from each FILENAME (B2, BRIEF-0007),
                                never the body — a converging adapter onto the
                                same write logic /api/submit uses

Security
--------
- uvicorn is bound to 127.0.0.1 only (enforced in scripts/pipeline_cockpit.py).
- No authentication needed for this solo local tool.
- No git operation of any kind: deposit writes working-tree files only.

Structural boundaries
----------------------
- K1: nothing under tooling/pipeline_cockpit/ imports from src/world_engine/.
- Distinct port (8100) from the world cockpit (8000) — see PORT below.
"""
from __future__ import annotations

import base64
import pathlib
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "glue"))

from . import deposit
from question_response import (  # noqa: E402
    MalformedQuestion,
    ResponseAlreadyFilled,
    list_open_questions,
    write_response,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
_INDEX_HTML = pathlib.Path(__file__).parent / "index.html"

HOST = "127.0.0.1"   # loopback only — never 0.0.0.0
PORT = 8100          # distinct from the world cockpit's 8000

app = FastAPI(title="Pipeline Cockpit", docs_url=None, redoc_url=None)


class SubmitBody(BaseModel):
    body: str
    bound_ticket: str | None = None


class AnswerBody(BaseModel):
    path: str
    text: str


class UploadFileItem(BaseModel):
    filename: str
    content_base64: str


class UploadBody(BaseModel):
    files: list[UploadFileItem]
    bound_ticket: str | None = None


@app.get("/", response_class=HTMLResponse)
def serve_ui() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")


@app.post("/api/submit")
def submit_artifact(payload: SubmitBody) -> dict:
    try:
        type_ = deposit.detect_type(payload.body)
        slug = deposit.extract_slug(payload.body, type_)
        numbered_body, number = deposit.assign_number(payload.body, type_, ROOT, payload.bound_ticket)
        path = deposit.target_path(type_, number, slug, numbered_body, ROOT)
    except (
        deposit.UnknownArtifactType,
        deposit.MissingSlug,
        deposit.MissingBoundTicket,
        deposit.TargetExists,
    ) as e:
        return {"ok": False, "error": str(e)}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(numbered_body, encoding="utf-8")

    return {
        "ok": True,
        "type": type_,
        "number": number,
        "path": path.relative_to(ROOT).as_posix(),
    }


@app.post("/api/upload")
def upload_artifacts(payload: UploadBody) -> dict:
    # JSON + base64 rather than multipart/form-data: FastAPI's UploadFile
    # would pull in python-multipart, a dependency BRIEF-0007 explicitly
    # rules out. The browser still uses a native file input (see
    # index.html) — only the wire format differs from multipart.
    names = [item.filename for item in payload.files]
    order = deposit.order_upload_batch(names)

    results: list[dict] = [{}] * len(payload.files)
    current_bound = payload.bound_ticket

    for i in order:
        item = payload.files[i]
        filename = names[i]
        try:
            body = base64.b64decode(item.content_base64).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            results[i] = {"filename": filename, "ok": False, "error": f"not valid UTF-8: {e}"}
            continue

        try:
            parsed = deposit.parse_filename(filename)
            number = deposit.resolve_upload_number(parsed, current_bound)
            numbered_body = deposit.substitute_upload_number(body, number)
            path = deposit.target_path(
                parsed.type_, number, parsed.slug, numbered_body, ROOT,
                brief_suffix=parsed.brief_suffix,
            )
        except (
            deposit.UnparseableFilename,
            deposit.MissingBoundTicket,
            deposit.TargetExists,
            deposit.UnknownArtifactType,
        ) as e:
            results[i] = {"filename": filename, "ok": False, "error": str(e)}
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(numbered_body, encoding="utf-8")
        if parsed.type_ == "ticket":
            current_bound = number

        results[i] = {
            "filename": filename,
            "ok": True,
            "type": parsed.type_,
            "number": number,
            "path": path.relative_to(ROOT).as_posix(),
        }

    return {"results": results, "bound_ticket": current_bound}


def _question_text(path: pathlib.Path) -> str:
    """Read-only display helper: the '## Question' section text, using the
    same header-to-next-header extraction shape as response_section."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Question":
            start = i
            break
    if start is None:
        return ""
    body_lines = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body_lines.append(line)
    return "\n".join(body_lines).strip()


@app.get("/api/questions")
def get_open_questions() -> dict:
    questions = [
        {"path": p.relative_to(ROOT).as_posix(), "question": _question_text(p)}
        for p in list_open_questions(ROOT)
    ]
    return {"questions": questions}


@app.post("/api/questions/answer")
def answer_question(payload: AnswerBody) -> dict:
    path = ROOT / payload.path
    try:
        write_response(path, payload.text)
    except ResponseAlreadyFilled as e:
        return {"ok": False, "error": str(e)}
    except MalformedQuestion as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}
