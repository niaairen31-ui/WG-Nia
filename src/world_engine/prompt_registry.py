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


PROMPT_REGISTRY: dict[str, PromptSpec] = {
    "npc_dialogue": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/cockpit/app.py:_load_npc_dialogue_template",),
        default_model=_game_model,
    ),
    "npc_initiative_act": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/app.py:_load_npc_initiative_act_template",),
        default_model=_game_model,
    ),
    "player_narration": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=True,
        call_sites=("src/world_engine/cockpit/app.py:_load_mj_narration_template",),
        default_model=_game_model,
    ),
    "mj_interpretation": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/app.py:_load_mj_interpret_template",),
        default_model=_game_model,
    ),
    "mj_arbitration": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/app.py:_load_mj_arbiter_template",),
        default_model=_game_model,
    ),
    "mj_establishment": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/app.py:_load_mj_establishment_template",),
        default_model=_game_model,
    ),
    "mj_gathering": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/gathering.py:_load_gathering_template",),
        default_model=_game_model,
    ),
    "mj_speaker_selection": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/app.py:_load_mj_speaker_template",),
        default_model=_game_model,
    ),
    "mj_initiative": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/cockpit/app.py:_load_mj_initiative_template",),
        default_model=_game_model,
    ),
    "conversation_analysis": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/analyzer.py:load_analysis_prompt",),
        default_model=_game_model,
    ),
    "overhearing_classification": PromptSpec(
        surface="play",
        world_scoped=True,
        dry_run_capable=False,
        call_sites=("src/world_engine/analyzer.py:load_analysis_prompt",),
        default_model=_game_model,
    ),
    "entity_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_template",),
        default_model=_author_model,
    ),
    "world_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_world_template",),
        default_model=_author_model,
    ),
    "player_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_player_template",),
        default_model=_author_model,
    ),
    "skill_catalogue": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_skill_catalogue_template",),
        default_model=_author_model,
    ),
    "npc_goal_generation": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/entity_author.py:_load_npc_goals_template",),
        default_model=_author_model,
    ),
    "region_manifest": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/region_author.py:_load_manifest_template",),
        default_model=_author_model,
    ),
    "region_manifest_topup": PromptSpec(
        surface="authoring",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/region_author.py:_load_manifest_topup_template",),
        default_model=_author_model,
    ),
    "world_tick": PromptSpec(
        surface="play",
        world_scoped=False,
        dry_run_capable=False,
        call_sites=("src/world_engine/tick.py:run_world_tick",),
        default_model=_game_model,
    ),
}
