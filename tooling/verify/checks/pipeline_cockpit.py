"""Structural gate for the pipeline cockpit (BRIEF-0006-a). No network.

- imports tooling.pipeline_cockpit.app cleanly; asserts its PORT constant
  is 8100 (distinct from the world cockpit's 8000).
- K1 import boundary: no .py under tooling/pipeline_cockpit/ may import
  from world_engine.
- deposit round-trip in a temp tree (deposit.py pure functions).
- QUESTION writer guard (question_response.py).
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
PIPELINE_COCKPIT_DIR = ROOT / "tooling" / "pipeline_cockpit"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tooling" / "glue"))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_app_imports_and_port() -> None:
    try:
        from tooling.pipeline_cockpit import app as pc_app
    except Exception as e:  # noqa: BLE001
        fail(f"tooling.pipeline_cockpit.app failed to import: {e}")
        return
    if pc_app.PORT != 8100:
        fail(f"PORT constant is {pc_app.PORT!r}, expected 8100")
    if pc_app.PORT == 8000:
        fail("PORT collides with the world cockpit's 8000")


def check_k1_import_boundary() -> None:
    for path in PIPELINE_COCKPIT_DIR.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as e:
            fail(f"{path}: SyntaxError while parsing for K1 scan: {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "world_engine" in alias.name:
                        fail(f"{path}: imports '{alias.name}' — K1 boundary violation")
            elif isinstance(node, ast.ImportFrom):
                if node.module and "world_engine" in node.module:
                    fail(f"{path}: imports from '{node.module}' — K1 boundary violation")


def check_deposit_roundtrip() -> None:
    from tooling.pipeline_cockpit import deposit

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = pathlib.Path(tmp)

        ticket_body = (
            "---\n"
            "id: TICKET-NNNN\n"
            "slug: check-fixture\n"
            "title: fixture\n"
            "---\n"
            "\n# TICKET-NNNN — fixture\n"
        )
        try:
            type_ = deposit.detect_type(ticket_body)
            if type_ != "ticket":
                fail(f"detect_type misclassified fixture ticket body as {type_!r}")
            slug = deposit.extract_slug(ticket_body, type_)
            numbered_body, number = deposit.assign_number(ticket_body, type_, tmp_root, None)
            path = deposit.target_path(type_, number, slug, numbered_body, tmp_root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(numbered_body, encoding="utf-8")

            expected_path = tmp_root / "tooling" / "tickets" / f"TICKET-{number}-check-fixture.md"
            if path != expected_path:
                fail(f"ticket target_path mismatch: got {path}, expected {expected_path}")
            if not expected_path.exists():
                fail(f"ticket deposit did not create {expected_path}")
            written = expected_path.read_text(encoding="utf-8")
            if "NNNN" in written:
                fail("ticket deposit left an unsubstituted NNNN placeholder in the body")
            if f"TICKET-{number}" not in written:
                fail(f"ticket deposit body does not contain the substituted number {number}")
        except Exception as e:  # noqa: BLE001
            fail(f"ticket deposit round-trip raised unexpectedly: {e}")
            return

        recon_body = (
            "<!-- slug: check-fixture -->\n"
            "# RECON — fixture\nSpec: RECON-NNNN-check-fixture.md.\n"
        )
        try:
            r_type = deposit.detect_type(recon_body)
            if r_type != "recon":
                fail(f"detect_type misclassified fixture recon body as {r_type!r}")
            r_slug = deposit.extract_slug(recon_body, r_type)
            r_numbered_body, r_number = deposit.assign_number(recon_body, r_type, tmp_root, number)
            if r_number != number:
                fail(f"recon deposit did not bind to the ticket's number: got {r_number}, expected {number}")
            r_path = deposit.target_path(r_type, r_number, r_slug, r_numbered_body, tmp_root)
            r_path.parent.mkdir(parents=True, exist_ok=True)
            r_path.write_text(r_numbered_body, encoding="utf-8")

            expected_r_path = tmp_root / "tooling" / "recon" / f"RECON-{number}-check-fixture.md"
            if r_path != expected_r_path:
                fail(f"recon target_path mismatch: got {r_path}, expected {expected_r_path}")
            if "NNNN" in r_path.read_text(encoding="utf-8"):
                fail("recon deposit left an unsubstituted NNNN placeholder in the body")
        except Exception as e:  # noqa: BLE001
            fail(f"recon deposit round-trip raised unexpectedly: {e}")


QUESTION_TEMPLATE = (
    "# QUESTION — TICKET-9999\n"
    "Trigger: D1-a\n"
    "## Context\nfixture context\n"
    "## Question\nfixture question?\n"
    "## Options\nnone proposed\n"
    "## Response\n{response}"
)


def check_question_writer_guard() -> None:
    from question_response import (
        MalformedQuestion,
        ResponseAlreadyFilled,
        write_response,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = pathlib.Path(tmp)

        filled_path = tmp_root / "QUESTION-filled.md"
        filled_text = QUESTION_TEMPLATE.format(response="Nia's decision here.\n")
        filled_path.write_text(filled_text, encoding="utf-8")

        try:
            write_response(filled_path, "overwrite attempt")
            fail("write_response did not raise on an already-filled '## Response'")
        except ResponseAlreadyFilled:
            pass
        except Exception as e:  # noqa: BLE001
            fail(f"write_response raised the wrong exception on a filled file: {e}")

        after = filled_path.read_text(encoding="utf-8")
        if after != filled_text:
            fail("write_response mutated a file it should have refused (not byte-identical)")

        empty_path = tmp_root / "QUESTION-empty.md"
        empty_path.write_text(QUESTION_TEMPLATE.format(response=""), encoding="utf-8")

        try:
            write_response(empty_path, "Go with option A.")
        except Exception as e:  # noqa: BLE001
            fail(f"write_response raised unexpectedly on an empty '## Response': {e}")
            return

        if "Go with option A." not in empty_path.read_text(encoding="utf-8"):
            fail("write_response did not write the answer text")

        try:
            write_response(empty_path, "second attempt")
            fail("write_response did not refuse a second write to a now-filled file")
        except ResponseAlreadyFilled:
            pass
        except Exception as e:  # noqa: BLE001
            fail(f"write_response raised the wrong exception on a second write: {e}")

        malformed_path = tmp_root / "QUESTION-malformed.md"
        malformed_path.write_text("# QUESTION — TICKET-9999\nno response header here\n", encoding="utf-8")
        try:
            write_response(malformed_path, "text")
            fail("write_response did not raise MalformedQuestion on a header-less file")
        except MalformedQuestion:
            pass
        except Exception as e:  # noqa: BLE001
            fail(f"write_response raised the wrong exception on a malformed file: {e}")


def main() -> None:
    check_app_imports_and_port()
    check_k1_import_boundary()
    check_deposit_roundtrip()
    check_question_writer_guard()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: pipeline cockpit — port, K1 boundary, deposit round-trip, QUESTION writer guard")
    sys.exit(0)


if __name__ == "__main__":
    main()
