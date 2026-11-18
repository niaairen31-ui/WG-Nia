# LOT — TICKET-0131 "error-message"

## Objective and cut

One reader, `errorMessage(body, fallback)` in
`frontend/src/lib/errorMessage.js`, turns a failed request's JSON body into
readable text for the creator's shell (N1). The 33 sites that read `detail`
themselves (R-01 to R-03) call it instead. A new check,
`frontend_error_message.py`, proves the function's behaviour by running it
under Node, and forbids the old patterns. INV-69 records the rule. The
player shell, the legacy document and every server route are untouched.
No schema change.

## Briefs in this lot

- A -- `error-message`: the function, the 33 call sites, the check,
  INV-69, the build.

## Dependency graph

One brief. TICKET-0131 runs before TICKET-0128 by Nia's decision (N1), not
by a dependency: nothing in 0128's lot reads this one.

## RECON

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

## Contract sheet

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

## Gate output

(a) Property trace
- 23 sites, their exact line and body name -> R-01, each file opened by the grep.
- `res.json().catch(() => ({ detail: ... }))` precedes them -> R-01, read in
  `sheetRequest.svelte.js:32`, `dashboard.svelte.js:51`, `locationType.js:50`.
- 9 string-only blocks and their `msg` fallback -> R-02, `relations.js:36-44`
  and each file's block.
- observation line 113 and its `failures` branch -> R-03, `observation.svelte.js:84-123`.
- joueur `call()` never renders an object; PSH3 forbids `..` imports ->
  R-04, `joueur.svelte.js:28-41`, `player_shell.py:134-147` (the rule's
  implementation, not its docstring).
- relative import form and depth -> R-05, the five importing lines.
- no check asserts the replaced literals -> R-06, raw grep.
- invariant format, budget, next id -> R-07, `claude_md_contract.py` and the
  rule files.
- no check runs Node -> R-08, raw grep (empty).
- build committed -> R-09, `frontend.md:9-12`.
- footer position, FILE_MAP freshness -> R-10.
- budgets -> R-12, `module_budget.py:55-59`.

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

(c) Enumerations: R-01, R-02, R-06, R-08 pasted above; R-05's no-import
list from `grep -cE "^\s*import "` over the 33 files.

(d) One contract, no family. Re-read after the brief's Scope IN: tick.

(e) Gates proposed: `frontend_error_message.py` FE1-FE4 -> satisfied by
`frontend/src/lib/errorMessage.js` (C-01) and the 33 edits; FE4 needs Node
on the machine (R-08) and nothing the check forbids. Gates passed:
`frontend_build_fresh.py` -> the committed rebuild (R-09);
`claude_md_contract.py` -> INV-69's bullet (R-07); `file_map.py` -> the new
check's docstring and the regenerated map (R-10); `player_shell.py` ->
`joueur/` untouched (R-04); `module_budget.py` -> R-12; the 32 checks of
R-06 -> unchanged, their patterns untouched (raw grep).

## Amendments

- AMENDMENT-0131-01 (2026-11-17, brief A in flight): `EntityList.svelte` already binds `errorMessage` as a local `$state`; R-05 corrected (identifier enumeration), Scope IN 5a renames it `loadError`. Gate (a), (c) re-run for R-05.
