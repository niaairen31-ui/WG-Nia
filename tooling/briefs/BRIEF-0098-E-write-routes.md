<!-- slug: write-routes -->
# BRIEF 0098-E — "Writing panel routes: questions, draft, commit, history"

Lot: LOT-0098-lore-writing.md (authoritative on conflict)
Depends on: BRIEF-0098-C, BRIEF-0098-D (wired here); BRIEF-0098-A (E1d)
Commit header for decisions: `(BRIEF-0098-e, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0098`, on the tree the previous brief left, before applying anything. Halt if one has moved.

- `src/world_engine/cockpit/app.py:62` → `from .routes import lore_choices as _routes_lore_choices`; `:122` → `app.middleware("http")(origin_guard)`; `:138` → `app.include_router(_routes_lore_choices.router)`
- `tooling/verify/checks/lore_isolation.py:98` → `    SRC / "lore_write_draft.py",` then `)`
- `tooling/verify/checks/lore_write.py:86` → `    "lore_write_apply.py", "writes/lore_entries.py", "lore_write_draft.py",`
- `src/world_engine/lore_mentions_read.py:30` → `def active_world_id(db: Session) -> Optional[str]:`
- `src/world_engine/cockpit/crud/entities.py:525` → `def _create_entity_core(body: EntityWriteBody, db: DbSession) -> Entity:`
- `CLAUDE.md:265` → `- **PC knowledge is written `is_secret=False`; `_normalize_knowledge` is`

## Facts carried

### R-11 — creating an entity [M]
Opened: `src/world_engine/cockpit/crud/entities.py:123-215`
(`ENTITY_TYPE_REGISTRY`), `:525-560` (`_create_entity_core`,
`_write_body_facets`), `:562-630` (static core); `cockpit/routes/regions.py:135-220`.
Finding: static types are exactly `character`, `location`, `faction`,
`item` (enumeration E4); the core never commits, flushes, raises
`HTTPException(422)` on a missing name, and is called from routes by
region, NPC agent and room batch (enumeration E5). `character_type`
defaults to `npc` in the registry fields.
Consequence: G3 is exactly the static registry; the route injects a
creator wrapping `_crud._create_entity_core` (C-02's `create_entity`), and
re-raises its `HTTPException` after a rollback.

### R-17 — the Lore shell [M]
Opened: `frontend/src/lore/Lore.svelte` (whole, 218 lines; tabs at 94-101);
`frontend/src/lore/namesPanel.svelte.js:1-60`;
`frontend/src/creation/sheetRequest.svelte.js:30-35` (`api`);
`src/world_engine/cockpit/crud/entities.py:474-483` (`GET /api/entities`);
`src/world_engine/lore_mentions_read.py:30-33` (`active_world_id`).
Finding: two tabs (`question`, `names`); panels keep state in a
`*.svelte.js` module; `api()` throws `Error(detail)`; `/api/entities` lists
the active world's entities with `type`, `name`, `status`.
Consequence: F adds a third tab and a state module in the same shape.

## Contracts

### C-02 — the proposal (family: entities, facts, memberships, controls)
Produced by: F (client), D (as a draft, C-05)   Consumed by: C (`validate`,
`apply_proposal`), E (`write_commit`)
```
{"statement": str (non-empty), "questions": str|null, "answers": str|null,
 "entities": [{"ref", "action": "create", "name", "type": character|location|faction|item}
            | {"ref", "action": "existing", "entity_id"}],
 "facts": [{"ref", "action": "create", "content", "facet" (non-typed), "aspect"?,
            "participants": [ref], "defaults": [scope], "knowers": [knower],
            "mentions"?: [{"name","category"}]}
         | {"ref", "action": "existing", "fact_id", "participants", "defaults", "knowers"}
         | {"ref", "action": "rewrite", "fact_id" (a bloc descriptive fact), "content",
            "participants", "defaults", "knowers"}],
 "memberships": [{"entity_ref" (character), "faction_ref" (faction)}],
 "controls": [{"owner_ref", "location_ref" (location)}]}
scope  = {"scope_type": "world"} | {"scope_type": faction|location|rencontre, "scope_ref": ref}
knower = {"entity_ref", "level" (ladder), "is_secret": bool, "is_incorrect": bool}
```
- `lore_write_apply.validate(db, world_id, proposal) -> refs` raises
  `ProposalError` (French message) on: missing statement; an entity ref
  twice; an entity action outside `create|existing`; a created type outside
  `ENTITY_TYPES`; an existing id that is not an ACTIVE entity of the world;
  a fact ref twice; a fact action outside `FACT_ACTIONS`; a ref to no
  entity; a typed or unknown facet; a `bloc` or `appellation` fact without
  exactly one participant; a fact id outside the world; participants on a
  typed fact; a rewrite of a non-bloc fact; an unknown scope, a world scope
  with a ref, a scope ref of the wrong type, the same scope twice; a knower
  twice on one fact, an unknown level, a non-bool flag; a membership whose
  sides are not character/faction; a control whose target is not a
  location; nothing to write.
- `apply_proposal(db, world_id, proposal, create_entity) -> ApplyResult`
  (`entry_id`, `written` {"table:action": n}, `skipped` [French notes]).
  Never commits. Order: entry, entities (flushed), facts, memberships,
  controls. Skips (and reports) a knower already holding the fact, a
  participant already attached, an identical default, an active
  membership, an existing `controls` pair. A write-site `ValueError`
  becomes `ProposalError`.
- `create_entity(name, type) -> Entity` is injected by the caller.
- `CREATED_BY = "creator_lore"`.

### C-05 — the draft
Produced by: D   Consumed by: E, F
- `lore_write_draft`: `QUESTIONS_USAGE = "lore_statement_questions"`,
  `PROPOSAL_USAGE = "lore_statement_to_proposal"`, `MAX_QUESTIONS = 3`,
  `MAX_CODED_FACTS = 200`, `WRITE_UNAVAILABLE_MESSAGE` (French),
  `CATEGORY_TYPE`.
- `draft_context(db, world_id, statement) -> DraftContext(entity_lines,
  coded)`; `draft_questions(db, world_id, statement) -> list[str]`;
  `draft_proposal(db, world_id, statement, answers="") -> dict` with keys
  `statement, answers, entities, facts, memberships, controls, notes,
  facets`. Each entity carries `status`: `matched` (`action: existing`,
  `entity_id`, `name`, `type`), `ambiguous` (`action: null`, `candidates`
  [{entity_id,name,type}]) or `new` (`action: create`, `type` from the
  category or null, `near` [{entity_id,name,type,score}]). Facts follow
  C-02 with `fact_id` resolved from the model's `code`. `facets` =
  [{name, label}] of the non-typed `FACETS`. `OllamaError` and
  `LlmParseError` propagate.
- Prompt variables: questions `statement, entities, facts`; proposal
  `facets, entities, facts, statement, answers`.

### C-06 — the writing routes (family)
Produced by: E   Consumed by: F
- `POST /api/lore/write/questions` `{statement}` -> `{"questions": [...]}`.
- `POST /api/lore/write/draft` `{statement, answers?}` -> C-05's draft.
- `POST /api/lore/write/commit` `{proposal}` -> `{"ok": true, "entry_id",
  "written", "skipped"}`; 422 `{detail}` on a refused proposal (rolled
  back).
- `GET /api/lore/write/entries` -> `{"entries": [{id, statement, questions,
  answers, created_at, rows: [{row_table, action, label}]}]}` (newest 50).
- Common: 400 with no active world; 422 on an empty statement; 503 with
  `WRITE_UNAVAILABLE_MESSAGE` when Ollama is down; 502 on an unparseable
  model reply; 403 from C-01 for a non-local writer.

## Context

The four routes the panel calls. They orchestrate only: drafting lives in D, writing in C, the history read in a new read module. A commit creates entities through the creator CRUD's commit-free core, the region commit's precedent.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `cockpit/routes/lore_write.py` (C-06) and `lore_write_read.py`; mounts the router in `cockpit/app.py`; adds both files to `lore_isolation.py`'s `PANEL_FILES`; adds the CLAUDE.md invariant above the « PC knowledge » line; extends `lore_write.py` (census: five files; E1, E2); appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): writing panel routes — questions, draft, commit, history (BRIEF-0098-e)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 96a2b70..f848b9e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -262,6 +262,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   reaches a canon row; the accept/reject cascade and link targets are
   re-derived server-side from raw client state; rejected/uncommitted/
   unresolved/self-referential targets write nothing.
+- **A lore statement commits whole or not at all, through `lore_write_apply.apply_proposal`.**
+  No model-emitted id reaches a canon row: facts by code, entities by name, both resolved in code
+  and confirmed by the creator; every row written is recorded in `lore_entry_row`.
 - **PC knowledge is written `is_secret=False`; `_normalize_knowledge` is
   NPC-only and forces `is_secret=True` — never reuse it for a PC.**
   `_normalize_player_knowledge` emits no `is_secret` key; `False` is
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index 43e67ef..7579d75 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -59,6 +59,7 @@ from .routes import day as _routes_day
 from .routes import link_agent as _routes_link_agent
 from .routes import lore as _routes_lore
 from .routes import lore_mentions as _routes_lore_mentions
+from .routes import lore_write as _routes_lore_write
 from .routes import lore_choices as _routes_lore_choices
 from .routes import mutations as _routes_mutations
 from .routes import npc_agent as _routes_npc_agent
@@ -136,6 +137,7 @@ app.include_router(_routes_observation.router)
 app.include_router(_routes_lore.router)
 app.include_router(_routes_lore_mentions.router)
 app.include_router(_routes_lore_choices.router)
+app.include_router(_routes_lore_write.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
 
diff --git a/src/world_engine/cockpit/routes/lore_write.py b/src/world_engine/cockpit/routes/lore_write.py
new file mode 100644
index 0000000..d4babbb
--- /dev/null
+++ b/src/world_engine/cockpit/routes/lore_write.py
@@ -0,0 +1,111 @@
+"""The Lore shell's writing panel routes (TICKET-0098, BRIEF-0098-E).
+
+A second bounded reopening of the Lore shell's read-only lock (the Q17d
+precedent): the creator writes lore in prose, answers at most one round of
+clarification questions (J3), corrects the draft, and commits it. Every
+model call lives in `lore_write_draft.py`, every write in
+`lore_write_apply.apply_proposal`, every history read in
+`lore_write_read.py`; this module orchestrates, runs no query and no model
+call, and commits once per commit request. The consultation pipeline is
+untouched: this module imports none of `lore_selectors`, `lore_query`,
+`lore_plan`, `lore_render`, `lore_prompt` (`lore_isolation.py` R17). Every
+POST passes the origin guard first (BRIEF-0098-A).
+
+Ollama down answers 503 with `lore_write_draft.WRITE_UNAVAILABLE_MESSAGE`
+(K1); nothing is written by a draft route, ever.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional
+
+from fastapi import APIRouter, Depends, HTTPException
+from pydantic import BaseModel
+from sqlmodel import Session
+
+from ... import lore_mentions_read as _world
+from ... import lore_write_apply as _apply
+from ... import lore_write_draft as _draft
+from ... import lore_write_read as _read
+from ...db import get_session
+from ...llm_parse import LlmParseError
+from ...ollama_client import OllamaError
+from .. import crud as _crud
+
+router = APIRouter()
+
+
+class StatementBody(BaseModel):
+    statement: str
+    answers: Optional[str] = None
+
+
+class CommitBody(BaseModel):
+    proposal: dict[str, Any]
+
+
+def _world_id(db: Session) -> str:
+    world_id = _world.active_world_id(db)
+    if world_id is None:
+        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
+    return world_id
+
+
+def _statement(body: StatementBody) -> str:
+    if not body.statement.strip():
+        raise HTTPException(status_code=422, detail="Le texte est vide.")
+    return body.statement
+
+
+@router.post("/api/lore/write/questions")
+def write_questions(body: StatementBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _world_id(db)
+    try:
+        questions = _draft.draft_questions(db, world_id, _statement(body))
+    except OllamaError as exc:
+        raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
+    except LlmParseError as exc:
+        raise HTTPException(status_code=502, detail=f"lore questions drafting failed: {exc}") from exc
+    return {"questions": questions}
+
+
+@router.post("/api/lore/write/draft")
+def write_draft(body: StatementBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _world_id(db)
+    try:
+        return _draft.draft_proposal(db, world_id, _statement(body), body.answers or "")
+    except OllamaError as exc:
+        raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
+    except LlmParseError as exc:
+        raise HTTPException(status_code=502, detail=f"lore proposal drafting failed: {exc}") from exc
+
+
+def _entity_creator(db: Session):
+    """C1: a minimal fiche through the creator CRUD's commit-free core; a
+    character is born an NPC."""
+    def create(name: str, entity_type: str):
+        extension = {"character_type": "npc"} if entity_type == "character" else {}
+        body = _crud.EntityWriteBody(entity={"type": entity_type, "name": name}, extension=extension)
+        return _crud._create_entity_core(body, db)
+    return create
+
+
+@router.post("/api/lore/write/commit")
+def write_commit(body: CommitBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _world_id(db)
+    try:
+        result = _apply.apply_proposal(db, world_id, body.proposal, _entity_creator(db))
+    except _apply.ProposalError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    except HTTPException:
+        db.rollback()
+        raise
+    db.commit()
+    return {"ok": True, "entry_id": result.entry_id, "written": result.written,
+            "skipped": result.skipped}
+
+
+@router.get("/api/lore/write/entries")
+def write_entries(db: Session = Depends(get_session)) -> dict:
+    return {"entries": _read.list_entries(db, _world_id(db))}
diff --git a/src/world_engine/lore_write_read.py b/src/world_engine/lore_write_read.py
new file mode 100644
index 0000000..100db8f
--- /dev/null
+++ b/src/world_engine/lore_write_read.py
@@ -0,0 +1,76 @@
+"""Reads for the Lore shell's writing panel (TICKET-0098, BRIEF-0098-E, M1).
+
+The panel's history view: the world's `lore_entry` rows, newest first, each
+with what it wrote, labelled for the creator (an entity's current name, a
+fact's rendered text, who knows which fact, a membership, a possession).
+A row whose target was deleted since is labelled as such, never dropped.
+Reads only.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .models import (
+    Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, LoreEntry,
+    LoreEntryRow, Relation,
+)
+from .prose_render import fact_text
+
+ENTRY_LIMIT = 50
+_DELETED = "(supprimé depuis)"
+
+
+def _name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else _DELETED
+
+
+def _fact_label(db: Session, fact_id: str) -> str:
+    fact = db.get(Fact, fact_id)
+    return fact_text(db, fact) if fact is not None else _DELETED
+
+
+def _label(db: Session, row: LoreEntryRow) -> str:
+    model = {"entity": Entity, "fact": Fact, "fact_participant": FactParticipant,
+             "fact_default": FactDefault, "knowledge": Knowledge, "relation": Relation,
+             "faction_membership": FactionMembership}[row.row_table]
+    target = db.get(model, row.row_id)
+    if target is None:
+        return _DELETED
+    if row.row_table == "entity":
+        return f"{target.name} ({target.type})"
+    if row.row_table == "fact":
+        return _fact_label(db, target.id)
+    if row.row_table == "fact_participant":
+        return f"{_name(db, target.entity_id)} — {_fact_label(db, target.fact_id)}"
+    if row.row_table == "fact_default":
+        scope = "tout le monde" if target.scope_type == "world" else \
+            f"{target.scope_type} {_name(db, target.scope_id)}"
+        return f"{scope} — {_fact_label(db, target.fact_id)}"
+    if row.row_table == "knowledge":
+        flags = "".join((" (secret)" if target.is_secret else "",
+                         " (croyance fausse)" if target.is_incorrect else ""))
+        return f"{_name(db, target.entity_id)} [{target.level}]{flags} — {_fact_label(db, target.fact_id)}"
+    if row.row_table == "relation":
+        return f"{_name(db, target.entity_a_id)} possède {_name(db, target.entity_b_id)}"
+    return f"{_name(db, target.entity_id)} membre de {_name(db, target.faction_id)}"
+
+
+def list_entries(db: Session, world_id: str) -> list[dict]:
+    """The world's newest `ENTRY_LIMIT` entries with their labelled rows."""
+    entries = db.exec(select(LoreEntry).where(LoreEntry.world_id == world_id).order_by(
+        LoreEntry.created_at.desc(), LoreEntry.id).limit(ENTRY_LIMIT)).all()
+    out = []
+    for entry in entries:
+        rows = db.exec(select(LoreEntryRow).where(LoreEntryRow.entry_id == entry.id).order_by(
+            LoreEntryRow.row_table, LoreEntryRow.id)).all()
+        out.append({
+            "id": entry.id, "statement": entry.statement, "questions": entry.questions,
+            "answers": entry.answers, "created_at": entry.created_at.isoformat(),
+            "rows": [{"row_table": r.row_table, "action": r.action, "label": _label(db, r)}
+                     for r in rows],
+        })
+    return out
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index f8e5336..7bda50f 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17314,6 +17314,29 @@ world's facts): reactivates if the model duplicates facts about entities the
 statement did not name. J2 (several clarification rounds): reactivates if
 one round regularly leaves the draft off.
 
+## THE LORE SHELL GETS A WRITING PANEL (TICKET-0098) -- FOUR ROUTES, ONE COMMIT (BRIEF-0098-e, no schema change)
+
+**H1 -- a second bounded reopening.** The Lore shell's read-only lock (0085)
+opens again, the Q17d way: `cockpit/routes/lore_write.py` serves the
+questions, the draft, the commit and the history. It runs no query and no
+model call, and commits once, in `write_commit`. Its modules join
+`lore_isolation.py`'s panel list, so none imports the consultation pipeline.
+
+**C1 -- a minimal fiche.** A new entity is created through the creator
+CRUD's commit-free core (`_create_entity_core`, the region commit's
+precedent), in the proposal's transaction; a character is born an NPC.
+
+**K1.** Ollama down answers 503 with `WRITE_UNAVAILABLE_MESSAGE`; the
+draft routes write nothing, ever. A refused proposal answers 422 with the
+French reason and rolls back.
+
+**M1 -- rereading a story.** `GET /api/lore/write/entries` lists the world's
+last fifty entries, each with a label per written row; a row whose target
+was deleted since is labelled, never dropped.
+
+**Rejected.** H2 (the panel in Création): reactivates if the panel ever
+needs a consultation module to work.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_isolation.py b/tooling/verify/checks/lore_isolation.py
index 89b1712..35d1d57 100644
--- a/tooling/verify/checks/lore_isolation.py
+++ b/tooling/verify/checks/lore_isolation.py
@@ -96,6 +96,9 @@ PANEL_FILES = (
     # TICKET-0098 (BRIEF-0098-D): the writing panel's modules.
     SRC / "lore_write_apply.py",
     SRC / "lore_write_draft.py",
+    # TICKET-0098 (BRIEF-0098-E): its route and history read.
+    SRC / "lore_write_read.py",
+    SRC / "cockpit" / "routes" / "lore_write.py",
 )
 PIPELINE_FILES = (LORE_SELECTORS_FILE, LORE_QUERY_FILE, LORE_PLAN_FILE, LORE_RENDER_FILE, LORE_PROMPT_FILE)
 
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index df29858..1cf1b8a 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -55,6 +55,20 @@ D2 -- prompts. `seed_pilot.LORE_WRITE_PROMPT_HEADS` holds exactly the usages
    `{placeholders}` of its user template; `apply_ticket_0098_lore_write_prompts.py`
    reads that tuple and embeds no prompt text; `lore_prompt.py` re-exports
    `prompt_load.load`, the loader the writing path imports.
+E1 -- routes (BRIEF-0098-E), through `TestClient(app, base_url=...)` on the
+   active fixture world, `lore_write_draft.chat` stubbed:
+   a. `POST /api/lore/write/questions` answers the questions; with Ollama
+      down it answers 503 with exactly `WRITE_UNAVAILABLE_MESSAGE`;
+   b. `POST /api/lore/write/draft` answers the draft; with Ollama down, 503;
+      no draft request changes any row count;
+   c. `POST /api/lore/write/commit` of a valid proposal creating a
+      character answers 200; the entity has its `character` row as an NPC;
+      `GET /api/lore/write/entries` lists the entry first, with a label per
+      row; an invalid proposal answers 422 and changes no row count;
+   d. the same commit with a non-local `Origin` answers 403 and changes no
+      row count.
+E2 -- thin route. `cockpit/routes/lore_write.py` contains no `select(` and
+   no `chat(`, and exactly one `.commit(` -- inside `write_commit`.
 C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
    `chat(`, no `.commit(`, and import neither `ollama_client` nor any
    `cockpit` module; `lore_write_draft.py` contains no `db.add(`, no
@@ -84,6 +98,7 @@ FAILURES: list[str] = []
 _CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
 _LORE_WRITE_FILES: frozenset[str] = frozenset({
     "lore_write_apply.py", "writes/lore_entries.py", "lore_write_draft.py",
+    "lore_write_read.py", "cockpit/routes/lore_write.py",
 })
 _PURE_FILES = ("lore_write_apply.py", "writes/lore_entries.py")
 _COUNTED_TABLES = ("entity", "fact", "fact_participant", "fact_default", "knowledge",
@@ -499,6 +514,98 @@ def check_d1() -> None:
             fail(f"D1e: the settled draft does not validate: {exc}")
 
 
+def check_e1() -> None:
+    from fastapi.testclient import TestClient
+    from sqlmodel import Session, select
+
+    from world_engine import lore_write_draft as lwd
+    from world_engine.cockpit.app import app
+    from world_engine.db import engine
+    from world_engine.models import Character, Entity, World
+    from world_engine.ollama_client import OllamaError
+
+    with Session(engine) as db:
+        ids = _fixture(db)
+        for world in db.exec(select(World)).all():
+            world.is_active = world.id == ids["world"]
+            db.add(world)
+        db.commit()
+    client = TestClient(app, base_url="http://127.0.0.1")
+    stub = _Stub([{"questions": ["Qui le sait ?"]}, OllamaError("down"),
+                  {"entities": [{"ref": "e1", "name": "Maëlle", "category": "person"}],
+                   "facts": [], "memberships": [], "controls": []}, OllamaError("down")])
+    original = lwd.chat
+    lwd.chat = stub
+    with Session(engine) as db:
+        before = _counts(db)
+    try:
+        body = {"statement": "Maëlle garde le Manoir Gris."}
+        resp = client.post("/api/lore/write/questions", json=body)
+        if resp.status_code != 200 or resp.json() != {"questions": ["Qui le sait ?"]}:
+            fail(f"E1a: questions answered {resp.status_code} {resp.text[:120]}")
+        resp = client.post("/api/lore/write/questions", json=body)
+        if resp.status_code != 503 or resp.json().get("detail") != lwd.WRITE_UNAVAILABLE_MESSAGE:
+            fail(f"E1a: Ollama down answered {resp.status_code} {resp.text[:120]}")
+        resp = client.post("/api/lore/write/draft", json=dict(body, answers="Tout le monde."))
+        if resp.status_code != 200 or resp.json()["entities"][0].get("entity_id") != ids["npc"]:
+            fail(f"E1b: draft answered {resp.status_code} {resp.text[:160]}")
+        resp = client.post("/api/lore/write/draft", json=body)
+        if resp.status_code != 503:
+            fail(f"E1b: Ollama down on draft answered {resp.status_code}")
+    finally:
+        lwd.chat = original
+    with Session(engine) as db:
+        if _counts(db) != before:
+            fail("E1b: a draft request changed rows")
+    proposal = {"statement": "Joss, un docker, sert Maëlle.", "entities": [
+        {"ref": "e1", "action": "create", "name": "Joss Fer", "type": "character"},
+        {"ref": "e2", "action": "existing", "entity_id": ids["npc"]}], "facts": [
+        {"ref": "f1", "action": "create", "facet": "histoire", "content": "Joss Fer sert Maëlle.",
+         "participants": ["e1", "e2"], "knowers": [{"entity_ref": "e2", "level": "knows"}]}]}
+    with Session(engine) as db:
+        before = _counts(db)
+    far = client.post("/api/lore/write/commit", json={"proposal": proposal},
+                      headers={"origin": "https://evil.example"})
+    with Session(engine) as db:
+        if far.status_code != 403 or _counts(db) != before:
+            fail(f"E1d: a non-local commit answered {far.status_code} or wrote rows")
+    resp = client.post("/api/lore/write/commit", json={"proposal": proposal})
+    with Session(engine) as db:
+        joss = db.exec(select(Entity).where(Entity.name == "Joss Fer",
+                                            Entity.world_id == ids["world"])).first()
+        char = db.get(Character, joss.id) if joss else None
+        if resp.status_code != 200 or char is None or char.character_type != "npc":
+            fail(f"E1c: commit answered {resp.status_code} {resp.text[:160]}")
+    entries = client.get("/api/lore/write/entries").json().get("entries") or [{}]
+    labels = [r["label"] for r in entries[0].get("rows", [])]
+    if entries[0].get("statement") != proposal["statement"] or not labels \
+            or not any("Joss Fer" in label for label in labels):
+        fail(f"E1c: entries listed {entries[0]!r}"[:300])
+    proposal["facts"][0]["facet"] = "lien"
+    with Session(engine) as db:
+        before = _counts(db)
+    resp = client.post("/api/lore/write/commit", json={"proposal": proposal})
+    with Session(engine) as db:
+        if resp.status_code != 422 or _counts(db) != before:
+            fail(f"E1c: an invalid commit answered {resp.status_code} or wrote rows")
+
+
+def check_e2() -> None:
+    import ast
+
+    route = SRC / "cockpit" / "routes" / "lore_write.py"
+    text = route.read_text(encoding="utf-8")
+    for needle in ("select(", "chat("):
+        if needle in text:
+            fail(f"E2: the writing route contains {needle!r}")
+    tree = ast.parse(text)
+    commits = [(fn.name, node) for fn in tree.body if isinstance(fn, ast.FunctionDef)
+               for node in ast.walk(fn) if isinstance(node, ast.Call)
+               and isinstance(node.func, ast.Attribute) and node.func.attr == "commit"]
+    if [name for name, _ in commits] != ["write_commit"]:
+        fail(f"E2: commits in {[name for name, _ in commits]}, expected only write_commit")
+
+
 def check_d2() -> None:
     import re as _re
 
@@ -534,6 +641,8 @@ def main() -> int:
     check_c2()
     check_d1()
     check_d2()
+    check_e1()
+    check_e2()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -541,7 +650,8 @@ def main() -> int:
     print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
           "v2.11 declares the source record and migrates from v2.10 only; a proposal "
           "writes all or nothing, each row recorded, existing rows skipped; the draft "
-          "names things by name and code only and resolves both in code")
+          "names things by name and code only and resolves both in code; the routes are "
+          "thin, guarded, and write only on commit")
     return 0
 
 
````

## Scope OUT

- The frontend (F).
- Bulk undo or any edit of a past entry (M2).
- Pagination of the history beyond the newest 50.
- Route authentication (I2/I3).
- Every later brief of the lot: BRIEF-0098-F.

## Invariants to defend

**Creator-direct create helpers never commit in their core; the commit boundary belongs to the caller:** `write_commit` commits once, after `apply_proposal`; every refusal rolls back. **No model-emitted id reaches a canon row:** the new CLAUDE.md invariant; the commit accepts only what C-02 validates. **The lore renderer receives rows, never a `Session`** is untouched: the writing route imports no consultation module (R17).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `lore_isolation.py` R6/R17 or `lore_write.py` E2 flags a query, a model call or a second commit in the route.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `claude_md_contract.py` fails on the new invariant's line length after a merge reflowed the section: rewrap the three lines at ≤ 100 characters, same words.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `lore_write.py` → `PASS … the routes are thin, guarded, and write only on commit`.
- `lore_isolation.py`, `origin_guard.py`, `claude_md_contract.py` → `PASS`.
- Mutation test: replace `db.commit()` in `write_commit` by `pass`; E1c (the committed story is not listed) and E2 fail; revert.
- `corpus_gate.py` → 128/128.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

CLAUDE.md invariant « A lore statement commits whole or not at all … ». Decision entry `THE LORE SHELL GETS A WRITING PANEL (TICKET-0098) … (BRIEF-0098-e, no schema change)`.
