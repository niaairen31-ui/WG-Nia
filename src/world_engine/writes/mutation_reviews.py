"""The creator's review of a proposal, recorded round by round -- the one writer of `mutation_review`, `mutation_review_change` and `proposed_mutation.original_payload` (TICKET-0115, BRIEF-0115-B; decisions A3, C1 and H1a of the conditions series' dashboard).

The four review paths of `cockpit/routes/mutations.py` (approve, reject,
and both in batch) call `record_review` once per proposal they move, after
setting its status and before their commit, with a `ReviewCall` built
before anything was applied:

- `action` `approve` | `reject`, `via` `unit` | `batch`;
- `before_payload`: the payload stored before the call -- a copy taken
  before an edited one replaced it;
- `step_verdict`: `review_verdict.step_verdict`, judged before the apply.

`record_review` writes the next round (1 + the proposal's rounds so far),
its status after the call, and -- for a unit approve only, the one call
that carries a payload -- every value the creator changed
(`review_diff.diff_payloads`), `edited` saying whether there was any. The
first edited round also keeps the producer's payload in `original_payload`,
never written again. Nothing here commits or deletes; the caller owns the
transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from ..models import (
    REVIEW_ACTIONS,
    REVIEW_STATUSES,
    REVIEW_VIAS,
    STEP_VERDICTS,
    MutationReview,
    MutationReviewChange,
    ProposedMutation,
)
from ..review_diff import diff_payloads


@dataclass(frozen=True)
class ReviewCall:
    action: str
    via: str
    before_payload: Any
    step_verdict: Optional[str] = None


def record_review(db: Session, mutation: ProposedMutation, call: ReviewCall) -> MutationReview:
    """Write one round of `mutation`'s review (see the module docstring).
    `ValueError`, nothing written, on an action, via, status or verdict
    outside its tuple, or a reject that did not leave `rejected`."""
    if call.action not in REVIEW_ACTIONS or call.via not in REVIEW_VIAS:
        raise ValueError(f"mutation_review: unknown action or via {call.action!r}/{call.via!r}")
    if mutation.status not in REVIEW_STATUSES or (call.action == "reject") != (mutation.status == "rejected"):
        raise ValueError(f"mutation_review: a {call.action} cannot leave the status {mutation.status!r}")
    if call.step_verdict is not None and call.step_verdict not in STEP_VERDICTS:
        raise ValueError(f"mutation_review: unknown step verdict {call.step_verdict!r}")
    changes = diff_payloads(call.before_payload, mutation.payload) \
        if (call.action, call.via) == ("approve", "unit") else []
    rounds = db.exec(select(func.count()).select_from(MutationReview)
                     .where(MutationReview.mutation_id == mutation.id)).one()
    review = MutationReview(
        world_id=mutation.world_id, mutation_id=mutation.id, round=rounds + 1, action=call.action, via=call.via,
        status_after=mutation.status, edited=bool(changes), step_verdict=call.step_verdict,
    )
    db.add(review)
    db.flush()
    for change in changes:
        db.add(MutationReviewChange(
            world_id=mutation.world_id, review_id=review.id, path=change.path, field=change.field,
            kind=change.kind, before_value=change.before_value, after_value=change.after_value,
        ))
    if changes and mutation.original_payload is None:
        mutation.original_payload = call.before_payload
        db.add(mutation)
    return review
