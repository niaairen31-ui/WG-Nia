"""Cockpit — local review web UI for World Engine.

App factory, static/vendor serving, router mounting, and the NPC link and
NPC group agents' startup retention purges (`purge_closed_link_batches`,
TICKET-0036; `purge_closed_npc_batches`, TICKET-0037), both thin wrappers
over the shared `_purge_closed_batches` helper. Every route
handler lives in a domain module, split out of this file at TICKET-0027,
BRIEF-0027-d (R5):
- `cockpit/crud/` — author CRUD (entities, relations, knowledge, goals,
  agendas, events, factions, skills, locations, ledger, prompts read path).
- `cockpit/routes/creator.py` — creator-mode generation + composite routes
  (entities, worlds, characters, skill-definitions, agendas, events,
  bootstrap, npcs, creations).
- `cockpit/routes/regions.py` — region generation + commit (split out of
  creator.py to fit the module-budget cap).
- `cockpit/routes/prompts.py` — prompt dry-run preview routes.
- `cockpit/routes/mutations.py` — the mutation review queue.
- `cockpit/routes/play.py` — conversations, travel, world-tick; the private
  helpers those routes call live in `cockpit/play.py`, `cockpit/play_physical.py`
  and `cockpit/play_stream.py`.
- `cockpit/routes/scene.py` — scene lifecycle (view/enter/join/leave),
  extracted from `routes/play.py` at TICKET-0032 (C2, module-budget cap).

Every route keeps its original path, method, and body verbatim (pure move,
no logic change) — see BRIEF-0027-d for the full census.

Security
--------
- uvicorn is bound to 127.0.0.1 only (enforced in scripts/cockpit.py).
- No authentication needed for this solo local tool.
- No CORS opened to any origin.
- No external calls except the local Ollama endpoint via the existing client.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Type

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, select

from ..db import engine
from ..models import LinkBatch, LinkBatchRow, NpcBatch, NpcBatchRow
from . import crud as _crud
from .routes import creator as _routes_creator
from .routes import link_agent as _routes_link_agent
from .routes import mutations as _routes_mutations
from .routes import npc_agent as _routes_npc_agent
from .routes import play as _routes_play
from .routes import prompts as _routes_prompts
from .routes import regions as _routes_regions
from .routes import room_batch as _routes_room_batch
from .routes import scene as _routes_scene
from .routes import spatial as _routes_spatial

_INDEX_HTML = Path(__file__).parent / "index.html"
_log = logging.getLogger(__name__)

# Vendored JS dependencies (BRIEF-0023-a, H1): one whitelisted file per
# entry, no StaticFiles mount — that generalization waits for a second
# vendored asset.
_VENDOR_DIR = Path(__file__).parent / "vendor"
_VENDOR_WHITELIST = {"cytoscape-3.34.0.min.js"}

app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)
app.include_router(_crud.router)
app.include_router(_routes_creator.router)
app.include_router(_routes_regions.router)
app.include_router(_routes_prompts.router)
app.include_router(_routes_mutations.router)
app.include_router(_routes_play.router)
app.include_router(_routes_scene.router)
app.include_router(_routes_spatial.router)
app.include_router(_routes_link_agent.router)
app.include_router(_routes_npc_agent.router)
app.include_router(_routes_room_batch.router)


def _purge_closed_batches(
    db: Session, batch_model: Type[SQLModel], row_model: Type[SQLModel], row_fk_attr: str
) -> None:
    """Shared retention purge (R1) for a staging batch/row table pair: keep
    the 2 most recently closed batch rows (status committed/abandoned),
    delete older ones and their row-table children. Legal by construction
    for the ephemeral stratum — see the NOTE on the batch model in
    `models/ephemeral.py` — the append-only journal for the batch's agent
    is never touched here.

    NOTE (BRIEF-0037-e): children are deleted before the batch via two
    explicit Core DELETEs in statement order, NOT via per-object
    `db.delete(...)`. These models declare only a column-level
    `foreign_key=` (no ORM `relationship()`), so the unit-of-work gives
    no child-before-parent delete ordering; under `PRAGMA
    foreign_keys=ON` an autoflush would emit the parent DELETE first and
    SQLite would reject it. Statement-ordered Core deletes make the
    order explicit and independent of flush timing.
    """
    ids = db.exec(
        select(batch_model.id)
        .where(batch_model.status.in_(("committed", "abandoned")))
        .order_by(batch_model.closed_at.desc())
        .offset(2)
    ).all()
    if not ids:
        return
    row_fk_column = getattr(row_model, row_fk_attr)
    db.exec(delete(row_model).where(row_fk_column.in_(ids)))
    db.exec(delete(batch_model).where(batch_model.id.in_(ids)))
    db.commit()


def purge_closed_link_batches(db: Session) -> None:
    """Retention purge for the NPC link agent's staging tables (TICKET-0036,
    BRIEF-0036-a, R1): keep the 2 most recently closed `link_batch` rows
    (status committed/abandoned), delete older ones and their
    `link_batch_row` rows. Legal by construction for this ephemeral
    stratum — see the NOTE on `link_batch` in `models/ephemeral.py` — the
    append-only journal under `~/.world_engine/link_agent_journal/` is
    never touched here."""
    _purge_closed_batches(db, LinkBatch, LinkBatchRow, "batch_id")


def purge_closed_npc_batches(db: Session) -> None:
    """Retention purge for the NPC group agent's staging tables (TICKET-0037,
    BRIEF-0037-a, R1): keep the 2 most recently closed `npc_batch` rows
    (status committed/abandoned), delete older ones and their
    `npc_batch_row` rows. Legal by construction for this ephemeral
    stratum — see the NOTE on `npc_batch` in `models/ephemeral.py` — the
    append-only journal under `~/.world_engine/npc_agent_journal/` is
    never touched here."""
    _purge_closed_batches(db, NpcBatch, NpcBatchRow, "batch_id")


@app.on_event("startup")
def _purge_closed_batches_on_startup() -> None:
    with Session(engine) as db:
        purge_closed_link_batches(db)
        purge_closed_npc_batches(db)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")


@app.get("/vendor/{filename}")
def serve_vendor_file(filename: str) -> FileResponse:
    if filename not in _VENDOR_WHITELIST:
        raise HTTPException(status_code=404, detail=f"{filename!r} is not a vendored asset")
    return FileResponse(_VENDOR_DIR / filename, media_type="application/javascript")
