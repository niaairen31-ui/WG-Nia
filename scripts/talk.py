"""Live wiring — hold a terminal conversation with Maelis through the local model.

Assembles Maelis's context (her "brain"), injects it as the system prompt to
Ollama, and loops: your line as Joran -> model -> Maelis's reply. Every turn is
persisted as a conversation_message; the assembled context is stored on the
conversation row for audit. No mutations to world state are produced here.

Run from the project root (after seeding), with Ollama running:

    python scripts/talk.py

Type your lines at the `Joran >` prompt. Type /quit to end.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

# UTF-8 console for accented French, both directions.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine import ollama_client  # noqa: E402
from world_engine.context import assemble_npc_context  # noqa: E402
from world_engine.db import engine  # noqa: E402

WORLD_ID = "verkhaal"
NPC_ID = "npc-maelis"
PLAYER_ID = "char-player"
LOCATION_ID = "loc-dernier-verre"

NPC_LABEL = "Maelis"
PLAYER_LABEL = "Joran"


def get_or_open_session(db: Session) -> m.Session:
    """Return the world's open session, creating one if none exists."""
    existing = db.exec(
        select(m.Session)
        .where(m.Session.world_id == WORLD_ID, m.Session.status == "open")
        .order_by(m.Session.number.desc())
    ).first()
    if existing is not None:
        return existing
    numbers = db.exec(
        select(m.Session.number).where(m.Session.world_id == WORLD_ID)
    ).all()
    number = (max(numbers) if numbers else 0) + 1
    session_row = m.Session(
        world_id=WORLD_ID,
        number=number,
        title="Live test session",
        status="open",
        started_at=datetime.now(UTC),
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return session_row


def main() -> None:
    model = ollama_client.DEFAULT_MODEL
    host = ollama_client.OLLAMA_HOST

    # Fail fast and clearly if Ollama isn't up.
    try:
        available = ollama_client.ping(host)
    except ollama_client.OllamaError as exc:
        print(f"\n[error] {exc}")
        sys.exit(1)
    if model not in available:
        print(
            f"[warn] Model '{model}' is not in Ollama's local list "
            f"({available or 'none pulled'}).\n"
            f"        If the first reply fails, run: ollama pull {model}\n"
        )

    with Session(engine) as db:
        session_row = get_or_open_session(db)

        # Assemble Maelis's context and open the conversation with it stored.
        system_prompt = assemble_npc_context(NPC_ID, PLAYER_ID, LOCATION_ID, db)
        conversation = m.Conversation(
            world_id=WORLD_ID,
            session_id=session_row.id,
            location_id=LOCATION_ID,
            player_id=PLAYER_ID,
            npc_id=NPC_ID,
            status="open",
            injected_context={
                "model": model,
                "npc_id": NPC_ID,
                "interlocutor_id": PLAYER_ID,
                "location_id": LOCATION_ID,
                "system_prompt": system_prompt,
            },
            started_at=datetime.now(UTC),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        print("=" * 72)
        print(f"  Le Dernier Verre — vous parlez à {NPC_LABEL} (modèle : {model})")
        print(f"  session #{session_row.number} · conversation {conversation.id}")
        print("  Tapez vos répliques après « Joran > ». /quit pour terminer.")
        print("=" * 72)

        history: list[dict[str, str]] = []
        turn_order = 1
        ended_cleanly = True

        while True:
            try:
                line = input(f"\n{PLAYER_LABEL} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()  # newline after ^C/^D
                break

            if line == "/quit":
                break
            if not line:
                continue

            # Persist the player's turn immediately.
            db.add(
                m.ConversationMessage(
                    conversation_id=conversation.id,
                    turn_order=turn_order,
                    speaker="player",
                    speaker_id=PLAYER_ID,
                    content=line,
                )
            )
            db.commit()
            turn_order += 1
            history.append({"role": "user", "content": line})

            # Ask the model. The system prompt is Maelis's brain.
            messages = [{"role": "system", "content": system_prompt}, *history]
            print(f"{NPC_LABEL} réfléchit…", end="\r", flush=True)
            try:
                reply = ollama_client.chat(messages, model=model, host=host)
            except ollama_client.OllamaError as exc:
                print(" " * 24, end="\r")  # clear the "réfléchit" line
                print(f"\n[error] {exc}")
                ended_cleanly = False
                break

            print(" " * 24, end="\r")  # clear the "réfléchit" line
            shown = reply if reply else "(Maelis garde le silence.)"
            print(f"{NPC_LABEL} > {shown}")

            # Persist Maelis's spoken line (think block already stripped).
            db.add(
                m.ConversationMessage(
                    conversation_id=conversation.id,
                    turn_order=turn_order,
                    speaker="npc",
                    speaker_id=NPC_ID,
                    content=reply,
                )
            )
            db.commit()
            turn_order += 1
            history.append({"role": "assistant", "content": reply})

        # Close the conversation.
        conversation.status = "closed"
        conversation.ended_at = datetime.now(UTC)
        db.add(conversation)
        db.commit()

        message_count = db.exec(
            select(m.ConversationMessage).where(
                m.ConversationMessage.conversation_id == conversation.id
            )
        ).all()
        print("\n" + "-" * 72)
        status_note = "" if ended_cleanly else " (ended on error)"
        print(
            f"Conversation closed{status_note}: {len(message_count)} message(s) "
            f"persisted to conversation {conversation.id}."
        )


if __name__ == "__main__":
    main()
