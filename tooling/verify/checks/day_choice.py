"""G1 check for TICKET-0094 — Concordance H2, the model chooses and the code
judges. Created by BRIEF-0094-A with the near cases; BRIEF-0094-B adds the
narrowing and the judge; BRIEF-0094-C adds the call; BRIEF-0094-D adds the
static route rules.

N1 -- `near_in_surfaces` (C-03) scores a typo and a shared token like
   `near_candidates` does: "Maelys" -> Maelis 83; "reine" -> La Reine Grise
   63, Reine Ysolde 59.
N2 -- `exclude_ids` drops an entity from the result.
N3 -- every category counts: a location surface is returned with its
   `entity_type`; the caller filters.

Pure cases on hand-built `NameSurface` tuples, no DB. Vacuity guard: N1 must
have produced candidates. FAILURES list, print FAIL lines, exit 1.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _surfaces():
    from world_engine.name_index import NameSurface

    def name(text: str, entity_id: str, entity_type: str) -> NameSurface:
        return NameSurface(text=text, entity_id=entity_id, entity_name=text, entity_type=entity_type,
                           source="name", fact_id=None)

    return (
        name("Maelis", "m", "character"),
        name("La Reine Grise", "g", "character"),
        name("Reine Ysolde", "y", "character"),
        name("Porte de Vesk", "p", "location"),
    )


def check_near() -> int:
    from world_engine.lore_resolve import near_in_surfaces

    surfaces = _surfaces()

    def scored(found):
        return [(c.entity_id, c.score) for c in found]

    maelys = scored(near_in_surfaces("Maelys", surfaces))
    if maelys != [("m", 83)]:
        fail(f"N1: 'Maelys' -> {maelys}, expected [('m', 83)]")
    reine = scored(near_in_surfaces("reine", surfaces))
    if reine != [("g", 63), ("y", 59)]:
        fail(f"N1: 'reine' -> {reine}, expected [('g', 63), ('y', 59)]")

    excluded = scored(near_in_surfaces("reine", surfaces, exclude_ids=frozenset({"g"})))
    if excluded != [("y", 59)]:
        fail(f"N2: 'reine' excluding g -> {excluded}, expected [('y', 59)]")

    vesk = near_in_surfaces("Vesk", surfaces)
    if not any(c.entity_id == "p" and c.entity_type == "location" for c in vesk):
        fail(f"N3: 'Vesk' -> {[(c.entity_id, c.entity_type) for c in vesk]}, expected p as a location")

    return len(maelys) + len(reine)


def main() -> int:
    if check_near() == 0:
        fail("vacuity: N1 produced no candidates")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: day_choice — near_in_surfaces scores typos and shared tokens, honours "
        "exclude_ids, and returns every category (N1-N3)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
