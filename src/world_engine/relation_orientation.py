"""Relation orientation vocabulary (TICKET-0090, BRIEF-0090-a) — pure, no DB.

The single source of the social/structural split of `relation` types
(`RELATION_GRAPH_EXCLUDED_TYPES`, `is_social`) and of the two typed-fact
content templates (`lien_fact_content`, `connects_to_fact_content`).
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
# "connects_to is location map topology, never a social signal" / "controls"
# is a faction-control edge, also never a social signal).
RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to", "controls")


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
