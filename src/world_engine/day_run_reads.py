"""What the day's run looks like: its failures, what awaits publication, what a character may still declare (TICKET-0128).

Reads only. A day module (INV-71): every read is scoped by the world or
the day it is given, never by the active world.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Batch, DayRunFailure, Entity, PassPlay
from .models import Session as GameSession

STAGE_LABELS_FR = {"plan": "Plan", "resolve": "Résolution"}
CODE_LABELS_FR = {
    "model_failed": "Modèle indisponible ou réponse illisible",
    "blocked": "Bloquée : quelque chose est à régler dans le monde",
    "rejected": "Récit refusé par le juge",
    "refused": "Refusée",
    "crashed": "Erreur inattendue",
    "interrupted": "Interrompue (serveur arrêté)",
}


def latest_failure(db: Session, pass_play_id: str) -> Optional[DayRunFailure]:
    """The day's most recent failure (`created_at`, then `id`), or None."""
    return db.exec(
        select(DayRunFailure)
        .where(DayRunFailure.pass_play_id == pass_play_id)
        .order_by(DayRunFailure.created_at.desc(), DayRunFailure.id.desc())
    ).first()


def failed_days(db: Session, world_id: str) -> list[dict]:
    """The world's `flagged` days, newest failure first, each read from its
    latest failure."""
    rows = db.exec(
        select(Batch, PassPlay, Entity.name)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .join(Entity, Entity.id == PassPlay.character_id)
        .where(GameSession.world_id == world_id, PassPlay.status == "flagged")
    ).all()
    out: list[tuple] = []
    for batch, pass_play, character_name in rows:
        failure = latest_failure(db, pass_play.id)
        if failure is None:
            continue
        out.append((failure.created_at, failure.id, {
            "batch_id": batch.id,
            "day_number": batch.day_number,
            "character_name": character_name,
            "declared_action": pass_play.declared_action,
            "stage": failure.stage,
            "stage_label": STAGE_LABELS_FR[failure.stage],
            "code": failure.code,
            "code_label": CODE_LABELS_FR[failure.code],
            "reason": failure.reason,
            "failed_at": failure.created_at.isoformat() if failure.created_at else None,
        }))
    out.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in out]
