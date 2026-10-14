"""G1 check: a quest request is worked from the review queue, its lore from the Lore panel (TICKET-0121, BRIEF-0121-G, C-14).

« Demandes de quête » is a child of the review queue, never an island of
its own; an existence answer is written through the Lore « Écrire » panel,
whose commit carries the request and runs the designer again. Static text
only, no DB, no Svelte compiler (the frontend checks' precedent); a file
that is missing, or a pattern that matches nothing, is a FAILURE.

  RP1. `Queue.svelte` imports `QuestRequests.svelte` and renders
       `<QuestRequests`; `QuestRequests.svelte` names the five statuses'
       French labels (« à concevoir », « question d'existence »,
       « à écrire dans Lore », « proposée », « déjà couverte par ») and
       the three existence answers' values `exists`, `absent`, `already`.
  RP2. `questRequests.svelte.js` calls the four routes of C-12 --
       `/api/quest-requests`, `.../design`, `.../answer`, `.../drop` --
       and `navigate('lore')`.
  RP3. `writePanel.svelte.js`'s `commit()` sends `quest_request_id` in the
       commit body and posts to `/api/quest-requests/.../design` after it;
       `blank()` holds `questRequestId`.
  RP4. `Lore.svelte` has a `$effect` that reads `writeState.questRequestId`
       and sets `loreTab = 'write'`.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "frontend" / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(rel: str) -> str:
    path = SRC / rel
    if not path.is_file():
        fail(f"{rel} is missing")
        return ""
    return path.read_text(encoding="utf-8")


def _need(rule: str, name: str, text: str, pattern: str, what: str) -> None:
    if text and not re.search(pattern, text):
        fail(f"{rule}: {name} -- {what}")


def _block(text: str, opener: str) -> str:
    """The brace-matched body that follows the first match of `opener` (ending in `{`)."""
    m = re.search(opener, text)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i]


def check_rp1() -> None:
    queue = _read("creation/Queue.svelte")
    _need("RP1", "Queue.svelte", queue, r"import\s+QuestRequests\s+from\s+'\./QuestRequests\.svelte'",
          "does not import QuestRequests.svelte")
    _need("RP1", "Queue.svelte", queue, r"<QuestRequests\b", "does not render <QuestRequests")
    panel = _read("creation/QuestRequests.svelte")
    for label in ("à concevoir", "question d'existence", "à écrire dans Lore", "proposée",
                  "déjà couverte par"):
        _need("RP1", "QuestRequests.svelte", panel, re.escape(label), f"names no « {label} »")
    for answer in ("exists", "absent", "already"):
        _need("RP1", "QuestRequests.svelte", panel, rf"'{answer}'", f"names no answer '{answer}'")


def check_rp2() -> None:
    store = _read("creation/questRequests.svelte.js")
    for pattern, what in (
        (r"'/api/quest-requests'", "never reads /api/quest-requests"),
        (r"/api/quest-requests/\$\{id\}/design", "never posts .../design"),
        (r"/api/quest-requests/\$\{id\}/answer", "never posts .../answer"),
        (r"/api/quest-requests/\$\{id\}/drop", "never posts .../drop"),
        (r"navigate\('lore'\)", "never calls navigate('lore')"),
    ):
        _need("RP2", "questRequests.svelte.js", store, pattern, what)


def check_rp3() -> None:
    store = _read("lore/writePanel.svelte.js")
    if not store:
        return
    blank = _block(store, r"function\s+blank\s*\(\s*\)\s*\{")
    if not re.search(r"\bquestRequestId\s*:", blank):
        fail("RP3: writePanel.svelte.js -- blank() holds no questRequestId")
    commit = _block(store, r"export\s+function\s+commit\s*\(\s*\)\s*\{")
    if not commit:
        fail("RP3: writePanel.svelte.js does not export commit()")
        return
    sent = re.search(r"'/api/lore/write/commit'\s*,\s*\{([^}]*)\}", commit)
    if not sent or not re.search(r"\bquest_request_id\s*:", sent.group(1)):
        fail("RP3: writePanel.svelte.js -- the commit body does not send quest_request_id")
    design = re.search(r"/api/quest-requests/\$\{\w+\}/design", commit)
    if not design:
        fail("RP3: writePanel.svelte.js -- commit() never posts .../design")
    elif sent and design.start() < sent.start():
        fail("RP3: writePanel.svelte.js -- commit() posts .../design before the commit")


def check_rp4() -> None:
    lore = _read("lore/Lore.svelte")
    if not lore:
        return
    bodies = []
    rest = lore
    while True:
        m = re.search(r"\$effect\(\s*\(\)\s*=>\s*\{", rest)
        if not m:
            break
        body = _block(rest, r"\$effect\(\s*\(\)\s*=>\s*\{")
        bodies.append(body)
        rest = rest[m.end():]
    if not bodies:
        fail("RP4: Lore.svelte has no $effect")
        return
    if not any("writeState.questRequestId" in b and re.search(r"loreTab\s*=\s*'write'", b) for b in bodies):
        fail("RP4: Lore.svelte -- no $effect reads writeState.questRequestId and sets loreTab = 'write'")


def main() -> int:
    check_rp1()
    check_rp2()
    check_rp3()
    check_rp4()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: quest_request_panel -- « Demandes de quête » is rendered by the review queue with its "
          "statuses and existence answers, calls the four request routes and opens Lore; the writing "
          "panel's commit carries the request and designs after it; Lore opens « Écrire » on the hand-off")
    return 0


if __name__ == "__main__":
    sys.exit(main())
