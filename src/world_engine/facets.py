"""The facet registry (TICKET-0091, BRIEF-0091-A, contract C-01).

A facet says what kind of statement a `fact` is. The vocabulary is code, not
schema: `fact.facet` is free TEXT with no CHECK (Q2a) and this module is the
single authority on which names exist. Per facet it declares the family, the
granularity (`bloc` = one fact per entity; `affirmation` = one fact per
statement; `typed` = the fact IS a relation/event/world_law row), the
default-knowledge preset applied to NEW writing, a French label and a French
one-line description (UI help and future extractor vocabulary; no check reads
them), and the known aspects — a suggestion list, never a closed set (Q12d).

`FACETS` insertion order is the display order. This module imports nothing
from `models` or `writes`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

FAMILIES = ("identite", "interiorite", "collectif", "monde")
GRANULARITIES = ("bloc", "affirmation", "typed")
PRESETS = ("none", "world", "public_world", "location", "rencontre", "typed")


@dataclass(frozen=True)
class FacetSpec:
    name: str
    family: str          # in FAMILIES
    granularity: str     # in GRANULARITIES
    preset: str          # in PRESETS — default knowledge for NEW writing
    label: str           # French UI label
    description: str     # one French sentence: what belongs here
    aspects: tuple[str, ...] = ()   # known aspects, suggestion only


_SPECS = (
    FacetSpec("appellation", "identite", "affirmation", "rencontre", "Appellations",
              "Un nom, surnom ou titre sous lequel on désigne l'entité."),
    FacetSpec("statut", "identite", "affirmation", "location", "Statuts",
              "Une position sociale, une charge ou un rang que l'entité occupe."),
    FacetSpec("physique", "identite", "bloc", "rencontre", "Physique",
              "Ce que l'on voit durablement de l'entité : corps, visage, allure."),
    FacetSpec("tenue", "identite", "bloc", "none", "Tenue",
              "Ce que l'entité porte en ce moment et qui peut changer."),
    FacetSpec("description", "identite", "bloc", "public_world", "Description",
              "La présentation générale de l'entité."),
    FacetSpec("reputation", "identite", "affirmation", "location", "Réputation",
              "Ce qui se dit de l'entité, vrai ou non."),
    FacetSpec("histoire", "interiorite", "affirmation", "none", "Histoire",
              "Un fait du passé de l'entité."),
    FacetSpec("personnalite", "interiorite", "affirmation", "none", "Personnalité",
              "Un trait de caractère de l'entité."),
    FacetSpec("preference", "interiorite", "affirmation", "none", "Préférences",
              "Une chose que l'entité aime ou recherche."),
    FacetSpec("aversion", "interiorite", "affirmation", "none", "Aversions",
              "Une chose que l'entité rejette, craint ou fuit."),
    FacetSpec("doctrine", "collectif", "bloc", "world", "Doctrine",
              "Le credo affiché et les valeurs revendiquées publiquement."),
    FacetSpec("organisation", "collectif", "bloc", "none", "Organisation",
              "La forme d'organisation du groupe telle qu'on peut la connaître."),
    FacetSpec("tension", "collectif", "affirmation", "none", "Tensions",
              "Une fracture, une rivalité ou une faiblesse interne du groupe."),
    FacetSpec("visee", "collectif", "affirmation", "none", "Visées",
              "Un but que le groupe poursuit réellement."),
    FacetSpec("coutume", "collectif", "affirmation", "location", "Coutumes",
              "Un usage, une valeur ou une règle de vie propre au lieu.", ("values",)),
    FacetSpec("information", "monde", "affirmation", "none", "Informations",
              "Une information détenue par quelqu'un."),
    FacetSpec("lien", "monde", "typed", "typed", "Liens",
              "Un lien entre deux entités, porté par une relation."),
    FacetSpec("evenement", "monde", "typed", "typed", "Événements",
              "Un événement du monde."),
    FacetSpec("loi", "monde", "typed", "typed", "Lois",
              "Une loi du monde."),
)

FACETS: dict[str, FacetSpec] = {spec.name: spec for spec in _SPECS}

DESCRIPTIVE_FACETS: frozenset[str] = frozenset(
    name for name, spec in FACETS.items()
    if spec.family in ("identite", "interiorite", "collectif")
)
KNOWLEDGE_SECTION_FACETS: frozenset[str] = frozenset(
    {"information", "lien", "evenement", "loi"})
TYPED_FACET_BY_FK = {"relation_id": "lien", "event_id": "evenement",
                     "world_law_id": "loi"}


def facet_spec(name: str) -> FacetSpec:
    """The spec of facet `name`; `ValueError` if the name is not registered."""
    spec = FACETS.get(name)
    if spec is None:
        raise ValueError(f"unknown facet {name!r}")
    return spec


def normalize_aspect(raw: Optional[str]) -> Optional[str]:
    """Strip and casefold an aspect; empty or `None` becomes `None`."""
    if raw is None:
        return None
    value = raw.strip().casefold()
    return value or None
