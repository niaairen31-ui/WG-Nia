"""Migration to schema v1.31 — add the ledger table (BRIEF-18).

New table: ledger
  - Append-only conserved-currency ledger. Balance = SUM(amount) per
    entity_id, computed at read time — no stored balance, no CHECK.
  - INSERT-only on every write path: no UPDATE, no DELETE, ever. A mistake
    is corrected with a new compensating line (source_type='correction'),
    never by editing or deleting an existing row.
  - counterparty_id is filled (registre legibility) but never triggers a
    second ledger row this step (decision A1, no PNJ double-entry).
  - source_type 'conversation' / 'pass_play' are reserved for step 2
    (AI-detected resource_change); this step's creator path only accepts
    'creator' / 'correction'.

Idempotent: safe to run if the table already exists.

Run from the project root:
    python scripts/migrate_v1_31_ledger.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def main() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "ledger" in tables:
        print("Table 'ledger' already exists — nothing to do.")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE ledger (
              id              TEXT PRIMARY KEY,
              world_id        TEXT NOT NULL REFERENCES world(id),
              entity_id       TEXT NOT NULL REFERENCES entity(id),
              amount          INTEGER NOT NULL,
              counterparty_id TEXT REFERENCES entity(id),
              reason          TEXT,
              source_type     TEXT,
              conversation_id TEXT REFERENCES conversation(id),
              pass_play_id    TEXT REFERENCES pass_play(id),
              session_id      TEXT REFERENCES session(id),
              created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("CREATE INDEX idx_ledger_entity ON ledger(entity_id)"))
        conn.execute(text("CREATE INDEX idx_ledger_session ON ledger(session_id)"))

    print("Migration v1.31 applied: ledger table and indexes created.")


if __name__ == "__main__":
    main()
