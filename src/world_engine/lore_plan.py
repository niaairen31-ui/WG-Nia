"""The model reads the question and names selectors. It never receives canon
rows here, never writes a query, and never chooses between two entities
that share a name. Its output is parsed through `llm_parse` and validated
against the whitelist before a single row is read; anything it names that
is not in `SELECTORS` is a rejected plan, not an improvised query.

(TICKET-0085, BRIEF-0085-c.)
"""

from __future__ import annotations

from sqlmodel import Session

from . import llm_parse, lore_prompt
from .lore_query import LorePlan, PlanCall, PlanMention
from .ollama_client import chat

# Independent of lore_resolve._CATEGORY_ENTITY_TYPE on purpose: this is the
# vocabulary the MODEL is told about, and the G1 check (lore_isolation R9)
# asserts the two stay equal rather than one importing the other -- a
# category added to one without the other fails the check instead of
# silently drifting apart. Five since TICKET-0092 (BRIEF-0092-c): `object`
# and `other` make every entity nameable on the creator surfaces.
_MENTION_CATEGORIES: tuple[str, ...] = ("place", "person", "faction", "object", "other")

# One line per selector, keyed by name; the G1 check (lore_isolation R8)
# asserts this key set equals SELECTORS, so a selector added later without a
# description fails the check instead of silently becoming invisible to the
# planner.
_SELECTOR_DESCRIPTIONS: dict[str, str] = {
    "entity_dossier": (
        "entity_dossier(entity_id, $world) -- dossier complet sur UNE entite "
        "nommee : identite, relations, savoirs, appartenances, objectifs."
    ),
    "world_factions": (
        "world_factions($world) -- une ligne par faction active du monde."
    ),
    "who_knows_about": (
        "who_knows_about(entity_id, $world) -- qui, dans le monde, détient un "
        "savoir portant sur UNE entité nommée : un connaisseur par ligne, avec "
        "son niveau."
    ),
}

def _render_selectors() -> str:
    return "\n".join(f"- {name}: {desc}" for name, desc in _SELECTOR_DESCRIPTIONS.items())


def _coerce_mention(raw: object) -> PlanMention:
    if not isinstance(raw, dict):
        raise llm_parse.LlmParseError(f"lore_plan: mention is not an object: {raw!r}")
    ref = raw.get("ref")
    surface_form = raw.get("surface_form")
    category = raw.get("category")
    if not isinstance(ref, str) or not ref:
        raise llm_parse.LlmParseError(f"lore_plan: mention missing a string ref: {raw!r}")
    if not isinstance(surface_form, str) or not surface_form:
        raise llm_parse.LlmParseError(f"lore_plan: mention missing a string surface_form: {raw!r}")
    if category not in _MENTION_CATEGORIES:
        # A category outside the five literals is a rejected plan, never a
        # coerced one (BRIEF-0085-c item 4) -- resolve_named's
        # _CATEGORY_ENTITY_TYPE lookup would KeyError on anything else.
        raise llm_parse.LlmParseError(f"lore_plan: mention {ref!r} has an unsupported category: {category!r}")
    return PlanMention(ref=ref, surface_form=surface_form, category=category)


def _coerce_call(raw: object) -> PlanCall:
    if not isinstance(raw, dict):
        raise llm_parse.LlmParseError(f"lore_plan: call is not an object: {raw!r}")
    selector = raw.get("selector")
    args = raw.get("args")
    if not isinstance(selector, str) or not selector:
        raise llm_parse.LlmParseError(f"lore_plan: call missing a string selector: {raw!r}")
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise llm_parse.LlmParseError(f"lore_plan: call {selector!r} has a non-string arg list: {raw!r}")
    return PlanCall(selector=selector, args=tuple(args))


def draft_plan(question: str, world_id: str, db: Session) -> LorePlan:
    """Builds the prompt, calls the model through the resolved
    `lore_prompt.RenderSpec`, parses the reply with `llm_parse.extract_object`,
    and maps the JSON into a `LorePlan`. `LlmParseError` propagates -- a
    malformed reply, a missing template, or an out-of-vocabulary mention
    category is a failed draft, never silently coerced into an empty plan.
    `validate_plan` (lore_query.py) still runs afterward against the selector
    whitelist; this function only guards the shape it itself constructs."""
    spec = lore_prompt.load(db, "lore_question_to_plan")
    user_message = (
        spec.user_template
        .replace("{selectors}", _render_selectors())
        .replace("{question}", question)
    )
    raw = chat(
        [
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": user_message},
        ],
        model=spec.model,
        format="json",
    )
    parsed = llm_parse.extract_object(raw)

    raw_mentions = parsed.get("mentions")
    raw_mentions = raw_mentions if isinstance(raw_mentions, list) else []
    mentions = tuple(_coerce_mention(m) for m in raw_mentions)

    raw_calls = parsed.get("calls")
    raw_calls = raw_calls if isinstance(raw_calls, list) else []
    calls = tuple(_coerce_call(c) for c in raw_calls)

    return LorePlan(mentions=mentions, calls=calls)
