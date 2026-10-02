<!-- slug: faction-registry-goals -->
# BRIEF 0102-A — "A registry field is a column of its model"

Lot: LOT-0102-faction-registry-goals.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0102-a, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on `main` (expected `3eda315` or a descendant that has not touched these files) before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/cockpit/crud/entities.py:125` → `ENTITY_TYPE_REGISTRY: dict[str, dict[str, Any]] = {`; `:187` → `                "options": ["", "global", "national", "regional", "local", "other"],`; `:189` → `            {"name": "goals", "label": "Goals", "kind": "textarea"},`
- `src/world_engine/cockpit/crud/entities.py:245` → `def _extension_dict(entity_type: str, ext: Any) -> dict:`; `:247` → `    return {f["name"]: getattr(ext, f["name"]) for f in spec["fields"]}`
- `src/world_engine/cockpit/crud/entities.py:117` → `ENTITY_BASE_FIELDS: list[dict[str, Any]] = [`; `:335` → `        setattr(entity, name, value)`
- `src/world_engine/models/canon_faction.py:22` → `class Faction(SQLModel, table=True):`; `:28` → `    # internal_structure/philosophy/internal_tensions/goals/aversion moved to`; no line of `:22-44` declares a `goals` attribute
- `src/world_engine/facets.py:64` → `    FacetSpec("visee", "collectif", "affirmation", "none", "Visées",`
- `src/world_engine/db.py:58` (± a few) → `    explicit_url = os.getenv("WORLD_ENGINE_DATABASE_URL")`
- `tooling/verify/checks/dynamic_ext_crud.py:51` → `    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"`
- `ls tooling/verify/checks/registry_model_columns.py` → no such file
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank line, `*Co-built with Claude, June 2026.*`

## Facts carried

### R-01 — the faction registry entry [M]
Opened: `src/world_engine/cockpit/crud/entities.py:125-201`
(`ENTITY_TYPE_REGISTRY`, the declaring file), whole file 915 lines.
Finding: `"faction"` declares six fields: `faction_type`,
`magic_knowledge_level`, `parent_faction_id`, `scope` (`:183-188`, its
`"options"` line at `:187`), then `{"name": "goals", "label": "Goals",
"kind": "textarea"}` at `:189`. `GET /api/entity-types` serves these fields
verbatim (`get_entity_types`, `:418-461`), and the Création form renders
them.
Consequence: removing `:189` removes the « Goals » field from the form; no
frontend edit (A1).

### R-02 — the `Faction` model [M]
Opened: `src/world_engine/models/canon_faction.py:22-44` (the model, the
declaring file).
Finding: columns `id`, `faction_type`, `magic_knowledge_level`,
`parent_faction_id`, `scope`. A comment at `:28-30` records that
`internal_structure/philosophy/internal_tensions/goals/aversion` moved to
facts in TICKET-0091, schema v2.06 (`visee` for goals).
Consequence: the registry field has no column (A2 rejected).

### R-03 — where the 500 is raised, and why the row survives [M]
Opened: `src/world_engine/cockpit/crud/entities.py` (`_extension_dict`
`:245-247`; `get_entity` `:520-541`; `create_entity` `:726-771`;
`update_entity` `:774-`; `_create_static_entity_core` `:596-670`).
Finding: `_extension_dict` reads `getattr(ext, f["name"])` for every
declared field (`:247`); its static-type callers are `get_entity` (`:525`),
`create_entity` (`:749`), `update_entity` (`:836`). On a `Faction` row this
raises `AttributeError: 'Faction' object has no attribute 'goals'`.
`create_entity` commits at `:732`, before building its response.
Consequence: removing the field fixes all three routes.

### R-05 — the registry against its models, enumerated [M]
Opened: an import of `ENTITY_TYPE_REGISTRY`, `ENTITY_BASE_FIELDS` and
`Entity`, comparing each `field["name"]` to `model.__table__.columns`.
Finding (raw output, `main`):
```
character missing in model: []
location missing in model: []
faction missing in model: ['goals']
item missing in model: []
base fields: ['name', 'internal_name', 'is_public', 'status'] missing: []
```
`_apply_base_fields` (`:331-335`) sets each base field on the `Entity` by
name, so a base field has the same failure mode.
Consequence: one defect only; C-01 covers both lists.

### R-08 — the verify corpus [M]
Opened: `tooling/verify/checks/corpus_gate.py` (run on `main`: 135/135),
`json_ui_boundary.py:1-30`, `dynamic_ext_crud.py:44-62`,
`src/world_engine/db.py:1-12, 50-60`.
Finding: no check reads a faction through the CRUD; no check compares the
registry to its models. With neither `WORLD_ENGINE_DATABASE_URL` nor
`WORLD_ENGINE_ENV` set, importing `world_engine.db` raises `RuntimeError`;
a check importing the CRUD sets the URL first (`dynamic_ext_crud.py:51`).
Consequence: C-01 sets the URL to a throwaway path and creates nothing.

### R-09 — the decision registry [M]
Opened: `tooling/verify/checks/decisions_index.py:10-17`;
`tooling/standards/ARCHITECTURE_DECISIONS.md` (last three lines `---`,
blank, `*Co-built with Claude, June 2026.*`).
Consequence: header `## … (BRIEF-0102-a, no schema change)`, above the
footer; `DECISIONS_INDEX.md` regenerated.

## Contracts

### C-01 — `registry_model_columns.py`
Produced by: A   Consumed by: the corpus gate, every later ticket
A stdlib + `world_engine` import check, no table created, no row read.
Sets `WORLD_ENGINE_DATABASE_URL` to `sqlite:///<tempdir>/check.db` before
importing `world_engine.cockpit.crud.entities` (`ENTITY_TYPE_REGISTRY`,
`ENTITY_BASE_FIELDS`) and `world_engine.models` (`Entity`).
- Extension volet: for every registry entry, every `field["name"]` is in
  `spec["model"].__table__.columns.keys()`; else `FAIL:
  ENTITY_TYPE_REGISTRY[<type>] declares field <name>, which is not a column
  of <Model> (<table>); the create discards it and every read of that type
  raises`.
- Base volet: every `ENTITY_BASE_FIELDS` name is in
  `Entity.__table__.columns.keys()`; else `FAIL: ENTITY_BASE_FIELDS declares
  field <name>, which is not a column of Entity`.
- Vacuous-proof: zero types, zero extension fields or zero base fields
  collected is a FAIL.
- An import failure is a FAIL naming the exception.
- PASS line: `PASS: registry_model_columns -- 4 registry type(s), 18
  extension field(s), 4 base field(s), each a column of its model`.

## Context

Since TICKET-0091 dropped `faction.goals` (schema v2.06), the creator-CRUD registry still declares it, so every faction create, read and update answers 500; a create commits before it raises. Nia locked A1 (remove the field: a faction's goals are `visee` facts), B1 (a G1 check holding every registry field to a column of its model) and C1 (no data repair in code).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
is not in the diff: regenerate it.

1. Apply the embedded diff. It:
   - `cockpit/crud/entities.py`: removes the faction `goals` field and puts in its place a three-line comment naming where a faction's goals live and which check holds the registry (A1);
   - new `tooling/verify/checks/registry_model_columns.py` per C-01 (B1);
   - the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Named mutations, each run then restored with `git checkout -- src/world_engine/cockpit/crud/entities.py` before committing:
   - re-insert `            {"name": "goals", "label": "Goals", "kind": "textarea"},` just above the new comment: `registry_model_columns.py` prints `FAIL: ENTITY_TYPE_REGISTRY['faction'] declares field 'goals', which is not a column of Faction (faction); the create discards it and every read of that type raises` and exits 1;
   - add `    {"name": "description", "label": "Description", "kind": "textarea"},` to `ENTITY_BASE_FIELDS` after the `internal_name` line: it prints `FAIL: ENTITY_BASE_FIELDS declares field 'description', which is not a column of Entity` and exits 1.
4. Commit message: `fix(crud): faction registry drops the dead goals field; registry fields are model columns (BRIEF-0102-a)`.

````diff
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index 9ff5acd..d5a8221 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -186,7 +186,9 @@ ENTITY_TYPE_REGISTRY: dict[str, dict[str, Any]] = {
                 "name": "scope", "label": "Scope", "kind": "select",
                 "options": ["", "global", "national", "regional", "local", "other"],
             },
-            {"name": "goals", "label": "Goals", "kind": "textarea"},
+            # A faction's goals are `visee` facts (TICKET-0091, schema v2.06),
+            # edited in the sheet's facts editor -- never a field here: every
+            # field names a column of `model` (registry_model_columns.py).
         ],
     },
     "item": {
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index cf976ae..5498a87 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17592,6 +17592,24 @@ switches modes through three head buttons (the relations consumer's
 recentres Ego on a double-clicked child zone. Linking two nodes posts
 `connects_to`; the server derives the type.
 
+## A REGISTRY FIELD IS A COLUMN OF ITS MODEL (TICKET-0102) -- FACTION GOALS (BRIEF-0102-a, no schema change)
+
+**A1.** TICKET-0091 moved a faction's goals to `visee` facts and dropped
+`faction.goals` (schema v2.06), but `ENTITY_TYPE_REGISTRY["faction"]` kept a
+`goals` field: the form rendered it, the create discarded what was typed,
+and `_extension_dict` raised on it, so every faction create, read and
+update answered 500. The field is removed; a faction's goals are written in
+the sheet's facts editor, under « Visées ». **B1.** `registry_model_columns.py`
+holds every `ENTITY_TYPE_REGISTRY` field and every `ENTITY_BASE_FIELDS`
+field to a column of the model it writes; zero collected is a failure.
+
+**Rejected.** A2, restoring the column: undoes TICKET-0091's lore-as-facts
+decision; reactivates only if that decision is reopened. B2, a live
+create/read/update per static type: heavier than the defect class; reactivates
+on a second 500 on an entity route that `registry_model_columns.py` would not
+have caught. C2, a repair script for the roles a failed create never posted:
+Nia re-enters them through the fiche.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/registry_model_columns.py b/tooling/verify/checks/registry_model_columns.py
new file mode 100644
index 0000000..c7be142
--- /dev/null
+++ b/tooling/verify/checks/registry_model_columns.py
@@ -0,0 +1,98 @@
+"""G1 check: every field the creator-CRUD registry declares is a column of
+the model it writes (TICKET-0102, BRIEF-0102-a).
+
+TICKET-0091 dropped `faction.goals` (schema v2.06, the goals became `visee`
+facts) but `ENTITY_TYPE_REGISTRY["faction"]` kept a `goals` field. The form
+kept rendering it, the create silently discarded what was typed in it, and
+`_extension_dict`'s `getattr(ext, "goals")` raised: every faction create,
+read and update answered 500, while the corpus stayed green because no
+check read a faction.
+
+Two volets, each vacuous-proof:
+
+  a. Extension volet -- for every `ENTITY_TYPE_REGISTRY` entry, every
+     `field["name"]` is a column of `spec["model"].__table__`.
+  b. Base volet -- every `ENTITY_BASE_FIELDS` `field["name"]` is a column of
+     `Entity.__table__` (`_apply_base_fields` sets them by name).
+
+Zero registry types, zero extension fields or zero base fields collected is
+a FAIL: a registry that parses to nothing proves nothing.
+
+Import-only: no table is created and no row is read. The database URL is
+pointed at a throwaway path first because importing `world_engine.db`
+resolves it fail-closed.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src"
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _report(counts: dict[str, int]) -> int:
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        f"PASS: registry_model_columns -- {counts['types']} registry type(s), "
+        f"{counts['ext']} extension field(s), {counts['base']} base field(s), "
+        "each a column of its model"
+    )
+    return 0
+
+
+def main() -> int:
+    tmp_dir = tempfile.mkdtemp()
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
+    sys.path.insert(0, str(SRC))
+    try:
+        from world_engine.cockpit.crud.entities import ENTITY_BASE_FIELDS, ENTITY_TYPE_REGISTRY
+        from world_engine.models import Entity
+    except Exception as exc:  # noqa: BLE001 - a broken import is a FAIL
+        fail(f"world_engine.cockpit.crud.entities failed to import: {exc}")
+        return _report({})
+
+    counts = {"types": 0, "ext": 0, "base": 0}
+
+    for type_name, spec in ENTITY_TYPE_REGISTRY.items():
+        counts["types"] += 1
+        model = spec["model"]
+        columns = set(model.__table__.columns.keys())
+        for field in spec["fields"]:
+            counts["ext"] += 1
+            if field["name"] not in columns:
+                fail(
+                    f"ENTITY_TYPE_REGISTRY[{type_name!r}] declares field {field['name']!r}, "
+                    f"which is not a column of {model.__name__} ({model.__tablename__}); "
+                    "the create discards it and every read of that type raises"
+                )
+
+    entity_columns = set(Entity.__table__.columns.keys())
+    for field in ENTITY_BASE_FIELDS:
+        counts["base"] += 1
+        if field["name"] not in entity_columns:
+            fail(f"ENTITY_BASE_FIELDS declares field {field['name']!r}, which is not a column of Entity")
+
+    if counts["types"] == 0:
+        fail("zero ENTITY_TYPE_REGISTRY types collected -- a rule that passes on nothing proves nothing")
+    if counts["ext"] == 0:
+        fail("zero extension fields collected -- a rule that passes on nothing proves nothing")
+    if counts["base"] == 0:
+        fail("zero ENTITY_BASE_FIELDS collected -- a rule that passes on nothing proves nothing")
+
+    return _report(counts)
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- Restoring `faction.goals` or any column dropped by TICKET-0091 (A2 rejected).
- A live create/read/update check per static type (B2 rejected; reactivates on a second 500 on an entity route that `registry_model_columns.py` would not have caught).
- Any data repair: deleting duplicate factions, re-posting lost role drafts, scanning for roleless factions (C1; Nia does it through the fiche).
- `_extension_dict` itself (making it tolerant of a missing attribute would hide the next mismatch instead of failing it), the region commit, the facts editor, `Sheet.svelte`'s save flow (drafts not reset after an error), any reader of `visee`.
- The governed-runtime type path (`entity_runtime.py`): its fields come from `entity_trait`, not from this registry.

## Invariants to defend

- **UI-visible data never lives in JSON** (`json_ui_boundary.py`): the registry edit removes a field and adds none; no `"kind": "json"` appears.
- **Creator-direct create helpers never commit in their core** (CLAUDE.md): the fix touches no create core and no commit boundary.
- No other invariant is in reach: no schema change, no write path, no prompt, no reader.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of item 3 does not fail as stated.
- `registry_model_columns.py` reports a field missing from a model other than through a mutation of item 3 (a second mismatch is Nia's decision, not a fix to make here).
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- The PASS line's counts differ from `4 / 18 / 4` because a later ticket added a registry type or field that is a real column: proceed, and report the counts.

REPORT-ONLY:
- Timing of the corpus run.
- Factions in the prod database whose roles or facets look incomplete: do not query or touch prod; mention nothing beyond what the checks print.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly `src/world_engine/cockpit/crud/entities.py`, `tooling/verify/checks/registry_model_columns.py`, `tooling/standards/ARCHITECTURE_DECISIONS.md`, `tooling/standards/DECISIONS_INDEX.md`.
- `registry_model_columns.py` → `PASS: registry_model_columns -- 4 registry type(s), 18 extension field(s), 4 base field(s), each a column of its model`.
- Both named mutations of item 3 failed as stated.
- `dynamic_ext_crud.py`, `json_ui_boundary.py`, `module_budget.py`, `function_length.py`, `decisions_index.py`, `claude_md_contract.py`, `pipeline_state.py` → `PASS`.
- `corpus_gate.py` → `136 check(s) discovered, 136 executed, 136 passed`.
- Live (Nia): Création → Factions → « + Nouveau » shows no « Goals » field; a new faction with a role in draft and a « Visées » fact saves with « Saved. » and opens with both; every existing faction opens and saves.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A REGISTRY FIELD IS A COLUMN OF ITS MODEL (TICKET-0102) -- FACTION GOALS (BRIEF-0102-a, no schema change)` — in the diff. No schema change, no CLAUDE.md change, no changelog entry.
