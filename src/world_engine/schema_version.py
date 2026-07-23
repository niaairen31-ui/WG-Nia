"""Code-side expected static schema version (C2 two-plane governance,
plane 1 — TICKET-0044, BRIEF-0044-a).

`EXPECTED_STATIC_SCHEMA_VERSION` is the code's single source of truth for
"what static schema does this code expect". A migration bumps this
constant, the `schema_meta` singleton row, and the `world-engine-schema.md`
header line together, in the SAME commit — never one without the others.
The cockpit boot guard (`cockpit/app.py`) refuses to start when the DB's
`schema_meta.static_version` disagrees; `verify/checks/schema_version_agreement.py`
statically checks this constant against the doc header.
"""

from __future__ import annotations

EXPECTED_STATIC_SCHEMA_VERSION: str = "v1.87"
