"""Origin guard for every write route (TICKET-0098, BRIEF-0098-A, decision I1).

The cockpit is bound to loopback with no authentication. Loopback binding
does not stop a web page open in the creator's own browser from sending a
request to `127.0.0.1`: a cross-site form post, or a DNS-rebinding page
whose name resolves to loopback. Both carry a non-local `Origin` (the
first) or a non-local `Host` (the second). This guard refuses any write
method whose `Host` hostname is not local, or whose `Origin`, when sent,
is not a local http(s) origin. Reads pass untouched; a local script that
sends no `Origin` passes as long as its `Host` is local.

The rule is hostname-only, never port: the cockpit runs on 8000 and, from
`.claude/launch.json`, on 8001. `verdict` is pure; the middleware is the
only caller in `src/`.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

LOCAL_HOSTNAMES: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})
WRITE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
REFUSED_MESSAGE = (
    "Écriture refusée : la requête ne vient pas du cockpit local "
    "(origine ou hôte non local)."
)


def host_name(host: Optional[str]) -> Optional[str]:
    """The hostname of a `Host` header value (`name`, `name:port`,
    `[v6]:port`), lowercased; None when absent or empty."""
    if not host:
        return None
    parsed = urlsplit(f"//{host.strip()}")
    return parsed.hostname


def verdict(method: str, host: Optional[str], origin: Optional[str]) -> Optional[str]:
    """None when the request may proceed, else the refusal message.

    A read method always proceeds. A write method proceeds only when the
    `Host` hostname is local and the `Origin` is absent or a local
    http(s) origin. `Origin: null` (sandboxed or opaque) is refused."""
    if method.upper() not in WRITE_METHODS:
        return None
    if host_name(host) not in LOCAL_HOSTNAMES:
        return REFUSED_MESSAGE
    if origin is None:
        return None
    parsed = urlsplit(origin.strip())
    if parsed.scheme not in ("http", "https") or parsed.hostname not in LOCAL_HOSTNAMES:
        return REFUSED_MESSAGE
    return None


async def origin_guard(request: Request, call_next):
    """HTTP middleware: a 403 with `REFUSED_MESSAGE` on a refused write."""
    refusal = verdict(request.method, request.headers.get("host"), request.headers.get("origin"))
    if refusal is not None:
        return JSONResponse(status_code=403, content={"detail": refusal})
    return await call_next(request)
