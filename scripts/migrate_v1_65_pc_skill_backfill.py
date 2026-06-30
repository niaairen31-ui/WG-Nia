"""Migration — PC base-skill backfill (BRIEF-59, no new tables or columns).

Backfills the four base skill rows (tier=0) for every character_type='player'
entity that is missing any of them. Covers all worlds — this is a data
migration, not an active-world-only pass.

Backfill predicate per (PC, base domain): insert only if no skill row with
that character_id, that exact domain, and skill_definition_id IS NULL already
exists. A custom-skill row sharing the same domain column is never touched and
never counted as satisfying the predicate.

Inserted row shape: id (new UUID), character_id, domain, tier=0,
change_history='[]', skill_definition_id=NULL, created_at/updated_at=NOW —
byte-identical to the create-route seed (app.py:1188–1202).

Single transaction, one commit at the end. Rolls back on any error and exits
non-zero with the offending character_id printed.

Idempotent: re-running inserts nothing and prints 0 for every PC.

Run from the project root:
    python scripts/migrate_v1_65_pc_skill_backfill.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import text  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import BASE_SKILL_DOMAINS  # noqa: E402

_BASE_DOMAINS = list(BASE_SKILL_DOMAINS)  # ("physical", "agility", "perception", "composure")


def main() -> None:
    summary: list[tuple[str, str, int]] = []
    current_pc_id = "(none)"

    try:
        with engine.begin() as conn:
            pcs = conn.execute(text(
                "SELECT e.id, e.name "
                "FROM entity e "
                "JOIN character c ON c.id = e.id "
                "WHERE c.character_type = 'player'"
            )).mappings().all()

            for pc in pcs:
                current_pc_id = pc["id"]
                inserted = 0

                for domain in _BASE_DOMAINS:
                    existing = conn.execute(text(
                        "SELECT 1 FROM skill "
                        "WHERE character_id = :cid "
                        "  AND domain = :domain "
                        "  AND skill_definition_id IS NULL"
                    ), {"cid": pc["id"], "domain": domain}).first()
                    if existing is not None:
                        continue

                    conn.execute(text(
                        "INSERT INTO skill "
                        "(id, character_id, domain, tier, change_history, "
                        " skill_definition_id, created_at, updated_at) "
                        "VALUES (:id, :cid, :domain, 0, '[]', NULL, "
                        "        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ), {"id": str(uuid.uuid4()), "cid": pc["id"], "domain": domain})
                    inserted += 1

                summary.append((pc["id"], pc["name"], inserted))

    except Exception as exc:
        print(
            f"ERROR — transaction rolled back. Offending character_id={current_pc_id}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    for char_id, name, n in summary:
        print(f"  {char_id[:8]}…  {name!r:<30}  {n} row(s) inserted")
    total = sum(n for _, _, n in summary)
    print(f"\n{len(summary)} PC(s) checked, {total} base-skill row(s) inserted total.")


if __name__ == "__main__":
    main()
