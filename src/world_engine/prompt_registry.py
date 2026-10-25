"""Prompt registry — code facts about every seeded `prompt_template.usage`
(BRIEF-0008-a, schema v1.67).

Two responsibilities, kept deliberately separate:

- `effective_model(template, default)` — the ONE resolver every templated
  model call routes through. Pure: no DB access, no import of cockpit
  modules. `template.model` is a creator override (non-NULL); NULL means
  "code decides", i.e. the caller's own default. With `model` NULL on every
  row (the state of a fresh seed, and every row until a write path ships),
  this always returns `default` unchanged — runtime behavior is
  bit-identical to before this module existed.
- `PROMPT_REGISTRY` — a plain dict of code facts per usage (surface,
  world_scoped resolution semantics, dry-run capability, static call
  sites). DB owns prompt text + the `model` override; this registry owns
  the wiring facts a reader (BRIEF-0008-b's API) needs to display "what
  will actually run" without re-deriving it from scratch. Adding a new
  prompt usage costs one entry here — no other structural change.

`default_model` is intentionally NOT a plain string on `PromptSpec`: it is
a zero-argument callable resolved at READ time from the same symbols the
call sites use (`ollama_client.DEFAULT_MODEL` / `entity_author.AUTHOR_MODEL`),
so an env override of `WORLD_ENGINE_OLLAMA_MODEL` shows through, and so this
module never imports `entity_author` at module load time (entity_author
imports `effective_model` from here — a plain top-level import the other
way would cycle).

`premise` (TICKET-0124, C1) -- the regime in which the world premise reaches
this usage's text: `creator`, `player`, or `none` with its reason.
`world_premise.fill` reads it; a check holds the 47 entries to the partition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from . import ollama_client

if TYPE_CHECKING:
    from .models import PromptTemplate


def effective_model(template: "PromptTemplate | None", default: str) -> str:
    """NULL/missing `template.model` -> default; non-NULL -> the override."""
    return template.model if (template is not None and template.model) else default


def _game_model() -> str:
    return ollama_client.DEFAULT_MODEL


def _author_model() -> str:
    from .entity_author import AUTHOR_MODEL  # lazy: avoids the import cycle
    return AUTHOR_MODEL


@dataclass(frozen=True)
class PromptSpec:
    surface: str  # "play" | "authoring"
    world_scoped: bool
    dry_run_capable: bool
    call_sites: tuple[str, ...]
    default_model: Callable[[], str]
    premise: str  # "creator" | "player" | "none" (world_premise.PREMISE_REGIMES)
    premise_reason: str = ""  # non-empty exactly when premise == "none"


PROMPT_REGISTRY: dict[str, PromptSpec] = {
    "npc_dialogue": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/cockpit/play.py:_load_npc_dialogue_template",),
        default_model=_game_model,
        premise="player",
    ),
    "npc_initiative_act": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/play_initiative.py:_load_npc_initiative_act_template",),
        default_model=_game_model,
        premise="player",
    ),
    "player_narration": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/cockpit/play_stream.py:_load_mj_narration_template",),
        default_model=_game_model,
        premise="player",
    ),
    "mj_interpretation": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/play_physical.py:_load_mj_interpret_template",),
        default_model=_game_model,
        premise="player",
    ),
    "mj_arbitration": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/play_physical.py:_load_mj_arbiter_template",),
        default_model=_game_model,
        premise="player",
    ),
    "mj_establishment": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/play_physical.py:_load_mj_establishment_template",),
        default_model=_game_model,
        premise="player",
    ),
    "mj_gathering": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/gathering.py:_load_gathering_template",),
        default_model=_game_model,
        premise="player",
    ),
    "mj_speaker_selection": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/play_physical.py:_load_mj_speaker_template",),
        default_model=_game_model,
        premise="none",
        premise_reason="Picks one speaker among a given roster.",
    ),
    "mj_initiative": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/play_initiative.py:_load_mj_initiative_template",),
        default_model=_game_model,
        premise="player",
    ),
    "observation_intent": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/observation_engine.py:request_intent",),
        default_model=_game_model,
        premise="player",
    ),
    "observation_narration": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/observation_runner.py:_generate_mj_narration",),
        default_model=_game_model,
        premise="player",
    ),
    "conversation_analysis": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/analyzer_transcript.py:load_analysis_prompt",),
        default_model=_game_model,
        premise="none",
        premise_reason="Classifies a transcript into proposals.",
    ),
    "overhearing_classification": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/analyzer_transcript.py:load_analysis_prompt",),
        default_model=_game_model,
        premise="none",
        premise_reason="Classifies what was overheard into proposals.",
    ),
    "entity_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "world_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_world_template",),
        default_model=_author_model,
        premise="none",
        premise_reason="Drafts the world itself: there is no premise yet.",
    ),
    "player_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_player_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "skill_catalogue": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_skill_catalogue_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "npc_goal_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_npc_goals_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "agenda_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/event_author.py:_load_agenda_draft_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "event_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/event_author.py:_load_event_draft_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "region_manifest": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/region_author.py:_load_manifest_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "room_batch_manifest": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/room_batch_author.py:_load_manifest_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "room_batch_coherence": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/room_batch_author.py:_load_coherence_template",),
        default_model=_author_model,
        premise="none",
        premise_reason="Judges a staged batch against canon; writes no fiction.",
    ),
    "npc_link_pair": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/link_author.py:_load_pair_template",),
        default_model=_author_model,
        premise="creator",
    ),
    "npc_link_coherence": PromptSpec(
        surface="authoring",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/link_author.py:_load_coherence_template",),
        default_model=_author_model,
        premise="none",
        premise_reason="Judges staged links against canon; writes no fiction.",
    ),
    "npc_batch_placement": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/npc_group_author.py:_load_placement_template",),
        default_model=_author_model,
        premise="none",
        premise_reason="Assigns given character lines to given places; writes no fiction.",
    ),
    "lore_question_to_plan": PromptSpec(
        surface="authoring",
        # world_scoped=False: the planner prompt carries no world content --
        # only the fixed selector whitelist and the creator's question, both
        # identical in every world, so a per-world override row would be a
        # row nobody has a reason to differentiate. (Not "every authoring
        # usage is False" -- npc_link_coherence is authoring and True, for
        # the real reason that its content IS world-specific: it judges
        # whether a relationship fits a given world's tone.)
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/lore_plan.py:draft_plan",),
        default_model=_author_model,
        premise="none",
        premise_reason="Plans selectors from a question; carries no world content.",
    ),
    "lore_rows_to_prose": PromptSpec(
        surface="authoring",
        # world_scoped=False, for the criterion that actually governs it
        # (BRIEF-0085-d, second revision): whether a creator would want the
        # template to differ between worlds, not whether the usage is
        # "authoring" -- npc_link_coherence is authoring and True because
        # tone/social convention ARE world properties there. Here the job is
        # fidelity to the rows the selectors returned, not register, and no
        # per-world override has a reader yet. Flipping it later is one line
        # in the registry, with no migration and no data rework.
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/lore_render.py:_call_model",),
        default_model=_author_model,
        premise="none",
        premise_reason="Renders canon rows as they stand; must add nothing to them.",
    ),
    # TICKET-0098 (BRIEF-0098-D, O1): the lore writing path's two calls.
    # world_scoped=False for the lore_rows_to_prose reason: the job is
    # fidelity to the creator's statement, not a world's register.
    "lore_statement_questions": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/lore_write_draft.py:_call",),
        default_model=_author_model,
        premise="creator",
    ),
    "lore_statement_to_proposal": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/lore_write_draft.py:_call",),
        default_model=_author_model,
        premise="creator",
    ),
    # TICKET-0112 (BRIEF-0112-C): the condition interpreter, a creator tool
    # (IJ1: the authoring model by default, overridable per template).
    "condition_interpret": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/condition_interpreter.py:_call",),
        default_model=_author_model,
        premise="none",
        premise_reason="Translates the creator's sentence into a condition tree.",
    ),
    # TICKET-0121 (BRIEF-0121-E): the quest designer's two calls -- the
    # subject of a request, then the offer. Creator tools: the authoring
    # model by default, overridable per template.
    "quest_subject": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/quest_designer.py:_subject",),
        default_model=_author_model,
        premise="creator",
    ),
    "quest_design": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/quest_designer.py:_design_call",),
        default_model=_author_model,
        premise="creator",
    ),
    # TICKET-0116 (BRIEF-0116-E): a rank trial's offer -- the design's answer under a preamble of its own.
    "quest_trial": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/quest_designer.py:_design_call",),
        default_model=_author_model,
        premise="creator",
    ),
    # TICKET-0126 (BRIEF-0126-F): the player-side character designer -- the backstory's subject, then the
    # proposal. Player regime: it reads what everybody knows.
    "creation_subject": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/creation_designer.py:_subject_call",),
        default_model=_author_model,
        premise="player",
    ),
    "creation_design": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=True,
        call_sites=("src/world_engine/creation_designer.py:_design_call",),
        default_model=_author_model,
        premise="player",
    ),
    "world_tick": PromptSpec(
        surface="play",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/tick.py:run_world_tick",),
        default_model=_game_model,
        premise="player",
    ),
    "world_tick_events": PromptSpec(
        surface="play",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/tick.py:run_world_tick",),
        default_model=_game_model,
        premise="player",
    ),
    "day_plan": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_plan.py:emit_plan",),
        default_model=_game_model,
        premise="player",
    ),
    "day_extract_place": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_extract.py:extract_places",),
        default_model=_game_model,
        premise="none",
        premise_reason="Extracts mentions; already framed by world_frame.",
    ),
    "day_extract_person": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_extract.py:extract_persons",),
        default_model=_game_model,
        premise="none",
        premise_reason="Extracts mentions; already framed by world_frame.",
    ),
    "day_extract_faction": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_extract.py:extract_factions",),
        default_model=_game_model,
        premise="none",
        premise_reason="Extracts mentions; already framed by world_frame.",
    ),
    "day_narration": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_narration.py:narrate",),
        default_model=_game_model,
        premise="player",
    ),
    "day_rewrite": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_narration.py:rewrite",),
        default_model=_game_model,
        premise="player",
    ),
    "day_feasibility": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_feasibility.py:veto",),
        default_model=_game_model,
        premise="none",
        premise_reason="Vetoes steps; already framed by world_frame.",
    ),
    "day_reconcile": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_reconcile.py:reconcile",),
        default_model=_game_model,
        premise="none",
        premise_reason="Routes a declaration to an open plan.",
    ),
    "day_plan_select": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_plan_select.py:select_plan",),
        default_model=_game_model,
        premise="none",
        premise_reason="Routes a declaration to an open plan.",
    ),
    "day_mention_choice": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/day_choice.py:choose",),
        default_model=_game_model,
        premise="none",
        premise_reason="Picks one candidate among the code's.",
    ),
    "conversation_summary": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/context_window.py:_load_summary_template",),
        default_model=_author_model,
        premise="none",
        premise_reason="Compresses a transcript.",
    ),
}
