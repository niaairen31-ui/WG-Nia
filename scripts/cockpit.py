"""Launch the World Engine Cockpit on 127.0.0.1:8000.

The server binds to loopback only — it is never reachable from another device
on the same network.  No authentication is needed because the port is not
exposed beyond the local machine.

Usage
-----
    python scripts/cockpit.py
    python scripts/cockpit.py --ouvrir   # also opens the browser on the home page

Then open: http://127.0.0.1:8000 (home page; the cockpit is /play).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the src layout importable without an editable install.
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# UTF-8 console on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import uvicorn  # noqa: E402

from world_engine.cockpit.app import app  # noqa: E402 — triggers DB model import
from world_engine.cockpit.browser_open import start_opener  # noqa: E402

HOST = "127.0.0.1"   # loopback only — never 0.0.0.0
PORT = 8000

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch the World Engine Cockpit.")
    parser.add_argument(
        "--ouvrir",
        action="store_true",
        help="ouvre le navigateur sur la page d'accueil une fois le cockpit prêt",
    )
    args = parser.parse_args()

    print(f"Starting World Engine Cockpit …")
    print(f"  URL   : http://{HOST}:{PORT}")
    print(f"  Access: local only (127.0.0.1 bound)")
    print(f"  Stop  : Ctrl+C\n")
    if args.ouvrir:
        start_opener(f"http://{HOST}:{PORT}/", HOST, PORT)
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False,
        access_log=True,
    )
