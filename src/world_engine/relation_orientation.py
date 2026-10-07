"""Relation orientation vocabulary (TICKET-0090, BRIEF-0090-a) — pure, no DB.

The single source of the social/structural split of `relation` types
(`RELATION_GRAPH_EXCLUDED_TYPES`, `is_social`) and of the two typed-fact
content templates (`lien_fact_content`, `connects_to_fact_content`,
`borde_fact_content`) and of the map-topology pair (`MAP_TOPOLOGY_TYPES`).
`context.py` re-imports `RELATION_GRAPH_EXCLUDED_TYPES` from here, so every
existing importer of `context.RELATION_GRAPH_EXCLUDED_TYPES` keeps working
and the constant is never re-typed.

A social relation is one perceiver's feeling toward one target: `entity_a`
feels, `entity_b` receives, `direction = 'a_to_b'` always. `orient_legacy`
maps a legacy (`direction`, `visible_to_b`) row onto that shape — the closed
case table of the lot's C-04.
"""

from __future__ import annotations

from dataclasses import dataclass

# Structural exclusion shared by every world-wide relation scan (CLAUDE.md:
# "connects_to and borde are location map topology, never a social signal" /
# "controls" is a faction-control edge, also never a social signal).
RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to", "borde", "controls")

# The two geographic link types (TICKET-0101, L1). `connects_to` joins two
# visitable locations and is the only traversable link; `borde` is the link
# whenever a zone is an endpoint. The type is derived from the endpoints
# (`zone_rules.geographic_link_type`), never chosen by the creator.
MAP_TOPOLOGY_TYPES: tuple[str, str] = ("connects_to", "borde")

# Relation types no path may write any more (TICKET-0110, BRIEF-0110-A, I2):
# « X owes Y » lives in the `debt` table alone, never in a relation's type.
# `write_relation` refuses them; no row of production carried one when the
# type was retired (Nia's query, 2026-10-07).
RETIRED_RELATION_TYPES: tuple[str, ...] = ("debt",)


def is_social(relation_type: str) -> bool:
    """True for a social relation type; False for a structural one or None."""
    if relation_type is None:
        return False
    return relation_type not in RELATION_GRAPH_EXCLUDED_TYPES


def lien_fact_content(name_a: str, relation_type: str, name_b: str) -> str:
    """Content of a social relation's typed `lien` fact. No validation."""
    return f"{name_a} éprouve « {relation_type} » envers {name_b}."


def connects_to_fact_content(name_a: str, name_b: str) -> str:
    """Content of a `connects_to` edge's typed fact — byte-identical to
    `scripts/migrate_v2_00_connects_to_facts.py`'s for the same arguments;
    `write_relation` passes identity tokens (BRIEF-0091-J), the migration
    plain names."""
    return f"{name_a} communique avec {name_b}."


def borde_fact_content(name_a: str, name_b: str) -> str:
    """Content of a `borde` edge's typed fact (TICKET-0101) — the sibling of
    `connects_to_fact_content`, same arguments, same `knows` default."""
    return f"{name_a} borde {name_b}."


@dataclass(frozen=True)
class OrientedSpec:
    perceiver_id: str
    target_id: str
    target_knows: bool
    visibility_ambiguous: bool


def orient_legacy(
    direction: str, entity_a_id: str, entity_b_id: str, visible_to_b: bool
) -> list[OrientedSpec]:
    """Normalize a legacy social row into one oriented spec per perceiver.

    `a_to_b` keeps its endpoints and turns `visible_to_b` into
    `target_knows`; `b_to_a` swaps them, and a TRUE `visible_to_b` there has
    no defined meaning (`visibility_ambiguous`, never converted); `mutual`
    splits into two specs. Any other value raises `ValueError`.
    """
    a, b = entity_a_id, entity_b_id
    if direction == "a_to_b":
        return [OrientedSpec(a, b, bool(visible_to_b), False)]
    if direction == "b_to_a":
        return [OrientedSpec(b, a, False, bool(visible_to_b))]
    if direction == "mutual":
        return [OrientedSpec(a, b, False, False), OrientedSpec(b, a, False, False)]
    raise ValueError(f"orient_legacy: unknown direction {direction!r}")
