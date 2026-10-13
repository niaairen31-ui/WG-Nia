"""The « Suivi » tab's routes -- the creator's dashboard and its export (TICKET-0115, BRIEF-0115-D; decisions H1, E2, I1, J1 and M1 of the conditions series' dashboard). Reads only:

    GET /api/dashboard          `{worlds, scope, metrics, deferrals}`:
                                every metric of `dashboard_metrics.METRICS`
                                and the deferral registry
    GET /api/dashboard/export   the same scope as one JSON file to save
                                (`dashboard_export.build_export`)

Query: `world` -- `all` (default) or one world's id (J1); `since`, `until`
-- real-world dates `YYYY-MM-DD` on the cockpit's own clock, both days
included, either may be left out (the timestamps are stored in UTC). A date that does not parse, `since` after `until`, or an unknown world
answers 422.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session

from ...dashboard_deferrals import deferral_dicts
from ...dashboard_export import build_export
from ...dashboard_metrics import Scope, compute_metrics, world_names
from ...db import get_session

router = APIRouter()
ALL_WORLDS = "all"


def _day(raw: Optional[str], name: str) -> Optional[date]:
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{name} : date invalide {raw!r} (AAAA-MM-JJ)") from exc


def _utc(day: date) -> datetime:
    """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
    naive UTC the timestamps are stored in."""
    return datetime.combine(day, time.min).astimezone().astimezone(UTC).replace(tzinfo=None)


def scope_of(db: Session, world: str, since: Optional[str], until: Optional[str]) -> Scope:
    """The scope a query names (see the module docstring)."""
    first, last = _day(since, "since"), _day(until, "until")
    if first is not None and last is not None and first > last:
        raise HTTPException(status_code=422, detail="« du » est après « au ».")
    names = world_names(db)
    if world != ALL_WORLDS and world not in names:
        raise HTTPException(status_code=422, detail=f"monde inconnu {world!r}")
    return Scope(
        world_ids=None if world == ALL_WORLDS else (world,),
        since=_utc(first) if first is not None else None,
        until=_utc(last + timedelta(days=1)) if last is not None else None,
    )


@router.get("/api/dashboard")
def dashboard(world: str = Query(ALL_WORLDS), since: Optional[str] = Query(None),
              until: Optional[str] = Query(None), db: Session = Depends(get_session)) -> dict:
    scope = scope_of(db, world, since, until)
    return {
        "worlds": [{"id": w, "name": n} for w, n in sorted(world_names(db).items(), key=lambda p: p[1])],
        "scope": {"world": world, "since": since or None, "until": until or None},
        "metrics": compute_metrics(db, scope),
        "deferrals": deferral_dicts(),
    }


@router.get("/api/dashboard/export")
def dashboard_export(world: str = Query(ALL_WORLDS), since: Optional[str] = Query(None),
                     until: Optional[str] = Query(None), db: Session = Depends(get_session)) -> Response:
    scope = scope_of(db, world, since, until)
    body = json.dumps(build_export(db, scope), ensure_ascii=False, indent=2, default=str)
    name = f"suivi-{world if world == ALL_WORLDS else 'monde'}-{since or 'debut'}-{until or 'fin'}.json"
    return Response(content=body, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
