"""G1 check: the modal-dialog convergence lock (TICKET-0059, BRIEF-0059-l
item 10).

BRIEF-0059-h landed frontend/src/creation/Modal.svelte (lock O1) but
deliberately withheld this lock: the legacy generic modal
(genericModalOpen/genericModalClose, index.html) was still alive, competing
with it as a second real implementation. BRIEF-0059-l commit 3 retires that
legacy implementation (world create/delete, its last consumers, converge
onto Modal.svelte too) -- this is the lock that was withheld until then.

The rule: no `.svelte` file other than Modal.svelte may contain BOTH the
token `modal-backdrop` AND `modal-container` -- the two classes that
together are Modal.svelte's own backdrop-plus-panel shape (a
`.modal-backdrop` div wrapping a `.modal-container` div). Either token
alone is fine (a file may reuse one class for something unrelated); it is
the COMBINATION that reproduces this primitive. No allow-list: any second
file constructing this shape is a failure, whoever it is.

Same idiom as location_tree.py/effect_self_write.py: module-level FAILURES
list, fail(), _report_and_exit(), ROOT via parents[3], stdlib only, no DB,
no subprocess, textual scanning rather than a real Svelte parser (this
project has none). The vacuity guard sits on the SCAN, exactly as the brief
specifies: zero `.svelte` files collected, or Modal.svelte itself absent,
is a FAILURE, never a trivially-satisfied "nothing to check."
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
MODAL_FILE = FRONTEND_SRC / "creation" / "Modal.svelte"

BACKDROP_TOKEN = "modal-backdrop"
CONTAINER_TOKEN = "modal-container"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(scanned: int | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: modal_primitive — {scanned} .svelte file(s) scanned, "
        f"Modal.svelte confirmed present, 0 duplicate backdrop-plus-panel "
        f"dialog(s) found"
    )
    sys.exit(0)


def main() -> None:
    if not FRONTEND_SRC.is_dir():
        fail(f"vacuous scan: {FRONTEND_SRC} is not a directory")
        _report_and_exit()
        return

    svelte_files = sorted(FRONTEND_SRC.rglob("*.svelte"))
    if not svelte_files:
        fail("vacuous scan: zero .svelte files under frontend/src/")
        _report_and_exit()
        return

    if not MODAL_FILE.is_file():
        fail(f"{MODAL_FILE} does not exist — the modal-dialog primitive is absent")
        _report_and_exit()
        return

    for path in svelte_files:
        if path == MODAL_FILE:
            continue
        text = path.read_text(encoding="utf-8")
        if BACKDROP_TOKEN in text and CONTAINER_TOKEN in text:
            rel = path.relative_to(ROOT).as_posix()
            fail(
                f"{rel}: contains both {BACKDROP_TOKEN!r} and {CONTAINER_TOKEN!r} — "
                "a second backdrop-plus-panel dialog implementation"
            )

    _report_and_exit(len(svelte_files))


if __name__ == "__main__":
    main()
