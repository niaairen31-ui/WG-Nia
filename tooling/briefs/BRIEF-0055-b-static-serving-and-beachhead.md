# BRIEF — Step "Static serving + beachhead route"

## Context

BRIEF-0055-a produced a committed build output under
`src/world_engine/cockpit/static/` that nothing serves. This step wires it,
and only it. `app.py:66-68` carries the standing deferral -- "one whitelisted
file per entry, no StaticFiles mount -- that generalization waits for a second
vendored asset". A build output is not a second vendored asset, so this step
resolves the deferral explicitly on its own grounds rather than by analogy.

C1 is locked: `GET /` keeps serving `index.html` verbatim. The beachhead is
proven at a NEW route, never by editing `index.html` -- leaving that file
byte-untouched is what keeps nine structural checks green with zero re-homing
during the whole of 0055.

## Mini-RECON (report-only)

- **MR-b1.** Confirm no verify check asserts anything about `app.py`'s route
  set, count, or the body of `serve_ui`. Grep every file under
  `tooling/verify/checks/` for `app.py`, `serve_ui`, `@app.get`, `StaticFiles`.
  Report each hit with `file:line`. Expected: only `relation_graph.py:93`
  (the `/vendor/{filename}` pattern). If ANY other check constrains `app.py`'s
  routes, STOP and escalate -- adding `/shell` would then be a check-re-homing
  question, which is out of this brief's scope.
- **MR-b2.** Report the installed `fastapi` and `starlette` versions, and
  confirm `from fastapi.staticfiles import StaticFiles` imports cleanly in the
  project venv. `StaticFiles` ships with Starlette; `requirements.txt` may not
  name it directly. Report whether any `requirements.txt` change is needed --
  do NOT make one without reporting first.
- **MR-b3.** Report `wc -l src/world_engine/cockpit/app.py` and the current
  function count, against R5 (module budget: 40 functions / 1000 lines).
  Expected: ~205 lines. Report the headroom.

## Scope IN

1. **`app.py` -- module docstring.** Extend the existing "App factory,
   static/vendor serving, ..." opening sentence's inventory with one line
   noting the built-frontend static mount and the transitional `/shell` route.
   Keep it factual and short; no rationale (that lives in
   `ARCHITECTURE_DECISIONS.md`, written in -d).

2. **`app.py` -- new module-level anchor**, placed immediately after the
   existing `_VENDOR_DIR` / `_VENDOR_WHITELIST` block (currently lines 66-70),
   with this comment verbatim:

   ```python
   # Built frontend assets (TICKET-0055, C1). The deferral recorded above --
   # "no StaticFiles mount until a second vendored asset" -- is resolved here
   # on different grounds: a build output is a whole asset FAMILY with
   # content-hashed names, which a per-file whitelist cannot express without
   # ceasing to be a whitelist. The vendor whitelist below is unchanged and
   # keeps its own single entry.
   _STATIC_DIR = Path(__file__).parent / "static"
   ```

3. **`app.py` -- mount the static directory**, after the router includes
   (currently ending at line 84):

   ```python
   app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
   ```

   with `from fastapi.staticfiles import StaticFiles` added to the existing
   FastAPI import group. Do **not** pass `html=True`: directory-index
   behaviour differs across Starlette versions and the beachhead must be a
   deterministic named route, not a directory-index side effect.

4. **`app.py` -- fail-closed startup guard.** Add a third `@app.on_event("startup")`
   handler, mirroring the shape of the two existing ones
   (`_check_schema_version_on_startup`, `_purge_closed_batches_on_startup`),
   named `_check_frontend_build_on_startup`, which raises `RuntimeError` when
   `_STATIC_DIR` does not exist or contains no `.js` file:

   ```python
   @app.on_event("startup")
   def _check_frontend_build_on_startup() -> None:
       """Fail-closed boot guard (TICKET-0055, E1): the frontend build output
       is committed, not built at launch, so its absence is corruption of the
       working tree -- refuse to serve rather than mount an empty directory
       and render a blank page."""
       if not _STATIC_DIR.is_dir() or not any(_STATIC_DIR.glob("**/*.js")):
           raise RuntimeError(
               f"no built frontend assets under {_STATIC_DIR} -- run "
               "`npm run build` in frontend/ (the output is committed; an "
               "empty tree means a bad checkout, not a missing build step)."
           )
   ```

   This is the point of E1: the failure mode is a refusal, never a blank page.

5. **`app.py` -- the beachhead route**, added after the existing
   `serve_vendor_file` handler:

   ```python
   @app.get("/shell", response_class=HTMLResponse)
   def serve_shell() -> str:
       """Transitional beachhead for the built frontend (TICKET-0055, C1).

       `GET /` keeps serving the legacy single-file cockpit verbatim for the
       whole of this ticket; this route is the seam TICKET-0056 renames to
       `/` once the shell owns the surfaces. It exists so the toolchain can
       be proven live without editing `index.html`, which nine structural
       checks and one cross-branch byte-equality assertion depend on.
       """
       return (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
   ```

6. **Nothing else in `app.py` changes.** `serve_ui`, `serve_vendor_file`,
   `_VENDOR_WHITELIST`, the two existing startup handlers, every router
   include: untouched.

## Scope OUT

- **No byte changes to `src/world_engine/cockpit/index.html`.** Not a script
  tag, not a link tag, not whitespace. If proving the beachhead seems to
  require touching it, the brief has been misread: that is exactly what
  `/shell` exists to avoid.
- **`GET /` does not change behaviour or implementation.** Not "temporarily",
  not behind a flag, not with a redirect. Flipping `/` is TICKET-0056.
- **No shell, no router, no layout, no navigation, no legacy-mount
  component.** A1 is the target; the shell and the monotonically-shrinking
  legacy-mount registry are TICKET-0056's first open decision. Building any
  part of them here pre-empts an unmade decision.
- **No change to the vendor route or whitelist.** Cytoscape stays vendored
  (D3); `relation_graph.py` assertion 1 must keep passing unmodified.
- **No dev-server proxy configuration.** `vite dev` against the FastAPI API is
  a real question and it belongs to whoever first needs hot reload while
  migrating a surface -- i.e. TICKET-0056. Do not add a `server.proxy` block.
- **No CORS.** The security note at `app.py:27-32` says no CORS is opened to
  any origin; same-origin `/static` needs none, and a dev proxy (which would)
  is out of scope above.
- **No new verify check.** That is BRIEF-0055-c.
- **No doc or doctrine edit.** That is BRIEF-0055-d.
- **No `requirements.txt` edit without reporting MR-b2 first.**

## Invariants to defend

- **`app.py:27-32` security block** -- loopback-only, no auth, no CORS, no
  external calls. The static mount serves a local directory over the existing
  loopback-bound server; it opens no origin and adds no external fetch. Do not
  weaken any of those four lines.
- **`CLAUDE.md:58`'s guarantee that `index.html` is a single untouched file.**
  Still literally true at the end of this step.
- **The `/vendor/{filename}` whitelist as a whitelist.** The new mount must not
  be reachable as an alternate path to `vendor/`: `_STATIC_DIR` and
  `_VENDOR_DIR` are siblings, and `StaticFiles` must be given `_STATIC_DIR`
  only. Confirm in the report that `GET /static/../vendor/cytoscape-3.34.0.min.js`
  does not resolve (Starlette normalizes and rejects traversal; state the
  observed status code rather than asserting the behaviour).
- **R5 module budget on `app.py`** -- report the post-change line and function
  count against 1000 / 40.

## Done means

- [ ] MR-b1, MR-b2, MR-b3 results are in the report, MR-b1 with `file:line`
      citations and MR-b2 with observed versions.
- [ ] `git diff main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] `python scripts/cockpit.py` starts cleanly.
- [ ] `http://127.0.0.1:8000/` renders the legacy cockpit unchanged: three top
      views, Creation sub-tabs, NPC relation graph, Lieux graph all behave as
      on `main`.
- [ ] `http://127.0.0.1:8000/shell` renders the beachhead: the literal string
      `TICKET-0055 beachhead` is visible AND the counter increments on click
      (proving Svelte reactivity is executing, not that a file was served).
- [ ] `GET /static/<hashed-asset>.js` returns 200 with a JavaScript content
      type; the exact filename tested is named in the report.
- [ ] `GET /vendor/cytoscape-3.34.0.min.js` still returns 200.
- [ ] `GET /vendor/anything-else.js` still returns 404.
- [ ] The traversal probe in "Invariants to defend" is run and its observed
      status code reported.
- [ ] Renaming `src/world_engine/cockpit/static/` aside makes
      `python scripts/cockpit.py` **refuse to start** with the item-4 message;
      restoring it makes it start again. (Red-test of the fail-closed guard,
      run live, directory restored afterwards.)
- [ ] All nine pre-existing index-anchored checks pass (same list as
      BRIEF-0055-a's Done means), each verdict reported.

## Docs to update

None in this step -- BRIEF-0055-d carries the whole doc and doctrine change,
including the `docs/launch-procedure.md` note and the `CLAUDE.md` file-tree
entry for `static/`.
