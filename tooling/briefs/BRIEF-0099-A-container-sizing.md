<!-- slug: container-sizing -->
# BRIEF 0099-A — "Every single-container Création tab sizes its container"

Lot: LOT-0099-competences-list-sheet.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0099-a, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0099`, cut from `main` at `5784471` or later, before applying anything. Halt if one has moved.

- `frontend/public/creation.css:333` → `#creation-prompts     { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }`, and no rule for `#creation-competences`, `#creation-registre` or `#creation-subjects` anywhere in the file
- `frontend/src/creation/tabs.js:263` → `    containers: ['creation-competences'],`; `:300` → `    containers: ['creation-registre'],`; `:331` → `    containers: ['creation-subjects'],`
- `CLAUDE.md:363` → `  fact that feeds it, never from \`activeTabKey\` -- enforced by \`creation_tab_switch.py\`.`
- `tooling/verify/checks/creation_container_sizing.py` → does not exist
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank line, `*Co-built with Claude, June 2026.*`

## Facts carried

### R-01 — the height chain's last link [M]
Opened: `frontend/public/shared.css:41` (`.app-view { flex: 1; min-height: 0;
display: flex; flex-direction: column; overflow: hidden; }`);
`frontend/public/creation.css:323-333` (the per-container rules);
`frontend/src/creation/Creation.svelte:235-236` (`#creation-competences`).
Finding: every tab container is a child of `.app-view`. A container with no
rule takes its content's height; `.app-view` clips it and nothing scrolls.
`#creation-competences` has no rule. `Competences.svelte:210-390` stacks four
sections in one column, each system a three-field form (~150 px).
Consequence: the reported symptom. F1 names the rule; B removes the container.

### R-02 — which containers lack a rule [M]
Opened: `frontend/src/creation/tabs.js:188-365` (every `containers:` list);
`frontend/public/creation.css:323-333`.
Finding: 15 entries; `lieux` holds two containers, the other 14 one each.
Three single containers have no rule (enumeration E1, gate (c)):
`creation-competences` (`tabs.js:263`), `creation-registre` (`:300`),
`creation-subjects` (`:331`).
Consequence: A fixes all three; the check makes a fourth impossible.

### R-03 — the queue-panel shape [M]
Opened: `frontend/public/shared.css:81-93` (`.queue-panel { flex: 1;
min-height: 0; display: flex; flex-direction: column; }`, `.queue-body { flex:
1; min-height: 0; overflow-y: auto; … }`); `Queue.svelte:30`,
`Prompts.svelte:206`, `Registre.svelte:138`, `SubjectWorklist.svelte:28` (each
renders `<div class="queue-panel">` at its root); `creation.css:332-333`
(`#creation-queue`/`#creation-prompts { flex: 1; min-height: 0; display: flex;
flex-direction: column; overflow: hidden; }`).
Consequence: Registre and Sujets take that exact rule (a fixed header, a
scrolling body). A's transient Compétences rule scrolls the whole container
instead (`overflow-y: auto`, the `#creation-region` shape, `creation.css:330`),
because its stacked sections are not a queue-body.

### R-04 — what already guards the chain [M]
Opened: `tooling/verify/checks/shell_height_chain.py:71-130` (implementation).
Finding: rule 1 bans `100vh`; rule 2 checks `:global(#app)` and
`.shell-layout` in `App.svelte`. Nothing examines a tab container.
Consequence: `creation_container_sizing.py` (C-08) is new, not an extension.

### R-05 — CSS placement and the build [M]
Opened: `tooling/verify/checks/stylesheet_partition.py:321-336` (rule 2
implementation: a top-level selector in two sheets fails), `:385-400` (rule 6:
`static/creation.css` must byte-match `frontend/public/creation.css`);
`frontend/vite.config.js:1-18` (`outDir: '../src/world_engine/cockpit/static'`,
`emptyOutDir: true`); `frontend/package.json` (`build`: `vite build && node
scripts/write-manifest.mjs`).
Finding: the source of truth is `frontend/public/creation.css`; `npm run build`
copies it into `static/` (measured on the prototype); the three new selectors
are unique.
Consequence: every brief edits `frontend/public/` only and rebuilds.

### R-18 — ticket arrows [M]
Opened: `tooling/verify/checks/pipeline_state.py:108-114` (from `brief` status
on, every Machine arrow must resolve to a file under `tooling/verify/checks/`);
`tooling/verify/run.py:10-23` (`LINK`, `machine_checks`).
Consequence: A creates `creation_container_sizing.py` (dependency graph).

### R-19 — CLAUDE.md [M]
Opened: `CLAUDE.md:20-23` (Stack: "an editor plus a system-grouped
catalogue"), `:129` (Invariants heading), `:360-365`;
`tooling/verify/checks/claude_md_contract.py:1-40` (38 000-character budget,
100-character lines, no `TICKET-`/`BRIEF-` in Invariants). File at 36 280
characters.
Consequence: A adds a three-line invariant; B rewords line 22.

### R-20 — the decision registry [M]
Opened: `tooling/verify/checks/decisions_index.py:14-40` (strict header
pattern for new entries; index must equal a regeneration);
`tooling/glue/gen_decisions_index.py:46-53`; the archive's footer
(`---` / `*Co-built with Claude, June 2026.*`).
Consequence: each brief inserts its entry above the footer and regenerates
`DECISIONS_INDEX.md`.

## Contracts

### C-08 — `creation_container_sizing.py`
Produced by: A   Consumed by: B, C (must stay green)
For every `CREATION_TABS` entry whose `containers` list holds exactly one id X,
`frontend/public/creation.css` (comments stripped) holds a rule whose selector
is exactly `#X` declaring `flex: 1` and `min-height: 0`. Entries with two or
more containers are counted, not examined. Zero entries, zero single-container
entries, or an entry with no parseable `containers` is a FAIL.

## Context

Nia's Compétences tab clips everything below its third system: its container has no sizing rule (R-01), and Registre and Sujets carry the same latent defect (R-02). This brief closes the defect class for every single-container tab with a check, before B moves Compétences onto the shared editor area.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `tooling/verify/checks/creation_container_sizing.py` (C-08);
   - adds three rules to `frontend/public/creation.css`, right under `#creation-prompts`: `#creation-registre` and `#creation-subjects` in the `#creation-queue` shape (R-03), and a transient `#creation-competences { flex: 1; min-height: 0; overflow-y: auto; }` that BRIEF-0099-B deletes with its container;
   - adds the invariant to `CLAUDE.md` under the `creation_tab_switch.py` bullet;
   - appends the decision entry above the footer of `tooling/standards/ARCHITECTURE_DECISIONS.md`.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build` (copies `public/creation.css` into `src/world_engine/cockpit/static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutation, then restore: delete the `#creation-registre` line from `frontend/public/creation.css`, run `python tooling/verify/checks/creation_container_sizing.py` → it must print `FAIL: CREATION_TABS.registre: creation.css has no '#creation-registre' rule …` and exit 1. Restore the line (`git checkout -- frontend/public/creation.css`) before committing.
5. Commit message: `fix(creation): every single-container tab sizes its container (BRIEF-0099-a)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index f848b9e..9751f7b 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -361,6 +361,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   (`showCreationSubTab`), BEFORE `activeTabKey` moves and on every change, never per
   registry entry; and `Sheet.svelte` selects its render branch from `sheetType`, the same
   fact that feeds it, never from `activeTabKey` -- enforced by `creation_tab_switch.py`.
+- A Création tab that owns a single container sizes it in `frontend/public/creation.css`
+  (`flex: 1; min-height: 0`), so its content scrolls instead of being clipped -- enforced by
+  `creation_container_sizing.py`.
 - Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the
   same body — enforced by `effect_self_write.py`.
 - **The lore renderer receives rows, never a `Session`,** and only the `answered` verdict reaches
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index 295014b..dc17cbd 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -331,6 +331,9 @@ input.notes::placeholder { color: var(--muted); }
 #creation-constructeur { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 20px; }
 #creation-queue       { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-prompts     { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
+#creation-registre    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
+#creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
+#creation-competences { flex: 1; min-height: 0; overflow-y: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 8e2d1d1..883d4ac 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17356,6 +17356,22 @@ mention of every new fact, so the tokenizer records it in « Noms à lier ».
 **Rejected.** A free field for an entity id or an unlisted name: the
 creator never recalls names (K1 of TICKET-0095).
 
+## EVERY SINGLE-CONTAINER CRÉATION TAB SIZES ITS CONTAINER (TICKET-0099) -- THE LAST LINK OF THE HEIGHT CHAIN (BRIEF-0099-a, no schema change)
+
+**F1.** `.app-view` clips what overflows it. A tab container with no rule of
+its own takes its content's height, so past one window of content nothing
+scrolls: the Compétences tab lost its system form and its catalogue at three
+systems, and Registre and Sujets carried the same latent defect.
+`creation_container_sizing.py` requires, for every `CREATION_TABS` entry
+with exactly one container, a `#<id>` rule in `frontend/public/creation.css`
+declaring `flex: 1` and `min-height: 0`. Registre and Sujets take the Queue/
+Prompts shape (a fixed header, a scrolling body); Compétences scrolls whole
+until it moves onto the shared editor area.
+
+**Not examined.** An entry with several containers (`lieux`, whose room
+batch panel stacks under the editor area) decides its own split; the check
+counts it in its PASS line instead of guessing.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/creation_container_sizing.py b/tooling/verify/checks/creation_container_sizing.py
new file mode 100644
index 0000000..15020d9
--- /dev/null
+++ b/tooling/verify/checks/creation_container_sizing.py
@@ -0,0 +1,171 @@
+"""G1 check: every single-container Création tab sizes its container
+(TICKET-0099, BRIEF-0099-a).
+
+`.app-view` (shared.css) is a `display:flex; flex-direction:column;
+overflow:hidden` column. A tab container with no rule of its own takes
+its content's height, so once the content outgrows the window it is
+clipped and nothing scrolls -- the Compétences tab lost its system form
+and its catalogue this way at three systems, and Registre and Sujets
+carried the same latent defect. `shell_height_chain.py` holds the chain
+down to the shell only; this check holds its last link, per tab.
+
+Same idiom as shell_height_chain.py: module-level FAILURES, fail(),
+_report_and_exit(counts), ROOT via parents[3], stdlib only, no DB, no
+subprocess. Vacuous-proof: a missing file, a registry that parses to zero
+entries, or zero single-container entries is a FAILURE.
+
+  1. `frontend/src/creation/tabs.js` holds an `export const CREATION_TABS`
+     literal; every top-level entry's `containers: [...]` parses to string
+     ids. An entry with no parseable `containers` list is a FAILURE.
+  2. For every entry whose `containers` list holds EXACTLY ONE id X,
+     `frontend/public/creation.css` (comments stripped) holds a rule whose
+     selector is exactly `#X` and whose body declares both `flex: 1` and
+     `min-height: 0`. A missing rule, or a rule missing either
+     declaration, is a FAILURE naming the entry and the id.
+
+Entries with two or more containers (today: `lieux`, whose second
+container is a panel stacked under the editor area) are not examined:
+which of their containers takes the remaining height is that entry's own
+layout decision, not a property of the tab. They are counted in the PASS
+line so the exclusion is visible, never silent.
+"""
+from __future__ import annotations
+
+import re
+import sys
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[3]
+TABS_FILE = ROOT / "frontend" / "src" / "creation" / "tabs.js"
+CREATION_CSS = ROOT / "frontend" / "public" / "creation.css"
+
+CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
+CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
+CONTAINERS_RE = re.compile(r"\bcontainers\s*:\s*\[([^\]]*)\]")
+ID_RE = re.compile(r"""['"]([^'"]+)['"]""")
+FLEX_ONE_RE = re.compile(r"(^|[;\s])flex\s*:\s*1\s*(;|$)")
+MIN_HEIGHT_ZERO_RE = re.compile(r"(^|[;\s])min-height\s*:\s*0\s*(;|$)")
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _report_and_exit(counts: dict | None = None) -> None:
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        sys.exit(1)
+    print(
+        f"PASS: creation_container_sizing — {counts['single']} single-container "
+        f"entr(y/ies) size their container (flex: 1; min-height: 0); "
+        f"{counts['multi']} multi-container entr(y/ies) not examined"
+    )
+    sys.exit(0)
+
+
+def _braced_block(text: str, start_pattern: str) -> str:
+    m = re.search(start_pattern, text)
+    if not m:
+        return ""
+    brace_start = text.find("{", m.end() - 1)
+    if brace_start == -1:
+        return ""
+    depth = 0
+    for i in range(brace_start, len(text)):
+        if text[i] == "{":
+            depth += 1
+        elif text[i] == "}":
+            depth -= 1
+            if depth == 0:
+                return text[brace_start:i + 1]
+    return ""
+
+
+def _top_level_entries(registry_src: str) -> list[tuple[str, str]]:
+    """(key, entry source) for every top-level entry, walked brace by brace
+    so a nested object never passes for a sibling entry."""
+    inner = registry_src[1:-1]
+    entries = []
+    key_re = re.compile(r"(\w+)\s*:\s*\{")
+    idx, n = 0, len(inner)
+    while idx < n:
+        m = key_re.search(inner, idx)
+        if not m:
+            break
+        brace_start = inner.find("{", m.end() - 1)
+        depth, end = 0, -1
+        for i in range(brace_start, n):
+            if inner[i] == "{":
+                depth += 1
+            elif inner[i] == "}":
+                depth -= 1
+                if depth == 0:
+                    end = i
+                    break
+        if end == -1:
+            fail(f"{TABS_FILE}: CREATION_TABS entry {m.group(1)!r} has no balanced closing brace")
+            break
+        entries.append((m.group(1), inner[brace_start:end + 1]))
+        idx = end + 1
+    return entries
+
+
+def _css_rules() -> dict[str, str]:
+    text = CSS_COMMENT_RE.sub("", CREATION_CSS.read_text(encoding="utf-8"))
+    rules: dict[str, str] = {}
+    for selector, body in CSS_RULE_RE.findall(text):
+        rules[selector.strip()] = body
+    return rules
+
+
+def main() -> None:
+    if not TABS_FILE.is_file():
+        fail(f"{TABS_FILE} does not exist")
+        _report_and_exit()
+    if not CREATION_CSS.is_file():
+        fail(f"{CREATION_CSS} does not exist")
+        _report_and_exit()
+
+    registry_src = _braced_block(TABS_FILE.read_text(encoding="utf-8"), r"export const CREATION_TABS\s*=\s*\{")
+    if not registry_src:
+        fail(f"{TABS_FILE}: 'export const CREATION_TABS = {{' literal not found")
+        _report_and_exit()
+
+    entries = _top_level_entries(registry_src)
+    if not entries:
+        fail(f"{TABS_FILE}: CREATION_TABS parsed to zero entries")
+        _report_and_exit()
+
+    rules = _css_rules()
+    single = multi = 0
+    for key, entry_src in entries:
+        m = CONTAINERS_RE.search(entry_src)
+        ids = ID_RE.findall(m.group(1)) if m else []
+        if not ids:
+            fail(f"CREATION_TABS.{key}: no parseable 'containers: [...]' list")
+            continue
+        if len(ids) > 1:
+            multi += 1
+            continue
+        single += 1
+        container = ids[0]
+        body = rules.get(f"#{container}")
+        if body is None:
+            fail(f"CREATION_TABS.{key}: {CREATION_CSS.name} has no '#{container}' rule — "
+                 "the container takes its content's height and nothing scrolls")
+            continue
+        if not FLEX_ONE_RE.search(body):
+            fail(f"CREATION_TABS.{key}: '#{container}' does not declare 'flex: 1'")
+        if not MIN_HEIGHT_ZERO_RE.search(body):
+            fail(f"CREATION_TABS.{key}: '#{container}' does not declare 'min-height: 0'")
+
+    if single == 0:
+        fail("zero single-container CREATION_TABS entries collected — the scan proved nothing")
+    _report_and_exit({"single": single, "multi": multi})
+
+
+if __name__ == "__main__":
+    main()
````

## Scope OUT

- Any change to `Competences.svelte` or its tab entry: BRIEF-0099-B replaces both.
- The `lieux` tab's split between `#creation-editor-area` and `#batch-panel-wrap` (carried forward).
- Any change to `shell_height_chain.py`.
- Every later brief of the lot: B (the record tab), C (the add-system button).

## Invariants to defend

- **The shell owns one height authority** (`shell_height_chain.py`): no `100vh`, anywhere. The new rules use `flex: 1; min-height: 0` only.
- **Stylesheets stay partitioned** (`stylesheet_partition.py`): edit `frontend/public/creation.css` only, never `static/`; the three selectors must not exist in another sheet.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `creation_container_sizing.py` fails after the diff on an entry other than the three named in R-02.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails, or `frontend_build_fresh.py`/`stylesheet_partition.py` stays red after the rebuild.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` rewrites `.build-manifest.json` with a new `built_at` only: commit it.

REPORT-ONLY:
- Before this brief's commit, `pipeline_state.py` (and with it `corpus_gate.py`) fails on `TICKET-0099-competences-list-sheet.md: Machine-checkable arrow 'creation_container_sizing.py' does not resolve …`: the ticket was deposited at `brief` status before the check existed (R-18). This brief creates the file; the failure must be gone after the commit.
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly: `CLAUDE.md`, `frontend/public/creation.css`, `src/world_engine/cockpit/static/creation.css`, `src/world_engine/cockpit/static/.build-manifest.json`, `tooling/standards/ARCHITECTURE_DECISIONS.md`, `tooling/standards/DECISIONS_INDEX.md`, `tooling/verify/checks/creation_container_sizing.py`.
- `creation_container_sizing.py` → `PASS: creation_container_sizing — 14 single-container entr(y/ies) size their container (flex: 1; min-height: 0); 1 multi-container entr(y/ies) not examined`.
- The named mutation of Scope IN item 4 failed as stated.
- `stylesheet_partition.py`, `claude_md_contract.py`, `decisions_index.py`, `frontend_build_fresh.py` → `PASS`.
- `corpus_gate.py` → 129/129.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `EVERY SINGLE-CONTAINER CRÉATION TAB SIZES ITS CONTAINER (TICKET-0099) -- THE LAST LINK OF THE HEIGHT CHAIN (BRIEF-0099-a, no schema change)` and the CLAUDE.md invariant — both in the diff.
