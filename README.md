# World Engine

A local, single-player-first engine for running a persistent RPG world.

This repository currently contains the **database layer only**: the SQLModel
table definitions (mirroring `world-engine-schema.md`) and a script to
initialize the SQLite database. No web routes, AI calls, or UI yet.

## Project structure

```
World-genrator/
├── src/
│   └── world_engine/
│       ├── __init__.py
│       ├── db.py          # engine + session; URL from env var
│       └── models.py      # all SQLModel table classes (the schema)
├── scripts/
│   └── init_db.py         # creates the SQLite file with every table
├── pyproject.toml
├── requirements.txt
├── .env.example
├── world-engine-schema.md # authoritative schema (reference)
└── ARCHITECTURE_DECISIONS.md
```

## Requirements

- Python 3.10+

## Install

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

(On macOS/Linux: `source .venv/bin/activate`.)

## Configure the database

The engine URL comes from the `WORLD_ENGINE_DATABASE_URL` environment variable
and **defaults to a local SQLite file** (`world_engine.db`) when unset. Copy the
example file if you want to override it:

```powershell
copy .env.example .env
```

Switching to PostgreSQL/Supabase later means changing only that variable — no
application code changes.

## Initialize the database

From the project root:

```powershell
python scripts/init_db.py
```

This creates `world_engine.db` with all 17 tables and their indexes, then prints
the tables it created. Running it again is safe — existing tables are left as-is.
