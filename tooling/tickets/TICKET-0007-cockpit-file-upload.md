---
id: TICKET-0007
title: Pipeline cockpit — file upload on the Soumettre surface
type: feature
status: live-gate
created: 2026-07-03
slug: cockpit-file-upload
model_lane: { intake: opus, recon: none, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0007]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

« Je veux juste une petite modification : je veux envoyer les dossiers .md
et pas le corps des messages. » — upload the delivered `.md` files directly
into the Soumettre surface instead of pasting their body.

## Clarifications resolved (intake)

- **A1 — coexistence, converging adapter.** An upload zone is ADDED next to
  the textarea; both inputs feed the exact same pure pipeline
  (`assign_number` → write). The upload path is an adapter (file →
  parsed parts → existing functions), never a second logic.
- **B2 — filename is the authority, upload channel only.** For uploaded
  files, type, number (or `0007` placeholder), optional brief suffix, and
  slug are parsed from the filename; the body shape is NOT consulted for
  detection. Structural consequence, accepted at intake: the paste channel
  necessarily keeps body-shape detection (pasted text has no name) —
  per-channel authority, no cross-validation (B3 rejected). An
  unparseable filename is REFUSED with a visible message; no silent
  fallback to body detection.
- **C1 — ordered multi-file upload.** Several files in one gesture;
  tickets are processed first; a ticket deposit binds `bound_ticket` for
  the remaining files of the same request and for the page state, exactly
  like the paste flow.
- **D1 — no recon.** The touched surface is one route + pure functions
  specified by BRIEF-0006-a days ago. This ticket is the first live
  exercise of the "no recon spec on disk = phase inapplicable by
  construction" rule.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `parse_filename` pure function: `TICKET-0007-my-slug.md` →
      (ticket, placeholder, "my-slug"); `BRIEF-0042-a-thing.md` →
      (brief, "0042", suffix "a", "thing"); `notes.md` and `TICKET-.md`
      raise `UnparseableFilename`  -> verify/checks/pipeline_cockpit.py (extended)
      (note: `0007` is the upload channel's numeric placeholder literal —
      it always resolves to `None`/bound-ticket, for every type, not just
      TICKET; the brief example above intentionally uses `0042` instead of
      `0007` for the BRIEF case to avoid the coincidental collision with
      this ticket's own number)
- [ ] Multi-file ordering: given (recon, ticket) in one batch, the ticket
      is processed first and the recon binds to its number  -> same check
- [ ] A refused file leaves nothing written for that file; other files in
      the same batch still process  -> same check

### Live  ->  human gate (Nia)
- [ ] Upload ticket + recon `.md` together: both land correctly numbered,
      number displayed, recon bound to the ticket
- [ ] Upload a brief carrying a concrete number in its filename: written
      as-is under that number
- [ ] Paste path still works unchanged (regression)
- [ ] A badly named file shows a clear refusal in the UI