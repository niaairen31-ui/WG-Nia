<!-- slug: suivi-tab -->
# BRIEF 0115-E — "« Suivi », a Création tab that reads only -- Dashboard.svelte, dashboard.svelte.js (no schema change)"

Lot: LOT-0115-creator-dashboard.md (authoritative on conflict)
Depends on: BRIEF-0115-D (C-04)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after the previous brief of this lot).

- `frontend/src/creation/tabs.js` -> `  queue: {` right after the `subjects` entry
- `frontend/src/creation/registry.js` -> the `vocabulary` island, `    createdBy: 'TICKET-0114',`, then `  }),` / `});`
- `frontend/src/creation/mount.js` -> `import Vocabulary from './Vocabulary.svelte';` and `COMPONENTS` ending `vocabulary: Vocabulary };`
- `frontend/src/creation/Creation.svelte` -> `  <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->`
- `frontend/public/creation.css` -> `#creation-vocabulaire { flex: 1; min-height: 0; overflow: auto; }`
- `GET /api/dashboard` answers (BRIEF-0115-D); no `Dashboard.svelte`, no `tooling/verify/checks/dashboard_tab.py`.

## Facts carried

### R-07 — the lists this lot extends [M]
Opened: `frontend/src/creation/tabs.js:381`, `registry.js:578`, `mount.js:49`, `Creation.svelte:261`, `frontend/public/creation.css:314`; INV-49 (`page_contract.py`), INV-50 (`creation_island.py`), INV-54 (`creation_container_sizing.py`), INV-55 (`effect_self_write.py`) govern a new tab. The prototype rendered in Chromium on a scratch database: cards, deferrals, world filter, export download.

## Contracts

### C-04 — the dashboard's routes
Produced by: BRIEF-0115-D   Consumed by: this brief
(see the lot) `GET /api/dashboard`, `GET /api/dashboard/export`.

## Context

H1 of the series: « Suivi » in Création, reading D's routes only. The export button is I1; the warning beside it is INV-01's honest face: the file holds the secrets.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `Dashboard.svelte`, `dashboard.svelte.js` (new): the island and its requests;
   - `tabs.js` (`suivi`, before `queue`), `registry.js` (`dashboard`, origin `new`), `mount.js`, `Creation.svelte` (`creation-suivi`), `creation.css` (its sizing);
   - creates check `dashboard_tab.py` (DT1-DT3); appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/public/creation.css
   - frontend/src/creation/Creation.svelte
   - frontend/src/creation/Dashboard.svelte
   - frontend/src/creation/dashboard.svelte.js
   - frontend/src/creation/mount.js
   - frontend/src/creation/registry.js
   - frontend/src/creation/tabs.js
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/dashboard_tab.py

````diff
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index e663234..66c1d05 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -312,6 +312,7 @@ input.notes::placeholder { color: var(--muted); }
 #creation-quetes      { flex: 1; min-height: 0; overflow: auto; }
 #creation-dettes      { flex: 1; min-height: 0; overflow: auto; }
 #creation-vocabulaire { flex: 1; min-height: 0; overflow: auto; }
+#creation-suivi       { flex: 1; min-height: 0; overflow: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index 05a16d6..4a2ed3d 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -258,6 +258,9 @@
   <div id="creation-vocabulaire" style:display={containerVisible('creation-vocabulaire') ? '' : 'none'}></div>
   <div id="creation-subjects" style:display={containerVisible('creation-subjects') ? '' : 'none'}></div>
 
+  <!-- ── Suivi sub-tab -- Svelte island (TICKET-0115): empty by construction ── -->
+  <div id="creation-suivi" style:display={containerVisible('creation-suivi') ? '' : 'none'}></div>
+
   <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->
   <div id="creation-queue" style:display={containerVisible('creation-queue') ? '' : 'none'}></div>
 
diff --git a/frontend/src/creation/Dashboard.svelte b/frontend/src/creation/Dashboard.svelte
new file mode 100644
index 0000000..973ff7b
--- /dev/null
+++ b/frontend/src/creation/Dashboard.svelte
@@ -0,0 +1,107 @@
+<script>
+  /* TICKET-0115 (BRIEF-0115-E; H1, E2, F2, I1, J1 and M1 of the
+     conditions series' dashboard). The « Suivi » island: the creator's
+     dashboard -- each metric a question, its numbers and the decision codes
+     it watches, no threshold (E2) -- the deferrals she watches with their
+     reactivation condition, and the export of the same scope for a deeper
+     analysis. One world or all (J1), two real-world days. Reads only; its
+     CREATION_ISLANDS entry declares origin 'new'. State and requests live
+     in dashboard.svelte.js. */
+  import { untrack } from 'svelte';
+  import { dashboardState, loadDashboard, exportDashboard, share } from './dashboard.svelte.js';
+
+  // Loaded once when the island mounts; the selectors reload on change.
+  $effect(() => {
+    untrack(() => loadDashboard());
+  });
+
+  const STATUS_FR = { open: 'en attente', reached: 'atteinte' };
+  let metricTitles = $derived(Object.fromEntries(dashboardState.metrics.map((m) => [m.key, m.title])));
+
+  function metricLabel(key) {
+    if (!key) return 'à surveiller toi-même';
+    if (key === 'export') return "mesurable dans l'export";
+    return 'suivie par « ' + (metricTitles[key] || key) + ' »';
+  }
+</script>
+
+<div class="dashboard">
+  <div class="queue-panel">
+    <div class="queue-body">
+      <div class="inline">
+        <label>Monde
+          <select bind:value={dashboardState.world} onchange={loadDashboard}>
+            <option value="all">Tous les mondes</option>
+            {#each dashboardState.worlds as w (w.id)}<option value={w.id}>{w.name}</option>{/each}
+          </select>
+        </label>
+        <label>du <input type="date" bind:value={dashboardState.since} onchange={loadDashboard} /></label>
+        <label>au <input type="date" bind:value={dashboardState.until} onchange={loadDashboard} /></label>
+        <button class="btn-icon" onclick={loadDashboard} title="Rafraîchir">↻</button>
+        <button class="btn-send" disabled={dashboardState.exporting} onclick={exportDashboard}>
+          {dashboardState.exporting ? 'Export…' : 'Exporter (JSON)'}
+        </button>
+      </div>
+      <div class="muted">
+        L'export contient tout ce que voit Création, secrets et notes compris : il ne quitte ta machine que si
+        tu l'envoies.
+      </div>
+      {#if dashboardState.exportError}<div class="r-err">Export : {dashboardState.exportError}</div>{/if}
+      {#if dashboardState.loadError}
+        <div class="r-err">Erreur : {dashboardState.loadError}</div>
+      {:else}
+        <div class="cards">
+          {#each dashboardState.metrics as metric (metric.key)}
+            <div class="row-card metric">
+              <div class="head">
+                <strong>{metric.title}</strong>
+                {#each metric.watches as code (code)}<span class="badge b-other">{code}</span>{/each}
+                {#if !metric.dated}<span class="badge b-other">état actuel</span>{/if}
+              </div>
+              <div class="question">{metric.question}</div>
+              {#if metric.rows.length === 0}
+                <div class="muted">Aucune donnée pour cette période.</div>
+              {:else}
+                <table>
+                  <tbody>
+                    {#each metric.rows as row, i (i)}
+                      <tr><td class="muted">{row.group}</td><td>{row.label}</td><td class="num">{share(row)}</td></tr>
+                    {/each}
+                  </tbody>
+                </table>
+              {/if}
+              <div class="muted">{metric.note}</div>
+            </div>
+          {/each}
+        </div>
+        <h4>Reports surveillés</h4>
+        {#each dashboardState.deferrals as d (d.code + d.ticket)}
+          <div class="row-card" class:reached={d.status === 'reached'}>
+            <div class="head">
+              <strong>{d.code}</strong> <span class="muted">{d.ticket}</span>
+              <span class="badge b-other">{STATUS_FR[d.status] || d.status}</span>
+              {#if d.follow_up}<span class="badge b-other">{d.follow_up}</span>{/if}
+            </div>
+            <div>{d.deferred}</div>
+            <div class="muted">Revient si : {d.condition} — {metricLabel(d.metric)}</div>
+          </div>
+        {/each}
+      {/if}
+    </div>
+  </div>
+</div>
+
+<style>
+  .dashboard { display: flex; flex-direction: column; gap: 12px; }
+  .head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
+  .inline { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 6px; }
+  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; margin-top: 10px; }
+  .metric table { width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 13px; }
+  .metric td { padding: 2px 4px; vertical-align: top; }
+  .metric td.num { text-align: right; white-space: nowrap; }
+  .question { margin: 4px 0; font-style: italic; }
+  .row-card.reached { border-left: 3px solid var(--red); }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+  h4 { margin: 16px 0 4px; font-size: 13px; color: var(--muted); }
+</style>
diff --git a/frontend/src/creation/dashboard.svelte.js b/frontend/src/creation/dashboard.svelte.js
new file mode 100644
index 0000000..7a98873
--- /dev/null
+++ b/frontend/src/creation/dashboard.svelte.js
@@ -0,0 +1,74 @@
+/* TICKET-0115 (BRIEF-0115-E). State and requests of the « Suivi » island
+   (Dashboard.svelte): the creator's dashboard -- every metric of
+   `dashboard_metrics.METRICS` and the deferral registry, for one world or
+   all of them, between two real-world days (GET /api/dashboard) -- and its
+   export, the same scope as a JSON file to save
+   (GET /api/dashboard/export). Reads only. */
+import { api } from './sheetRequest.svelte.js';
+
+export const dashboardState = $state({
+  world: 'all',
+  since: '',
+  until: '',
+  worlds: [],
+  metrics: [],
+  deferrals: [],
+  loading: false,
+  loadError: '',
+  exporting: false,
+  exportError: '',
+});
+
+function query() {
+  const params = new URLSearchParams({ world: dashboardState.world });
+  if (dashboardState.since) params.set('since', dashboardState.since);
+  if (dashboardState.until) params.set('until', dashboardState.until);
+  return params.toString();
+}
+
+export async function loadDashboard() {
+  dashboardState.loading = true;
+  dashboardState.loadError = '';
+  try {
+    const data = await api('/api/dashboard?' + query());
+    dashboardState.worlds = data.worlds;
+    dashboardState.metrics = data.metrics;
+    dashboardState.deferrals = data.deferrals;
+  } catch (e) {
+    dashboardState.loadError = e.message;
+  } finally {
+    dashboardState.loading = false;
+  }
+}
+
+/** Fetch the export and hand it to the browser as a file to save. */
+export async function exportDashboard() {
+  dashboardState.exporting = true;
+  dashboardState.exportError = '';
+  try {
+    const res = await fetch('/api/dashboard/export?' + query());
+    if (!res.ok) {
+      const data = await res.json().catch(() => ({ detail: res.statusText }));
+      throw new Error(data.detail || res.statusText);
+    }
+    const disposition = res.headers.get('content-disposition') || '';
+    const match = disposition.match(/filename="([^"]+)"/);
+    const url = URL.createObjectURL(await res.blob());
+    const link = document.createElement('a');
+    link.href = url;
+    link.download = match ? match[1] : 'suivi.json';
+    link.click();
+    URL.revokeObjectURL(url);
+  } catch (e) {
+    dashboardState.exportError = e.message;
+  } finally {
+    dashboardState.exporting = false;
+  }
+}
+
+/** « 3 / 5 (60 %) », or the value alone. */
+export function share(row) {
+  if (row.of === null || row.of === undefined) return String(row.value);
+  if (!row.of) return `${row.value} / 0`;
+  return `${row.value} / ${row.of} (${Math.round((100 * row.value) / row.of)} %)`;
+}
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index 72b2fb0..b621bd1 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -45,8 +45,9 @@ import SubjectWorklist from './SubjectWorklist.svelte';
 import QuestOffers from './QuestOffers.svelte';
 import Debts from './Debts.svelte';
 import Vocabulary from './Vocabulary.svelte';
+import Dashboard from './Dashboard.svelte';
 
-const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts, vocabulary: Vocabulary };
+const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts, vocabulary: Vocabulary, dashboard: Dashboard };
 
 const live = {}; // key -> { node, instance }
 
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index a5335bd..1b2d42b 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -577,4 +577,13 @@ export const CREATION_ISLANDS = Object.freeze({
     origin: 'new',
     createdBy: 'TICKET-0114',
   }),
+  // TICKET-0115 (BRIEF-0115-E, H1): the creator's dashboard and the
+  // deferrals she watches -- created directly as an island, no legacy
+  // predecessor.
+  dashboard: Object.freeze({
+    containerId: 'creation-suivi',
+    component: 'Dashboard.svelte',
+    origin: 'new',
+    createdBy: 'TICKET-0115',
+  }),
 });
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index a2af20e..a3f1a55 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -378,6 +378,17 @@ export const CREATION_TABS = {
     islands: [{ key: 'subjectWorklist', containerId: 'creation-subjects' }],
     primaryAction: null, // binds existing knowledge subjects; creates no row
   },
+  // TICKET-0115 (BRIEF-0115-E, H1): the creator's dashboard -- metrics in
+  // code, the deferrals she watches, the export. Reads only.
+  suivi: {
+    label: 'Suivi',
+    archetype: 'bespoke',
+    containers: ['creation-suivi'],
+    loader: null,
+    state: { onTabEnter: null, onWorldSwitch: null },
+    islands: [{ key: 'dashboard', containerId: 'creation-suivi' }],
+    primaryAction: null, // reads only: nothing is created here
+  },
   queue: {
     label: 'Review Queue',
     archetype: 'bespoke',
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 836cc9f..aa978fb 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19783,6 +19783,25 @@ world's secrets: the tab says so beside the button.
 **Rejected.** H2 (metrics typed in the interface), E1 (thresholds with a
 minimum sample: Nia's prod held 3 typed events), I2 (a CSV per table).
 
+## « SUIVI », A CRÉATION TAB THAT READS ONLY (TICKET-0115) -- `Dashboard.svelte`, `dashboard.svelte.js` (BRIEF-0115-e, no schema change)
+
+**H1 of the series -- « Suivi » in Création.** One bespoke tab, one island
+created as one (origin `new`): a world selector (every world, or one --
+J1), two day inputs, a card per metric (its question, the codes it
+watches, its rows as « 3 / 5 (60 %) », « état actuel » when it ignores the
+dates) and the deferral registry (what waits, « Revient si : », the metric
+that watches it, « atteinte » in red). No primary action: nothing is
+created here.
+
+**I1 -- the export button.** It saves `GET /api/dashboard/export` for the
+scope on screen, named after it; the warning beside it says the file holds
+the secrets and the creator's notes and leaves the machine only if she
+sends it.
+
+**Rejected.** A chart per metric: E2 shows numbers, and a chart of three
+events is noise; reactivation: a metric whose rows Nia reads as a trend
+over several weeks.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/dashboard_tab.py b/tooling/verify/checks/dashboard_tab.py
new file mode 100644
index 0000000..185bbe3
--- /dev/null
+++ b/tooling/verify/checks/dashboard_tab.py
@@ -0,0 +1,82 @@
+"""G1 check for TICKET-0115 -- the « Suivi » tab shows the dashboard's metrics and deferrals, exports the same scope, and warns that the export holds secrets.
+
+BRIEF-0115-E's rules (H1, F2, I1 and J1 of the conditions series'
+dashboard). Static: the tab's registration is held by `page_contract.py`,
+`creation_island.py` and `creation_container_sizing.py`; this check holds
+what the tab says.
+
+DT1 -- registered. `tabs.js` declares a `suivi` entry labelled « Suivi »
+   whose one island is `dashboard` in `creation-suivi`, with no primary
+   action; `registry.js` declares `dashboard` origin `new`, created by
+   TICKET-0115.
+DT2 -- requests. `dashboard.svelte.js` reads `/api/dashboard?` and
+   `/api/dashboard/export?` with the same query (`world`, `since`, `until`)
+   and writes nothing (no `method:` POST, PUT or DELETE).
+DT3 -- what it shows. `Dashboard.svelte` renders each metric's `question`,
+   `watches` and `rows` (through `share`), each deferral's `condition` and
+   `status`, a world selector with « Tous les mondes », two date inputs,
+   the export button, and the warning that the export holds the secrets
+   and notes.
+
+Stdlib only, no DB. A missing file or a missing passage is a FAILURE.
+"""
+from __future__ import annotations
+
+import pathlib
+import re
+import sys
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+CREATION = ROOT / "frontend" / "src" / "creation"
+
+FAILURES: list[str] = []
+
+PASSAGES: dict[str, tuple[str, ...]] = {
+    "DT1 tabs.js": ("suivi: {", "label: 'Suivi'", "islands: [{ key: 'dashboard', containerId: 'creation-suivi' }]"),
+    "DT1 registry.js": ("dashboard: Object.freeze({", "containerId: 'creation-suivi'", "createdBy: 'TICKET-0115'"),
+    "DT2 dashboard.svelte.js": ("'/api/dashboard?' + query()", "'/api/dashboard/export?' + query()",
+                                "new URLSearchParams({ world: dashboardState.world })",
+                                "params.set('since'", "params.set('until'"),
+    "DT3 Dashboard.svelte": ("{metric.question}", "metric.watches", "metric.rows", "share(row)", "{d.condition}",
+                             "d.status", '<option value="all">Tous les mondes</option>', 'type="date"',
+                             "onclick={exportDashboard}", "secrets et notes compris"),
+}
+FILES = {"DT1 tabs.js": "tabs.js", "DT1 registry.js": "registry.js",
+         "DT2 dashboard.svelte.js": "dashboard.svelte.js", "DT3 Dashboard.svelte": "Dashboard.svelte"}
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def main() -> None:
+    texts = {}
+    for rule, name in FILES.items():
+        path = CREATION / name
+        if not path.exists():
+            fail(f"{rule}: {path} not found")
+            continue
+        texts[rule] = path.read_text(encoding="utf-8")
+        for passage in PASSAGES[rule]:
+            if passage not in texts[rule]:
+                fail(f"{rule}: missing {passage!r}")
+    tabs = texts.get("DT1 tabs.js", "")
+    block = re.search(r"\n  suivi: \{(.*?)\n  \},", tabs, re.DOTALL)
+    if block is None or "primaryAction: null" not in block.group(1):
+        fail("DT1: the suivi entry has a primary action")
+    registry = texts.get("DT1 registry.js", "")
+    entry = re.search(r"dashboard: Object\.freeze\(\{(.*?)\}\)", registry, re.DOTALL)
+    if entry is None or "origin: 'new'" not in entry.group(1):
+        fail("DT1: the dashboard island is not origin 'new'")
+    if re.search(r"method:\s*'(POST|PUT|PATCH|DELETE)'", texts.get("DT2 dashboard.svelte.js", "")):
+        fail("DT2: dashboard.svelte.js writes")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        sys.exit(1)
+    print("PASS: dashboard_tab -- « Suivi » shows the metrics and the deferrals, exports the same scope, "
+          "and warns about secrets")
+
+
+if __name__ == "__main__":
+    main()
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- Charts (rejected in the decision entry); any write from the tab.
- The deferrals' text: D's registry, never edited here.

## Invariants to defend

INV-49, INV-50, INV-54, INV-55 (the tab's registration and its `$effect`: the load runs in `untrack`, nothing assigned in an effect body is read back). INV-01: the export warning is rendered beside the button (DT3).

## Decision rights

STOP:
- Registering the tab would need a branch outside `CREATION_TABS`, or `Creation.svelte` importing a component.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- `lore_usage.py` timing out at 16-17 s inside the corpus: it does the same on `main` (pre-existing, R-09 of the lot).
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice, Vite's chunk-size warning.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/dashboard_tab.py` -> `PASS`.
- `python tooling/verify/checks/creation_island.py` -> `PASS`.
- `python tooling/verify/checks/page_contract.py` -> `PASS`.
- `python tooling/verify/checks/creation_container_sizing.py` -> `PASS`.
- `python tooling/verify/checks/effect_self_write.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/stylesheet_partition.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (167 on the prototype; `lore_usage.py` may time out as on `main` -- REPORT-ONLY).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **DT1** -- `tabs.js`, the `suivi` entry: `    primaryAction: null, // reads only: nothing is created here` -> `    primaryAction: { label: '+', handler: () => triggerPrimaryAction('dashboard') },`
  - **DT2** -- `dashboard.svelte.js` `query`: `  if (dashboardState.until) params.set('until', dashboardState.until);` -> (line deleted)
  - **DT3** -- `Dashboard.svelte`, the warning: `secrets et notes compris` -> `secrets compris`
- Live gate (Nia): Création › « Suivi »: every world then one; two days; the cards show their numbers and codes; the reports list shows WH3 « atteinte » with TICKET-0122; « Exporter (JSON) » saves a file that opens in Claude Code.
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated; the static build rebuilt.
