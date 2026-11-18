# BRIEF 0131-A — "error-message"

Lot: LOT-0131-error-message.md (authoritative on conflict)
Depends on: nothing in this lot
Amended by: AMENDMENT-0131-01 (R-05, Scope IN 5a, Done means)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `frontend/src/creation/sheetRequest.svelte.js:33` -> `if (!res.ok) throw new Error(data.detail || JSON.stringify(data));`
- The FE2 scan of the lot (three regexes, `.js` / `.svelte` under
  `frontend/src`, `joueur/` excluded) matches exactly the 33 lines of R-01,
  R-02 and R-03, at those line numbers.
- `frontend/src/joueur/joueur.svelte.js:37` -> `const detail = body && typeof body.detail === 'string' ? body.detail : \`Erreur ${response.status}\`;`
- `tooling/verify/checks/player_shell.py:134-135` -> `_allowed_import` accepts `svelte`, `svelte/...`, or `./` without `..`.
- `ls frontend/src/lib` -> `router.js`, `serverState.svelte.js` only.
- `.claude/rules/frontend.md` ends with INV-55 (lines 40-42); the highest
  INV in `.claude/rules/` is INV-68.
- `grep -rn "\"node\"\|'node'" tooling/verify/checks` -> empty.
- `tooling/standards/ARCHITECTURE_DECISIONS.md:21004-21006` -> `---`, blank, `*Co-built with Claude, June 2026.*`.

## Facts carried

Measured on `main` at `e568908` (PR #158).

### R-01 -- the 23 sites that throw `new Error(<body>.detail || <fallback>)`
Opened: `grep -rnE "throw new Error\(\w+\.detail \|\|" frontend/src`
Finding (paths under `frontend/src/`, raw):
```
creation/ConversationWindowConfig.svelte:31 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/DiscDetailsEditor.svelte:35 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/DoorsEditor.svelte:67 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/EntityList.svelte:233 | if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
creation/Evenements.svelte:62 | if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
creation/GeneratePanel.svelte:32 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/GeometryEditor.svelte:77 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/MembershipsPanel.svelte:39 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/PricingEditor.svelte:36 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/QueueFilters.svelte:36 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/Region.svelte:81 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/Registre.svelte:44 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/RoomBatch.svelte:81 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/competences.svelte.js:123 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/creationRules.svelte.js:25 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/dashboard.svelte.js:52 | throw new Error(data.detail || res.statusText);
creation/factionPanel.svelte.js:28 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/linkAgent.svelte.js:82 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/locationType.js:51 | if (!postRes.ok) throw new Error(postData.detail || JSON.stringify(postData));
creation/npcAgent.svelte.js:96 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/prompts.svelte.js:82 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/queue.svelte.js:59 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
creation/sheetRequest.svelte.js:33 | if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
```
Each body comes from `res.json().catch(() => ({ detail: res.statusText }))`
on the line before (`sheetRequest.svelte.js:32`, `dashboard.svelte.js:51`,
`locationType.js:50` read for the three shapes). A non-string `detail` is
truthy, so `new Error(<object>)` reads `[object Object]`.
Consequence: each line becomes `throw new Error(errorMessage(<body>,
<fallback>))`, the fallback expression kept verbatim.

### R-02 -- the 9 sites that keep `detail` only as a string
Opened: `grep -rnF "if (body && typeof body.detail === 'string') msg = body.detail;" frontend/src`;
full context read at `graph/consumers/relations.js:36-44` (the other nine
blocks are the same nine lines, read in each file)
Finding (raw, `joueur/` listed for completeness, see R-04):
```
creation/Constructeur.svelte:59
creation/Sheet.svelte:152
creation/WorldSheet.svelte:72
creation/pcDrafts.svelte.js:15
creation/sheetState.svelte.js:77
creation/tabs.js:112
creation/worldCrud.svelte.js:55
graph/consumers/lieux.js:39
graph/consumers/relations.js:40
```
Each block: `let msg = \`<path or METHOD path> -> ${res.status}\`;` then, in
a `try`, `const body = await res.json();` and the matched line; then
`throw new Error(msg);`. An object or a list leaves `msg` at the status
line: the server's reason is lost.
Consequence: the matched line becomes `msg = errorMessage(body, msg);`.

### R-03 -- the observation launch
Opened: `frontend/src/observation/observation.svelte.js:84-123`
Finding: `startRun` fetches directly (comment 84-88: `api()` would collapse
the readiness gate's `{failures: [...]}` to `[object Object]`). Line 113:
`const failures = (data.detail && data.detail.failures) || [String(data.detail || res.statusText)];`.
A non-`failures` object still renders `[object Object]`.
Consequence: only `[String(data.detail || res.statusText)]` becomes
`[errorMessage(data, res.statusText)]`; the `failures` branch stays (it
lists each failure on its own line).

### R-04 -- the player shell
Opened: `frontend/src/joueur/joueur.svelte.js:28-41`;
`tooling/verify/checks/player_shell.py:14-16, 134-147`
Finding: `call()` throws `body && typeof body.detail === 'string' ?
body.detail : \`Erreur ${response.status}\``: never `[object Object]`.
PSH3: no import under `frontend/src/joueur/` resolves outside that folder
(`_allowed_import`: `svelte`, `svelte/...` or `./` without `..`).
Consequence: `joueur/` is untouched and excluded from the new check's scan
by folder. A copy of `errorMessage` inside `joueur/` would be a second copy:
not made (ticket, Carried forward).

### R-05 -- `frontend/src/lib/` and its import form
*Corrected by AMENDMENT-0131-01 (identifier `errorMessage` bound in `EntityList.svelte`).*
Opened: `ls frontend/src/lib`; `frontend/src/observation/observation.svelte.js:22`;
`frontend/src/journee/Journee.svelte:17-18`;
`frontend/src/creation/tabs.js:75-77`; `frontend/src/graph/consumers/lieux.js:23`
Finding: `lib/` holds `router.js` and `serverState.svelte.js`. Callers
import with a relative path: `import { serverState } from
'../lib/serverState.svelte.js';` (observation, Journee),
`import { replace } from '../lib/router.js';` (tabs.js:77). From
`graph/consumers/`, the parent of `creation/` is reached with `../../`
(`lieux.js:23`).
Consequence: `creation/*` and `observation/*` import
`'../lib/errorMessage.js'`; `graph/consumers/*` import
`'../../lib/errorMessage.js'`. Files with no import today (enumerated:
`ConversationWindowConfig.svelte`, `DiscDetailsEditor.svelte`,
`DoorsEditor.svelte`, `GeometryEditor.svelte`, `PricingEditor.svelte`,
`creationRules.svelte.js`, `factionPanel.svelte.js`, `linkAgent.svelte.js`,
`prompts.svelte.js`, `queue.svelte.js`, `sheetRequest.svelte.js`) take it as
the first statement after their leading comment (in a `.svelte`, the first
line of its single `<script>` block's body).

*Corrected by AMENDMENT-0131-01.* `grep -nw errorMessage` over the 33 files
on `e568908`: only `creation/EntityList.svelte`, lines 68 (`let errorMessage
= $state('');`), 120, 135, 152, 168 (`errorMessage = err.message;`) and 355
(`<div class="empty">{errorMessage}</div>`). `loadError` is free there; no
check names either identifier; `creation_layout.py` reads `EntityList.svelte`
for `selectGerm(` (CL3) and `selectPcDraft(`, `Soumis (` (CL5) only.
Consequence: the local state is renamed `loadError` (Scope IN 5a).

### R-06 -- the checks that read the edited files
Opened: for each of the 33 file names, `grep -rln <name> tooling/verify/checks`;
then each of `detail ||`, `JSON.stringify(data)`, `JSON.stringify(result)`,
`typeof body.detail`, `res.status}`, `keep the status-based message`,
`function api`, `errorMessage` with `grep -rnF` over `tooling/verify/checks`
Finding: 32 checks name at least one edited file (e.g. `tabs.js` is read by
13 checks, `Sheet.svelte` by 14). The literal grep returns, raw:
```
== detail ||
== JSON.stringify(data)
== JSON.stringify(result)
== typeof body.detail
== res.status}
== keep the status-based message
== function api
== errorMessage
```
-- empty for every literal. `frontend/src/lib` is named only by
`legacy_mount.py:33` (`router.js`) and `review_component.py:27`
(`router.js`). The import rules among them: `creation_island.py` parses
`creation/mount.js` imports only (990-1010); `review_component.py:132`
matches imports of `review/registry.js` only; `player_shell.py` PSH3 scans
`joueur/` only.
Consequence: no existing check asserts the replaced text or forbids the
new import. No file moves or is renamed.

### R-07 -- the invariant corpus
Opened: `.claude/rules/frontend.md` (42 lines, 2 030 characters; INV-55 at
40-42, last line of the file); `tooling/verify/checks/claude_md_contract.py:1-40`;
`.claude/rules/character-creation.md:36`
Finding: rule files <= 4 000 characters, lines <= 100 characters, every
Invariants bullet starts `- **INV-NN**` and ends `-- enforced by` and a
`` `<check>.py` `` under `tooling/verify/checks/`; ids contiguous; no
`TICKET-\d` / `BRIEF-\d` in an Invariants section. Highest id: INV-68.
`frontend.md` paths cover `frontend/src/**/*.js` and `**/*.svelte`.
Consequence: INV-69 is appended after INV-55 in `frontend.md`.

### R-08 -- writing a check; Node
Opened: `.claude/rules/verify-checks.md`; `tooling/verify/checks/effect_self_write.py:1-60`;
`grep -rn "\"node\"\|'node'" tooling/verify/checks`; `which node`
Finding: fail-closed, `FAILURES` / `fail()`, `FAIL:` lines and exit 1, one
`PASS: <name> -- ...` line otherwise; `ROOT = parents[3]`; 15-second budget
under `corpus_gate.py`; every rule proven by a named mutation. No existing
check runs Node (grep empty). Node v22 is on the Claude Code machine
(`/opt/node22/bin/node`); Nia's machine runs `npm run build`.
Consequence: FE4 is the first check to run Node, through
`shutil.which("node")`; Node absent is a FAILURE (fail-closed), never a
skip.

### R-09 -- the build
Opened: `.claude/rules/frontend.md:9-12`; `tooling/verify/checks/frontend_build_fresh.py:1-30`
Finding: any `frontend/` edit is rebuilt (`npm run build` in `frontend/`)
and `src/world_engine/cockpit/static/` committed with it; the check
compares the source hash with `.build-manifest.json`.
Consequence: the brief rebuilds and commits the output.

### R-10 -- decisions registry and file map
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:21004-21006`
(`---`, blank, `*Co-built with Claude, June 2026.*`);
`tooling/verify/checks/file_map.py:1-15`
Finding: an entry goes above the footer's `---`. `FILE_MAP.md` lists every
Python module of `tooling/verify` with its docstring's first sentence; FM3
fails on a stale map (`python tooling/glue/gen_file_map.py`).
Consequence: one entry above line 21004; the map regenerated.

### R-11 -- the legacy document
Opened: `src/world_engine/cockpit/legacy.html:655-660, 1226`
Finding: `if (!res.ok) throw new Error(data.detail || JSON.stringify(data));`
(660) and `throw new Error(err.detail || 'Request failed');` (1226). Not
under `frontend/src`, not a Vite module.
Consequence: out of scope (ticket, Carried forward).

### R-12 -- module budget
Opened: `wc -l` of the 33 files; `tooling/verify/checks/module_budget.py:55-59`
Finding: the largest are `creation/Sheet.svelte` (906) and
`creation/tabs.js` (898); `FRONTEND_MAX_LINES = 1000` over
`FRONTEND_SRC = ROOT / "frontend" / "src"` (`module_budget.py:55, 59`).
Consequence: every edit adds at most one import line and replaces one line:
no budget risk.

## Contracts

### C-01 -- `errorMessage`
Produced by: BRIEF-0131-A   Consumed by: BRIEF-0131-A (33 sites), the check
Signature: `export function errorMessage(body, fallback)` in
`frontend/src/lib/errorMessage.js`, a plain ES module (no `$state`, no
import).
Return: a string.
- `body.detail` a non-empty string -> it.
- `body.detail` a list -> each item with a string `msg` becomes
  `<loc without "body", joined by ".">` + ` : ` + `msg` (just `msg` when
  that path is empty); lines joined by ` ; `. No such item -> `fallback`.
- `body.detail` an object with a non-empty string `message` -> `message`.
- otherwise, `body.detail` an object with a `failures` list -> its non-empty
  strings joined by ` ; `; none -> `fallback`.
- anything else (no body, `null`, no `detail`, empty string, other object)
  -> `String(fallback)`.
Never returns a string holding `[object Object]` when `fallback` does not.

Verbatim module (the executor copies it):
```js
/* The one reader of a failed request's body for the creator's shell.
   FastAPI answers `detail` as a string, as an object (`{message, ...}`,
   `{failures: [...]}`) or, for a validation error, as a list of
   `{loc, msg}`. Each becomes readable text; anything else becomes
   `fallback`. Never "[object Object]". */

function validationLine(item) {
  if (!item || typeof item.msg !== 'string') return null;
  const where = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : '';
  return where ? `${where} : ${item.msg}` : item.msg;
}

export function errorMessage(body, fallback) {
  const detail = body && typeof body === 'object' ? body.detail : undefined;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const lines = detail.map(validationLine).filter(Boolean);
    if (lines.length) return lines.join(' ; ');
  } else if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message) return detail.message;
    if (Array.isArray(detail.failures)) {
      const failures = detail.failures.filter((f) => typeof f === 'string' && f);
      if (failures.length) return failures.join(' ; ');
    }
  }
  return String(fallback);
}
```
Run under Node v22 against the FE4 cases before delivery (gate (e)).

### FE4 / FE2 case tables (lot gate (b), verbatim)

(b) Case table -- `errorMessage(body, fallback)` (run under Node v22):

| body | fallback | result |
|---|---|---|
| `{detail:'Le nom est requis.'}` | `'fb'` | `Le nom est requis.` |
| `{detail:{message:'day narration rejected by judge: x', reason:'x', offending_words:[], prose:'p'}}` | `'fb'` | `day narration rejected by judge: x` |
| `{detail:[{type:'missing', loc:['body','declared_action'], msg:'Field required', input:{}}]}` | `'fb'` | `declared_action : Field required` |
| `{detail:{failures:['a','b']}}` | `'fb'` | `a ; b` |
| `{detail:{weird:1}}` | `'{"detail":{"weird":1}}'` | `{"detail":{"weird":1}}` |
| `null` | `'/api/x -> 500'` | `/api/x -> 500` |
| `{detail:''}` | `'fb'` | `fb` |
| `{detail:[{foo:1}]}` | `'fb'` | `fb` |

Case table -- FE2's scan (regexes `\.detail\s*\|\|`,
`typeof\s+\w+\.detail\s*===`, `String\(\s*\w+\.detail`) over `.js` /
`.svelte` under `frontend/src`, `joueur/` excluded, on `e568908`: 151 files
scanned, 33 lines matched = R-01 (23) + R-02 (9) + R-03 (1). After the
brief: 33 -> 0. `joueur.svelte.js:37` would match and is out by folder.

## Context

Nia reads « Objet : objet » where an error's reason should be (`[object
Object]`): the creator's shell builds error messages from a response's
`detail` in 33 places, and an object or a list renders as that, or is
dropped. N1 puts one reader in `frontend/src/lib/` and makes the rule
structural. This runs before TICKET-0128, whose day-chain failures must be
readable.

## Scope IN

1. Create `frontend/src/lib/errorMessage.js` with C-01's verbatim module,
   nothing else in the file.
2. R-01's 23 lines: replace `throw new Error(<B>.detail || <F>)` by
   `throw new Error(errorMessage(<B>, <F>))`, where `<B>` is the body name
   on that line (`data`, `result`, `postData`) and `<F>` the fallback
   expression copied verbatim (`JSON.stringify(<B>)`, or `res.statusText`
   in `dashboard.svelte.js:52`). The `if (!res.ok)` / `if (!postRes.ok)`
   guard stays.
3. R-02's 9 lines: replace
   `if (body && typeof body.detail === 'string') msg = body.detail;` by
   `msg = errorMessage(body, msg);`. The surrounding `let msg = ...`, `try`,
   `catch` and `throw new Error(msg);` stay.
4. R-03: in `observation.svelte.js:113`, replace
   `[String(data.detail || res.statusText)]` by
   `[errorMessage(data, res.statusText)]`; the `(data.detail &&
   data.detail.failures) ||` part stays.
5. Each of the 33 files imports `{ errorMessage }` exactly once, by R-05's
   form: `import { errorMessage } from '../lib/errorMessage.js';` under
   `creation/` and `observation/`;
   `import { errorMessage } from '../../lib/errorMessage.js';` under
   `graph/consumers/`. Beside the file's existing imports; in a file with
   none (R-05's list), as the first statement after its leading comment
   (in a `.svelte`, the first line of its `<script>` body).
5a. (AMENDMENT-0131-01) In commit (1), before Scope IN 5's import, rename
   the identifier `errorMessage` to `loadError` in
   `frontend/src/creation/EntityList.svelte` on lines 68, 120, 135, 152,
   168 and 355, and nowhere else. This is a pure rename: no other character
   on those lines changes.
6. New check `tooling/verify/checks/frontend_error_message.py`, the
   `.claude/rules/verify-checks.md` idiom (R-08). Docstring first sentence:
   `G1 check: a failed request's body becomes text only through
   frontend/src/lib/errorMessage.js (TICKET-0131, BRIEF-0131-a).` Rules:
   - FE1 -- `frontend/src/lib/errorMessage.js` exists and holds
     `export function errorMessage(body, fallback)`.
   - FE2 -- no line of a `.js` / `.svelte` under `frontend/src`, outside
     `frontend/src/joueur/` and outside `lib/errorMessage.js`, matches
     `\.detail\s*\|\|`, `typeof\s+\w+\.detail\s*===` or
     `String\(\s*\w+\.detail`. Each hit is a FAIL naming file and line.
     Zero files scanned is a FAILURE.
   - FE3 -- every file outside `lib/` whose text holds `errorMessage(`
     imports it by a specifier ending `lib/errorMessage.js`; zero such files
     is a FAILURE.
   - FE4 -- behaviour. `shutil.which("node")` absent is a FAILURE. Write a
     temporary `.mjs` file (in `tempfile.TemporaryDirectory()`) that
     imports the module by its absolute `file://` URL
     (`pathlib.Path.as_uri()`), calls `errorMessage` on the eight rows of
     the lot's case table (gate (b)), and prints the results as one JSON
     array; run it with `subprocess.run([node, path], capture_output=True,
     text=True, timeout=10)`. A non-zero exit, unparsable output, a result
     different from the table's, or any result holding `[object Object]`
     is a FAIL naming the row.
7. Append to `.claude/rules/frontend.md`, after INV-55, verbatim, each line
   under 100 characters:
   ```
   - **INV-69** A failed request's body becomes the creator shell's error
     text only through `errorMessage` (`frontend/src/lib/errorMessage.js`);
     no other file under `frontend/src` outside `joueur/` reads `detail`
     into a message. -- enforced by `frontend_error_message.py`
   ```
8. `npm run build` in `frontend/`; commit `src/world_engine/cockpit/static/`
   and its manifest with the sources (R-09).
9. `tooling/standards/ARCHITECTURE_DECISIONS.md`: above line 21004's `---`,
   an entry `## TICKET-0131 -- one reader for a failed request's body
   (BRIEF-0131-a, no schema change)`: one paragraph (33 sites read `detail`
   themselves; an object or a list rendered `[object Object]` or lost the
   reason; `errorMessage` reads string, object `message`, `failures`,
   validation list; the player shell keeps its `call()` because PSH3 keeps
   its imports inside its folder; `legacy.html` untouched), then
   `**INV-69.**` with Scope IN 7's sentence, `Held in
   .claude/rules/frontend.md. Gate: frontend_error_message.py.`, then
   `Deferred: legacy.html's two sites; the player shell's call().`
10. `python tooling/glue/gen_file_map.py`; commit `FILE_MAP.md`.

Commits: (1) Scope IN 1-5 and 8; (2) Scope IN 6; (3) Scope IN 7, 9, 10.

## Scope OUT

- `frontend/src/joueur/` (R-04): no edit, no copy of `errorMessage` there.
- `src/world_engine/cockpit/legacy.html` (R-11).
- Any server route or the shape of any `detail`; the day chain itself
  (TICKET-0128).
- Rewording any message, or changing a fallback expression.
- Changing how observation lists `failures`.
- Merging the 33 local `api()` / fetch helpers into one: only the error
  text moves.
- A JavaScript test runner (FE4 runs Node directly).

## Invariants to defend

- INV-66 (`player-surface.md`) and PSH3: the player shell must stay
  untouched and import nothing outside its folder.
- INV-49 / INV-50 (`frontend.md`): no edit to `CREATION_TABS`,
  `CREATION_ISLANDS` or `creation/mount.js`.
- INV-55: no `$effect` body is edited.
- The build-freshness gate: the committed build matches the sources.

## Decision rights

STOP:
- An anchor does not hold.
- The FE2 scan finds a 34th line, or one of the 33 is not where R-01..R-03
  put it.
- An edit would need a change in `joueur/`, `legacy.html`, a route or a
  CREATION registry.
- `npm run build` fails.

ADAPT:
- A file of R-05's no-import list already gained an import: put the new
  import beside it, report.
- A `.svelte` file's `<script>` block opens with a comment: the import goes
  after that comment, report.
- FE4 exceeds 10 seconds on the machine: raise the subprocess timeout to
  14 seconds, report (corpus_gate's limit is 15).
- `claude_md_contract.py` flags a line of INV-69 over 100 characters: rewrap
  it, wording unchanged, report.

REPORT-ONLY:
- Another site under `frontend/src` builds an `Error` from a response body
  without reading `detail` (e.g. `res.statusText` alone).
- A check of R-06 reads a different line of an edited file than expected.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/frontend_error_message.py` PASS (FE1-FE4).
- [ ] `frontend_build_fresh.py`, `player_shell.py`, `module_budget.py`,
      `effect_self_write.py`, `file_map.py`, `claude_md_contract.py` PASS.
- [ ] Named mutations, each red then reverted:
      put `sheetRequest.svelte.js:33` back to
      `throw new Error(data.detail || JSON.stringify(data))` -> FE2;
      rename the export to `errorText` -> FE1 (and FE4);
      drop the import line from `creation/tabs.js` -> FE3;
      in `errorMessage.js`, delete the `detail.message` line -> FE4 (row 2);
      replace `return String(fallback);` by `return String(detail ?? fallback);` -> FE4 (row 5 holds `[object Object]`).
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` PASS.
- [ ] Live, on Nia's machine: Création › Monde, empty the name and save ->
      « Le nom est requis. »; Création and Journée otherwise unchanged.
- [ ] `grep -nw errorMessage frontend/src/creation/EntityList.svelte` ->
      only the import line and the line-233 call (AMENDMENT-0131-01).
- [ ] Live: Création, entity list. An error while loading still shows its
      text in the list's empty state.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`.claude/rules/frontend.md` (Scope IN 7), ARCHITECTURE_DECISIONS (9),
FILE_MAP (10). No schema change, no migration, no CLAUDE.md change (the
rule files' list is unchanged).
