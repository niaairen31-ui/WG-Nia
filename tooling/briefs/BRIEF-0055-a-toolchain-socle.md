# BRIEF — Step "Frontend toolchain socle"

## Context

First step of TICKET-0055, first ticket of the index-split chain. `index.html`
is 12708 lines, of which ~11081 are a single `<script>` holding 540 top-level
functions in one global scope; the domains are physically interleaved so no
range cut exists. Before any surface can move, a JS build and a place to put
its output must exist. This repo is greenfield on that axis: no `package.json`,
no `vite.config*`, no `.svelte` anywhere in the tree.

This step introduces the toolchain and NOTHING that the running app consumes.
Serving is BRIEF-0055-b; the gate is -c; doctrine is -d.

## Mini-RECON (report-only, run before writing any file)

Report results in the execution report. Do NOT act on findings beyond the
narrow conditional in Scope IN item 8.

- **MR-a1 (empirical, not asserted).** Determine the exact shell invocation
  that runs npm from Claude Code on this Windows box. Run, and report verbatim
  stdout/exit code for each: `node --version`, `npm --version`,
  `npm.cmd --version`. Report which form works. This is an empirical driver-
  behaviour question of the same class as the pysqlite atomicity finding in
  TICKET-0044 -- state the observed result, never a parenthetical assumption.
  If none of the three works, STOP and escalate before creating any file.
- **MR-a2.** Confirm the tree is still greenfield: report the output of
  `git ls-files | Select-String -Pattern "package.json|vite.config|\.svelte$"`
  (or the POSIX equivalent). Expected: empty.
- **MR-a3.** Report the current content of `.gitignore` and of
  `.claude/settings.json` verbatim, so the edits below are anchored to what is
  actually on the branch rather than to this brief's transcription.

## Scope IN

1. **Branch.** `ticket/0055`, off current `main`.

2. **Source root: `frontend/` at repository root.** Not under `src/`.
   Rationale to preserve: `pyproject.toml` declares
   `[tool.setuptools.packages.find] where = ["src"]`; the JS toolchain has no
   business inside the Python package tree. Create:

   ```
   frontend/
     package.json
     package-lock.json          (produced by npm, committed)
     vite.config.js
     index.html                 (Vite entry HTML, NOT the cockpit's index.html)
     scripts/write-manifest.mjs
     src/
       main.js
       Beachhead.svelte
   ```

3. **`frontend/package.json. Exactly these fields; "private": true; no
dependencies beyond what is listed. Pin exact versions (no ^, no ~) --
a lockfile plus floating ranges is two truths about the dependency set. Resolve the three versions empirically, never from memory. Run and
report verbatim:
npm view vite version
npm view @sveltejs/vite-plugin-svelte version
npm view @sveltejs/vite-plugin-svelte peerDependencies
npm view svelte version
Then pin the resolved vite and svelte versions literally, and pin the
@sveltejs/vite-plugin-svelte version that its own peerDependencies
declare compatible with BOTH. If the latest plugin's peer range excludes
the latest vite or the latest svelte, STOP and escalate with the three
outputs — do not resolve a version conflict by judgment.
json
{
  "name": "world-engine-cockpit",
  "private": true,
  "type": "module",
  "version": "0.1.0",
  "engines": { "node": ">=24" },
  "scripts": {
    "build": "vite build && node scripts/write-manifest.mjs",
    "dev": "vite"
  },
  "devDependencies": {
    "vite": "<resolved above>",
    "svelte": "<resolved above>",
    "@sveltejs/vite-plugin-svelte": "<resolved above>"
  }
}
engines is DECLARATIVE here: npm does not enforce it without
engine-strict, and we deliberately do not enable it. ">=24" states the
major actually validated on this box (node --version -> v24.18.0), not
a compatibility claim for lower majors, which have not been tested. Do not
widen it to a lower floor. Do not add any other package.

4. **`frontend/vite.config.js`.** Build output goes into the Python package so
   `Path(__file__).parent` can reach it -- the same idiom `vendor/` already
   uses (`app.py:69`).

   ```js
   import { defineConfig } from 'vite';
   import { svelte } from '@sveltejs/vite-plugin-svelte';

   export default defineConfig({
     plugins: [svelte()],
     base: '/static/',
     build: {
       outDir: '../src/world_engine/cockpit/static',
       emptyOutDir: true,
       rollupOptions: {
         // TICKET-0055 D3: cytoscape stays vendored and is served by the
         // pre-existing GET /vendor/{filename} route. The bundler must never
         // own it. Which engine sits under the graph primitive is TICKET-0057.
         external: ['cytoscape'],
       },
     },
   });
   ```

5. **`frontend/index.html`** -- the Vite entry document. Minimal: a `<div id="app">`
   and `<script type="module" src="/src/main.js"></script>`. It must NOT
   reference `/vendor/cytoscape-3.34.0.min.js` (nothing in the beachhead needs
   a graph).

6. **`frontend/src/main.js` and `frontend/src/Beachhead.svelte`.** The
   beachhead must prove the framework is actually executing, not that a string
   was served: `Beachhead.svelte` renders a heading plus a counter with an
   increment button bound to reactive state. Keep it under 30 lines total. Its
   visible text must include the literal string `TICKET-0055 beachhead` so the
   live gate is unambiguous.

7. **`frontend/scripts/write-manifest.mjs`.** Emits
   `src/world_engine/cockpit/static/.build-manifest.json` after every build.
   The canonical hash algorithm is specified VERBATIM in BRIEF-0055-c and the
   Python check re-implements the same steps; copy that specification exactly,
   do not paraphrase it and do not invent a different digest shape. The file
   content is exactly:

   ```json
   { "source_hash": "<64 hex chars>", "built_at": "<ISO-8601 UTC>" }
   ```

8. **`.gitignore` additions.** Append, with the comment verbatim:

   ```
   # Frontend toolchain (TICKET-0055). node_modules never enters the tree.
   # The BUILD OUTPUT under src/world_engine/cockpit/static/ IS committed on
   # purpose (E1): building at launch would fail open -- a stale or absent
   # build renders a blank page instead of refusing.
   frontend/node_modules/
   ```

   Do not add any ignore rule for `src/world_engine/cockpit/static/`.
   **Conditional (narrow):** if MR-a3 reports that `.gitignore` already
   contains a `node_modules` rule, skip this addition entirely and report it;
   do not restructure the file.

9. **`.claude/settings.json` -- exactly two new `permissions.allow` entries**,
   appended at the end of the existing list, preserving the existing thirteen
   verbatim and their order:

   ```
   "Bash(npm ci:*)",
   "Bash(npm run build:*)"
   ```

   If MR-a1 established that the working invocation is `npm.cmd`, add the
   `npm.cmd` forms **instead of** the `npm` forms (still exactly two entries),
   and say so in the report. No `npm install`, no `npx`, no generic
   `Bash(node:*)`.

10. **Run `npm install` once locally to produce `package-lock.json`, then
    commit the lockfile**, then verify `npm ci` reproduces `node_modules/` from
    it. The lockfile is committed; `node_modules/` is not.

11. **Run `npm run build`.** Commit the resulting
    `src/world_engine/cockpit/static/` tree in full, including
    `.build-manifest.json`.

## Scope OUT

- **No change to `src/world_engine/cockpit/index.html`. Not one byte.**
  `relation_graph.py:192-206` compares twelve Lieux-graph functions against
  `main` via `git show`; nine checks grep this file. Touching it is an
  escalation, never a convenience.
- **No change to `app.py`.** The static mount and the `/shell` route are
  BRIEF-0055-b. This step's output is inert: built, committed, served by
  nothing.
- **No new verify check here.** `frontend_build_fresh.py` is BRIEF-0055-c.
- **No doctrine edit here.** `CLAUDE.md`, `ARCHITECTURE_DECISIONS.md`,
  `DECISIONS_INDEX.md` and `docs/launch-procedure.md` are BRIEF-0055-d.
- **No migration of any existing surface.** No Play, no Creation, no
  Observation, no graph code. Those are 0057..0060.
- **No SPA router, no shell, no legacy-mount component.** A1 is the TARGET;
  the shell and the legacy-mount registry are TICKET-0056's first decision.
  Building any part of it here pre-empts a decision that has not been made.
- **No cytoscape npm package.** D3: it stays vendored.
- **No dependency beyond vite / svelte / the svelte vite plugin.** No Tailwind,
  no linter, no test runner, no TypeScript, no `svelte-check`. Each is a
  separate decision under `CLAUDE.md:17-18`.
- **No CI workflow file.**

## Invariants to defend

- **`CLAUDE.md:17-18` -- "No build step, no new dependencies without a
  decision."** This step deliberately reverses the first half under an explicit
  locked decision, and defends the second half structurally via the F3
  permission scope (item 9): after this brief, Claude Code can build but cannot
  add a package.
- **`CLAUDE.md:58` -- "`index.html` remains a single file with no build step;
  splitting it is a doctrine change, not a refactor."** Still literally true at
  the end of this step: `index.html` is untouched and nothing splits. The
  doctrine text is amended in -d, after the fact it describes has changed.
- **The vendored-asset boundary (`app.py:66-70`).** The comment there defers a
  `StaticFiles` mount "until a second vendored asset". A build output is not a
  vendored asset; -b resolves this explicitly rather than by analogy.

## Done means

- [ ] MR-a1/a2/a3 results are in the execution report, with verbatim command
      output for MR-a1.
- [ ] `frontend/` exists with exactly the files listed in item 2.
- [ ] `frontend/package.json` pins three exact devDependency versions, no
      ranges; the resolved versions are named in the report.
- [ ] `frontend/package-lock.json` is committed; `frontend/node_modules/` is
      not tracked (`git ls-files frontend/node_modules` returns nothing).
- [ ] `npm ci` from a deleted `node_modules/` succeeds.
- [ ] `npm run build` succeeds and produces
      `src/world_engine/cockpit/static/` containing at least one `.js` asset,
      an `index.html`, and `.build-manifest.json` with a 64-hex `source_hash`.
- [ ] That whole output tree is committed.
- [ ] `.claude/settings.json` has exactly 15 `permissions.allow` entries, the
      original 13 unchanged and in order, plus the two from item 9.
- [ ] `git diff main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] `git diff main -- src/world_engine/cockpit/app.py` is EMPTY.
- [ ] `python tooling/verify/run.py --ticket TICKET-0055` is not run at this
      step (the ticket's checks do not all exist yet); instead run every
      pre-existing index-anchored check directly and report each verdict:
      `page_contract.py`, `relation_graph.py`, `review_component.py`,
      `observation_surface.py`, `creation_return_nav.py`, `event_tab.py`,
      `faction_roster_panel.py`, `review_root_fallback.py`, `schema_0024.py`.
      All nine must pass.
- [ ] `python scripts/cockpit.py` still starts and `http://127.0.0.1:8000/`
      is unchanged.
- [ ] ` The four npm view outputs are in the report verbatim, and the three
pinned versions are mutually compatible per the plugin's declared
peerDependencies.

## Docs to update

None. This step is deliberately doc-silent: the doctrine amendment is
BRIEF-0055-d, so that `CLAUDE.md` never describes a state the tree has not
reached and never lags one it has.
