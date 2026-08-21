"""G1 check for TICKET-0009 (BRIEF-0009-a) — prompt_template.model write path.

The law (delegated from CLAUDE.md, TICKET-0071 BRIEF-0071-a; rules 1-3 and
5 below already cover the write/read/seed contract): seeded rows stay
NULL — the `WORLD_ENGINE_OLLAMA_MODEL` env override must keep showing
through NULL-model templates.

No live Ollama required: `ping` is monkeypatched at the `cockpit.crud.prompts`
module level (`crud/prompts.py` does `from ...ollama_client import ping`, so
the module-level name there — not ollama_client.py's — is the one call
sites resolve).

Uses a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) so this check never touches Nia's real DB.

1. PATCH /api/prompts/{id}/model: unknown id -> 404; null always accepted
   (no ping() call, V1); valid model accepted + persisted + updated_at
   bumped; invalid model -> 422, row unchanged.
2. V1 fail-closed: ping() raising OllamaError -> 503 on a non-null save
   (row unchanged); null save still 200 (no ping() call at all).
3. GET /api/ollama/models: stub list -> 200 with exactly that list; stub
   raise -> 503, body is never an empty-list masquerade.
4. Grep guard: every `.model` attribute reference in crud/prompts.py is one of the
   two pre-existing display reads, the new write, or the new body-field
   read — no second dispatch resolver.
5. scripts/seed_pilot.py sets no `model=` on any prompt_template row
   (S-null intact).
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SEED = ROOT / "scripts" / "seed_pilot.py"
CRUD_FILE = SRC / "world_engine" / "cockpit" / "crud" / "prompts.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


ALLOWED_MODEL_ATTR_LINES = {
    '"model": r.model,',
    '"model": row.model,',
    'value = (body.model or "").strip() or None',
    'row.model = value',
    '"""Write path for `prompt_template.model` (W1) — writes `model` and',
}


def check_no_second_resolver() -> None:
    crud_text = CRUD_FILE.read_text(encoding="utf-8")
    if "def effective_model(" in crud_text:
        fail("crud/prompts.py defines its own effective_model — a second resolver, forbidden")
    for lineno, line in enumerate(crud_text.splitlines(), start=1):
        stripped = line.strip()
        if re.search(r"\.model\b", stripped) and stripped not in ALLOWED_MODEL_ATTR_LINES:
            fail(f"crud/prompts.py:{lineno} unexpected `.model` reference outside the allowlist: {stripped!r}")


def check_seed_model_free() -> None:
    r"""S-null (Q1): the seed never sets a model on a prompt_template head.

    TICKET-0067 (D1). This rule was `re.search(r"\bmodel\s*=", seed_text)`
    over the whole file. `seed_pilot.py` is 3257 lines holding 64
    triple-quoted prompt bodies, and three comments (:2206, :2227, :2339)
    record the invariant in the words `model=NULL (Q1)` — so the comments
    documenting the rule tripped the rule. Parsed, never grepped.

    Anchoring on a `PromptTemplate(` construction was rejected: this file
    has ZERO of them and 29 `upsert_prompt_template(...)` calls, whose
    `**head_fields` is how a `model=` would actually arrive. That anchor
    would match nothing and pass forever.
    """
    try:
        tree = ast.parse(SEED.read_text(encoding="utf-8"), filename=str(SEED))
    except SyntaxError as exc:
        fail(f"{SEED}: SyntaxError: {exc}")
        return

    seeded = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "upsert_prompt_template":
                seeded += 1
            for kw in node.keywords:
                if kw.arg == "model":
                    fail(
                        f"scripts/seed_pilot.py:{node.lineno} passes a `model=` "
                        "keyword argument — S-null violated"
                    )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "model":
                    fail(
                        f"scripts/seed_pilot.py:{node.lineno} assigns `.model` "
                        "— S-null violated"
                    )

    if seeded == 0:
        fail(
            "scripts/seed_pilot.py: zero upsert_prompt_template(...) calls "
            "parsed — the seeding shape changed and this scan proves nothing"
        )


def _fresh_engine():
    """Point WORLD_ENGINE_DATABASE_URL at a fresh temp SQLite file BEFORE
    importing world_engine.db (module-level engine) — isolates this check
    from the real DB and from any other check already imported in-process."""
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def check_write_path_and_list_route() -> None:
    engine = _fresh_engine()

    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit import crud as _crud
    from world_engine.cockpit.app import app
    from world_engine.models import PromptTemplate
    from world_engine.ollama_client import OllamaError
    from world_engine.writes.prompts import write_prompt_version

    with Session(engine) as session:
        row = PromptTemplate(
            name="check-fixture", usage="npc_dialogue", system_prompt="s", user_template="u"
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        row_id = row.id
        # TICKET-0067 (C1). A versionless head is structurally impossible
        # post-migration — prompt_store.current_prompt raises on one, by
        # design — and the PATCH under test summarises the row through it
        # (cockpit/crud/prompts.py:115). Seeded through the sanctioned
        # write path, never a bare Session.add(PromptVersion(...)):
        # prompt_version.py's single-write-shape rule scans src/ plus the
        # migration and would not catch the shortcut here, which is a
        # reason to avoid it, not a licence to use it.
        write_prompt_version(
            session,
            template_id=row_id,
            system_prompt="s",
            user_template="u",
        )
        session.commit()
        session.refresh(row)
        last_updated_at = row.updated_at

    client = TestClient(app)

    # unknown id -> 404
    resp = client.patch("/api/prompts/does-not-exist/model", json={"model": None})
    if resp.status_code != 404:
        fail(f"PATCH unknown id: expected 404, got {resp.status_code}")

    # null accepted, no ping() call (V1)
    def _ping_forbidden(*_a, **_k):
        fail("ping() was called for a null model save — V1 forbids this")
        raise OllamaError("should not be reached")

    _crud.prompts.ping = _ping_forbidden
    resp = client.patch(f"/api/prompts/{row_id}/model", json={"model": None})
    if resp.status_code != 200:
        fail(f"PATCH null model: expected 200, got {resp.status_code}: {resp.text}")
    elif resp.json().get("model") is not None:
        fail(f"PATCH null model: expected model=None in response, got {resp.json().get('model')!r}")
    with Session(engine) as session:
        refreshed = session.get(PromptTemplate, row_id)
        if refreshed.model is not None:
            fail("PATCH null model: row.model not cleared in DB")
        if refreshed.updated_at <= last_updated_at:
            fail("PATCH null model: updated_at was not bumped")
        last_updated_at = refreshed.updated_at

    # valid model accepted (stubbed ping -> ["m1", "m2"])
    _crud.prompts.ping = lambda *_a, **_k: ["m1", "m2"]
    resp = client.patch(f"/api/prompts/{row_id}/model", json={"model": "m1"})
    if resp.status_code != 200:
        fail(f"PATCH valid model: expected 200, got {resp.status_code}: {resp.text}")
    else:
        body = resp.json()
        if body.get("model") != "m1":
            fail(f"PATCH valid model: expected model='m1', got {body.get('model')!r}")
        if "effective_model" not in body:
            fail("PATCH valid model: response missing effective_model")
    with Session(engine) as session:
        refreshed = session.get(PromptTemplate, row_id)
        if refreshed.model != "m1":
            fail("PATCH valid model: row.model not persisted")
        if refreshed.updated_at <= last_updated_at:
            fail("PATCH valid model: updated_at was not bumped")
        last_updated_at = refreshed.updated_at

    # invalid model rejected (not in live list) -> 422, row unchanged
    resp = client.patch(f"/api/prompts/{row_id}/model", json={"model": "zz"})
    if resp.status_code != 422:
        fail(f"PATCH invalid model: expected 422, got {resp.status_code}")
    with Session(engine) as session:
        refreshed = session.get(PromptTemplate, row_id)
        if refreshed.model != "m1":
            fail(f"PATCH invalid model: row.model changed to {refreshed.model!r}, expected unchanged 'm1'")
        if refreshed.updated_at != last_updated_at:
            fail("PATCH invalid model: updated_at was bumped on a rejected save")

    # ping() raising -> 503 on non-null save, row unchanged (V1 fail-closed)
    def _ping_raises(*_a, **_k):
        raise OllamaError("Ollama is not reachable at http://fixture.")

    _crud.prompts.ping = _ping_raises
    resp = client.patch(f"/api/prompts/{row_id}/model", json={"model": "m2"})
    if resp.status_code != 503:
        fail(f"PATCH with ping raising, non-null save: expected 503, got {resp.status_code}")
    with Session(engine) as session:
        refreshed = session.get(PromptTemplate, row_id)
        if refreshed.model != "m1":
            fail(f"PATCH with ping raising, non-null save: row.model changed to {refreshed.model!r}")

    # ping() raising -> null save still 200 (no ping() call needed)
    resp = client.patch(f"/api/prompts/{row_id}/model", json={"model": None})
    if resp.status_code != 200:
        fail(f"PATCH with ping raising, null save: expected 200, got {resp.status_code}")
    with Session(engine) as session:
        refreshed = session.get(PromptTemplate, row_id)
        if refreshed.model is not None:
            fail("PATCH with ping raising, null save: row.model not cleared")

    # GET /api/ollama/models: stub list -> 200 with exactly that list
    _crud.prompts.ping = lambda *_a, **_k: ["alpha", "beta"]
    resp = client.get("/api/ollama/models")
    if resp.status_code != 200:
        fail(f"GET /api/ollama/models: expected 200, got {resp.status_code}")
    elif resp.json().get("models") != ["alpha", "beta"]:
        fail(f"GET /api/ollama/models: expected exact stub list, got {resp.json()}")

    # GET /api/ollama/models: stub raise -> 503, never an empty-list masquerade
    _crud.prompts.ping = _ping_raises
    resp = client.get("/api/ollama/models")
    if resp.status_code != 503:
        fail(f"GET /api/ollama/models with ping raising: expected 503, got {resp.status_code}")
    else:
        body = resp.json()
        if body.get("models") == []:
            fail("GET /api/ollama/models with ping raising: returned an empty-list masquerade")


def main() -> int:
    check_no_second_resolver()
    check_seed_model_free()
    check_write_path_and_list_route()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: prompt model write path — PATCH null/valid/invalid/unknown, "
        "V1 fail-closed, GET /api/ollama/models, no second resolver, seed S-null"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
