"""The indicative unit of a quest (TICKET-0109, BRIEF-0109-B, C1/E1,
contract C-03). Reads only.

Every term is worth some units: money 1 a coin, a relation point 1, a fact
5, a skill 20 (learned, taught, or a reward of points) -- a world changes
any of them in `quest_economy`; an item is worth its own `value` a piece.
`offer_value` adds the costs and the rewards and says whether the reward
lies in the world's band (by default 100 % to 150 % of the cost). The unit
is a display for the creator, never a currency: nothing converts it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .models import Item, QuestEconomy

# The code's defaults (E1); a NULL column of `quest_economy` reads these.
DEFAULT_RATES: dict[str, int] = {
    "rate_money": 1, "rate_relation": 1, "rate_fact": 5, "rate_skill": 20,
    "band_low_pct": 100, "band_high_pct": 150,
}

# The verdict of a reward against the band, as the editor shows it.
VERDICT_LABELS: dict[str, str] = {
    "balanced": "équilibrée", "generous": "généreuse", "meagre": "maigre", "free": "sans coût",
}


@dataclass(frozen=True)
class OfferValue:
    cost: int
    reward: int
    ratio_pct: Optional[int]
    band_low_pct: int
    band_high_pct: int
    verdict: str


def world_rates(db: Session, world_id: str) -> dict[str, int]:
    """The world's rates, each NULL column or a missing row at its default."""
    row = db.exec(select(QuestEconomy).where(QuestEconomy.world_id == world_id)).first()
    return {name: (getattr(row, name) if row is not None and getattr(row, name) is not None else default)
            for name, default in DEFAULT_RATES.items()}


def term_value(db: Session, term, rates: dict[str, int]) -> int:
    """The units of one term (an offer's or a quest's)."""
    if term.currency == "money":
        return (term.amount or 0) * rates["rate_money"]
    if term.currency == "relation":
        return (term.amount or 0) * rates["rate_relation"]
    if term.currency == "fact":
        return rates["rate_fact"]
    if term.currency == "skill":
        return rates["rate_skill"]
    item = db.get(Item, term.item_id) if term.item_id else None
    return (term.amount or 0) * (item.value if item is not None else 0)


def offer_value(db: Session, world_id: str, terms: list) -> OfferValue:
    """The two totals, the reward as a percentage of the cost, and the
    verdict: `free` (no cost), `meagre` (below the band), `generous` (above
    it), else `balanced`."""
    rates = world_rates(db, world_id)
    cost = sum(term_value(db, t, rates) for t in terms if t.direction == "cost")
    reward = sum(term_value(db, t, rates) for t in terms if t.direction == "reward")
    low, high = rates["band_low_pct"], rates["band_high_pct"]
    if cost == 0:
        return OfferValue(cost, reward, None, low, high, "free")
    ratio = round(reward * 100 / cost)
    verdict = "meagre" if ratio < low else "generous" if ratio > high else "balanced"
    return OfferValue(cost, reward, ratio, low, high, verdict)


def value_dict(value: OfferValue) -> dict:
    return {"cost": value.cost, "reward": value.reward, "ratio_pct": value.ratio_pct,
            "band_low_pct": value.band_low_pct, "band_high_pct": value.band_high_pct,
            "verdict": value.verdict, "verdict_label": VERDICT_LABELS[value.verdict]}
