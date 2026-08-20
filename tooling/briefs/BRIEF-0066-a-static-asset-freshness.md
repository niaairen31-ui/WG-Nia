# BRIEF — Step "static asset freshness policy"

TICKET-0066. Single brief; the ticket is one coherent commit plus a check.

## Context

`app.py:91` mounts the built frontend with bare `StaticFiles`, which emits
`etag` and `last-modified` but no `Cache-Control`. Browsers therefore apply
heuristic freshness to `shared.css` and `creation.css` — the two assets that
keep stable filenames by design so `cockpit/index.html` can link them — and
reuse cached copies without contacting the server at all. `_serve_shell`
returns the shell document with no cache headers either, where a stale copy
references a hashed bundle that `emptyOutDir: true` has already deleted, giving
a blank page rather than a stale render. This shipped a full session of debugging
disguised as a CSS regression. This step makes revalidation the default posture
and holds it with a fail-closed partition check.

## Mini-RECON — verify before writing

Report `file:line` for each, and STOP and escalate if any does not hold:

1. The installed Starlette version, and the exact signature of
   `StaticFiles.get_response(self, path, scope)`. The subclass in Scope IN
   item 2 overrides `get_response` specifically because it is the stable API
   across versions and also covers the 304 path; if the installed version
   differs, report before writing rather than substituting `file_response`.
2. Confirm `app.py:91` is the only `app.mount(` call in the file, and that no
   router registers a second `StaticFiles`.
3. Confirm `_serve_shell` (`app.py:247-248`) is registered only through the
   `_SHELL_ROUTES` loop at `app.py:251-253` and has no other caller.
4. `serve_legacy` (`app.py:218-226`) — confirm it is a plain
   `response_class=HTMLResponse` route returning `str`, like `_serve_shell`.
   Item 4 of Scope IN gives it the same directive; if its shape differs,
   report before changing it.
5. Enumerate every file under `_STATIC_DIR` and confirm at least one lies
   under `assets/` and at least one does not. Both partition classes must be
   non-empty or the check's own vacuous-proof guard cannot pass.
6. `app.py:73` states "The vendor whitelist below is unchanged and keeps its
   own single entry", but `grep -n vendor src/world_engine/cockpit/app.py`
   returns only comment lines. REPORT ONLY: confirm the `/vendor` route is
   gone and the comment is stale. Do not edit it — that is TICKET-0061's
   doctrine pass.

## Scope IN

1. **`src/world_engine/cockpit/app.py`, module-level policy constant.** Insert
   immediately after `_STATIC_DIR` (currently line 75), verbatim:

   ```python
   # TICKET-0066 (BRIEF-0066-a). The freshness partition, declared once and
   # read structurally by tooling/verify/checks/static_asset_freshness.py.
   # Everything Vite emits under this prefix carries a content hash in its
   # filename, so it can be cached forever; everything else -- shared.css,
   # creation.css, anything dropped into frontend/public/ later -- keeps a
   # STABLE name and therefore has no cache-busting mechanism of its own.
   # The default posture is revalidate, and immutability is the opt-in
   # exception, so a new unhashed asset is covered without anyone thinking
   # about it. This is not a convention: the check reads this constant by
   # AST and fails closed if the partition stops being exhaustive.
   _IMMUTABLE_ASSET_PREFIX = "assets"
   _IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
   _REVALIDATE_CACHE_CONTROL = "no-cache"
   ```

2. **`src/world_engine/cockpit/app.py`, the `StaticFiles` subclass.** Define it
   after the constants and before `app = FastAPI(...)`:

   ```python
   class _FreshnessAwareStaticFiles(StaticFiles):
       """Serves /static with an explicit freshness directive on every response.

       Bare StaticFiles sends etag + last-modified and NO Cache-Control, which
       lets a browser apply HEURISTIC freshness and reuse a cached copy without
       issuing a request at all. That is invisible in the Network panel and it
       is how a post-TICKET-0059 bundle came to render against pre-TICKET-0063
       stylesheets. `no-cache` means "revalidate", not "do not store": with the
       etag already emitted, the steady-state cost is a 304 on two small files.
       """

       async def get_response(self, path: str, scope):
           response = await super().get_response(path, scope)
           head = path.replace("\\", "/").lstrip("/").split("/", 1)[0]
           response.headers["cache-control"] = (
               _IMMUTABLE_CACHE_CONTROL
               if head == _IMMUTABLE_ASSET_PREFIX
               else _REVALIDATE_CACHE_CONTROL
           )
           return response
   ```

3. **`src/world_engine/cockpit/app.py:91`, the mount.** Replace
   `StaticFiles(directory=_STATIC_DIR)` with
   `_FreshnessAwareStaticFiles(directory=_STATIC_DIR)`. The `"/static"` path
   and `name="static"` are unchanged.

4. **`src/world_engine/cockpit/app.py`, the HTML routes.** `_serve_shell`
   (currently `app.py:247-248`) returns a `str`; it must return a response
   object so it can carry the header. Replace with:

   ```python
   def _serve_shell() -> HTMLResponse:
       # TICKET-0066 (BRIEF-0066-a). The shell document has a stable name and
       # no cache-busting. A stale copy is worse than a stale render: it names
       # a hashed bundle that `emptyOutDir: true` already deleted, so the
       # failure mode is a 404 on the bundle and a BLANK PAGE.
       return HTMLResponse(
           (_STATIC_DIR / "index.html").read_text(encoding="utf-8"),
           headers={"cache-control": _REVALIDATE_CACHE_CONTROL},
       )
   ```

   Apply the same change to `serve_legacy` (`app.py:218-226`): return an
   `HTMLResponse` carrying `_REVALIDATE_CACHE_CONTROL`, keeping its existing
   docstring verbatim and reading `_INDEX_HTML` exactly as it does now. Do not
   otherwise touch that function, and do not touch `index.html` itself.

   The `response_class=HTMLResponse` argument on both registrations stays.

5. **`tooling/verify/checks/static_asset_freshness.py`** — new fail-closed
   check. Same idiom as `shell_height_chain.py` and `legacy_mount.py`:
   module-level `FAILURES`, `fail()`, `_report_and_exit(counts)`, `ROOT` via
   `parents[3]`, stdlib only, no DB, no subprocess. Constants are read from
   `app.py` by **AST, never by regex** — same discipline as
   `legacy_mount.py:186-205` and `single_canon_write.py`. Four assertions:

   - **rule1 — the mount is policy-bearing.** AST-walk `app.py` for the
     `app.mount("/static", ...)` call and assert its second positional argument
     is a call to `_FreshnessAwareStaticFiles`. A bare `StaticFiles(` as the
     mounted argument anywhere in the file is a FAILURE. Missing mount call is
     a FAILURE.
   - **rule2 — the policy constants exist and are coherent.** AST-read
     `_IMMUTABLE_ASSET_PREFIX`, `_IMMUTABLE_CACHE_CONTROL` and
     `_REVALIDATE_CACHE_CONTROL` as string constants. Assert
     `_REVALIDATE_CACHE_CONTROL` contains `no-cache`, `_IMMUTABLE_CACHE_CONTROL`
     contains `immutable`, and `_IMMUTABLE_ASSET_PREFIX` names a directory that
     EXISTS under `_STATIC_DIR` — so the prefix cannot silently drift to a typo
     that classifies every asset as revalidating. Any missing or non-string
     constant is a FAILURE.
   - **rule3 — the partition is exhaustive and both classes are inhabited.**
     Walk `_STATIC_DIR` recursively. Classify each file by
     `_IMMUTABLE_ASSET_PREFIX` on its first path segment. Assert every file
     lands in exactly one class. Vacuous-proof, three ways: zero files walked
     is a FAILURE; zero files in the immutable class is a FAILURE; zero files
     in the revalidate class is a FAILURE. The last two matter — a partition
     with a dead branch proves nothing about the branch that is dead.
   - **rule4 — HTML routes carry the directive.** AST-walk `app.py` for every
     function registered with `response_class=HTMLResponse` (both the
     `@app.get` decorator form and the `add_api_route` loop form) and assert
     each body constructs an `HTMLResponse` with a `headers=` keyword whose
     dict contains a `cache-control` key. Assert `_SHELL_ROUTES` is non-empty
     and every one of its entries is registered. Zero HTML routes found is a
     FAILURE.

   Success report line, matching the corpus style:
   `PASS: static_asset_freshness — mount is policy-bearing, N immutable file(s) / M revalidating file(s), K HTML route(s) covered`

6. **`ARCHITECTURE_DECISIONS.md`** — append an entry recording the freshness
   contract: hashed assets immutable, everything else revalidating, DEFAULT
   posture is revalidate so new unhashed assets are covered by construction,
   and the partition is held by `static_asset_freshness.py` rather than by a
   hard-reload habit. Record the generalised lesson explicitly: **a check that
   proves an artifact is correct on disk does not prove it is the artifact the
   consumer received.** This is the third instance of that shape, after
   partition-vs-coverage (`stylesheet_partition` rule7) and
   dispatch-vs-listen (`graph_primitive` rule 11).

## Scope OUT

- **Hashing `shared.css` or `creation.css`.** L1 is locked: their stable names
  are load-bearing while `cockpit/index.html` exists, and that constraint
  expires on its own at TICKET-0061. Do not add a query string, a manifest
  lookup, or a hashed filename.
- **`src/world_engine/cockpit/index.html`.** Byte-untouched by doctrine
  (`app.py:222-226`); nine structural checks depend on it, including
  `relation_graph.py`'s byte-equality assertion. `serve_legacy` changes how the
  file is WRAPPED in a response; the file itself is not edited.
- **`frontend/vite.config.js`**, `publicDir`, `base`, or `emptyOutDir`. The
  build is correct; only delivery changes.
- **The stale `/vendor` comment at `app.py:73`.** Mini-RECON item 6 reports it;
  fixing it is TICKET-0061's doctrine pass.
- **Cache headers on the 151 API routes.** H2 was rejected precisely to keep
  them out of this blast radius. Nothing under `/api` changes.
- **`frontend_build_fresh.py`.** K1 is locked: this is a separate check, and
  merging the two guarantees is what made the original failure ambiguous. Do
  not extend it, do not reference it from the new check.
- **A dev-server proxy or a `Disable cache` documentation note.** The point of
  this ticket is to delete the need for the habit, not to document it better.
- **Any `no-store` directive.** `no-cache` means revalidate; `no-store` would
  discard the etag benefit and make every load a full transfer.

## Invariants to defend

- **Structural over disciplinary.** The whole ticket exists because
  "remember to hard-reload" is a convention. If any part of the implementation
  reintroduces a convention — a hash-shaped regex, a hardcoded list of two
  filenames, a comment asking future readers to keep something in sync — that
  part is wrong. The partition must be readable from a declared constant.
- **Vacuous-proof guards.** rule3's two "class is empty" failures are the heart
  of the check. Demonstrate each one firing, not just the aggregate.
- **Fail-closed.** Every rule fails on a missing file, a missing constant, or an
  unparseable AST. None may pass by finding nothing.
- **AST, never regex, for Python constants.** Same discipline as
  `legacy_mount.py:18-19` states explicitly. A regex over `app.py` would be the
  same class of mistake this ticket is fixing.
- **No canon-write, no schema, no mutation gating.** This step touches serving
  only.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python3 tooling/verify/checks/static_asset_freshness.py` returns PASS, report line showing non-zero counts in BOTH partition classes and a non-zero HTML route count
- [ ] It returns FAIL when the mount is temporarily reverted to bare `StaticFiles(` (demonstrate, revert)
- [ ] It returns FAIL when `_IMMUTABLE_ASSET_PREFIX` is temporarily set to a directory that does not exist (demonstrate, revert)
- [ ] It returns FAIL when the `headers=` kwarg is temporarily removed from `_serve_shell` (demonstrate, revert)
- [ ] It returns FAIL when `_STATIC_DIR` is temporarily pointed at a directory holding only `assets/` files, i.e. an empty revalidate class (demonstrate, revert)
- [ ] `frontend_build_fresh`, `legacy_mount`, `stylesheet_partition`, `shell_height_chain`, `graph_primitive`, `page_contract`, `creation_island` all return PASS
- [ ] `curl -sI http://127.0.0.1:8000/static/shared.css` shows `cache-control: no-cache`
- [ ] `curl -sI http://127.0.0.1:8000/static/assets/<hashed>.js` shows `cache-control: public, max-age=31536000, immutable`
- [ ] `curl -sI http://127.0.0.1:8000/` and `curl -sI http://127.0.0.1:8000/legacy` both show `cache-control: no-cache`
- [ ] Live: edit a visible rule in `frontend/public/creation.css`, `npm run build`, restart, **plain reload with no Ctrl+F5** — the change appears
- [ ] Live: DevTools > Network on an unchanged reload shows `shared.css` and `creation.css` as `304`, not `(disk cache)`
- [ ] Live: `assets/index-<hash>.js` still served from cache with no revalidation round trip
- [ ] Live: Play, Création and Observation all render unchanged
- [ ] `/review-step` and `/close-step` run (engine code touched: `app.py`)
- [ ] Mini-RECON item 6 report delivered (stale `/vendor` comment), no edit made

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — the freshness contract entry (Scope IN item 6).
- `static_asset_freshness.py`'s own module docstring carries the four numbered
  rules in the same voice as `shell_height_chain.py`. This step IS that doc.
- `CLAUDE.md` — verify whether any line documents a hard-reload dev convention
  this ticket makes obsolete. Amend only if such a line exists; report either way.
- No schema changelog entry: no schema change.
