"""Launch the Pipeline Cockpit on 127.0.0.1:8100.

The server binds to loopback only — it is never reachable from another device
on the same network. No authentication is needed because the port is not
exposed beyond the local machine. Runs alongside the World Engine Cockpit
(port 8000, scripts/cockpit.py) without interference — distinct port,
distinct package, no shared imports (K1).

Usage
-----
    python scripts/pipeline_cockpit.py

Then open: http://127.0.0.1:8100
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root onto sys.path (not src/) — the pipeline cockpit is a tooling/
# package, not part of the world_engine src-layout package.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# UTF-8 console on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import uvicorn  # noqa: E402

from tooling.pipeline_cockpit.app import HOST, PORT, app  # noqa: E402

if __name__ == "__main__":
    print(f"Starting Pipeline Cockpit …")
    print(f"  URL   : http://{HOST}:{PORT}")
    print(f"  Access: local only (127.0.0.1 bound)")
    print(f"  Stop  : Ctrl+C\n")
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False,
        access_log=True,
    )
