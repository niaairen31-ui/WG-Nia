"""Post-conversation analysis — extract proposed mutations from a transcript.

Reads a finished conversation, asks the local model to identify atomic
canon-worthy changes (relation shifts, new knowledge, events, etc.), and
writes them as proposed_mutation rows.  Nothing is applied to world state.

Usage:
    python scripts/analyze_conversation.py <conversation_id> [--dry-run] [--force]

Options:
    --dry-run   Print proposed mutations to stdout; do NOT write to the DB.
    --force     Delete existing proposals for this conversation and re-run.
                Without --force the script exits if proposals already exist,
                so you never silently accumulate duplicates.
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
from world_engine.analyzer import analyze_conversation  # noqa: E402
from world_engine.db import engine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract proposed mutations from a conversation transcript."
    )
    parser.add_argument("conversation_id", help="UUID of the conversation to analyse.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed mutations to stdout without writing to the DB.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing proposals for this conversation and re-run.",
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
        # Idempotency: refuse to silently duplicate proposals.
        existing = db.exec(
            select(m.ProposedMutation).where(
                m.ProposedMutation.conversation_id == args.conversation_id
            )
        ).all()

        # Separate unreviewed (deletable) from reviewed (immutable history).
        # --force ONLY deletes proposed rows; applied/approved/rejected rows
        # are permanent audit history and must never be destroyed.
        proposed_rows = [r for r in existing if r.status == "proposed"]
        reviewed_rows = [r for r in existing if r.status != "proposed"]

        if existing:
            if not args.force:
                if proposed_rows:
                    print(
                        f"[skip] {len(proposed_rows)} proposed proposal(s) already exist for "
                        f"conversation {args.conversation_id}.\n"
                        f"       Run with --force to delete them and re-run."
                    )
                    if reviewed_rows:
                        print(
                            f"       ({len(reviewed_rows)} reviewed row(s) will be kept regardless.)"
                        )
                    sys.exit(0)
                # Only reviewed rows exist — no pending proposals blocking re-analysis.

            # Force (or no proposed rows): delete only proposed rows.
            for row in proposed_rows:
                db.delete(row)
            if proposed_rows:
                db.commit()
                print(f"[force] Deleted {len(proposed_rows)} proposed proposal(s).")
            if reviewed_rows:
                print(
                    f"[force] Kept {len(reviewed_rows)} reviewed proposal(s) "
                    f"({', '.join(r.status for r in reviewed_rows)}) — history is sacred."
                )

        try:
            mutations = analyze_conversation(
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

        if args.dry_run:
            print(f"\n--- DRY RUN: {len(mutations)} proposed mutation(s) ---\n")
            for i, mut in enumerate(mutations, 1):
                print(f"[{i}] mutation_type : {mut.mutation_type}")
                print(f"     target_table  : {mut.target_table}")
                print(f"     target_id     : {mut.target_id}")
                print(f"     payload       : {mut.payload}")
                print(f"     rationale     : {mut.rationale}")
                print()
            print(
                f"(Nothing written — dry-run mode. "
                f"Conversation {args.conversation_id})"
            )
            return

        # Write proposals to the DB — no other table is touched.
        for mut in mutations:
            db.add(mut)
        db.commit()
        print(
            f"Wrote {len(mutations)} proposed_mutation row(s) for "
            f"conversation {args.conversation_id}."
        )
        print("Status: proposed | proposed_by: local_ai | world state: unchanged.")


if __name__ == "__main__":
    main()
