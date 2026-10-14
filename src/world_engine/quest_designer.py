"""The quest designer (TICKET-0121, BRIEF-0121-E; decisions C1, D1, F1, G1, H2, V1).

From a `quest_request` it frames the subject (one model call), reads what the whole lore says of it
(`quest_lore.gather_lore`, the creator regime of INV-01), and either sends the existence question to the
creator (`asking`), reports an open offer that already covers it (`covered`), or writes a full quest
offer as a `quest_offer_creation` proposal (`proposed`): its conditions read by the condition
interpreter's own reader (C1) and journaled, its terms resolved by code or name (F1), the vocabulary it
lacks left to the creator (G1), up to three suggested givers (D1), and the player-visible prose checked
against the secrets it read (`prose_guard`, V1). Nothing is written to canon here: the proposal waits in
the review queue, and the applier (`cockpit/quest_offer_save.apply_offer_proposal`) writes it after the
creator's approval. `OllamaError` and `LlmParseError` propagate; the caller rolls back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlmodel import Session, select

from . import condition_interpreter as _interpreter
from . import prompt_call
from .conditions import node_to_dict
from .llm_parse import LlmParseError
from .lore_resolve import resolve_named
from .models import BASE_SKILL_DOMAINS, Entity, Fact, Knowledge, ProposedMutation, QuestOffer, QuestRequest
from .name_index import CREATOR
from .ollama_client import chat
from .prose_guard import flags as prose_flags
from .prose_guard import secret_ids
from .prose_render import fact_texts
from .quest_lore import gather_lore
from .writes.condition_drafts import write_condition_draft
from .writes.quest_requests import DESIGNER_PRODUCER, QUEST_OFFER_CREATION, move_request

SUBJECT_USAGE = "quest_subject"
DESIGN_USAGE = "quest_design"
MAX_GIVER_SUGGESTIONS = 3
DESIGNER_UNAVAILABLE_MESSAGE = (
    "Le modèle local (Ollama) est indisponible : la demande n'a pas été conçue et rien n'a changé. "
    "Relance quand Ollama est démarré."
)
OUTCOMES = ("offer", "covered", "unknown")
ROLES = ("prerequisite", "completion", "failure")
EXISTENCE_FR = {
    "exists": "La créatrice a dit que ce sujet existe dans ce monde : {text}.",
    "absent": "La créatrice a dit que ce sujet n'existe pas dans ce monde ({text}) : la quête mène le "
              "personnage à apprendre qu'il n'existe pas, et pourquoi.",
    "already": "La créatrice dit que le lore le contient déjà : {name}.",
}
NO_STEP_FR = "Le modèle n'a proposé aucune étape."


@dataclass
class DesignResult:
    outcome: str  # proposed | asking | covered | refused
    mutation: Optional[ProposedMutation] = None
    notes: list[str] = field(default_factory=list)


def _entity_name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else ""


def _strings(value: Any) -> list[str]:
    return [s for s in value if isinstance(s, str)] if isinstance(value, list) else []


def _subject(db: Session, request: QuestRequest, exchanges: Optional[list]) -> dict:
    """The `quest_subject` call: the subject, its keywords, the names it cites."""
    existing = _entity_name(db, request.existing_entity_id)
    values = {
        "character_name": _entity_name(db, request.character_id), "declaration": request.declaration,
        "existing": EXISTENCE_FR["already"].format(name=existing) if existing else "",
    }
    parsed = prompt_call.call_json(db, SUBJECT_USAGE, values, exchanges, chat)
    if not str(parsed.get("subject") or "").strip():
        raise LlmParseError("quest_subject: the answer names no subject")
    return parsed


def _design_call(db: Session, values: dict[str, str], exchanges: Optional[list]) -> dict:
    """The `quest_design` call: one whole offer, or `covered`, or `unknown`."""
    parsed = prompt_call.call_json(db, DESIGN_USAGE, values, exchanges, chat)
    if parsed.get("outcome") not in OUTCOMES:
        raise LlmParseError(f"quest_design: outcome {parsed.get('outcome')!r} is not one of {OUTCOMES}")
    return parsed


def _existence(request: QuestRequest, db: Session) -> str:
    if request.existence_answer is None:
        return ""
    return EXISTENCE_FR[request.existence_answer].format(
        text=(request.creator_text or "").strip(), name=_entity_name(db, request.existing_entity_id))


def _lore_lines(ctx: _interpreter.InterpreterContext, gathering) -> str:
    lines = []
    for fact_id, line in zip(gathering.fact_ids, gathering.lines):
        code = ctx.lists["f"].code_of(fact_id)
        lines.append(f"{code} — {line}" if code else line)
    return "\n".join(lines) or "(rien)"


def _design_values(db: Session, request: QuestRequest, subject: str, ctx, gathering,
                   errors: list[str]) -> dict[str, str]:
    base = _interpreter.prompt_values(ctx, "eligibility", request.declaration, errors)
    values = {key: base[key] for key in ("forms", "entities", "facts", "offers", "skills", "attributes",
                                         "entity_types", "event_types", "sortes", "errors")}
    values.update(character_name=_entity_name(db, request.character_id), declaration=request.declaration,
                  lore=_lore_lines(ctx, gathering), existence=_existence(request, db), subject=subject)
    return values


def _steps(answer: dict, notes: list[str]) -> list[dict]:
    """The answer's steps, cleaned: cost clamped, domain kept when known, a step with no objective dropped."""
    steps = []
    for raw in answer.get("steps") if isinstance(answer.get("steps"), list) else []:
        if not isinstance(raw, dict) or not str(raw.get("objective") or "").strip():
            notes.append("Une étape sans objectif a été abandonnée.")
            continue
        cost = raw.get("cost")
        cost = cost if isinstance(cost, int) and not isinstance(cost, bool) else 1
        domain = raw.get("domain")
        steps.append({"raw": raw, "objective": str(raw["objective"]).strip(), "cost": min(4, max(1, cost)),
                      "domain": domain if domain in BASE_SKILL_DOMAINS else None})
    return steps


def _conditions(steps: list[dict], eligibility: Any) -> list[tuple[str, str, Any, str]]:
    """`(where, role, answer, fallback instruction)` for every condition slot of the offer."""
    slots = [("eligibility", "eligibility", eligibility, "À qui l'offre est proposée")]
    for i, step in enumerate(steps):
        slots += [(f"steps.{i}.{role}", role, step["raw"].get(role), step["objective"]) for role in ROLES]
    return slots


def _usable(interp: _interpreter.Interpretation) -> bool:
    """A condition that goes straight into the offer's tree: proposed whole, with no attribute or
    vocabulary of its own still to confirm (those wait in `pending_drafts`)."""
    return (interp.outcome == "proposed" and interp.tree is not None and not interp.vocabulary
            and not any(not d.get("adopted") for d in interp.definitions))


def _settle(db: Session, request: QuestRequest, ctx, slots, exchanges: list, retried: bool) -> list[dict]:
    """Each non-null condition read by the interpreter's reader and journaled as a `condition_draft`
    (attempt id = the request's); the design call's exchanges are recorded once, on the first draft."""
    from .cockpit.routes.conditions import answer_dict

    out: list[dict] = []
    records = [e.to_record() for e in exchanges]
    for where, role, answer, fallback in slots:
        entry: dict = {"where": where, "role": role, "interp": None, "draft_id": None, "tree": None,
                       "notes": [], "pending": None}
        out.append(entry)
        if not isinstance(answer, dict):
            continue
        instruction = str(answer.get("phrase") or "").strip() or fallback
        interp = _interpreter.settle_answer(db, request.world_id, answer, ctx, (), retried)
        draft = write_condition_draft(
            db, attempt_id=request.id, world_id=request.world_id, role=role, instruction=instruction,
            outcome=interp.outcome, payload=interp.payload(None), model_calls=records, retried=retried)
        records = []
        entry.update(interp=interp, draft_id=draft.id, notes=interp.notes)
        if _usable(interp):
            entry["tree"] = node_to_dict(interp.tree)
        else:
            entry["pending"] = {"where": where, "answer": {
                **answer_dict(draft, interp, db), "instruction": instruction, "role": role}}
    return out


def _retry_errors(settled: list[dict]) -> list[str]:
    """II1: the errors the model may fix, each prefixed by where it occurred."""
    errors: list[str] = []
    for entry in settled:
        interp = entry["interp"]
        if interp is not None and interp.outcome == "refused" and _interpreter._retryable(interp):
            errors += [f"{entry['where']} : {e}" for e in interp.errors]
    return errors


def _named_entity(db: Session, world_id: str, name: Any, categories: tuple[str, ...]) -> Optional[Entity]:
    """The entity a name resolves to, when exactly one does (the designer never picks)."""
    if not isinstance(name, str) or not name.strip():
        return None
    for category in categories:
        resolution = resolve_named(name.strip(), category, world_id, db, scope=CREATOR)
        if resolution.verdict == "matched":
            return db.get(Entity, resolution.entity_id)
    return None


def _givers(db: Session, world_id: str, answer: dict, notes: list[str]) -> list[dict]:
    found: list[dict] = []
    for name in _strings(answer.get("givers")):
        entity = _named_entity(db, world_id, name, ("person", "faction"))
        if entity is None:
            notes.append(f"Donneur introuvable : « {name} » (aucun nom de ce monde ne correspond).")
        elif entity.id not in {g["entity_id"] for g in found} and len(found) < MAX_GIVER_SUGGESTIONS:
            found.append({"entity_id": entity.id, "name": entity.name, "type": entity.type})
    return found


def _term(db: Session, world_id: str, ctx, raw: Any) -> tuple[Optional[dict], Optional[str]]:
    """One term, resolved by code (`f`, `s`) or name (items, counterparties); `(None, why)` when not."""
    if not isinstance(raw, dict) or raw.get("direction") not in ("cost", "reward"):
        return None, "Un coût ou une récompense sans sens a été abandonné."
    currency, target, amount = raw.get("currency"), raw.get("target"), raw.get("amount")
    amount = amount if isinstance(amount, int) and not isinstance(amount, bool) else None
    level = raw.get("level") if isinstance(raw.get("level"), str) else None
    term = {"direction": raw["direction"], "currency": currency, "counterparty_entity_id": None,
            "item_id": None, "fact_id": None, "skill_key": None, "amount": amount, "level": None}
    if currency == "money":
        resolved = amount is not None
    elif currency == "item":
        entity = _named_entity(db, world_id, target, ("object",))
        term["item_id"] = entity.id if entity is not None else None
        resolved = entity is not None
    elif currency == "relation":
        entity = _named_entity(db, world_id, target, ("person", "faction"))
        term["counterparty_entity_id"] = entity.id if entity is not None else None
        resolved = entity is not None
    elif currency == "fact":
        term["fact_id"], term["level"] = ctx.lists["f"].resolve(target), level
        resolved = term["fact_id"] is not None
    elif currency == "skill":
        term["skill_key"], term["level"] = ctx.lists["s"].resolve(target), level
        resolved = term["skill_key"] is not None
    else:
        return None, f"Une monnaie inconnue ({currency}) : le terme a été abandonné."
    if resolved:
        return term, None
    kind = "coût" if raw["direction"] == "cost" else "récompense"
    return None, f"Un {kind} n'a pas pu être résolu (« {target or currency} ») : abandonné."


def _unknown_facts(db: Session, world_id: str, fact_ids: tuple[str, ...]) -> list[str]:
    """The gathered facts no entity of the world knows -- the creator is warned, nothing invented."""
    if not fact_ids:
        return []
    known = set(db.exec(select(Knowledge.fact_id).join(Entity, Entity.id == Knowledge.entity_id)
                        .where(Entity.world_id == world_id, Knowledge.fact_id.in_(list(fact_ids)))).all())
    facts = [db.get(Fact, fid) for fid in fact_ids if fid not in known]
    return [f"Personne ne sait encore : {text}" for text in fact_texts(db, facts)]


def _payload(db: Session, request: QuestRequest, subject: str, answer: dict, steps: list[dict],
             settled: list[dict], ctx, notes: list[str]) -> dict:
    """C-10, whole."""
    by_where = {e["where"]: e for e in settled}
    elig = by_where["eligibility"]
    out_steps = []
    for i, step in enumerate(steps):
        item = {"objective": step["objective"], "cost": step["cost"], "domain": step["domain"]}
        for role in ROLES:
            entry = by_where[f"steps.{i}.{role}"]
            item[role] = entry["tree"]
            item[f"{role}_draft_id"] = entry["draft_id"] if entry["tree"] else None
        out_steps.append(item)
    terms = []
    for raw in answer.get("terms") if isinstance(answer.get("terms"), list) else []:
        term, why = _term(db, request.world_id, ctx, raw)
        if term is not None:
            terms.append(term)
        else:
            notes.append(why)
    consulted = list(ctx.lists["f"].codes.values())
    secrets = secret_ids(db, request.world_id, consulted)
    title = str(answer.get("title") or "").strip() or request.declaration
    summary = str(answer.get("summary") or "").strip()
    texts = {"title": title, "summary": summary,
             **{f"steps.{i}.objective": s["objective"] for i, s in enumerate(steps)}}
    return {
        "request_id": request.id, "character_id": request.character_id, "subject": subject,
        "giver_entity_id": "", "contact_entity_id": None,
        "giver_suggestions": _givers(db, request.world_id, answer, notes),
        "title": title, "summary": summary, "repeatable": False, "status": "open",
        "eligibility": elig["tree"], "eligibility_draft_id": elig["draft_id"] if elig["tree"] else None,
        "steps": out_steps, "terms": terms, "unsaved_attributes": [],
        "pending_drafts": [e["pending"] for e in settled if e["pending"] is not None],
        "notes": notes, "consulted_fact_ids": consulted, "secret_fact_ids": secrets,
        "flags": prose_flags(db, {k: v for k, v in texts.items() if v}, secrets), "flags_confirmed": False,
    }


def _settled_notes(settled: list[dict], answer: dict) -> list[str]:
    notes = [n.strip() for n in _strings(answer.get("notes")) if n.strip()]
    for entry in settled:
        notes += entry["notes"]
    return list(dict.fromkeys(notes))


def design(db: Session, request: QuestRequest, exchanges: Optional[list] = None) -> DesignResult:
    """C-11. Writes `condition_draft` journal rows and the proposal in the caller's transaction, moves
    the request, never commits. `exchanges` receives the model calls it made."""
    subject_calls: list = []
    design_calls: list = []
    try:
        return _design(db, request, subject_calls, design_calls)
    finally:
        if exchanges is not None:
            exchanges.extend(subject_calls + design_calls)


def _design(db: Session, request: QuestRequest, subject_calls: list, design_calls: list) -> DesignResult:
    world_id = request.world_id
    parsed = _subject(db, request, subject_calls)
    subject = str(parsed["subject"]).strip()
    gathering = gather_lore(
        db, world_id, keywords=_strings(parsed.get("keywords")), names=_strings(parsed.get("names")),
        entity_ids=(request.existing_entity_id,) if request.existing_entity_id else (),
        lore_entry_id=request.lore_entry_id)
    if gathering.empty and request.existence_answer is None:
        move_request(db, request, "asking", subject=subject)
        return DesignResult("asking")
    instruction = f"{request.declaration} {subject}"

    def context():
        return _interpreter.build_context(db, world_id, instruction, None, (), extra_fact_ids=gathering.fact_ids)

    ctx = context()
    answer = _design_call(db, _design_values(db, request, subject, ctx, gathering, []), design_calls)
    if answer["outcome"] == "covered":
        offer_id = ctx.lists["q"].resolve(answer.get("covered_by"))
        offer = db.get(QuestOffer, offer_id) if offer_id else None
        if offer is None or offer.world_id != world_id or offer.status != "open":
            raise LlmParseError("quest_design: covered_by names no open quest offer of the list")
        move_request(db, request, "covered", offer_id=offer.id, subject=subject)
        return DesignResult("covered", notes=[f"Déjà couvert par « {offer.title} »."])
    if answer["outcome"] == "unknown":
        why = str(answer.get("unknown") or "").strip() or "Le lore ne dit rien de ce sujet."
        move_request(db, request, "asking", note=why, subject=subject)
        return DesignResult("asking", notes=[why])
    notes: list[str] = []
    steps = _steps(answer, notes)
    if not steps:
        return DesignResult("refused", notes=notes + [NO_STEP_FR])
    settled = _settle(db, request, ctx, _conditions(steps, answer.get("eligibility")), design_calls, False)
    errors = _retry_errors(settled)
    if errors:
        ctx = context()
        again = _design_call(db, _design_values(db, request, subject, ctx, gathering, errors), design_calls)
        if again["outcome"] != "offer":
            raise LlmParseError("quest_design: the corrected answer is no offer")
        answer, notes = again, []
        steps = _steps(answer, notes)
        if not steps:
            return DesignResult("refused", notes=notes + [NO_STEP_FR])
        settled = _settle(db, request, ctx, _conditions(steps, answer.get("eligibility")), [], True)
    notes += _settled_notes(settled, answer) + _unknown_facts(db, world_id, gathering.fact_ids)
    payload = _payload(db, request, subject, answer, steps, settled, ctx, notes)
    mutation = ProposedMutation(
        world_id=world_id, source_type="pass_play", pass_play_id=request.pass_play_id,
        mutation_type=QUEST_OFFER_CREATION, target_table="quest_offer", payload=payload,
        status="proposed", proposed_by=DESIGNER_PRODUCER, rationale=f"quest request {request.id} -- {subject}")
    db.add(mutation)
    db.flush()
    move_request(db, request, "proposed", mutation_id=mutation.id, subject=subject)
    return DesignResult("proposed", mutation, payload["notes"])
