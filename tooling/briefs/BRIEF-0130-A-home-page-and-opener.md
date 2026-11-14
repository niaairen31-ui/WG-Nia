# BRIEF 0130-A — "home-page-and-opener"

Lot: LOT-0130-home-page.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/cockpit/app.py:292-299` -> `@app.get("/jouer", response_class=HTMLResponse)` on `serve_player_shell`, `HTMLResponse((_STATIC_DIR / "jouer.html").read_text(encoding="utf-8"), headers={"cache-control": _REVALIDATE_CACHE_CONTROL})`.
- `src/world_engine/cockpit/app.py:332` -> `_SHELL_ROUTES = ("/", "/play", "/creation", "/creation/{sub_tab}", "/observation", "/journee", "/lore")`; loop at 346-349.
- `frontend/src/lib/router.js:10` -> the same seven, same order.
- `frontend/vite.config.js:14-17` -> `input: { main: ...index.html, jouer: ...jouer.html }`.
- `tooling/verify/checks/frontend_build_fresh.py:38` and `frontend/scripts/write-manifest.mjs:31` -> the same five root files ending with `jouer.html`.
- `scripts/cockpit.py:29, 31-32, 34` -> module-level `from world_engine.cockpit.app import app`; `HOST = "127.0.0.1"`, `PORT = 8000`; `if __name__ == "__main__":`.
- `.claude/launch.json` -> one configuration `cockpit`, port 8001, no environment set in its `-c` program.
- `grep -rn "accueil\|browser_open\|home_page\|--ouvrir\|webbrowser"` over `src scripts frontend/src frontend/*.html frontend/*.js frontend/scripts tooling .claude` -> empty.

## Facts carried

### R-01 -- the cockpit's HTML routes
Opened: `src/world_engine/cockpit/app.py:86, 95, 109, 166, 292-299, 330-349`
Finding: `_STATIC_DIR = Path(__file__).parent / "static"` (95);
`_REVALIDATE_CACHE_CONTROL = "no-cache"` (109); `/static` is mounted on
`_STATIC_DIR` (166). `/jouer` is a decorator route on `serve_player_shell`
returning `static/jouer.html` with `headers={"cache-control":
_REVALIDATE_CACHE_CONTROL}` (292-299). `_SHELL_ROUTES` (332) holds `"/"`
first; `_serve_shell` returns `static/index.html` with the same header
(335-343); a module-level loop registers each with `app.add_api_route`
(346-349).
Consequence: the home route copies the `/jouer` form, reading
`accueil.html`; `"/"` leaves the tuple.

### R-02 -- the client router
Opened: `frontend/src/lib/router.js:8-34`
Finding: `SHELL_ROUTES` (10) mirrors `_SHELL_ROUTES`. `parse` maps `"/"`
and `"/play"` to play (13-15) and falls back to play (33).
Consequence: `"/"` leaves `SHELL_ROUTES`; `parse` unchanged.

### R-03 -- legacy_mount rule 7
Finding: `_SHELL_ROUTES` (AST) must equal `SHELL_ROUTES` (regex), ordered.
Consequence: both lose `"/"` in the same commit.

### R-04 -- static_asset_freshness rule 4
Finding: every `@app.<verb>(..., response_class=HTMLResponse)` function
builds `HTMLResponse(..., headers={"cache-control": ...})` with a dict
literal; `_SHELL_ROUTES` non-empty with its loop.
Consequence: `serve_home` passes the header as a dict literal.

### R-05 -- player_shell PSH4
Finding: `jouer.html` a Vite input loading `/src/joueur/main.js`; the
`/jouer` decorator route reading `"jouer.html"`; `/jouer` not in
`_SHELL_ROUTES`.
Consequence: unchanged; `frontend/src/joueur/` untouched.

### R-06 -- the build's source set, two copies
Finding: `ROOT_FILES` (`frontend_build_fresh.py:38`) and
`write-manifest.mjs` (header comment 3-5, loop 31) name the same five root
files; docstring lines 11 and 63 say "five".
Consequence: both gain `accueil.html` at the end; "five" becomes "six".

### R-07 -- Vite inputs
Finding: `base: '/static/'`, outDir `../src/world_engine/cockpit/static`,
`emptyOutDir: true`; inputs `main`, `jouer`. Measured: a script-free HTML
input builds and comes out unchanged.
Consequence: a third key `accueil`.

### R-08 -- the shared stylesheet
Finding: `frontend/public/shared.css` declares `--bg`, `--panel`,
`--card`, `--border`, `--text`, `--muted`, `--accent`, `--radius`
(15-25), served at `/static/shared.css`.
Consequence: `accueil.html` uses only those tokens.

### R-09 -- the launcher script
Finding: `scripts/cockpit.py` imports `app` at module level (29); `HOST`,
`PORT` (31-32); `uvicorn.run(app, host=HOST, port=PORT, reload=False,
access_log=True)` under `__main__`; no argument parsing; docstring first
sentence "Launch the World Engine Cockpit on 127.0.0.1:8000."
Consequence: `--ouvrir` parsed under `__main__`; first sentence kept.

### R-10 -- database resolution
Finding: `WORLD_ENGINE_DATABASE_URL` wins; else `WORLD_ENGINE_ENV` `prod`
or `test`; else `RuntimeError` at import. `load_dotenv()` runs first.
Consequence: P1 sets `WORLD_ENGINE_ENV` before the app import.

### R-11 -- Claude Code's preview
Finding: `.claude/launch.json` `runtimeArgs` is `["-c", "import sys;
sys.path.insert(0, 'src'); import uvicorn; from world_engine.cockpit.app
import app; uvicorn.run(app, host='127.0.0.1', port=8001)"]`; no env.
Consequence: the program gains the env assignment before the import.

### R-14 -- checks reading the touched files (disposition)
`legacy_mount.py` rule 7: both lists change together. `static_asset_freshness.py`
rule 4: `serve_home` carries the header. `player_shell.py` PSH4: unchanged.
`frontend_build_fresh.py`: `ROOT_FILES` gains `accueil.html`. The other
`app.py` readers (router mounts, origin-guard wiring, purge and boot
guards, absence of `db.delete` / `Entity(` / `/vendor`, docstring
mentions) are unaffected. No check enumerates HTML files. No check reads
`scripts/cockpit.py` or `.claude/launch.json`. Full raw grep: LOT R-14.

### R-15 -- module map and discovery
Finding: FM1 needs a module docstring in every module of
`src/world_engine`, `scripts`, `tooling/glue`, `tooling/verify`; FM3 needs
`tooling/standards/FILE_MAP.md` fresh (`python tooling/glue/gen_file_map.py`).
`corpus_gate.py` runs every check file by glob.

### R-16 -- how a check builds a client
Finding: `origin_guard.py` sets `WORLD_ENGINE_DATABASE_URL` to a
temp-file SQLite URL and `setdefault("WORLD_ENGINE_ENV", "test")` before
any `world_engine` import, then `TestClient(app, base_url=...)`. O4 binds
only files that call `client.(post|put|patch|delete)(`.

### R-17 -- CLAUDE.md
Finding: line 326 `- **World cockpit:** \`python scripts/cockpit.py\` ->
http://127.0.0.1:8000,`; budget 22,000 characters, file at 20,662; lines
at most 100 characters.

### R-18 -- the decision log
Finding: `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a
blank line, `*Co-built with Claude, June 2026.*`; the last entry is
TICKET-0129's.

## Contracts

### C-01 -- the browser opener
Module: `src/world_engine/cockpit/browser_open.py`, stdlib only (`socket`,
`threading`, `time`, `webbrowser`, `typing`); imports nothing from
`world_engine`.
```python
def open_when_ready(url: str, host: str, port: int, *, timeout: float = 30.0,
                    opener: Callable[[str], object] = webbrowser.open) -> bool
def start_opener(url: str, host: str, port: int) -> threading.Thread
```
`open_when_ready`: tries `socket.create_connection((host, port),
timeout=0.5)` every 0.25 s until it succeeds or `timeout` seconds have
passed (`time.monotonic`). On the first success it closes the socket,
calls `opener(url)` exactly once and returns `True`. On timeout it never
calls `opener` and returns `False`. An `OSError` from the connection is
the retry signal, never raised.
`start_opener`: starts and returns a daemon thread running
`open_when_ready(url, host, port)`; if that returns `False`, the thread
prints `Navigateur non ouvert : le cockpit n'a pas répondu à temps.`

### C-02 -- the home page
`frontend/accueil.html` verbatim (Scope IN 1), built unchanged to
`src/world_engine/cockpit/static/accueil.html`. Holds `href="/play"` with
`Créatrice`, `href="/jouer"` with `Joueur`, links `/static/shared.css`,
no `<script`, no `fetch`. `GET /` -> `serve_home`, 200, that file,
`cache-control: no-cache`.

## Context

The player shell exists at `/jouer` (TICKET-0125) but nothing leads to it,
and Nia's launcher opens no browser. This brief puts a home page at `/`
with two doors, lets the launcher open it, and pins Claude Code's preview
to the test database. Decisions A2-a, H1, B1, O1, P1 (ticket).

## Scope IN

Commit 1 -- the page, the routes, the opener (items 1-9).

1. Create `frontend/accueil.html`, verbatim:
   ```html
   <!doctype html>
   <html lang="fr">
     <head>
       <meta charset="UTF-8" />
       <title>World Engine</title>
       <link rel="stylesheet" href="/static/shared.css">
       <style>
         .home { min-height: 100vh; display: flex; flex-direction: column;
                 align-items: center; justify-content: center; gap: 2rem;
                 background: var(--bg); color: var(--text); }
         .home h1 { margin: 0; font-size: 2rem; }
         .home-doors { display: flex; gap: 1.5rem; flex-wrap: wrap;
                       justify-content: center; }
         .home-door { display: block; width: 14rem; padding: 1.5rem;
                      background: var(--card); border: 1px solid var(--border);
                      border-radius: var(--radius); color: var(--text);
                      text-decoration: none; text-align: center; }
         .home-door:hover { border-color: var(--accent); }
         .home-door strong { display: block; font-size: 1.25rem;
                             margin-bottom: 0.5rem; }
         .home-door span { color: var(--muted); }
       </style>
     </head>
     <body>
       <main class="home">
         <h1>World Engine</h1>
         <nav class="home-doors">
           <a class="home-door" href="/play">
             <strong>Créatrice</strong>
             <span>Créer et faire vivre les mondes</span>
           </a>
           <a class="home-door" href="/jouer">
             <strong>Joueur</strong>
             <span>Entrer dans un monde ouvert</span>
           </a>
         </nav>
       </main>
     </body>
   </html>
   ```
2. `frontend/vite.config.js`: after the `jouer:` line of `input`, add
   `accueil: fileURLToPath(new URL('./accueil.html', import.meta.url)),`
   with the comment `// TICKET-0130 (A2-a): the home page at /, no script.`
   on the line above it.
3. The build's source set (R-06), both copies, in one commit:
   - `tooling/verify/checks/frontend_build_fresh.py:38`: `ROOT_FILES =
     ("package.json", "package-lock.json", "vite.config.js", "index.html",
     "jouer.html", "accueil.html")`; "five" -> "six" at lines 11 and 63.
   - `frontend/scripts/write-manifest.mjs`: the loop list (31) ends with
     `'jouer.html', 'accueil.html'`; the header comment (3-5) names
     `frontend/accueil.html` after `frontend/jouer.html`.
4. `src/world_engine/cockpit/app.py`, immediately above
   `@app.get("/jouer", ...)`:
   ```python
   @app.get("/", response_class=HTMLResponse)
   def serve_home() -> HTMLResponse:
       """The home page (TICKET-0130, A2-a): two links, the creator's shell
       at /play and the player's at /jouer. No script. Not a `_SHELL_ROUTES`
       surface."""
       return HTMLResponse(
           (_STATIC_DIR / "accueil.html").read_text(encoding="utf-8"),
           headers={"cache-control": _REVALIDATE_CACHE_CONTROL},
       )
   ```
   and remove `"/", ` from `_SHELL_ROUTES` (332), leaving `("/play",
   "/creation", "/creation/{sub_tab}", "/observation", "/journee",
   "/lore")`.
5. `frontend/src/lib/router.js:10`: the same six, same order. `parse` is
   not changed.
6. Create `src/world_engine/cockpit/browser_open.py` satisfying C-01, with
   the module docstring opening: `Open the browser on the cockpit once it
   answers (TICKET-0130, O1).` No other public name.
7. `scripts/cockpit.py`:
   - keep the docstring's first sentence; in its Usage block, add
     `    python scripts/cockpit.py --ouvrir   # also opens the browser on the home page`
     and change `Then open: http://127.0.0.1:8000` to
     `Then open: http://127.0.0.1:8000 (home page; the cockpit is /play).`
   - under `if __name__ == "__main__":`, before the prints: parse
     arguments with `argparse` -- one flag `--ouvrir`
     (`action="store_true"`, help `ouvre le navigateur sur la page
     d'accueil une fois le cockpit prêt`). After the prints and before
     `uvicorn.run`: `if args.ouvrir: start_opener(f"http://{HOST}:{PORT}/",
     HOST, PORT)`. `start_opener` is imported from
     `world_engine.cockpit.browser_open` next to the existing app import.
   - nothing else changes (host, port, `reload`, `access_log`).
8. `.claude/launch.json`: `runtimeArgs[1]` becomes, verbatim:
   `import os; os.environ['WORLD_ENGINE_ENV'] = 'test'; import sys; sys.path.insert(0, 'src'); import uvicorn; from world_engine.cockpit.app import app; uvicorn.run(app, host='127.0.0.1', port=8001)`.
   Nothing else in the file changes.
9. `cd frontend`, `npm ci`, `npm run build`; commit the output under
   `src/world_engine/cockpit/static/` (including `accueil.html` and the new
   `.build-manifest.json`).

Commit 2 -- the check.

10. Create `tooling/verify/checks/home_page.py`, a G1 check in the
    `FAILURES` / `fail` / exit-code form of `player_shell.py`, its
    docstring listing the rules below. A missing file, or a rule that
    collects nothing, is a FAILURE.
    - HP1 (static, AST of `cockpit/app.py`): a module-level function
      decorated `@app.get("/", response_class=HTMLResponse)` whose source
      holds `"accueil.html"`; `"/"` is not in `_SHELL_ROUTES`; `"/play"`
      is.
    - HP2 (static, frontend): `vite.config.js` names `accueil.html` inside
      `input`; `frontend/accueil.html` holds `href="/play"`,
      `href="/jouer"`, `Créatrice`, `Joueur`, `/static/shared.css`, and
      none of `<script`, `fetch(`; the built
      `src/world_engine/cockpit/static/accueil.html` exists and holds both
      hrefs; no file under `frontend/src/joueur/` holds `href="/"`,
      `href="/play"` or `"/play"` (B1), at least one file scanned (today
      the grep is empty: `grep -rn 'href="/"\|"/play"\|href="/play"'
      frontend/src/joueur` returned nothing in the lot RECON).
    - HP3 (live): set-up as R-16 (temp-file `WORLD_ENGINE_DATABASE_URL`,
      `setdefault("WORLD_ENGINE_ENV", "test")`, before any `world_engine`
      import); `TestClient(app, base_url="http://127.0.0.1")`, no `with`
      block. `GET /` is 200, holds `href="/jouer"` and `href="/play"`, and
      its `cache-control` contains `no-cache`; `GET /play` is 200, holds
      `<div id="app">` and not `href="/jouer"`; `GET /jouer` is 200 and
      holds `World Engine — Joueur`.
    - HP4 (live, C-01): import `world_engine.cockpit.browser_open` alone.
      With a listening socket on `127.0.0.1`, port 0: `open_when_ready`
      returns `True` and a recording opener got exactly `[url]`. With a
      port bound then closed (nothing listening), `timeout=1.0`: returns
      `False` and the opener got nothing. AST of `scripts/cockpit.py`: an
      `add_argument("--ouvrir", ...)` call exists; every call to
      `start_opener` sits inside an `if` whose test names `ouvrir`; at
      least one such call.
    - HP5 (static): `.claude/launch.json` parses as JSON; the `cockpit`
      configuration's `-c` program holds `os.environ['WORLD_ENGINE_ENV'] =
      'test'` at an index before `from world_engine.cockpit.app import
      app`, and does not hold `prod`.

Commit 3 -- the docs.

11. `CLAUDE.md`, the « World cockpit » bullet (R-17): replace
    `http://127.0.0.1:8000,` with the text below, rewrapping the bullet at
    100 characters like its neighbours, the rest of the bullet unchanged:
    `http://127.0.0.1:8000 (home page: creator's shell at \`/play\`,
    player's at \`/jouer\`; \`--ouvrir\` opens it once the server answers;
    \`.claude/launch.json\` pins \`WORLD_ENGINE_ENV=test\`),`
12. `tooling/standards/ARCHITECTURE_DECISIONS.md`, above the closing `---`
    (R-18), verbatim:
    ```markdown
    ## TICKET-0130 — the home page and the launcher (BRIEF-0130-a, no schema change)

    `/` serves `accueil.html`, a third Vite input with no script and two
    links: « Créatrice » to the creator's shell, now reached at `/play`,
    and « Joueur » to the player's shell at `/jouer` (A2-a, H1). `/` left
    `_SHELL_ROUTES` and `router.js`. The player's shell links to neither
    (B1). `scripts/cockpit.py --ouvrir` opens the default browser on the
    home page once the server accepts connections
    (`cockpit/browser_open.py`); without the flag nothing opens (O1). The
    preview in `.claude/launch.json` sets `WORLD_ENGINE_ENV=test` itself
    (P1); an explicit `WORLD_ENGINE_DATABASE_URL` still wins. Gate:
    `home_page.py`.

    Deferred: a link from the creator's shell to the home page; the
    player profiles on the home page (H2).
    ```
13. `python tooling/glue/gen_file_map.py`; commit
    `tooling/standards/FILE_MAP.md`.

## Scope OUT

- `start-prod.cmd` (on Nia's desktop, not in the repo): Claude edits it
  from the chat after the merge.
- Any link from the creator's shell (header, tabs, `legacy.html`) to `/`
  or to `/jouer`; any link from `frontend/src/joueur/` anywhere (B1).
- Listing player profiles on the home page (H2); any script or API call
  on it.
- `router.js` `parse` and `navigate`; any other shell route.
- Authentication, a change of host or port, an opener in `.claude/launch.json`.
- Defending against `WORLD_ENGINE_DATABASE_URL` (carried forward).
- `frontend/index.html`, `frontend/jouer.html`, `legacy.html`.

## Invariants to defend

- INV-66 (`.claude/rules/player-surface.md`): a player surface learns the
  world only through a perspective. The home page is reached by the
  player; it must show nothing of any world -- no script, no call (H1,
  HP2).
- The fail-closed database resolution (R-10): `launch.json` sets `test`
  explicitly; nothing defaults to prod.
- The loopback binding of `scripts/cockpit.py`: `HOST` stays
  `127.0.0.1`.

## Decision rights

STOP:
- An anchor does not hold.
- `legacy_mount.py`, `static_asset_freshness.py`, `player_shell.py`,
  `origin_guard.py` or `frontend_build_fresh.py` turns red on a rule this
  brief cannot satisfy.
- `npm run build` does not emit `static/accueil.html`.

ADAPT:
- The installed uvicorn binds the port before running startup events, so
  a failed boot guard would still open the browser: keep C-01 as written,
  report it.
- HP3's `GET /play` body differs from `frontend/index.html` beyond the
  built script tags (no `<div id="app">`): assert the marker the built
  `static/index.html` actually holds, report.
- `CLAUDE.md`'s rewrapped bullet still breaks the 100-character rule:
  rewrap again, wording unchanged, report.

REPORT-ONLY:
- Another process already on port 8000 makes `--ouvrir` open on it.
- `parse("/")` in `router.js` is now unreachable.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/home_page.py`
      PASS (HP1-HP5); `legacy_mount.py`, `static_asset_freshness.py`,
      `player_shell.py`, `frontend_build_fresh.py`, `origin_guard.py`,
      `file_map.py`, `claude_md_contract.py` PASS.
- [ ] Named mutations, each red then reverted: put `"/"` back first in
      `_SHELL_ROUTES` and `SHELL_ROUTES` -> HP1 (and the route conflicts);
      in `open_when_ready`, call `opener(url)` before the first connection
      attempt -> HP4; drop the `os.environ` assignment from `launch.json`
      -> HP5; add `<script>` to `accueil.html` -> HP2.
- [ ] `corpus_gate.py` PASS.
- [ ] Live, on Nia's machine: `python scripts/cockpit.py --ouvrir` with
      `WORLD_ENGINE_ENV=test` opens the browser on the home page;
      « Créatrice » shows Play, « Joueur » shows the profile choice;
      without `--ouvrir` no browser opens.
- [ ] `/review-step` then `/close-step` (DECISIONS_INDEX regenerated).

## Docs to update

CLAUDE.md (Scope IN 11), ARCHITECTURE_DECISIONS (12), FILE_MAP (13). No
schema change, no migration. After the merge, Claude (chat) adds
`--ouvrir` to `start-prod.cmd` with Nia's yes.
