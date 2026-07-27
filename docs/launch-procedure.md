# Launch procedure

The engine refuses to start unless the database is explicitly resolved
(`src/world_engine/db.py`). Export `WORLD_ENGINE_ENV` before importing
`world_engine` anything, or set `WORLD_ENGINE_DATABASE_URL` for a one-off
override.

## Prod

```powershell
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
$env:WORLD_ENGINE_ENV = "prod"
python scripts/cockpit.py
```

Resolves to `~/.world_engine/world_engine.db`.

## Test

```powershell
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
$env:WORLD_ENGINE_ENV = "test"
python scripts/seed_test.py
python scripts/test_context.py
```

Resolves to `~/.world_engine/test/world_engine_test.db` — a separate file
from prod, safe to reset or delete without touching prod data.

`seed_test.py` is idempotent (safe to re-run); `reset_test.py` deletes the
test DB file, rebuilds the schema, and reseeds in one step — the disposable
reset cycle:

```powershell
$env:WORLD_ENGINE_ENV = "test"
python scripts/reset_test.py
```
