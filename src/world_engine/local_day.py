"""A real-world day on the cockpit's own clock (Nia's machine), turned into the naive UTC instant every timestamp is stored in (TICKET-0123, BRIEF-0123-A; decision A1).

The one meaning of « a day » for the dashboard's `since`/`until`
(`cockpit/routes/dashboard.py`) and for `scripts/export_lore_usage.py`'s
`--since`. Standard library only.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, tzinfo
from typing import Optional


def local_midnight_utc(day: date, tz: Optional[tzinfo] = None) -> datetime:
    """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
    naive UTC the timestamps are stored in. `tz` fixes the clock instead of
    the machine's (`lore_usage.py` U12f); None is the machine's."""
    local = (datetime.combine(day, time.min, tzinfo=tz) if tz is not None
             else datetime.combine(day, time.min).astimezone())
    return local.astimezone(UTC).replace(tzinfo=None)
