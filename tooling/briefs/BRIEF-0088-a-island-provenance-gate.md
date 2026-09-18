# BRIEF 0088-A — "Island provenance gate"

Lot: LOT-0088-greenfield-creation-island.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Re-verify each before the first edit. **If any has moved, STOP and report**
— this is a confirmation that `main` has not drifted since drafting, not a
discovery pass.

1. **The base.** On `ticket/0088`, cut from `main`:
   `git merge-base --is-ancestor ced51c1 HEAD` exits 0. If the MR was
   squashed or rebased, the alternative form is
   `git diff --quiet ced51c1 HEAD -- frontend/src/creation tooling/verify/checks/creation_island.py tooling/verify/checks/page_contract.py src/world_engine/subject_resolve.py src/world_engine/cockpit/crud/knowledge.py`.
2. `tooling/verify/checks/creation_island.py:107` -> `INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "legacy.html"`.
3. `creation_island.py:109-116` -> `ENTRY_RE` matches `containerId`,
   `component`, `migratedBy`, `retiredPrefixes` in that order, then `})`.
4. `creation_island.py:229` -> `re.findall(r"'([^']*)'", prefixes_src)`.
5. `creation_island.py:582` -> `html = INDEX_HTML.read_text(...) if INDEX_HTML.is_file() else ""`, and a second read of the same file at `:432`.
6. `creation_island.py:604-617` -> the verdict requires
   `shape_count == len(entries)`, `retired_count == len(entries)` and
   `action_count == 8`; `_report_and_exit(counts)` is at `:129-140`.
7. `frontend/src/creation/registry.js:28` -> `export const CREATION_ISLANDS = Object.freeze({`;
   `:511` -> `});`; 15 `migratedBy:` lines at `:32, 38, 65, 277, 290, 303,
   350, 359, 378, 393, 416, 455, 471, 487, 505`, each indented four spaces.
8. `registry.js:19-27` -> the field block that says the fields are
   cross-referenced "against index.html", ending with `*/` at the end of
   `:27`; `:1-18` is the intro plus the BRIEF-0058-e paragraph plus a blank
   line.
9. `frontend/src/creation/mount.js:46` -> one line,
   `const COMPONENTS = { constructeur: Constructeur, ... , queueBatchBar: QueueBatchBar };`,
   15 keys; `:51` holds the regex literal `/[&<>"']/g`; `:91` holds
   `svelteMount(Component, { target: node, props: { legacyDoc: node.ownerDocument } })`.
10. `frontend/src/creation/Creation.svelte` -> exactly one `<script>` block,
    four static imports, none with a `.svelte` specifier, the only `svelte`
    clause being `{ onMount }`.
11. `CLAUDE.md:407` -> `│   └── src/creation/         # Svelte islands + review-tree; registry.js GROWS as surfaces migrate`;
    `:335-336` -> the "Every Création page is a `CREATION_TABS` registry
    entry …" invariant; the file is 34 100 characters.
12. `tooling/standards/ARCHITECTURE_DECISIONS.md:11237` -> the
    "**The island registry GROWS.**" paragraph; the file ends with `---`, a
    blank line and `*Co-built with Claude, June 2026.*`.
13. `python tooling/verify/checks/creation_island.py` prints, today:
    `PASS: creation_island — 15 island(s) registered, 15 retired legacy prefix set(s) confirmed gone, 8 mount-action identifier(s) confined, 11 island primaryAction(s) wired`.

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

## Contracts

This brief produces C-01 through C-06. It consumes none it does not produce.

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

## Context

`CREATION_ISLANDS` is a migration ledger: rule 2 requires a non-empty
`retiredPrefixes` of every entry, so a surface with no legacy predecessor
cannot register, and BRIEF-0087-d stopped there (AMENDMENT-0087-2, `K3`).
This brief makes the registry record provenance instead of assuming it, and
closes the two holes the RECON found next to it: a registry key whose
`COMPONENTS` line is missing renders an empty tab with every gate green
(R-12), and a tab whose component `Creation.svelte` imports directly bypasses
the island seam entirely (R-14). Brief B then lands the first
`origin: 'new'` surface; nothing else in the lot depends on this one.

## Scope IN

Three commits. Items are exhaustive; where a text must be copied verbatim it
is given in full and the executor copies it rather than paraphrasing.

### Commit 0 — baseline, before any edit

1. Record the baseline: `python tooling/verify/checks/corpus_gate.py`. If
   `day_mutations.py` reports `CRASH` naming `WORLD_ENGINE_ENV`, set
   `$env:WORLD_ENGINE_ENV = "test"` in the shell and re-run; report which
   form was used. Expected: `110 check(s) discovered, 110 executed, 110
   passed`.
2. Confirm `git status` shows nothing but the four artifacts Nia deposited
   (`tooling/tickets/TICKET-0088-greenfield-creation-island.md`,
   `tooling/lots/LOT-0088-greenfield-creation-island.md`,
   `tooling/briefs/BRIEF-0088-a-island-provenance-gate.md`,
   `tooling/briefs/BRIEF-0088-b-subject-worklist-panel.md`), already
   committed by her deposit commit. Any other modified file: list it and
   STOP.

### Commit 1 — the gate and the registry, one atomic commit

The old parser cannot read `origin` and the new one requires it, so
`creation_island.py`, `registry.js` and the rebuilt `static/` land together.

3. **Rename the constant.** `INDEX_HTML` becomes `LEGACY_HTML` at
   `creation_island.py:107`, same path, and every reference and message that
   names it follows.
4. **Read the document once.** In `main()`, replace the `:582` expression
   with
   `html = LEGACY_HTML.read_text(encoding="utf-8") if LEGACY_HTML.is_file() else None`,
   pass `html` to rule 7 and to rule 8, and delete rule 8's own read at
   `:432`. Rule 8 keeps its meaning: with `html` `None` the legacy document
   contributes no survivor, and the rule still counts 8.
5. **Add `_strip_js_comments(text, fail, label)`** exactly as C-02
   specifies — three parameters, in every call and every mention.
6. **Replace `_parse_registry`** with the grammar of C-01 rule 1, operating
   on the stripped text. It returns the declared items in source order, each
   a key plus its fields or `None` when the entry is malformed, and it
   records a failure for every malformed entry naming the key and, where the
   fault is a field, the field.
7. **Rewrite `_rule2_shape`** as C-01's field-set table: per-origin closed
   sets, `^TICKET-\d{4}$` on `migratedBy`/`createdBy`, non-empty
   `containerId`/`component`, a non-empty `retiredPrefixes` whose items all
   match `^[A-Za-z_$][A-Za-z0-9_$]*$`, no duplicate key. It returns the
   conforming entries as the mapping rules 3, 4, 5, 9 and 11 already
   consume, with `origin` added.
8. **Rewrite rule 7** as `(migration_count, retired_count)`: migration
   entries only; zero migration entries is a failure naming the ledger; an
   absent document while migration entries exist is a failure stating that
   absence cannot be proven; `new` entries are never examined. The per-prefix
   search keeps its current form,
   `re.compile(rf"function {re.escape(prefix)}\w*\(")`.
9. **Add rule 12** exactly as C-03 specifies, over the stripped `mount.js`.
10. **Add rule 13** exactly as C-04 specifies, over `Creation.svelte`.
11. **Apply the verdict and the PASS line of C-05**, including the rule that
    every unmet condition records a failure message before reporting, so the
    PASS path is never reached with absent counts.
12. **Add the self-test**, run as the first statement of `main()`, reading
    no file, each case using its own local collector and expecting *at least
    one* message naming the refused thing (C-06). Split it across several
    module-level functions so no function exceeds 80 lines; the case data
    lives in module-level literals. Cases, each a separate expectation:
    - a valid registry with one `migration` and one `new` entry, fields out
      of order, and a `//` comment containing an apostrophe inside the
      prefix list — no message, and the parsed prefix list equals the
      expected list exactly;
    - `new` carrying `retiredPrefixes`; `new` carrying `migratedBy`;
    - `origin` removed; `origin` with an unknown value;
    - `retiredPrefixes: []`; a double-quoted prefix; a prefix that is not
      identifier-shaped;
    - an unknown field; a value that is a bare identifier;
      `createdBy: 'T-88'`;
    - a duplicate top-level key; an entry not wrapped in `Object.freeze`;
    - an unterminated string (the stripper fails and returns `None`);
    - rule 7: one surviving `function <prefix>(` hit; a clean document;
      `html=None` with a migration entry; a registry of `new` entries only;
    - rule 12: a valid `mount.js` including a regex literal; a missing key;
      an extra key; a value that is not an imported identifier; a path
      mismatch; an unused `.svelte` import; an import that appears only
      inside a comment (which must pass);
    - rule 13: a valid document; a `.svelte` import; a dynamic `import(`; a
      `mount` import from `'svelte'`; `<Foo />`; `<svelte:component>`;
      `<lib.Foo />`; and each of these inside a comment only (which must
      pass).
    An unexpected result calls `fail("self-test: <case>: …")` on the
    module-level collector.
13. **Rewrite the docstring's numbered rules from the code** (`:44-91`),
    adding rules 12 and 13. Rule 6 states exactly what is executed —
    `\bsvelteMount\(` in `creation/mount.js` and `graph/mount.js` only — and
    names **D-0088-rule6-alias**. Rule 11 keeps its pairing description
    unchanged and names **D-0088-rule11-unrouted** for the non-routed
    object with no `createPanel` field; it does **not** say that an object
    "must call" `triggerPrimaryAction`. Keep `:1-10`, both amendment
    paragraphs (`:12-24`, `:26-36`) and the idiom paragraph (`:38-42`) as
    history, and append to the end of the BRIEF-0059-l paragraph, after
    "the migration only partly happened.", this sentence verbatim:

    ```
    (As executed, the two identifiers are imported only by Creation.svelte
    and wired into tabs.js through setMountActions -- see rule 8.)
    ```

    Then add one new paragraph opening `TICKET-0088 amendment
    (BRIEF-0088-a):` that states the four changes: the registry is parsed
    from comment-stripped text with free field order, every entry declares
    its `origin` with a closed field set per origin, rule 7 covers migration
    entries only and fails closed on a missing document, and rules 12 and 13
    close the `COMPONENTS` and direct-render gaps.
14. **`registry.js`, the entries.** Insert `origin: 'migration',` on its own
    line, indented like its neighbours, immediately **before** each of the 15
    `migratedBy:` lines. Do this by script over the file rather than by hand,
    and verify afterwards that exactly 15 lines were added and that the file
    still parses to 15 entries and 297 prefixes.
15. **`registry.js`, the header.** Keep `:1-18` unchanged. Replace `:19-27`
    with this text verbatim — every line starts with exactly three spaces,
    and one blank line follows the first paragraph:

    ```
       TICKET-0088 amendment (BRIEF-0088-a): the registry also records
       surfaces that were CREATED as islands, with no legacy predecessor.
       Each entry declares its `origin` -- 'migration' for a surface that
       moved (the ledger described above), 'new' for one that did not.
       Nothing is removed once added, whichever the origin.

       tooling/verify/checks/creation_island.py parses this literal
       (comments ignored, field order free) and cross-references every
       field against the filesystem, Creation.svelte, tabs.js, mount.js
       and, for migration entries, src/world_engine/cockpit/legacy.html.
       The field set is closed per origin:
         containerId:     id of the Creation.svelte element the component
                          mounts into (both origins)
         component:       Svelte component filename, relative to this
                          directory (both origins)
         origin:          'migration' | 'new'
         migratedBy:      migration only -- the ticket that performed the
                          migration (^TICKET-\d{4}$)
         retiredPrefixes: migration only -- the legacy function-name
                          prefixes the migration retired; the check proves
                          zero `function <prefix>...(` declarations remain
                          in legacy.html, for EVERY prefix in the list
         createdBy:       new only -- the ticket that created the surface
                          (^TICKET-\d{4}$)
       Every key also needs a COMPONENTS entry in mount.js. */
    ```

16. **Rebuild.** `npm run build` in `frontend/`, then
    `git add -A src/world_engine/cockpit/static`. Bytes changed under
    `frontend/src` make the committed build stale otherwise (R-28).
17. **Commit** `creation_island.py`, `registry.js` and
    `src/world_engine/cockpit/static/` together. Run `/review-step` and
    `/close-step`.

### Commit 2 — the record

18. **Append one ADR entry** to `tooling/standards/ARCHITECTURE_DECISIONS.md`,
    immediately before the closing `---` / footer block, separated by one
    blank line, with this header verbatim:

    ```
    ## CREATION ISLANDS DECLARE THEIR ORIGIN — MIGRATION OR NEW (BRIEF-0088-a, no schema change)
    ```

    The entry covers, in prose of the same register as the entry at
    `ARCHITECTURE_DECISIONS.md:15501-15517`:
    - what the registry now is, superseding the `:11237` sentence **on the
      record** by quoting it — "the record of what has MOVED: one entry per
      migrated surface, never removed once added" — and replacing it with:
      a record of every Creation island and its origin, never removed once
      added, whichever the origin. The old entry is not edited.
    - `A1b`'s closed field sets, and why `A1a` (a `new` entry carrying
      `migratedBy` and `retiredPrefixes: []`) was rejected: it records a
      migration that never happened.
    - `A2` (a second registry) and `A3` (retiring rules 2 and 7) as
      rejected, each with its reactivation condition from the lot.
    - `D3`: rule 7 migration-only and fail-closed, rule 12's `COMPONENTS`
      agreement, rule 13's no-mount rule, and what each closes.
    - the self-test, and why it lives inside the check (`corpus_gate.py`
      runs every `*.py` in `checks/`).
    - the two named deferrals **D-0088-rule6-alias** and
      **D-0088-rule11-unrouted**, with their grep reactivation conditions
      verbatim from the lot.
19. **Regenerate the index**: `python tooling/glue/gen_decisions_index.py`.
20. **`CLAUDE.md`, line 407**, replaced verbatim (99 characters):

    ```
    │   └── src/creation/         # Svelte islands + review-tree; registry.js: islands and their origin
    ```

21. **`CLAUDE.md`, after line 336**, insert verbatim (98, 99 and 23
    characters):

    ```
    - Every Création surface mounts as a `CREATION_ISLANDS` entry declaring its origin (`migration` or
      `new`) through `mount.js` alone; `Creation.svelte` imports and renders no component — enforced by
      `creation_island.py`.
    ```

22. **Commit** the three documents. Run `/review-step` and `/close-step`.

## Scope OUT

- **The worklist panel, its tab, its container, its component and its
  registry entry.** All of brief B. This brief adds no `origin: 'new'` entry
  and no sixteenth island.
- **`page_contract.py`.** Its `TAB_KEYS` and its PASS wording are brief B's
  (`J1`).
- **Repairing rule 6's alias blindness and rule 11's `:533` gap.** Both are
  named deferrals; the docstring records them, the code does not change.
- **`page_contract.py`'s own `INDEX_HTML` constant**, still pointing at
  `legacy.html` under an old name. Observed, left alone.
- **`Registre.svelte:20-21`**, whose header still says islands render
  "inside the legacy iframe document". Observed, left alone.
- **Retiring rules 2 and 7, or touching `legacy.html`.** `A3` is rejected
  while the document is live (R-02).
- **Any backend file, any route, any schema artifact.** None is touched.
- **AMENDMENT-0087-3, TICKET-0087, LOT-0087 and BRIEF-0087-e.** Another
  session's work (`H1`); do not edit them, do not deposit them.
- **The 16 prefixes the old parser never examined.** They are examined from
  this commit on; none has a survivor. Nothing to repair.

## Invariants to defend

- **Structural over disciplinary.** The provenance distinction must be
  impossible to get wrong silently: an entry that does not parse is a
  FAILURE, never an invisible entry (C-01). This is the invariant the old
  positional parser broke.
- **Fail-closed, vacuous-proof.** Zero declared entries, zero migration
  entries, an absent legacy document, an empty `COMPONENTS`, zero tags in
  `Creation.svelte` — each is a FAILURE, never a trivially satisfied
  comparison.
- **"Every Création page is a `CREATION_TABS` registry entry rendered by the
  generic dispatcher"** (`CLAUDE.md:335-336`). Rule 13 is what makes the
  second half of that sentence enforced rather than conventional; the new
  bullet states it and names the check.
- **History is sacred.** The docstring's amendment paragraphs, the
  `registry.js` header's first two paragraphs, and the ADR's `:11237`
  paragraph are supplemented, never rewritten.

## Decision rights

**STOP:**
- Any Mini-RECON anchor that has moved.
- P-1 fails in both forms.
- The rewritten parser cannot read the real `registry.js` after step 14
  without loosening a rule stated in C-01 — that is an amendment, never a
  local relaxation.
- A `CLAUDE.md` or ADR edit cannot satisfy `claude_md_contract.py` or
  `decisions_index.py` with the texts given in items 18-21.
- Any finding touching a `CLAUDE.md` invariant or a `danger_class` of this
  ticket, listed here or not.

**ADAPT (act as stated, then report):**
- A line number in an anchor has shifted while the content matches: anchor
  by content, proceed.
- A file's line endings differ from the repository's (`CLAUDE.md`,
  `ARCHITECTURE_DECISIONS.md` and `creation_island.py` are CRLF in the
  Windows working tree, everything under `frontend/` is LF): preserve each
  file's existing endings, and never let an edit convert a whole file.
- `npm run build` exits 0 with warnings: proceed, quote the warnings.
- A `migratedBy:` line's indentation differs from four spaces: match the
  indentation of the line the insertion precedes.
- The self-test takes the check past 1 s: keep it, report the measured time.
- `corpus_gate.py` reports `CRASH` for `day_mutations.py` naming
  `WORLD_ENGINE_ENV`: set `$env:WORLD_ENGINE_ENV = "test"` and re-run.

**REPORT-ONLY:**
- Rule 11's `:533` gap and rule 6's alias blindness (both deferred).
- The 16 previously unexamined prefixes, now examined and all clean.
- `page_contract.py`'s stale `INDEX_HTML` constant and `Registre.svelte`'s
  stale header comment.
- Anything else found in the files opened here.

**Default clause:**

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/creation_island.py` exits 0 and its last
      line is exactly:
      `PASS: creation_island — 15 island(s) registered (15 migration, 0 new), 15 retired legacy prefix set(s) confirmed gone, 15 component binding(s) agreed, 8 mount-action identifier(s) confined, 11 island primaryAction(s) wired, Creation.svelte mounts no component`
- [ ] Each of these four breaks, applied one at a time to the working tree
      and reverted with `git checkout --` immediately after, makes the check
      exit 1 with a message naming the item: (a) deleting one
      `origin: 'migration',` line — names that entry key; (b) renaming
      `src/world_engine/cockpit/legacy.html` away — states that absence
      cannot be proven; (c) deleting `queueBatchBar: QueueBatchBar` from
      `mount.js:46` — names `queueBatchBar`; (d) adding
      `import Foo from './Foo.svelte';` to `Creation.svelte`'s script —
      names that specifier.
- [ ] The self-test is reached before any file is read: running the check in
      a directory where `frontend/src/creation/registry.js` is absent still
      produces the self-test's verdict and then the file-missing failure.
- [ ] `python tooling/verify/checks/corpus_gate.py` prints
      `110 check(s) discovered, 110 executed, 110 passed`.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py`,
      `static_asset_freshness.py`, `claude_md_contract.py` and
      `decisions_index.py` each exit 0.
- [ ] `python tooling/verify/run.py --ticket TICKET-0088-greenfield-creation-island`
      is green.
- [ ] `git status` is clean, and the work is in exactly two commits after
      Nia's deposit commit.
- [ ] `grep -c "origin: 'migration'," frontend/src/creation/registry.js`
      prints 15, and `grep -n "index.html" frontend/src/creation/registry.js`
      prints nothing.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — the new entry (item 18).
- `tooling/standards/DECISIONS_INDEX.md` — regenerated (item 19).
- `CLAUDE.md` — items 20 and 21.
- `frontend/src/creation/registry.js` header and
  `tooling/verify/checks/creation_island.py` docstring — items 13 and 15;
  this brief **is** their doc update.
- No schema changelog entry: no schema change.
