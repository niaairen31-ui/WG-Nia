"""A real-world day on the cockpit's own clock (Nia's machine), turned into the naive UTC instant every timestamp is stored in (TICKET-0123, BRIEF-0123-A; decision A1).

The one meaning of « a day » for the dashboard's `since`/`until`
(`cockpit/routes/dashboard.py`) and for `scripts/export_lore_usage.py`'s
`--since`. Standard library only.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time


def local_midnight_utc(day: date) -> datetime:
    """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
    naive UTC the timestamps are stored in."""
    return datetime.combine(day, time.min).astimezone().astimezone(UTC).replace(tzinfo=None)
