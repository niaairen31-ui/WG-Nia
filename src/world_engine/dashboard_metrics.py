"""The creator's dashboard: a registry of metrics in code, each a question in French, its computation over relational columns, and the decision codes it watches (TICKET-0115, BRIEF-0115-D; decisions H1, D1, E2 and M1 of the conditions series' dashboard).

H1: a metric is code -- never SQL written in the interface. E2: no
threshold; the numbers are shown and Nia judges. M1: a metric reads
relational columns only, never a JSON column (`ProposedMutation.payload`,
`ConditionDraft.payload`: INV-20) -- what lives in JSON is measured from
the export (`dashboard_export.py`).

`Scope(world_ids, since, until)`: the worlds (None: every world) and the
real-world dates, `until` excluded (the route passes the day after the last
day asked). A metric of reviews reads `mutation_review.reviewed_at`, of the
interpreter `condition_draft.created_at`, of the lexicon
`skill_resolution.created_at`; a metric of the world as it stands
(conditions, encounters, the queue) ignores the dates.

`compute_metrics(db, scope) -> list[dict]`: each `METRICS` entry as
`{key, title, question, watches, dated, rows: [{group, label, value, of}],
note}` -- `value` out of `of` when `of` is set.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from sqlmodel import Session, select

from .conditions import and_path_leaves, read_condition
from .models import (
    Agenda, AgendaStep, Character, ConditionDraft, ConditionNode, Entity, MutationReview, MutationReviewChange,
    PassPlay, ProposedMutation, Quest, QuestOffer, QuestRequest, Rencontre, SkillResolution, World,
)
from .models import Session as SessionRow
from .proposal_producers import producer_label


@dataclass(frozen=True)
class Scope:
    world_ids: Optional[tuple[str, ...]] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None


@dataclass(frozen=True)
class Row:
    group: str
    label: str
    value: int
    of: Optional[int] = None


@dataclass(frozen=True)
class Metric:
    key: str
    title: str
    question: str
    watches: tuple[str, ...]
    dated: bool
    compute: Callable[[Session, Scope], tuple[list[Row], str]]


def _in_worlds(column, scope: Scope):
    return True if scope.world_ids is None else column.in_(scope.world_ids)


def _dated(column, scope: Scope):
    conditions = []
    if scope.since is not None:
        conditions.append(column >= scope.since)
    if scope.until is not None:
        conditions.append(column < scope.until)
    return conditions


def _rounds(db: Session, scope: Scope, mutation_type: str) -> dict[str, list[MutationReview]]:
    """The review rounds of `mutation_type` proposals whose LAST round falls
    in the scope, by proposal, in round order."""
    rows = db.exec(select(MutationReview)
                   .join(ProposedMutation, ProposedMutation.id == MutationReview.mutation_id)
                   .where(ProposedMutation.mutation_type == mutation_type,
                          _in_worlds(MutationReview.world_id, scope))
                   .order_by(MutationReview.mutation_id, MutationReview.round)).all()
    by_mutation: dict[str, list[MutationReview]] = defaultdict(list)
    for review in rows:
        by_mutation[review.mutation_id].append(review)
    return {m: r for m, r in by_mutation.items() if all(_holds(r[-1].reviewed_at, b) for b in _bounds(scope))}


def _bounds(scope: Scope) -> list[tuple[str, datetime]]:
    return [(op, at) for op, at in ((">=", scope.since), ("<", scope.until)) if at is not None]


def _holds(at: datetime, bound: tuple[str, datetime]) -> bool:
    op, limit = bound
    at, limit = at.replace(tzinfo=None), limit.replace(tzinfo=None)
    return at >= limit if op == ">=" else at < limit


def _producers(db: Session, ids) -> dict[str, Optional[str]]:
    if not ids:
        return {}
    return dict(db.exec(select(ProposedMutation.id, ProposedMutation.proposed_by)
                        .where(ProposedMutation.id.in_(list(ids)))).all())


# --- the metrics -------------------------------------------------------------------

def _event_reviews(db: Session, scope: Scope) -> tuple[list[Row], str]:
    rounds = _rounds(db, scope, "event_creation")
    producers = _producers(db, rounds)
    outcome: dict[str, Counter] = defaultdict(Counter)
    for mutation_id, reviews in rounds.items():
        last = reviews[-1]
        if last.action == "reject":
            kind = "rejeté"
        elif last.status_after == "approved":
            kind = "en attente (« Needs attention »)"
        elif any(r.edited for r in reviews):
            kind = "accepté corrigé"
        else:
            kind = "accepté tel quel"
        outcome[producer_label(producers.get(mutation_id))][kind] += 1
    rows = [Row(group, kind, n, sum(counts.values()))
            for group, counts in sorted(outcome.items())
            for kind, n in sorted(counts.items())]
    return rows, "Chaque événement proposé, selon sa dernière revue dans la période."


def _tick_retyped(db: Session, scope: Scope) -> tuple[list[Row], str]:
    rounds = _rounds(db, scope, "event_creation")
    producers = _producers(db, rounds)
    tick = {m: r for m, r in rounds.items() if producers.get(m) == "local_ai_tick" and r[-1].action == "approve"}
    retyped = 0
    for reviews in tick.values():
        ids = [r.id for r in reviews]
        fields = db.exec(select(MutationReviewChange.field)
                         .where(MutationReviewChange.review_id.in_(ids))).all()
        if any(f in ("type_id", "type") or f.startswith("new_type") for f in fields):
            retyped += 1
    return [Row("Tick du monde", "retypés par Nia", retyped, len(tick))], \
        "Événements du tick acceptés dont Nia a changé le type."


_AGREE = {("approve", "met"), ("reject", "unmet")}
_JUDGED = ("met", "unmet")


def _step_verdicts(db: Session, scope: Scope) -> tuple[list[Row], str]:
    rounds = _rounds(db, scope, "agenda_step_change")
    counts: Counter = Counter()
    for reviews in rounds.values():
        first = reviews[0]
        verdict = first.step_verdict
        if verdict in _JUDGED:
            counts["Nia confirme la condition" if (reviews[-1].action, verdict) in _AGREE
                   else "Nia contredit la condition"] += 1
        elif verdict == "unknown":
            counts["condition invérifiable"] += 1
        else:
            counts["pas de condition à juger"] += 1
    total = sum(counts.values())
    return [Row("Étapes", label, n, total) for label, n in sorted(counts.items())], \
        "Le verdict de la condition au moment de la revue, comparé à la décision finale de Nia."


OUTCOMES_FR: dict[str, str] = {
    "proposed": "proposée, sans suite", "needs_choice": "un nom à choisir, sans suite",
    "refused": "refusée par le code", "unavailable": "modèle indisponible", "parse_error": "réponse illisible",
    "inserted": "insérée, offre non enregistrée", "discarded": "écartée par Nia", "saved": "enregistrée",
}


def _interpreter(db: Session, scope: Scope) -> tuple[list[Row], str]:
    rows = db.exec(select(ConditionDraft.outcome, ConditionDraft.saved_as_proposed)
                   .where(_in_worlds(ConditionDraft.world_ref, scope),
                          *_dated(ConditionDraft.created_at, scope))).all()
    total = len(rows)
    outcomes = Counter(o for o, _s in rows)
    saved = [s for o, s in rows if o == "saved"]
    out = [Row("Propositions", OUTCOMES_FR.get(outcome, outcome), n, total)
           for outcome, n in sorted(outcomes.items())]
    if saved:
        out.append(Row("Enregistrées", "telles que proposées", sum(1 for s in saved if s), len(saved)))
    return out, "Chaque proposition de l'interprète de conditions, selon son issue."


def _steps_without_day_npc(db: Session, scope: Scope) -> tuple[list[Row], str]:
    steps = db.exec(select(AgendaStep, Agenda.world_id)
                    .join(Agenda, Agenda.id == AgendaStep.agenda_id)
                    .join(Quest, Quest.agenda_id == Agenda.id)
                    .where(AgendaStep.status == "active", Agenda.status == "active",
                           _in_worlds(Agenda.world_id, scope))).all()
    with_prerequisite = without_npc = 0
    for step, _world in steps:
        try:
            tree = read_condition(db, role="prerequisite", agenda_step_id=step.id)
        except ValueError:
            continue
        if tree is None:
            continue
        with_prerequisite += 1
        if not any(leaf.type == "relation_gte" for leaf in and_path_leaves(tree)):
            without_npc += 1
    return [Row("Étapes de quête actives", "sans PNJ de journée", without_npc, with_prerequisite)], \
        "Étapes actives avec un prérequis, dont aucune relation atteinte par « toutes » ne nomme le PNJ."


def _absence_leaves(db: Session, scope: Scope) -> tuple[list[Row], str]:
    leaves = db.exec(select(ConditionNode.parent_id).where(
        ConditionNode.op == "leaf", ConditionNode.form == "event",
        _in_worlds(ConditionNode.world_id, scope))).all()
    parents = {p for p in leaves if p}
    nots = set(db.exec(select(ConditionNode.id).where(ConditionNode.id.in_(list(parents)),
                                                       ConditionNode.op == "not")).all()) if parents else set()
    under_not = sum(1 for p in leaves if p in nots)
    return [Row("Feuilles « événement »", "sous un « non »", under_not, len(leaves))], \
        "« Sans être repéré » s'écrit « non » sur une feuille événement."


def _edited_fields(db: Session, scope: Scope) -> tuple[list[Row], str]:
    rows = db.exec(select(ProposedMutation.mutation_type, MutationReviewChange.field)
                   .join(MutationReview, MutationReview.id == MutationReviewChange.review_id)
                   .join(ProposedMutation, ProposedMutation.id == MutationReview.mutation_id)
                   .where(_in_worlds(MutationReviewChange.world_id, scope),
                          *_dated(MutationReview.reviewed_at, scope))).all()
    counts = Counter(rows)
    return [Row(mutation_type, field, n) for (mutation_type, field), n in counts.most_common(15)], \
        "Ce que Nia corrige le plus souvent avant d'accepter (15 premiers)."


def _rencontre_pairs(db: Session, scope: Scope) -> tuple[list[Row], str]:
    characters = set(db.exec(select(Character.id).where(_in_worlds(Character.world_id, scope))).all())
    pairs = db.exec(select(Rencontre.entity_lo_id, Rencontre.entity_hi_id)
                    .where(_in_worlds(Rencontre.world_id, scope))).all()
    other = sum(1 for lo, hi in pairs if lo not in characters or hi not in characters)
    return [Row("Rencontres", "hors deux personnages", other, len(pairs))], \
        "A1'b revient si aucune rencontre ne lie autre chose que deux personnages."


def _lexicon_gaps(db: Session, scope: Scope) -> tuple[list[Row], str]:
    forms = db.exec(select(SkillResolution.surface_form).where(
        SkillResolution.verdict == "unmatched", _in_worlds(SkillResolution.world_id, scope),
        *_dated(SkillResolution.created_at, scope))).all()
    distinct = {f.strip().casefold() for f in forms}
    return [Row("Lexique d'actions", "formes non reconnues distinctes", len(distinct), len(forms))], \
        "Le seuil de C3b est le tien : la liste des formes est dans « Compétences »."


def _needs_attention(db: Session, scope: Scope) -> tuple[list[Row], str]:
    rows = db.exec(select(ProposedMutation.proposed_by).where(
        ProposedMutation.status == "approved", _in_worlds(ProposedMutation.world_id, scope))).all()
    counts = Counter(producer_label(p) for p in rows)
    return [Row("En attente", label, n) for label, n in sorted(counts.items())], \
        "Approuvées sans pouvoir s'appliquer (ou en attente de réalisation) : la file « Needs attention »."


_TRIGGERS_FR = (("route", "Déclaration aiguillée"), ("blocked", "Étape bloquée"),
                ("dropped", "Savoir introuvable"), ("trial", "Épreuve de rang"))
_ANSWERS_FR = (("exists", "Elle existe"), ("absent", "Elle n'existe pas"),
               ("already", "Le lore le disait déjà"))


def _after(at: datetime, limit: datetime) -> bool:
    return at.replace(tzinfo=None) > limit.replace(tzinfo=None)


def _quest_requests(db: Session, scope: Scope) -> tuple[list[Row], str]:
    requests = db.exec(select(QuestRequest).where(
        _in_worlds(QuestRequest.world_id, scope), *_dated(QuestRequest.created_at, scope))).all()
    triggers = Counter(r.trigger for r in requests)
    answers = Counter(r.existence_answer for r in requests)
    days = db.exec(select(PassPlay.id).join(SessionRow, SessionRow.id == PassPlay.session_id).where(
        PassPlay.agenda_id.is_not(None), _in_worlds(SessionRow.world_id, scope),
        *_dated(PassPlay.submitted_at, scope))).all()
    rows = [Row("Origine", label, triggers[key], len(requests)) for key, label in _TRIGGERS_FR]
    rows.append(Row("Origine", "Journées aiguillées vers une quête", triggers["route"], len(days)))
    rows += [Row("Existence", label, answers[key], len(requests)) for key, label in _ANSWERS_FR]
    approved = created_after = 0
    mutation_ids = [r.mutation_id for r in requests if r.mutation_id]
    if mutation_ids:
        proposals = {p.id: p for p in db.exec(select(ProposedMutation).where(
            ProposedMutation.id.in_(mutation_ids), ProposedMutation.status == "applied")).all()}
        for request in requests:
            proposal = proposals.get(request.mutation_id)
            if proposal is None:
                continue
            approved += 1
            offer = db.get(QuestOffer, request.offer_id) if request.offer_id else None
            giver = db.get(Entity, offer.giver_entity_id) if offer is not None else None
            if giver is not None and _after(giver.created_at, proposal.proposed_at):
                created_after += 1
    rows.append(Row("Donneur", "Offres approuvées", approved, len(requests)))
    rows.append(Row("Donneur", "Donneur créé après la proposition", created_after, approved))
    return rows, "Ce que deviennent les demandes de quête nées des journées et des épreuves de rang (P1, S3, D2)."


METRICS: tuple[Metric, ...] = (
    Metric("event_reviews", "Événements proposés",
           "Combien d'événements proposés acceptes-tu tels quels ?", ("D1", "D2"), True, _event_reviews),
    Metric("tick_retyped", "Types du tick",
           "Retypes-tu souvent les événements du tick ?", ("A1 (0119)",), True, _tick_retyped),
    Metric("step_verdicts", "Objectifs d'étape",
           "Confirmes-tu ce que la condition d'accomplissement dit déjà ?", ("M1", "M2"), True, _step_verdicts),
    Metric("interpreter", "Interprète de conditions",
           "Que deviennent les propositions de l'interprète ?", ("IH1",), True, _interpreter),
    Metric("steps_without_day_npc", "PNJ de journée",
           "Des étapes actives n'ont-elles pas de PNJ de journée ?", ("Q1", "Q2"), False, _steps_without_day_npc),
    Metric("absence_leaves", "Absence",
           "Écris-tu souvent « non » sur une feuille événement ?", ("absence",), False, _absence_leaves),
    Metric("edited_fields", "Corrections",
           "Que corriges-tu dans les propositions ?", ("A3", "H1a"), True, _edited_fields),
    Metric("rencontre_pairs", "Rencontres",
           "Des rencontres lient-elles autre chose que deux personnages ?", ("A1'b",), False, _rencontre_pairs),
    Metric("lexicon_gaps", "Lexique d'actions",
           "Combien de gestes le lexique ne reconnaît-il pas ?", ("C3b",), True, _lexicon_gaps),
    Metric("needs_attention", "File « Needs attention »",
           "Combien de propositions approuvées attendent encore ?", (), False, _needs_attention),
    Metric("quest_requests", "Demandes de quête",
           "D'où viennent les demandes de quête, et que deviennent-elles ?", ("P1", "S3", "D2"), True,
           _quest_requests),
)


def compute_metrics(db: Session, scope: Scope) -> list[dict]:
    """Every metric of `METRICS` for `scope` (see the module docstring)."""
    out = []
    for metric in METRICS:
        rows, note = metric.compute(db, scope)
        out.append({"key": metric.key, "title": metric.title, "question": metric.question,
                    "watches": list(metric.watches), "dated": metric.dated, "note": note,
                    "rows": [{"group": r.group, "label": r.label, "value": r.value, "of": r.of} for r in rows]})
    return out


def world_names(db: Session) -> dict[str, str]:
    """Every world's name by id."""
    return dict(db.exec(select(World.id, World.name)).all())
