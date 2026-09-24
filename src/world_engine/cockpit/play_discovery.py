"""Engine discovery proposal (TICKET-0091 BRIEF-B, pure move).

`_propose_engine_discovery` moved verbatim out of `cockpit/play.py` for
its module budget; `play_physical.py` imports it from here. It only stages
a `proposed_mutation` row — never auto-applied.
"""

from __future__ import annotations

from sqlmodel import Session

from ..models import Conversation, DiscoverableDetail, ProposedMutation


def _propose_engine_discovery(
    conv: "Conversation",
    detail: "DiscoverableDetail",
    db: "Session",
) -> None:
    """Propose a new_knowledge mutation with proposed_by='engine'.

    Fires deterministically when a perception search finds an undiscovered
    hidden detail. Goes through the normal review pipeline — never auto-applied.
    The discoverable_detail_id back-reference in the payload lets _apply_mutation
    flip detail.discovered to TRUE when the creator approves (see that branch).
    """
    db.add(ProposedMutation(
        world_id=conv.world_id,
        source_type="conversation",
        conversation_id=conv.id,
        mutation_type="new_knowledge",
        target_table="entity",
        target_id=conv.player_id,
        payload={
            "entity_id": conv.player_id,
            "subject": detail.subject,
            "level": "knows",
            "content": detail.content,
            "source": "discovery",
            "is_secret": False,
            "discoverable_detail_id": detail.id,
        },
        rationale=(
            f"Perception search in location {conv.location_id!r}: "
            f"detail '{detail.subject}' found."
        ),
        proposed_by="engine",
    ))
