---
description: Execute one brief of a ticket's lot on its ticket branch.
---
Read the named brief (tooling/briefs/) and only the files it names. The brief
embeds every RECON finding and contract it relies on; its lot header
(tooling/lots/) is authoritative on conflict. Do NOT read the whole tree.

1. `git switch ticket/<NNNN>`, or `git switch -c ticket/<NNNN>` from `main`
   when the branch does not exist yet. Never commit on `main`.
2. Confirm the brief's Mini-RECON anchors. One that does not hold is a STOP.
3. Implement exactly what the brief specifies, under its Decision rights. A
   decision the brief did not settle is a STOP: report it, do not guess.
4. For every commit the brief lists: run /review-step, then continue to
   /close-step in the same turn when the verdict is CLEAN or ATTENTION.
   Stop only on VIOLATION. Commits are pre-authorized: /close-step commits
   without waiting for approval.
5. Never push to main. When the brief's commits are done, run /verify for
   this ticket.
