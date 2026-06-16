"""Physical-action dice resolution (BRIEF-11, schema v1.23).

Pure function, no DB or model access — the roll is computed in Python, never
by the local model. `_arbitrate` (cockpit/app.py) classifies the action into
a domain and optional NPC opposition; this module turns that classification
into a mechanical verdict.

Player-roll rule (verbatim): The roll always belongs to the player. When an
NPC initiates a physical action against the player, we do not roll the NPC's
attempt — we roll the player's response (dodge, resist, endure), with the NPC
tier as opposition. One mechanic, one code path, one audit point.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import randint


@dataclass(frozen=True)
class Verdict:
    domain: str
    dice: tuple[int, int]
    modifier: int
    total: int
    band: str  # "failure" | "partial" | "success"


def resolve_physical(domain: str, player_tier: int, npc_tier: int = 0) -> Verdict:
    """Roll 2d6 + (player_tier - npc_tier) and band the result.

    Bands: <= 6 -> "failure", 7-9 -> "partial", >= 10 -> "success".
    """
    dice = (randint(1, 6), randint(1, 6))
    modifier = player_tier - npc_tier
    total = sum(dice) + modifier

    if total <= 6:
        band = "failure"
    elif total <= 9:
        band = "partial"
    else:
        band = "success"

    return Verdict(domain=domain, dice=dice, modifier=modifier, total=total, band=band)
