# SUPPLEMENT-0059 — RECON amendments

Ticket: TICKET-0059. Issued after BRIEF-0059-a executed and triggered its own
M4 Stop rule. This document amends TICKET-0059's Clarifications and its brief
chain. Locks resolved by Nia this session: **F3, G1, H1, I1, J1**.

Every brief in the chain reads this file alongside the ticket. Where this
document and TICKET-0059 disagree, this document wins.

---

## AMENDMENT 1 — lock C1 is amended, not withdrawn (lock F3)

**Finding.** RECON-0059-a M4: `_npcAgentTreeHtml` (`index.html:7463-7475`)
and `_linkAgentTreeHtml` (`index.html:7959-7971`) are not a copy-paste modulo
renames. One is a single-select radio tree over a lone
`npcAgentSelectedRoot`; the other is a multi-select checkbox tree over a
`Set`, whose `_linkAgentIsChecked` (`index.html:7948`) additionally treats a
node as checked when **any ancestor** is checked.

**What is actually shared.** The recursive traversal, and only that: root
detection (`!parent_location_id || !known.has(parent_location_id)`),
alphabetical sort, recursion, and the two CSS classes
`linkagent-loc-node` / `linkagent-loc-children` — which M4 confirms are
already styled by **one shared rule set** serving both trees.

**What is not shared.** The row control (radio vs checkbox) and the
checked-state predicate. Note that `_linkAgentIsChecked` is a *predicate*,
not tree logic: ancestor inheritance is a question the consumer answers about
a node, not a traversal behaviour.

**Amended C1.** `frontend/src/creation/LocationTree.svelte` owns the
traversal. It takes:

- `locations` — the flat array; the component derives its own `known` id set.
- `isChecked(node)` — a predicate prop, called per node.
- a **row snippet** (Svelte 5 snippet, not a `mode` prop) rendering the
  control for one node.

`npcAgent` passes `isChecked = (n) => n.id === selectedRoot` and a radio
snippet. `linkAgent` passes its ancestor-aware predicate and a checkbox
snippet.

**Rejected: a `mode: 'single' | 'multi'` prop** (RECON-0059-a's own
suggestion). It is the leaky union type TICKET-0057's D-C question taught
this project to refuse: a component that branches internally on an
interaction-model enum has absorbed two behaviours rather than converged one.
The snippet seam puts the difference where it actually lives — at the row —
and leaves the component with a single behaviour.

**Rejected: withdrawing C1 and shipping two pickers.** The traversal *is*
duplicated, the CSS *is* already shared. Two Svelte tree renderers would
reproduce in the new stack the exact divergence this workstream exists to
end.

**Consequence for the chain.** Brief `-f` extracts `LocationTree.svelte`
first, in its own commit, before either agent migrates. A new fail-closed
check `location_tree.py` asserts exactly one recursive location-tree renderer
exists under `frontend/src/` — the ticket's acceptance list already names it.

---

## AMENDMENT 2 — the seal is scoped to `callLegacy`, not to the string `legacyCall` (lock G1)

**Finding.** RECON-0059-a M1's note: the real primitive is the private,
unexported `callLegacy(fnName, ...args)` (`frontend/src/legacy/bridge.js:24`).
`legacyCall` (`bridge.js:153`) is a thin passthrough. Eight further named
exports reach the identical legacy window through the identical primitive
without ever spelling `legacyCall`:

```
showSurface              -> callLegacy(entry.showFn)                  bridge.js:38
activateWorldViaLegacy   -> callLegacy('activateWorld', ...)          bridge.js:42
openWorldCreate          -> callLegacy('worldCreateOpen')             bridge.js:46
openWorldDelete          -> callLegacy('worldDeleteOpen')             bridge.js:50
showCreationTab          -> callLegacy('showCreationSubTab', ...)     bridge.js:95
getSelectedCharacterId   -> callLegacy('authorGetSelectedEntityId')   bridge.js:123
selectEntity             -> callLegacy('authorSelectEntity', ...)     bridge.js:136
selectRecord             -> callLegacy('creationSelectRecord', ...)   bridge.js:140
```

A check grepping the literal string `legacyCall(` — which is what
BRIEF-0059-b originally specified — would have been structurally blind to
this entire class, and to any new site added the same way. That is a
fail-open gap in the one seam E1 declares must be fail-closed.

**Amended E1.** `legacy_call.py` censuses **call sites of every
`legacy/bridge.js` export that resolves through `callLegacy`** — all nine,
`legacyCall` included. The baseline enumerates those call sites across
`frontend/src/`, not the wrapper definitions inside `bridge.js`.

**Explicitly out of scope:** `legacyContainer` and `legacyDocument`. They do
not call a legacy function; they hand out a DOM node, and that seam is
already governed by `creation_island.py` and `legacy_mount.py`. Adding them
here would duplicate an existing guard and confuse two distinct couplings.

**Baseline seed count is measured, not asserted.** M1 reported the eight
wrapper *definitions* and named callers for only three of them
(`relations.js:214`, `EntityList.svelte:168`, `EntityList.svelte:172`).
Brief `-b` performs the remaining census itself. Expected order of magnitude:
28-32 records. A materially different figure is REPORTED in the commit
message, not a Stop.

**Baseline gains a `retiredBy` column.** Record format:

```
<path-relative-to-repo-root>::<legacy function name>::<TICKET-NNNN>
```

Not every record can close in this ticket: `showSurface` dispatches Play and
Observation and survives until TICKET-0061; `activateWorld` is read on every
boot by the still-legacy Play surface. Rule 7's terminal condition is
therefore **"zero records bearing `TICKET-0059`"**, not "zero records" — the
same shape as `LEGACY_MOUNTS`'s own `retiredBy` field, one level down.

**Assignment rule for `retiredBy`, and its default.** A record is
`TICKET-0059` if its legacy target is a Creation-side function — the `author*`
families, the `creation*` chrome helpers, `worldCreateOpen`/`worldDeleteOpen`,
`showCreationSubTab`, `genericModal*`. It is `TICKET-0061` only where the
target is demonstrably read by Play (`showSurface`, `activateWorld`).

**Ambiguous cases default to `TICKET-0059`.** That is the fail-closed
direction: a record wrongly marked 0059 blocks `-l` and produces an
escalation, which is visible and correct; a record wrongly marked 0061
survives the ticket silently, which is the failure this seal exists to
prevent.

---

## AMENDMENT 3 — `-e` cannot reach zero; chrome-owned records close at `-l`

**Finding.** Not reported by `-a` directly, but forced by M3 + M6 read
together, and confirmed against the tree this session: several `legacyCall`
targets are **chrome**, not sheet-local, and cannot be deleted before the
chrome inverts.

- `creationRefreshList` (`index.html:4432`) — 4 call sites
  (`Sheet.svelte:393`, `:474`, `Region.svelte:311`, `RoomBatch.svelte:246`).
  Chrome. Dispatches `island:slot` for every island the active tab declares;
  still-legacy tabs depend on it.
- `creationOpenEntityFrom` (`FactionRoster.svelte:58`) and
  `creationSelectRecord` (`EntityList.svelte:172`) — chrome navigation
  helpers, guarded by `creation_return_nav.py`.
- `genericModalOpen` / `genericModalClose` (`locationType.js:46`, `:104`) —
  **a shared modal primitive**, defined at `index.html:8326`/`8334` with its
  own markup at `index.html:8892-8898`, and consumed by three call sites
  beyond the Svelte one: `competences` (`4752`, `4770`), world create
  (`8401`, `8445`), world delete (`8500`, `8519`). It is not sheet-local and
  cannot move with the sheet.

**Amended `-e`.** The brief is re-scoped from "residual `legacyCall` sites;
baseline -> 0" to **"entity-sheet state ownership"**: the sheet's selection
and create-draft lifecycle move into a Svelte store, closing
`authorSelectEntity`, `authorGetSelectedEntityId`, `authorDelete`, and the
four `_author*` lifecycle helpers. `Sheet.svelte`'s own bridge-reach count
reaches **zero**; the baseline drops by roughly nine records but does not
empty.

**The baseline reaches zero-for-TICKET-0059 at `-l`**, when the chrome
inverts and `creationRefreshList` / `creationSelectRecord` /
`creationOpenEntityFrom` / `genericModal*` cease to exist. Rule 7 gates that
brief, which is exactly the ordering the seal was built to enforce.

**New scope for `-l`, consequent:** `genericModal*` becomes
`frontend/src/creation/Modal.svelte`, a governed primitive with three
declared consumers. Three legacy consumers plus one Svelte consumer, one
implementation — the same shape as the graph and review primitives. This is
not an opportunistic improvement; the legacy implementation must die for the
mount to retire, and its consumers need somewhere to land.

---

## AMENDMENT 4 — `-k` is Review Queue only; world CRUD folds into `-l` (lock H1)

**Finding.** RECON-0059-a M5 corrects the queue cluster from 13 to **23
functions** (`index.html:2752-3191`), and — materially — **refutes the
workstream map's A2 interleaving claim for this cluster**: `2079-2747` is
Play-scene code with zero queue functions inside it. There is no
function-body interleaving here. `Active project.md` A2 is wrong on this
point and is corrected in `-m`.

M5 also confirms all 23 are Creation-only by caller trace, including the
generically-named `showResult` / `lockCard` / `unlockCard` / `markCardDone`
(queue-private despite the names). No Stop trigger.

**Amended chain.** `-k` carries the 23 queue functions and nothing else. The
six `world*` CRUD functions (`index.html:8400-8513`) move to `-l`: M6 already
places `loadWorldSelector` (8349) and `activateWorld` (8364) in the chrome
inventory, and `worldCreateOpen`/`worldDeleteOpen` are reached from the
shell's own Header through `bridge.js`. World CRUD is chrome, and it needs
`Modal.svelte` (Amendment 3) to exist, which `-l` builds.

Re-lettering is clean here: only `-a` has executed.

---

## AMENDMENT 5 — `cw*` migrates with Prompts, still parked (lock I1)

**Finding.** RECON-0059-a M5: three functions in the Prompts line range —
`cwLoadConfig` (5323), `_cwRenderConfig` (5334), `cwPatchField` (5359) —
implement the conversation-window config panel. It renders inside the Prompts
tab (`promptsLoadList` calls `cwLoadConfig()` at 5304) but is a world-level
config surface parked there by named deferral **D-0050**.

**Resolution.** `-i` ports all 34 functions (31 prompts + 3 `cw*`) verbatim.
`cw*` stays rendered inside the Prompts pane. D-0050 is untouched, and is
re-stated verbatim in `-m` with its reactivation condition intact.

Rejected: activating D-0050 and building the world-config surface now. That
is a doctrine decision, and a migration ticket does not carry one.

---

## AMENDMENT 6 — the frontend module budget becomes a check (lock J1)

**Finding.** RECON-0059-a M8: `module_budget.py` is AST-based and globs only
`SRC.rglob("*.py")`. It has no code path touching `.svelte` or `.js`. The
1000-line module budget (R5) is presently **doctrinal convention only** for
`frontend/`.

M8 also measures `Sheet.svelte` at **656 lines**, with `-c` (~230) and `-d`
(~400) both landing in its vicinity: 1286 lines if the sub-editors are
inlined.

**Resolution.** `-b` extends `module_budget.py` with a line-count rule over
`frontend/src/**/*.{svelte,js}`, in a **separate commit** from the seal.
BRIEF-0059-c already specifies sibling component files
(`RelationsEditor.svelte`, `KnowledgeEditor.svelte`) rather than inlining, so
`-c` is unaffected; `-d` follows the same pattern.

Structural over disciplinary: the constraint that would otherwise be enforced
by two briefs remembering it becomes a gate.

---

## AMENDMENT 7 — `creation_island.py` is named explicitly for `-l`

**Finding.** RECON-0059-a M7 flags a soft gap: `creation_island.py` rules
4/5/9/10/11 are anchored on the `CREATION_TABS` literal,
`_creationActivateTab` and `creationRefreshList` living in `index.html` —
precisely what D1 moves to `frontend/src/creation/tabs.js` and
`Creation.svelte` at `-l`. Only rule 7's mechanism is named in TICKET-0059's
acceptance list.

**Resolution.** Add to TICKET-0059's machine-checkable acceptance criteria:

> - [ ] `creation_island.py` rules 4/5/9/10/11 re-anchored onto
>       `frontend/src/creation/tabs.js` and `Creation.svelte`, with rule 7's
>       retired-prefix scan against `index.html` preserved  ->
>       verify/checks/creation_island.py

---

## AMENDMENT 8 — inputs carried forward to specific briefs

Not decisions; findings that must not be lost between sessions.

- **`-d`:** `_goalPrereqRawList` (`index.html:6907`) is a private helper used
  exclusively by the goals family and is not `author*`-prefixed. It ports
  with the family and must be added to the retired-identifier list by name.
- **`-d`:** a `document.addEventListener('creation:goals-backfilled', ...)`
  listener at `index.html:7033` makes the **legacy document listen to a
  Svelte event** emitted by the already-migrated `EntityList.svelte`. This is
  the reverse of the `legacyCall` direction and is invisible to the seal's
  census. `-d` must re-express it Svelte-side and prove the backfill still
  refreshes the goals panel.
- **`-h`:** `authorAddLedgerEntry` (`index.html:4801`) is confirmed
  Registre-owned — its sole caller is the static button at `index.html:1468`
  inside the Registre add-form markup. It closes in `-h`, not `-d`.
- **`-l`:** `faction_roster_panel.py`, `review_component.py` and
  `schema_0024.py` are confirmed to need **no** re-homing (M7). Do not spend
  effort on them. `graph_primitive.py`'s `GONE_PLAIN` is a data list extended
  per migrating brief — `-f` and `-g` each extend it in their own commits.
- **`-m`:** correct `Active project.md` A2's interleaving claim for the
  queue cluster (Amendment 4), and correct TICKET-0059's intake figure of
  "30 files" under `frontend/src/creation/` to 33.

---

## Amended brief chain

| Brief | Step | Status |
|---|---|---|
| `-a` | periphery closure mini-RECON | **DONE** — Stop fired on M4, resolved by Amendment 1 |
| `-b` | `legacy_call.py` (scoped per Amendment 2) + frontend module budget | revised, reissued |
| `-c` | Sheet: relations + knowledge | unchanged |
| `-d` | Sheet: goals + discipline details | issued |
| `-e` | Sheet state ownership (re-scoped per Amendment 3) | issued |
| `-f` | `LocationTree.svelte` (per Amendment 1) + npcAgent island | pending |
| `-g` | linkAgent island | pending |
| `-h` | `competences` + `registre` + `artefacts` | pending |
| `-i` | `prompts` + `cw*` (per Amendment 5) | pending |
| `-j` | `intrigues` bespoke + `pj`/`pc`/`skill` | pending |
| `-k` | Review Queue, 23 fns (per Amendment 4) | pending |
| `-l` | chrome inversion + world CRUD + `Modal.svelte` + check re-homing | pending |
| `-m` | doctrine seal + docs + map corrections | pending |
