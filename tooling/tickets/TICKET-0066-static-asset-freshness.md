---
id: TICKET-0066
title: Unhashed static assets are served with no freshness directive
type: bug
status: live-gate
created: 2026-08-19
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0066-a]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> 1- j'ai fait ctrl+F5 sur le site et mes colonnes se sont divisé et sont revenu
> normal. toujours pas de graph et on ne peut pas scrolé. est-ce que je dois
> faire les autres M ? explique moi ce qui c'est passé et pourquoi cela a
> marché. Dans quel circonstances je dois faire ctrl+F5.

Split out of TICKET-0065 (finding F3) by locked decision G1.

## Clarifications resolved (intake)

**The defect.** The cockpit serves two classes of frontend asset with unequal
freshness guarantees:

| Asset | Filename | Cache-busting |
|---|---|---|
| `static/assets/index-<hash>.js`, `index-<hash>.css` | content-hashed | by construction |
| `static/shared.css`, `static/creation.css` | **stable** | **none** |
| `static/index.html` (the shell document) | stable | none |

The two stylesheets keep stable names deliberately: they live in Vite's
`publicDir` and are copied unhashed (`frontend/vite.config.js`, `base: '/static/'`)
precisely so `src/world_engine/cockpit/index.html:6` can `<link>` one of them by
fixed path — a legacy document cannot link a content-hashed asset.

`app.py:91` mounts the directory with bare
`app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")`.
Starlette's `StaticFiles` emits `etag` and `last-modified` but sets no
`Cache-Control`. With no explicit freshness directive a browser applies
HEURISTIC freshness and reuses the cached copy **without issuing a request at
all** — no round trip, no 304, nothing in the Network panel.

`_serve_shell` (`app.py:247-248`) returns the shell document as a plain string
under `response_class=HTMLResponse`, with no cache headers either. That is the
more dangerous half: a cached `static/index.html` references a hashed bundle
filename that `emptyOutDir: true` has already deleted from disk, so the failure
mode is a 404 on the bundle and a blank page, not a stale render.

**The confirmed consequence.** TICKET-0063/0064 moved rules out of
`cockpit/index.html`'s inline `<style>` into `shared.css` and `creation.css`.
Browsers took the new bundle (hashed name forces a fetch) and kept the old
stylesheets. A post-TICKET-0059 bundle rendered its DOM against pre-0063
stylesheets: `.creation-sub-tab-bar`, `.row-card`, `.btn-ghost`, `.btn-icon`
and `.author-list-item` resolved (already present in the cached copies) while
`.layout`, `.sidebar`, `.right-col`, `.panel-head`, `.conv-list` and
`.btn-send` did not. The Creation surface presented as a layout defect and
consumed a full RECON session before the delivery layer was identified.

Falsification record, worth keeping so this is never re-litigated: a
`npm run build` plus a prod-server restart changed nothing — the browser was
asking the server nothing. A single `Ctrl+F5`, which adds `Cache-Control:
no-cache` to the document request and its subresources, restored correct
rendering immediately and permanently. Stale-server, stale-build and
stale-checkout hypotheses are all ruled out by that pair of observations.

**Why this is structural, not a usage note.** "Remember to hard-reload after
touching `frontend/public/`" is a disciplinary guarantee. It failed once, in the
most expensive possible way — as a symptom indistinguishable from a CSS
regression. `frontend_build_fresh.py` proves the artifact on disk is fresh; it
does not and cannot prove what the browser loaded. Same "proves X, not Y" shape
as partition-vs-coverage (closed by `stylesheet_partition.py` rule7) and
dispatch-vs-listen (closed by `graph_primitive.py` rule 11, TICKET-0065). This
is the third instance.

**Locked decisions (G1, H1, I1, J4, K1, L1).**

- **G1** — separate ticket rather than a BRIEF-0065-c, because the fix lives in
  `app.py` and TICKET-0065 declares frontend-only scope (workstream map PART C
  rule 2). Independent of the 0060/0061 chain; lands in any order.
- **H1** — a `StaticFiles` subclass whose DEFAULT posture is `no-cache`, with
  `public, max-age=31536000, immutable` as the opt-in exception for one declared
  prefix. Default-revalidate matters: an asset dropped into `frontend/public/`
  tomorrow is covered without anyone thinking about it. Rejected H2 (middleware
  runs on all 151 API routes for zero benefit) and H3 (per-file routes — already
  decided against at `app.py:69-74`: "a build output is a whole asset FAMILY
  with content-hashed names, which a per-file whitelist cannot express without
  ceasing to be a whitelist").
- **I1** — the shell HTML routes carry the directive too, on the blank-page
  failure mode above.
- **J4** — the check asserts an EXHAUSTIVE PARTITION of `_STATIC_DIR` against a
  policy constant read from `app.py` by AST, not an enumeration of `<link>`
  references. Measured basis: the reference surface is only 7 URLs across three
  documents, five of which reduce to two filenames — but enumerating them would
  make "is this filename hashed?" a REGEX CONVENTION, the one place a
  reference-based check rots. Under J4 "hashed" is not inferred, it is declared
  by H1 and read structurally. J4 is also stronger (covers files not yet
  referenced) and needs no edit when `cockpit/index.html` retires at
  TICKET-0061. Rejected J1 (regex hash detection), J2 (whitelist that rots,
  the A7 pattern), J3 (proves the directive exists, not that it covers
  anything — the exact gap this ticket closes).
- **K1** — its own check file. `frontend_build_fresh` proves disk-against-source;
  this proves delivery-against-policy. Merging them would make the report line
  ambiguous about which guarantee lapsed, and their conflation is what masked
  the bug.
- **L1** — the two stylesheets keep their stable names. The constraint forcing
  them (`cockpit/index.html` cannot link a hashed asset) expires on its own at
  TICKET-0061, and L2 would require touching a document that is byte-untouched
  by doctrine (`app.py:222-226`; nine structural checks depend on it, including
  `relation_graph.py`'s byte-equality assertion).

**RECON anchors (main, post-TICKET-0065).** `_STATIC_DIR` = `app.py:75`; mount
= `app.py:91`; boot guard = `app.py:201-215`; `serve_legacy` = `app.py:218-226`;
`_SHELL_ROUTES` = `app.py:244`; `_serve_shell` = `app.py:247-248`; registration
loop = `app.py:251-253`. `_STATIC_DIR` currently holds six files:
`.build-manifest.json`, `assets/index-CBFgNMnZ.js`, `assets/index-DZVnARB4.css`,
`creation.css`, `index.html`, `shared.css` — so both partition classes are
non-empty today, which the check requires.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The `/static` mount uses the subclass, not bare `StaticFiles`  -> verify/checks/static_asset_freshness.py
- [ ] The immutable prefix is a module-level constant in `app.py`, readable by AST, naming a directory that exists under `_STATIC_DIR`  -> verify/checks/static_asset_freshness.py
- [ ] Every file under `_STATIC_DIR` is classified by the declared partition, and BOTH classes are non-empty  -> verify/checks/static_asset_freshness.py
- [ ] Every HTML-serving route returns a response carrying a `cache-control` header containing `no-cache`  -> verify/checks/static_asset_freshness.py
- [ ] The check is vacuous-proof: zero files walked, zero HTML routes found, or either partition class empty is a FAILURE  -> verify/checks/static_asset_freshness.py
- [ ] The check FAILS when the directive is temporarily removed from the subclass, and when the mount is temporarily reverted to bare `StaticFiles`  -> demonstrated, reverted
- [ ] `frontend_build_fresh`, `legacy_mount`, `stylesheet_partition`, `shell_height_chain`, `graph_primitive` all still PASS  -> existing checks

### Live  ->  human gate (Nia)

- [ ] Edit a visible rule in `frontend/public/creation.css`, `npm run build`, restart the server, **plain reload (NO Ctrl+F5)** — the change is visible
- [ ] DevTools > Network on an unchanged reload: `shared.css` and `creation.css` show `304`, not `(disk cache)`
- [ ] DevTools > Network: `assets/index-<hash>.js` still served from cache with no revalidation round trip
- [ ] Any `frontend/src/` edit + rebuild is picked up on a plain reload, with no blank page
- [ ] Play, Création and Observation all render unchanged after the header change

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: the freshness contract — hashed assets are
  immutable, everything else revalidates, default posture is revalidate, and
  the boundary is held by a check rather than by remembering to hard-reload.
- `CLAUDE.md`: only if it documents a dev-loop hard-reload convention this
  ticket makes obsolete. Verify; amend only if such a line exists.
- No schema changelog entry: no schema change.
