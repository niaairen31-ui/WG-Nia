"""Open the browser on the cockpit once it answers (TICKET-0130, O1).

Used by `scripts/cockpit.py --ouvrir`. Stdlib only; imports nothing from
`world_engine`, so a check can exercise it without resolving a database.
The browser opens only once the port accepts a TCP connection, never
before; a port that never answers opens nothing.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
import webbrowser
from typing import Callable

_log = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 0.5
_RETRY_INTERVAL = 0.25


def open_when_ready(
    url: str,
    host: str,
    port: int,
    *,
    timeout: float = 30.0,
    opener: Callable[[str], object] = webbrowser.open,
) -> bool:
    """Wait until `host:port` accepts a connection, then call `opener(url)`
    exactly once and return True. Return False, without calling `opener`,
    if nothing answers within `timeout` seconds. Never raises on a refused
    or failed connection: an `OSError` is the retry signal."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            sock = socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT)
        except OSError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(_RETRY_INTERVAL)
            continue
        sock.close()
        opener(url)
        return True


def start_opener(url: str, host: str, port: int) -> threading.Thread:
    """Start and return a daemon thread running `open_when_ready`; log a
    warning (logging, never `print`: code standard R3) if the cockpit did
    not answer in time."""

    def _run() -> None:
        if not open_when_ready(url, host, port):
            _log.warning("Navigateur non ouvert : le cockpit n'a pas répondu à temps.")

    thread = threading.Thread(target=_run, name="browser-opener", daemon=True)
    thread.start()
    return thread
