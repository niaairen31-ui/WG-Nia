<!-- slug: lore-perspective-tab -->
# BRIEF 0125-F — "Lore > Perspective: see what the public sees, and what it does not"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: BRIEF-0125-E (creator perspective routes)

## Anchors to confirm (Mini-RECON)

- `frontend/src/lore/Lore.svelte:105-108` -> three tab buttons `question`,
  `names`, `write`; `loreTab = $state('question')` (R-28).
- `frontend/src/lore/lore.svelte.js` -> posts through `api` from
  `../creation/sheetRequest.svelte.js`, `world_id: serverState.worldId`,
  `attempt_id: crypto.randomUUID()` (R-28).
- `src/world_engine/cockpit/routes/lore_perspective.py` -> `POST
  /api/lore/perspective/ask` and `/resolve` per C-10 (E).
- `tooling/verify/checks/quest_request_panel.py` RP4 -> a `$effect` in
  `Lore.svelte` reading `writeState.questRequestId` (R-28).

Halt if any has moved.

## Facts carried

### R-28 -- the Lore shell
Opened: `frontend/src/lore/Lore.svelte:1-120`, `frontend/src/lore/lore.svelte.js`.
Finding: tabs `question`, `names`, `write` (buttons at lines 106-108);
`loreTab = $state('question')`; panels rendered by `{#if loreTab === ...}`.
`lore.svelte.js` posts through `api` from `../creation/sheetRequest.svelte.js`
with `world_id: serverState.worldId` and `attempt_id: crypto.randomUUID()`.
Checks reading `Lore.svelte`: `quest_request_panel.py` RP4 (a `$effect`
reading `writeState.questRequestId`).
Consequence: F adds a fourth tab `perspective` and a panel component with
its own state module; RP4's effect is untouched.
### R-29 -- the shell server and build
Opened: `src/world_engine/cockpit/app.py:80-160, 285-329`;
`frontend/vite.config.js`; `frontend/index.html`;
`frontend/scripts/write-manifest.mjs:1-55`;
`tooling/verify/checks/frontend_build_fresh.py:30-120`;
`tooling/verify/checks/static_asset_freshness.py:1-52, 288-330`;
`tooling/verify/checks/legacy_mount.py:1-80`.
Finding: `/static` is served by `_FreshnessAwareStaticFiles`; `_SHELL_ROUTES
= ("/", "/play", "/creation", "/creation/{sub_tab}", "/observation",
"/journee", "/lore")` registered in a loop to `_serve_shell`, which returns
`static/index.html` with `cache-control`. Vite: `base: '/static/'`, `outDir:
'../src/world_engine/cockpit/static'`, `emptyOutDir: true`, `external:
['cytoscape']`, no `input` (single page `index.html`). The source-hash set
is `frontend/src/**` plus exactly `package.json, package-lock.json,
vite.config.js, index.html`, written identically in `write-manifest.mjs:31`
and `frontend_build_fresh.py:38` (`ROOT_FILES`). `static_asset_freshness`
rule 4: every decorator-form `HTMLResponse` route must construct its
response with `headers={"cache-control": ...}`; rule 3: every static file is
classified. `legacy_mount` rule 7: `_SHELL_ROUTES` equals `SHELL_ROUTES` in
`router.js`.
Consequence: G adds a page `frontend/jouer.html` as a second Vite input,
served by a decorator route `GET /jouer` returning `static/jouer.html` with
`cache-control`; `/jouer` is not added to `_SHELL_ROUTES` (it is not a
surface of the creator shell). `jouer.html` joins the source-hash set in
both `write-manifest.mjs` and `frontend_build_fresh.py`.

## Contracts

### C-07 -- the audit
Produced by: D   Consumed by: E
Module: `src/world_engine/perspective_audit.py`.
`WITHHELD_REASONS = ("creator_only", "not_public", "entity_not_public", "secret_membership", "faction_not_public")`.
`withheld(plan, world_id, db, bindings=None) -> list[dict]`, rows
`{"reason", "subject", "content"}` (`subject` = the dossier entity's name,
or the searched text), sorted by subject then reason then
content. For each call of a valid plan whose mentions all resolve
(creator scope is NOT used: the audit resolves under the public scope, and
for a mention that does not resolve publicly it resolves under
`NameScope("names_only")` to name the entity withheld):
- `public_dossier` on X: X not public -> one `entity_not_public` row
  (`content` = X's name) and nothing else for X; else every fact with X as
  participant or on a relation of X that is not in `view.fact_ids`, as
  `creator_only` (in `creator_only_fact_ids`) or `not_public`; every current
  membership of X (and, for a faction, of its members) that the dossier
  dropped, as `secret_membership` or `faction_not_public`.
- `public_facts_mentioning`: every matching fact not in `view.fact_ids`, as
  `creator_only` or `not_public`, with `subject` = the searched text.
- `public_factions`: every active non-public faction, `entity_not_public`,
  `subject` and `content` = its name.
- `world_laws`: nothing.
Invalid plan or `ambiguous_mention`: `[]`. `content` of a fact row is its
`fact_texts` text. Reads only. Never imported by a player-facing module
other than `routes/player.py` (which journals it and never returns it).
### C-10 -- creator perspective routes
Produced by: E   Consumed by: F
Module: `src/world_engine/cockpit/routes/lore_perspective.py`.
`POST /api/lore/perspective/ask` body `{question, world_id, perspective,
attempt_id?}`; `POST /api/lore/perspective/resolve` body `{plan, bindings,
world_id, question, perspective, attempt_id?}`. `perspective` must be
`"public"` (else 422 `"Perspective inconnue."`). Answer:
`{verdict, answer, renderer, candidates, plan, rows, withheld}` where
`candidates` is `{ref: [{entity_id,name,type}]}` from
`PerspectiveResult.ambiguous`. Errors as `/api/lore/ask` (503 / 502), a
refused binding -> 422 `"Choix refusé."`. Each request journals one row
(kind `perspective`, `asked_by "creator"`).

## Context

Nia must be able to check the player's view and see why each line was
withheld (H1-a, H1-b). The Lore shell gets a fourth tab that asks the same
question "as the public", through the creator perspective routes.

## Scope IN

1. New `frontend/src/lore/perspective.svelte.js`: a `$state`
   `perspectiveState = { perspective: 'public', question: '', asking: false,
   error: '', result: null, selections: {}, attemptId: '' }`;
   `askPerspective()` (fresh `attemptId`, POST `/api/lore/perspective/ask`
   with `{question, world_id: serverState.worldId, perspective,
   attempt_id}`), `selectPerspectiveCandidate(ref, entityId)`,
   `confirmPerspective()` (POST `/resolve` with the plan as received, the
   selections, the same attempt id), `resetPerspectiveForWorld()`. Uses
   `api` from `../creation/sheetRequest.svelte.js`, as `lore.svelte.js` does.
2. New `frontend/src/lore/PerspectivePanel.svelte` (prop `visible`):
   - a select labelled `Perspective` with one option `Public — ce que tout le
     monde sait` (value `public`);
   - the question textarea and an `Interroger` button;
   - « Ce que voit le joueur » : `result.answer`, and on
     `ambiguous_mention` the candidates as radio choices (name and type)
     with a `Confirmer` button;
   - « Retenu » : one line per `result.withheld` row, `subject — content`,
     with the reason in French: `creator_only` -> `réservé à la créatrice`,
     `not_public` -> `pas public`, `entity_not_public` -> `entité non
     publique`, `secret_membership` -> `appartenance secrète`,
     `faction_not_public` -> `faction non publique`; when empty: `Rien n'a
     été retenu.`;
   - a folded « Lignes rendues » list of `result.rows` by section.
   No `alert(`, `confirm(`, `prompt(`.
3. `Lore.svelte`: a fourth tab button `Perspective` (`loreTab ===
   'perspective'`) after `Écrire`, and `{#if loreTab === 'perspective'}
   <PerspectivePanel visible={active} />{/if}`. The RP4 `$effect` and every
   other line unchanged.
4. Rebuild the frontend; commit the output.
5. Extend `tooling/verify/checks/player_shell.py` (created here; G extends
   it), docstring first sentence "G1 check for TICKET-0125 -- the Lore
   perspective tab and the player shell are wired and confined.", rules:
   - **PSH1** -- static: `Lore.svelte` holds `loreTab === 'perspective'` and
     `<PerspectivePanel`; `perspective.svelte.js` posts to
     `/api/lore/perspective/ask` and `/api/lore/perspective/resolve` and
     sends `attempt_id`; `PerspectivePanel.svelte` holds the five French
     reason labels of item 2 and `Rien n'a été retenu.`, and none of
     `alert(`, `confirm(`, `prompt(`.
   PASS line (for this brief): `PASS: player_shell -- the Lore perspective tab is wired`.

## Scope OUT

- No other perspective than `public` in the select (TICKET-0127 adds
  characters).
- No change to the question tab, the names tab, the write tab.
- No player shell (G).

## Invariants to defend

- INV-55 -- no `$effect` writes a `$state` it reads after.
- The Lore surface's read-only lock (0085) -- the new tab writes nothing
  but the journal row the route writes.

## Decision rights

STOP: an anchor has moved; RP4 of `quest_request_panel.py` turns red.
ADAPT: a CSS class collides: rename the new class.
REPORT-ONLY: visual layout remarks.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `player_shell.py` (PSH1), `quest_request_panel.py`,
      `effect_self_write.py`, `frontend_build_fresh.py` PASS.
- [ ] Named mutation PSH1: removing the `Perspective` tab button makes
      PSH1 fail (then revert).
- [ ] `corpus_gate.py` passes.
- [ ] Live (Nia): Lore > Perspective answers a question about a public
      entity and lists the withheld lines with their reason.
- [ ] `/review-step` and `/close-step`.

## Docs to update

- None beyond the check (decision recorded in D).
- Regenerate `FILE_MAP.md` (new check).
