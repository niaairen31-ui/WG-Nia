<!-- slug: proposal-producers -->
# BRIEF 0115-C — "Who proposed it is one closed list -- proposal_producers.py; Journée's objective event is the engine's (no schema change)"

Lot: LOT-0115-creator-dashboard.md (authoritative on conflict)
Depends on: BRIEF-0115-B

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after the previous brief of this lot).

- `src/world_engine/day_events.py` -> its one `ProposedMutation(` with `            proposed_by="local_ai",`
- `src/world_engine/observation_runner.py` -> `        mutation.proposed_by = OBSERVED_PROPOSED_BY`; `src/world_engine/observation_writes.py` -> `OBSERVED_PROPOSED_BY = "observed_scene"`
- `src/world_engine/cockpit/skill_progress.py` -> `SKILL_PROGRESS_PROPOSED_BY = "engine_roll"`
- `CLAUDE.md` -> the INV-14 bullet ending `review queue as AI proposals — never auto-applied. [no check]`
- No `src/world_engine/proposal_producers.py`, no `tooling/verify/checks/proposal_producers.py`.

## Facts carried

### R-04 — the producers [M]
Opened: every `ProposedMutation(` of `src/world_engine` (13: `tick.py` ×2 `local_ai_tick`; `analyzer_transcript.py` ×3 `local_ai_window`, `local_ai_overhearing`; `day_mutations.py` ×3 and `day_concordance.py` `local_ai`; `day_events.py:124` `local_ai` -- no model, Bt1 of 0119; `play_discovery.py`, `play_stream.py` `engine`; `skill_progress.py` the constant `engine_roll`) and `observation_runner.py:607` (a reassignment to `observed_scene`). CLAUDE.md INV-14 :194. Production (2026-10-12): `local_ai_tick`, `local_ai`, `local_ai_overhearing`, `local_ai_window`, `observed_scene`, `engine`.
Consequence: seven live producers, four legacy values; the check resolves module constants; INV-14 gains a check.

## Contracts

### C-03 — producers
Produced by: BRIEF-0115-C   Consumed by: D, (0121)
`proposal_producers.PRODUCERS: dict[value, (kind, label_fr)]` -- kinds in `PRODUCER_KINDS = ("model", "engine", "auto")`; `LEGACY_PRODUCERS`; `producer_label(value)`, `producer_kind(value)`; `UNKNOWN_PRODUCER_FR`. A new producer adds its entry in the brief that writes it.

## Context

B2 of the dashboard: `proposed_by` is the producer column. One value lied -- Journée's objective event, written by code, stamped like the day chain's model output -- so an acceptance rate « of the model » would have counted code.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `proposal_producers.py` (new, C-03);
   - `day_events.py`: `proposed_by="engine"`;
   - CLAUDE.md INV-14: names `emit_objective_events` and the list, enforced by `proposal_producers.py`;
   - creates check `proposal_producers.py` (PP1-PP4); appends the decision entry above the footer.
   The files it touches, exactly:
   - CLAUDE.md
   - src/world_engine/day_events.py
   - src/world_engine/proposal_producers.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/proposal_producers.py

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 44e1491..315d3b0 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -192,8 +192,10 @@ listed in `tooling/verify/baselines/invariant_ids.retired`. Each ends with
   paths, corrections are new compensating lines, and no UPDATE/DELETE
   endpoint or code path touches a `ledger` row. [no check]
 - **INV-14** `proposed_by='engine'` deterministic proposals
-  (`_propose_engine_injury`, `_propose_engine_discovery`) follow the same
-  review queue as AI proposals — never auto-applied. [no check]
+  (`_propose_engine_injury`, `_propose_engine_discovery`,
+  `emit_objective_events`) follow the same review queue as AI proposals —
+  never auto-applied. Every `proposed_by` written is named in
+  `proposal_producers.PRODUCERS`. -- enforced by `proposal_producers.py`
 - **INV-15** `skill_progress` is the one live auto-applied mutation: a roll's
   point (`proposed_by='engine_roll'`) applied through `_apply_mutation` at
   proposal time; `write_skill_progress` moves the rank. -- enforced by
diff --git a/src/world_engine/day_events.py b/src/world_engine/day_events.py
index 3c92484..1071397 100644
--- a/src/world_engine/day_events.py
+++ b/src/world_engine/day_events.py
@@ -7,7 +7,8 @@ loups ». When the day resolves such a step as completed (the dice band
 completion condition already says what has to have happened -- so Journée
 proposes that very event, beside the step's `agenda_step_change`, both
 reviewed by the creator (V1: proposing, never applying). Nothing is
-invented and no model is asked: every key comes from the leaf.
+invented and no model is asked: every key comes from the leaf, and the row
+says so -- `proposed_by='engine'` (INV-14, TICKET-0115).
 
 For each `event` leaf of the step's completion reached through `all` only
 (Q1: a leaf under `any`, `not` or `at_least` is not guaranteed) whose
@@ -121,7 +122,8 @@ def emit_objective_events(
             target_table="event",
             payload=payload,
             status="proposed",
-            proposed_by="local_ai",
+            # TICKET-0115 (B2): code proposed it, no model -- INV-14.
+            proposed_by="engine",
             rationale=(f"step {outcome.step_order} ({outcome.objective}) completed -- its objective is the event "
                        f"« {view.name} »"),
         ))
diff --git a/src/world_engine/proposal_producers.py b/src/world_engine/proposal_producers.py
new file mode 100644
index 0000000..16eb2e6
--- /dev/null
+++ b/src/world_engine/proposal_producers.py
@@ -0,0 +1,44 @@
+"""Who proposed a change: the closed list of `proposed_mutation.proposed_by` values, what each one is, and how the creator's dashboard names it (TICKET-0115, BRIEF-0115-C; decision B2 of the conditions series' dashboard).
+
+`proposed_by` is the producer column (B2): every producer stamps its own
+value, and `proposal_producers.py` (the check) holds every value written in
+`src/` to this list -- a new producer is a red gate until it is named here.
+
+`PRODUCERS` -- each value written today: its kind (`model`, a local model
+proposed it; `engine`, code proposed it, no model; `auto`, code applied it
+at once, INV-15) and its French label. `LEGACY_PRODUCERS` -- values older
+rows still carry and nothing writes any more: the dashboard names them,
+never mixes them with a live producer.
+"""
+
+from __future__ import annotations
+
+PRODUCERS: dict[str, tuple[str, str]] = {
+    "local_ai_window": ("model", "Play — analyse de fenêtre"),
+    "local_ai_overhearing": ("model", "Play — ce qui est entendu"),
+    "local_ai_tick": ("model", "Tick du monde"),
+    "local_ai": ("model", "Journée — modèle"),
+    "observed_scene": ("model", "Scène observée"),
+    "engine": ("engine", "Moteur — sans modèle"),
+    "engine_roll": ("auto", "Jet de Play — appliqué d'office"),
+}
+LEGACY_PRODUCERS: dict[str, str] = {
+    "local_ai_immediate": "Ancienne analyse par réplique",
+    "interpretation": "Ancienne interprétation de /say",
+    "claude": "Claude (ancien)",
+    "creator": "Créatrice (ancien)",
+}
+PRODUCER_KINDS: tuple[str, ...] = ("model", "engine", "auto")
+UNKNOWN_PRODUCER_FR = "Producteur inconnu"
+
+
+def producer_label(value: str | None) -> str:
+    """The dashboard's name for a `proposed_by` value."""
+    if value in PRODUCERS:
+        return PRODUCERS[value][1]
+    return LEGACY_PRODUCERS.get(value or "", UNKNOWN_PRODUCER_FR)
+
+
+def producer_kind(value: str | None) -> str | None:
+    """`model`, `engine` or `auto` for a live producer; None otherwise."""
+    return PRODUCERS[value][0] if value in PRODUCERS else None
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 24b7bfc..2dedc33 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19724,6 +19724,29 @@ would vanish). A positional diff everywhere (a reordered list reads as a
 rewrite). The verdict after the apply (the apply moves the step: M2 would
 compare the condition with its own consequence).
 
+## WHO PROPOSED IT IS ONE CLOSED LIST (TICKET-0115) -- `proposal_producers.py`; JOURNÉE'S OBJECTIVE EVENT IS THE ENGINE'S (BRIEF-0115-c, no schema change)
+
+**B2.** `proposed_mutation.proposed_by` already is the producer column; it
+lied once: Journée's objective event (`day_events.py`, Bt1 of 0119, no
+model) was stamped `local_ai` like the day chain's model output, so an
+acceptance rate « of the model » would have counted code. It is `engine`
+now, beside `_propose_engine_injury` and `_propose_engine_discovery`
+(INV-14). `proposal_producers.PRODUCERS` names every value written -- its
+kind (model, engine, auto) and the dashboard's French label -- and
+`LEGACY_PRODUCERS` the values older rows still carry. The check
+`proposal_producers.py` reads every `ProposedMutation(` and every
+`.proposed_by =` of the package (a module constant counts: `observed_scene`,
+`engine_roll`) and fails on a value the list does not name, or a listed
+value nobody writes; it also holds INV-14 (a model's or the engine's
+proposal is never built applied, and only an `auto` producer's module
+applies one itself).
+
+**Rejected.** B1, a separate `producer` column (reactivation: two real
+producers sharing one `proposed_by` value that must be told apart). Rows
+stamped `local_ai` by Journée's objective event before this brief stay as
+they are (history): the export carries `mutation_type` and `rationale`,
+which tell them apart.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/proposal_producers.py b/tooling/verify/checks/proposal_producers.py
new file mode 100644
index 0000000..0d587fd
--- /dev/null
+++ b/tooling/verify/checks/proposal_producers.py
@@ -0,0 +1,176 @@
+"""G1 check for TICKET-0115 -- every proposal names its producer from one closed list, and code-made proposals are reviewed like a model's (INV-14).
+
+BRIEF-0115-C's rules (B2 of the conditions series' dashboard).
+
+PP1 -- every producer is named (AST of `src/world_engine/**/*.py`). Every
+   `ProposedMutation(...)` call passes `proposed_by=`, and every
+   `<x>.proposed_by = ...` assignment sets one; each value is a string
+   literal or a name bound at module level to one (in any module of the
+   package). The values found equal `proposal_producers.PRODUCERS`' keys
+   exactly: a producer missing from the list, or a listed producer nobody
+   writes, fails. Zero sites is a FAILURE.
+PP2 -- the list (import). Each producer's kind is one of `PRODUCER_KINDS`
+   and its label is not empty; no value is both live and legacy;
+   `producer_label` names a legacy value and an unknown one.
+PP3 -- never auto-applied (AST). Every `ProposedMutation(...)` whose
+   producer is of kind `engine` or `model` passes no `status=` other than
+   `"proposed"`; outside `cockpit/routes/mutations.py`, only the modules
+   writing an `auto` producer call `_approve_apply_and_commit` or
+   `_apply_mutation`.
+PP4 -- Journée's objective event (AST). `day_events.py`'s one
+   `ProposedMutation(` passes `proposed_by="engine"`: no model is asked
+   (Bt1 of 0119).
+
+Stdlib plus the package's own `proposal_producers`; no DB.
+"""
+from __future__ import annotations
+
+import ast
+import pathlib
+import sys
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+PKG = ROOT / "src" / "world_engine"
+ROUTES = PKG / "cockpit" / "routes" / "mutations.py"
+DAY_EVENTS = PKG / "day_events.py"
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _modules() -> dict[pathlib.Path, ast.Module]:
+    return {p: ast.parse(p.read_text(encoding="utf-8")) for p in sorted(PKG.rglob("*.py"))}
+
+
+def _constants(trees: dict[pathlib.Path, ast.Module]) -> dict[str, set[str]]:
+    """Every module-level `NAME = "literal"` of the package, by name."""
+    out: dict[str, set[str]] = {}
+    for tree in trees.values():
+        for node in tree.body:
+            targets = node.targets if isinstance(node, ast.Assign) else \
+                [node.target] if isinstance(node, ast.AnnAssign) and node.value is not None else []
+            value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
+            if isinstance(value, ast.Constant) and isinstance(value.value, str):
+                for t in targets:
+                    if isinstance(t, ast.Name):
+                        out.setdefault(t.id, set()).add(value.value)
+    return out
+
+
+def _value(node: ast.AST, constants: dict[str, set[str]]) -> str | None:
+    if isinstance(node, ast.Constant) and isinstance(node.value, str):
+        return node.value
+    if isinstance(node, ast.Name) and len(constants.get(node.id, ())) == 1:
+        return next(iter(constants[node.id]))
+    return None
+
+
+def _is_ctor(node: ast.AST) -> bool:
+    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation"
+
+
+def _sites(trees, constants) -> list[tuple[pathlib.Path, int, str | None, ast.Call | None]]:
+    sites = []
+    for path, tree in trees.items():
+        for node in ast.walk(tree):
+            if _is_ctor(node):
+                kw = next((k for k in node.keywords if k.arg == "proposed_by"), None)
+                sites.append((path, node.lineno, _value(kw.value, constants) if kw else None, node))
+                if kw is None:
+                    fail(f"PP1: {path.relative_to(ROOT)}:{node.lineno} builds a ProposedMutation with no proposed_by")
+            elif isinstance(node, ast.Assign) and any(
+                    isinstance(t, ast.Attribute) and t.attr == "proposed_by" for t in node.targets):
+                sites.append((path, node.lineno, _value(node.value, constants), None))
+    return sites
+
+
+def check_pp1(sites) -> None:
+    from world_engine.proposal_producers import PRODUCERS
+
+    if not sites:
+        fail("PP1: no ProposedMutation construction found")
+        return
+    found = set()
+    for path, line, value, _call in sites:
+        if value is None:
+            fail(f"PP1: {path.relative_to(ROOT)}:{line} sets proposed_by to no literal or module constant")
+        else:
+            found.add(value)
+    if found != set(PRODUCERS):
+        fail(f"PP1: written {sorted(found)}, listed {sorted(PRODUCERS)}")
+
+
+def check_pp2() -> None:
+    from world_engine.proposal_producers import (
+        LEGACY_PRODUCERS, PRODUCER_KINDS, PRODUCERS, UNKNOWN_PRODUCER_FR, producer_label,
+    )
+
+    if not PRODUCERS or not LEGACY_PRODUCERS:
+        fail("PP2: an empty producer list")
+    for value, (kind, label) in PRODUCERS.items():
+        if kind not in PRODUCER_KINDS or not label.strip():
+            fail(f"PP2: {value!r} is ({kind!r}, {label!r})")
+    if set(PRODUCERS) & set(LEGACY_PRODUCERS):
+        fail(f"PP2: live and legacy {sorted(set(PRODUCERS) & set(LEGACY_PRODUCERS))}")
+    legacy = next(iter(LEGACY_PRODUCERS))
+    if producer_label(legacy) != LEGACY_PRODUCERS[legacy] or producer_label("nobody") != UNKNOWN_PRODUCER_FR:
+        fail("PP2: producer_label does not name a legacy or an unknown producer")
+
+
+def _calls(tree: ast.AST, names: set[str]) -> bool:
+    return any(isinstance(n, ast.Call) and ((isinstance(n.func, ast.Name) and n.func.id in names)
+                                            or (isinstance(n.func, ast.Attribute) and n.func.attr in names))
+               for n in ast.walk(tree))
+
+
+def check_pp3(trees, sites) -> None:
+    from world_engine.proposal_producers import PRODUCERS
+
+    auto_modules = set()
+    checked = 0
+    for path, line, value, call in sites:
+        kind = PRODUCERS.get(value or "", ("", ""))[0]
+        if kind == "auto":
+            auto_modules.add(path)
+        if call is None or kind not in ("engine", "model"):
+            continue
+        checked += 1
+        status = next((k.value for k in call.keywords if k.arg == "status"), None)
+        if status is not None and not (isinstance(status, ast.Constant) and status.value == "proposed"):
+            fail(f"PP3: {path.relative_to(ROOT)}:{line} builds a {kind} proposal not 'proposed'")
+    if not checked or not auto_modules:
+        fail(f"PP3: {checked} reviewed producer site(s), {len(auto_modules)} auto module(s)")
+    for path, tree in trees.items():
+        if path == ROUTES or path in auto_modules:
+            continue
+        if _calls(tree, {"_approve_apply_and_commit", "_apply_mutation"}):
+            fail(f"PP3: {path.relative_to(ROOT)} applies a proposal itself")
+
+
+def check_pp4(sites) -> None:
+    mine = [value for path, _line, value, call in sites if path == DAY_EVENTS and call is not None]
+    if mine != ["engine"]:
+        fail(f"PP4: day_events.py proposes as {mine}")
+
+
+def main() -> None:
+    sys.path.insert(0, str(ROOT / "src"))
+    trees = _modules()
+    sites = _sites(trees, _constants(trees))
+    check_pp1(sites)
+    check_pp2()
+    check_pp3(trees, sites)
+    check_pp4(sites)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        sys.exit(1)
+    print(f"PASS: proposal_producers -- {len(sites)} producer site(s), each naming a listed producer; "
+          "code-made proposals are reviewed")
+
+
+if __name__ == "__main__":
+    main()
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- Rewriting rows stamped `local_ai` by Journée's objective event before this brief (history).
- A separate `producer` column (B1, rejected).
- Every later brief of this lot: BRIEF-0115-D, E.

## Invariants to defend

INV-14 (an engine proposal is reviewed, never auto-applied) -- now enforced by PP3. INV-15 (`engine_roll` the one auto-applied mutation) -- PP3 allows only an `auto` producer's module to apply itself.

## Decision rights

STOP:
- A producer the Mini-RECON did not list (a fourteenth constructor): name it, do not guess its kind -- STOP.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- `lore_usage.py` timing out at 16-17 s inside the corpus: it does the same on `main` (pre-existing, R-09 of the lot).
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/proposal_producers.py` -> `PASS`.
- `python tooling/verify/checks/event_day.py` -> `PASS`.
- `python tooling/verify/checks/day_mutations.py` -> `PASS`.
- `python tooling/verify/checks/claude_md_contract.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (165 on the prototype; `lore_usage.py` may time out as on `main` -- REPORT-ONLY).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **PP1** -- `proposal_producers.py` `PRODUCERS`: `    "engine_roll": ("auto", "Jet de Play — appliqué d'office"),` -> (line deleted)
  - **PP2** -- `proposal_producers.py` `PRODUCERS`: `"engine": ("engine", "Moteur — sans modèle"),` -> `"engine": ("robot", "Moteur — sans modèle"),`
  - **PP3** -- `cockpit/play_stream.py` `_propose_engine_injury`: `        proposed_by="engine",` -> `        status="applied", proposed_by="engine",`
  - **PP4** -- `day_events.py` `emit_objective_events`: `            proposed_by="engine",` -> `            proposed_by="local_ai",`
- Live gate (Nia): Journée: a quest step whose objective is an event, completed: its proposed event's card shows the producer `engine`.
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

CLAUDE.md INV-14, ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
