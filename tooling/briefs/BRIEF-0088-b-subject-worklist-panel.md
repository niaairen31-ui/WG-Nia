# BRIEF 0088-B — "Subject worklist panel"

Lot: LOT-0088-greenfield-creation-island.md (authoritative on conflict)
Depends on: BRIEF-0088-a (strictly — its parser is the first to accept
`origin`, and its rules 12 and 13 check two of this brief's edits)

## Anchors to confirm (Mini-RECON)

Re-verify each before the first edit. **If any has moved, STOP and report.**

1. **Brief a has landed.** `python tooling/verify/checks/creation_island.py`
   exits 0 and its last line contains `15 island(s) registered (15
   migration, 0 new)` and `Creation.svelte mounts no component`.
2. `frontend/src/creation/registry.js` -> the `queueBatchBar` entry is the
   last one, closing with `}),` immediately before the file's final `});`.
3. `frontend/src/creation/tabs.js:50-53` -> the header sentence containing
   `(14 static entries`; `:328` -> `queue: {` with `label: 'Review Queue'`
   at `:329`; `:318-327` -> the `evenements` entry; `:345-353` -> the
   `prompts` entry, the bespoke shape this brief copies.
4. `frontend/src/creation/Creation.svelte:249` -> the comment
   `  <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->`,
   with `creation-registre` at `:247` and `creation-queue` at `:250`.
5. `frontend/src/creation/mount.js:44` -> `import QueueBatchBar from './QueueBatchBar.svelte';`,
   and `:46` -> the single-line `const COMPONENTS = { … queueBatchBar: QueueBatchBar };`.
6. `tooling/verify/checks/page_contract.py:46-49` -> `TAB_KEYS` with the 14
   static keys, `evenements` immediately before `queue`; `:373-389` -> the
   `migrated_count` / `legacy_count` counters and the PASS tail ending
   "still render entirely from legacy code".
7. `src/world_engine/cockpit/crud/knowledge.py:144-165` -> the residue
   route, returning `subject`, `fact_ids`, `row_count` and a nested
   `resolution` object; `:243-258` -> the attach route.
8. `frontend/src/creation/sheetRequest.svelte.js:30-35` -> `export async function api(path, options)`.
9. `frontend/src/lib/serverState.svelte.js` -> `serverState.worldId`.
10. `python tooling/verify/checks/page_contract.py` prints, today,
    `14 of 14 CREATION_TABS entries have migrated at least one mount point, 0 still render entirely from legacy code`.

## Facts carried

### R-01 — the base, and P-1

Opened: `git ls-remote`, and a blobless clone of
`github.com/niaairen31-ui/WG-Nia` (`git log`, `git rev-parse`). [M]

Finding: `origin/main` is `994c9b2` ("Merge pull request #113 from
niaairen31-ui/ticket/0087", 2026-09-15). `ced51c1` (`ticket/0087`,
`refs/pull/113/head`) is its second parent, so
`git merge-base --is-ancestor ced51c1 HEAD` exits 0. `main`'s tree object
and `ced51c1`'s tree object are the same hash, `751ff36` -- the merge
introduced no other change.

Consequence: every line number below, measured on `main`, is also valid on
`ced51c1`; the decision session's anchors carry over unchanged. P-1 is
satisfied today in its ancestor form. Both briefs still check it before
their first edit: the working tree is Nia's, not this one.
### R-03 — `registry.js`: the literal, and the header that describes it

Opened: `frontend/src/creation/registry.js` (511 lines, LF in the repo). [M]

Finding:
- `:1-9` is the intro paragraph, and `:6-9` reads that this registry GROWS,
  "one entry per surface a brief converges ... It is the record of what has
  moved, not of what remains."
- `:11-17` is the BRIEF-0058-e amendment paragraph; `:18` is blank;
  `:19-27` is a field block, opening at `:19` with
  "tooling/verify/checks/creation_island.py cross-references every field
  against index.html and the real filesystem", calling `containerId` a
  "legacy element id the component mounts into", and closing with `*/` at
  the end of `:27`. The whole header is one `/* ... */` comment opened at
  `:1`.
- `export const CREATION_ISLANDS = Object.freeze({` is at `:28`; the file's
  last line, `:511`, is `});`.
- The 15 `migratedBy:` lines are at `:32, 38, 65, 277, 290, 303, 350, 359,
  378, 393, 416, 455, 471, 487, 505`, each indented by four spaces.
- Trailing commas occur after the last field of every entry, after the last
  item of every multi-line prefix list, and after the last entry (`:510`).

Consequence: the A.1 replacement text replaces `:19-27` only; `:1-18` stays.
Any grammar this lot specifies must accept trailing commas in all three
positions, or it fails all 15 entries.
### R-12 — `mount.js`: the sixth registration site, unchecked

Opened: `frontend/src/creation/mount.js` (163 lines). [M][E]

Finding:
- `:26` `import { mount as svelteMount, unmount as svelteUnmount } from 'svelte';`
- `:27-29` import `./registry.js`, `./state.svelte.js`, `./queue.svelte.js`
  -- specs ending in `.svelte.js`, not `.svelte`.
- `:30-44` are 15 single default imports, each spec `'./<Component>.svelte'`.
- `:46` is one line: `const COMPONENTS = { constructeur: Constructeur, ... , queueBatchBar: QueueBatchBar };`.
  Its key set equals the 15 registry keys; its key *order* differs
  (`linkAgent` sits seventh here, eleventh in the registry), and every value
  is the default import of `'./' + entry.component` (prototype, [E]).
- `escapeHtml` (`:50-54`) holds the regex literal `/[&<>"']/g` at `:51`. The
  file holds 24 backticks in template literals, none nested inside a `${}`.
- `mountIsland` (`:68-96`) throws on a key missing from either table
  (`:71-73`) and calls
  `svelteMount(Component, { target: node, props: { legacyDoc: node.ownerDocument } })`
  at `:91`; `graph_primitive.py:339,774` requires that exact text to remain.
- `activateIsland` (`:119-127`) catches the throw and only runs
  `console.error` (`:125`).

Consequence: a registry key whose `COMPONENTS` line is forgotten passes
every check on `main` and renders an empty tab with one console line. Rule 12
(C-03) closes it, and its comparison is on key *sets*, never on order. Any
comment stripper this lot specifies must understand regex literals, or it
breaks on `:51`.
### R-14 — `Creation.svelte`: what it is, and the bypass it allows

Opened: `frontend/src/creation/Creation.svelte` (256 lines), and a
throwaway prototype of rule 13's scan over it. [M][E]

Finding:
- One `<script>` block (`:1`), four static imports (`:26`, `:27`, `:28-33`
  from `./tabs.js` -- a multi-line clause -- and `:34`
  `{ triggerPrimaryAction, activateIsland } from './mount.js'`), no
  `.svelte` spec, no dynamic `import(`, and the only `svelte` import clause
  is `{ onMount }`.
- Markup, after HTML comments are removed: 61 tags, all lowercase HTML
  (`div` 38, `button` 10, `span` 8, `h2` 3, `aside` 1, `strong` 1); no
  uppercase tag, no dotted tag, no `svelte:component`, no `svelte:self`.
- Prose comments name `.svelte` files at `:3` and `:17`, and HTML comments
  do at `:124`, `:146`, `:150` -- a scan that does not strip comments first
  reports them.
- Containers run `:233-254`: `creation-registre` at `:247`, the comment
  `<!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->`
  at `:249`, `creation-queue` at `:250`, `creation-prompts` at `:254`;
  `</div><!-- #creation-view -->` closes at `:256`. Each container is
  `<div id="creation-x" style:display={containerVisible('creation-x') ? '' : 'none'}></div>`.
- The component is always mounted (`App.svelte:56`), and `App.svelte`
  imports and renders `WorldCrud` (`:8`, `:60`), which lives under
  `creation/` with no registry entry -- the shell-level path, outside the
  tab dispatcher.
- A `CREATION_TABS` entry with no `islands`, rendered by a component
  `Creation.svelte` imports directly, passes `creation_island`,
  `page_contract` and `creation_tab_switch` today [C].

Consequence: rule 13 (C-04) is satisfiable on the file as it stands, and it
is what makes the CLAUDE.md invariant structural instead of conventional.
The rule scans `Creation.svelte` only; `App.svelte`'s shell-level path is
untouched.
### R-15 — `tabs.js`: where a static tab is declared, and what it costs

Opened: `frontend/src/creation/tabs.js` (787 lines). [M]

Finding:
- `:50-53` is a header sentence reading "every `onWorldSwitch` in
  CREATION_TABS (14 static entries + the runtime-tab factory's own
  template) is `null` (measured, not assumed ...".
- `export const CREATION_TABS = {` is at `:188`; the literal closes with
  `};` at `:354`. Insertion order: `npc :189, pj :207, lieux :220,
  factions :235, objets :248, competences :260, region :269,
  constructeur :278, artefacts :287, registre :297, intrigues :306,
  evenements :318, queue :328, prompts :345`.
- `queue` declares `label: 'Review Queue'` at `:329`; `prompts` spans
  `:345-353` and is the bespoke shape, verbatim at `:345-353`:
  `{ label: 'Prompts', archetype: 'bespoke', containers: ['creation-prompts'], loader: null, state: { onTabEnter: null, onWorldSwitch: null }, islands: [{ key: 'prompts', containerId: 'creation-prompts' }], primaryAction: null }`.
- 12 `primaryAction: {` sites: `:199, 217, 229, 244, 257, 267, 276, 285,
  304, 316, 326` (static) and `:549` (the runtime-tab factory's template).
  Three `primaryAction: null`: `:295` artefacts, `:334` queue, `:352`
  prompts.
- The runtime-tab factory (`:522`) touches no static entry.
- The tab bar is one `{#each}` over `Object.entries(CREATION_TABS)`
  (`Creation.svelte:49-53`, `:81`), so a new entry appears with no template
  edit, in insertion order. `containerVisible` (`:387-397`) shows an id
  listed in the active entry's `containers`. `showCreationSubTab` (`:448`)
  returns early on an unknown key (`:451`); `router.js:28-31` already maps
  `/creation/<x>`.

Consequence: a new static entry needs no route, no template and no
dispatcher change -- only the entry, a container, a registry entry and a
`COMPONENTS` line. The header's "14 static entries" becomes a false
statement the moment the entry lands, so brief B corrects it.
### R-16 — `page_contract.py` keeps a hand-written tab list

Opened: `tooling/verify/checks/page_contract.py` (395 lines). [M]

Finding: `TAB_KEYS` (`:46-49`) is a literal list of the 14 static keys. The
loop at `:173-186` requires each of them to exist in `CREATION_TABS` and to
declare `primaryAction`; the loops at `:186-205` forbid each key as a
literal inside `showCreationSubTab` and `_creationActivateTab`. The
counters at `:373-381` classify every `CREATION_TABS` entry by
`_has_nonempty_islands`, and the PASS tail (`:383-389`) reads
"{migrated_count} of {migrated_count + legacy_count} CREATION_TABS entries
have migrated at least one mount point, {legacy_count} still render entirely
from legacy code". On `main` it prints "14 of 14 ... 0 still render entirely
from legacy code" [E].

Consequence: a key absent from `TAB_KEYS` is not covered by the
dispatcher-literal rule at all, so brief B adds `subjects` there. The PASS
sentence would then call an `origin: 'new'` tab "migrated" -- decision `J1`
renames the counters and rewrites the tail.
### R-17 — the sibling checks a new Creation component must satisfy

Opened: each check's own module. [M]

| check | what its code forbids or requires |
|---|---|
| `creation_tab_switch.py` | `CustomEvent('creation:sheet-reset'` (`DISPATCH_RE`, `:72`) anywhere under `frontend/src` except `tabs.js`; the three retired `_*TabEnterReset` identifiers (`:73`) gone. |
| `legacy_mount.py` | `contentWindow` (`:65`), `legacy-frame` (`:66`), `src="/legacy"` (`:67`) and `\.src\s*=` (`SRC_ASSIGN_RE`, `:68`) under `frontend/src`. |
| `graph_primitive.py` | `cytoscape(` (`:313`) and `<svg` (`:314`) outside `frontend/src/graph/`; `mount.js` keeps `legacyDoc: node.ownerDocument` (`:339`, `:774`). |
| `modal_primitive.py` | scans `frontend/src/**/*.svelte` (`:64`): `modal-backdrop` and `modal-container` must not both appear in one file. |
| `location_tree.py` | scans `*.svelte` (`:111`) for a `{#snippet}` (`:44`) recursion shape around `linkagent-loc-node`. |
| `event_tab.py` | no `@router.delete("/api/events` (`:34`) and no `api(/api/events` DELETE call under `frontend/src/creation` (`:35`, `:53`). |
| `shell_height_chain.py` | `100vh` (`:36`) anywhere in the scanned frontend files (`:65`). |
| `legacy_call.py` | `legacyCall(`/`callLegacy(` reaching exports outside the recorded baseline (`:97-106`). |
| `effect_self_write.py` | scans `frontend/src/**/*.svelte` (`:150`): inside an `$effect`, a `$state` binding assigned there must not be read afterwards; called *local* functions are inlined one level. |
| `stylesheet_partition.py` rule 7 | every class or id a component applies needs a strict base rule in `shared.css`/`creation.css`/the bundle or its own `<style>`; the reachable set is built by `_reachable_names()` (`:163`), whose definition of a strict base rule is at `:158-163`. |
| `static_asset_freshness.py` | scans `src/world_engine/cockpit/static` (`:171`) for the cache policy of built assets. |

Consequence: the panel of brief B uses no `<svg`, no `cytoscape(`, no
`.src =`, no `contentWindow`, no `100vh`, no modal pair, no snippet
recursion, no `/api/events` call and no `creation:sheet-reset` dispatch; its
state module holds every `$state` write, and its `$effect` calls an
*imported* function, which `effect_self_write.py` does not inline. Each of
these is a gate the lot must merely pass -- gate (e) names the module.
### R-18 — the class vocabulary that is reachable

Opened: `stylesheet_partition.py::_reachable_names()`, executed against the
tree. [E]

Finding: the reachable set holds 111 classes and 14 ids. Every class the
panel applies is in it: `queue-panel`, `panel-head`, `queue-body`,
`row-card`, `row-card-actions`, `empty`, `empty-ok`, `spin`, `btn-icon`,
`btn-send`. `span-2` is **not** reachable.

Consequence: brief B's markup is limited to that vocabulary plus inline
`style="..."` attributes, and it declares no `<style>` block of its own.
### R-19 — the budgets, and what they do not cover

Opened: `tooling/verify/checks/module_budget.py`,
`tooling/verify/checks/function_length.py`. [M]

Finding: `module_budget.py` enforces 40 top-level functions and 1 000 lines
on `src/**/*.py` (`SRC`, `:49`), 1 000 lines on
`frontend/src/**/*.{svelte,js}` with no exemption mechanism, and the legacy
ratchet (R-02). `function_length.py` enforces 80 physical lines per function
over `src/` only (`SRC.rglob("*.py")`, `:115`).

Consequence: `tooling/verify/checks/*.py` is outside both -- brief A's
growth of `creation_island.py` is bounded by nothing mechanical, so the
brief states the split it wants rather than relying on a check. The files
brief B touches are far from 1 000 lines (`registry.js` 511, `tabs.js` 787,
`mount.js` 163, `Creation.svelte` 256, and two new files under 120).
### R-21 — `sheetRequest.svelte.js`: `api` is the reusable half

Opened: `frontend/src/creation/sheetRequest.svelte.js` (53 lines). [M]

Finding: `api(path, options)` (`:30-35`) parses the JSON body, falls back to
`{ detail: res.statusText }` on a non-JSON body, and throws
`new Error(data.detail || JSON.stringify(data))` when the response is not
ok. `sheetRequest(legacyDoc, path, method, body, reload)` (`:37-53`) writes
its status into the element `author-status`, which lives inside
`#creation-editor-area` in `Creation.svelte` and is hidden on a tab that
does not declare that container. `api` is already imported outside the sheet
(`frontend/src/lore/lore.svelte.js:11`).

Consequence: the panel imports `api` and keeps its own status in its own
state; `sheetRequest` would report into an element its tab never shows.
### R-22 — the world-scoped panel precedent

Opened: `frontend/src/creation/Queue.svelte` (55 lines),
`frontend/src/creation/queue.svelte.js` (260 lines),
`frontend/src/lib/serverState.svelte.js`. [M]

Finding: `serverState.worldId` (`serverState.svelte.js:8`, set at `:28`
from the bootstrap payload) is the client's mirror of the server's active
world. `Queue.svelte` keeps its state and requests in `queue.svelte.js` and
holds one effect (`:22-28`):
`$effect(() => { void serverState.worldId; void queueState.reloadToken; loadQueue(); })`.
Its markup opens `queue-panel` (`:30`) > `panel-head` (`:31`) > `h2`
(`:32`) plus `<button class="btn-icon" onclick={loadQueue} title="Rafraîchir">↻</button>`
(`:33`).

Consequence: the same split -- state and requests in a sibling
`.svelte.js`, rendering in the component, a single `$effect` keyed on
`serverState.worldId` -- is what brief B's two files implement.
### R-23 — `KnowledgeEditor.svelte`, the binding precedent

Opened: `frontend/src/creation/KnowledgeEditor.svelte` (231 lines);
`grep -rn "/participants" frontend/src`. [M]

Finding: the picker is filled from `/api/entities` filtered to
`status === 'active'` (`:56-62`); a suggestion is taken from the residue
route when `r.resolution.verdict === 'matched'` (`:64-75`); a bind POSTs
`{ entity_id }` with no role to
`/api/facts/${encodeURIComponent(row.fact_id)}/participants` through
`sheetRequest` (`:82-92`), with no in-flight guard; the picker is rendered
only for a row with no participant (`:183-200`). `/participants` appears in
that file only (`:34`, `:87`, `:97`).

Consequence: one entity per row is the established shape, and the worklist
keeps it at subject grain. After brief B, a second file names
`/participants` -- which is the observable behind D-0087's reactivation
condition, written by the TICKET-0087 closing session on a tree where the
file exists.
### R-24 — the residue the panel renders

Opened: `src/world_engine/subject_resolve.py:71-107`,
`src/world_engine/cockpit/crud/knowledge.py:144-165`. [M]

Finding: `unresolved_subjects(world_id, db)` selects
`(Knowledge.subject, Knowledge.fact_id, FactParticipant.id)` joined to
`Entity` for the world scope and **outer-joined** to `FactParticipant`, then
skips in Python every row whose `participant_id is not None` (`:88-89`). It
groups the survivors by subject text, keeps the distinct `fact_ids` and a
`row_count`, resolves each subject once, and sorts by `row_count`
descending then `subject` ascending. The route
`GET /api/worlds/{world_id}/unresolved-subjects` 404s on an unknown world
and returns
`[{"subject", "fact_ids": [...], "row_count", "resolution": {"verdict", "entity_id", "candidate_ids": [...], "category"}}]`;
`verdict` is one of `matched`, `ambiguous`, `unmatched`.

Consequence: a fact that has *any* participant leaves the residue, so a
subject only partly bound stays listed carrying only its still-unbound
`fact_ids`. That is the property decision `E1`'s retry safety rests on.
### R-25 — the attach route, and what a duplicate costs

Opened: `src/world_engine/cockpit/crud/knowledge.py:243-258` and `:111-113`,
`src/world_engine/writes/facts.py:57-83`,
`src/world_engine/cockpit/crud/_shared.py:51-62`,
`src/world_engine/models/canon_knowledge.py:112-122`. [M]

Finding: `POST /api/facts/{fact_id}/participants` takes
`FactParticipantBody {entity_id: str, role: Optional[str] = None}`
(`:111-113`), 404s on an unknown fact, resolves the entity with
`_get_entity` (existence only, no world check), calls `attach_participants`,
which raises `ValueError` on a typed fact -- surfaced as 409 -- and
otherwise stamps `world_id=fact.world_id` and does a plain `db.add` with no
duplicate read; the route commits at `:257`. `FactParticipant` declares
`Index("idx_fact_participant_unique", "fact_id", "entity_id", unique=True)`
(`models/canon_knowledge.py:120`), so a duplicate pair raises
`IntegrityError` at commit, uncaught: HTTP 500. `IntegrityError` is imported
in the module and used nowhere.

Consequence: the panel must never send a second POST for a pair it already
bound. It cannot, by construction: it posts only `fact_ids` the residue
returned (facts with zero participants), one bind at a time, and reloads
before another bind is possible (`E1`). The 500 stays a named deferral of
TICKET-0087 (S-2), not a repair in this lot.
### R-26 — the entity list the picker uses

Opened: `src/world_engine/cockpit/crud/entities.py:503-512` and `:229-238`,
`crud/_shared.py:51-55`. [M]

Finding: `GET /api/entities` is scoped to the server's active world through
`_world_id(db)`, returns every type with no status filter, and each summary
carries `id, world_id, type, name, internal_name, status, is_public`.

Consequence: the panel filters on `status === 'active'` **and** on
`world_id === serverState.worldId`, so a cross-world entity can never reach
a POST from this surface (S-3 stays unreachable here).
### R-27 — a bind reaches the fact, not the row

Opened: `src/world_engine/cockpit/crud/knowledge.py:206-229`,
`src/world_engine/writes/knowledge.py:180-205`,
`frontend/src/creation/KnowledgeEditor.svelte:164`. [M]

Finding: a `knowledge` row's `fact_id` is set at creation -- auto-created
with `content = subject` when the caller passes none -- and
`write_knowledge` ignores `fact_id` on update, while
`PUT /api/knowledge/{id}` does update `subject`; the entity sheet exposes
`subject` as a free-text input (`KnowledgeEditor.svelte:164`). Several
`knowledge` rows share one fact by design (the fact spine is what makes
"who knows this" answerable).

Consequence: attaching a participant is an assertion about the *fact*, so it
also covers any other subject text sitting on that fact. This is the
existing reach of the entity sheet's own bind, not something this lot
introduces, and the data state it can produce is already named by
TICKET-0087's `J2` reactivation condition (a fact carrying a participant
that is not a subject of the knowledge attached to it). The lot adds no
guard and no new deferral; brief B's REPORT-ONLY records what the executor
observes.
### R-28 — the build the frontend edits require

Opened: `frontend/package.json`, `frontend/vite.config.js`, `.gitattributes`,
`tooling/verify/checks/frontend_build_fresh.py`. [M]

Finding: `npm run build` is `vite build && node scripts/write-manifest.mjs`
(`package.json:10`). `vite.config.js:8-9` sets
`outDir: '../src/world_engine/cockpit/static'` with `emptyOutDir: true`.
`frontend_build_fresh.py` hashes every file under `frontend/src` plus
`package.json`, `package-lock.json`, `vite.config.js`, `index.html`
(`ROOT_FILES`, `:38`) and compares with
`src/world_engine/cockpit/static/.build-manifest.json` (`:40`); line endings
are hashed as they exist on disk (`:85-89`). `.gitattributes` sets
`frontend/** text eol=lf` and `src/world_engine/cockpit/static/** -text`.

Consequence: every byte changed under `frontend/src` -- including brief A's
15 `origin:` lines -- requires `npm run build` and
`git add -A src/world_engine/cockpit/static` in the same commit, and
frontend files stay LF.
### R-29 — the decision record, and the index over it

Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md` (15 521 lines, CRLF in
the working tree [C]), `tooling/verify/checks/decisions_index.py`,
`tooling/glue/gen_decisions_index.py`. [M]

Finding: the CREATION SPINE entry opens at `:11128`; its
"**The island registry GROWS.**" paragraph is at `:11237`.
`D-0059-prompts-surface` is named at `:11506` ("Reactivate when a second
creator-tooling surface appears ..."). The most recent entry,
`## THE SUBJECT-BINDING SURFACE LIVES IN CREATION, NOT LORE (BRIEF-0087-d, no schema change)`,
opens at `:15501`. The file ends with `---`, a blank line and
`*Co-built with Claude, June 2026.*`. `decisions_index.py`'s
`STRICT_HEADER` (`:15-17`) is
`^## .+ \(BRIEF-\d{4}(-[a-z])?(, BRIEF-\d{4}(-[a-z])?)*, (schema v\d+\.\d+|no schema change)\)$`,
and `DECISIONS_INDEX.md` stores line numbers, regenerated by
`python tooling/glue/gen_decisions_index.py`.

Consequence: both ADR headers of this lot are written to that pattern, each
entry is appended immediately before the footer, the `:11237` sentence is
superseded on the record (quoted, never edited), and the index is
regenerated in the same commit.
### R-31 — the pipeline mechanics this lot must fit

Opened: `tooling/verify/run.py`, `tooling/verify/checks/pipeline_state.py`,
`.claude/commands/pipeline.md`, `.claude/commands/brief-exec.md`. [M]

Finding: `run.py`'s `machine_checks` (`:13-22`) reads between a
`### machine` heading and a `### live` heading and takes only the **first**
`-> verify/checks/X.py` on each line (`LINK`, `:10`); a check's recorded
message is the last line of its stdout (`:59-60`). `pipeline_state.py`
requires the 11 front-matter fields (`REQUIRED_FIELDS`, `:52-56`), a status
from the enum, exactly one `### Machine-checkable` heading and exactly one
`### Live` heading in that order (`:95-100`), and -- once the status is
`brief` or later -- at least one arrow resolving to a real file. Extra
front-matter fields are accepted (`TICKET-0085` carries `slug` and
`lot_id`). `/pipeline` Step 0 is the only writer of ticket front-matter and
reconciles `brief_ids` from the brief files on disk; `/brief-exec` step 1
creates or switches to `ticket/<NNNN>`.

Consequence: one arrow per Machine line, `corpus_gate.py` linked, and the
ticket's `brief_ids` written in the on-disk form (`BRIEF-0088-a`,
`BRIEF-0088-b`). A check may be linked by several lines; `creation_island.py`
runs in 0.09 s, so the repetition costs nothing.
### R-32 — the test database, and the script that must not be used

Opened: `src/world_engine/db.py:50-70`, `scripts/reset_test.py:1-40`,
`scripts/seed_pilot.py:31`, `scripts/init_db.py`, `scripts/cockpit.py`. [M]

Finding: `_resolve_database_url()` gives an explicit non-empty
`WORLD_ENGINE_DATABASE_URL` precedence over `WORLD_ENGINE_ENV`, and raises
`RuntimeError` at import when neither resolves. `reset_test.py` unlinks the
resolved database file (`:36`) before reseeding through `seed_test.main()`
-- whatever file the resolution points at. `seed_pilot.py` seeds
`WORLD_ID = "verkhaal"` (`:31`).

Consequence: brief B's behavioural test sets
`WORLD_ENGINE_DATABASE_URL` to a **new** file in the executor's own shell,
then runs `init_db.py`, `seed_pilot.py`, `cockpit.py`. `reset_test.py` is
named as forbidden in the brief, with the reason measured here.
### R-33 — production numbers

Carried from LOT-0087 R-06/R-07 (production, 2026-09-14), not re-measured:
243 unresolved subjects and 517 rows across the worlds holding knowledge;
Verkhaal 28 subjects. [C]

Consequence: Nia's live gate runs on production, where the list is not
empty. The executor never touches that database (R-32).

## Contracts

This brief consumes C-01, C-03, C-04, C-05 and C-06, all produced by
BRIEF-0088-a. It produces none.

### C-01 — the `CREATION_ISLANDS` entry family

Produced by: BRIEF-0088-a   Consumed by: BRIEF-0088-b

The registry literal is parsed from the **comment-stripped** text (C-02) of
`frontend/src/creation/registry.js`. Family contract first, then the two
members; no member adds a field the family does not list.

**Grammar (rule 1).** Exactly one match of
`export\s+const\s+CREATION_ISLANDS\s*=\s*Object\.freeze\(\s*\{` -- any other
count is a FAILURE. From that `{`, the matching `}` is found by brace
balance with string contents skipped; an unbalanced literal is a FAILURE.
The body is split into items at depth-0 commas (string contents skipped); a
whitespace-only item is allowed only in last position (trailing comma) and
is a FAILURE anywhere else. Each item must match
`<ident>\s*:\s*<value>`; the identifier is recorded as **declared** even
when the value is malformed, and an item with no such prefix is a FAILURE
naming the offending text. Each value must match
`Object\s*\.\s*freeze\s*\(\s*\{ <fields> \}\s*\)`; anything else is a
FAILURE naming the key. `<fields>` is split at depth-0 commas the same way,
each field matching `<ident>\s*:\s*<value>`, the value being either a
single-quoted string containing no backslash and no newline, or a `[ ... ]`
array of such strings; a repeated field name, a double-quoted string, an
identifier, a number and any other form are FAILURES naming the key and the
field. Whitespace, including newlines, is free between tokens. Trailing
commas are accepted after the last entry, the last field and the last array
item. Zero declared keys is a FAILURE.

**Field sets (rule 2), closed per origin.**

| field | `origin: 'migration'` | `origin: 'new'` |
|---|---|---|
| `containerId` | required, non-empty string | required, non-empty string |
| `component` | required, non-empty string | required, non-empty string |
| `origin` | required, exactly `'migration'` | required, exactly `'new'` |
| `migratedBy` | required, `^TICKET-\d{4}$` | **forbidden** |
| `retiredPrefixes` | required, non-empty array, every item matching `^[A-Za-z_$][A-Za-z0-9_$]*$` | **forbidden** |
| `createdBy` | **forbidden** | required, `^TICKET-\d{4}$` |
| any other name | FAILURE naming the key and the field | FAILURE naming the key and the field |

A missing `origin`, an `origin` outside the two values, a duplicate top-level
key, a missing field, a forbidden field and a malformed value are each a
FAILURE naming the entry key and the field (C-06). Rule 2 returns only the
conforming entries, in source order, as
`dict[key] -> {containerId, component, origin, migratedBy?, retiredPrefixes?, createdBy?}`
-- the same mapping shape rules 3, 4, 5, 9 and 11 consume today (R-05).

**Verbatim shape of each member**, as it appears in `registry.js`:

```js
  <key>: Object.freeze({
    containerId: '<element id in Creation.svelte>',
    component: '<File>.svelte',
    origin: 'migration',
    migratedBy: 'TICKET-NNNN',
    retiredPrefixes: ['<prefix>', ...],
  }),
  <key>: Object.freeze({
    containerId: '<element id in Creation.svelte>',
    component: '<File>.svelte',
    origin: 'new',
    createdBy: 'TICKET-NNNN',
  }),
```

Field order is free for the parser; both members are written in the order
above.
### C-03 — rule 12, `COMPONENTS` agreement

Produced by: BRIEF-0088-a   Consumed by: BRIEF-0088-b

`_rule12_component_bindings(mount_src, entries, fail) -> int`, run over the
comment-stripped `frontend/src/creation/mount.js` (C-02), where `entries` is
rule 2's mapping (C-01).

- An import statement is a line-initial `import` not followed by `(`, up to
  and including the first quoted module specifier that follows; its clause
  may span several lines.
- Every import whose specifier ends exactly in `.svelte` must be a single
  default import (one identifier between `import` and `from`); a named,
  namespace, mixed or side-effect form is a FAILURE naming the specifier.
- Exactly one `const COMPONENTS = { ... }`; any other count is a FAILURE.
  Its items are `<ident>: <Ident>` pairs, split at depth-0 commas, trailing
  comma accepted; any other item form, and any repeated key, is a FAILURE
  naming it.
- The `COMPONENTS` key **set** equals `entries`' key set -- order is not
  compared (R-12). Every missing key and every extra key is named.
- For each key, the value identifier must be the default import whose
  specifier is `'./' + entries[key]["component"]`; otherwise a FAILURE
  names the key, the identifier and the expected specifier.
- Every default `.svelte` import must be used by some `COMPONENTS` value; an
  unused one is a FAILURE naming it.
- An empty import set, or an empty `COMPONENTS`, is a FAILURE.

Return: the number of keys agreeing on all of the above. The verdict
requires it to equal `len(entries)` (C-05).
### C-04 — rule 13, `Creation.svelte` mounts no component

Produced by: BRIEF-0088-a   Consumed by: BRIEF-0088-b

`_rule13_creation_mounts_nothing(creation_src, fail) -> int | None`.

- HTML comments `<!-- ... -->` are removed first, their newlines kept; an
  unterminated one is a FAILURE.
- Every `<script ...>...</script>` block is comment-stripped with C-02; a
  `None` return propagates (`None`).
- In the stripped script text, each is a FAILURE naming the offending text:
  a dynamic `import(`; a static import whose specifier ends in `.svelte`; a
  static import from the specifier `svelte` whose named clause imports a
  binding called `mount` or `hydrate` (the name before `as`, so `onMount`
  is not one).
- In the markup -- the file with `<script>` and `<style>` blocks removed --
  a tag name (`<` immediately followed by a letter, then letters, digits,
  `:`, `.`, `_` or `-`) is a FAILURE when it starts with an uppercase
  letter, contains a `.`, or is `svelte:component` or `svelte:self`; the
  message names the tag.
- Vacuity: zero script blocks, zero imports across them, or zero tags is a
  FAILURE.

Return: the number of tags examined, or `None` when this call recorded a
failure.
### C-05 — the verdict and the PASS line

Produced by: BRIEF-0088-a   Consumed by: BRIEF-0088-b

PASS requires **all** of:
- no `FAILURES`;
- `len(entries) == len(declared)` (C-01);
- `component_ok`, `container_ok`, `bijection_ok`, `mechanism_ok`,
  `state_ok`, `dispatch_ok` (rules 3, 4, 5, 6, 9, 10, unchanged);
- `migration_count >= 1` and `retired_count == migration_count` (rule 7);
- `action_count == 8` (rule 8);
- `binding_count == len(entries)` (C-03);
- rule 13 returned non-`None` (C-04).

Any unmet condition records a failure message before reporting, so the PASS
path is never reached with absent counts (R-10).

The PASS line is the last line printed, exactly:

```
PASS: creation_island — {n} island(s) registered ({m} migration, {k} new), {r} retired legacy prefix set(s) confirmed gone, {b} component binding(s) agreed, {a} mount-action identifier(s) confined, {p} island primaryAction(s) wired, Creation.svelte mounts no component
```

with `n = len(entries)`, `m = migration_count`, `k = n - m`,
`r = retired_count`, `b = binding_count`, `a = action_count`,
`p` = rule 11's count. After brief A: `15 island(s) registered (15
migration, 0 new)`, `15 retired`, `15 component binding(s)`, `8`, `11`.
After brief B: `16 island(s) registered (15 migration, 1 new)`, `15
retired`, `16 component binding(s)`, `8`, `11`.
### C-06 — the refusal-message family

Produced by: BRIEF-0088-a   Consumed by: BRIEF-0088-a (self-test) and
BRIEF-0088-b (done-means)

Every FAILURE this lot adds names the thing refused, so an expectation can
be written as "at least one message naming X":
- a registry failure names the entry key, and the field when the fault is a
  field;
- a rule 7 failure names the entry key and the surviving function name;
- a rule 12 failure names the key, the identifier or the module specifier;
- a rule 13 failure names the offending specifier, clause or tag;
- a stripper failure names the label it was given;
- a verdict failure names the unmet condition.

No message is required to be unique: the self-test's expectations read "at
least one message naming X", never "exactly one message".

## Context

TICKET-0087 built the residue route and the per-row bind in the entity
sheet, and left the world-scoped worklist undone because no greenfield
Creation surface could register (AMENDMENT-0087-2, `K3`). Brief a has just
made `origin: 'new'` registrable. This brief lands the surface itself: one
bespoke tab listing the active world's unresolved subjects, with a one-press
bind per subject that loops over that subject's facts on the client
(decision `E1`). No route, no schema, no backend file.

## Scope IN

Three commits. The component and its state module are given verbatim; copy
them, do not paraphrase.

### Commit 0 — baseline, before any edit

1. Record `python tooling/verify/checks/corpus_gate.py` (expected
   `110 check(s) discovered, 110 executed, 110 passed`; if `day_mutations.py`
   CRASHes naming `WORLD_ENGINE_ENV`, set `$env:WORLD_ENGINE_ENV = "test"`
   and re-run, reporting which form was used), and confirm `git status` is
   clean.

### Commit 1 — the panel, one atomic commit

Rules 4, 5 and 12 cross-check these edits, so a partial commit is red by
construction.

2. **New file** `frontend/src/creation/subjectWorklist.svelte.js`, verbatim:

```js
/* TICKET-0088 (BRIEF-0088-b). State and requests for the subject worklist
   (SubjectWorklist.svelte), the first Creation island whose registry entry
   declares origin 'new'. Same split as queue.svelte.js / Queue.svelte:
   this module owns the state and every request, the component renders.

   Rows are GET /api/worlds/{world_id}/unresolved-subjects unchanged: one
   row per distinct knowledge.subject whose facts carry no fact_participant
   at all. Binding a subject is one POST /api/facts/{fact_id}/participants
   per fact, sequential, with no role (decision E1). Each POST is correct
   on its own; the first failure stops the loop; the reload that always
   follows leaves a partly bound subject listed with only its unbound
   facts, so a retry binds the remainder and never duplicates a
   participant. The route answers 500 on a duplicate (fact, entity) pair,
   which is why one bind at a time runs and every control stays disabled
   until the reload that follows it has landed.

   loadSubjects() is called from the component's $effect: before its first
   await it only WRITES subjectState, and the world it compares against is
   a plain module variable, so the effect depends on serverState.worldId
   alone. */
import { api } from './sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';

export const subjectState = $state({
  loading: false,
  loadError: '',
  rows: [],
  entities: [],
  selections: {},
  bindingSubject: null,
  bindErrors: {},
});

let loadedWorldId = null;
let loadSeq = 0;

export async function loadSubjects(worldId) {
  const seq = ++loadSeq;
  if (worldId !== loadedWorldId) {
    loadedWorldId = worldId;
    subjectState.rows = [];
    subjectState.entities = [];
    subjectState.selections = {};
    subjectState.bindErrors = {};
  }
  subjectState.loadError = '';
  if (!worldId) {
    subjectState.loading = false;
    return;
  }
  subjectState.loading = true;
  try {
    const [rows, entities] = await Promise.all([
      api(`/api/worlds/${encodeURIComponent(worldId)}/unresolved-subjects`),
      api('/api/entities'),
    ]);
    if (seq !== loadSeq) return;
    subjectState.rows = rows;
    subjectState.entities = entities.filter((e) => e.status === 'active' && e.world_id === worldId);
  } catch (e) {
    if (seq !== loadSeq) return;
    subjectState.rows = [];
    subjectState.entities = [];
    subjectState.loadError = e.message;
  } finally {
    if (seq === loadSeq) subjectState.loading = false;
  }
}

export function suggestedEntityId(row) {
  const r = row.resolution;
  if (!r || r.verdict !== 'matched') return '';
  return subjectState.entities.some((e) => e.id === r.entity_id) ? r.entity_id : '';
}

export function selectedEntityId(row) {
  const chosen = subjectState.selections[row.subject];
  return chosen !== undefined ? chosen : suggestedEntityId(row);
}

export function selectEntity(subject, entityId) {
  subjectState.selections = { ...subjectState.selections, [subject]: entityId };
}

export async function bindSubject(row) {
  const entityId = selectedEntityId(row);
  if (!entityId || subjectState.bindingSubject !== null) return;
  const worldId = loadedWorldId;
  const subject = row.subject;
  const factIds = Array.from(row.fact_ids);
  const errors = { ...subjectState.bindErrors };
  delete errors[subject];
  subjectState.bindErrors = errors;
  subjectState.bindingSubject = subject;
  let bound = 0;
  try {
    for (const factId of factIds) {
      if (serverState.worldId !== worldId) break;
      await api(`/api/facts/${encodeURIComponent(factId)}/participants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId }),
      });
      bound += 1;
    }
  } catch (e) {
    subjectState.bindErrors = {
      ...subjectState.bindErrors,
      [subject]: `${bound}/${factIds.length} fait(s) lié(s) avant l'échec : ${e.message}`,
    };
  } finally {
    if (serverState.worldId === worldId) await loadSubjects(worldId);
    subjectState.bindingSubject = null;
  }
}
```

3. **New file** `frontend/src/creation/SubjectWorklist.svelte`, verbatim:

```svelte
<script>
  /* TICKET-0088 (BRIEF-0088-b). The subject worklist: every knowledge
     subject of the active world that no fact_participant binds yet, with a
     one-action bind per subject. Its CREATION_ISLANDS entry declares
     origin 'new' -- a surface created as an island, with no legacy
     predecessor. State and requests live in subjectWorklist.svelte.js;
     the empty and error states below are part of what the list means. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    subjectState, loadSubjects, suggestedEntityId, selectedEntityId, selectEntity, bindSubject,
  } from './subjectWorklist.svelte.js';

  $effect(() => {
    loadSubjects(serverState.worldId);
  });

  let busy = $derived(subjectState.bindingSubject !== null);
  let lineTotal = $derived(subjectState.rows.reduce((n, r) => n + r.row_count, 0));

  function entityLabel(id) {
    const e = subjectState.entities.find((x) => x.id === id);
    return e ? `${e.name} (${e.type})` : '';
  }
</script>

<div class="queue-panel">
  <div class="panel-head">
    <h2>Sujets non résolus</h2>
    <span>{subjectState.rows.length} sujet(s) · {lineTotal} ligne(s)</span>
    <button class="btn-icon" disabled={busy} onclick={() => loadSubjects(serverState.worldId)} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if !serverState.worldId}
      <div class="empty">Aucun monde actif.</div>
    {:else if subjectState.loading && subjectState.rows.length === 0}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else if subjectState.loadError}
      <div class="empty" style="color:var(--red)">Erreur : {subjectState.loadError}</div>
    {:else if subjectState.rows.length === 0}
      <div class="empty-ok">✓ Aucun sujet non résolu dans ce monde.</div>
    {:else}
      {#each subjectState.rows as row (row.subject)}
        <div class="row-card">
          <div><strong>{row.subject}</strong></div>
          <div style="font-size:12px;">{row.row_count} ligne(s) · {row.fact_ids.length} fait(s)</div>
          <div style="font-size:12px;">
            {#if suggestedEntityId(row)}
              Suggestion : {entityLabel(suggestedEntityId(row))}
            {:else if row.resolution && row.resolution.verdict === 'ambiguous'}
              Ambigu : {row.resolution.candidate_ids.length} candidat(s)
            {:else}
              Aucune suggestion
            {/if}
          </div>
          <div class="row-card-actions">
            <select value={selectedEntityId(row)} disabled={busy}
                    onchange={(e) => selectEntity(row.subject, e.target.value)}>
              <option value="">—</option>
              {#each subjectState.entities as ent (ent.id)}
                <option value={ent.id}>{ent.name} ({ent.type})</option>
              {/each}
            </select>
            <button class="btn-send" disabled={busy || !selectedEntityId(row)} onclick={() => bindSubject(row)}>
              {subjectState.bindingSubject === row.subject ? 'Liaison…' : 'Lier'}
            </button>
          </div>
          {#if subjectState.bindErrors[row.subject]}
            <div style="color:var(--red); font-size:12px;">{subjectState.bindErrors[row.subject]}</div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>
```

4. **`registry.js`** — append this entry after the `queueBatchBar` entry and
   before the file's closing `});`, verbatim:

```js
  // TICKET-0088 (BRIEF-0088-b): the unresolved-subject worklist, the first
  // surface created directly as an island -- no legacy predecessor, so no
  // migratedBy and no retiredPrefixes.
  subjectWorklist: Object.freeze({
    containerId: 'creation-subjects',
    component: 'SubjectWorklist.svelte',
    origin: 'new',
    createdBy: 'TICKET-0088',
  }),
```

5. **`tabs.js`** — insert this entry immediately before `  queue: {`
   (`:328` today), verbatim:

```js
  subjects: {
    label: 'Sujets',
    archetype: 'bespoke',
    containers: ['creation-subjects'],
    loader: null,
    state: { onTabEnter: null, onWorldSwitch: null },
    islands: [{ key: 'subjectWorklist', containerId: 'creation-subjects' }],
    primaryAction: null, // binds existing knowledge subjects; creates no row
  },
```

6. **`tabs.js` header** — in the sentence at `:50-53`, `(14 static entries`
   becomes `(15 static entries`. Nothing else in that paragraph changes.
7. **`Creation.svelte`** — insert immediately before the Review Queue
   comment (`:249` today), verbatim, followed by one blank line:

```svelte
  <!-- ── Sujets sub-tab -- Svelte island created as one (origin 'new'):
       empty by construction ── -->
  <div id="creation-subjects" style:display={containerVisible('creation-subjects') ? '' : 'none'}></div>
```

8. **`mount.js`** — after `:44`, add
   `import SubjectWorklist from './SubjectWorklist.svelte';`; in the
   `COMPONENTS` line, `queueBatchBar: QueueBatchBar };` becomes
   `queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist };`.
9. **`page_contract.py`** — add `"subjects",` to `TAB_KEYS` between
   `"evenements",` and `"queue",`; rename `migrated_count` to
   `island_count` and `legacy_count` to `bare_count` at every occurrence
   (`:373-381`, `:387-388`); and rewrite the PASS tail so it reads:

    ```python
        f"{island_count} of {island_count + bare_count} CREATION_TABS "
        f"entries mount at least one island, {bare_count} "
        "mount none"
    ```

10. **Rebuild.** `npm run build` in `frontend/`, then
    `git add -A src/world_engine/cockpit/static`.
11. **Commit** the two new files, `registry.js`, `tabs.js`,
    `Creation.svelte`, `mount.js`, `page_contract.py` and
    `src/world_engine/cockpit/static/` together. Run `/review-step` and
    `/close-step`.

### Commit 2 — the record

12. **Append one ADR entry** to `tooling/standards/ARCHITECTURE_DECISIONS.md`,
    immediately before the closing `---` / footer block, with this header
    verbatim:

    ```
    ## THE SUBJECT WORKLIST IS A NEW CREATION ISLAND, BOUND BY A CLIENT LOOP (BRIEF-0088-b, no schema change)
    ```

    In the register of the entry at `ARCHITECTURE_DECISIONS.md:15501-15517`,
    it covers:
    - `B1`: its own bespoke tab, with `B2` (a second island inside an
      existing tab) rejected and its reactivation condition;
    - the judgment that **D-0059-prompts-surface has not fired**: the
      worklist curates canon, it does not configure the engine, so it is not
      the "second creator-tooling surface" that condition names;
    - `E1`: the sequential client loop, why it is safe (the residue excludes
      every fact carrying any participant, so a partial bind leaves the
      subject listed with only its unbound facts and a retry sends no
      duplicate pair), the single-bind lock held through the reload that
      follows, and the `status === 'active'` **and** `world_id` filter that
      keeps a cross-world entity unreachable from this surface;
    - `E2` (a bulk backend route) rejected, with its reactivation condition;
    - that this is the first `origin: 'new'` entry, and what that costs: the
      registry now records provenance for both kinds;
    - the named deferral **D-0088-one-entity-per-subject**, with its SQL
      reactivation condition verbatim from the lot.
13. **Regenerate the index**: `python tooling/glue/gen_decisions_index.py`.
14. **Commit.** `CLAUDE.md` does not change in this brief.

### After the commits — the behavioural test

15. Exercise the surface on a **new, throwaway** database file, never on
    production and never through `scripts/reset_test.py`, which unlinks
    whatever file the environment resolves to (R-32). Set the override
    explicitly in the shell, because a `WORLD_ENGINE_DATABASE_URL` coming
    from `.env` would otherwise win:

    ```powershell
    $env:WORLD_ENGINE_ENV = "test"
    $env:WORLD_ENGINE_DATABASE_URL = "sqlite:///C:/Users/<user>/.world_engine/test/worklist_check.db"   # a NEW file
    python scripts/init_db.py
    python scripts/seed_pilot.py
    python scripts/cockpit.py
    ```

    Then observe the six done-means marked *(browser)*. If this session has
    no browser, say so plainly in the report; those six move to Nia's live
    gate and the brief still closes.

## Scope OUT

- **Any backend change.** No route, no model, no write path, no schema
  artifact. The 500 on a duplicate participant pair and the attach route's
  missing world check are TICKET-0087's deferrals, not this brief's
  (R-25, R-26).
- **A bulk bind route.** `E2`, rejected.
- **Touching `KnowledgeEditor.svelte`**, including its missing in-flight
  guard on « Bind ». Observed, reported, unchanged.
- **`creation_island.py`.** Brief a owns it; this brief must not edit it to
  make its own entry pass.
- **`CLAUDE.md`.** Brief a made the only edits this ticket needs.
- **Promoting Prompts out of Creation** (D-0059-prompts-surface). Judged not
  fired; recorded in the ADR entry, not acted on.
- **Any `<style>` block, any class outside the ten of R-18, any id.**
- **Sorting, filtering, paging or searching the list.** The route's own
  order (`row_count` descending, then `subject`) is the order shown.
- **Unbinding from this panel.** The entity sheet owns unbind.
- **AMENDMENT-0087-3, TICKET-0087, LOT-0087, BRIEF-0087-e.** Another
  session's work (`H1`).

## Invariants to defend

- **"Every Création page is a `CREATION_TABS` registry entry rendered by the
  generic dispatcher"** (`CLAUDE.md:335-336`), and brief a's new bullet: the
  panel mounts through `CREATION_ISLANDS` and `mount.js` alone. The
  declarative bypass — a component `Creation.svelte` imports and renders —
  is exactly what rule 13 now refuses.
- **Model proposes, code judges.** The resolver's `matched` verdict only
  preselects a picker value; nothing is written until Nia presses « Lier ».
- **History is sacred / single canon-write path.** The bind uses the
  existing sanctioned route; no direct write, no delete, no new write path.
- **Fail-closed empty states.** `Queue.svelte`'s header calls its empty
  states "the surface's meaning, not decoration": this panel distinguishes
  no active world, loading, a load error, and a genuinely empty residue —
  never one silent blank.

## Decision rights

**STOP:**
- Any Mini-RECON anchor that has moved, including anchor 1: if
  `creation_island.py` does not report `(15 migration, 0 new)`, brief a has
  not landed and this brief does not start.
- A check refuses one of the verbatim texts above and the only way through
  would change a contract (C-01, C-03, C-04, C-05) — that is an amendment.
- The residue route or the attach route answers a shape other than the one
  recorded in R-24 and R-25.
- Any finding touching a `CLAUDE.md` invariant or a `danger_class` of this
  ticket, listed here or not.

**ADAPT (act as stated, then report):**
- A line number in an anchor has shifted while the content matches: anchor
  by content (the `queue: {` entry, the Review Queue comment, the
  `QueueBatchBar` import), proceed.
- `npm run build` exits 0 with warnings: proceed, quote them.
- This session has no browser: skip the six *(browser)* done-means, say so,
  and report the state of everything else.
- `corpus_gate.py` reports `CRASH` for `day_mutations.py` naming
  `WORLD_ENGINE_ENV`: set `$env:WORLD_ENGINE_ENV = "test"` and re-run.
- The seeded throwaway world shows no unresolved subject at all: report the
  counts observed and move the bind observations to Nia's live gate rather
  than seeding extra rows by hand.

**REPORT-ONLY:**
- The residue counts observed on the throwaway database.
- Whether any fact in a listed subject's `fact_ids` also carries another
  subject's rows (R-27) — observation only, no guard, no code change.
- `KnowledgeEditor.svelte`'s missing in-flight guard.
- Anything else found in the files opened here.

**Default clause:**

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/creation_island.py` exits 0 and its last
      line is exactly:
      `PASS: creation_island — 16 island(s) registered (15 migration, 1 new), 15 retired legacy prefix set(s) confirmed gone, 16 component binding(s) agreed, 8 mount-action identifier(s) confined, 11 island primaryAction(s) wired, Creation.svelte mounts no component`
- [ ] `python tooling/verify/checks/page_contract.py` exits 0 and its last
      line ends with
      `15 of 15 CREATION_TABS entries mount at least one island, 0 mount none`.
- [ ] Deleting `subjectWorklist: SubjectWorklist` from `mount.js`'s
      `COMPONENTS`, running the check, and restoring with `git checkout --`:
      the check exits 1 with a message naming `subjectWorklist`.
- [ ] `python tooling/verify/checks/corpus_gate.py` prints
      `110 check(s) discovered, 110 executed, 110 passed`.
- [ ] `python tooling/verify/run.py --ticket TICKET-0088-greenfield-creation-island`
      is green.
- [ ] `git status` is clean, and the work is in exactly two commits.
- [ ] *(browser)* The Creation tab bar reads `… Événements, Sujets, Review
      Queue, Prompts`, and `/creation/subjects` opens the tab directly.
- [ ] *(browser)* The panel head reads `N sujet(s) · M ligne(s)`, with `N`
      equal to the length of
      `GET /api/worlds/<world>/unresolved-subjects` and `M` the sum of its
      `row_count` values.
- [ ] *(browser)* A row whose `resolution.verdict` is `matched` shows
      `Suggestion : <name> (<type>)` with the picker preselected and « Lier »
      enabled; a row with no suggestion keeps « Lier » disabled until an
      entity is chosen.
- [ ] *(browser)* Binding a subject with `k` facts writes exactly `k`
      `fact_participant` rows, all with `role` NULL, removes the subject
      from the list, and lowers both head counts.
- [ ] *(browser)* With a simulated failure on the second POST of a two-fact
      subject, one fact stays bound, the card shows
      `1/2 fait(s) lié(s) avant l'échec : <message>`, and the subject stays
      listed with `1 fait(s)`.
- [ ] *(browser)* Leaving the tab and returning keeps the rows; the browser
      console shows no error other than that simulated failure and any
      pre-existing `/favicon.ico` 404.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — the new entry (item 12).
- `tooling/standards/DECISIONS_INDEX.md` — regenerated (item 13).
- `frontend/src/creation/registry.js` — the entry's own comment (item 4) is
  its doc.
- No `CLAUDE.md` change, no schema changelog entry.
