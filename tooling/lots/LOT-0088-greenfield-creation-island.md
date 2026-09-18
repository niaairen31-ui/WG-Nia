<!-- slug: greenfield-creation-island -->

# LOT — TICKET-0088 "Greenfield Creation islands, and the unresolved-subject worklist"

## Objective and cut

`CREATION_ISLANDS` is a migration-provenance ledger: every entry declares
`migratedBy` and a non-empty `retiredPrefixes`, and `creation_island.py`
proves those prefixes are gone from the legacy document. A surface created
directly as an island has no migration to declare, which is why BRIEF-0087-d
could not build the residue worklist (AMENDMENT-0087-2, code `K3`).

This lot teaches the registry to record `origin` -- `'migration'` or `'new'` --
with a closed field set per origin, closes the two registration gaps the
RECON of the decision session found (`COMPONENTS` agreement, the
declarative bypass), and lands the first `origin: 'new'` surface: the
unresolved-subject worklist, bound by a client-side loop over the existing
routes.

The lot stops there. No backend change, no schema change, no new route. It
does not touch TICKET-0087's artifacts: AMENDMENT-0087-3 (code `G1`) and
BRIEF-0087-e's regeneration belong to the session that closes TICKET-0087
(code `H1`), and are deposited on the branch BRIEF-0087-e runs from.

## Briefs in this lot

| letter | file | one line |
|--------|------|----------|
| A | `BRIEF-0088-a-island-provenance-gate.md` | `creation_island.py` parses the registry order-free and comment-aware, enforces a closed field set per `origin`, fails closed on a missing legacy document, adds the `COMPONENTS` agreement rule and the no-mount rule for `Creation.svelte`, and carries its own self-test; `registry.js` gains `origin: 'migration'` on all 15 entries. |
| B | `BRIEF-0088-b-subject-worklist-panel.md` | The `subjects` Creation tab: `SubjectWorklist.svelte` + `subjectWorklist.svelte.js`, the first `origin: 'new'` registry entry, its `tabs.js` entry, container, `COMPONENTS` line, and `page_contract.py`'s coverage list and PASS wording. |

## Dependency graph

Strictly sequential: **A -> B**.

- B's registry entry declares `origin: 'new'`, which brief A's parser is the
  first to accept. Under the parser on `main` today (R-05), that entry does
  not match `ENTRY_RE` at all: it is silently absent from `entries`, and
  rules 5 and 11 fail with "no matching entry" (R-05, R-09).
- B's `mount.js` edit is checked by rule 12, which brief A creates (C-03).
- B's `Creation.svelte` edit is checked by rule 13, which brief A creates
  (C-04).
- B's done-means quote the PASS line of C-02, which brief A creates.

No other order is available, and this order comes from the dependency, not
from a locked decision.

Branch: `ticket/0088`, cut from `main`, MR onto `main` (code `F3`). P-1 is
checked before the first edit (R-01).

## RECON

Run 2026-09-17 in the chat session against `origin/main` at `994c9b2`,
fetched from GitHub. Tags: **[M]** opened and measured in the file that
declares the property; **[E]** measured by running code (the check itself, or
a throwaway prototype, never on the real tree); **[C]** carried from the
decision session's RECON without re-measurement; **[I]** inferred.

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

### R-02 — `legacy.html` is live Play code, and rule 7 still guards it

Opened: `src/world_engine/cockpit/legacy.html`,
`frontend/src/legacy/registry.js`, `tooling/tickets/TICKET-0069-play-surface-migration.md`,
`src/world_engine/cockpit/app.py`, `tooling/verify/checks/module_budget.py`. [M]

Finding: the document is 2 762 lines. `module_budget.py:65` holds
`LEGACY_DOCUMENT_LINE_CEILING = 2762`, a two-way ratchet: exceeding it fails,
and coming in under it also fails until the constant is lowered in the same
commit; the file's absence is a failure (`module_budget.py:1-40`).
`frontend/src/legacy/registry.js:33-35` reads
`LEGACY_MOUNTS = { play: { showFn: 'showPlayView', retiredBy: 'TICKET-0069' } }`,
and TICKET-0069 is `status: paused`. `cockpit/app.py:68` resolves the path
and `:258-270` serves `GET /legacy`.

Consequence: retiring rules 2 and 7 is not available to this lot. Rule 7
keeps a real subject -- Creation code reappearing in the sealed document --
for the 15 migration entries, and must keep proving it for them alone.

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

### R-04 — what the registry actually holds

Opened: `frontend/src/creation/registry.js`, parsed by a throwaway
comment-aware prototype (never on the real tree; the tree was read only). [E]

Finding: 15 entries, all `migratedBy: TICKET-0058` (5) or `TICKET-0059`
(10); 297 prefixes, all distinct, all matching
`^[A-Za-z_$][A-Za-z0-9_$]*$`; zero of the 297 matches
`function <prefix>\w*\(` in `legacy.html`. Enumeration pasted in gate (c).

Consequence: the lot's claims about the registry rest on this enumeration,
not on the check's own reading, which is not faithful (R-06). After brief A
the same parse must still yield 15 entries and 297 prefixes; after brief B,
16 entries and 297 prefixes.

### R-05 — `creation_island.py`: constants and the positional parse

Opened: `tooling/verify/checks/creation_island.py` (630 lines). [M]

Finding:
- `INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "legacy.html"`
  (`:107`) -- the constant name no longer matches the file it points at.
- `ENTRY_RE` (`:109-116`) requires `containerId`, `component`, `migratedBy`,
  `retiredPrefixes` in that exact order, then `})`.
- `_parse_registry()` (`:218-234`) takes no argument, reads `REGISTRY_FILE`
  itself, keeps `ENTRY_RE.findall` matches only, and returns
  `dict[key] -> {containerId, component, migratedBy, retiredPrefixes}` or
  `None` (after `fail`) when the file is missing or zero entries parse.
- Prefixes are read at `:229` with `re.findall(r"'([^']*)'", prefixes_src)`
  over the raw text captured by `retiredPrefixes:\s*\[([^\]]*)\]`.
- An entry that deviates in any way -- an added field, a reordered field --
  does not error: it is simply absent from `entries`. Rules 2, 3, 4, 7 never
  see it; only rule 5 (`:274-301`) and rule 11 (`:507-563`) notice, and only
  because `tabs.js` declares the key, with "declares island key 'x' with no
  matching entry".

Consequence: `origin` cannot be added under this parser. The parse is
replaced, not extended, and the replacement must make a declared-but-
unparsable entry a FAILURE (C-01), which is what makes the `origin` field
safe to require.

### R-06 — the positional parse mis-reads the prefix lists

Opened: `creation_island.py:229` run against
`frontend/src/creation/registry.js`, compared with the comment-aware parse
of R-04. [E]

Finding: registry-wide, `:229` reads 303 strings where 297 real prefixes
exist. Every entry parses exactly except `entitySheet`, whose list carries
`//` comments containing apostrophes and quoted words: the check reads 140
strings there for 134 real prefixes, and **16 real prefixes are never
examined** (enumeration in gate (c)). None of the 16 has a surviving
`function <prefix>...(` declaration in `legacy.html`, so nothing is
hidden-red today.

Consequence: "15 retired legacy prefix set(s) confirmed gone" is not what
the check proves. Stripping comments before parsing (C-02) is what makes the
sentence true, and it changes the examined set from 303 strings to 297
prefixes.

### R-07 — rule 2 as implemented

Opened: `creation_island.py:237-251`, `:117`. [M]

Finding: `_rule2_shape(entries) -> int` requires, per entry and in this
order: `migratedBy` matches `^TICKET-\d{4}$` (`MIGRATED_BY_RE`, `:117`);
`containerId` and `component` both non-empty; `retiredPrefixes` non-empty
and every item non-empty. It returns the count of conforming entries, and
the verdict requires `shape_count == len(entries)` (`:606`).

Consequence: `retiredPrefixes` is required of every entry, which is the wall
BRIEF-0087-d hit. The rule is rewritten around `origin` (C-01), keeping the
same count-equality shape so the verdict stays fail-closed.

### R-08 — rule 7 is fail-open on a missing document; rule 8 re-reads it

Opened: `creation_island.py:329-342`, `:582`, `:432`. [M][E]

Finding: `_rule7_retired_gone(html, entries) -> int` searches
`function {re.escape(prefix)}\w*\(` in `html` for every prefix of every
entry and counts entries with no hit; the verdict requires
`retired_count == len(entries)` (`:611`). `main()` builds that argument at
`:582` as
`html = INDEX_HTML.read_text(...) if INDEX_HTML.is_file() else ""`.
With the document absent, every prefix "passes" and the check prints the
full PASS line and exits 0 (measured on a throwaway copy by the decision
session [C]; the code path is plain on the line). Rule 8 independently
re-reads the same file with the same fallback at `:432`, inside its event
loop.

Consequence: the document is read once in `main()` and passed to both rules
as `str | None`; rule 7 fails closed on `None` while migration entries exist
(C-01, case table in gate (b)). `module_budget.py` also fails on the
document's absence (R-02), so the corpus was never blind to it -- but this
check's own PASS line claimed something it did not prove.

### R-09 — the rules this lot does not change

Opened: `creation_island.py:254-326`, `:345-442`, `:445-563`. [M]

Finding:
- Rule 3 (`:254-261`): every `component` exists under `frontend/src/creation/`.
- Rule 4 (`:264-271`): `id="<containerId>"` appears in `Creation.svelte`.
- Rule 5 (`:274-301`): many-to-many between registry keys and
  `CREATION_TABS` `islands: [{ key, containerId }]` declarations, with
  matching `containerId`, in both directions; `ISLAND_DECL_RE` (`:120`)
  expects `key` then `containerId`, single-quoted, in that order.
- Rule 6 (`:304-326`): `\bsvelteMount\(` (`SVELTE_MOUNT_CALL_RE`, `:118`)
  appears only in `creation/mount.js` and `graph/mount.js`, and at least
  once in the former. The docstring's "`mount(` from `svelte`" half is not
  implemented.
- Rule 8 (`:345-442`) counts 8: `activateIsland` and `triggerPrimaryAction`
  each `export function`-defined once in `mount.js` and imported only by
  `Creation.svelte` (2); `_activateIslandImpl(` and
  `_triggerPrimaryActionImpl(` present in `tabs.js` (2);
  `export function setMountActions(` in `tabs.js` (1), called only from
  `Creation.svelte` (1); `island:slot` and `island:action` neither
  dispatched nor listened for anywhere under `frontend/src` nor in the
  legacy document (2). The verdict requires `action_count == 8` (`:612`).
- Rule 9 (`:445-475`): an entry with a non-empty `islands` list declares
  `loader: null` and `state.onWorldSwitch: null`.
- Rule 10 (`:478-504`): `_creationActivateTab` calls `creationRefreshList(`,
  `creationRefreshList` calls `activateIslandFor(`, and neither body
  contains `loaded|mounted|_once`.
- Rule 11 (`:507-563`): pairing. A `primaryAction` object whose handler
  contains `triggerPrimaryAction(` requires `createPanel` null or absent and
  the component's `export function primaryAction`; a non-routed one requires
  a non-null `createPanel`. `:533` lets a non-routed object with **no**
  `createPanel` field through. All 12 `primaryAction: {` sites in `tabs.js`
  are routed (gate (c)), so the gap is unreachable today.

Consequence: none of these rules changes. A `new` entry satisfies 3, 4, 5, 9
and 10 exactly as a migration entry does; rule 11 never looks at it, because
its tab declares `primaryAction: null` (B1). The rule 6 and rule 11 gaps are
named deferrals of this lot, not repairs.

### R-10 — the verdict, the PASS line, and what the runner keeps

Opened: `creation_island.py:129-140`, `:566-627`; `tooling/verify/run.py:55-60`. [M]

Finding: `main()` reads `tabs.js`, `mount.js`, `Creation.svelte` (existence
checked first, empty content fails), then the registry, then runs the rules
in order and applies the verdict at `:604-617`: any `FAILURES`, or
`shape_count != len(entries)`, or a false `component_ok/container_ok/
bijection_ok/mechanism_ok/state_ok/dispatch_ok`, or
`retired_count != len(entries)`, or `action_count != 8`, routes to
`_report_and_exit()` with no counts. `_report_and_exit(counts)` (`:129-140`)
prints one `FAIL: <msg>` line per failure and exits 1, or the single PASS
line at `:134-139` and exits 0 -- it dereferences `counts` unconditionally
on the PASS path, so an unmet equality with an empty `FAILURES` list would
raise rather than print. `run.py` records only the last stdout line of a
check as its message (`:59-60`).

Consequence: C-02 keeps the equality shape and closes that hole: every
unmet verdict condition records a failure message before reporting. The PASS
line stays one line, printed last, because that single line is the recorded
verdict.

### R-11 — the docstring, and what drifted inside it

Opened: `creation_island.py:1-92`. [M]

Finding: `:1-10` intro; `:12-24` the BRIEF-0058-e amendment paragraph;
`:26-36` the BRIEF-0059-l commit 1 amendment paragraph, whose last sentence
ends at `:36` with "the migration only partly happened."; `:38-42` the idiom
paragraph (module-level `FAILURES`, `fail()`, `_report_and_exit(counts)`,
`ROOT` via `parents[3]`, stdlib only, vacuity-proof rules). The numbered
rules are `:44-91`. Two amendment paragraphs, not three. The drift is in
rule 6 (`:56-59`, claims a `mount(`-from-`svelte` form that is not
implemented), rule 7 (`:60-65`, names `index.html`) and rule 8 (`:66-72`,
"invoked ... only from tabs.js", while the implementation confines the
imports to `Creation.svelte` and looks for the `_*Impl(` wrappers in
`tabs.js`). No other check imports this module; `creation_tab_switch.py:27`,
`legacy_call.py:60` and `review_component.py:35` name it in comments only.

Consequence: brief A rewrites the numbered rules from the code and appends
one amendment paragraph, keeping the intro, both existing amendment
paragraphs and the idiom paragraph as history.

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

### R-13 — who imports `mount` from `svelte`

Opened: `grep -rlE "import\s*\{[^}]*\b(mount|hydrate)\b[^}]*\}\s*from\s*['\"]svelte['\"]" frontend/src`. [M]

Finding: exactly three files -- `frontend/src/main.js` (the App root),
`frontend/src/creation/mount.js`, `frontend/src/graph/mount.js`.

Consequence: rule 6's `svelteMount(` alias is the only call form in use, and
the docstring must say so rather than claim a form it does not implement.
The absence of a fourth importer is what makes D-0088-rule6-alias's
reactivation condition meaningful.

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

### R-20 — how a check is run, and the precedent for self-verification

Opened: `tooling/verify/checks/corpus_gate.py`,
`tooling/verify/checks/fact_spine.py`. [M]

Finding: `corpus_gate.py` discovers every `*.py` in `tooling/verify/checks/`
(`_discover`, `:163-175`, `CHECKS.glob("*.py")` at `:167`), excludes exactly
itself, and runs each in a subprocess with `TIMEOUT_SECONDS = 15` (`:53`,
`:199`). `fact_spine.py` builds a fresh temp-file SQLite fixture through the
real writers inside the check file and asserts vacuity-proof counts over it
(`check_db_fixture`, `:103-163`).

Consequence: a self-test helper placed in `checks/` would itself be
discovered and run as a check, so the self-test lives inside
`creation_island.py` (decision `K1`); the corpus already contains a check
that verifies itself against data it builds, so this is not a new idiom.
`creation_island.py` runs in 0.09 s today [E], two orders below the timeout.

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

### R-30 — `CLAUDE.md` and its contract

Opened: `CLAUDE.md`, `tooling/verify/checks/claude_md_contract.py`. [M]

Finding: 34 100 characters, 532 lines, longest line 100. The budgets are
`TOTAL_CHAR_BUDGET = 38_000` (`:69`), `MAX_LINE_LENGTH = 100` (`:70`),
`FILE_STRUCTURE_LINE_BUDGET = 80` (`:71`). The archaeology ban gives the
`### File structure` section zero matches for `BRIEF-`, `schema v` or
`v\d+\.\d+`, and the `## Invariants (verified at every review)` section zero
matches for `TICKET-\d` or `BRIEF-\d` (`:19-22`, enforced `:155-177`); an
Invariants section collecting zero `- ` bullets is a failure (`:169`). Every
bare `<name>.py` token in the file must name a file that exists on disk
(`check_py_pointer_freshness`, `:203-215`). Line 407 reads
`│   └── src/creation/         # Svelte islands + review-tree; registry.js GROWS as surfaces migrate`
(99 characters). Lines 335-336 hold the invariant "Every Création page is a
`CREATION_TABS` registry entry rendered by the generic dispatcher; no
page/tab-specific branch exists outside it — enforced by `page_contract.py`."

Consequence: decision `I1`'s two texts cost +223 characters (34 323 of
38 000), add three lines of 98/99/23 characters, name only
`creation_island.py` (which exists), and carry no `TICKET-`/`BRIEF-` token
inside the Invariants section.

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

### R-34 — corpus baseline

Carried from the decision session: a full copy of this tree under Python
3.13 with `WORLD_ENGINE_ENV=test` gives
`PASS: corpus_gate — 110 check(s) discovered, 110 executed, 110 passed`;
without that variable, `109 passed, 1 crash`, because `day_mutations.py`
reaches `db.py`'s fail-closed resolution at import time (S-4, pre-existing).
[C] On this session's tree, `creation_island.py` and `page_contract.py` were
re-run directly and are green [E].

Consequence: each brief records its own baseline first, on the real machine,
and sets `WORLD_ENGINE_ENV=test` for the run when `day_mutations.py`
crashes naming it.

## Contract sheet

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

### C-02 — `_strip_js_comments(text, fail, label)`

Produced by: BRIEF-0088-a   Consumed by: BRIEF-0088-a (rules 1, 12, 13); no
later brief.

Signature: `_strip_js_comments(text: str, fail, label: str) -> str | None`.
Exactly three parameters in every mention. `fail` is a callable taking one
message; `label` names the file in every message it emits.

One left-to-right scan:
- `//` to end of line: removed, the newline kept.
- `/* ... */`: removed, its newlines kept (so line numbers are preserved).
- `'`, `"` and `` ` `` strings: copied verbatim, including the quotes; a
  backslash escapes the next character; a raw newline inside a `'` or `"`
  string is an error.
- A `/` that opens a regex literal -- its previous significant character
  (the last non-whitespace character already emitted) being one of
  `( , = : [ ! & | ? { } ; +`, or there being none -- is copied verbatim up
  to the next unescaped `/` outside a `[...]` class; a newline before that
  `/` is an error. Any other `/` is division and is copied.
- An unterminated string, comment or regex literal calls `fail` once,
  naming `label`, and the function returns `None`.

Return: the stripped text, of the same line count as the input.

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

## Gate output

### (a) Property trace

Every property this lot asserts about existing code, the finding that
carries it, and the file that finding opened -- the file where the property
is **declared**.

| property asserted | finding | declaring file opened |
|---|---|---|
| The registry literal's position, header block, trailing commas | R-03 | `frontend/src/creation/registry.js` |
| 15 entries, all migration; 297 identifier-shaped prefixes; none survives in the legacy document | R-04 | `registry.js`, `legacy.html` (parsed) |
| `ENTRY_RE` is positional; a deviating entry is silently absent | R-05 | `creation_island.py:109-116, 218-234` |
| Prefixes are read with `'([^']*)'` over raw text; 303 strings, 16 real prefixes never examined | R-06 | `creation_island.py:229` (executed) |
| Rule 2 requires `migratedBy` and a non-empty `retiredPrefixes` | R-07 | `creation_island.py:237-251` |
| Rule 7 is fail-open on a missing document; rule 8 re-reads it | R-08 | `creation_island.py:329-342, 432, 582` |
| Rules 3, 4, 5, 6, 8, 9, 10, 11 as executed; rule 11's `:533` gap | R-09 | `creation_island.py:254-563` |
| The verdict's equalities; `_report_and_exit` dereferences `counts` | R-10 | `creation_island.py:129-140, 604-627` |
| `run.py` keeps the last stdout line | R-10, R-31 | `tooling/verify/run.py:55-60` |
| The docstring's structure and its three drifted rules | R-11 | `creation_island.py:1-92` |
| `COMPONENTS` is hand-kept, key set equal, order different; no check reads it | R-12 | `frontend/src/creation/mount.js:26-46` |
| `escapeHtml` holds a regex literal at `:51` | R-12 | `mount.js:50-54` |
| `mountIsland` throws; `activateIsland` only logs | R-12 | `mount.js:68-96, 119-127` |
| `legacyDoc: node.ownerDocument` must survive in `mount.js` | R-12 | `graph_primitive.py:339, 774` |
| Exactly three files import `mount` from `svelte` | R-13 | enumeration over `frontend/src` |
| `Creation.svelte`: one script, four imports, 61 lowercase tags, comments naming `.svelte` | R-14 | `frontend/src/creation/Creation.svelte` |
| The container block's shape and line numbers | R-14 | `Creation.svelte:233-256` |
| `CREATION_TABS` layout, order, bespoke shape, `primaryAction` values | R-15 | `frontend/src/creation/tabs.js:50-354` |
| A new static key needs no route or template change | R-15 | `tabs.js:387-451`, `Creation.svelte:49-88`, `router.js:28-31` |
| `TAB_KEYS` is hand-kept; the counters and the PASS tail | R-16 | `tooling/verify/checks/page_contract.py:46-49, 173-205, 373-389` |
| What each sibling check forbids | R-17 | each check's own module (line refs in the table) |
| The reachable class vocabulary | R-18 | `stylesheet_partition.py::_reachable_names` (executed) |
| Budgets cover `src/` and `frontend/src`, not `tooling/verify/checks` | R-19 | `module_budget.py:49-65`, `function_length.py:115` |
| `corpus_gate` runs every `*.py` in `checks/`, 15 s each | R-20 | `corpus_gate.py:53, 163-199` |
| A check may verify itself with data it builds | R-20 | `fact_spine.py:103-163` |
| `api` throws on a non-ok response; `sheetRequest` writes `author-status` | R-21 | `sheetRequest.svelte.js:30-53` |
| `serverState.worldId` is the client's mirror of the active world | R-22 | `frontend/src/lib/serverState.svelte.js:8, 28` |
| The `Queue.svelte` / `queue.svelte.js` split and its effect | R-22 | `Queue.svelte:20-34`, `queue.svelte.js` |
| The sheet's bind shape, and `/participants` having one caller | R-23 | `KnowledgeEditor.svelte:56-92, 183-200` |
| The residue excludes any fact with any participant; JSON shape | R-24 | `subject_resolve.py:71-107`, `crud/knowledge.py:144-165` |
| The attach route's 404/409, the missing read, the 500 on a duplicate | R-25 | `crud/knowledge.py:243-258`, `writes/facts.py:57-83` |
| `idx_fact_participant_unique` on `(fact_id, entity_id)` | R-25 | `models/canon_knowledge.py:120` |
| `GET /api/entities` is world-scoped and unfiltered on status | R-26 | `crud/entities.py:229-238, 503-512` |
| A bind asserts about the fact; `subject` is editable, `fact_id` is not | R-27 | `crud/knowledge.py:206-229`, `writes/knowledge.py:180-205` |
| The build command, its hashed inputs, `emptyOutDir`, LF | R-28 | `package.json:10`, `vite.config.js:8-9`, `frontend_build_fresh.py:38-89`, `.gitattributes` |
| ADR anchors, footer, header pattern, index generator | R-29 | `ARCHITECTURE_DECISIONS.md`, `decisions_index.py:15-17` |
| CLAUDE.md size, budgets, banned tokens, lines 335-336 and 407 | R-30 | `CLAUDE.md`, `claude_md_contract.py:19-22, 69-71, 203-215` |
| `run.py`'s first-arrow-per-line rule; `pipeline_state`'s section shape | R-31 | `run.py:10-22`, `pipeline_state.py:52-100` |
| `WORLD_ENGINE_DATABASE_URL` wins; `reset_test.py` unlinks the resolved file | R-32 | `db.py:50-70`, `scripts/reset_test.py:36` |

No brief asserts a property that is absent from this table. Facts about code
this lot creates appear only as contract references (C-01..C-06).

### (b) Case tables

**Rule 2, per declared entry (C-01).**

| origin value | field set | outcome |
|---|---|---|
| `'migration'` | exactly `containerId, component, origin, migratedBy, retiredPrefixes` | conforming |
| `'migration'` | plus `createdBy` | FAIL: forbidden field named |
| `'migration'` | `retiredPrefixes: []` | FAIL: non-empty list required |
| `'migration'` | `migratedBy: 'T-88'` | FAIL: pattern named |
| `'new'` | exactly `containerId, component, origin, createdBy` | conforming |
| `'new'` | plus `retiredPrefixes` | FAIL: forbidden field named |
| `'new'` | plus `migratedBy` | FAIL: forbidden field named |
| `'new'` | missing `createdBy` | FAIL: missing field named |
| absent | any | FAIL: `origin` named |
| `'legacy'` (unknown) | any | FAIL: value named |
| any | unknown field `foo` | FAIL: key and `foo` named |
| any | field value double-quoted, identifier or number | FAIL (rule 1) naming key and field |
| any | key declared twice | FAIL: key named; neither occurrence conforms |
| any | entry not wrapped in `Object.freeze({...})` | FAIL: key named; key still counted as declared |

In every FAIL row `len(entries) < len(declared)`, so the verdict (C-05)
fails even if a message were lost.

**Rule 7 (C-05 inputs).**

| migration entries | `html` | outcome |
|---|---|---|
| >= 1 | present, no `function <prefix>...(` hit | `retired_count == migration_count`, PASS path |
| >= 1 | present, one hit | FAIL naming the entry and the survivor; that entry not counted |
| >= 1 | `None` (document absent) | FAIL "cannot prove absence"; `retired_count` stays below `migration_count` |
| 0 | any | FAIL "the migration ledger is gone" |
| any | `new` entries | never examined, never counted |

**Rule 12 (C-03).**

| mount.js state | outcome |
|---|---|
| key set equal, each value the right default import | `binding_count == len(entries)`, PASS path |
| registry key missing from `COMPONENTS` | FAIL naming the key |
| `COMPONENTS` key with no registry entry | FAIL naming the key |
| value identifier not a `.svelte` default import | FAIL naming key and identifier |
| value imported from the wrong path | FAIL naming key, identifier, expected specifier |
| a `.svelte` default import used by no property | FAIL naming the identifier |
| a `.svelte` import that is named, namespace or side-effect | FAIL naming the specifier |
| zero imports, or empty `COMPONENTS` | FAIL (vacuity) |
| an import or a `COMPONENTS` line inside a comment | invisible after C-02: no effect, no failure |

**Rule 13 (C-04).**

| `Creation.svelte` state | outcome |
|---|---|
| no `.svelte` import, no `mount`/`hydrate` from `svelte`, no `import(`, all tags lowercase | returns the tag count |
| `import Foo from './Foo.svelte'` | FAIL naming the specifier |
| `const m = await import('./Foo.svelte')` | FAIL naming the dynamic import |
| `import { mount } from 'svelte'` (aliased or not) | FAIL naming the clause |
| `import { onMount } from 'svelte'` | no failure -- the imported name is not `mount` |
| `<Foo />`, `<lib.Foo />`, `<svelte:component>`, `<svelte:self>` | FAIL naming the tag |
| any of the above inside a comment only | no failure |
| zero scripts, zero imports or zero tags | FAIL (vacuity) |

**The stripper (C-02).**

| input | outcome |
|---|---|
| `// x` / `/* x */` | removed, newlines preserved |
| `'a // b'`, `"a /* b */"` | copied verbatim |
| `` `a ${b} c` `` | copied verbatim |
| `.replace(/[&<>"']/g, ...)` | regex literal copied verbatim (previous significant character `(`) |
| `a / b` | division, copied |
| `'a` with a newline before the close | FAIL naming the label, returns `None` |
| `/* x` to end of file | FAIL naming the label, returns `None` |

**The bind loop (E1), per press of « Lier ».**

| state | outcome |
|---|---|
| no selection for the row | button disabled; nothing sent |
| a bind already in flight | every control disabled; nothing sent |
| n facts, all POSTs succeed | n rows written, list reloads, the subject leaves the list |
| POST k of n fails | loop stops; the card shows `k/n fait(s) lié(s) avant l'échec : <message>`; the list reloads and the subject stays with its n-k unbound facts |
| the world changes mid-loop | the loop stops at the next iteration; the reload is skipped for the old world |
| retry after a partial failure | only the still-unbound facts are posted, so no duplicate pair can be sent (R-24, R-25) |

**Loading, per `$effect` run.**

| state | outcome |
|---|---|
| `worldId` null | rows cleared, "Aucun monde actif." |
| `worldId` changed | rows, entities, selections and errors cleared before the fetch |
| two loads overlap | the older sequence number's result is discarded |
| either request throws | rows and entities cleared, the error rendered |
| zero rows | "✓ Aucun sujet non résolu dans ce monde." |
| rows, `verdict: matched` and the entity in the list | suggestion shown and preselected |
| rows, `verdict: matched`, entity absent from the list | no suggestion, picker empty, button disabled |
| rows, `verdict: ambiguous` | candidate count shown, no preselection |
| rows, `verdict: unmatched` | "Aucune suggestion" |

**`page_contract.py` counters after J1.**

| entry | counted as |
|---|---|
| declares a non-empty `islands` | `island_count` |
| declares none | `bare_count` |
| after brief B | 15 of 15 island, 0 bare |

### (c) Enumerations

Registry, parsed comment-aware (R-04):

```
constructeur   TICKET-0058  creation-constructeur      Constructeur.svelte    prefixes=1
entityList     TICKET-0058  author-entity-list         EntityList.svelte      prefixes=11
entitySheet    TICKET-0058  author-main                Sheet.svelte           prefixes=134
region         TICKET-0058  creation-region            Region.svelte          prefixes=5
batch          TICKET-0058  batch-panel-wrap           RoomBatch.svelte       prefixes=2
npcAgent       TICKET-0059  npcagent-panel             NpcAgent.svelte        prefixes=28
artefacts      TICKET-0059  creation-artefacts         Artefacts.svelte       prefixes=2
competences    TICKET-0059  creation-competences       Competences.svelte     prefixes=13
registre       TICKET-0059  creation-registre          Registre.svelte        prefixes=7
prompts        TICKET-0059  creation-prompts           Prompts.svelte         prefixes=34
linkAgent      TICKET-0059  linkagent-panel            LinkAgent.svelte       prefixes=26
pjSkillFiche   TICKET-0059  creation-pj-skill          PjSkillFiche.svelte    prefixes=8
queueFilters   TICKET-0059  creation-shell-extra       QueueFilters.svelte    prefixes=9
queue          TICKET-0059  creation-queue             Queue.svelte           prefixes=10
queueBatchBar  TICKET-0059  creation-shell-batch-bar   QueueBatchBar.svelte   prefixes=7

15 entries, all origin-less today, all migratedBy TICKET-0058 (5) or TICKET-0059 (10)
297 prefixes, all distinct, all matching ^[A-Za-z_$][A-Za-z0-9_$]*$
0 prefixes match `function <prefix>\w*\(` in src/world_engine/cockpit/legacy.html
```

The current parser's reading of the same file (R-06):

```
old parser: 15 entries, 303 strings read for 297 real prefixes
entitySheet: real=134  read=140  never examined=16
never examined: _authorResetCreateDrafts, _authorGetPendingCreationMutationId,
  _authorConsumePendingCreationMutationId, _authorNotifySaved, loadAgendasList,
  renderAgendaSheet, _intriguesRenderStep, _intriguesRenderLinkedGoal,
  _intriguesRefreshSelection, intriguesSetAgendaStatus, intriguesDetachLink,
  intriguesStepStatus, _intriguesPopulateOwnerSelect, intriguesRenderCreatePanel,
  intriguesGenerateDraft, intriguesSubmitCreate
junk read as prefixes (sample): "s three commits).\n      ", ",\n      ",
  ",\n      // BRIEF-0059-e commit 2: selection -- ported to sheetState.svelte.js"
none of the 16 has a surviving `function <prefix>...(` declaration in legacy.html
```

`COMPONENTS` versus the registry (R-12):

```
COMPONENTS keys (mount.js:46): constructeur, entityList, entitySheet, region, batch,
  npcAgent, linkAgent, artefacts, competences, registre, prompts, pjSkillFiche,
  queueFilters, queue, queueBatchBar
registry keys (order):        constructeur, entityList, entitySheet, region, batch,
  npcAgent, artefacts, competences, registre, prompts, linkAgent, pjSkillFiche,
  queueFilters, queue, queueBatchBar
sets equal: yes    lists equal: no (linkAgent 7th vs 11th)
every value is the default import of './' + component: yes
unused .svelte default imports: none
```

`mount` imported from `svelte` (R-13):

```
frontend/src/main.js
frontend/src/creation/mount.js
frontend/src/graph/mount.js
```

`Creation.svelte` tags, comments removed (R-14):

```
61 tags: div 38, button 10, span 8, h2 3, aside 1, strong 1
uppercase / dotted / svelte:component / svelte:self: none
static imports: 'svelte' ({ onMount }), './state.svelte.js', './tabs.js', './mount.js'
specs ending in .svelte: none        dynamic import(: none
```

`primaryAction` sites in `tabs.js` (R-15), for rule 11's gap:

```
primaryAction: {   199 217 229 244 257 267 276 285 304 316 326 549   (12, all containing triggerPrimaryAction()
primaryAction: null   295 (artefacts)  334 (queue)  352 (prompts)
```

`/participants` under `frontend/src` (R-23):

```
frontend/src/creation/KnowledgeEditor.svelte:34
frontend/src/creation/KnowledgeEditor.svelte:87
frontend/src/creation/KnowledgeEditor.svelte:97
```

Reachable classes used by the panel (R-18):

```
queue-panel True   panel-head True   queue-body True   row-card True
row-card-actions True   empty True   empty-ok True   spin True
btn-icon True   btn-send True        (span-2 False -- unused by this lot)
```

`TAB_KEYS` today (R-16): `npc, pj, lieux, factions, objets, competences,
region, constructeur, artefacts, registre, intrigues, evenements, queue,
prompts` (14), equal to `CREATION_TABS`'s static key set.

### (d) Family contracts

Tick. C-01 was written as a family (grammar, then the shared fields, then
the per-origin sets) before either member was drafted, and re-read after the
second member -- the `new` variant -- was added: the two members differ in
exactly the two fields the table marks forbidden on the other side, and no
member carries a field the family table omits. C-06 was written before the
self-test cases and re-read after the last rule (13) was specified: every
rule this lot adds names the thing it refuses.

### (e) Gates, and the module that satisfies each

Gates this lot **proposes**:

| gate | satisfied by | what it needs that the check forbids |
|---|---|---|
| registry parses and every declared entry conforms (C-01) | `registry.js` after brief A: 15 entries each gaining `origin: 'migration'` | nothing -- the closed field set is exactly what the 15 entries carry |
| rule 7 migration-only, fail-closed | the same 15 entries, plus `legacy.html` (R-02) | nothing; the `new` entry of brief B is never examined |
| `COMPONENTS` agreement (C-03) | `mount.js:26-46`, and brief B's added import + key | the comparison is on key sets, because the two orders differ today (R-12) |
| `Creation.svelte` mounts no component (C-04) | `Creation.svelte` as it stands (R-14), plus brief B's container `<div>` | brief B adds a container and an HTML comment only -- no import, no uppercase tag |
| the self-test names each seeded break (C-06) | `creation_island.py` itself, reading no file (R-20) | it must run inside the check file, since a helper in `checks/` is itself run as a check |

Gates this lot must merely **pass**:

| gate | module that satisfies it |
|---|---|
| `page_contract.py` | brief B's `tabs.js` entry declares `primaryAction: null` and a non-empty `islands`; `subjects` is added to `TAB_KEYS`; the key appears as a literal in neither `showCreationSubTab` nor `_creationActivateTab` (R-16) |
| `effect_self_write.py` | `SubjectWorklist.svelte`'s single `$effect` calls the imported `loadSubjects`; every `$state` write lives in `subjectWorklist.svelte.js`, which the check does not scan (R-17) |
| `stylesheet_partition.py` | the ten classes of R-18, no `<style>` block, no id |
| `graph_primitive.py` | no `<svg`, no `cytoscape(`; `mount.js:91` untouched by both briefs (R-12, R-17) |
| `legacy_mount.py` | no `.src =`, no `contentWindow`, no `legacy-frame` in either new file (R-17) |
| `creation_tab_switch.py` | no `CustomEvent('creation:sheet-reset'` outside `tabs.js`; brief B adds none (R-17) |
| `module_budget.py` | the five touched frontend files stay far under 1 000 lines; `legacy.html` is untouched, so the ratchet holds (R-19, R-02) |
| `frontend_build_fresh.py`, `static_asset_freshness.py` | `npm run build` plus `git add -A src/world_engine/cockpit/static`, in the commit that changes bytes under `frontend/src`, in both briefs (R-28) |
| `claude_md_contract.py` | brief A's two texts: +223 characters, three lines of 98/99/23, `creation_island.py` exists on disk, no `TICKET-`/`BRIEF-` token inside the Invariants section (R-30) |
| `decisions_index.py` | both ADR headers match `STRICT_HEADER`; `gen_decisions_index.py` is re-run in the same commit (R-29) |
| `pipeline_state.py` | the ticket carries the 11 required fields, one `### Machine-checkable` and one `### Live` heading, and one arrow per Machine line (R-31) |
| `corpus_gate.py` | every check above, plus the 110 already green; `WORLD_ENGINE_ENV=test` set for the run (R-34) |

## Named deferrals introduced by this lot

- **D-0088-rule6-alias.** Rule 6 recognizes `svelteMount(` only; the
  docstring stops claiming a `mount(`-from-`svelte` form (R-09, R-11).
  *Reactivate when*
  `grep -rlE "import\s*\{[^}]*\b(mount|hydrate)\b[^}]*\}\s*from\s*['\"]svelte['\"]" frontend/src`
  lists a file other than `frontend/src/main.js`,
  `frontend/src/creation/mount.js` and `frontend/src/graph/mount.js`.
- **D-0088-rule11-unrouted.** Rule 11 keeps its `:533` gap: a non-routed
  `primaryAction` object with no `createPanel` field passes (R-09).
  *Reactivate when*
  `grep -n "primaryAction: {" frontend/src/creation/tabs.js | grep -v "triggerPrimaryAction("`
  prints a line.
- **D-0088-one-entity-per-subject.** The worklist binds all of a subject's
  facts to one entity, as the sheet binds one entity per row (R-23).
  *Reactivate when*
  `SELECT COUNT(*) FROM (SELECT fp.fact_id FROM fact_participant fp JOIN knowledge k ON k.fact_id = fp.fact_id GROUP BY fp.fact_id HAVING COUNT(DISTINCT fp.entity_id) > 1)`
  returns more than 0 on the production database.

## Amendments

None.
