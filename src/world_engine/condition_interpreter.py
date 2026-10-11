"""The condition interpreter: a sentence in French -> a condition tree the
creator confirms (TICKET-0112, BRIEF-0112-C; decisions A1 and T1 of the
conditions series, IA1-IK1 of TICKET-0112).

The model proposes, code validates, the creator confirms (A1): nothing here
writes. `interpret` shows the model the language (`form_lines`), the
entities the instruction names, coded lists of the world's facts (`f`), its
quest offers (`q`), skills (`s`) and attributes (`a`, TICKET-0113: a state
by its code, a choice by its label), and -- when the creator edits a
condition (IC1) -- the current tree in the model's own form, its entities
coded `e`. The model answers that form (C-03): entities by name (or by an
`e` code), every other target by code, never an id (ID1a). Code reads the
answer back (`read_answer`): codes through their list, names through
`lore_resolve.resolve_named` under the creator regime -- an ambiguous name,
or an unknown one with near names, waits for the creator's pick
(`needs_choice`, 0092: the tool never picks); then every leaf through
`writes.conditions.clean_leaf`, each error kept. Errors other than an
unknown name send the model one more call carrying them (II1); a second
failure is `refused`, the errors shown. What the language cannot say yet is
listed by the model as `unsupported` and shown as a note naming where it
will come from (IF1); a cost or a reward is never a condition (IA1).

The creator-only facts are shown to the model (IE1: a surface of the
creator; a condition on a secret is legitimate). `OllamaError` and
`LlmParseError` propagate: the route answers `INTERPRET_UNAVAILABLE_MESSAGE`
or a parse error and journals it (K1 of TICKET-0098).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlmodel import Session, select

from . import model_exchange, prompt_call
from .attribute_proposals import (
    adopt,
    is_unsaved,
    near_existing,
    read_definitions,
    spec_dict,
    spec_from_dict,
    unsaved_views,
    UnsavedAttribute,
)
from .attributes import ATTRIBUTE_FORM, AttributeView, world_attributes, world_entity_type_labels
from .condition_forms import ENTITY_TARGET_TYPES, FORM_VALUES, REQUIREMENT_TYPES, RequirementSpec
from .condition_text import FORM_PHRASES_FR, VALUE_LABELS_FR
from .conditions import CONNECTORS, SUBJECT_ROLES, ConditionTree, all_of, check_shape, leaves, node_to_dict
from .fact_refs import CodedRefs, code_facts, code_refs
from .lore_resolve import CATEGORIES, near_candidates, normalize_surface, resolve_named
from .lore_write_draft import MAX_CODED_FACTS, named_entity_ids, world_fact_ids
from .models import BASE_SKILL_DOMAINS, Entity, FactParticipant, QuestOffer, SkillDefinition
from .name_index import CREATOR
from .ollama_client import chat
from .writes.conditions import clean_condition, clean_leaf

INTERPRET_USAGE = "condition_interpret"
INTERPRET_UNAVAILABLE_MESSAGE = (
    "Le modèle local (Ollama) est indisponible : aucune condition n'a pu être "
    "proposée et rien n'a changé dans l'offre. Ta phrase est conservée ; relance "
    "quand Ollama est démarré."
)
# `resource`'s key is a label: one currency per world. Mirrors
# `frontend/src/creation/questRequirements.js` MONEY_KEY (NC1 keeps them equal).
RESOURCE_KEY = "monnaie"

ROLE_LABELS_FR: dict[str, str] = {
    "eligibility": "à qui l'offre est proposée",
    "prerequisite": "ce qu'il faut pour tenter l'étape",
    "completion": "quand l'objectif de l'étape est atteint",
}

# What each form takes as its target, in the model's form (C-03). One line
# per form of `REQUIREMENT_TYPES` (NC1): a new form is shown to the model
# the day it exists, or this check is red.
TARGET_HINTS_FR: dict[str, str] = {
    "knowledge": "un fait, par son code f",
    "relation_gte": "un personnage, par son nom ; seuil = l'appréciation minimale",
    "resource": "aucune cible ; seuil = la somme minimale",
    "location_reachable": "un lieu, par son nom",
    "has_met": "un personnage ou une entité, par son nom",
    "faction_member": "une faction, par son nom",
    "skill_rank_gte": "une compétence, par son code s ; seuil = le rang de 1 à 5",
    "quest_state": "une quête, par son code q ; valeur = son état",
    "has_debt_to": "un personnage ou une faction, par son nom",
    "no_debt_to": "un personnage ou une faction, par son nom",
    "item_held": "un objet, par son nom ; seuil = la quantité minimale",
    "attribute": "un état, par son code a ; pour un choix, valeur = un de ses libellés ; pour un nombre, "
                 "seuil = le minimum ; pour une entité, valeur = une entité par son nom, ou null pour "
                 "« quelqu'un »",
}
# The forms whose target is a code, and the list each code comes from.
CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a"}

# IF1: what the language cannot say yet, by the kind the model gives it, and
# where it will come from. IA1: a cost or a reward is a term of the offer.
UNSUPPORTED_NOTES_FR: dict[str, str] = {
    "state": "« {text} » : cet état n'existe pas encore dans ce monde ; définis-le dans Création › États, "
             "puis redemande.",
    "event": "« {text} » : ce qui s'est passé (tué, repéré, capturé…) n'est pas encore une "
             "condition ; il arrive avec le journal d'événements (TICKET-0114).",
    "time": "« {text} » : le temps (avant le jour N, pendant N tours) n'est pas encore une "
            "condition ; aucun ticket ne l'a encore.",
    "cost": "« {text} » : c'est un coût, pas une condition : ajoute-le dans « Coûts » de l'offre.",
    "reward": "« {text} » : c'est une récompense, pas une condition : ajoute-la dans « Récompenses » "
              "de l'offre.",
    "other": "« {text} » : cette forme de condition n'existe pas encore.",
}
NOTHING_PROPOSED_FR = "Le modèle n'a proposé aucune condition."
UNKNOWN_NAME_FR = "« {name} » : aucun nom de ce monde ne correspond."


# --- context -------------------------------------------------------------------

@dataclass(frozen=True)
class InterpreterContext:
    """What the model may see; the coded lists also resolve its answer."""

    entity_lines: tuple[str, ...]
    lists: dict[str, CodedRefs]  # "e", "f", "q", "s", "a"
    current: Optional[dict]
    attributes: dict[str, AttributeView] = field(default_factory=dict)  # key -> view, the `a` list's
    type_lines: tuple[str, ...] = ()  # the types a proposed definition may name (BRIEF-0113-E)


def _current_ids(tree: Optional[ConditionTree]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {"e": [], "f": [], "q": [], "s": [], "a": []}
    for spec in leaves(tree):
        for entity_id in (spec.subject_entity_id, spec.target_entity_id):
            if entity_id and entity_id not in found["e"]:
                found["e"].append(entity_id)
        if spec.type in CODE_LISTS and spec.target_key:
            found[CODE_LISTS[spec.type]].append(spec.target_key)
    return found


def _entity_label(db: Session, entity_id: str) -> str:
    entity = db.get(Entity, entity_id)
    return f"{entity.name} ({entity.type})" if entity is not None else entity_id


def _skill_pairs(db: Session, world_id: str) -> list[tuple[str, str]]:
    definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
    return [(d, d) for d in BASE_SKILL_DOMAINS] + sorted(
        ((d.id, d.name) for d in definitions), key=lambda pair: pair[1].lower())


def build_context(db: Session, world_id: str, instruction: str, current: Optional[ConditionTree],
                  unsaved: tuple = ()) -> InterpreterContext:
    """IE1: the facts of the current tree, then of the entities the
    instruction names, then the world-level facts, creator-only facts
    included, capped at `MAX_CODED_FACTS`; every offer and skill of the
    world; the current tree's entities coded `e`."""
    ids = _current_ids(current)
    named = named_entity_ids(db, world_id, instruction)
    fact_ids = list(ids["f"])
    for entity_id in named:
        fact_ids += db.exec(select(FactParticipant.fact_id).where(
            FactParticipant.entity_id == entity_id).order_by(FactParticipant.fact_id)).all()
    fact_ids += world_fact_ids(db, world_id)
    offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).all()
    attributes = {view.key: view for view in world_attributes(db, world_id)}
    attributes.update(unsaved_views(unsaved))  # the draft's proposed ones (BRIEF-0113-E)
    types = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
    lists = {
        "e": code_refs("e", ((eid, _entity_label(db, eid)) for eid in ids["e"])),
        "f": code_facts(db, list(dict.fromkeys(fact_ids))[:MAX_CODED_FACTS]),
        "q": code_refs("q", sorted(((o.id, o.title) for o in offers), key=lambda pair: pair[1].lower())),
        "s": code_refs("s", _skill_pairs(db, world_id)),
        "a": code_refs("a", ((key, attribute_line(view, types)) for key, view in attributes.items())),
    }
    lines = tuple(f"- {_entity_label(db, eid)}" for eid in named)
    return InterpreterContext(entity_lines=lines, lists=lists, attributes=attributes,
                              type_lines=tuple(f"{t} — {label}" for t, label in types.items()),
                              current=encode(current, lists, attributes) if current is not None else None)


def attribute_line(view: AttributeView, types: dict[str, str]) -> str:
    """One attribute as the model reads it in the `a` list (BRIEF-0113-D):
    its name, its kind and what it compares to, the types it applies to."""
    holders = "toute entité" if view.holder_types is None else ", ".join(
        types.get(t, t).lower() for t in view.holder_types)
    if view.kind == "choice":
        kind = "choix : " + ", ".join(label for _key, label in view.choices)
    elif view.kind == "integer":
        kind = "nombre"
    else:
        kind = "une entité : " + ", ".join(types.get(t, t).lower() for t in view.value_types)
    status = "système ; " if view.system else "à créer, proposé ; " if is_unsaved(view.key) else ""
    return f"{view.name} ({status}{kind} ; pour : {holders})"


# --- the model's form (C-03) ---------------------------------------------------

def _encode_ref(entity_id: Optional[str], lists: dict[str, CodedRefs]) -> Optional[dict]:
    return {"code": lists["e"].code_of(entity_id)} if entity_id else None


def encode(tree: ConditionTree, lists: dict[str, CodedRefs], attributes: Optional[dict] = None) -> dict:
    """A clean tree in the model's form: entities by `e` code, facts,
    offers, skills and attributes by their code; an attribute's choice by
    its label, its entity value by `e` code (BRIEF-0113-D)."""
    if tree.op != "leaf":
        out: dict[str, Any] = {"op": tree.op, "children": [encode(c, lists, attributes) for c in tree.children]}
        if tree.op == "at_least":
            out["n"] = tree.n
        return out
    spec = tree.leaf
    target = _encode_ref(spec.target_entity_id, lists)
    value: Any = spec.value
    if spec.type in CODE_LISTS:
        target = {"code": lists[CODE_LISTS[spec.type]].code_of(spec.target_key)}
    if spec.type == ATTRIBUTE_FORM:
        view = (attributes or {}).get(spec.target_key)
        if view is not None and view.kind == "choice":
            value = dict(view.choices).get(spec.value, spec.value)
        elif view is not None and view.kind == "entity":
            value = _encode_ref(spec.target_entity_id, lists)
    return {"op": "leaf", "form": spec.type,
            "subject": spec.subject_role or _encode_ref(spec.subject_entity_id, lists),
            "target": target, "threshold": spec.threshold, "value": value}


def form_lines() -> str:
    """The language for the prompt: one line per form, its French phrase,
    its target and, for a form that compares to a value, its values."""
    lines = []
    for form in REQUIREMENT_TYPES:
        line = f"- {form} : {FORM_PHRASES_FR[form]} — cible : {TARGET_HINTS_FR[form]}"
        if form in FORM_VALUES:
            line += " ; valeurs : " + ", ".join(
                f"{value} ({VALUE_LABELS_FR[form][value]})" for value in FORM_VALUES[form])
        lines.append(line)
    return "\n".join(lines)


# --- reading the answer --------------------------------------------------------

@dataclass
class Reading:
    """The model's tree as code read it: `pending` is the dict form of
    `conditions.node_to_dict` whose leaves may also carry `subject_mention`
    / `target_mention` (a name still to pick); `mentions` the names it
    used; `errors` what refuses it, `name_errors` the unknown names."""

    pending: Optional[dict] = None
    mentions: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    name_errors: list[str] = field(default_factory=list)
    defined: dict[str, str] = field(default_factory=dict)  # the model's `define` ref -> `new:<ref>` (E)


def _mention(db: Session, world_id: str, raw: dict, reading: Reading) -> Optional[str]:
    """The ref of the mention `raw` names (`{"name", "kind"}`), recorded once."""
    name = str(raw.get("name") or "").strip()
    kind = raw.get("kind") if raw.get("kind") in CATEGORIES else "other"
    for mention in reading.mentions:
        if mention["name"].lower() == name.lower() and mention["kind"] == kind:
            return mention["ref"]
    mention: dict[str, Any] = {"ref": f"m{len(reading.mentions) + 1}", "name": name, "kind": kind,
                               "entity_id": None, "choices": []}
    found = resolve_named(name, kind, world_id, db, scope=CREATOR)
    if found.verdict == "unmatched" and kind != "other":
        found = resolve_named(name, "other", world_id, db, scope=CREATOR)
    if found.verdict == "matched":
        mention.update(status="matched", entity_id=found.entity_id)
    elif found.verdict == "ambiguous":
        mention.update(status="ambiguous", choices=[
            {"entity_id": e.id, "name": e.name, "type": e.type}
            for e in (db.get(Entity, cid) for cid in found.candidate_ids)])
    else:
        mention.update(status="unmatched", choices=[
            {"entity_id": c.entity_id, "name": c.name, "type": c.entity_type, "score": c.score}
            for c in near_candidates(name, world_id, db, scope=CREATOR)])
        if not mention["choices"]:
            reading.name_errors.append(UNKNOWN_NAME_FR.format(name=name))
    reading.mentions.append(mention)
    return mention["ref"]


def _entity(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading: Reading,
            where: str) -> tuple[Optional[str], Optional[str]]:
    """An entity reference -> (entity id, mention ref); an error noted."""
    if isinstance(raw, dict) and raw.get("code") is not None:
        entity_id = ctx.lists["e"].resolve(raw["code"])
        if entity_id is None:
            reading.errors.append(f"{where}code inconnu {raw['code']!r} (une entité se nomme par son nom)")
        return entity_id, None
    if isinstance(raw, dict) and str(raw.get("name") or "").strip():
        ref = _mention(db, world_id, raw, reading)
        mention = next(m for m in reading.mentions if m["ref"] == ref)
        return (mention["entity_id"], None) if mention["status"] == "matched" else (None, ref)
    reading.errors.append(f"{where}une entité attendue, reçu {raw!r}")
    return None, None


def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, reading: Reading, where: str) -> dict:
    form = raw.get("form")
    out: dict[str, Any] = {"op": "leaf", "type": form, "subject_role": None, "subject_entity_id": None,
                           "target_entity_id": None, "target_key": None, "threshold": raw.get("threshold"),
                           "value": raw.get("value")}
    if form not in REQUIREMENT_TYPES:
        reading.errors.append(f"{where}forme inconnue {form!r}")
        return out
    subject = raw.get("subject") or "doer"
    if isinstance(subject, str) and subject in SUBJECT_ROLES:
        out["subject_role"] = subject
    else:
        if isinstance(subject, str):  # a bare name: a person
            subject = {"name": subject, "kind": "person"}
        out["subject_entity_id"], out["subject_mention"] = _entity(db, world_id, subject, ctx, reading, where)
    target = raw.get("target")
    if form == ATTRIBUTE_FORM and isinstance(target, dict) and "define" in target:
        target = {"key": reading.defined.get(str(target["define"]))}
        if target["key"] is None:
            reading.errors.append(f"{where}état proposé inconnu {raw['target']['define']!r} (attendu : un "
                                  "ref de « define »)")
    if isinstance(target, str) and form in ENTITY_TARGET_TYPES:  # a bare name
        target = {"name": target, "kind": "other"}
    if form in ENTITY_TARGET_TYPES:
        out["target_entity_id"], out["target_mention"] = _entity(db, world_id, target, ctx, reading, where)
    elif form == ATTRIBUTE_FORM and isinstance(target, dict) and "key" in target:
        out["target_key"] = target["key"]
    elif form in CODE_LISTS:
        code = target.get("code") if isinstance(target, dict) else target
        out["target_key"] = ctx.lists[CODE_LISTS[form]].resolve(code)
        if out["target_key"] is None:
            reading.errors.append(f"{where}code inconnu {code!r} (attendu : un code {CODE_LISTS[form]})")
    elif form == "resource":
        out["target_key"] = RESOURCE_KEY
    if form == ATTRIBUTE_FORM and out["target_key"] is not None:
        _attribute_value(db, world_id, raw, ctx, reading, where, out)
    return {k: v for k, v in out.items() if v is not None or not k.endswith("_mention")}


def _attribute_value(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, reading: Reading,
                     where: str, out: dict) -> None:
    """What an `attribute` leaf compares to, by its attribute's kind
    (BRIEF-0113-D): a choice's label -- or its stored value -- read back to
    its key; an integer's threshold kept; an entity named (or null: anyone)
    resolved like any target."""
    view = ctx.attributes.get(out["target_key"])
    if view is None:
        return
    value = raw.get("value")
    out["value"] = None
    if view.kind == "integer":
        return
    out["threshold"] = None
    if view.kind == "entity":
        if value is not None:
            if isinstance(value, str):
                value = {"name": value, "kind": "other"}
            out["target_entity_id"], out["target_mention"] = _entity(db, world_id, value, ctx, reading, where)
        return
    wanted = normalize_surface(str(value or ""))
    for key, label in view.choices:
        if value == key or (wanted and normalize_surface(label) == wanted):
            out["value"] = key
            return
    labels = ", ".join(label for _key, label in view.choices)
    reading.errors.append(f"{where}« {value} » n'est pas un libellé de « {view.name} » (libellés : {labels})")


def _read(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading: Reading, path: str) -> dict:
    where = f"condition {path} : "
    if not isinstance(raw, dict):
        reading.errors.append(f"{where}un objet attendu, reçu {raw!r}")
        return {"op": "all", "children": []}
    if raw.get("op") == "leaf":
        return _leaf(db, world_id, raw, ctx, reading, where)
    if raw.get("op") not in CONNECTORS:
        reading.errors.append(f"{where}connecteur inconnu {raw.get('op')!r}")
        return {"op": "all", "children": []}
    children = raw.get("children") if isinstance(raw.get("children"), list) else []
    out: dict[str, Any] = {"op": raw["op"], "children": [
        _read(db, world_id, child, ctx, reading, f"{path}.{i}") for i, child in enumerate(children, start=1)]}
    if raw["op"] == "at_least":
        out["n"] = raw.get("n")
    return out


def read_answer(db: Session, world_id: str, raw: Any, ctx: InterpreterContext,
                defined: Optional[dict[str, str]] = None) -> Reading:
    """The model's `condition` read back: codes and names resolved, nothing
    validated yet. None reads as no tree. `defined`: the model's `define`
    refs, already read (`attribute_proposals.read_definitions`)."""
    reading = Reading(defined=dict(defined or {}))
    if raw is not None:
        reading.pending = _read(db, world_id, raw, ctx, reading, "1")
    return reading


# --- validation ----------------------------------------------------------------

def waiting(pending: Optional[dict]) -> bool:
    """A leaf of `pending` still waits for a name to be picked."""
    if pending is None:
        return False
    if pending.get("op") == "leaf":
        return "subject_mention" in pending or "target_mention" in pending
    return any(waiting(child) for child in pending.get("children", []))


def bind(pending: dict, mentions: list[dict], bindings: dict[str, str]) -> dict:
    """`pending` with every waiting name replaced by the creator's pick.
    `ValueError` when a waiting mention has no pick or a pick outside its
    choices."""
    by_ref = {m["ref"]: m for m in mentions}
    if pending.get("op") != "leaf":
        return {**pending, "children": [bind(c, mentions, bindings) for c in pending.get("children", [])]}
    out = dict(pending)
    for side in ("subject", "target"):
        ref = out.pop(f"{side}_mention", None)
        if ref is None:
            continue
        pick = bindings.get(ref)
        if pick not in {c["entity_id"] for c in by_ref.get(ref, {}).get("choices", [])}:
            raise ValueError(f"« {by_ref.get(ref, {}).get('name', ref)} » : choisis un des noms proposés")
        out[f"{side}_entity_id"] = pick
    return out


def _tree(raw: dict) -> ConditionTree:
    if raw.get("op") == "leaf":
        return ConditionTree(op="leaf", leaf=RequirementSpec(
            type=raw["type"], subject_role=raw.get("subject_role"), subject_entity_id=raw.get("subject_entity_id"),
            target_entity_id=raw.get("target_entity_id"), target_key=raw.get("target_key"),
            threshold=raw.get("threshold"), value=raw.get("value")))
    return ConditionTree(op=raw["op"], n=raw.get("n"), children=tuple(_tree(c) for c in raw.get("children", [])))


def validate(db: Session, world_id: str, pending: dict,
             unsaved: Optional[dict] = None) -> tuple[Optional[ConditionTree], list[str]]:
    """A bound tree checked whole: its shape, then every leaf on its own
    (`clean_leaf`), so every error is reported at once. (tree, []) or
    (None, errors). `unsaved`: the proposed attributes' views, by `new:`
    key (BRIEF-0113-E)."""
    try:
        tree = _tree(pending)
        check_shape(tree)
    except (ValueError, KeyError, TypeError) as exc:
        return None, [f"forme de l'arbre : {exc}"]
    errors = []
    for index, spec in enumerate(leaves(tree), start=1):
        try:
            clean_leaf(db, world_id, spec, where=f"condition {index} ({spec.type}) : ", unsaved=unsaved)
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        return None, errors
    clean = clean_condition(db, world_id, tree, unsaved=unsaved)
    # A lone leaf is proposed as the editor's list sends it back: `all` of it
    # (`conditions.flat_leaves`, T1), so an unchanged insert saves as proposed.
    return (all_of(leaves(clean)) if clean.op == "leaf" else clean), []


# --- interpretation ------------------------------------------------------------

@dataclass
class Interpretation:
    """What `interpret` and `resolve` give the route (C-04)."""

    outcome: str  # proposed | needs_choice | refused
    tree: Optional[ConditionTree]
    pending: Optional[dict]
    mentions: list[dict]
    notes: list[str]
    errors: list[str]
    retried: bool = False
    # BRIEF-0113-E: the attributes this answer proposes -- `{ref, definition,
    # near}`, `near` the attributes whose name is near (the creator picks).
    definitions: list[dict] = field(default_factory=list)

    def payload(self, current: Optional[ConditionTree], bindings: Optional[dict] = None) -> dict:
        """The journal's payload (`writes.condition_drafts.PAYLOAD_KEYS`)."""
        return {"current": node_to_dict(current), "pending": self.pending, "mentions": self.mentions,
                "bindings": bindings or {}, "proposed": node_to_dict(self.tree),
                "notes": self.notes, "errors": self.errors, "definitions": self.definitions}


Exchanges = Optional[list[model_exchange.ModelExchange]]


def _call(db: Session, values: dict[str, str], exchanges: Exchanges) -> dict:
    """One model call, through `prompt_call.call_json` with this module's
    `chat`."""
    return prompt_call.call_json(db, INTERPRET_USAGE, values, exchanges, chat)


def _lines(lines) -> str:
    return "\n".join(lines) or "(aucun)"


def prompt_values(ctx: InterpreterContext, role: str, instruction: str, errors: list[str]) -> dict[str, str]:
    """The prompt's variables (C-05)."""
    return {
        "role": ROLE_LABELS_FR[role], "forms": form_lines(), "entities": _lines(ctx.entity_lines),
        "tree_entities": _lines(ctx.lists["e"].lines), "facts": _lines(ctx.lists["f"].lines),
        "offers": _lines(ctx.lists["q"].lines), "skills": _lines(ctx.lists["s"].lines),
        "attributes": _lines(ctx.lists["a"].lines), "entity_types": _lines(ctx.type_lines),
        "current": json.dumps(ctx.current, ensure_ascii=False) if ctx.current is not None else "(aucune)",
        "instruction": instruction.strip(), "errors": _lines(f"- {e}" for e in errors),
    }


def _notes(raw: Any) -> list[str]:
    notes = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and str(item.get("text") or "").strip():
            kind = item.get("kind") if item.get("kind") in UNSUPPORTED_NOTES_FR else "other"
            notes.append(UNSUPPORTED_NOTES_FR[kind].format(text=str(item["text"]).strip()))
    return notes


def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retried: bool,
            proposals: Optional[Proposals] = None) -> Interpretation:
    proposals = proposals or Proposals()

    def done(outcome, tree=None, errors=()):
        return Interpretation(outcome, tree, reading.pending, reading.mentions, notes, list(errors), retried,
                              proposals.entries())

    if reading.errors or reading.name_errors:
        return done("refused", errors=reading.errors + reading.name_errors)
    if reading.pending is None:
        return done("refused", errors=[] if notes else [NOTHING_PROPOSED_FR])
    if waiting(reading.pending):
        return done("needs_choice")
    tree, errors = validate(db, world_id, reading.pending, proposals.views())
    if tree is None:
        return done("refused", errors=errors)
    return done("needs_choice" if proposals.near else "proposed", tree)


@dataclass
class Proposals:
    """BRIEF-0113-E: the draft's unsaved attributes (`unsaved`), those this
    answer proposes (`new`), and, for each new one, the attributes whose
    name is near (`near`, by ref)."""

    unsaved: tuple = ()
    new: list = field(default_factory=list)
    near: dict[str, list[dict]] = field(default_factory=dict)

    def views(self) -> dict[str, AttributeView]:
        return unsaved_views(tuple(self.unsaved) + tuple(self.new))

    def entries(self) -> list[dict]:
        return [{"ref": item.ref, "definition": spec_dict(item.spec), "near": self.near.get(item.ref, [])}
                for item in self.new]


def _answer(db: Session, world_id: str, parsed: dict, ctx: InterpreterContext, unsaved: tuple,
            retried: bool) -> Interpretation:
    """One answer read and settled: its `define` block first (the new
    attributes join the context), then its condition."""
    taken = {item.ref for item in unsaved}
    new, defined, errors = read_definitions(db, world_id, parsed.get("define"), taken, list(unsaved))
    ctx.attributes.update(unsaved_views(new))
    reading = read_answer(db, world_id, parsed.get("condition"), ctx, defined)
    reading.errors[:0] = errors
    proposals = Proposals(unsaved=unsaved, new=new, near=near_existing(db, world_id, new, list(unsaved)))
    return _settle(db, world_id, reading, _notes(parsed.get("unsupported")), retried, proposals)


def interpret(
    db: Session, world_id: str, role: str, instruction: str, current: Optional[ConditionTree],
    exchanges: Exchanges = None, unsaved: tuple = (),
) -> Interpretation:
    """II1: one call, and one more carrying the errors when code refused the
    first answer for anything but an unknown name. `OllamaError` and
    `LlmParseError` propagate. `unsaved`: the offer draft's proposed
    attributes not saved yet (BRIEF-0113-E, WN2), shown to the model and
    named by its leaves."""
    ctx = build_context(db, world_id, instruction, current, unsaved)
    parsed = _call(db, prompt_values(ctx, role, instruction, []), exchanges)
    result = _answer(db, world_id, parsed, ctx, unsaved, retried=False)
    if result.outcome == "refused" and _retryable(result):
        ctx = build_context(db, world_id, instruction, current, unsaved)
        parsed = _call(db, prompt_values(ctx, role, instruction, result.errors), exchanges)
        result = _answer(db, world_id, parsed, ctx, unsaved, retried=True)
    return result


def _retryable(result: Interpretation) -> bool:
    """II1: an error the model may fix -- not an unknown name, not an
    answer with no condition at all."""
    names = {UNKNOWN_NAME_FR.format(name=m["name"]) for m in result.mentions if m["status"] == "unmatched"}
    return any(e not in names and e != NOTHING_PROPOSED_FR for e in result.errors)


def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], notes: list[str],
            bindings: dict[str, str], definitions: tuple = (), unsaved: tuple = ()) -> Interpretation:
    """The creator's picks applied to a `needs_choice` proposal; no model
    call. `ValueError` when a pick is missing or outside its choices. A
    proposed attribute near another (BRIEF-0113-E, WK2) is picked by its
    ref: `new` keeps it, an existing key moves its leaves there (`adopt`) --
    a label that attribute does not have refuses the proposal. The adopted
    one stays in `definitions`, marked `adopted` with its key."""
    bound = bind(pending, mentions, bindings)
    new, errors, adopted = [], [], []
    for entry in definitions:
        pick = bindings.get(entry["ref"])
        if entry.get("adopted"):
            adopted.append(entry)
            continue
        if entry.get("near") and pick != "new":
            if pick not in {n["key"] for n in entry["near"]}:
                raise ValueError(f"« {entry['definition']['name']} » : choisis un état existant ou « créer »")
            try:
                bound = adopt(db, world_id, bound, entry["ref"], pick, unsaved_views(unsaved))
            except ValueError as exc:
                errors.append(str(exc))
            adopted.append({**entry, "adopted": pick})
            continue
        new.append(UnsavedAttribute(ref=entry["ref"], spec=spec_from_dict(entry["definition"])))
    proposals = Proposals(unsaved=unsaved, new=new)
    tree = None
    if not errors:
        tree, errors = validate(db, world_id, bound, proposals.views())
    outcome = "proposed" if tree is not None else "refused"
    # An adopted proposal stays in the journal with the key it went to
    # (the dashboard of TICKET-0115 counts them); no card shows it.
    return Interpretation(outcome, tree, bound, mentions, list(notes), errors, False,
                          proposals.entries() + adopted)


def confirm(db: Session, world_id: str, proposed: Optional[dict], unsaved: tuple,
            edited: tuple) -> tuple[Optional[ConditionTree], list[str]]:
    """BRIEF-0113-E: the proposed tree checked again against the definitions
    as the creator confirmed them (`edited`, perhaps retouched in the card)
    and the draft's other unsaved ones. (tree, []) or (None, errors)."""
    if proposed is None:
        return None, []
    return validate(db, world_id, proposed, unsaved_views(tuple(unsaved) + tuple(edited)))
