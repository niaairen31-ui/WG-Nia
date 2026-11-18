---
id: TICKET-0131
slug: error-message
title: One reader turns a failed request's body into readable text for the creator's shell; no "[object Object]"
type: bug
status: live-gate
created: 2026-11-17
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
lot_id: LOT-0131-error-message.md
brief_ids: [A]
current_brief: A
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> En passant dans ce que j'ai dans l'actuelle, la raison c'est souvent
> Objet : objet. c'Est a cause JS je pense.

> K1, L1, M1, N1

"Objet : objet" is the browser's `[object Object]`: an `Error` built from a
`detail` that is not a string.

## Clarifications resolved (intake)

- Measured on `main` at `e568908` (R-01 to R-03): 33 sites under
  `frontend/src` build an error message from a response's `detail`
  themselves. 23 throw `new Error(<body>.detail || <fallback>)`, which
  renders an object or a list as `[object Object]`. 9 keep `detail` only
  when it is a string, so an object or a list loses the server's reason
  and shows `<path> -> <status>`. 1 (`observation.svelte.js`) stringifies a
  non-`failures` object.
- FastAPI answers `detail` as a string, as an object (the day judge's
  `{message, reason, offending_words, prose}`, the observation gate's
  `{failures}`) or as a list of `{loc, msg}` for a validation error.
- Journée goes through `creation/sheetRequest.svelte.js`'s `api()`, one of
  the 23.
- The player shell (`frontend/src/joueur/`) cannot import outside its folder
  (`player_shell.py` PSH3), and its `call()` already shows only a string
  `detail` or `Erreur <status>` (R-04). It is left as it is.

## Decisions locked (do not re-litigate without Nia)

- N1 -- a small ticket of its own, executed before TICKET-0128: one function
  `errorMessage(body, fallback)` in `frontend/src/lib/errorMessage.js`;
  every creator-side site calls it; a check forbids reading `detail` into an
  error message anywhere else. Rejected: N2, a brief of TICKET-0128
  (33 files unrelated to that ticket); N3, fixing `sheetRequest.svelte.js`
  alone (the other sites keep the bug).

## Carried forward / open

- `src/world_engine/cockpit/legacy.html` holds the same pattern twice
  (R-11). Not a Vite module: it cannot import `errorMessage`. Reactivation:
  a ticket that edits the legacy document's request helpers, or Nia sees
  `[object Object]` in Play.
- The player shell keeps its own `call()` (R-04). Reactivation: a player
  route answers a non-string `detail` the player must read.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `frontend/src/lib/errorMessage.js` exports `errorMessage`, and it
      renders a string, an object with `message`, a validation list and a
      `failures` object as text, and anything else as the fallback, never
      `[object Object]`  -> verify/checks/frontend_error_message.py
- [ ] No `.js` / `.svelte` under `frontend/src` outside `joueur/` reads
      `detail` into an error message itself; every caller imports
      `errorMessage` from `lib/errorMessage.js`
      -> verify/checks/frontend_error_message.py
- [ ] `frontend_build_fresh.py`, `player_shell.py`, `module_budget.py`,
      `effect_self_write.py`, `file_map.py`, `claude_md_contract.py` stay
      green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] 1. Création › Monde: empty the name and save -> « Le nom est requis. »
- [ ] 2. Création and Journée work as before; an error that appears reads
      as a sentence, never « [object Object] » or « Objet : objet ».

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0131-01 | A | `EntityList.svelte` already binds `errorMessage` (local `$state`); build fails | A (Scope IN 5a, R-05 copy superseded) |
