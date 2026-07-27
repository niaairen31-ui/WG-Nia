"""Replay measurement for TICKET-0050 (BRIEF-0050-e) — where does NPC
dialogue repetition reappear across `verbatim_turns` (K) and `word_budget`,
and does a larger `repeat_last_n` help independently of K/budget?

Mini-RECON (this session, reported in the commit/decision entry): no
pre-existing monkeypatched-Ollama replay harness was found reusable for a
multi-turn conversation replay (the codebase's Ollama stubbing precedent —
`tooling/verify/checks/prompt_model_write.py` — monkeypatches `ping()` for a
model-list check, not `chat()` for a dialogue replay). This script is a
small, self-contained harness built on the SAME real call path production
uses (`conversation_window.build_npc_message_list` +
`ollama_client.chat`), against a real local Ollama model — it is
measurement only and NEVER writes config or changes defaults on its own
(Scope OUT).

Fixture: the seeded Verkhaal pilot world's tavern scene — player "Joran Vey"
(`char-player`) talking to tavern-keeper Maelis (`npc-maelis`) at
`loc-dernier-verre`, replaying a scripted sequence of mundane, repetitive
player lines designed to provoke the saturation behavior TICKET-0050
describes (a near-identical NPC paragraph reappearing after ~8-10 turns).

Repetition heuristic (Scope IN 3): `difflib.SequenceMatcher(None, a,
b).ratio()` between each NPC reply and the one immediately before it;
`SIMILARITY_THRESHOLD` (0.5) crossing marks the FIRST reappearance. Simple
by design (Scope OUT: no eval framework).

Run: `python scripts/measure_conversation_window.py` (requires Ollama
running locally with the game model pulled). Writes
`tooling/recon/RECON-0050-window-measurement.result.md` alongside the
stdout table.
"""
from __future__ import annotations

import difflib
import os
import sys
import tempfile
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_db_path = Path(tempfile.mkdtemp()) / "measure_conversation_window.db"
os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{_db_path}"

import seed_pilot  # noqa: E402
from sqlmodel import Session  # noqa: E402
from world_engine import ollama_client  # noqa: E402
from world_engine.context import assemble_npc_context, assemble_scene_tail  # noqa: E402
from world_engine.conversation_window import build_npc_message_list  # noqa: E402
from world_engine.db import create_db_and_tables, engine  # noqa: E402
from world_engine.prompt_store import current_prompt  # noqa: E402

NPC_ID = "npc-maelis"
PLAYER_ID = "char-player"
LOCATION_ID = "loc-dernier-verre"
WORLD_ID = "verkhaal"

SIMILARITY_THRESHOLD = 0.5

# Mundane, repetitive small talk — the exact shape the ticket names as the
# saturation trigger: nothing progresses, the topics loop.
FIXTURE_PLAYER_LINES = [
    "Bonjour Maelis, une bière s'il te plaît.",
    "Il fait calme ce soir, non ?",
    "Tu as des nouvelles de la ville ?",
    "Et sinon, les affaires, ça va ?",
    "Tu connais du monde par ici, j'imagine ?",
    "Rien de spécial à signaler ce soir ?",
    "Tu tiens ce lieu depuis longtemps ?",
    "Et la Garde, elle passe souvent par ici ?",
    "Tu as l'air songeuse, tout va bien ?",
    "Bon, je pense que je vais reprendre un verre.",
]

VERBATIM_TURNS_GRID = (2, 4, 6)
WORD_BUDGET_GRID = (800, 1200)

RESULT_PATH = ROOT / "tooling" / "recon" / "RECON-0050-window-measurement.result.md"


def _seed() -> None:
    create_db_and_tables()
    with Session(engine) as db:
        seed_pilot.seed(db)
        db.commit()


def _npc_dialogue_system_prompt_and_model(db: Session) -> tuple[str, str]:
    """(system_prompt, effective_model) — routes through the SAME
    `effective_model` resolver every live call site uses, so a creator model
    override on `npc_dialogue` is honored here too, not silently bypassed."""
    from world_engine.models import PromptTemplate
    from world_engine.prompt_registry import effective_model
    from sqlmodel import select

    template = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "npc_dialogue", PromptTemplate.is_active == True,  # noqa: E712
        )
    ).first()
    version = current_prompt(db, template)
    context = assemble_npc_context(NPC_ID, PLAYER_ID, LOCATION_ID, db)
    system_prompt = f"{version.system_prompt}\n\n{context}"
    return system_prompt, effective_model(template, ollama_client.DEFAULT_MODEL)


def _first_repetition_turn(replies: list[str]) -> "int | None":
    for i in range(1, len(replies)):
        ratio = difflib.SequenceMatcher(None, replies[i], replies[i - 1]).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            return i + 1  # 1-based turn index of the SECOND (repeating) reply
    return None


def _replay(
    db: Session, *, verbatim_turns: int, word_budget: int, options: dict, lines: list[str],
) -> tuple["int | None", list[str], list[int]]:
    """Replays `lines` against the real model; returns (first_repetition_turn,
    replies, cumulative_word_counts)."""
    system_prompt, model = _npc_dialogue_system_prompt_and_model(db)
    scene_tail = assemble_scene_tail(NPC_ID, LOCATION_ID, None, "unharmed", db)
    npc_history: list[dict] = []
    replies: list[str] = []
    word_counts: list[int] = []
    for line in lines:
        npc_history.append({"role": "user", "content": line})
        msgs = build_npc_message_list(
            system_prompt=system_prompt, npc_history=npc_history, scene_tail=scene_tail,
            word_budget=word_budget, verbatim_turns=verbatim_turns, summary_note=None,
        )
        reply = ollama_client.chat(msgs, model=model, options=options)
        npc_history.append({"role": "assistant", "content": reply})
        replies.append(reply)
        word_counts.append(sum(len(m["content"].split()) for m in npc_history))
    return _first_repetition_turn(replies), replies, word_counts


def run_grid(db: Session) -> dict[tuple[int, int], "int | None"]:
    results: dict[tuple[int, int], "int | None"] = {}
    for verbatim_turns, word_budget in product(VERBATIM_TURNS_GRID, WORD_BUDGET_GRID):
        print(f"--- replaying K={verbatim_turns}, word_budget={word_budget} ---")
        turn, replies, word_counts = _replay(
            db, verbatim_turns=verbatim_turns, word_budget=word_budget,
            options=ollama_client.NPC_DIALOGUE_OPTIONS, lines=FIXTURE_PLAYER_LINES,
        )
        results[(verbatim_turns, word_budget)] = turn
        print(f"    first repetition at turn {turn!r}; final history word count {word_counts[-1]}")
    return results


def run_k2_probe(db: Session) -> dict[str, "int | None"]:
    """K2: hold K/budget at the seeded defaults, replay twice — once with
    NPC_DIALOGUE_OPTIONS as-is (repeat_last_n=256), once with a LOCAL copy
    using repeat_last_n=512. `ollama_client.py`'s constant is never touched
    here."""
    baseline_options = dict(ollama_client.NPC_DIALOGUE_OPTIONS)
    wider_options = dict(ollama_client.NPC_DIALOGUE_OPTIONS, repeat_last_n=512)

    print("--- K2 probe: repeat_last_n=256 (baseline) ---")
    turn_256, _, _ = _replay(
        db, verbatim_turns=6, word_budget=1200, options=baseline_options,
        lines=FIXTURE_PLAYER_LINES,
    )
    print(f"    first repetition at turn {turn_256!r}")

    print("--- K2 probe: repeat_last_n=512 ---")
    turn_512, _, _ = _replay(
        db, verbatim_turns=6, word_budget=1200, options=wider_options,
        lines=FIXTURE_PLAYER_LINES,
    )
    print(f"    first repetition at turn {turn_512!r}")

    return {"repeat_last_n=256": turn_256, "repeat_last_n=512": turn_512}


def _fmt(turn: "int | None") -> str:
    return f"turn {turn}" if turn is not None else "not observed"


def _recommend(grid: dict[tuple[int, int], "int | None"]) -> "tuple[int, int] | None":
    """The (K, budget) pair with the LATEST first-repetition turn — i.e. the
    cell that held up longest over the fixture. Returns None when every cell
    tied at "not observed": with no differentiating signal at all, picking
    ANY pair would be a fabricated recommendation, not a measured one (Scope
    OUT — absent a clear signal, leave the seeded defaults)."""
    if all(turn is None for turn in grid.values()):
        return None

    def _score(item):
        turn = item[1]
        return (turn is None, turn or 0)
    return max(grid.items(), key=_score)[0]


def _k2_recommendation(k2: dict[str, "int | None"]) -> str:
    turn_256, turn_512 = k2["repeat_last_n=256"], k2["repeat_last_n=512"]
    if turn_256 is None and turn_512 is None:
        return (
            "Recommendation: no signal either way — neither `repeat_last_n` value "
            "produced an observed repetition on this fixture, so this run gives no "
            "basis to widen it. `ollama_client.py:30` is left unchanged (BRIEF-0050-e "
            "Scope OUT — a change, if warranted, needs a fixture that actually "
            "reproduces the repetition first)."
        )
    return (
        "Recommendation: widen `repeat_last_n` if the 512 run held up "
        "measurably longer than the 256 baseline on this fixture; "
        "`ollama_client.py:30` is left unchanged by this script either way "
        "(BRIEF-0050-e Scope OUT — a change, if warranted, is a separate "
        "commit Nia approves)."
    )


def write_report(grid: dict[tuple[int, int], "int | None"], k2: dict[str, "int | None"]) -> None:
    lines = [
        "# RECON-0050 — conversation window replay measurement",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat()} by "
        "`scripts/measure_conversation_window.py` (BRIEF-0050-e). Measurement "
        "only — writes no config, changes no default.",
        "",
        "## Fixture",
        "",
        f"Verkhaal pilot world, player `{PLAYER_ID}` vs NPC `{NPC_ID}` at "
        f"`{LOCATION_ID}`, {len(FIXTURE_PLAYER_LINES)} scripted mundane/"
        "repetitive player turns (real model calls, no stub).",
        "",
        "## Repetition heuristic",
        "",
        f"`difflib.SequenceMatcher(None, reply[i], reply[i-1]).ratio() >= "
        f"{SIMILARITY_THRESHOLD}` marks the first reappearance of a near-"
        "duplicate NPC reply.",
        "",
        "## Grid: first-repetition turn by (verbatim_turns, word_budget)",
        "",
        "| verbatim_turns \\ word_budget | " + " | ".join(str(b) for b in WORD_BUDGET_GRID) + " |",
        "|---" * (1 + len(WORD_BUDGET_GRID)) + "|",
    ]
    for k in VERBATIM_TURNS_GRID:
        row = [str(k)] + [_fmt(grid[(k, b)]) for b in WORD_BUDGET_GRID]
        lines.append("| " + " | ".join(row) + " |")

    recommended = _recommend(grid)
    if recommended is None:
        recommendation_line = (
            "**No differentiating signal**: every (verbatim_turns, word_budget) cell "
            f"held with no repetition over the {len(FIXTURE_PLAYER_LINES)}-turn fixture "
            "at the stated threshold — this run gives no basis to prefer one pair over "
            "another. Recommendation: leave the seeded defaults (word_budget=1200, "
            "verbatim_turns=6) unchanged (Scope OUT — absent a clear signal, do not "
            "auto-tune); a longer or more provocative fixture is needed to actually "
            "observe the saturation point this ticket describes."
        )
    else:
        recommendation_line = (
            f"**Recommended default pair from this run: verbatim_turns={recommended[0]}, "
            f"word_budget={recommended[1]}** (latest first-repetition turn over "
            f"the {len(FIXTURE_PLAYER_LINES)}-turn fixture). Seeded defaults "
            "(word_budget=1200, verbatim_turns=6) are left unchanged by this script; "
            "see BRIEF-0050-e Scope IN 5 for the conditional reconciliation gate."
        )
    lines += [
        "",
        recommendation_line,
        "",
        "## K2 probe — `repeat_last_n` (held K=6, word_budget=1200)",
        "",
        f"- `repeat_last_n=256` (current `ollama_client.NPC_DIALOGUE_OPTIONS`): "
        f"{_fmt(k2['repeat_last_n=256'])}",
        f"- `repeat_last_n=512` (local override, constant NOT changed): "
        f"{_fmt(k2['repeat_last_n=512'])}",
        "",
        _k2_recommendation(k2),
        "",
    ]
    RESULT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {RESULT_PATH}")


def main() -> None:
    _seed()
    with Session(engine) as db:
        grid = run_grid(db)
        k2 = run_k2_probe(db)
    write_report(grid, k2)


if __name__ == "__main__":
    main()
