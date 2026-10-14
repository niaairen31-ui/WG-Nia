"""Who proposed a change: the closed list of `proposed_mutation.proposed_by` values, what each one is, and how the creator's dashboard names it (TICKET-0115, BRIEF-0115-C; decision B2 of the conditions series' dashboard).

`proposed_by` is the producer column (B2): every producer stamps its own
value, and `proposal_producers.py` (the check) holds every value written in
`src/` to this list -- a new producer is a red gate until it is named here.

`PRODUCERS` -- each value written today: its kind (`model`, a local model
proposed it; `engine`, code proposed it, no model; `auto`, code applied it
at once, INV-15) and its French label. `LEGACY_PRODUCERS` -- values older
rows still carry and nothing writes any more: the dashboard names them,
never mixes them with a live producer.
"""

from __future__ import annotations

PRODUCERS: dict[str, tuple[str, str]] = {
    "local_ai_window": ("model", "Play — analyse de fenêtre"),
    "local_ai_overhearing": ("model", "Play — ce qui est entendu"),
    "local_ai_tick": ("model", "Tick du monde"),
    "local_ai": ("model", "Journée — modèle"),
    "local_ai_quest_designer": ("model", "Journée — concepteur de quêtes"),
    "observed_scene": ("model", "Scène observée"),
    "engine": ("engine", "Moteur — sans modèle"),
    "engine_roll": ("auto", "Jet de Play — appliqué d'office"),
}
LEGACY_PRODUCERS: dict[str, str] = {
    "local_ai_immediate": "Ancienne analyse par réplique",
    "interpretation": "Ancienne interprétation de /say",
    "claude": "Claude (ancien)",
    "creator": "Créatrice (ancien)",
}
PRODUCER_KINDS: tuple[str, ...] = ("model", "engine", "auto")
UNKNOWN_PRODUCER_FR = "Producteur inconnu"


def producer_label(value: str | None) -> str:
    """The dashboard's name for a `proposed_by` value."""
    if value in PRODUCERS:
        return PRODUCERS[value][1]
    return LEGACY_PRODUCERS.get(value or "", UNKNOWN_PRODUCER_FR)


def producer_kind(value: str | None) -> str | None:
    """`model`, `engine` or `auto` for a live producer; None otherwise."""
    return PRODUCERS[value][0] if value in PRODUCERS else None
