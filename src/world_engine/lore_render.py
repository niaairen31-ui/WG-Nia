"""The renderer neither proposes nor judges -- it renders. It receives the
rows the selectors returned and nothing else: no `Session`, no `select(`,
no entity id it can look up. Only the `answered` verdict reaches the model;
every empty verdict is rendered by code, because a model asked to explain
an absence will fill it.

(TICKET-0085, BRIEF-0085-d.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .lore_prompt import RenderSpec
from .lore_query import LoreResult
from .ollama_client import OllamaError, chat


@dataclass(frozen=True)
class RenderedAnswer:
    prose: str
    renderer: str  # "model" | "template" | "deterministic"
    trace: list[dict]


# --- the section contract (BRIEF-0085-d item 2) --------------------------
# The vocabulary is the union of what the shipped selectors emit: identity,
# relations, knowledge, memberships, goals from entity_dossier, and factions
# from world_factions (BRIEF-0085-d item 3). Order here is the order rows
# are grouped for both the model prompt and the template fallback.

def _format_identity(row: dict) -> str:
    return f"{row.get('name')} ({row.get('type')}) : {row.get('description') or '(sans description)'}"


def _format_relations(row: dict) -> str:
    other = row.get("other_entity_name") or row.get("other_entity_id")
    line = f"{other} — {row.get('type')} ({row.get('direction')}, intensité {row.get('intensity')})"
    if row.get("notes"):
        line += f" : {row['notes']}"
    return line


def _format_knowledge(row: dict) -> str:
    suffix = " (croyance fausse)" if row.get("is_incorrect") else ""
    return f"{row.get('subject')} — {row.get('level')} : {row.get('content')}{suffix}"


def _format_memberships(row: dict) -> str:
    return f"{row.get('faction_name')} ({row.get('role')})"


def _format_goals(row: dict) -> str:
    return f"{row.get('description')} [{row.get('status')}, {row.get('horizon')}, {row.get('kind')}]"


def _format_factions(row: dict) -> str:
    return f"{row.get('name')} ({row.get('faction_type')}) : {row.get('description') or '(sans description)'}"


_SECTION_FORMATTERS: dict[str, Callable[[dict], str]] = {
    "identity": _format_identity,
    "relations": _format_relations,
    "knowledge": _format_knowledge,
    "memberships": _format_memberships,
    "goals": _format_goals,
    "factions": _format_factions,
}


def _group_rows_by_section(rows: tuple[dict, ...]) -> dict[str, list[dict]]:
    """Groups `rows` by their `"section"` key, in `_SECTION_FORMATTERS`'s
    vocabulary. An unknown section RAISES -- it is never skipped, and rows
    are never dropped to keep a render from failing (BRIEF-0085-d item 2).
    `execute_plan` (lore_query.py) already guarantees every row carries a
    `"section"`; this is the vocabulary guard, not the presence guard."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        section = row.get("section")
        if section not in _SECTION_FORMATTERS:
            raise ValueError(
                f"lore_render: row carries unknown section {section!r} -- "
                "rows are never dropped to keep a render from failing"
            )
        grouped.setdefault(section, []).append(row)
    return grouped


def _serialize_rows_by_section(rows: tuple[dict, ...]) -> str:
    """Rows serialized by section, in the section-contract order, for the
    model prompt (BRIEF-0085-d item 7): the model sees the question and
    these rows and nothing else."""
    grouped = _group_rows_by_section(rows)
    blocks: list[str] = []
    for section, section_rows in grouped.items():
        formatter = _SECTION_FORMATTERS[section]
        lines = "\n".join(f"- {formatter(row)}" for row in section_rows)
        blocks.append(f"[{section}]\n{lines}")
    return "\n\n".join(blocks)


def render_template(result: LoreResult) -> RenderedAnswer:
    """Deterministic fallback for the `answered` verdict when the model is
    unreachable: one short paragraph per section present, each row rendered
    by its `_SECTION_FORMATTERS` entry (BRIEF-0085-d item 8)."""
    grouped = _group_rows_by_section(result.rows)
    paragraphs: list[str] = []
    for section, section_rows in grouped.items():
        formatter = _SECTION_FORMATTERS[section]
        paragraphs.append("; ".join(formatter(row) for row in section_rows))
    return RenderedAnswer(prose="\n\n".join(paragraphs), renderer="template", trace=result.trace)


# --- deterministic verdict messages (BRIEF-0085-d item 5) -----------------
# Copied verbatim -- these are the distinction the ticket is built on. Six
# module-level constants, never inline literals, so a paraphrase is visible
# in a diff (R13).

_UNKNOWN_ENTITY_WITH_NEAR = (
    "Aucune entité nommée « {surface_form} » dans ce monde. Noms proches : {noms}."
)
_UNKNOWN_ENTITY_WITHOUT_NEAR = (
    "Aucune entité nommée « {surface_form} » dans ce monde, et aucun nom proche."
)
_SILENT_CANON_WITH_ENTITY = "{nom} existe. Le canon ne détient rien sur ce point."
_SILENT_CANON_WITHOUT_ENTITY = "Le canon ne détient rien sur ce point."
_UNSUPPORTED_SELECTOR = (
    "Je ne sais pas encore interroger : {selector}. C'est une limite de l'outil, pas du monde."
)
_AMBIGUOUS_MENTION_HEADER = "{count_phrase} portent le nom « {surface_form} ». Laquelle ?"


def _render_unknown_entity(result: LoreResult) -> str:
    """One block per unmatched surface form, in plan order. No near-candidate
    source exists yet anywhere upstream (`resolve_named` has no fuzzy rung) --
    the "with near candidates" wording stays a real branch for when one does,
    but is unreachable today; every case renders the "without" form."""
    blocks = [
        _UNKNOWN_ENTITY_WITHOUT_NEAR.format(surface_form=surface_form)
        for surface_form in result.unmatched_surface_forms
    ]
    return "\n\n".join(blocks)


def _render_silent_canon(result: LoreResult) -> str:
    """`result.rows` still carries the resolved entity's `identity` row even
    on a silent-canon verdict (`execute_plan`'s `context_sections` carve-out)
    -- if present, its `name` is the mention form; if `rows` is empty (the
    `world_factions`-with-no-faction case, where no mention was ever
    resolved), there is no name to put in the sentence."""
    identity_row = next((row for row in result.rows if row.get("section") == "identity"), None)
    if identity_row is not None:
        return _SILENT_CANON_WITH_ENTITY.format(nom=identity_row.get("name"))
    return _SILENT_CANON_WITHOUT_ENTITY


def _render_ambiguous(result: LoreResult, candidates: dict[str, list[dict]]) -> str:
    """One block per ambiguous mention, in plan order. The surface form for
    each block comes from `result.trace` (the mention-resolution entries,
    filtered to `verdict == "ambiguous"`, preserve the same plan order as
    `result.ambiguous_mentions` -- both are built from the same single pass
    over `plan.mentions` in `lore_query._resolve_mentions`/`execute_plan`).
    `candidates` supplies the name/type/description/location detail no
    `Session`-free function could look up itself."""
    ambiguous_trace = [entry for entry in result.trace if entry.get("verdict") == "ambiguous"]
    blocks: list[str] = []
    for mention, trace_entry in zip(result.ambiguous_mentions, ambiguous_trace):
        surface_form = trace_entry["surface_form"]
        candidate_rows = candidates.get(mention["ref"], [])
        n = len(candidate_rows) or len(mention["candidate_ids"])
        count_phrase = "Deux entités" if n == 2 else f"{n} entités"
        lines = [_AMBIGUOUS_MENTION_HEADER.format(count_phrase=count_phrase, surface_form=surface_form)]
        for candidate in candidate_rows:
            line = f"- {candidate['name']} ({candidate['type']}) : {candidate.get('description') or '(sans description)'}"
            if candidate.get("location_name"):
                line += f" — {candidate['location_name']}"
            lines.append(line)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_deterministic(result: LoreResult, candidates: dict[str, list[dict]]) -> RenderedAnswer:
    if result.verdict == "unknown_entity":
        prose = _render_unknown_entity(result)
    elif result.verdict == "silent_canon":
        prose = _render_silent_canon(result)
    elif result.verdict == "unsupported_selector":
        prose = _UNSUPPORTED_SELECTOR.format(selector=result.rejection_reason)
    elif result.verdict == "ambiguous_mention":
        prose = _render_ambiguous(result, candidates)
    else:
        raise ValueError(f"lore_render: unexpected verdict {result.verdict!r}")
    return RenderedAnswer(prose=prose, renderer="deterministic", trace=result.trace)


def _call_model(result: LoreResult, question: str, spec: RenderSpec) -> str:
    user_message = (
        spec.user_template
        .replace("{question}", question)
        .replace("{rows}", _serialize_rows_by_section(result.rows))
    )
    raw = chat(
        [
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": user_message},
        ],
        model=spec.model,
    )
    return raw.strip()


def render(
    result: LoreResult, question: str, spec: RenderSpec, candidates: dict[str, list[dict]]
) -> RenderedAnswer:
    """No `Session` parameter -- the structural guarantee, not a convention
    (R10). `candidates` is `{}` on every verdict other than
    `ambiguous_mention`; `spec` is the chantier's shared `lore_prompt.load`
    result, resolved by the caller, which does hold a `Session`.

    Every verdict other than `answered` is rendered by code before any model
    call is possible (R11) -- an empty retrieval can never be filled in by
    the model. One `chat` attempt on the `answered` path; `OllamaError` falls
    through to `render_template` (R12); `LlmParseError` is never caught here
    -- the renderer returns prose, not JSON."""
    if result.verdict != "answered":
        return _render_deterministic(result, candidates)
    try:
        prose = _call_model(result, question, spec)
    except OllamaError:
        return render_template(result)
    return RenderedAnswer(prose=prose, renderer="model", trace=result.trace)
