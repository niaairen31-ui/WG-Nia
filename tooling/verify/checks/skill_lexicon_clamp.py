"""G1 check for TICKET-0084 (BRIEF-0084-c) — `skill_lexicon.judge`'s clamp
is total.

Behavioural only: no DB, no model, imports `skill_lexicon.judge` directly
and drives it against a fixed catalogue.

Three assertions, each vacuity-guarded (zero cases exercised is a FAIL):
  1. Every `BASE_SKILL_DOMAINS` member yields verdict `base`.
  2. Every fixed-catalogue skill name yields verdict `matched`.
  3. At least ten hostile inputs all yield verdict `unmatched` with
     `effective_domain == "physical"`, and `judge` never raises.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

FAILURES: list[str] = []

_CATALOGUE = {
    "Crochetage": ("skill-def-1", "agility"),
    "Intimidation": ("skill-def-2", "composure"),
}

_HOSTILE_INPUTS = (
    "",
    "   ",
    "Crochetag",          # near-miss, one character short of a catalogue name
    "CrochetageX",        # near-miss, one character over a catalogue name
    "physical.",          # base domain with a trailing period — not a strip-only match
    "crochetage",         # catalogue name, wrong case (catalogue compare is exact, no lowering)
    '{"domain": "physical"}',   # a JSON fragment
    "x" * 5000,           # a very long string
    "\t\n  ",             # whitespace-only, tabs/newlines
    None,                 # None-ish
    12345,                # non-string
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_base_domains(judge, base_domains) -> None:
    if not base_domains:
        fail("vacuous-proof: zero BASE_SKILL_DOMAINS to exercise")
        return
    for domain in base_domains:
        verdict = judge(domain, base_domains=base_domains, catalogue=_CATALOGUE)
        if verdict.verdict != "base":
            fail(f"skill_lexicon_clamp: base domain {domain!r} yielded verdict {verdict.verdict!r}, expected 'base'")
        elif verdict.base_domain != domain:
            fail(f"skill_lexicon_clamp: base domain {domain!r} yielded base_domain={verdict.base_domain!r}")

        # Case-insensitivity (Scope IN #2): an uppercase base domain still
        # yields 'base', canonicalised to the stored (lowercase) literal.
        upper_verdict = judge(domain.upper(), base_domains=base_domains, catalogue=_CATALOGUE)
        if upper_verdict.verdict != "base" or upper_verdict.base_domain != domain:
            fail(
                f"skill_lexicon_clamp: uppercase base domain {domain.upper()!r} yielded "
                f"verdict={upper_verdict.verdict!r} base_domain={upper_verdict.base_domain!r}, "
                f"expected verdict='base' base_domain={domain!r}"
            )


def check_catalogue_names(judge, base_domains) -> None:
    if not _CATALOGUE:
        fail("vacuous-proof: zero catalogue names to exercise")
        return
    for name, (skill_id, base_domain) in _CATALOGUE.items():
        verdict = judge(name, base_domains=base_domains, catalogue=_CATALOGUE)
        if verdict.verdict != "matched":
            fail(f"skill_lexicon_clamp: catalogue name {name!r} yielded verdict {verdict.verdict!r}, expected 'matched'")
            continue
        if verdict.skill_definition_id != skill_id:
            fail(f"skill_lexicon_clamp: catalogue name {name!r} yielded skill_definition_id={verdict.skill_definition_id!r}")
        if verdict.effective_domain != base_domain:
            fail(f"skill_lexicon_clamp: catalogue name {name!r} yielded effective_domain={verdict.effective_domain!r}, expected {base_domain!r}")


def check_hostile_inputs(judge, base_domains) -> None:
    if len(_HOSTILE_INPUTS) < 10:
        fail("vacuous-proof: fewer than ten hostile inputs configured")
        return
    for raw in _HOSTILE_INPUTS:
        try:
            verdict = judge(raw, base_domains=base_domains, catalogue=_CATALOGUE)
        except Exception as exc:  # noqa: BLE001 — judge must NEVER raise
            fail(f"skill_lexicon_clamp: judge({raw!r}) raised {exc!r} — it must never raise")
            continue
        if verdict.verdict != "unmatched":
            fail(f"skill_lexicon_clamp: hostile input {raw!r} yielded verdict {verdict.verdict!r}, expected 'unmatched'")
        if verdict.effective_domain != "physical":
            fail(f"skill_lexicon_clamp: hostile input {raw!r} yielded effective_domain={verdict.effective_domain!r}, expected 'physical'")


def main() -> int:
    from world_engine.models import BASE_SKILL_DOMAINS
    from world_engine.skill_lexicon import judge

    check_base_domains(judge, BASE_SKILL_DOMAINS)
    check_catalogue_names(judge, BASE_SKILL_DOMAINS)
    check_hostile_inputs(judge, BASE_SKILL_DOMAINS)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: skill_lexicon_clamp — every base domain yields 'base', every catalogue "
        "name yields 'matched', and every hostile input yields 'unmatched'/'physical' "
        "without raising"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
