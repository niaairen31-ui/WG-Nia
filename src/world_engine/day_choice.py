"""Model choice among narrowed candidates (TICKET-0094, H2).

The code narrows the candidates (`choice_requests`), the model chooses one
and cites an excerpt (`choose`, BRIEF-0094-C), the code judges the choice
(`judge_choice`). This reopens 0075 C1 / 0081 C2 knowingly: a pick now
happens, but only here, only among entities the concordance or the
character's own name surfaces produced, and only when the judge accepts it.
Every call is recorded (`writes.write_day_mention_choices`).

Evidence is what the character knows about each candidate, read through
`facet_reads.facts_of` (creator-only facts excluded by construction) and
filtered by one `resolve_levels_for_entity` call. The gameplay model is
abliterated: nothing the character does not know is ever assembled.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .day_concordance import ConcordanceResult, MatchedMention
from .day_extract import Mention
from .facet_reads import facts_of
from .facets import FACETS
from .knowledge_resolve import resolve_levels_for_entity
from .lore_resolve import category_of_type, near_in_surfaces, normalize_surface, rung_named_partial
from .models import Character, Entity, PromptTemplate
from .name_index import NameScope, surfaces as name_surfaces
from .prompt_registry import effective_model
from .prompt_store import current_prompt

MAX_CANDIDATES = 8
MAX_FACTS_PER_CANDIDATE = 12
MODEL_CHOICE_RUNG = "model_choice"

_EXCERPT_EDGE = " \t\n\"'«»“”.,;:!?…"
_CATEGORY_LABEL_FR = {"person": "personne", "place": "lieu", "faction": "faction"}


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    name: str
    facts: tuple[str, ...]
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class ChoiceRequest:
    mention: Mention
    trigger: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class ChoiceVerdict:
    verdict: str
    entity_id: Optional[str]
    excerpt: Optional[str]
    reason: Optional[str]
    detail: Optional[str]


def _near_ids(mention: Mention, surfaces: tuple) -> list[str]:
    """C-05 step 2: partial ids (sorted), then near ids in the mention's
    category, duplicates dropped, first MAX_CANDIDATES kept."""
    ids: list[str] = list(rung_named_partial(mention.surface_form, mention.category, surfaces) or [])
    for near in near_in_surfaces(mention.surface_form, surfaces):
        if category_of_type(near.entity_type) == mention.category and near.entity_id not in ids:
            ids.append(near.entity_id)
    return ids[:MAX_CANDIDATES]


def _candidates(ids: list[str], known: dict[str, str], db: Session) -> tuple[Candidate, ...]:
    """C-05 step 3: evidence per candidate, known facts only."""
    out: list[Candidate] = []
    for entity_id in ids:
        entity = db.get(Entity, entity_id)
        if entity is None:
            continue
        rows = [r for r in facts_of(db, entity_id=entity_id, facets=tuple(FACETS)) if r.fact_id in known]
        rows = rows[:MAX_FACTS_PER_CANDIDATE]
        out.append(Candidate(
            entity_id=entity_id, name=entity.name,
            facts=tuple(r.content for r in rows), fact_ids=tuple(r.fact_id for r in rows),
        ))
    return tuple(out)


def choice_requests(result: ConcordanceResult, character: Character, db: Session) -> tuple[ChoiceRequest, ...]:
    """C-05: one request per named ambiguity, then one per named unmatched
    mention with partial or near candidates among the character's own name
    surfaces (Y2b). Cast and inferred mentions never produce a request."""
    near_mentions = [um.mention for um in result.unmatched if um.mention.kind == "named"]
    if not result.ambiguous and not near_mentions:
        return ()
    known = resolve_levels_for_entity(db, character.id)
    requests: list[ChoiceRequest] = []
    for am in result.ambiguous:
        candidates = _candidates(list(am.candidate_ids), known, db)
        if candidates:
            requests.append(ChoiceRequest(mention=am.mention, trigger="ambiguous", candidates=candidates))
    if near_mentions:
        surfaces = name_surfaces(db, character.world_id, NameScope(
            "perceiver", known_fact_ids=frozenset(known),
        ))
        for mention in near_mentions:
            candidates = _candidates(_near_ids(mention, surfaces), known, db)
            if candidates:
                requests.append(ChoiceRequest(mention=mention, trigger="near", candidates=candidates))
    return tuple(requests)


def render_candidates(request: ChoiceRequest) -> str:
    """C-06: the numbered list the model reads."""
    blocks: list[str] = []
    for number, candidate in enumerate(request.candidates, start=1):
        lines = [f"{number}. {candidate.name}"]
        if candidate.facts:
            lines.append("   Ce que le personnage sait :")
            lines.extend(f"   - {fact}" for fact in candidate.facts)
        else:
            lines.append("   Le personnage ne sait rien de plus sur lui.")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def category_label(category: str) -> str:
    return _CATEGORY_LABEL_FR[category]


def parse_answer(raw: str) -> dict:
    """C-06: a technical failure (Y8a) raises LlmParseError."""
    obj = llm_parse.extract_object(raw)
    choix = obj.get("choix")
    if not isinstance(choix, int) or isinstance(choix, bool):
        raise llm_parse.LlmParseError("day_choice: choix missing or ill-typed")
    for key in ("extrait", "raison"):
        if not isinstance(obj.get(key), str):
            raise llm_parse.LlmParseError(f"day_choice: {key} missing or ill-typed")
    return {"choix": choix, "extrait": obj["extrait"], "raison": obj["raison"]}


def _joined(facts: tuple[str, ...]) -> str:
    return normalize_surface(" ".join(facts))


def judge_choice(request: ChoiceRequest, answer: dict, declaration: str) -> ChoiceVerdict:
    """C-06: pure. The model's number must be on the list; its excerpt must
    be found verbatim after normalization — for an ambiguity, in the chosen
    candidate's facts and in no other candidate's; for a near name, in the
    declaration or the chosen candidate's facts (X2b)."""
    excerpt = answer["extrait"].strip() or None
    reason = answer["raison"].strip() or None
    choix = answer["choix"]
    if choix == 0:
        return ChoiceVerdict("declined", None, excerpt, reason, None)
    if not 1 <= choix <= len(request.candidates):
        return ChoiceVerdict("rejected", None, excerpt, reason, "candidate out of range")
    chosen = request.candidates[choix - 1]
    normalized = normalize_surface(answer["extrait"].strip(_EXCERPT_EDGE))
    if len(normalized) < 3:
        return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason, "excerpt too short")
    in_chosen = normalized in _joined(chosen.facts)
    if request.trigger == "ambiguous":
        if not in_chosen:
            return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason,
                                 "excerpt not in the chosen candidate's facts")
        others = [c for c in request.candidates if c.entity_id != chosen.entity_id]
        if any(normalized in _joined(c.facts) for c in others):
            return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason,
                                 "excerpt does not single out the chosen candidate")
    elif not (in_chosen or normalized in normalize_surface(declaration)):
        return ChoiceVerdict("rejected", chosen.entity_id, excerpt, reason, "excerpt not found")
    return ChoiceVerdict("accepted", chosen.entity_id, excerpt, reason, None)


def record_of(request: ChoiceRequest, verdict: ChoiceVerdict, attempts: int) -> dict:
    """The choice-record family shape (C-02)."""
    return {
        "category": request.mention.category, "surface_form": request.mention.surface_form,
        "trigger": request.trigger,
        "candidate_ids": [c.entity_id for c in request.candidates],
        "evidence_fact_ids": [fid for c in request.candidates for fid in c.fact_ids],
        "verdict": verdict.verdict, "chosen_entity_id": verdict.entity_id if verdict.verdict != "declined" else None,
        "excerpt": verdict.excerpt, "reason": verdict.reason, "verdict_detail": verdict.detail,
        "attempts": attempts,
    }


def _load_choice_template(world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_plan_select._load_day_plan_select_template`'s precedent, verbatim."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "day_mention_choice",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


@dataclass(frozen=True)
class ChoiceOutcome:
    result: ConcordanceResult
    records: tuple[dict, ...]


def _ask(request: ChoiceRequest, declaration: str, template: PromptTemplate, db: Session) -> dict:
    """One attempt: render, call, parse. Raises OllamaError/LlmParseError."""
    version = current_prompt(db, template)
    user_msg = (
        version.user_template
        .replace("{declaration}", declaration)
        .replace("{surface_form}", request.mention.surface_form)
        .replace("{category}", category_label(request.mention.category))
        .replace("{candidates}", render_candidates(request))
        + "\n/no_think"
    )
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
        format="json",
    )
    return parse_answer(raw)


def _decide(request: ChoiceRequest, declaration: str, template: PromptTemplate, db: Session) -> dict:
    """Y5c/Y8a: one retry on a technical failure only, then `failed`."""
    error = ""
    for attempt in (1, 2):
        try:
            answer = _ask(request, declaration, template, db)
        except (ollama_client.OllamaError, llm_parse.LlmParseError) as exc:
            error = str(exc)
            continue
        return record_of(request, judge_choice(request, answer, declaration), attempt)
    return record_of(request, ChoiceVerdict("failed", None, None, None, error), 2)


def _apply(result: ConcordanceResult, request: ChoiceRequest, entity_id: str) -> ConcordanceResult:
    """An accepted choice: the mention leaves ambiguous/unmatched and joins
    matched with rung MODEL_CHOICE_RUNG (Y3b)."""
    matched = (*result.matched, MatchedMention(mention=request.mention, entity_id=entity_id, rung=MODEL_CHOICE_RUNG))
    if request.trigger == "ambiguous":
        ambiguous = tuple(am for am in result.ambiguous if am.mention is not request.mention)
        return replace(result, matched=matched, ambiguous=ambiguous)
    unmatched = tuple(um for um in result.unmatched if um.mention is not request.mention)
    return replace(result, matched=matched, unmatched=unmatched)


def choose(result: ConcordanceResult, declaration: str, character: Character, db: Session) -> ChoiceOutcome:
    """C-07: narrow, ask, judge, apply. No request → no template read and
    no call. A missing template raises before the first call and is never
    retried (X4a: the coverage guard refuses the declaration upstream)."""
    requests = choice_requests(result, character, db)
    if not requests:
        return ChoiceOutcome(result=result, records=())
    template = _load_choice_template(character.world_id, db)
    if template is None:
        raise llm_parse.LlmParseError("day_choice: no active prompt_template for usage='day_mention_choice'")
    records: list[dict] = []
    for request in requests:
        record = _decide(request, declaration, template, db)
        records.append(record)
        if record["verdict"] == "accepted":
            result = _apply(result, request, record["chosen_entity_id"])
    return ChoiceOutcome(result=result, records=tuple(records))
