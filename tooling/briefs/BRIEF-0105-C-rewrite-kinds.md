<!-- slug: rewrite-kinds -->
# BRIEF 0105-C — "A rewrite says whether it corrects or changes the world"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: BRIEF-0105-B
Commit header for decisions: `(BRIEF-0105-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/writes/facts.py:105` → `def update_fact_content(db: Session, *, fact: Fact, content: str, changed_by: str) -> Fact:`; `:142` → `def update_typed_fact_content(db: Session, *, fact: Fact, content: str, changed_by: str) -> Fact:`; both append `{"content", "changed_by", "at"}`.
- `src/world_engine/writes/facets.py:363` → `def edit_entity_fact(db: Session, *, fact_id: str, content: str, changed_by: str) -> Fact:`.
- `src/world_engine/writes/mentions.py:110` → `        update_fact_content(db, fact=owner, content=new_text, changed_by=changed_by)`.
- `src/world_engine/writes/relations.py:233` → `def _refresh_lien_content(`; `:248` → `def _refresh_map_content(`; each calls `update_typed_fact_content` once.
- `src/world_engine/cockpit/crud/facets.py:120` and `src/world_engine/lore_write_apply.py:284` → the two `edit_entity_fact(` calls of enumeration E3.
- `src/world_engine/prose_render.py:58` → `def render(db: Session, text: Optional[str]) -> Optional[str]:`, the module's last function; no `fact_versions.py` exists.
- `tooling/verify/checks/identity_tokens.py` `_allowed` → `content_raw` allowed in `prose_render.py`, `knowledge_resolve.py`, `writes/*.py`, `models/canon_knowledge.py`, `scripts/migrate_*`.

## Facts carried

### R-06 — fact rewrites [M]
Opened: `src/world_engine/writes/facts.py:105-157` (`update_fact_content`,
`update_typed_fact_content`: history entry `{content, changed_by, at}`,
`at` an aware ISO string); `src/world_engine/writes/facets.py:363-377`
(`edit_entity_fact`, which calls `update_fact_content` even when the text
is unchanged); `src/world_engine/writes/relations.py:233-262`
(`_refresh_lien_content`, `_refresh_map_content`); enumeration E3.
Finding: seven call sites, none naming what the rewrite is.
Consequence: `kind` becomes a required keyword of all three functions;
each caller names it (U1); C passes `correction` from the two creator
surfaces until F.

### R-07 — fact deletion [M]
Opened: `src/world_engine/writes/facts.py:121-139` (`delete_free_fact`).
Finding: it deletes the fact's knowledge, defaults and participants, then
the fact.
Consequence: I1 holds as is; nothing in this lot touches deletion.

### R-15 — datetimes [M]
Opened: `src/world_engine/models/canon.py:54-59` (plain `DateTime`
columns); the installed `sqlmodel/sql/sqltypes.py` (`UTCDateTime`, used for
fields annotated `datetime` without `sa_column`: refuses a naive value on
write, returns aware UTC); `requirements.txt` (`sqlmodel>=0.0.16`).
Finding: `first_at` (and the new `last_at` fields) are plain annotations,
so their type depends on the installed SQLModel; `created_at`,
`entered_at`, `updated_at` read back naive.
Consequence: every comparison goes through `fact_versions.utc` (a naive
value is UTC); writers and fixtures use aware datetimes.

### R-16 — where raw fact text may be read [M]
Opened: `tooling/verify/checks/identity_tokens.py:7-14, 56-63` (R1:
`content_raw` only in `models/canon_knowledge.py`, `writes/*.py`,
`prose_render.py`, `knowledge_resolve.py`, migrations).
Consequence: `fact_versions.py` takes the history and the current text as
arguments; `prose_render.fact_texts_at` / `fact_is_stale` pass them.

## Contracts

### C-04 — the kind of a rewrite
Produced by: BRIEF-0105-C   Consumed by: BRIEF-0105-D, E, F, G
`writes.facts.FACT_CHANGE_KINDS = ("correction", "changement")`.
`update_fact_content(db, *, fact, content, changed_by, kind)`,
`update_typed_fact_content(db, *, fact, content, changed_by, kind)`,
`writes.facets.edit_entity_fact(db, *, fact_id, content, changed_by,
kind)`: `kind` required, keyword-only; `ValueError` outside the vocabulary,
before any write. History entry `{"content": <text before>, "changed_by",
"at": <aware ISO>, "kind"}`. An entry without `kind` reads as a
correction.

### C-05 — the version known
Produced by: BRIEF-0105-C   Consumed by: BRIEF-0105-D, E, G
`fact_versions.utc(value) -> datetime` (naive = UTC).
`fact_versions.version_text(history, current, as_of) -> str`: `as_of` None
→ `current`; else the `content` of the first `changement` entry whose `at`
is after `as_of`, else `current`. Pure.
`prose_render.fact_texts_at(db, pairs: list[(Fact, as_of)]) -> list[str]`
(rendered, one entity query); `prose_render.fact_is_stale(fact, as_of) ->
bool`.

## Context

Nia locked G1: a correction fixes the text for everyone, a change in the world leaves whoever knew the fact with the version they learned (I1: deleting stays a correction). This brief makes every rewrite name its kind, and states the version rule as a pure function. The two creator surfaces pass `correction` until F gives the creator the choice; the code-made rewrites name theirs (U1).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `writes/facts.py`, `FACT_CHANGE_KINDS` and a private `_append_history`; `update_fact_content` and `update_typed_fact_content` take a required keyword `kind` (C-04); module docstring;
   - `writes/facets.edit_entity_fact` takes a required `kind` and passes it on;
   - callers: `writes/mentions.bind_mention` → `correction`; `writes/relations._refresh_lien_content` → `changement`; `_refresh_map_content` → `correction`; `cockpit/crud/facets.update_entity_fact_content` and the `lore_write_apply` rewrite → `correction` (F replaces both);
   - creates `src/world_engine/fact_versions.py` (`utc`, `version_text`, C-05), which never names the model attribute; `prose_render.py` gains `fact_texts_at` and `fact_is_stale`;
   - adds C1-C3 to `fact_learning.py`; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): a fact rewrite names its kind; the version known (BRIEF-0105-c)`.

````diff
diff --git a/src/world_engine/cockpit/crud/facets.py b/src/world_engine/cockpit/crud/facets.py
index 0a6018c..ba19be9 100644
--- a/src/world_engine/cockpit/crud/facets.py
+++ b/src/world_engine/cockpit/crud/facets.py
@@ -117,7 +117,8 @@ def update_entity_fact_content(
 ) -> dict:
     _get_fact(db, fact_id)
     try:
-        fact = edit_entity_fact(db, fact_id=fact_id, content=body.content, changed_by=CREATED_BY)
+        fact = edit_entity_fact(db, fact_id=fact_id, content=body.content, changed_by=CREATED_BY,
+                                kind="correction")
     except ValueError as exc:
         db.rollback()
         raise HTTPException(status_code=422, detail=str(exc))
diff --git a/src/world_engine/fact_versions.py b/src/world_engine/fact_versions.py
new file mode 100644
index 0000000..66646e4
--- /dev/null
+++ b/src/world_engine/fact_versions.py
@@ -0,0 +1,54 @@
+"""The version of a fact someone knows (TICKET-0105, BRIEF-0105-C, C-05).
+
+A fact's history is a list of entries `{"content", "changed_by", "at",
+"kind"}`, each holding the text the fact had BEFORE that rewrite. A
+`correction` fixes the text for everyone; a `changement` is a change in the
+world (G1). An entry without `kind` predates TICKET-0105 and reads as a
+correction (M1).
+
+Someone whose last contact with the fact was at `as_of` knows the text the
+fact had just before the first `changement` made after `as_of` -- with
+every correction made before that change included -- or the current text
+when no change in the world came after `as_of`. `as_of=None` means "always
+in contact" (a fact everyone knows, one's own description): the current
+text.
+
+Pure: no query, no write, no model attribute. The caller passes the stored
+history and the current stored text (`prose_render.fact_texts_at` does,
+the one reader of the raw text) and renders what comes back.
+"""
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Optional
+
+
+def utc(value: datetime) -> datetime:
+    """`value` as an aware UTC datetime; a naive value is taken to be UTC
+    (SQLite returns plain `DateTime` columns naive)."""
+    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)
+
+
+def _entry_at(entry: dict) -> Optional[datetime]:
+    raw = entry.get("at")
+    if not isinstance(raw, str):
+        return None
+    try:
+        return utc(datetime.fromisoformat(raw))
+    except ValueError:
+        return None
+
+
+def version_text(history: Optional[list], current: str, as_of: Optional[datetime]) -> str:
+    """The stored text known by someone last in contact at `as_of`, given
+    the fact's `history` and `current` stored text (module docstring)."""
+    if as_of is None:
+        return current
+    since = utc(as_of)
+    for entry in history or []:
+        if not isinstance(entry, dict) or entry.get("kind") != "changement":
+            continue
+        at = _entry_at(entry)
+        if at is not None and at > since and isinstance(entry.get("content"), str):
+            return entry["content"]
+    return current
diff --git a/src/world_engine/lore_write_apply.py b/src/world_engine/lore_write_apply.py
index 6b84628..4088735 100644
--- a/src/world_engine/lore_write_apply.py
+++ b/src/world_engine/lore_write_apply.py
@@ -282,7 +282,7 @@ class _Writer:
             fact = self.db.get(Fact, item["fact_id"])
             if item["action"] == "rewrite":
                 edit_entity_fact(self.db, fact_id=fact.id, content=item["content"],
-                                 changed_by=CREATED_BY)
+                                 changed_by=CREATED_BY, kind="correction")
                 self.record("fact", fact.id, "updated")
             self.add_participants(fact, participants)
             self.add_defaults(fact, self.scopes(item))
diff --git a/src/world_engine/prose_render.py b/src/world_engine/prose_render.py
index 81b50c5..a3f1dd7 100644
--- a/src/world_engine/prose_render.py
+++ b/src/world_engine/prose_render.py
@@ -22,6 +22,7 @@ from typing import Iterable, Optional
 
 from sqlmodel import Session, select
 
+from .fact_versions import version_text
 from .models import Entity
 
 TOKEN_RE = re.compile(r"\[\[e:([0-9a-fA-F-]{36})\|([^\]|]*)\]\]")
@@ -75,3 +76,14 @@ def fact_texts(db: Session, facts: list) -> list[str]:
 def knowledge_texts(db: Session, rows: list) -> list[Optional[str]]:
     """`knowledge_text` for many rows, one entity query."""
     return render_many(db, [k.content_raw for k in rows])
+
+
+def fact_texts_at(db: Session, pairs: list[tuple]) -> list[str]:
+    """`(fact, as_of)` pairs -> each fact's text as known at `as_of`
+    (`fact_versions.version_text`, TICKET-0105), rendered; one entity query."""
+    return render_many(db, [version_text(f.change_history, f.content_raw, at) for f, at in pairs])
+
+
+def fact_is_stale(fact, as_of) -> bool:
+    """True when the version known at `as_of` is not the current text."""
+    return version_text(fact.change_history, fact.content_raw, as_of) != fact.content_raw
diff --git a/src/world_engine/writes/facets.py b/src/world_engine/writes/facets.py
index 6687762..01091b4 100644
--- a/src/world_engine/writes/facets.py
+++ b/src/world_engine/writes/facets.py
@@ -360,21 +360,25 @@ def _edit_scope(db: Session, fact: Fact) -> NameScope:
     return NameScope("names_only", exclude_entity_id=owners[0] if len(owners) == 1 else None)
 
 
-def edit_entity_fact(db: Session, *, fact_id: str, content: str, changed_by: str) -> Fact:
+def edit_entity_fact(
+    db: Session, *, fact_id: str, content: str, changed_by: str, kind: str,
+) -> Fact:
     """Rewrite a descriptive fact's content through `update_fact_content`
-    (history appended). `ValueError` if unknown, not descriptive, or the
-    content is empty. New text gets identity tokens and its unresolved names
+    (history appended, with `kind`: `correction` or `changement`, TICKET-0105).
+    `ValueError` if unknown, not descriptive, the content is empty, or the
+    kind is unknown. New text gets identity tokens and its unresolved names
     are recorded (BRIEF-0091-J); text equal to the stored text, raw or
     rendered, keeps the stored text as is."""
     fact = _descriptive_fact(db, fact_id)
     if not isinstance(content, str) or not content.strip():
         raise ValueError("fact content is empty")
     if content in (fact.content_raw, fact_text(db, fact)):
-        return update_fact_content(db, fact=fact, content=fact.content_raw, changed_by=changed_by)
+        return update_fact_content(db, fact=fact, content=fact.content_raw,
+                                   changed_by=changed_by, kind=kind)
     tokens = tokenize(db, world_id=fact.world_id, text=content, scope=_edit_scope(db, fact))
     if tokens.unresolved:
         record_unresolved(db, world_id=fact.world_id, fact_id=fact.id, items=tokens.unresolved)
-    return update_fact_content(db, fact=fact, content=tokens.text, changed_by=changed_by)
+    return update_fact_content(db, fact=fact, content=tokens.text, changed_by=changed_by, kind=kind)
 
 
 def remove_entity_fact(db: Session, *, fact_id: str) -> None:
diff --git a/src/world_engine/writes/facts.py b/src/world_engine/writes/facts.py
index 257f7a4..8640b1c 100644
--- a/src/world_engine/writes/facts.py
+++ b/src/world_engine/writes/facts.py
@@ -33,6 +33,13 @@ same history-first shape as `update_typed_fact_content`. `delete_free_fact`
 is a creator-CRUD hard delete of a free fact: its `knowledge`, `fact_default`
 and `fact_participant` rows, then the fact, children first (FKs are on); it
 refuses a typed fact, which belongs to its relation/event/world_law row.
+
+TICKET-0105, BRIEF-0105-C (G1): both rewrites take a required `kind` in
+`FACT_CHANGE_KINDS`, recorded in the history entry. A `correction` fixes the
+text everyone sees; a `changement` is a change in the world, and whoever
+knew the fact keeps the previous version until a later contact
+(`fact_versions.py`). A history entry without `kind` predates the ticket and
+reads as a correction.
 """
 
 from __future__ import annotations
@@ -46,6 +53,24 @@ from sqlmodel import Session, select
 from ..facets import FACETS, TYPED_FACET_BY_FK, normalize_aspect
 from ..models import Fact, FactDefault, FactParticipant, Knowledge
 
+FACT_CHANGE_KINDS: tuple[str, ...] = ("correction", "changement")
+
+
+def _append_history(fact: Fact, *, changed_by: str, kind: str) -> None:
+    """Append the current content to `fact.change_history` with its `kind`;
+    `ValueError` on a kind outside `FACT_CHANGE_KINDS`."""
+    if kind not in FACT_CHANGE_KINDS:
+        raise ValueError(f"unknown change kind {kind!r}")
+    history = list(fact.change_history or [])
+    history.append({
+        "content": fact.content_raw,
+        "changed_by": changed_by,
+        "at": datetime.now(UTC).isoformat(),
+        "kind": kind,
+    })
+    fact.change_history = history
+    sa_attrs.flag_modified(fact, "change_history")
+
 
 def create_fact(
     db: Session,
@@ -102,17 +127,13 @@ def _check_facet(
         raise ValueError(f"create_fact: typed facet {facet!r} on a free fact")
 
 
-def update_fact_content(db: Session, *, fact: Fact, content: str, changed_by: str) -> Fact:
+def update_fact_content(
+    db: Session, *, fact: Fact, content: str, changed_by: str, kind: str,
+) -> Fact:
     """Overwrite `fact.content` on a free or typed fact, appending the previous
-    content to `fact.change_history` first (TICKET-0091, BRIEF-0091-A, C-03)."""
-    history = list(fact.change_history or [])
-    history.append({
-        "content": fact.content_raw,
-        "changed_by": changed_by,
-        "at": datetime.now(UTC).isoformat(),
-    })
-    fact.change_history = history
-    sa_attrs.flag_modified(fact, "change_history")
+    content to `fact.change_history` first (TICKET-0091, BRIEF-0091-A, C-03),
+    with `kind` (TICKET-0105, C-04)."""
+    _append_history(fact, changed_by=changed_by, kind=kind)
     fact.content_raw = content
     db.add(fact)
     return fact
@@ -139,17 +160,13 @@ def delete_free_fact(db: Session, *, fact: Fact) -> None:
     db.delete(fact)
 
 
-def update_typed_fact_content(db: Session, *, fact: Fact, content: str, changed_by: str) -> Fact:
+def update_typed_fact_content(
+    db: Session, *, fact: Fact, content: str, changed_by: str, kind: str,
+) -> Fact:
     """Overwrite `fact.content`, appending the previous content to
-    `fact.change_history` first (TICKET-0090, BRIEF-0090-a)."""
-    history = list(fact.change_history or [])
-    history.append({
-        "content": fact.content_raw,
-        "changed_by": changed_by,
-        "at": datetime.now(UTC).isoformat(),
-    })
-    fact.change_history = history
-    sa_attrs.flag_modified(fact, "change_history")
+    `fact.change_history` first (TICKET-0090, BRIEF-0090-a), with `kind`
+    (TICKET-0105, C-04)."""
+    _append_history(fact, changed_by=changed_by, kind=kind)
     fact.content_raw = content
     db.add(fact)
     return fact
diff --git a/src/world_engine/writes/mentions.py b/src/world_engine/writes/mentions.py
index 28df7f5..752d59b 100644
--- a/src/world_engine/writes/mentions.py
+++ b/src/world_engine/writes/mentions.py
@@ -107,7 +107,9 @@ def bind_mention(db: Session, *, mention: UnresolvedMention, entity_id: str, cha
         raise ValueError(f"unresolved_mention {mention.id!r}: {mention.surface!r} no longer occurs in the text")
     new_text = text[:at] + entity_token(entity_id, mention.surface) + text[at + len(mention.surface):]
     if isinstance(owner, Fact):
-        update_fact_content(db, fact=owner, content=new_text, changed_by=changed_by)
+        # Binding a name to its entity fixes the text: a correction (TICKET-0105, U1).
+        update_fact_content(db, fact=owner, content=new_text, changed_by=changed_by,
+                            kind="correction")
     else:
         apply_knowledge_patch(db, knowledge=owner, patch={"content": new_text}, changed_by=changed_by)
     return resolve_mention(db, mention=mention, entity_id=entity_id)
diff --git a/src/world_engine/writes/relations.py b/src/world_engine/writes/relations.py
index 0f97056..3f6360b 100644
--- a/src/world_engine/writes/relations.py
+++ b/src/world_engine/writes/relations.py
@@ -240,8 +240,10 @@ def _refresh_lien_content(db: Session, rel: Relation, old_type: Optional[str], c
     if lien is None:
         return
     name_a, name_b = _endpoint_tokens(db, rel)
+    # A social relation that changes type changed in the world (TICKET-0105, U1).
     update_typed_fact_content(
         db, fact=lien, content=lien_fact_content(name_a, rel.type, name_b), changed_by=changed_by,
+        kind="changement",
     )
 
 
@@ -255,8 +257,10 @@ def _refresh_map_content(db: Session, rel: Relation, old_type: Optional[str], ch
     if fact is None:
         return
     name_a, name_b = _endpoint_tokens(db, rel)
+    # `connects_to` <-> `borde` follows the zones: a correction (TICKET-0105, U1).
     update_typed_fact_content(
         db, fact=fact, content=_map_fact_content(rel.type, name_a, name_b), changed_by=changed_by,
+        kind="correction",
     )
 
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 7ab83e7..946a2e5 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17770,6 +17770,26 @@ entities acquaintances (Q5a) but is not a contact.
 place characters through `**ext_kwargs`, which no static scan can see.
 Reactivates if the listener proves incompatible with a write path.
 
+
+## A REWRITE SAYS WHETHER IT CORRECTS OR CHANGES THE WORLD (TICKET-0105) -- THE VERSION KNOWN FOLLOWS THE CHANGES (BRIEF-0105-c, no schema change)
+
+**G1.** `update_fact_content` and `update_typed_fact_content` take a
+required `kind` in `FACT_CHANGE_KINDS` (`correction`, `changement`),
+written into the history entry. A correction fixes the text for everyone; a
+change in the world leaves whoever knew the fact with the version they
+learned. `fact_versions.version_text` is that rule, pure: someone last in
+contact at `as_of` knows the text the fact had just before the first change
+in the world made after `as_of`, corrections before it included, or the
+current text. An entry without `kind` predates the ticket and reads as a
+correction (M1). `prose_render.fact_texts_at` renders a version; it stays
+the one reader of the raw text outside `writes/`.
+
+**U1.** The rewrites the code makes name their kind: a social relation that
+changes type changed in the world (`changement`); a geographic link that
+follows the zones (`connects_to` <-> `borde`) and a name bound to its entity
+are corrections. Until BRIEF-0105-F, the fiche and the Lore panel pass
+`correction`, which is today's behaviour.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
index 5d851cd..0ebced5 100644
--- a/tooling/verify/checks/fact_learning.py
+++ b/tooling/verify/checks/fact_learning.py
@@ -42,6 +42,23 @@ B4 -- encounters move their last contact (fixture): a new pair has
    keeps `first_at` and the row count; a later `relation` encounter and an
    earlier `gathering` one move nothing.
 
+C1 -- the kind of a rewrite (BRIEF-0105-C, fixture). `update_fact_content`
+   without `kind` raises `TypeError`; with a kind outside
+   `FACT_CHANGE_KINDS` it raises `ValueError` and appends nothing; with
+   `correction` and `changement` each history entry carries its kind.
+C2 -- every rewrite names its kind (AST). Every call to
+   `update_fact_content`, `update_typed_fact_content` and
+   `edit_entity_fact` under `src/` and `scripts/` passes `kind=`; the
+   literal is `correction` in `writes/mentions.py::bind_mention` and
+   `writes/relations.py::_refresh_map_content`, `changement` in
+   `writes/relations.py::_refresh_lien_content`.
+C3 -- the version known (`fact_versions.version_text`, pure). History:
+   correction at t1, changement at t2 (text before it "v1"), correction at
+   t3, changement at t4 (text before it "v2b"), current "v3", and one entry
+   without kind at t5 (text "old"). As of t0 < t1 and as of t1.5 -> "v1";
+   as of t2.5 and t3.5 -> "v2b"; as of t4.5 and t6 -> "v3"; as of None ->
+   "v3".
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -376,6 +393,102 @@ def check_b4(engine) -> None:
             fail("B4: a relation or an earlier encounter moved last_at")
 
 
+# --- C1-C3 ---------------------------------------------------------------------
+
+def check_c1(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.writes import create_fact
+    from world_engine.writes.facts import update_fact_content
+
+    with Session(engine) as session:
+        ids = _world(session, "C1")
+        fact = create_fact(session, world_id=ids["world"], content="a", created_by="check",
+                           facet="information")
+        session.flush()
+        try:
+            update_fact_content(session, fact=fact, content="b", changed_by="check")  # type: ignore[call-arg]
+            fail("C1: a rewrite without kind was accepted")
+        except TypeError:
+            pass
+        try:
+            update_fact_content(session, fact=fact, content="b", changed_by="check", kind="x")
+            fail("C1: an unknown kind was accepted")
+        except ValueError:
+            pass
+        if fact.change_history:
+            fail("C1: a refused rewrite appended history")
+        update_fact_content(session, fact=fact, content="b", changed_by="check", kind="correction")
+        update_fact_content(session, fact=fact, content="c", changed_by="check", kind="changement")
+        kinds = [e.get("kind") for e in fact.change_history]
+        if kinds != ["correction", "changement"] or fact.content_raw != "c":
+            fail(f"C1: history kinds {kinds}, content {fact.content_raw!r}")
+        session.rollback()
+
+
+_KIND_CALLS = {"update_fact_content", "update_typed_fact_content", "edit_entity_fact"}
+_KIND_LITERALS = {
+    ("src/world_engine/writes/mentions.py", "bind_mention"): "correction",
+    ("src/world_engine/writes/relations.py", "_refresh_map_content"): "correction",
+    ("src/world_engine/writes/relations.py", "_refresh_lien_content"): "changement",
+}
+
+
+def check_c2() -> None:
+    import ast
+
+    calls = 0
+    literals: dict = {}
+    for base in (ROOT / "src", ROOT / "scripts"):
+        for path in sorted(base.rglob("*.py")):
+            rel = path.relative_to(ROOT).as_posix()
+            tree = ast.parse(path.read_text(encoding="utf-8"))
+            for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
+                for node in ast.walk(func):
+                    if not isinstance(node, ast.Call):
+                        continue
+                    name = node.func.id if isinstance(node.func, ast.Name) else (
+                        node.func.attr if isinstance(node.func, ast.Attribute) else None)
+                    if name not in _KIND_CALLS:
+                        continue
+                    calls += 1
+                    kind = next((k.value for k in node.keywords if k.arg == "kind"), None)
+                    if kind is None:
+                        fail(f"C2: {rel}::{func.name} calls {name} without kind=")
+                    elif (rel, func.name) in _KIND_LITERALS:
+                        literals[(rel, func.name)] = getattr(kind, "value", None)
+    if calls == 0:
+        fail("C2: no rewrite call found")
+    if literals != _KIND_LITERALS:
+        fail(f"C2: the code-made rewrites name {literals}")
+
+
+def check_c3() -> None:
+    from datetime import UTC, datetime, timedelta
+
+    from world_engine.fact_versions import version_text
+
+    base = datetime(2026, 1, 1, tzinfo=UTC)
+
+    def t(n: float) -> datetime:
+        return base + timedelta(days=n)
+
+    history = [
+        {"content": "v0", "at": t(1).isoformat(), "kind": "correction"},
+        {"content": "v1", "at": t(2).isoformat(), "kind": "changement"},
+        {"content": "v2a", "at": t(3).isoformat(), "kind": "correction"},
+        {"content": "v2b", "at": t(4).isoformat(), "kind": "changement"},
+        {"content": "old", "at": t(5).isoformat()},
+    ]
+    cases = ((t(0), "v1"), (t(1.5), "v1"), (t(2.5), "v2b"), (t(3.5), "v2b"),
+             (t(4.5), "v3"), (t(6), "v3"), (None, "v3"),
+             (t(2.5).replace(tzinfo=None), "v2b"))
+    for as_of, want in cases:
+        got = version_text(history, "v3", as_of)
+        if got != want:
+            fail(f"C3: as of {as_of} -> {got!r}, expected {want!r}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -386,13 +499,18 @@ def main() -> int:
     create_db_and_tables()
     check_b3(engine)
     check_b4(engine)
+    check_c1(engine)
+    check_c2()
+    check_c3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: fact_learning -- v2.14 declares passage and the encounter's last "
           "contact, presets tenue to rencontre, and migrates from v2.13 only; every "
-          "placement and every encounter moves its last contact, through one writer each")
+          "placement and every encounter moves its last contact, through one writer each; "
+          "every rewrite says whether it corrects or changes the world, and the version "
+          "known follows the changes alone")
     return 0
 
 
````

## Scope OUT

- Any reader using the versions (E) or the resolver's `as_of` (D).
- The creator's choice in the UI and the `kind` field of the route and proposal (F).
- Rewriting existing history entries: an entry without `kind` reads as a correction.
- Any change to `delete_free_fact` (I1).
- Skipping the history entry of a no-op rewrite in `edit_entity_fact` (pre-existing; the version rule compares texts, so it is harmless).
- Every later brief of this lot.

## Invariants to defend

**History is sacred:** every rewrite still appends the previous text before overwriting; a refused kind appends nothing. **Raw text is read only through the render chokepoint** (`identity_tokens.py` R1): `fact_versions.py` receives the text, `prose_render.py` reads it.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- Enumeration E3 has grown (a rewrite call this brief does not name).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- … every rewrite says whether it corrects or changes the world, and the version known follows the changes alone`.
- `identity_tokens.py`, `lore_write.py`, `zone_map_links.py`, `relation_orientation.py`, `import_cycle.py` → `PASS`.
- Mutation tests, each red then reverted: in `_refresh_lien_content`, `kind="changement"` → `kind="correction"` → `C2`; in `version_text`, `entry.get("kind") != "changement"` → `entry.get("kind") == "correction"` → `C3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A REWRITE SAYS WHETHER IT CORRECTS OR CHANGES THE WORLD (TICKET-0105) -- THE VERSION KNOWN FOLLOWS THE CHANGES (BRIEF-0105-c, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
