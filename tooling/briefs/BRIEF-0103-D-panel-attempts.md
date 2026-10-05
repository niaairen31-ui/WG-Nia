<!-- slug: panel-attempts -->
# BRIEF 0103-D — "The Lore panels name their attempt"

Lot: LOT-0103-lore-usage-journal.md (authoritative on conflict)
Depends on: BRIEF-0103-C (the routes accept `attempt_id`)
Commit header for decisions: `(BRIEF-0103-d, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0103`, on the tree BRIEF-0103-C left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `frontend/src/lore/writePanel.svelte.js:31` → `function blank() {`; `:34` → `    busy: false, error: '', result: null, entities: null, entries: [], pick: {},` (last field line of `blank()`); `:68` → `    const body = await post('/api/lore/write/questions', { statement: writeState.statement });`; `:80` → `  const draft = await post('/api/lore/write/draft', {`; `:202` → `    const body = await post('/api/lore/write/commit', { proposal: toProposal() });`; `:210` → `export function restart() {` (it reassigns `blank()`).
- `frontend/src/lore/lore.svelte.js:14` → `export const loreState = $state({`; `:19` → `  selections: {},`; `:22` → `export async function askLore() {`; `:28` → `    const result = await api('/api/lore/ask', {`; `:64` → `    const resolved = await api('/api/lore/resolve', {`; `:83` → `export function reloadForWorld() {`.
- `frontend/src/lore/WritePanel.svelte:41` → the « Recommencer » button calls `restart()`; `:195` → « Relancer la proposition » calls `makeDraft()`.
- `tooling/verify/checks/lore_write.py` F1b → the set of paths `writePanel.svelte.js` calls is exactly `/api/lore/write/questions`, `/draft`, `/commit`, `/entries` and `/api/entities`.
- `src/world_engine/cockpit/routes/lore_write.py` and `routes/lore.py` declare `attempt_id: Optional[str] = None` on their four request bodies (BRIEF-0103-C).

## Facts carried

### R-03 — the panel keeps refs stable [M]
Opened: `frontend/src/lore/writePanel.svelte.js:31-38` (`blank()`), `:75-88`
(`draftNow`), `:139-141` (`removeAt` splices), `:170-200` (`toProposal`:
an entity kept « en texte » is dropped and becomes a `mentions` entry),
`:210-213` (`restart`).
Finding: the server assigns `e1…`/`f1…` refs to a draft; the panel edits in
place, never renumbers, and adds `k<n>` refs for knowers it adds.
Consequence: the analysis can pair a draft and its committed proposal by
`ref` (D1); nothing needs diffing at write time.

### R-14 — the panels' flows [M]
Opened: `frontend/src/lore/WritePanel.svelte:41` (« Recommencer » →
`restart()`), `:72-75`, `:195` (« Relancer la proposition » →
`makeDraft()`); `frontend/src/lore/lore.svelte.js:14-20, 22-40, 58-81,
83-88`; `tooling/verify/checks/lore_write.py:622-640` (F1b: the exact set
of paths `writePanel.svelte.js` calls).
Finding: a writing use runs text → questions → draft(s) → commit, restarted
by « Recommencer » or a world change; a consultation runs ask →
(resolve). Both state modules are plain `$state` objects.
Consequence: the attempt id is minted by the client per use (C-06) and sent
in the existing request bodies — no new path, F1b unchanged.

### R-17 — the frontend build is checked fresh [M]
Opened: `tooling/verify/checks/frontend_build_fresh.py:14-17, 119-133`.
Finding: `static/.build-manifest.json` must carry the hash of the current
`frontend/` sources.
Consequence: D rebuilds and commits `static/`.

## Contracts

### C-06 — the attempt id on the wire
Produced by: BRIEF-0103-C (server field), BRIEF-0103-D (client)
Consumed by: the journal, the export
Every request body of the five routes accepts an optional `attempt_id`.
The writing panel mints `crypto.randomUUID()` in `blank()` (each new use:
first load, « Recommencer », a world change) and sends it on questions,
draft and commit; the consultation panel mints one per `askLore()` and
reuses it in `confirmResolution()`; `reloadForWorld()` clears it.

## Context

An attempt is one use of a panel. The client mints the id so that a failed first request — which answers no body — still belongs to its attempt; the server keeps any UUID it receives (C). A re-draft or a commit retried after a refusal stays in the same attempt; « Recommencer » and a world change open a new one.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: adds `attemptId: crypto.randomUUID()` to `blank()` in `writePanel.svelte.js` and sends `attempt_id: writeState.attemptId` with its questions, draft and commit requests; adds `attemptId: ''` to `loreState` in `lore.svelte.js`, mints a fresh one at the start of each `askLore()` (before its request), sends it with the ask and resolve requests, and clears it in `reloadForWorld()`; documents both in the modules' header comments; extends `lore_usage.py` with U11; appends the decision entry.
2. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build` (writes `src/world_engine/cockpit/static/`); commit the rebuilt output.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `feat(lore): the Lore panels send their attempt id (BRIEF-0103-d)`.

````diff
diff --git a/frontend/src/lore/lore.svelte.js b/frontend/src/lore/lore.svelte.js
index c5a4f6d..2fad6e1 100644
--- a/frontend/src/lore/lore.svelte.js
+++ b/frontend/src/lore/lore.svelte.js
@@ -7,7 +7,10 @@
    answer, renderer) -- the component renders directly off it rather than
    this module reshaping it. `selections` is the only local addition: the
    creator's in-progress candidate choice per ambiguous mention ref, kept
-   here (not in `result`) until confirmResolution() sends it back. */
+   here (not in `result`) until confirmResolution() sends it back.
+
+   TICKET-0103 (BRIEF-0103-D): `attemptId` names one question for the usage
+   journal: askLore() opens a fresh one, confirmResolution() reuses it. */
 import { api } from '../creation/sheetRequest.svelte.js';
 import { serverState } from '../lib/serverState.svelte.js';
 
@@ -17,6 +20,7 @@ export const loreState = $state({
   askError: '',
   result: null,
   selections: {},
+  attemptId: '',
 });
 
 export async function askLore() {
@@ -24,11 +28,14 @@ export async function askLore() {
   if (!question || loreState.asking) return;
   loreState.asking = true;
   loreState.askError = '';
+  loreState.attemptId = crypto.randomUUID();
   try {
     const result = await api('/api/lore/ask', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
-      body: JSON.stringify({ question, world_id: serverState.worldId }),
+      body: JSON.stringify({
+        question, world_id: serverState.worldId, attempt_id: loreState.attemptId,
+      }),
     });
     loreState.result = result;
     loreState.selections = {};
@@ -69,6 +76,7 @@ export async function confirmResolution() {
         bindings: { ...loreState.selections },
         world_id: serverState.worldId,
         question: loreState.question,
+        attempt_id: loreState.attemptId,
       }),
     });
     loreState.result = resolved;
@@ -85,4 +93,5 @@ export function reloadForWorld() {
   loreState.askError = '';
   loreState.result = null;
   loreState.selections = {};
+  loreState.attemptId = '';
 }
diff --git a/frontend/src/lore/writePanel.svelte.js b/frontend/src/lore/writePanel.svelte.js
index cc2753d..a76d57b 100644
--- a/frontend/src/lore/writePanel.svelte.js
+++ b/frontend/src/lore/writePanel.svelte.js
@@ -7,7 +7,12 @@
    Every entity is picked from a list, never typed from memory (K1 of 0095):
    an ambiguous or new name offers the world's entities; "garder en texte"
    drops the entity and declares the name as a mention, so the tokenizer
-   records it in "Noms à lier". */
+   records it in "Noms à lier".
+
+   TICKET-0103 (BRIEF-0103-D): `attemptId` names one use of the panel, from
+   the text to its commit, for the usage journal. A fresh one comes with
+   every blank state (a new text, a world change); every request of the use
+   carries it. */
 import { api } from '../creation/sheetRequest.svelte.js';
 
 export const ENTITY_TYPES = Object.freeze([
@@ -32,6 +37,7 @@ function blank() {
   return {
     stage: 'text', statement: '', answers: '', questions: [], draft: null,
     busy: false, error: '', result: null, entities: null, entries: [], pick: {},
+    attemptId: crypto.randomUUID(),
   };
 }
 
@@ -65,7 +71,9 @@ export async function loadWorldEntities() {
 
 export function askQuestions() {
   return run(async () => {
-    const body = await post('/api/lore/write/questions', { statement: writeState.statement });
+    const body = await post('/api/lore/write/questions', {
+      statement: writeState.statement, attempt_id: writeState.attemptId,
+    });
     writeState.questions = body.questions;
     if (body.questions.length === 0) {
       await draftNow();
@@ -79,6 +87,7 @@ async function draftNow() {
   await loadWorldEntities();
   const draft = await post('/api/lore/write/draft', {
     statement: writeState.statement, answers: writeState.answers,
+    attempt_id: writeState.attemptId,
   });
   for (const entity of draft.entities) {
     if (entity.status === 'matched') entity.decision = 'existing';
@@ -199,7 +208,9 @@ function toProposal() {
 
 export function commit() {
   return run(async () => {
-    const body = await post('/api/lore/write/commit', { proposal: toProposal() });
+    const body = await post('/api/lore/write/commit', {
+      proposal: toProposal(), attempt_id: writeState.attemptId,
+    });
     writeState.result = body;
     writeState.stage = 'done';
     writeState.entities = null;
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index c5eb2e9..208ee6a 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17664,6 +17664,20 @@ copies it first. `ask` now answers an `OllamaError` raised while drafting
 the plan with the named 503 message, as it already did for a failed ping,
 instead of an unhandled 500 -- the step must be caught to be journaled.
 
+
+## THE LORE PANELS NAME THEIR ATTEMPT (TICKET-0103) -- CLIENT-MINTED UUID (BRIEF-0103-d, no schema change)
+
+**D1.** An attempt is one use of a panel. The writing panel mints
+`attemptId` with every blank state (a world change, « Recommencer ») and
+sends it with its questions, draft and commit requests; a
+re-draft or a refused commit stays in the same attempt. The consultation
+panel mints one per question and reuses it for the disambiguation round.
+The id is minted by the client so that a failed first request, which
+answers no body, still belongs to its attempt; the server keeps any UUID
+and mints its own for a missing or malformed one. A write attempt without
+an `ok` commit is an abandoned one: the analysis reads that from the
+journal, nothing records it.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_usage.py b/tooling/verify/checks/lore_usage.py
index 4621a2c..2c52f10 100644
--- a/tooling/verify/checks/lore_usage.py
+++ b/tooling/verify/checks/lore_usage.py
@@ -78,6 +78,14 @@ U10 -- structure. Neither route file calls `write_usage_event` (they go
    through `lore_usage`); `lore_usage.py` contains no `chat(` and no
    `select(`, and imports no consultation-pipeline and no writing-panel
    module.
+U11 -- the panels carry the attempt (BRIEF-0103-D), static:
+   a. `writePanel.svelte.js`: `blank()` mints `attemptId:
+      crypto.randomUUID()`, and its POSTs to `/api/lore/write/questions`,
+      `/draft` and `/commit` each send `attempt_id: writeState.attemptId`;
+   b. `lore.svelte.js`: `askLore()` mints `loreState.attemptId =
+      crypto.randomUUID()` before its POST, both POSTs send `attempt_id:
+      loreState.attemptId`, and `reloadForWorld()` clears it;
+   c. the built bundle under `cockpit/static/assets` carries `attempt_id`.
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -770,6 +778,37 @@ def check_u10() -> None:
         fail(f"U10: lore_usage.py imports {sorted(hits)}")
 
 
+def _function_body(text: str, header: str) -> str:
+    start = text.find(header)
+    if start < 0:
+        return ""
+    end = text.find("\n}\n", start)
+    return text[start:end if end > 0 else len(text)]
+
+
+def check_u11() -> None:
+    lore = ROOT / "frontend" / "src" / "lore"
+    write = (lore / "writePanel.svelte.js").read_text(encoding="utf-8")
+    if "attemptId: crypto.randomUUID()" not in _function_body(write, "function blank()"):
+        fail("U11a: blank() does not mint an attemptId")
+    for path in ("questions", "draft", "commit"):
+        call = write.find(f"'/api/lore/write/{path}'")
+        if call < 0 or "attempt_id: writeState.attemptId" not in write[call:write.find("});", call)]:
+            fail(f"U11a: the {path} request does not carry the attempt id")
+    consult = (lore / "lore.svelte.js").read_text(encoding="utf-8")
+    ask = _function_body(consult, "export async function askLore()")
+    minted = ask.find("loreState.attemptId = crypto.randomUUID();")
+    if minted < 0 or minted > ask.find("'/api/lore/ask'"):
+        fail("U11b: askLore() does not mint an attempt id before its request")
+    if consult.count("attempt_id: loreState.attemptId") != 2:
+        fail("U11b: the ask and resolve requests do not both carry the attempt id")
+    if "loreState.attemptId = '';" not in _function_body(consult, "export function reloadForWorld()"):
+        fail("U11b: reloadForWorld() does not clear the attempt id")
+    bundles = list((SRC / "cockpit" / "static" / "assets").glob("*.js"))
+    if not bundles or not any("attempt_id" in b.read_text(encoding="utf-8") for b in bundles):
+        fail("U11c: the built bundle does not carry attempt_id (rebuild the frontend)")
+
+
 def main() -> int:
     tmp = tempfile.mkdtemp(prefix="lore_usage_")
     db_path = f"{tmp}/u.db"
@@ -787,6 +826,7 @@ def main() -> int:
     check_u8()
     check_u9()
     check_u10()
+    check_u11()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -795,7 +835,8 @@ def main() -> int:
           "v2.13 declares it without world_id or FK and migrates from v2.12 only; the "
           "writer refuses every malformed record; a journal row outlives its world; every "
           "Lore model call can be captured with its prompt version and raw reply; every "
-          "writing and consultation step is journaled under its attempt, failures included")
+          "writing and consultation step is journaled under its attempt, failures included; "
+          "both panels send their attempt id")
     return 0
 
 
````

## Scope OUT

- Any new request path (F1b's set stays exactly as it is).
- Showing the attempt id, or anything from the journal, in the UI.
- Persisting the attempt id across a page reload (a reload starts a new attempt; `localStorage` is not used).
- Any change to `WritePanel.svelte`, `Lore.svelte` or the request shapes beyond the added field.
- The export (E).

## Invariants to defend

**Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the same body:** no `$effect` is touched — `attemptId` is assigned in plain functions only (`effect_self_write.py`). The built `static/` must match the sources (`frontend_build_fresh.py`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `lore_write.py` F1 fails (a path was added or removed).
- `npm run build` fails.
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- The built bundle's file name differs from the prototype's: expected (content hash); commit whatever `npm run build` wrote.

REPORT-ONLY:
- Timing of the corpus run.
- `npm` audit or deprecation notices.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt files under `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/lore_usage.py` → `PASS: lore_usage -- … every writing and consultation step is journaled under its attempt, failures included; both panels send their attempt id`.
- `lore_write.py`, `frontend_build_fresh.py`, `effect_self_write.py`, `module_budget.py` → `PASS`.
- Mutation test: in `writePanel.svelte.js`, drop `attempt_id: writeState.attemptId` from the commit request; U11a fails; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 137/137.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE LORE PANELS NAME THEIR ATTEMPT (TICKET-0103) -- CLIENT-MINTED UUID (BRIEF-0103-d, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
