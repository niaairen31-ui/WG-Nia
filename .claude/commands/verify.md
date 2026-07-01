---
description: Run the deterministic G1 gate for a ticket.
---
Ensure runtime: `. .\.venv\Scripts\Activate.ps1` then `$env:PYTHONPATH = "src"`.

Run: `python -m tooling.verify.run --ticket <TICKET-ID>`

Report the JSON verdict. If any check failed, list ONLY the failing criteria and
their messages. Do not attempt fixes here — that is the exec stage's job.
