"""The dashboard's export: everything a deeper analysis needs, between two real-world dates, as one JSON document for a Claude Code session (TICKET-0115, BRIEF-0115-D; decisions E2, I1, J1 and M1 of the conditions series' dashboard).

`build_export(db, scope) -> dict` -- reads only:

- `proposals`: every `proposed_mutation` proposed in the scope (its
  `proposed_at`), each with its world's name, producer and label, type,
  status, dates, rationale, creator notes, `payload` (as approved, or as
  proposed while unreviewed), `original_payload` (as the producer wrote it,
  when the creator edited it), and its review rounds with their changes;
- `interpreter`: every `condition_draft` created in the scope, whole --
  instruction, outcome, payload (notes, errors, proposed vocabulary) and
  model calls;
- `metrics`: `dashboard_metrics.compute_metrics` on the same scope;
  `deferrals`: `dashboard_deferrals.deferral_dicts`.

M1: the JSON columns the « Suivi » tab never reads are here, for the
analysis -- IA2, A2 and the missing label (`dashboard_deferrals.EXPORT`)
are measured from them. The export holds the world's secrets and the
creator's notes: the tab says so beside its button.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from .dashboard_deferrals import deferral_dicts
from .dashboard_metrics import Scope, compute_metrics, world_names
from .models import ConditionDraft, MutationReview, MutationReviewChange, ProposedMutation
from .proposal_producers import producer_kind, producer_label

EXPORT_FORMAT = "wg-nia-dashboard-export/1"


def _iso(at: Optional[datetime]) -> Optional[str]:
    return at.isoformat() if at is not None else None


def _scoped(query, column, world_column, scope: Scope):
    if scope.world_ids is not None:
        query = query.where(world_column.in_(scope.world_ids))
    if scope.since is not None:
        query = query.where(column >= scope.since)
    if scope.until is not None:
        query = query.where(column < scope.until)
    return query


def _reviews(db: Session, mutation_ids: list[str]) -> dict[str, list[dict]]:
    if not mutation_ids:
        return {}
    reviews = db.exec(select(MutationReview).where(MutationReview.mutation_id.in_(mutation_ids))
                      .order_by(MutationReview.mutation_id, MutationReview.round)).all()
    changes: dict[str, list[dict]] = defaultdict(list)
    if reviews:
        for c in db.exec(select(MutationReviewChange).where(
                MutationReviewChange.review_id.in_([r.id for r in reviews]))
                .order_by(MutationReviewChange.path)).all():
            changes[c.review_id].append({"path": c.path, "field": c.field, "kind": c.kind,
                                         "before": c.before_value, "after": c.after_value})
    out: dict[str, list[dict]] = defaultdict(list)
    for r in reviews:
        out[r.mutation_id].append({"round": r.round, "action": r.action, "via": r.via,
                                   "status_after": r.status_after, "edited": r.edited,
                                   "step_verdict": r.step_verdict, "reviewed_at": _iso(r.reviewed_at),
                                   "changes": changes.get(r.id, [])})
    return out


def _proposals(db: Session, scope: Scope, names: dict[str, str]) -> list[dict]:
    rows = db.exec(_scoped(select(ProposedMutation), ProposedMutation.proposed_at, ProposedMutation.world_id,
                           scope).order_by(ProposedMutation.proposed_at)).all()
    reviews = _reviews(db, [m.id for m in rows])
    return [{
        "id": m.id, "world_id": m.world_id, "world": names.get(m.world_id), "source_type": m.source_type,
        "producer": m.proposed_by, "producer_label": producer_label(m.proposed_by),
        "producer_kind": producer_kind(m.proposed_by), "mutation_type": m.mutation_type,
        "target_table": m.target_table, "target_id": m.target_id, "status": m.status,
        "proposed_at": _iso(m.proposed_at), "reviewed_at": _iso(m.reviewed_at), "applied_at": _iso(m.applied_at),
        "rationale": m.rationale, "creator_notes": m.creator_notes,
        "payload": m.payload, "original_payload": m.original_payload, "reviews": reviews.get(m.id, []),
    } for m in rows]


def _interpreter(db: Session, scope: Scope) -> list[dict]:
    rows = db.exec(_scoped(select(ConditionDraft), ConditionDraft.created_at, ConditionDraft.world_ref, scope)
                   .order_by(ConditionDraft.created_at)).all()
    return [{
        "id": d.id, "attempt_id": d.attempt_id, "world_id": d.world_ref, "world": d.world_name, "role": d.role,
        "instruction": d.instruction, "outcome": d.outcome, "retried": d.retried, "offer_id": d.offer_ref,
        "saved_as_proposed": d.saved_as_proposed, "created_at": _iso(d.created_at),
        "decided_at": _iso(d.decided_at), "payload": d.payload, "model_calls": d.model_calls,
    } for d in rows]


def build_export(db: Session, scope: Scope) -> dict[str, Any]:
    """The export of `scope` (see the module docstring)."""
    names = world_names(db)
    return {
        "format": EXPORT_FORMAT,
        "exported_at": datetime.now(UTC).isoformat(),
        "scope": {"worlds": [{"id": w, "name": names.get(w)} for w in scope.world_ids]
                  if scope.world_ids is not None else "all",
                  "since": _iso(scope.since), "until_excluded": _iso(scope.until)},
        "proposals": _proposals(db, scope, names),
        "interpreter": _interpreter(db, scope),
        "metrics": compute_metrics(db, scope),
        "deferrals": deferral_dicts(),
    }
