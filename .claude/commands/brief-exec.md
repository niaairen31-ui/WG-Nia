---
description: Execute a BRIEF-NN on a ticket branch.
---
Read the named BRIEF-NN (tooling/briefs/) AND its cited RECON AND only the target
files it names. Do NOT read the whole tree.

1. Create/switch to branch `ticket/<NNNN>`.
2. Implement exactly what the brief specifies. If you find yourself needing a
   decision the brief did not settle (D1), STOP and report — do not guess.
3. Commit with the mandatory protocol: /review-step then /close-step.
4. Never push to main. When done, run /verify for this ticket.
