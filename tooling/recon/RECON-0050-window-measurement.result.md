# RECON-0050 — conversation window replay measurement

Generated 2026-07-27T17:44:35.795854+00:00 by `scripts/measure_conversation_window.py` (BRIEF-0050-e). Measurement only — writes no config, changes no default.

## Fixture

Verkhaal pilot world, player `char-player` vs NPC `npc-maelis` at `loc-dernier-verre`, 10 scripted mundane/repetitive player turns (real model calls, no stub).

## Repetition heuristic

`difflib.SequenceMatcher(None, reply[i], reply[i-1]).ratio() >= 0.5` marks the first reappearance of a near-duplicate NPC reply.

## Grid: first-repetition turn by (verbatim_turns, word_budget)

| verbatim_turns \ word_budget | 800 | 1200 |
|---|---|---|
| 2 | not observed | not observed |
| 4 | not observed | not observed |
| 6 | not observed | not observed |

**No differentiating signal**: every (verbatim_turns, word_budget) cell held with no repetition over the 10-turn fixture at the stated threshold — this run gives no basis to prefer one pair over another. Recommendation: leave the seeded defaults (word_budget=1200, verbatim_turns=6) unchanged (Scope OUT — absent a clear signal, do not auto-tune); a longer or more provocative fixture is needed to actually observe the saturation point this ticket describes.

## K2 probe — `repeat_last_n` (held K=6, word_budget=1200)

- `repeat_last_n=256` (current `ollama_client.NPC_DIALOGUE_OPTIONS`): not observed
- `repeat_last_n=512` (local override, constant NOT changed): not observed

Recommendation: no signal either way — neither `repeat_last_n` value produced an observed repetition on this fixture, so this run gives no basis to widen it. `ollama_client.py:30` is left unchanged (BRIEF-0050-e Scope OUT — a change, if warranted, needs a fixture that actually reproduces the repetition first).
