# LOT — TICKET-0130 "A home page chooses the creator's cockpit or the player's shell"

Lot RECON run in the chat session on `main` at `2d419b4` (PR #156,
TICKET-0129 merged; schema v2.33). One brief. This header is authoritative
on any conflict with the brief's embedded copy.

## Objective and cut

`/` stops being the creator shell and serves a small home page with two
links: « Créatrice » to `/play`, « Joueur » to `/jouer` (A2-a, H1). The
player shell gets no link back (B1). `scripts/cockpit.py --ouvrir` opens
the default browser on the home page once the server answers (O1). Claude
Code's preview pins the test database (P1).

The lot stops there. Not in it: editing `start-prod.cmd` (it lives on
Nia's desktop, outside the repo; Claude edits it from the chat after the
merge, with Nia's yes), any authentication, a link from the creator shell
to the home page, the player profiles on the home page (H2).

## Briefs in this lot

- A -- `home-page-and-opener`: `accueil.html` and its route, `/` out of the
  shell vocabulary, the build lists, `browser_open.py` and `--ouvrir`, the
  preview's test database, the check `home_page.py`, the docs.

## Dependency graph

One brief; nothing in this lot precedes it. Inside the brief, commits in
the order of Scope IN: code and build, then the check, then the docs.

## RECON

### R-01 -- the cockpit's HTML routes
Opened: `src/world_engine/cockpit/app.py:86, 95, 109, 166, 292-299, 330-349`
Finding: `_STATIC_DIR = Path(__file__).parent / "static"` (95);
`_REVALIDATE_CACHE_CONTROL = "no-cache"` (109); `/static` is mounted on
`_STATIC_DIR` (166). `/jouer` is a decorator route,
`@app.get("/jouer", response_class=HTMLResponse)` on `serve_player_shell`,
returning `HTMLResponse((_STATIC_DIR / "jouer.html").read_text(encoding="utf-8"),
headers={"cache-control": _REVALIDATE_CACHE_CONTROL})` (292-299).
`_SHELL_ROUTES = ("/", "/play", "/creation", "/creation/{sub_tab}",
"/observation", "/journee", "/lore")` (332); `_serve_shell` returns
`static/index.html` with the same header (335-343); a module-level loop
registers each with `app.add_api_route(_shell_path, _serve_shell,
methods=["GET"], response_class=HTMLResponse)` (346-349). The file is 349
lines.
Consequence: the home route copies the `/jouer` form exactly, reading
`accueil.html`; `"/"` leaves the tuple so the loop does not register it a
second time.

### R-02 -- the client router
Opened: `frontend/src/lib/router.js:8-34`
Finding: `export const SHELL_ROUTES = ["/", "/play", "/creation",
"/creation/{sub_tab}", "/observation", "/journee", "/lore"];` (10), with a
comment that it is mirrored in `_SHELL_ROUTES`. `parse` maps `"/"` and
`"/play"` to `{ surface: "play" }` (13-15) and falls back to play for any
unknown path (33). `navigate("play")` pushes `/play` (37).
Consequence: `"/"` leaves `SHELL_ROUTES` in the same position as in
`app.py`. `parse` is left unchanged: once the shell is never served at
`/`, its `"/"` branch is unreachable but harmless, and its fallback is
already play.

### R-03 -- legacy_mount rule 7
Opened: `tooling/verify/checks/legacy_mount.py:27-32, 280-330`
Finding: `_SHELL_ROUTES` (AST) must equal `SHELL_ROUTES` (regex over the
array literal), compared as ordered lists; an empty side is a FAILURE.
Consequence: both lose `"/"`; the remaining six stay in order.

### R-04 -- static_asset_freshness rule 4
Opened: `tooling/verify/checks/static_asset_freshness.py:31-38, 200-330`
Finding: every module-level function decorated `@app.<verb>(...,
response_class=HTMLResponse)` must build `HTMLResponse(...,
headers={"cache-control": ...})` (a `headers=` dict literal with that
key); `_SHELL_ROUTES` must be non-empty and its registering loop found.
Consequence: the home route passes the header as a dict literal, as
`/jouer` does. Six shell routes remain.

### R-05 -- player_shell PSH4
Opened: `tooling/verify/checks/player_shell.py:17-20, 140-176`
Finding: PSH4 requires `jouer.html` as a Vite input, `jouer.html` loading
`/src/joueur/main.js`, the `/jouer` decorator route reading
`"jouer.html"`, and `/jouer` absent from `_SHELL_ROUTES`. PSH2/PSH3
confine `frontend/src/joueur/`.
Consequence: unchanged; nothing in `frontend/src/joueur/` is touched (B1).

### R-06 -- the build's source set, two copies
Opened: `tooling/verify/checks/frontend_build_fresh.py:1-25, 38, 62-80`;
`frontend/scripts/write-manifest.mjs:1-12, 31`
Finding: `ROOT_FILES = ("package.json", "package-lock.json",
"vite.config.js", "index.html", "jouer.html")` (38); the docstring says
"the five named root files" (11, 63). `write-manifest.mjs` names the same
five in its header comment (3-5) and its loop (31), "implemented
identically". The check hashes `frontend/src/**` plus those files and
compares to `static/.build-manifest.json`.
Consequence: `accueil.html` is added to both lists, at the end, and both
"five" become "six"; otherwise a change to `accueil.html` would never make
the build stale.

### R-07 -- Vite inputs
Opened: `frontend/vite.config.js:1-27`
Finding: `base: '/static/'`, `outDir: '../src/world_engine/cockpit/static'`,
`emptyOutDir: true`; `rollupOptions.input` is `{ main: ...index.html,
jouer: ...jouer.html }` (14-17).
Consequence: a third key `accueil` after `jouer`. Measured in the chat
session (copy of `frontend/`, `npx vite build` into a scratch outDir): an
HTML input with no script builds, and `accueil.html` comes out unchanged,
`/static/shared.css` link kept.

### R-08 -- the player page and the shared stylesheet
Opened: `frontend/jouer.html`; `frontend/public/` (listing);
`frontend/public/shared.css:15-26, 30`
Finding: `jouer.html` is `lang="fr"`, links `/static/shared.css`, holds
`<div id="app">` and one module script. `frontend/public/` holds
`creation.css` and `shared.css`, copied to `static/`. `shared.css`
declares `--bg`, `--panel`, `--card`, `--border`, `--text`, `--muted`,
`--accent`, `--radius` (15-25) and styles `body` (30).
Consequence: `accueil.html` links `/static/shared.css` and uses only those
tokens in its own `<style>`.

### R-09 -- the launcher script
Opened: `scripts/cockpit.py` (whole file, 46 lines)
Finding: module docstring first sentence "Launch the World Engine Cockpit
on 127.0.0.1:8000."; puts `src` on `sys.path`; imports `uvicorn` and then
`from world_engine.cockpit.app import app` at module level (29), which
resolves the database (R-10); `HOST = "127.0.0.1"`, `PORT = 8000` (31-32);
under `if __name__ == "__main__":` prints and calls `uvicorn.run(app,
host=HOST, port=PORT, reload=False, access_log=True)` (34-46). No argument
parsing.
Consequence: `--ouvrir` is parsed under `__main__`; the opener is a module
in `src/` (C-01) so the check can import it without importing `app`. The
docstring's first sentence stays (it is the FILE_MAP line, R-15).

### R-10 -- database resolution
Opened: `src/world_engine/db.py:1-75`
Finding: `load_dotenv()` runs if python-dotenv is installed.
`WORLD_ENGINE_DATABASE_URL`, when non-empty, wins outright; else
`WORLD_ENGINE_ENV` must be `prod` (`~/.world_engine/world_engine.db`) or
`test` (`~/.world_engine/test/world_engine_test.db`); else `RuntimeError`
at import.
Consequence: P1 is met by setting `WORLD_ENGINE_ENV` to `test` before
`world_engine.cockpit.app` is imported. An explicit URL still wins (ticket,
carried forward).

### R-11 -- Claude Code's preview
Opened: `.claude/launch.json` (whole file)
Finding: one configuration `"name": "cockpit"`, `"runtimeExecutable":
"python"`, `"runtimeArgs": ["-c", "import sys; sys.path.insert(0, 'src');
import uvicorn; from world_engine.cockpit.app import app; uvicorn.run(app,
host='127.0.0.1', port=8001)"]`, `"port": 8001`, `"autoPort": false`. No
environment is set: the database is whatever the inherited shell says.
Consequence: the `-c` program gains `import os; os.environ['WORLD_ENGINE_ENV']
= 'test';` before the app import. Port and the rest unchanged.

### R-12 -- Nia's button (outside the repo)
Opened: `C:\Users\Utilisateur\Desktop\start-prod.cmd` (staged, 6 lines)
Finding: `cd /d "C:\Users\Utilisateur\Documents\World-genrator"`, `set
PYTHONPATH=src`, `set WORLD_ENGINE_ENV=prod`,
`.venv\Scripts\python.exe scripts\cockpit.py`, `pause`. It opens no
browser.
Consequence: no brief touches it. After the merge, Claude (chat) appends
` --ouvrir` to the python line, with Nia's yes.

### R-13 -- links to `/` (negative claim)
Opened: `grep -rn "href=['\"]/['\"]\|location\.href\s*=\s*['\"]/['\"]\|location\.assign(['\"]/['\"]\|navigate(['\"]play\|window\.location\s*=\s*['\"]/['\"]\|RedirectResponse" frontend/src src/world_engine/cockpit/legacy.html src/world_engine/cockpit/*.py src/world_engine/cockpit/routes`
Finding (raw output, whole):
```
frontend/src/journee/Journee.svelte:35:    navigate('play');
```
Nothing links or redirects to `/`; the one hit pushes `/play` (R-02).
Consequence: no in-app navigation lands on the home page by surprise.

### R-13b -- the player shell links nowhere (negative claim, B1)
Opened: `grep -rn 'href="/"\|"/play"\|href="/play"' frontend/src/joueur`;
`grep -c '<div id="app">' src/world_engine/cockpit/static/index.html`
Finding (raw output): the first is empty; the second prints `1`.
Consequence: HP2's B1 rule holds today; HP3 can tell the shell (`<div
id="app">`) from the home page.

### R-14 -- checks that read the files this brief touches
Opened: `for p in "app.py" "router.js" "vite.config.js" "cockpit.py" "launch.json" "index.html" "jouer.html" "_SHELL_ROUTES" "SHELL_ROUTES"; do grep -rln --include=*.py "$p" tooling/verify; done`
Finding (raw output):
```
== app.py
condition_interpreter.py creator_review.py effects_ledger_source.py
effects_vocab.py event_assist.py legacy_mount.py link_agent_strata.py
npc_agent_strata.py npc_batch_purge.py origin_guard.py player_shell.py
prereq_judge.py prompt_registry.py quest_designer.py relation_graph.py
review_component.py role_closed_vocab.py schema_reconciliation.py
static_asset_freshness.py submitted_drafts.py visit_delta.py world_tick.py
== router.js
legacy_mount.py review_component.py
== vite.config.js
frontend_build_fresh.py player_shell.py
== cockpit.py
(none)
== launch.json
(none)
== index.html
creation_return_nav.py event_tab.py faction_roster_panel.py
frontend_build_fresh.py graph_primitive.py modal_primitive.py
observation_surface.py page_contract.py relation_graph.py
review_component.py review_root_fallback.py shell_height_chain.py
single_canon_write.py stylesheet_partition.py
== jouer.html
frontend_build_fresh.py player_shell.py
== _SHELL_ROUTES / SHELL_ROUTES
legacy_mount.py player_shell.py static_asset_freshness.py
```
(all under `tooling/verify/checks/`; one line per file in the raw output,
wrapped here.) Disposition, from what each executes:
- `legacy_mount.py` rule 7 -- reads both route lists; both change
  together (R-03).
- `static_asset_freshness.py` rule 4 -- reads every HTML decorator route;
  the new one carries the header (R-04).
- `player_shell.py` PSH4 -- unchanged, `/jouer` stays a decorator route
  outside `_SHELL_ROUTES` (R-05).
- `frontend_build_fresh.py` -- `ROOT_FILES` gains `accueil.html` (R-06).
- The other `app.py` readers assert router mounts
  (`condition_interpreter` ND1, `creator_review`, `quest_designer` QD8,
  `submitted_drafts` SD3, `event_assist` reads `routes/creator.py`),
  origin-guard registration (`origin_guard` O2), the purge and boot-guard
  wiring (`npc_batch_purge`, `schema_reconciliation`), the absence of
  `db.delete`, `Entity(`, `current_location_id` writes and the `/vendor`
  route (`visit_delta`, `world_tick`, `relation_graph`), or name `app.py`
  in a docstring or a file list (`effects_*`, `prereq_judge`,
  `prompt_registry`, `role_closed_vocab`, `review_component`,
  `link_agent_strata`, `npc_agent_strata`). The brief adds none of these.
- The `index.html` readers read named files (`frontend/index.html`,
  `cockpit/legacy.html`, `cockpit/index.html` in docstrings); none
  enumerates HTML files: `grep -n '\*\.html\|glob("\*\.html' tooling/verify/checks/*.py`
  returned nothing. `frontend/index.html` is not touched.
- `cockpit.py`, `launch.json`: no reader.

### R-15 -- module map and the gate's discovery
Opened: `tooling/verify/checks/file_map.py:1-40`; `tooling/glue/gen_file_map.py:20`;
`tooling/verify/checks/corpus_gate.py:175-200`
Finding: FM1 requires a module docstring in every module of `SCOPES =
("src/world_engine", "scripts", "tooling/glue", "tooling/verify")`; FM3
requires `tooling/standards/FILE_MAP.md` to equal a fresh render (`python
tooling/glue/gen_file_map.py`). `corpus_gate.py` globs every `*.py` of
`tooling/verify/checks/` except itself.
Consequence: `browser_open.py` and `home_page.py` carry docstrings; the
map is regenerated in the docs commit; `home_page.py` is run by the gate
with no registration.

### R-16 -- how a check builds a client
Opened: `tooling/verify/checks/origin_guard.py:8-20, 59-60, 125-150`
Finding: the check sets `WORLD_ENGINE_DATABASE_URL` to a temp-file SQLite
URL and `setdefault("WORLD_ENGINE_ENV", "test")` before any
`world_engine` import, then builds `TestClient(app, base_url=...)`. O4
requires `base_url="http://127.0.0.1"` on a `TestClient(app` construction
only in a file that also calls `client.(post|put|patch|delete)(`.
Consequence: `home_page.py` uses the same set-up and
`base_url="http://127.0.0.1"`; it makes GET calls only.

### R-17 -- CLAUDE.md
Opened: `CLAUDE.md:326-329`; `tooling/verify/checks/claude_md_contract.py:77-80`
Finding: line 326 reads `- **World cockpit:** \`python scripts/cockpit.py\`
-> http://127.0.0.1:8000,`. Budgets: `ROOT_CHAR_BUDGET = 22_000`,
`MAX_LINE_LENGTH = 100`; `CLAUDE.md` is 20,662 characters.
Consequence: one sentence added there (Scope IN 9), well inside budget.

### R-18 -- the decision log
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:20891-20923`
Finding: the last entry is TICKET-0129's; the file ends with `---`, a
blank line, `*Co-built with Claude, June 2026.*`.
Consequence: the new entry goes above that `---`.

### R-19 -- the new names are free (negative claim)
Opened: `grep -rn "accueil\|browser_open\|home_page\|--ouvrir\|webbrowser" --include=*.py --include=*.js --include=*.svelte --include=*.html --include=*.json --include=*.mjs src scripts frontend/src frontend/*.html frontend/*.js frontend/scripts tooling .claude`
Finding (raw output, whole): empty.
Consequence: no collision.

## Contract sheet

### C-01 -- the browser opener
Produced by: BRIEF-0130-A   Consumed by: BRIEF-0130-A (`scripts/cockpit.py`, `home_page.py`)
Module: `src/world_engine/cockpit/browser_open.py`, stdlib only (`socket`,
`threading`, `time`, `webbrowser`); imports nothing from `world_engine`.
Signatures:
```python
def open_when_ready(url: str, host: str, port: int, *, timeout: float = 30.0,
                    opener: Callable[[str], object] = webbrowser.open) -> bool
def start_opener(url: str, host: str, port: int) -> threading.Thread
```
`open_when_ready`: tries `socket.create_connection((host, port),
timeout=0.5)` every 0.25 s until it succeeds or `timeout` seconds have
passed (`time.monotonic`). On the first success it closes the socket,
calls `opener(url)` exactly once and returns `True`. On timeout it never
calls `opener` and returns `False`. It never raises on a refused or
failed connection (`OSError` is the retry signal).
`start_opener`: starts and returns a daemon thread running
`open_when_ready(url, host, port)`; if that returns `False`, the thread
prints `Navigateur non ouvert : le cockpit n'a pas répondu à temps.`
Error and empty cases: none raised; a port that never opens is `False`.

### C-02 -- the home page
Produced by: BRIEF-0130-A   Consumed by: `home_page.py`
`frontend/accueil.html`, verbatim in the brief (Scope IN 1); built
unchanged to `src/world_engine/cockpit/static/accueil.html` (R-07). Holds
`href="/play"` with the text `Créatrice`, `href="/jouer"` with the text
`Joueur`, links `/static/shared.css`, holds no `<script` and no `fetch`.
Route: `GET /` -> `serve_home`, 200, the built file, `cache-control:
no-cache`.

## Gate output

(a) Property trace:
- `/jouer` is a decorator route reading `jouer.html` with the header -- R-01, `cockpit/app.py`.
- `_SHELL_ROUTES` holds `"/"` first, registered by the loop -- R-01, `cockpit/app.py`.
- `SHELL_ROUTES` mirrors it; `parse` falls back to play -- R-02, `frontend/src/lib/router.js`.
- Rule 7 compares ordered lists -- R-03, `legacy_mount.py` (implementation).
- Rule 4 requires a `headers=` dict with `cache-control` -- R-04, `static_asset_freshness.py` (implementation).
- PSH4's four conditions -- R-05, `player_shell.py` (implementation).
- `ROOT_FILES` and the manifest list are the same five -- R-06, both files.
- Vite inputs and outDir; a script-free HTML input builds -- R-07, `vite.config.js` and a measured build.
- `shared.css` tokens -- R-08, `frontend/public/shared.css`.
- `cockpit.py` imports `app` at module level, HOST/PORT -- R-09, `scripts/cockpit.py`.
- URL override wins over ENV; `load_dotenv` -- R-10, `db.py`.
- `launch.json` sets no env -- R-11, `.claude/launch.json`.
- `start-prod.cmd` opens no browser -- R-12, the file itself.
- FM1/FM3, gate discovery -- R-15, `file_map.py`, `gen_file_map.py`, `corpus_gate.py`.
- Client set-up and O4 -- R-16, `origin_guard.py` (implementation).
- CLAUDE.md budget -- R-17, `claude_md_contract.py`.
- ADR footer -- R-18, `ARCHITECTURE_DECISIONS.md`.

(b) Case tables.

Routes after the brief:

| GET path | served by | body |
|---|---|---|
| `/` | `serve_home` (decorator) | `static/accueil.html` |
| `/play`, `/creation`, `/creation/{x}`, `/observation`, `/journee`, `/lore` | `_serve_shell` (loop) | `static/index.html` |
| `/jouer` | `serve_player_shell` | `static/jouer.html` |
| `/legacy` | `serve_legacy` | `legacy.html` |
| `/static/...` | mount | file |
| anything else (`/foo`) | none | 404, as today |

`--ouvrir` and the port:

| flag | port answers within 30 s | browser |
|---|---|---|
| absent | -- | no thread started, never opens |
| present | yes | opens once on `http://127.0.0.1:8000/` |
| present | no (boot guard failed, crash) | never opens; message printed |
| present | already taken by another process | opens on whatever answers (REPORT-ONLY) |

Database by launcher:

| launcher | `WORLD_ENGINE_ENV` | database |
|---|---|---|
| `start-prod.cmd` | `prod` (set by the file) | prod |
| `.claude/launch.json` | `test` (set by the `-c` program) | test, unless `WORLD_ENGINE_DATABASE_URL` is set |
| `python scripts/cockpit.py` by hand | inherited | inherited; none -> RuntimeError (R-10) |

(c) Enumerations: R-13, R-14, R-19 (pasted).

(d) Family contracts: none (one opener, one page). Ticked.

(e) Gates:
- `home_page.py` (proposed) -- satisfied by `cockpit/app.py` (`serve_home`,
  `_SHELL_ROUTES`), `frontend/accueil.html` and its build,
  `browser_open.py`, `scripts/cockpit.py`, `.claude/launch.json`. Needs
  nothing it forbids: HP3 imports `app` under a temp database (R-16);
  HP4 imports `browser_open` alone, which imports nothing from
  `world_engine`.
- `legacy_mount.py` -- `app.py` and `router.js` edited together.
- `static_asset_freshness.py` -- `serve_home` carries the header.
- `player_shell.py` -- untouched files.
- `frontend_build_fresh.py` -- both lists and a fresh `npm run build`.
- `file_map.py` -- docstrings, regenerated map.
- `claude_md_contract.py` -- one sentence, inside budget.
- `origin_guard.py` O4 -- `home_page.py` makes no write call.

## Amendments
