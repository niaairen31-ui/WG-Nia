"""Domain routers mounted on the cockpit app (TICKET-0027, BRIEF-0027-d).

Each sibling module exposes one `router: APIRouter`; `cockpit/app.py`
mounts all six (play, mutations, creator, regions, prompts, spatial)
with no prefix (every route decorator already carries its full
original path).
"""
