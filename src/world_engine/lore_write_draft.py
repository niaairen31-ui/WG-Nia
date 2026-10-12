"""The model side of the lore writing path (TICKET-0098, BRIEF-0098-D).

Two model calls, each its own prompt (decision O1): `draft_questions` asks
the creator at most `MAX_QUESTIONS` clarification questions about her
statement (J3); `draft_proposal` turns the statement and her answers into a
draft the writing panel shows for correction. The model sees the statement,
the answers, the facet vocabulary, the entities the statement names and a
coded list of the facts already about them (L1) -- never an id. It names
existing facts only by code (`fact_refs.code_facts`, CLAUDE.md invariant)
and entities only by name; code resolves both here: a code outside the list
is dropped, a name goes through `lore_resolve.resolve_named` under the
creator regime and comes back matched, ambiguous (candidates, the creator
picks) or new (near names shown, the creator creates, links or keeps it as
text). Nothing here writes: `lore_write_apply.apply_proposal` validates and
writes what the creator confirmed.

Ollama down surfaces as `ollama_client.OllamaError` to the route, which
answers `WRITE_UNAVAILABLE_MESSAGE` (K1: no fallback extractor).

TICKET-0119 (BRIEF-0119-G, U1, G3): the proposal call also sees the world's
event types (the coded `t` list, `event_analysis.analysis_vocabulary`) and
its sortes, and may return EVENTS: a type by code, participants by role --
an entity of the statement by its ref, or a sorte by name -- a quantity, a
place by ref; or a type the world lacks (`new_type`), which the panel offers
to create before the commit. Code reads each fail-closed (`_event`): an
unknown code drops the event with a note, a role the type lacks or a sorte
the world lacks drops that participant with a note. A known type's effects
pre-fill the event's changes on the entities the statement names that the
world already has (M-c).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlmodel import Session, select

from . import model_exchange, prompt_call
from .event_analysis import AnalysisVocabulary, analysis_vocabulary
from .event_changes import type_changes
from .event_proposals import type_definition, type_spec
from .facet_reads import creator_only_fact_ids
from .facets import FACETS
from .fact_refs import CodedRefs, code_facts
from .lore_resolve import near_candidates, normalize_surface, resolve_named
from .models import Entity, Fact, FactParticipant
from .name_index import CREATOR
from .ollama_client import chat
from .prose_render import TOKEN_RE
from .prose_tokens import tokenize
from .writes.event_types import clean_event_type
from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER

QUESTIONS_USAGE = "lore_statement_questions"
PROPOSAL_USAGE = "lore_statement_to_proposal"
MAX_QUESTIONS = 3
MAX_CODED_FACTS = 200
WRITE_UNAVAILABLE_MESSAGE = (
    "Le modèle local (Ollama) est indisponible : aucune proposition n'a pu être "
    "rédigée et rien n'a été écrit. Ton texte est conservé ; relance quand Ollama "
    "est démarré."
)
CATEGORY_TYPE: dict[str, Optional[str]] = {
    "person": "character", "place": "location", "faction": "faction", "object": "item",
    "other": None,
}
SCOPE_TYPES: tuple[str, ...] = ("world", "faction", "location", "rencontre")


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


@dataclass(frozen=True)
class DraftContext:
    """What the model may see: the named entities and the coded facts."""

    entity_lines: tuple[str, ...]
    coded: CodedRefs


def named_entity_ids(db: Session, world_id: str, statement: str) -> list[str]:
    """Entity ids the statement names, in order of first appearance, found by
    the tokenizer (a read; nothing is recorded)."""
    tokens = tokenize(db, world_id=world_id, text=statement)
    ordered: list[str] = []
    for match in TOKEN_RE.finditer(tokens.text):
        if match.group(1) not in ordered:
            ordered.append(match.group(1))
    return ordered


def world_fact_ids(db: Session, world_id: str) -> list[str]:
    """Free facts of the world with no participant (world-level lore)."""
    bound = select(FactParticipant.fact_id)
    return list(db.exec(select(Fact.id).where(
        Fact.world_id == world_id, Fact.relation_id.is_(None), Fact.event_id.is_(None),
        Fact.world_law_id.is_(None), Fact.id.not_in(bound),
    ).order_by(Fact.created_at, Fact.id)).all())


def draft_context(db: Session, world_id: str, statement: str) -> DraftContext:
    """L1: the facts of the entities the statement names, then the world-level
    facts, creator-only facts excluded, capped at `MAX_CODED_FACTS`."""
    entity_ids = named_entity_ids(db, world_id, statement)
    entity_lines = []
    fact_ids: list[str] = []
    for entity_id in entity_ids:
        entity = db.get(Entity, entity_id)
        entity_lines.append(f"- {entity.name} ({entity.type})")
        fact_ids += db.exec(select(FactParticipant.fact_id).where(
            FactParticipant.entity_id == entity_id).order_by(FactParticipant.fact_id)).all()
    fact_ids += world_fact_ids(db, world_id)
    hidden = creator_only_fact_ids(db, fact_ids)
    kept = [fid for fid in dict.fromkeys(fact_ids) if fid not in hidden][:MAX_CODED_FACTS]
    return DraftContext(entity_lines=tuple(entity_lines), coded=code_facts(db, kept))


def _facet_lines() -> str:
    return "\n".join(
        f"- {name} ({spec.granularity}) : {spec.description}"
        for name, spec in FACETS.items() if spec.granularity != "typed"
    )


Exchanges = Optional[list[model_exchange.ModelExchange]]


def _call(db: Session, usage: str, values: dict[str, str], exchanges: Exchanges) -> dict:
    """One model call. When `exchanges` is a list (TICKET-0103, BRIEF-0103-B,
    C-03), the call is appended to it as a `ModelExchange`, its raw reply
    kept before parsing, so a reply that does not parse is still recorded.
    The call itself is `prompt_call.call_json` (TICKET-0112, BRIEF-0112-A),
    handed this module's `chat`."""
    return prompt_call.call_json(db, usage, values, exchanges, chat)


def _values(context: DraftContext, statement: str, answers: str = "",
            vocab: Optional[AnalysisVocabulary] = None) -> dict[str, str]:
    values = {
        "statement": statement.strip(),
        "answers": answers.strip() or "(aucune réponse)",
        "entities": "\n".join(context.entity_lines) or "(aucune entité connue nommée)",
        "facts": "\n".join(context.coded.lines) or "(aucun fait connu)",
        "facets": _facet_lines(),
    }
    if vocab is not None:
        values.update(vocab.prompt_values())
    return values


def draft_questions(
    db: Session, world_id: str, statement: str, exchanges: Exchanges = None,
) -> list[str]:
    """At most `MAX_QUESTIONS` non-empty questions, in the model's order.
    `OllamaError` and `LlmParseError` propagate. `exchanges`: see `_call`
    (TICKET-0103, C-03)."""
    parsed = _call(db, QUESTIONS_USAGE, _values(draft_context(db, world_id, statement), statement),
                   exchanges)
    questions = [q.strip() for q in _as_list(parsed.get("questions"))
                 if isinstance(q, str) and q.strip()]
    return questions[:MAX_QUESTIONS]


def _entity(db: Session, world_id: str, raw: Any, notes: list[str]) -> Optional[dict]:
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str) or not raw["name"].strip():
        notes.append("Une entité sans nom a été ignorée.")
        return None
    ref, name = str(raw.get("ref") or ""), raw["name"].strip()
    category = raw.get("category") if raw.get("category") in CATEGORY_TYPE else "other"
    found = resolve_named(name, category, world_id, db, scope=CREATOR)
    if found.verdict == "unmatched" and category != "other":
        found = resolve_named(name, "other", world_id, db, scope=CREATOR)
    item: dict[str, Any] = {"ref": ref, "name": name, "category": category}
    if found.verdict == "matched":
        entity = db.get(Entity, found.entity_id)
        item.update(status="matched", action="existing", entity_id=entity.id,
                    name=entity.name, type=entity.type)
    elif found.verdict == "ambiguous":
        item.update(status="ambiguous", action=None, candidates=[
            {"entity_id": e.id, "name": e.name, "type": e.type}
            for e in (db.get(Entity, cid) for cid in found.candidate_ids)])
    else:
        near = near_candidates(name, world_id, db, scope=CREATOR)
        item.update(status="new", action="create", type=CATEGORY_TYPE[category], near=[
            {"entity_id": c.entity_id, "name": c.name, "type": c.entity_type, "score": c.score}
            for c in near])
    return item


def _refs(raw: Any, known: set[str]) -> list[str]:
    return [r for r in _as_list(raw) if isinstance(r, str) and r in known]


def _scopes(raw: Any, known: set[str]) -> list[dict]:
    out = []
    for scope in _as_list(raw):
        if not isinstance(scope, dict) or scope.get("scope_type") not in SCOPE_TYPES:
            continue
        if scope["scope_type"] == "world":
            out.append({"scope_type": "world"})
        elif scope.get("scope_ref") in known:
            out.append({"scope_type": scope["scope_type"], "scope_ref": scope["scope_ref"]})
    return out


def _knowers(raw: Any, known: set[str]) -> list[dict]:
    out = []
    for knower in _as_list(raw):
        if (isinstance(knower, dict) and knower.get("entity_ref") in known
                and knower.get("level") in KNOWLEDGE_LEVEL_LADDER):
            out.append({"entity_ref": knower["entity_ref"], "level": knower["level"],
                        "is_secret": knower.get("is_secret") is True,
                        "is_incorrect": knower.get("is_incorrect") is True})
    return out


def _fact(raw: Any, coded: CodedRefs, known: set[str], notes: list[str]) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    action = raw.get("action")
    action = action if action in ("create", "existing", "rewrite") else "create"
    item: dict[str, Any] = {
        "ref": str(raw.get("ref") or ""), "action": action,
        "participants": _refs(raw.get("participants"), known),
        "defaults": _scopes(raw.get("defaults"), known),
        "knowers": _knowers(raw.get("knowers"), known),
    }
    if action != "create":
        fact_id = coded.resolve(raw.get("code"))
        if fact_id is None:
            notes.append(f"Un fait désigné par un code inconnu ({raw.get('code')!r}) a été ignoré.")
            return None
        item["fact_id"] = fact_id
    if action in ("create", "rewrite"):
        content = raw.get("content")
        if not isinstance(content, str) or not content.strip():
            notes.append("Un fait sans texte a été ignoré.")
            return None
        item["content"] = content.strip()
    if action == "create":
        spec = FACETS.get(raw.get("facet"))
        if spec is None or spec.granularity == "typed":
            notes.append(f"Un fait de facette inconnue ({raw.get('facet')!r}) a été ignoré.")
            return None
        aspect = raw.get("aspect")
        item.update(facet=raw["facet"], aspect=aspect if isinstance(aspect, str) else None)
    return item


def _pairs(raw: Any, keys: tuple[str, str], known: set[str]) -> list[dict]:
    out = []
    for pair in _as_list(raw):
        if isinstance(pair, dict) and all(pair.get(k) in known for k in keys):
            out.append({k: pair[k] for k in keys})
    return out


def _event_type(db: Session, world_id: str, raw: dict, vocab: AnalysisVocabulary, notes: list[str]):
    """(type id or None, type name, {role name key: (role id or None, name)},
    counts quantity, new type definition or None), or None to drop."""
    code = raw.get("event_type")
    if code not in (None, "") and not isinstance(code, dict):
        type_id = vocab.codes.resolve(code)
        if type_id is None:
            notes.append(f"Un événement de type inconnu ({code!r}) a été ignoré.")
            return None
        view = vocab.types[type_id]
        roles = {normalize_surface(r.name): (r.id, r.name) for r in view.active_roles()}
        return type_id, view.name, roles, view.counts_quantity, None
    if not isinstance(raw.get("new_type"), dict):
        notes.append("Un événement sans type a été ignoré.")
        return None
    try:
        clean = clean_event_type(db, world_id, type_spec(raw["new_type"]))
    except ValueError as exc:
        notes.append(f"Un type d'événement proposé a été refusé ({exc}).")
        return None
    roles = {normalize_surface(r.name): (None, r.name) for r in clean.roles}
    return None, clean.name, roles, clean.counts_quantity, type_definition(clean)


def _event_participant(raw: Any, roles: dict, by_ref: dict, vocab: AnalysisVocabulary,
                       notes: list[str]) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    role = roles.get(normalize_surface(str(raw.get("role") or "")))
    if role is None:
        notes.append(f"Un participant d'un rôle inconnu ({raw.get('role')!r}) a été ignoré.")
        return None
    out = {"role_id": role[0], "role": role[1], "entity_ref": None, "sorte_id": None, "secret": None}
    if str(raw.get("sorte") or "").strip():
        name = normalize_surface(str(raw["sorte"]))
        out["sorte_id"] = next((sid for sid, s in vocab.sortes.items() if normalize_surface(s) == name), None)
        if out["sorte_id"] is None:
            notes.append(f"La sorte « {raw['sorte']} » n'existe pas : crée-la dans Vocabulaire du monde.")
            return None
        return out
    if raw.get("ref") not in by_ref:
        return None
    out["entity_ref"] = raw["ref"]
    return out


def _event(db: Session, world_id: str, raw: Any, vocab: AnalysisVocabulary, by_ref: dict,
           notes: list[str]) -> Optional[dict]:
    """One event of the model, read fail-closed (see the module docstring)."""
    if not isinstance(raw, dict):
        return None
    found = _event_type(db, world_id, raw, vocab, notes)
    if found is None:
        return None
    type_id, type_name, roles, counts, definition = found
    participants = [p for p in (_event_participant(r, roles, by_ref, vocab, notes)
                                for r in _as_list(raw.get("participants"))) if p is not None]
    quantity = raw.get("quantity")
    item: dict[str, Any] = {
        "type_id": type_id, "type_name": type_name,
        "title": str(raw.get("title") or "").strip() or type_name,
        "description": str(raw.get("description") or "").strip() or None,
        "quantity": quantity if counts and isinstance(quantity, int) and not isinstance(quantity, bool)
        and quantity >= 1 else None,
        "location_ref": raw.get("place_ref") if raw.get("place_ref") in by_ref else None,
        "participants": participants, "state_changes": [],
    }
    if definition is not None:
        item["new_type"] = definition
        return item
    known = {by_ref[p["entity_ref"]]["entity_id"]: p["entity_ref"] for p in participants
             if p["entity_ref"] and by_ref[p["entity_ref"]].get("entity_id")}
    changes = type_changes(db, world_id, vocab.types[type_id],
                           [(p["role_id"], by_ref[p["entity_ref"]].get("entity_id")) for p in participants
                            if p["entity_ref"]])
    item["state_changes"] = [{"entity_ref": known[c["entity_id"]], "attribute": c["attribute"],
                              "mode": c["mode"], "value": known.get(c["value"], c["value"])} for c in changes]
    return item


def _preset_kind(db: Session, fact_id: str) -> str:
    """The rewrite kind preselected for a fact's facet (TICKET-0105, H1)."""
    fact = db.get(Fact, fact_id)
    spec = FACETS.get(fact.facet or "") if fact is not None else None
    return spec.edit_kind if spec is not None else "correction"


def draft_proposal(
    db: Session, world_id: str, statement: str, answers: str = "", exchanges: Exchanges = None,
) -> dict:
    """The draft the writing panel edits (C-05), with the facet vocabulary the
    panel offers (names and French labels, from `FACETS`). Every entity carries a
    `status` (`matched` / `ambiguous` / `new`); every fact code is resolved to
    an id or dropped with a note. `OllamaError` and `LlmParseError`
    propagate. `exchanges`: see `_call` (TICKET-0103, C-03)."""
    context = draft_context(db, world_id, statement)
    vocab = analysis_vocabulary(db, world_id)
    parsed = _call(db, PROPOSAL_USAGE, _values(context, statement, answers, vocab), exchanges)
    notes: list[str] = []
    entities = [e for e in (_entity(db, world_id, raw, notes)
                            for raw in _as_list(parsed.get("entities"))) if e is not None]
    seen: set[str] = set()
    for index, entity in enumerate(entities, start=1):
        if not entity["ref"] or entity["ref"] in seen:
            entity["ref"] = f"e{index}"
        seen.add(entity["ref"])
    facts = [f for f in (_fact(raw, context.coded, seen, notes)
                         for raw in _as_list(parsed.get("facts"))) if f is not None]
    for index, fact in enumerate(facts, start=1):
        fact["ref"] = f"f{index}"
        if fact["action"] == "rewrite":
            fact["kind"] = _preset_kind(db, fact["fact_id"])
    by_ref = {e["ref"]: e for e in entities}
    events = [e for e in (_event(db, world_id, raw, vocab, by_ref, notes)
                          for raw in _as_list(parsed.get("events"))) if e is not None]
    for index, event in enumerate(events, start=1):
        event["ref"] = f"v{index}"
    return {
        "statement": statement.strip(), "answers": answers.strip() or None,
        "entities": entities, "facts": facts,
        "memberships": _pairs(parsed.get("memberships"), ("entity_ref", "faction_ref"), seen),
        "controls": _pairs(parsed.get("controls"), ("owner_ref", "location_ref"), seen),
        "events": events,
        "notes": notes,
        "facets": [{"name": name, "label": spec.label} for name, spec in FACETS.items()
                   if spec.granularity != "typed"],
    }
