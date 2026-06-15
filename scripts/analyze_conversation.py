"""Window analysis — extract proposed mutations from unanalyzed turns.

Reads the conversation's unanalyzed turns (`turn_order >
conversation.last_analyzed_turn`), asks the local model to identify
canon-worthy changes (relation deltas, new knowledge, status changes), and
writes them as proposed_mutation rows (proposed_by='local_ai_window').
`last_analyzed_turn` is advanced atomically with the write. Nothing is
applied to world state.

Usage:
    python scripts/analyze_conversation.py <conversation_id> [--force]

Options:
    --force     Delete existing 'proposed' rows for this conversation, reset
                last_analyzed_turn to 0, and re-run over the full transcript.
                Reviewed rows (applied/approved/rejected) are NEVER deleted —
                history is sacred.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# UTF-8 console for French output on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlmodel import Session, select  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine import ollama_client  # noqa: E402
from world_engine.analyzer import analyze_window  # noqa: E402
from world_engine.db import engine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run window analysis on a conversation's unanalyzed turns."
    )
    parser.add_argument("conversation_id", help="UUID of the conversation to analyse.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete 'proposed' rows and reset last_analyzed_turn to 0, then re-run.",
    )
    args = parser.parse_args()

    model = ollama_client.DEFAULT_MODEL
    host = ollama_client.OLLAMA_HOST

    try:
        available = ollama_client.ping(host)
    except ollama_client.OllamaError as exc:
        print(f"\n[error] {exc}")
        sys.exit(1)
    if model not in available:
        print(
            f"[warn] Model '{model}' not in Ollama's local list. "
            f"Pull it first if the request fails: ollama pull {model}"
        )

    with Session(engine) as db:
        conv = db.get(m.Conversation, args.conversation_id)
        if conv is None:
            print(f"[error] Conversation {args.conversation_id!r} not found.")
            sys.exit(1)

        if args.force:
            # --force ONLY deletes proposed rows; applied/approved/rejected
            # rows are permanent audit history and must never be destroyed.
            proposed_rows = db.exec(
                select(m.ProposedMutation).where(
                    m.ProposedMutation.conversation_id == args.conversation_id,
                    m.ProposedMutation.status == "proposed",
                )
            ).all()
            for row in proposed_rows:
                db.delete(row)
            if proposed_rows:
                db.commit()
                print(f"[force] Deleted {len(proposed_rows)} proposed proposal(s).")
            conv.last_analyzed_turn = 0
            db.add(conv)
            db.commit()
            print("[force] Reset last_analyzed_turn to 0 — re-running over the full transcript.")

        has_new = db.exec(
            select(m.ConversationMessage).where(
                m.ConversationMessage.conversation_id == args.conversation_id,
                m.ConversationMessage.turn_order > conv.last_analyzed_turn,
                m.ConversationMessage.speaker.in_(("player", "npc")),
            )
        ).first()
        if has_new is None:
            print("Nothing new to analyze.")
            return

        try:
            mutations = analyze_window(
                args.conversation_id,
                db,
                model=model,
                host=host,
            )
        except ValueError as exc:
            print(f"[error] {exc}")
            sys.exit(1)

        if not mutations:
            print("Analysis complete: no canon-worthy mutations detected.")
            return

        print(
            f"Wrote {len(mutations)} proposed_mutation row(s) for "
            f"conversation {args.conversation_id}."
        )
        print("Status: proposed | proposed_by: local_ai_window | world state: unchanged.")


if __name__ == "__main__":
    main()
