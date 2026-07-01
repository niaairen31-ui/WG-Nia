---
name: recon
description: How to author and run a RECON. Use before writing any brief.
---
A RECON confirms `file:line` anchors in the LIVING code before a brief relies on
them. It is report-only.

Authoring a RECON spec: list each thing a future brief will assume — a function,
a table, a call-site, an entry point — phrased as a question ("Where is X? What
are its current write paths?"). One anchor per item.

Running it: /recon. Every answer is a real `path:line`, or "does not exist".

Never fix or refactor inside a RECON. A surprising finding is a result, not a
problem to solve on the spot.
