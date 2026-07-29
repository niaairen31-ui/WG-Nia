"""Observed lane's adapter onto the shared context window (TICKET-0052,
BRIEF-0052-b, decisions G2/I2/J1/H1/K2).

`context_window.py` (BRIEF-0052-a) made the sliding-window seam
lane-neutral; this module is the observed lane's half of that seam, the
counterpart to `cockpit/play.py`'s use of `resolve_npc_message_list`. It
reads and computes only — it writes no row, canon or otherwise (mirrors
`summary_not_persisted.py`'s guarantee for `context_window.py`). It must
not import any `cockpit` module: core modules never import the UI layer
(the rule already stated at `observation_runner.py:334-339`).

Resolution is PER NPC (G2), mirroring the played lane, and required by
J1's per-NPC scene tail (`assemble_scene_tail` cannot produce a shared
result for several viewers at once). `role` on the `TurnLine`s this module
builds is populated for the played lane's converters and the deferred
K1 shape-parity work (D-0052-shape); under K2 the rendered blob ignores
it — it has no reader on this path today.
"""

from __future__ import annotations

from sqlmodel import Session

from .context import assemble_scene_tail
from .context_window import (
    TurnLine,
    format_summary_note,
    line_word_count,
    load_conversation_window_config,
    render_transcript,
    split_verbatim_tail,
    summarize_older_lines,
)
from .models import Entity, ObservationBeat


def beats_to_lines(beats: list[ObservationBeat], viewer_npc_id: str, db: Session) -> list[TurnLine]:
    """Project prior beats onto the neutral line form FROM ONE NPC'S POINT
    OF VIEW (TICKET-0052, G2 — the played lane resolves per NPC, so the
    observed lane does too).

    Role mirrors the played lane's convention: the viewer's own prior
    lines are 'assistant', every other line is 'user'. Label is the
    speaker's entity name followed by ' :', matching the existing
    `_intent_transcript` rendering byte for byte. An injected event beat
    (outcome == 'event') keeps its raw line with an empty label and role
    'user' — it is creator narration, not an NPC speaking.

    Skips beats with `line is None`, exactly as `_intent_transcript` does.
    Entity names are resolved through a per-call memo so a run with many
    beats does not re-query one name per beat.
    """
    names: dict[str, str] = {}
    lines: list[TurnLine] = []
    for beat in beats:
        if beat.line is None:
            continue
        if beat.outcome == "event":
            lines.append(TurnLine(role="user", label="", content=beat.line))
            continue
        if beat.actor_id not in names:
            entity = db.get(Entity, beat.actor_id)
            names[beat.actor_id] = entity.name if entity else beat.actor_id
        role = "assistant" if beat.actor_id == viewer_npc_id else "user"
        lines.append(TurnLine(role=role, label=f"{names[beat.actor_id]} :", content=beat.line))
    return lines


def resolve_observation_transcript(
    *,
    world_id: str,
    npc_id: str,
    location_id: str,
    beats: list[ObservationBeat],
    db: Session,
) -> str:
    """The observed lane's counterpart to `context_window.
    resolve_npc_message_list`. Returns a STRING (K2 — the observed prompts
    keep their single `{transcript}` blob shape; only the lines composing
    it are windowed). Same config row, same budget, same K, same
    `summary_enabled` gate as the played lane (C1, E1).

    The cap applies whenever `beats_to_lines` is over budget, independent
    of `summary_enabled` (BRIEF-0050-b's split, restated here, not
    re-decided); the summary is an additional recovery layer on top
    (BRIEF-0050-d). The scene tail (J1) is always appended last, separated
    by a blank line — the played lane's tail is the model's LAST read, so
    the observed one must be too. `gathering_id=None` / `player_condition
    =""`: an observed run carries no gathering and no player
    (`player_presence` is always 'absent', TICKET-0051 H2)."""
    cfg = load_conversation_window_config(world_id, db)
    lines = beats_to_lines(beats, npc_id, db)
    if line_word_count(lines) <= cfg.word_budget:
        body = render_transcript(lines)
    else:
        older, recent = split_verbatim_tail(lines, cfg.verbatim_turns)
        body = render_transcript(recent)
        if cfg.summary_enabled:
            note = format_summary_note(summarize_older_lines(older, world_id, db))
            if note is not None:
                body = f"{note}\n\n{body}"
    scene_tail = assemble_scene_tail(npc_id, location_id, None, "", db)
    return f"{body}\n\n{scene_tail}" if body else scene_tail
