---
description: Run a RECON spec against the living code. Report-only.
---
You are running a RECON. Read the RECON spec the user names (in tooling/recon/).

For EACH anchor it asks about:
- Locate it in the living code and report the exact `path:line`.
- Report what is actually there vs what the spec assumed. Note mismatches.

RULES:
- Report-only. Do NOT edit code, do NOT act on any finding, do NOT open branches.
- If an anchor does not exist, say so plainly — that is a valid finding.

Write the result to tooling/recon/<id>.result.md as a plain report.
