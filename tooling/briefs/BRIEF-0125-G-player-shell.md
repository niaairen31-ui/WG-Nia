<!-- slug: player-shell -->
# BRIEF 0125-G — "The player shell at /jouer"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: BRIEF-0125-E (player routes), C (a world can be opened), F (`player_shell.py` exists)

## Anchors to confirm (Mini-RECON)

- `frontend/vite.config.js` -> `base: '/static/'`, `outDir:
  '../src/world_engine/cockpit/static'`, `emptyOutDir: true`, `external:
  ['cytoscape']`, no `input` (R-29).
- `frontend/scripts/write-manifest.mjs:31` -> `['package.json',
  'package-lock.json', 'vite.config.js', 'index.html']` (R-29).
- `tooling/verify/checks/frontend_build_fresh.py:38` -> `ROOT_FILES = (...
  "index.html")` (R-29).
- `src/world_engine/cockpit/app.py` -> `_SHELL_ROUTES` (seven paths, no
  `/jouer`), `_serve_shell` returning `static/index.html` with
  `cache-control`, `_REVALIDATE_CACHE_CONTROL` (R-29).
- `tooling/verify/checks/static_asset_freshness.py` rule 4 -> decorator HTML
  routes must build `HTMLResponse(..., headers={"cache-control": ...})` (R-29).
- `src/world_engine/cockpit/routes/player.py` -> the five C-11 routes (E).
- `CLAUDE.md` -> Path-scoped rules list; highest invariant INV-65 (R-32).
- `frontend/src/main.js` -> the three mounting lines of R-37.

Halt if any has moved.

## Facts carried

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
### R-30 -- the origin guard
Opened: `src/world_engine/cockpit/origin_guard.py:1-40`.
Finding: every write method is refused unless `Host` is local and `Origin`,
when sent, is a local http(s) origin; reads pass.
Consequence: `/jouer` is served by the same local server, so its POSTs pass
unchanged. No change.
### R-32 -- invariant ids and CLAUDE.md budget
Opened: `CLAUDE.md` (Invariants, Path-scoped rules), `.claude/rules/*.md`,
`tooling/verify/checks/claude_md_contract.py:77-80`.
Finding: highest live id INV-65 (`.claude/rules/prompts.md`); budgets
`ROOT_CHAR_BUDGET = 22_000`, `RULE_CHAR_BUDGET = 4_000`; `wc -c CLAUDE.md`
= 20448. The Path-scoped rules section lists one line per rule file.
Consequence: G adds `.claude/rules/player-surface.md` holding INV-66 and one
list line in CLAUDE.md (about 70 characters).
### R-37 -- the creator shell entry
Opened: `frontend/src/main.js` (whole, 4 lines).
Finding: `import App from './App.svelte'; import { mount } from 'svelte';
mount(App, { target: document.getElementById('app') });`
Consequence: the player entry `frontend/src/joueur/main.js` is the same
three lines with `JoueurApp.svelte`.

## Contracts

### C-11 -- player routes
Produced by: E   Consumed by: G
Module: `src/world_engine/cockpit/routes/player.py`, all paths under `/api/joueur`.
- `GET /api/joueur/profils` -> `[{id, name}]`, active `role='player'` users by name.
- `POST /api/joueur/profils` body `{name}` -> `{id, name}` (201). 422
  `"Le nom est requis."` when empty after strip; 422 `"Nom trop long (80 caractères au plus)."`
  over 80; 409 `"Ce nom de joueur existe déjà."` when an active player's
  name equals it under `normalize_surface`.
- `GET /api/joueur/mondes` -> `[{id, name, description, laws}]` for
  `open_to_players` worlds by name; laws by position.
- `POST /api/joueur/savoir/ask` body `{profile_id, world_id, question,
  attempt_id?}`; `POST /api/joueur/savoir/resolve` body `{profile_id,
  world_id, plan, bindings, question, attempt_id?}`. Answer keys exactly
  `{verdict, answer, renderer, candidates, plan}`. 404 `"Monde introuvable."`
  for a world unknown or not open; 404 `"Profil introuvable."` for a profile
  unknown, inactive or not `player`; 503/502/422 as C-10. Journal as C-10
  with `asked_by "player:<profile_id>"`, `withheld` computed and journaled,
  never returned.
Writer: C-12.
### C-14 -- the player shell
Produced by: G   Consumed by: (live gate)
Files: `frontend/jouer.html` (loads `/src/joueur/main.js`),
`frontend/src/joueur/main.js`, `JoueurApp.svelte`, `joueur.svelte.js`
(state + fetch helpers), `ProfilePicker.svelte`, `WorldList.svelte`,
`WorldPage.svelte`. Every `fetch` URL under `frontend/src/joueur/` starts
with `/api/joueur/`; no import leaves `frontend/src/joueur/`. Server:
`GET /jouer` in `app.py` returns `static/jouer.html` with
`headers={"cache-control": _REVALIDATE_CACHE_CONTROL}`.

## Context

The player gets his own page (P1): a separate bundle that never loads the
creator's code. He picks a profile, sees the open worlds with their
description and laws, and asks what everybody knows. Character creation
(TICKET-0126) will be added to the world page.

## Scope IN

Commit 1 -- **build and serving**:
1. `frontend/vite.config.js`: `build.rollupOptions.input = { main:
   fileURLToPath(new URL('./index.html', import.meta.url)), jouer:
   fileURLToPath(new URL('./jouer.html', import.meta.url)) }` (with
   `import { fileURLToPath } from 'node:url'`); `external` unchanged.
2. `frontend/jouer.html`: same skeleton as `index.html` (`lang="fr"`,
   title `World Engine — Joueur`, `/static/shared.css` only, `<div
   id="app"></div>`, `<script type="module" src="/src/joueur/main.js">`).
3. `frontend/scripts/write-manifest.mjs:31` and
   `tooling/verify/checks/frontend_build_fresh.py:38`: add `jouer.html`
   after `index.html`, in both, identically (R-29: the two algorithms must
   stay equal). Update both header comments' SOURCE SET line.
4. `src/world_engine/cockpit/app.py`: one decorator route
   ```python
   @app.get("/jouer", response_class=HTMLResponse)
   def serve_player_shell() -> HTMLResponse:
       """The player shell (TICKET-0125, P1): its own page and bundle, never
       the creator shell. Not a `_SHELL_ROUTES` surface."""
       return HTMLResponse(
           (_STATIC_DIR / "jouer.html").read_text(encoding="utf-8"),
           headers={"cache-control": _REVALIDATE_CACHE_CONTROL},
       )
   ```
   `_SHELL_ROUTES` and `router.js` unchanged.

Commit 2 -- **the player shell** (all files under `frontend/src/joueur/`,
French UI, no import outside this folder):
5. `main.js`, exactly (R-37):
   ```js
   import JoueurApp from './JoueurApp.svelte';
   import { mount } from 'svelte';

   mount(JoueurApp, { target: document.getElementById('app') });
   ```
6. `joueur.svelte.js`: `joueurState = $state({ profile: null, profiles: [],
   worlds: [], world: null, question: '', asking: false, error: '',
   result: null, selections: {}, attemptId: '' })`; a local `call(url,
   options)` fetch helper that throws `Error(detail)` on a non-2xx answer;
   `loadProfiles`, `createProfile(name)`, `chooseProfile(p)` (stores
   `{id, name}` under `localStorage` key `wg-joueur-profile`, read/written
   in try/catch), `restoreProfile()`, `loadWorlds`, `openWorld(w)`,
   `askSavoir()`, `selectSavoirCandidate`, `confirmSavoir()` -- every URL a
   C-11 path.
7. `JoueurApp.svelte`: no profile -> `ProfilePicker`; else, no world ->
   `WorldList`; else `WorldPage`. A header line `Joueur : {name}` with
   `Changer de joueur`.
8. `ProfilePicker.svelte`: the profile list as buttons; a field and `Créer`
   (422/409 messages shown as returned).
9. `WorldList.svelte`: one card per open world: name, description, laws as
   a list titled `Lois du monde`; empty -> `Aucun monde n'est ouvert aux
   joueurs pour l'instant.`
10. `WorldPage.svelte`: the world's name, description and laws; a section
    `Ce que tout le monde sait` with the question box, the answer, and on
    `ambiguous_mention` the candidates (name and type) to choose; a disabled
    button `Créer mon personnage (bientôt)`; `Retour aux mondes`.
11. Rebuild; commit the output (`static/jouer.html` and its assets).

Commit 3 -- **the invariant and the checks**:
12. New `.claude/rules/player-surface.md`:
    ```markdown
    ---
    paths:
      - "frontend/src/joueur/**"
      - "src/world_engine/cockpit/routes/player.py"
      - "src/world_engine/cockpit/perspective_flow.py"
      - "src/world_engine/perspective_*.py"
    ---

    # The player surface

    The player shell is `/jouer`, its own bundle. Its pages call only
    `/api/joueur/*`; those routes key on a world (and later a character),
    never on `world.is_active`.

    ## Invariants

    - **INV-66** A player surface learns about the world only through a
      perspective (`perspective_query`), never a creator selector, the
      creator name regime, a trace, near names or the audit; every
      perspective question is journaled with what was withheld. The
      perspective selectors read `faction_membership` with the
      `read_public_memberships` WHERE triplet, keyed by faction (a third
      sanctioned reader, INV-03). -- enforced by `perspective_isolation.py`,
      `player_routes.py`, `player_shell.py`
    ```
13. `CLAUDE.md`, Path-scoped rules list, after `- \`authoring-lore.md\` …`:
    `` - `player-surface.md` — the player shell, its routes, the perspective. ``
    and in Stack, after the sentence ending "until its own ticket.":
    "The player shell is a second page, `/jouer`, with its own bundle."
    Stay within `claude_md_contract.py`'s budgets (R-32).
14. `player_shell.py` gains:
    - **PSH2** -- every `fetch(` / `call(` URL literal under
      `frontend/src/joueur/` starts with `/api/joueur/`; at least one found.
    - **PSH3** -- no `import` under `frontend/src/joueur/` resolves outside
      that folder (relative paths only, never `..`) other than `svelte`.
    - **PSH4** -- `vite.config.js` names `jouer.html` as an input;
      `frontend/jouer.html` loads `/src/joueur/main.js`; `app.py` holds the
      `/jouer` decorator route reading `jouer.html`; `/jouer` is not in
      `_SHELL_ROUTES`.
    PASS line: `PASS: player_shell -- the Lore perspective tab is wired; the player shell calls only /api/joueur and imports nothing of the creator`.

## Scope OUT

- No link to `/jouer` from the creator header (drafting decision 10).
- No character creation, no "Mes savoirs" on a character (0126, 0127).
- No authentication, no cookie, no server session.
- No change to `_SHELL_ROUTES`, `router.js`, `App.svelte`.

## Invariants to defend

- **INV-66** (new, this brief).
- INV-55 -- no `$effect` self-write.
- `static_asset_freshness.py` rules 3-4 and `frontend_build_fresh.py`:
  the new page and route carry the freshness directive and the hash.
- `legacy_mount.py` rule 7: `_SHELL_ROUTES` and `SHELL_ROUTES` untouched.

## Decision rights

STOP:
- an anchor has moved;
- `claude_md_contract.py` reports a budget overflow (Nia decides what to
  shorten);
- the multi-page build breaks `index.html`'s output path.
ADAPT:
- Vite emits the second page under another name than `jouer.html`: point the
  route at the emitted name and assert it in PSH4;
REPORT-ONLY:
- styling choices of the player pages.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `player_shell.py` (PSH1-PSH4), `static_asset_freshness.py`,
      `frontend_build_fresh.py`, `legacy_mount.py`, `claude_md_contract.py`,
      `effect_self_write.py` PASS.
- [ ] Named mutation PSH2: a `fetch('/api/worlds')` in `WorldList.svelte`
      makes PSH2 fail (then revert).
- [ ] Named mutation PSH3: an import of `../lib/serverState.svelte.js` makes
      PSH3 fail (then revert).
- [ ] `corpus_gate.py` passes; TICKET-0125's Machine-checkable section all
      green.
- [ ] Live (Nia): the live criteria of TICKET-0125.
- [ ] `/review-step` and `/close-step` on each commit.

## Docs to update

- `.claude/rules/player-surface.md` and `CLAUDE.md` (Scope IN 12-13).
- `ARCHITECTURE_DECISIONS.md` entry above the footer:
  `## The player shell (BRIEF-0125-G, no schema change)` -- P1, why a
  second page and not a surface, INV-66.
- Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.
