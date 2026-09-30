<!-- slug: add-system-button -->
# BRIEF 0099-C — "« + Ajouter un système » in the shell band"

Lot: LOT-0099-competences-list-sheet.md (authoritative on conflict)
Depends on: BRIEF-0099-B (C-01, C-04, C-06 and `CREATION_TABS.competences`)
Commit header for decisions: `(BRIEF-0099-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0099`, on the tree BRIEF-0099-B left, before applying anything. Halt if one has moved.

- `frontend/src/creation/tabs.js:89` → `function triggerPrimaryAction(key) {`; `:184` → `//                 the same side (creation_island.py rule 11).`; `:268` → `    primaryAction: { label: '+ Ajouter une compétence', handler: () => triggerPrimaryAction('entitySheet') },` inside `competences:` (`archetype: 'entity'`, `containers: ['creation-editor-area']`)
- `frontend/src/creation/mount.js:132` → `export function triggerPrimaryAction(key) {`, calling `existing.instance.primaryAction();`
- `frontend/src/creation/Creation.svelte:93` → `       primaryAction, exactly one button in this same fixed position on`; `:112-114` → the `{#if activeEntry?.primaryAction}` block with `id="creation-shell-action"`
- `frontend/src/creation/Sheet.svelte:199` → `  /** Called by mount.js's _islandPrimaryAction('entitySheet') when the`; `export function primaryAction() {` below it; `if (creationState.sheetType === 'competences') creationState.sheetDetail = blankRecord();` inside it
- `frontend/src/creation/competences.svelte.js:88` → `export function blankRecord() {`; `saveSystem` issues a PUT only
- `tooling/verify/checks/creation_island.py:112` → ``      `primaryAction: {` site with no accompanying `createPanel` field.``; `:182` → the `primary_actions` line of the PASS message; `:940` → `# C-03: rule 12, COMPONENTS agreement`; `:1406` → `    primary_action_count = _rule11_pairing(tabs_src, entries)`
- `tooling/verify/checks/page_contract.py:319` → `    # TICKET-0059 (BRIEF-0059-h commit 4): the add-form moved off static`
- `grep -rn "Ajouter un système" frontend/src` → no output

## Facts carried

### R-12 — the mount seam [M]
Opened: `frontend/src/creation/mount.js:38` (`import Competences`), `:47`
(`COMPONENTS`), `:130-149` (`triggerPrimaryAction(key)` calls
`instance.primaryAction()`); `tabs.js:78-91` (`setMountActions`, local
`triggerPrimaryAction(key)`); `creation_island.py:734-790` (rule 8: one
definition, imported only by `Creation.svelte`; `action_count` must be 8,
`:1420`), `:889-944` (rule 11: the primary key is read by
`triggerPrimaryAction\(\s*'…'\s*\)` — ONE literal — and the component must
`export function primaryAction(`).
Consequence: G1 passes the variant through the existing function (C-06);
rule 11's one-literal regex keeps matching the primary call; rule 11b is new.

*(Lines above are `main`'s; on B's tree `mount.js`'s function sits at `:132` and `creation_island.py`'s rule 11 at `:880-938` — the anchors list gives B's lines.)*

### R-13 — the page contract [M]
Opened: `tooling/verify/checks/page_contract.py:46-49` (`TAB_KEYS` includes
`competences`), `:179-183` (every entry has `primaryAction`), `:297-316`
("Ajouter une compétence" exactly once under `frontend/src/creation/`),
`:331-366` (Intrigues/Événements must be `archetype: 'entity'` on
`creation-editor-area`; `creation-intrigues` must not exist); `Creation.svelte:
91-114` (the shell band renders one primary button).
Consequence: B adds the Compétences twin of `:331-366`; C adds the
`secondaryAction` assertions and the one-occurrence rule for « Ajouter un
système ».

### R-15 — the endpoints [M]
Opened: `src/world_engine/cockpit/crud/skills.py:157-318` (skill systems and
gaps), `:309-470` (skill definitions).
Finding: GET lists; POST/PUT return the saved row (`_skill_system_dict` with
`skill_count`; `_skill_definition_dict`); 409 on a duplicate name and on
deleting a system with skills; 422 on an empty name or a bad `base_domain`.
Consequence: frontend-only ticket; every save returns what the fiche shows next.

## Contracts

### C-01 — the competences record (family)
Produced by: B   Consumed by: B (list, fiche, save), C
Built only by the factories of `frontend/src/creation/competences.svelte.js`;
always a fresh object, never a row of `competencesState`.
- **skill**: `{ kind: 'skill', persisted, id, draftKey, name, base_domain,
  system_id, description }`. `skillRecord(row)` → `persisted: true`, `id` =
  the uuid, `draftKey: null`. `draftRecord(d)` → `persisted: false`,
  `id: 'draft:<key>'`, `draftKey: d.key`. `blankRecord()` → `persisted:
  false`, `id: null`, `draftKey: null`, `base_domain: 'physical'`.
- **system**: `{ kind: 'system', persisted, id, name, description,
  skill_count }`. `systemRecord(sys)` → `persisted: true`. `blankRecord(
  'system')` (C) → `persisted: false`, `id: null`, `skill_count: 0`.
- **assistant**: `{ kind: 'assistant', persisted: false, id: 'assistant' }`
  from `assistantRecord()`; `ASSISTANT_RECORD_ID = 'assistant'`.
- `persisted` alone decides POST vs PUT, the « Nouvelle/Nouveau » title and
  whether Supprimer shows. `id` is the list identity (`selectedRecordId`).
- `competenceSheetTitle(record)`: assistant → `'Assistant de compétences'`;
  system → name, or `'Nouveau système'`; skill → name, or `'Nouvelle
  compétence'`; `null` → `''`.

### C-04 — writes
Produced by: B (skill POST/PUT, system PUT), C (system POST)   Consumed by: B, C
`saveCompetenceRecord(record)` → the saved C-01 record, or throws `Error`:
`'Nom requis.'` (blank name, both kinds), `'Domaine de base requis.'` (skill
whose `base_domain` is not one of `COMPETENCES_DOMAINS`), `'Rien à
enregistrer.'` (any other kind), or the server's `detail`. A skill with a
`draftKey` is removed from `draft` once saved. `deleteSkill(id)`,
`deleteSystem(id)`: DELETE, no reload (the caller refreshes the list).

### C-06 — opening a blank record
Produced by: B (no variant), C (variant)   Consumed by: B, C
`Sheet.svelte`'s `export function primaryAction(variant)`: after
`enterCreateMode(...)`, when `creationState.sheetType === 'competences'`,
`sheetDetail = blankRecord(variant)`. `mount.js`'s
`triggerPrimaryAction(key, variant)` calls `instance.primaryAction(variant)`;
`tabs.js`'s local wrapper forwards both arguments.

### C-07 — `secondaryAction`
Produced by: C   Consumed by: C (`Creation.svelte`, `creation_island.py`,
`page_contract.py`)
A `CREATION_TABS` field `{ label, handler }`, optional. `handler` calls
`triggerPrimaryAction('<key>', '<variant>')` with two string literals, `<key>`
equal to the entry's own routed `primaryAction` key. The shell band renders it
as `<button class="btn-send" id="creation-shell-secondary-action">`, just
before the primary button, only when the entry also has a `primaryAction`.
Compétences: `{ label: '+ Ajouter un système', handler: () =>
triggerPrimaryAction('entitySheet', 'system') }`.

## Context

After B, a system can be opened, edited and deleted from the list, but not created. Nia locked G1: « + Ajouter un système » sits beside « + Ajouter une compétence » in the shell band, as a registry field that reuses the primary action's route with a variant.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `tabs.js`: documents `secondaryAction` in the entry contract comment; the local `triggerPrimaryAction(key, variant)` forwards both; `CREATION_TABS.competences` gains C-07's `secondaryAction`;
   - `mount.js`: `triggerPrimaryAction(key, variant)` calls `instance.primaryAction(variant)` (still one definition, rule 8);
   - `Creation.svelte`: renders `#creation-shell-secondary-action` before `#creation-shell-action` when the entry declares both; the band comment names it;
   - `Sheet.svelte`: `primaryAction(variant)`, `blankRecord(variant)`;
   - `competences.svelte.js`: `blankRecord('system')` (C-01), `saveSystem` POSTs an unpersisted system (C-04);
   - `creation_island.py`: rule 11b (`_rule11b_secondary`) with its docstring entry and PASS count; `page_contract.py`: the `secondaryAction` contract comment, the shell render, « Ajouter un système » exactly once, in `tabs.js`;
   - the decision entry above the footer.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutations, each run then restored with `git checkout -- frontend/src/creation/tabs.js` before committing:
   - `triggerPrimaryAction('entitySheet', 'system')` → `triggerPrimaryAction('entityList', 'system')`: `creation_island.py` prints `secondaryAction routes to 'entityList' but primaryAction routes to 'entitySheet'` and `rule11b: zero paired secondaryAction(s) collected`;
   - `triggerPrimaryAction('entitySheet', 'system')` → `triggerPrimaryAction('entitySheet')`: `creation_island.py` prints `secondaryAction.handler does not call triggerPrimaryAction('<key>', '<variant>') with two string literals`.
5. Commit message: `feat(creation): + Ajouter un système in the shell band (BRIEF-0099-c)`.

````diff
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index 6f23b27..e955d6a 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -91,7 +91,8 @@
   <!-- ── Standard shell band (BRIEF-0005-c) -- one header band above every
        Création page: the entry's label (title) plus, iff it declares a
        primaryAction, exactly one button in this same fixed position on
-       every tab. #creation-shell-extra/#creation-shell-batch-bar are
+       every tab -- preceded, iff it also declares a secondaryAction
+       (TICKET-0099, G1), by that one second button. #creation-shell-extra/#creation-shell-batch-bar are
        Review Queue's mount points (a one-off relocation, not a generic
        shell concept); both are declared slots on CREATION_TABS.queue so
        containerVisible covers them the same way as any other slot. -->
@@ -109,6 +110,9 @@
         </button>
       {/each}
     </div>
+    {#if activeEntry?.primaryAction && activeEntry?.secondaryAction}
+      <button class="btn-send" id="creation-shell-secondary-action" onclick={activeEntry.secondaryAction.handler}>{activeEntry.secondaryAction.label}</button>
+    {/if}
     {#if activeEntry?.primaryAction}
       <button class="btn-send" id="creation-shell-action" onclick={activeEntry.primaryAction.handler}>{activeEntry.primaryAction.label}</button>
     {/if}
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index fee1389..6248b12 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -196,7 +196,12 @@
     creationState.sheetDetail = detail;
   }
 
-  /** Called by mount.js's _islandPrimaryAction('entitySheet') when the
+  /** TICKET-0099 (G1): `variant` is what a secondaryAction button passes
+   *  through triggerPrimaryAction ('system' for Compétences' second
+   *  button); the primary button passes none, and only a competences
+   *  fiche reads it.
+   *
+   *  Called by mount.js's _islandPrimaryAction('entitySheet') when the
    *  standard shell action band ("+ Nouveau"/"+ Nouvelle intrigue") is
    *  clicked -- every entity-archetype tab routes here now, including pj
    *  (BRIEF-0059-j commit 3: pj's createPanel goes null too, rule 11) and
@@ -206,7 +211,7 @@
    *  branch in this function. Mirrors creationNewEntity's own draft reset
    *  (the plain "+ Nouveau" idiom every entity tab shared before this
    *  brief), via the same legacy helper so the two paths never drift. */
-  export function primaryAction() {
+  export function primaryAction(variant) {
     resetCreateDrafts();
     resetDraftRoles();
     resetFactsDraft();
@@ -217,7 +222,7 @@
     // TICKET-0099 (BRIEF-0099-b): a competences fiche always holds a whole
     // C-01 record, never enterCreateMode's bare {} -- selected by the
     // sheetType just written, the same fact that picks the render branch.
-    if (creationState.sheetType === 'competences') creationState.sheetDetail = blankRecord();
+    if (creationState.sheetType === 'competences') creationState.sheetDetail = blankRecord(variant);
   }
 
   legacyDoc.addEventListener('creation:sheet-reset', () => {
diff --git a/frontend/src/creation/competences.svelte.js b/frontend/src/creation/competences.svelte.js
index 8788976..d7f0c3c 100644
--- a/frontend/src/creation/competences.svelte.js
+++ b/frontend/src/creation/competences.svelte.js
@@ -82,9 +82,13 @@ export function assistantRecord() {
   return { kind: 'assistant', persisted: false, id: ASSISTANT_RECORD_ID };
 }
 
-/** The blank record the shell's primary action opens (Sheet.svelte's
- *  primaryAction). */
-export function blankRecord() {
+/** The blank record the shell's buttons open (Sheet.svelte's
+ *  primaryAction): 'system' from the shell's secondaryAction button
+ *  (TICKET-0099, G1), a skill otherwise. */
+export function blankRecord(kind) {
+  if (kind === 'system') {
+    return { kind: 'system', persisted: false, id: null, name: '', description: '', skill_count: 0 };
+  }
   return {
     kind: 'skill', persisted: false, id: null, draftKey: null,
     name: '', base_domain: 'physical', system_id: null, description: '',
@@ -208,7 +212,9 @@ async function saveSkill(record) {
 async function saveSystem(record) {
   const name = requireName(record);
   const body = JSON.stringify({ name, description: record.description || null });
-  const saved = await api(`/api/skill-systems/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body });
+  const saved = record.persisted
+    ? await api(`/api/skill-systems/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
+    : await api('/api/skill-systems', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
   return systemRecord(saved);
 }
 
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index 3a83c05..9fc7679 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -128,11 +128,13 @@ export function activateIsland(key, tabKey) {
 
 /** Replaces the old 'island:action' dispatch (BRIEF-0059-l item 5): the
  *  standard shell band's primaryAction button forwards its click to the
- *  mounted component's own exported primaryAction(), by direct call. */
-export function triggerPrimaryAction(key) {
+ *  mounted component's own exported primaryAction(), by direct call.
+ *  TICKET-0099 (G1): a secondaryAction button reaches the same function
+ *  with a variant string; the primary button passes none. */
+export function triggerPrimaryAction(key, variant) {
   const existing = live[key];
   if (existing && typeof existing.instance.primaryAction === 'function') {
-    existing.instance.primaryAction();
+    existing.instance.primaryAction(variant);
     return;
   }
   const msg = `creation/mount: triggerPrimaryAction fired for ${JSON.stringify(key)} with no mounted primaryAction()`;
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 92c3169..9444fc6 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -86,8 +86,8 @@ export function setMountActions({ triggerPrimaryAction, activateIsland }) {
   _activateIslandImpl = activateIsland;
 }
 
-function triggerPrimaryAction(key) {
-  if (_triggerPrimaryActionImpl) _triggerPrimaryActionImpl(key);
+function triggerPrimaryAction(key, variant) {
+  if (_triggerPrimaryActionImpl) _triggerPrimaryActionImpl(key, variant);
 }
 
 /** HTML-escape a value (null/undefined -> empty string) -- local copy,
@@ -182,6 +182,14 @@ async function api(path, options) {
 //                 `listRenderer` are not mutually exclusive; only
 //                 `primaryAction` and `createPanel` must stay paired on
 //                 the same side (creation_island.py rule 11).
+//   secondaryAction: { label, handler } | undefined (TICKET-0099, G1) --
+//                 a second shell-band button beside the primary one, for a
+//                 page that creates two kinds of record. Its handler calls
+//                 triggerPrimaryAction with the SAME island key as
+//                 primaryAction plus a literal variant string, which that
+//                 component's exported primaryAction(variant) receives;
+//                 never declared without a routed primaryAction
+//                 (creation_island.py rule 11b).
 // }
 // Every Création page is a registry entry. No page renders outside it.
 
@@ -266,6 +274,7 @@ export const CREATION_TABS = {
     islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
     createPanel: null,
     primaryAction: { label: '+ Ajouter une compétence', handler: () => triggerPrimaryAction('entitySheet') },
+    secondaryAction: { label: '+ Ajouter un système', handler: () => triggerPrimaryAction('entitySheet', 'system') },
   },
   region: {
     label: 'Région',
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 017f9df..9363718 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17404,6 +17404,23 @@ left to mount. Its ledger line moved whole into `entitySheet`'s
 `retiredPrefixes`, and the registry header names the exception: an
 absorbed surface moves its line, it never drops it.
 
+## A SECOND BUTTON IN THE SHELL BAND (TICKET-0099) -- SECONDARYACTION (BRIEF-0099-c, no schema change)
+
+**G1.** A `CREATION_TABS` entry may declare `secondaryAction: { label,
+handler }`, rendered by the shell band just before its primary button.
+Compétences uses it for « + Ajouter un système » beside « + Ajouter une
+compétence ». The handler reuses the primary route with a variant --
+`triggerPrimaryAction('entitySheet', 'system')` -- so `mount.js` forwards
+the variant to the component's own `primaryAction(variant)`: no second
+mount-action function, rule 8's confinement unchanged.
+`creation_island.py` rule 11b holds the pairing (same key as a routed
+primary action, two literals); `page_contract.py` holds the label to one
+occurrence, in the registry.
+
+**Rejected.** G2, a generic `actions: [...]` list: reactivates when a
+second tab asks for a second button, or this tab for a third. G3, the
+button in the list header: not where the creator asked for it.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/creation_island.py b/tooling/verify/checks/creation_island.py
index d005abe..ccc00b2 100644
--- a/tooling/verify/checks/creation_island.py
+++ b/tooling/verify/checks/creation_island.py
@@ -110,6 +110,14 @@ comparison.
       `createPanel` field at all passes unchecked; reactivate if
       `grep -n "createPanel" frontend/src/creation/tabs.js` ever shows a
       `primaryAction: {` site with no accompanying `createPanel` field.
+  11b. Secondary actions (TICKET-0099, BRIEF-0099-c, G1): every
+      CREATION_TABS entry declaring a `secondaryAction: { ... }` object
+      has a handler calling `triggerPrimaryAction('<key>', '<variant>')`
+      with two string literals, and its own `primaryAction.handler` calls
+      `triggerPrimaryAction('<key>')` with the SAME key -- a second button
+      is a variant of the routed primary action, never a separate route
+      and never a button without one. Zero `secondaryAction` objects
+      collected is a failure.
   12. Every registry key has a matching `COMPONENTS` entry in mount.js,
       whose value is the default import of `'./' + component`; every
       `.svelte` default import in mount.js is used by some `COMPONENTS`
@@ -180,6 +188,7 @@ def _report_and_exit(counts: dict | None = None) -> None:
         f"{counts['bindings']} component binding(s) agreed, "
         f"{counts['events']} mount-action identifier(s) confined, "
         f"{counts['primary_actions']} island primaryAction(s) wired, "
+        f"{counts['secondary_actions']} secondaryAction(s) paired, "
         f"Creation.svelte mounts no component"
     )
     sys.exit(0)
@@ -936,6 +945,43 @@ def _rule11_pairing(tabs_src: str, entries: dict[str, dict[str, object]]) -> int
     return count
 
 
+SECONDARY_CALL_RE = re.compile(r"""triggerPrimaryAction\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""")
+PRIMARY_CALL_RE = re.compile(r"""triggerPrimaryAction\(\s*['"]([^'"]+)['"]\s*\)""")
+
+
+def _rule11b_secondary(tabs_src: str) -> int:
+    tabs_registry_src = _braced_block(tabs_src, r"export const CREATION_TABS\s*=\s*\{")
+    if not tabs_registry_src:
+        fail(f"{TABS_FILE}: CREATION_TABS registry literal not found")
+        return 0
+    count = 0
+    for entry_name in _top_level_keys(tabs_registry_src):
+        entry_src = _entry_block(tabs_registry_src, entry_name)
+        sa_src = _braced_block(entry_src, r"secondaryAction\s*:\s*\{")
+        if not sa_src:
+            continue
+        sec_m = SECONDARY_CALL_RE.search(sa_src)
+        if not sec_m:
+            fail(f"CREATION_TABS.{entry_name}: secondaryAction.handler does not call "
+                 "triggerPrimaryAction('<key>', '<variant>') with two string literals")
+            continue
+        pa_src = _braced_block(entry_src, r"(?<!secondary)primaryAction\s*:\s*\{")
+        pri_m = PRIMARY_CALL_RE.search(pa_src) if pa_src else None
+        if not pri_m:
+            fail(f"CREATION_TABS.{entry_name}: declares a secondaryAction without a primaryAction "
+                 "routed through triggerPrimaryAction('<key>')")
+            continue
+        if pri_m.group(1) != sec_m.group(1):
+            fail(f"CREATION_TABS.{entry_name}: secondaryAction routes to {sec_m.group(1)!r} but "
+                 f"primaryAction routes to {pri_m.group(1)!r} -- a secondary action is a variant "
+                 "of the primary route, never a second route")
+            continue
+        count += 1
+    if count == 0:
+        fail("rule11b: zero paired secondaryAction(s) collected -- a rule that passes on nothing proves nothing")
+    return count
+
+
 # --------------------------------------------------------------------------
 # C-03: rule 12, COMPONENTS agreement
 # --------------------------------------------------------------------------
@@ -1404,6 +1450,7 @@ def main() -> None:
     state_ok = _rule9_state_nulls(tabs_src, entries)
     dispatch_ok = _rule10_unconditional_dispatch(tabs_src)
     primary_action_count = _rule11_pairing(tabs_src, entries)
+    secondary_action_count = _rule11b_secondary(tabs_src)
     stripped_mount = _strip_js_comments(mount_src, fail, str(MOUNT_FILE))
     binding_count = _rule12_component_bindings(stripped_mount, entries, fail) if stripped_mount is not None else 0
     tag_count = _rule13_creation_mounts_nothing(creation_svelte_src, fail)
@@ -1435,6 +1482,7 @@ def main() -> None:
             "bindings": binding_count,
             "events": action_count,
             "primary_actions": primary_action_count,
+            "secondary_actions": secondary_action_count,
         }
     )
 
diff --git a/tooling/verify/checks/page_contract.py b/tooling/verify/checks/page_contract.py
index e9dae35..42edf59 100644
--- a/tooling/verify/checks/page_contract.py
+++ b/tooling/verify/checks/page_contract.py
@@ -316,6 +316,34 @@ def main() -> int:
             "control must not exist (BRIEF-0005-c)"
         )
 
+    # TICKET-0099/BRIEF-0099-c (G1): a page's second create button exists
+    # only as its registry secondaryAction, rendered by the shell band —
+    # "Ajouter un système" once, in tabs.js, never an in-body control; the
+    # contract comment documents the field.
+    if contract_comment_m and "secondaryAction" not in contract_comment_m.group(0):
+        failures.append(
+            f"CREATION_TABS entry-contract comment does not document 'secondaryAction' in {TABS_JS} (BRIEF-0099-c)"
+        )
+    if "activeEntry.secondaryAction.handler" not in creation_svelte:
+        failures.append(
+            "Creation.svelte's shell band does not render activeEntry.secondaryAction (BRIEF-0099-c)"
+        )
+    system_occurrences = 0
+    system_sites = []
+    if CREATION_SRC.is_dir():
+        for path in CREATION_SRC.rglob("*"):
+            if path.is_file() and path.suffix in (".js", ".svelte"):
+                n = path.read_text(encoding="utf-8").count("Ajouter un système")
+                if n:
+                    system_occurrences += n
+                    system_sites.append(path.name)
+    if system_occurrences != 1 or system_sites != ["tabs.js"]:
+        failures.append(
+            f"'Ajouter un système' appears {system_occurrences} time(s) in {system_sites} under "
+            f"{CREATION_SRC} — expected exactly once, in tabs.js (the registry's secondaryAction "
+            "label); an in-body control must not exist (BRIEF-0099-c)"
+        )
+
     # TICKET-0059 (BRIEF-0059-h commit 4): the add-form moved off static
     # markup onto Registre.svelte's own {#if addFormOpen} — collapsed by
     # construction (the node doesn't exist until toggled) is a STRONGER
````

## Scope OUT

- A generic `actions: [...]` list (G2), or a secondary button on any other tab.
- The button in the list header (G3).
- Any change to rule 8's confinement or to `setMountActions`.
- Hiding covered gaps (carried forward).
- Every earlier brief of the lot: done. This is the last brief.

## Invariants to defend

- **Every Création page is a `CREATION_TABS` entry rendered by the generic dispatcher; no page-specific branch outside it** (`page_contract.py`): the second button is registry data, rendered by the band from `activeEntry`, never a `competences` literal in `Creation.svelte`.
- **`activateIsland`/`triggerPrimaryAction` are defined once in `mount.js` and imported only by `Creation.svelte`** (`creation_island.py` rule 8): the variant is a parameter, never a second function.
- **`Sheet.svelte` selects from `sheetType`**: the variant only chooses which blank C-01 record fills an already-selected competences fiche.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of item 4 does not fail as stated.
- `creation_island.py` reports a mount-action count other than 8.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and files under `src/world_engine/cockpit/static/`.
- `creation_island.py` → `PASS … 8 mount-action identifier(s) confined, 11 island primaryAction(s) wired, 1 secondaryAction(s) paired …`.
- `page_contract.py`, `creation_tab_switch.py`, `creation_container_sizing.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` → `PASS`.
- Both named mutations of item 4 failed as stated.
- `corpus_gate.py` → 129/129.
- Live: the Compétences band shows « + Ajouter un système » then « + Ajouter une compétence »; the first opens « Nouveau système » with no Supprimer, Save creates it and the list shows it; a duplicate name shows the server's refusal in the status; the NPC band shows no second button.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A SECOND BUTTON IN THE SHELL BAND (TICKET-0099) -- SECONDARYACTION (BRIEF-0099-c, no schema change)` — in the diff. This is the last brief: after it the ticket goes to `/verify` and the live gate.
