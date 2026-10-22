"""Player profiles (TICKET-0125, K1): the only runtime writer of `user`.

A player profile is a `user` row with `role='player'` (R-07): no schema
change, and `user` is not a canon table, so this writer sits outside the
canon-write gate. Users are not world-scoped: a profile name is unique
among the active players of every world, compared under
`lore_resolve.normalize_surface` on both sides. Nothing here commits; the
caller owns the transaction (INV-18).
"""

from __future__ import annotations

from sqlmodel import Session, select

from ..models import User

MAX_PROFILE_NAME = 80

PROFILE_NAME_REQUIRED = "Le nom est requis."
PROFILE_NAME_TOO_LONG = f"Nom trop long ({MAX_PROFILE_NAME} caractères au plus)."
PROFILE_NAME_TAKEN = "Ce nom de joueur existe déjà."


class ProfileNameTaken(ValueError):
    """An active player profile already carries this name."""


def create_player_profile(db: Session, name: str) -> User:
    """Add and flush one `User(name, role='player')`. `ValueError` on an
    empty or too long name, `ProfileNameTaken` on a duplicate; never
    commits."""
    from ..lore_resolve import normalize_surface

    name = (name or "").strip()
    if not name:
        raise ValueError(PROFILE_NAME_REQUIRED)
    if len(name) > MAX_PROFILE_NAME:
        raise ValueError(PROFILE_NAME_TOO_LONG)
    wanted = normalize_surface(name)
    players = db.exec(
        select(User).where(User.role == "player", User.is_active == True)  # noqa: E712
    ).all()
    if any(normalize_surface(p.name) == wanted for p in players):
        raise ProfileNameTaken(PROFILE_NAME_TAKEN)
    user = User(name=name, role="player")
    db.add(user)
    db.flush()
    return user
