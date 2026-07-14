"""Single shared APIRouter for every `cockpit/crud/` domain module.

Split out with the rest of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d).
Every domain module does `from ._router import router` and decorates onto
this one object, so all routes still register on a single prefix/tag pair —
identical to the pre-split single-file router.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["author-crud"])
