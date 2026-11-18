# AMENDMENT-0131-01 -- `errorMessage` already names a local state in `EntityList.svelte`

Ticket: TICKET-0131   Lot: LOT-0131-error-message.md   Brief in flight: A

## What deviated

BRIEF-0131-A Scope IN 5 adds `import { errorMessage } from
'../lib/errorMessage.js';` to `creation/EntityList.svelte`, which already
declares `let errorMessage = $state('');`. `npm run build` fails on the
duplicate binding (executor STOP, "npm run build fails").

Cause: the lot asserted that the 33 files could import the name, but never
enumerated whether the identifier was free in them. Gate (c) had no
enumeration for that negative claim.

## Corrected finding

### R-05 -- `frontend/src/lib/` and its import form
*Corrected by AMENDMENT-0131-01.* Add to the finding:
`grep -nw errorMessage` over the 33 files, on `main` at `e568908`, raw:
```
creation/EntityList.svelte:68:  let errorMessage = $state('');
creation/EntityList.svelte:120:      errorMessage = err.message;
creation/EntityList.svelte:135:      errorMessage = err.message;
creation/EntityList.svelte:152:      errorMessage = err.message;
creation/EntityList.svelte:168:      errorMessage = err.message;
creation/EntityList.svelte:355:  <div class="empty">{errorMessage}</div>
```
No other file of the 33 holds the identifier. `grep -nw loadError
frontend/src/creation/EntityList.svelte` -> empty.
`grep -rn "errorMessage\|loadError" tooling/verify/checks` -> empty. The
only check that reads `EntityList.svelte`, `creation_layout.py`, asserts
`selectGerm(` (CL3, line 133) and `selectPcDraft(`, `Soumis (` (CL5,
line 155).
Consequence: in `EntityList.svelte`, the local state is renamed
`loadError`. The import keeps C-01's name; no alias.

## Amended Scope IN (BRIEF-0131-A)

5a (new, in commit (1), before the import is added). In
`frontend/src/creation/EntityList.svelte`, rename the identifier
`errorMessage` to `loadError` on the six lines above, and nowhere else.
This is a pure rename: no other character on those lines changes. Then
Scope IN 5 adds the import as written.

Done means, added:
- [ ] `grep -nw errorMessage frontend/src/creation/EntityList.svelte` ->
      only the import line and the line-233 call.
- [ ] Live: Création, entity list. An error while loading still shows its
      text in the list's empty state.

## Rejected

- An import alias in `EntityList.svelte` only (`errorMessage as ...`): one
  caller would differ from the 32 others, and FE3's `errorMessage(` needle
  would not see it.
- Renaming the exported function: it touches C-01 and 33 files to work
  around one local name.

## Downstream

One brief. BRIEF-0131-A's embedded R-05 is superseded by this page, and
the header wins on conflict. Gate checks re-run: (a) and (c) for R-05. No
other gate or contract changes.

## Protocol lesson (for Nia)

When a lot adds an import of a name to existing files, the RECON pastes
`grep -nw <name>` over those files. A name already bound in a file is a
negative claim like any other.
