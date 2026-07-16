"""Cockpit — local review web UI for World Engine.

App factory, static/vendor serving, and router mounting only. Every route
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from . import crud as _crud
from .routes import creator as _routes_creator
from .routes import mutations as _routes_mutations
from .routes import play as _routes_play
from .routes import prompts as _routes_prompts
from .routes import regions as _routes_regions
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")


@app.get("/vendor/{filename}")
def serve_vendor_file(filename: str) -> FileResponse:
    if filename not in _VENDOR_WHITELIST:
        raise HTTPException(status_code=404, detail=f"{filename!r} is not a vendored asset")
    return FileResponse(_VENDOR_DIR / filename, media_type="application/javascript")
