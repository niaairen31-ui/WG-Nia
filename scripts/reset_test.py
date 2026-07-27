"""Disposable reset cycle for the test database (D1).

Deletes the test DB file (if present), rebuilds the schema, and reseeds via
`seed_test.main()`. Gated to `WORLD_ENGINE_ENV=test` so it can never run
against prod, even if a stray `WORLD_ENGINE_DATABASE_URL` override is set.

    WORLD_ENGINE_ENV=test python scripts/reset_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env != "test":
    print(
        f"reset_test.py refuses to run unless WORLD_ENGINE_ENV=test (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from world_engine.db import create_db_and_tables, engine  # noqa: E402

import seed_test  # noqa: E402


def main() -> None:
    db_path = Path(engine.url.database)
    engine.dispose()
    if db_path.exists():
        db_path.unlink()

    create_db_and_tables()
    seed_test.main()
    print(f"reset_test: reset {db_path} and seeded.")


if __name__ == "__main__":
    main()
