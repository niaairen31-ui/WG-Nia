"""G1 check: a proposed quest is reviewed in the offer editor (TICKET-0121, BRIEF-0121-F, C-14).

The queue's card of a `quest_offer_creation` proposal edits the very form
the creator writes an offer in, and opens each condition the designer left
waiting on the designer's answer. Static text only, no DB, no Svelte
compiler (the frontend checks' precedent); a file that is missing, or a
pattern that matches nothing, is a FAILURE.

  RC1. `frontend/src/creation/OfferEditor.svelte` exists, renders the
       `ConditionEditor` roles `eligibility`, `prerequisite`, `completion`
       and `failure`, and `QuestTermRow`; `QuestOffers.svelte` renders
       `<OfferEditor` and holds no `role="prerequisite"` of its own (the
       editor is not copied back inline).
  RC2. `ConditionInterpreter.svelte` declares the props `seed` and
       `onsettle`, calls `seededState(` and passes `onsettle` to both
       `insertProposal` and `discardProposal`;
       `conditionInterpreter.svelte.js` exports `seededState`.
  RC3. `QueueCard.svelte` names `quest_offer_creation`, renders
       `<OfferEditor`, posts to `/api/conditions/view`, names
       `is_character`, `has_met`, `flags_confirmed` (through the
       creator's `flagsConfirmed` tick) and `giver_suggestions`, and
       approves with `proposalBody(`.
  RC4. `questOffers.svelte.js` exports `draftFromProposal` and
       `proposalBody`; `proposalBody`'s body copies `request_id`,
       `pending_drafts`, `flags` and `flags_confirmed`.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CREATION = ROOT / "frontend" / "src" / "creation"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(name: str) -> str:
    path = CREATION / name
    if not path.is_file():
        fail(f"{name} is missing")
        return ""
    return path.read_text(encoding="utf-8")


def _need(rule: str, name: str, text: str, pattern: str, what: str) -> None:
    if text and not re.search(pattern, text):
        fail(f"{rule}: {name} -- {what}")


def _function_body(text: str, name: str) -> str:
    """The text of `export function <name>(...) { ... }`, brace-matched."""
    m = re.search(rf"export\s+function\s+{name}\s*\([^)]*\)\s*\{{", text)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i]


def check_rc1() -> None:
    editor = _read("OfferEditor.svelte")
    for role in ("eligibility", "prerequisite", "completion", "failure"):
        _need("RC1", "OfferEditor.svelte", editor, rf"<ConditionEditor[^>]*role=\"{role}\"",
              f"no ConditionEditor with role=\"{role}\"")
    _need("RC1", "OfferEditor.svelte", editor, r"<QuestTermRow\b", "does not render QuestTermRow")
    offers = _read("QuestOffers.svelte")
    _need("RC1", "QuestOffers.svelte", offers, r"<OfferEditor\b", "does not render <OfferEditor")
    if offers and 'role="prerequisite"' in offers:
        fail("RC1: QuestOffers.svelte holds a role=\"prerequisite\" of its own -- the editor is inline again")


def check_rc2() -> None:
    comp = _read("ConditionInterpreter.svelte")
    props = re.search(r"let\s*\{([^}]*)\}\s*=\s*\$props\(\)", comp)
    if comp and not props:
        fail("RC2: ConditionInterpreter.svelte declares no $props()")
    elif props:
        for prop in ("seed", "onsettle"):
            if not re.search(rf"\b{prop}\b", props.group(1)):
                fail(f"RC2: ConditionInterpreter.svelte does not declare the prop `{prop}`")
    _need("RC2", "ConditionInterpreter.svelte", comp, r"seededState\(", "never calls seededState(")
    _need("RC2", "ConditionInterpreter.svelte", comp, r"insertProposal\([^)]*\bonsettle\)",
          "insertProposal is not passed onsettle")
    _need("RC2", "ConditionInterpreter.svelte", comp, r"discardProposal\([^)]*\bonsettle\)",
          "discardProposal is not passed onsettle")
    store = _read("conditionInterpreter.svelte.js")
    _need("RC2", "conditionInterpreter.svelte.js", store, r"export\s+function\s+seededState\s*\(",
          "does not export seededState")


def check_rc3() -> None:
    card = _read("QueueCard.svelte")
    for pattern, what in (
        (r"'quest_offer_creation'", "names no quest_offer_creation"),
        (r"<OfferEditor\b", "does not render <OfferEditor"),
        (r"'/api/conditions/view'", "never posts to /api/conditions/view"),
        (r"'is_character'", "names no is_character"),
        (r"'has_met'", "names no has_met"),
        (r"flags_confirmed", "names no flags_confirmed"),
        (r"bind:checked=\{flagsConfirmed\}", "flagsConfirmed is not the creator's own tick"),
        (r"giver_suggestions", "names no giver_suggestions"),
        (r"proposalBody\(", "does not approve with proposalBody("),
    ):
        _need("RC3", "QueueCard.svelte", card, pattern, what)


def check_rc4() -> None:
    store = _read("questOffers.svelte.js")
    if not store:
        return
    _need("RC4", "questOffers.svelte.js", store, r"export\s+function\s+draftFromProposal\s*\(",
          "does not export draftFromProposal")
    body = _function_body(store, "proposalBody")
    if not body:
        fail("RC4: questOffers.svelte.js does not export proposalBody")
        return
    keys = re.search(r"REVIEW_KEYS\s*=\s*\[([^\]]*)\]", store)
    copied = body + (keys.group(1) if keys and "REVIEW_KEYS" in body else "")
    for key in ("request_id", "pending_drafts", "flags", "flags_confirmed"):
        if not re.search(rf"\b{key}\b", copied):
            fail(f"RC4: proposalBody does not copy `{key}`")


def main() -> int:
    check_rc1()
    check_rc2()
    check_rc3()
    check_rc4()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: quest_review_card -- the offer editor is one component shared by « Quêtes » and the "
          "review card; a designer's waiting condition opens seeded and settles; the card names the "
          "giver suggestions, « a rencontré », « Quête unique », the creator's own confirmation, and "
          "approves the edited offer with its review keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
