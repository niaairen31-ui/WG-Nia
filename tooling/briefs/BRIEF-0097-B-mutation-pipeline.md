<!-- slug: mutation-pipeline -->
# BRIEF 0097-B — "The mutation pipeline keys knowledge by fact"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: A
Commit header for decisions: `(BRIEF-0097-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/writes/knowledge.py:216` → `resolved_subject = subject or "unknown"` (the fact is created from the subject)
- `src/world_engine/analyzer_transcript.py:531` → `def _mutation_match_key(mutation_type: str, payload: dict):` returning `payload.get("subject")` for `new_knowledge`
- `src/world_engine/analyzer_transcript.py:242` → `def _content_to_subject_slug(content: str) -> str:`
- `src/world_engine/cockpit/mutations.py:486` → `Knowledge.subject == subject,` in `_mutation_apply_knowledge_change`
- `src/world_engine/cockpit/routes/mutations.py:166` → `def _dup_tick_new_knowledge(payload: dict, db: Session) -> Optional[str]:`
- `src/world_engine/fact_refs.py` → does not exist
- `idx_knowledge_entity_fact` → declared in `models/canon_knowledge.py` (brief A)

## Facts carried

### R-02 — the five jobs of `knowledge.subject`
Opened: every file below, at the lines named; enumeration in gate (c).
Finding:
- identity/dedup: `analyzer_transcript._mutation_match_key` (531),
  `tick._tick_npc_dedup_note` (`(entity_id, subject)`, 142),
  `cockpit/routes/mutations._dup_tick_new_knowledge` (166) and the
  conversation-sourced guard (~340), `cockpit/mutations._knowledge_leg_already_applied`
  (~76), `_mutation_apply_knowledge_change` (473-486), the resource leg
  (~739-750), `analyzer._overhearing_existing_keys` (76-104);
- bridges: `scene_format.active_signposts` (`discoverable_detail.subject` ↔
  `knowledge.subject`, 44-65), `cockpit/play_discovery._propose_engine_discovery`
  (36), `day_plan._eval_knowledge` / `_anchorable_subjects` /
  `_held_subjects` (142, 327-352), `day_mutations` (170, 210, 232-246),
  `link_author` (`npc:{id}`: 161, 310, 514, 588), `link_context` (69-110),
  `tick._tick_build_npc_indexes` (`secret_subjects`, 102);
- labels: `context._knowledge_line` / `_mj_knowledge_line` /
  `_mj_context_player_knowledge` (126, 682, 809), `tick_context._knowledge_line`
  (128), `lore_selectors._knowledge_rows` (182), `lore_render._format_knowledge`
  (62), `cockpit/crud/_shared` (`KNOWLEDGE_FIELDS` 222, `_knowledge_dict` 254);
- aboutness: `subject_resolve.py` (whole module), `cockpit/crud/knowledge.list_unresolved_subjects`
  (142), `day_mutations._emit_new_knowledge` (246);
- writers: `writes/knowledge.py` (`write_knowledge`, `apply_knowledge_patch`,
  `upsert_knowledge_row`), `writes/facets._write_creator_meta` (187),
  `writes/relations` (384), `knowledge_resolve.resolve_default_rows` (359),
  `cockpit/crud/knowledge` (create/update), `cockpit/routes/creator` (PC,
  572-629), `cockpit/routes/npc_agent` (224), `entity_author` (55, 213-256),
  `tick_normalize._tick_normalize_new_knowledge` (718).
Consequence: one brief per group; the census K3 pins what is left.

### R-05 — `write_knowledge` fallback
Opened: `writes/knowledge.py:178-240`.
Finding: without `fact_id`, creates a fact with `content = subject or
"unknown"` (216-224), so every overheard or discovered row got its own fact.
Consequence: B changes the content to the row's stored text (M1); G removes
the parameter.

## Contracts

### C-01 — `fact_refs.text_key`, `knowledge_key`, `find_held`
Produced by: B   Consumed by: B, C, D, E
```python
def text_key(content: Optional[str]) -> str  # first 5 words, lower, \W stripped, "_"-joined, <=50; "unknown" if empty
def knowledge_key(payload: dict) -> tuple[str, str]
    # ("fact", fact_id) when payload["fact_id"] is truthy, else ("text", text_key(payload["content"]))
def find_held(db, entity_id: Optional[str], payload: dict) -> Optional[Knowledge]
    # None when entity_id is falsy; by fact: the row (entity_id, fact_id);
    # by text: the first row of entity_id whose fact text or own text has the key
```

### C-02 — knowledge apply rules (`cockpit/mutations.py`)
Produced by: B   Consumed by: C, D, E
- `new_knowledge`: payload `fact_id` optional; a discovery's detail supplies
  `detail.fact_id`; a fact of another world → error string; a fact the entity
  already holds → error string; no `fact_id` → a new fact from the row's text.
  The first approved discovery sets `detail.fact_id`.
- `knowledge_change`: finds the row by `(entity_id, fact_id)`; no `fact_id`
  → `"knowledge_change: payload must contain entity_id and fact_id"`.
- resource knowledge leg: needs `entity_id` and non-empty `content`; a held
  row (`find_held`) → `"knowledge already held (upgrade-by-purchase deferred)"`.
- window normalization: model `knowledge_change` dropped (N1); `subject` and
  `fact_id` popped from a model `new_knowledge` / resource leg (a subject
  with no content becomes the content).

### C-03 — `fact_refs.code_facts`, `CodedFacts`
Produced by: B   Consumed by: C, D
```python
def code_facts(db, fact_ids: Iterable[str]) -> CodedFacts
    # in order, first occurrence wins, ids without a fact skipped; line "f<n> — <rendered text>"
@dataclass(frozen=True)
class CodedFacts:
    codes: dict[str, str]        # "f1" -> fact id
    lines: tuple[str, ...]
    def resolve(self, code) -> Optional[str]   # tolerates "[F1]", " f1 "; non-str or unknown -> None
    def code_of(self, fact_id) -> Optional[str]
```

## Context

With the identity in place (A), every place the mutation pipeline compares or applies knowledge moves from the subject string to the fact. `fact_refs.py` is the one module that computes identity; a model never names a fact (M1), and a model-emitted `knowledge_change` is dropped (N1).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `src/world_engine/fact_refs.py` (C-01, C-03); moves `_content_to_subject_slug` there unchanged as `text_key`; makes `write_knowledge` create a new fact from the row's stored text (M1); keys `_mutation_match_key`, the tick emit-time note, `_dup_tick_new_knowledge`, the conversation-sourced guard, `_knowledge_leg_already_applied` and the resource leg on C-01; adds `_payload_fact` and the `knowledge_change`-by-`fact_id` rule (C-02); sets `discoverable_detail.fact_id` on the first approved discovery; drops a model-emitted `knowledge_change` and strips `subject`/`fact_id` from model payloads in window normalization; adds K4 and lowers the census.
2. Regenerate the index.
3. Message: `feat(knowledge): the mutation pipeline keys knowledge by fact (BRIEF-0097-b)`.

```diff
diff --git a/src/world_engine/analyzer.py b/src/world_engine/analyzer.py
index 9ecc0de..e1d72cb 100644
--- a/src/world_engine/analyzer.py
+++ b/src/world_engine/analyzer.py
@@ -46,7 +46,6 @@ from .analyzer_transcript import (
     AttributionContext,
     _GOAL_ACTION_MAP,
     _MUTATION_TYPE_MAP,
-    _content_to_subject_slug,
     _mutation_match_key,
     analyze_overheard_lines,
     analyze_transcript,
diff --git a/src/world_engine/analyzer_transcript.py b/src/world_engine/analyzer_transcript.py
index 5abb885..e22396c 100644
--- a/src/world_engine/analyzer_transcript.py
+++ b/src/world_engine/analyzer_transcript.py
@@ -51,7 +51,6 @@ never migrated).
 from __future__ import annotations
 
 import logging
-import re
 import sys
 from dataclasses import dataclass, field
 from datetime import UTC, datetime
@@ -63,6 +62,7 @@ from . import llm_parse, ollama_client
 from .models import Character, Entity, Knowledge, ProposedMutation, PromptTemplate
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
+from .fact_refs import knowledge_key
 from .prose_render import knowledge_text
 from .writes import knowledge_level_rank
 
@@ -177,9 +177,6 @@ _KNOWLEDGE_LEVEL_DOWNGRADE: dict[str, str] = {
     "unaware": "rumor",
 }
 
-# Strips non-word chars for subject slugs.
-_SLUG_NON_WORD = re.compile(r"[^\w]")
-
 # Sentinel distinguishing "key absent from the model's item" from "key
 # present with a falsy value" — needed to know whether a field fell through
 # to an AttributionContext default (see _build_payload_relation_change /
@@ -239,15 +236,6 @@ def load_analysis_prompt(
     return templates[0]
 
 
-def _content_to_subject_slug(content: str) -> str:
-    """Derive a short DB-friendly subject slug from free-text content."""
-    if not content:
-        return "unknown"
-    words = content.lower().split()[:5]
-    parts = [_SLUG_NON_WORD.sub("", w) for w in words if w]
-    return ("_".join(p for p in parts if p))[:50] or "unknown"
-
-
 def _first_of(item: dict, *keys: str, default: Any = None) -> Any:
     """Return the value of the first key found in item."""
     for k in keys:
@@ -294,7 +282,6 @@ def _build_payload_new_knowledge(
         entity_id = attribution.default_subject_id
     payload = {
         "entity_id": entity_id,
-        "subject": _content_to_subject_slug(content),
         "level": item.get("level") or "rumor",
         "content": content,
         "source": "conversation",
@@ -362,7 +349,6 @@ def _build_payload_resource_change(
         k_content = str(raw_knowledge.get("content") or "")
         resource_payload["knowledge"] = {
             "entity_id": raw_knowledge.get("entity_id") or entity_id,
-            "subject": raw_knowledge.get("subject") or _content_to_subject_slug(k_content),
             "level": raw_knowledge.get("level") or "rumor",
             "content": k_content,
             "source": raw_knowledge.get("source") or "conversation",
@@ -416,9 +402,22 @@ def _guard_resource_change(item: dict) -> dict | None:
     payload = item["payload"]
     if not payload.get("entity_id") or not isinstance(payload.get("amount"), int):
         return None
+    if isinstance(payload.get("knowledge"), dict):
+        _strip_fact_naming(payload["knowledge"])
     return item
 
 
+def _strip_fact_naming(payload: dict) -> None:
+    # A model never names a fact (TICKET-0097, M1): a `subject` it wrote is
+    # at most the text of what was learned, and a `fact_id` it wrote is
+    # never trusted. Both leave the payload; a subject with no content
+    # becomes the content, so no model text is lost.
+    subject = payload.pop("subject", None)
+    payload.pop("fact_id", None)
+    if not str(payload.get("content") or "").strip() and subject:
+        payload["content"] = str(subject)
+
+
 def _guard_goal_change(item: dict, attribution: AttributionContext) -> tuple[dict | None, bool]:
     # goal_change (TICKET-0013, BRIEF-0013-c, H1/O1): npc_id is FORCED here,
     # in code — structural, not instructional. The model's input only ever
@@ -463,6 +462,14 @@ def _apply_type_guards(item: dict, attribution: AttributionContext) -> tuple[dic
         return _guard_relation_change(item), False
     if mt == "resource_change":
         return _guard_resource_change(item), False
+    if mt == "new_knowledge":
+        _strip_fact_naming(item["payload"])
+        return item, False
+    if mt == "knowledge_change":
+        # N1 (TICKET-0097): a model cannot name the row it would raise --
+        # knowledge upgrades come only from code-built proposals.
+        _log.warning("[skip] model-emitted knowledge_change dropped (N1): %r", item["payload"])
+        return None, False
     if mt == "goal_change":
         return _guard_goal_change(item, attribution)
     return item, False
@@ -540,7 +547,7 @@ def _mutation_match_key(mutation_type: str, payload: dict):
     in `_apply_mutation` at apply time (4c), not here at propose time.
     """
     if mutation_type == "new_knowledge":
-        return ("new_knowledge", payload.get("entity_id"), payload.get("subject"))
+        return ("new_knowledge", payload.get("entity_id"), knowledge_key(payload))
     if mutation_type == "status_change":
         eid = payload.get("entity_id")
         return ("status_change", eid) if eid else None
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index 351d421..ec37f60 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -30,6 +30,7 @@ from typing import Any, Optional
 
 from sqlmodel import Session, select
 
+from ..fact_refs import find_held, knowledge_key
 from ..gathering import close_open_memberships
 from ..ledger import get_balance as _get_balance
 from ..models import (
@@ -39,12 +40,12 @@ from ..models import (
     Conversation,
     DiscoverableDetail,
     Entity,
+    Fact,
     Faction,
     FactionMembership,
     FactionRole,
     GoalPrerequisite,
     Item,
-    Knowledge,
     NpcGoal,
     ProposedMutation,
 )
@@ -74,12 +75,12 @@ def _knowledge_leg_already_applied(
     db: Session,
     conversation_id: str,
     entity_id: str,
-    subject: str,
+    key: tuple[str, str],
 ) -> bool:
     """True if an equivalent knowledge acquisition was already applied for this
     conversation — scanning BOTH applied `new_knowledge` rows (payload
-    `entity_id`+`subject`) AND applied `resource_change` knowledge legs
-    (payload `knowledge.entity_id`+`knowledge.subject`). Part of the
+    `entity_id` + `knowledge_key`) AND applied `resource_change` knowledge legs
+    (payload `knowledge.entity_id` + `knowledge_key` of the leg). Part of the
     resource_change knowledge-leg block-whole guard (4c, BRIEF-19).
 
     KNOWN ACCEPTED GAP, one-directional by design: this guard protects a
@@ -99,11 +100,11 @@ def _knowledge_leg_already_applied(
     for row in rows:
         p = row.payload if isinstance(row.payload, dict) else {}
         if row.mutation_type == "new_knowledge":
-            if p.get("entity_id") == entity_id and p.get("subject") == subject:
+            if p.get("entity_id") == entity_id and knowledge_key(p) == key:
                 return True
         else:
             k = p.get("knowledge")
-            if isinstance(k, dict) and k.get("entity_id") == entity_id and k.get("subject") == subject:
+            if isinstance(k, dict) and k.get("entity_id") == entity_id and knowledge_key(k) == key:
                 return True
     return False
 
@@ -386,16 +387,20 @@ def _mutation_apply_new_knowledge(mut: ProposedMutation, payload: dict, db: Sess
         if subject_entity is None:
             return f"new_knowledge: subject_entity_id {subject_entity_id!r} is not an active entity of this world"
 
+    fact_id, refused = _payload_fact(mut, payload, entity_id, db)
+    if refused:
+        return refused
+
     session_id: Optional[str] = None
     if mut.conversation_id:
         conv = db.get(Conversation, mut.conversation_id)
         if conv:
             session_id = conv.session_id
 
-    write_knowledge(
+    known = write_knowledge(
         db,
         entity_id=entity_id,
-        subject=str(payload.get("subject") or "unknown"),
+        fact_id=fact_id,
         level=str(payload.get("level") or "rumor"),
         content=str(payload.get("content") or ""),
         source=str(payload.get("source") or "conversation"),
@@ -413,6 +418,7 @@ def _mutation_apply_new_knowledge(mut: ProposedMutation, payload: dict, db: Sess
         detail = db.get(DiscoverableDetail, str(detail_id))
         if detail is not None:
             detail.discovered = True
+            detail.fact_id = detail.fact_id or known.fact_id
             detail.updated_at = datetime.now(UTC)
             db.add(detail)
     return None
@@ -468,24 +474,40 @@ def _mutation_apply_item_update(mut: ProposedMutation, payload: dict, db: Sessio
     return None
 
 
+def _payload_fact(mut: ProposedMutation, payload: dict, entity_id: str, db: Session):
+    """(fact_id, refusal) for a `new_knowledge` payload (TICKET-0097). A
+    `fact_id` is written only by code (a coded list or a discovery), yet is
+    re-checked here: a fact of this mutation's world the entity does not
+    already know. A discovery's detail supplies its own fact (H1)."""
+    fact_id = payload.get("fact_id")
+    detail_id = payload.get("discoverable_detail_id")
+    detail = db.get(DiscoverableDetail, str(detail_id)) if detail_id else None
+    if fact_id is None and detail is not None and detail.fact_id is not None:
+        fact_id = detail.fact_id
+    if fact_id is None:
+        return None, None
+    fact = db.get(Fact, str(fact_id))
+    if fact is None or fact.world_id != mut.world_id:
+        return None, f"new_knowledge: fact {fact_id!r} is not a fact of this world"
+    if find_held(db, entity_id, {"fact_id": fact.id}) is not None:
+        return None, f"new_knowledge: entity already knows fact {fact.id!r}"
+    return fact.id, None
+
+
 # ── knowledge_change ──────────────────────────────────────────────────────────
 
 def _mutation_apply_knowledge_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
-    """Find the knowledge row by entity_id + subject, append its previous
-    state to change_history, update level and source. Monotone — never
-    applies a level that is not strictly higher than the row's current
-    level."""
+    """Find the knowledge row by entity_id + fact_id (TICKET-0097), append
+    its previous state to change_history, update level and source. Monotone
+    — never applies a level that is not strictly higher than the row's
+    current level. A payload without `fact_id` (written before 0097) is
+    refused and stays visible in the queue."""
     entity_id = payload.get("entity_id") or mut.target_id
-    subject = payload.get("subject")
-    if not entity_id or not subject:
-        return "knowledge_change: payload must contain entity_id and subject"
-
-    row = db.exec(
-        select(Knowledge).where(
-            Knowledge.entity_id == entity_id,
-            Knowledge.subject == subject,
-        )
-    ).first()
+    fact_id = payload.get("fact_id")
+    if not entity_id or not fact_id:
+        return "knowledge_change: payload must contain entity_id and fact_id"
+
+    row = find_held(db, entity_id, {"fact_id": fact_id})
     if row is None:
         return "knowledge row not found"
 
@@ -736,21 +758,14 @@ def _mutation_apply_resource_change(mut: ProposedMutation, payload: dict, db: Se
     # is written (not even the money leg).
     if knowledge_leg is not None:
         k_entity_id = knowledge_leg.get("entity_id")
-        k_subject = knowledge_leg.get("subject")
-        if not k_entity_id or not k_subject:
-            return "resource_change: knowledge leg must contain entity_id and subject"
-
-        existing_row = db.exec(
-            select(Knowledge).where(
-                Knowledge.entity_id == k_entity_id,
-                Knowledge.subject == k_subject,
-            )
-        ).first()
-        if existing_row is not None:
+        if not k_entity_id or not str(knowledge_leg.get("content") or "").strip():
+            return "resource_change: knowledge leg must contain entity_id and content"
+
+        if find_held(db, k_entity_id, knowledge_leg) is not None:
             return "knowledge already held (upgrade-by-purchase deferred)"
 
         if mut.conversation_id and _knowledge_leg_already_applied(
-            db, mut.conversation_id, k_entity_id, k_subject
+            db, mut.conversation_id, k_entity_id, knowledge_key(knowledge_leg)
         ):
             return "duplicate knowledge leg"
 
@@ -770,7 +785,6 @@ def _mutation_apply_resource_change(mut: ProposedMutation, payload: dict, db: Se
         write_knowledge(
             db,
             entity_id=knowledge_leg.get("entity_id"),
-            subject=str(knowledge_leg.get("subject") or "unknown"),
             level=str(knowledge_leg.get("level") or "rumor"),
             content=str(knowledge_leg.get("content") or ""),
             source=str(knowledge_leg.get("source") or "conversation"),
diff --git a/src/world_engine/cockpit/routes/mutations.py b/src/world_engine/cockpit/routes/mutations.py
index 2aafc9b..e25a3d0 100644
--- a/src/world_engine/cockpit/routes/mutations.py
+++ b/src/world_engine/cockpit/routes/mutations.py
@@ -38,6 +38,7 @@ from ...gathering import enter_location as _enter_location
 from ...gathering import migrate_npc as _migrate_npc
 from ...analyzer import analyze_overhearing as _analyze_overhearing
 from ...analyzer import analyze_window as _analyze_window
+from ...fact_refs import find_held, knowledge_key
 from ...tick import run_world_tick as _run_world_tick
 from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt
@@ -164,18 +165,13 @@ def _dup_tick_goal_change_create(payload: dict, db: Session) -> Optional[str]:
 
 
 def _dup_tick_new_knowledge(payload: dict, db: Session) -> Optional[str]:
-    """new_knowledge: duplicate iff a Knowledge row already exists for
-    (entity_id, subject)."""
-    existing = db.exec(
-        select(Knowledge).where(
-            Knowledge.entity_id == payload.get("entity_id"),
-            Knowledge.subject == payload.get("subject"),
-        )
-    ).first()
+    """new_knowledge: duplicate iff the entity already holds a Knowledge row
+    with the payload's identity (`fact_refs.find_held`, TICKET-0097)."""
+    existing = find_held(db, payload.get("entity_id"), payload)
     if existing is not None:
         return (
             f"new_knowledge for entity {str(payload.get('entity_id',''))[:8]}… "
-            f"subject={payload.get('subject')!r} already exists as a knowledge row."
+            f"already exists as knowledge row {existing.id[:8]}…."
         )
     return None
 
@@ -294,9 +290,9 @@ def _find_applied_duplicate_conversation_sourced(mut: ProposedMutation, db: Sess
     knowledge acquired in two different conversations is not a duplicate.
 
     Match keys (design choice):
-    - new_knowledge : same conversation_id + entity_id + subject. (entity,
-      subject) is the identity of a fact; applying twice creates duplicate
-      knowledge rows and inflates NPC context.
+    - new_knowledge : same conversation_id + entity_id + `knowledge_key`
+      (TICKET-0097: the fact, or the text of a new one); applying twice
+      creates duplicate knowledge rows and inflates NPC context.
     - status_change : same conversation_id + entity_id. Two status changes
       on the same entity in one conversation are unlikely to both be
       correct; surface for creator review.
@@ -337,10 +333,10 @@ def _find_applied_duplicate_conversation_sourced(mut: ProposedMutation, db: Sess
 
         if mut.mutation_type == "new_knowledge":
             if (prev_p.get("entity_id") == payload.get("entity_id")
-                    and prev_p.get("subject") == payload.get("subject")):
+                    and knowledge_key(prev_p) == knowledge_key(payload)):
                 return (
                     f"new_knowledge for entity {str(payload.get('entity_id',''))[:8]}… "
-                    f"subject={payload.get('subject')!r} was already applied by "
+                    f"{knowledge_key(payload)[1]!r} was already applied by "
                     f"mutation {prev.id[:8]}…  Applying again would create a "
                     f"duplicate knowledge row."
                 )
diff --git a/src/world_engine/fact_refs.py b/src/world_engine/fact_refs.py
new file mode 100644
index 0000000..fcd04fb
--- /dev/null
+++ b/src/world_engine/fact_refs.py
@@ -0,0 +1,110 @@
+"""Fact references (TICKET-0097): how a model names a fact, and how the
+mutation pipeline tells two knowledge proposals apart.
+
+A knowledge row is identified by the fact it knows (schema v2.09). Two
+consequences live here, and only here:
+
+- **Codes (D1'a, L1, Z2).** A model never emits a fact id and never copies a
+  free-text key. It is shown a coded list (`f1 — <the fact's text>`), emits
+  a code, and `CodedFacts.resolve` turns it back into a fact id -- or None
+  for any code the list did not show. Codes are positional: the same fact
+  ids in the same order give the same codes, so a list rebuilt from the same
+  rows resolves the codes a prompt carried.
+- **Identity key (M1).** `knowledge_key(payload)` is the dedup identity of a
+  `new_knowledge` payload or a `resource_change` knowledge leg:
+  `("fact", fact_id)` when the payload names an existing fact,
+  `("text", text_key(content))` otherwise. `text_key` is the former
+  `analyzer_transcript._content_to_subject_slug`, moved unchanged; it is
+  computed at compare time and never stored.
+"""
+
+from __future__ import annotations
+
+import re
+from dataclasses import dataclass
+from typing import Iterable, Optional
+
+from sqlmodel import Session, select
+
+from .models import Fact, Knowledge
+from .prose_render import fact_texts, knowledge_texts
+
+CODE_PREFIX = "f"
+
+# Strips non-word chars for text keys.
+_SLUG_NON_WORD = re.compile(r"[^\w]")
+
+
+def text_key(content: Optional[str]) -> str:
+    """Derive a short comparison key from free-text content: the first five
+    words, lower-cased, non-word characters stripped, joined by `_`, at
+    most 50 characters; "unknown" for empty content."""
+    if not content:
+        return "unknown"
+    words = content.lower().split()[:5]
+    parts = [_SLUG_NON_WORD.sub("", w) for w in words if w]
+    return ("_".join(p for p in parts if p))[:50] or "unknown"
+
+
+def knowledge_key(payload: dict) -> tuple[str, str]:
+    """The dedup identity of a knowledge payload (see module docstring)."""
+    fact_id = payload.get("fact_id")
+    if fact_id:
+        return ("fact", str(fact_id))
+    return ("text", text_key(str(payload.get("content") or "")))
+
+
+def find_held(db: Session, entity_id: Optional[str], payload: dict) -> Optional[Knowledge]:
+    """The row of `entity_id` a knowledge payload would duplicate, or None:
+    the row on the payload's `fact_id`, or else a row whose fact text or own
+    text has the payload's `text_key`."""
+    if not entity_id:
+        return None
+    kind, value = knowledge_key(payload)
+    if kind == "fact":
+        return db.exec(
+            select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == value)
+        ).first()
+    rows = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id)).all()
+    fact_keys = [text_key(t) for t in fact_texts(db, [db.get(Fact, row.fact_id) for row in rows])]
+    row_keys = [text_key(t) for t in knowledge_texts(db, rows)]
+    for row, fact_key, row_key in zip(rows, fact_keys, row_keys):
+        if value in (fact_key, row_key):
+            return row
+    return None
+
+
+@dataclass(frozen=True)
+class CodedFacts:
+    """A coded fact list: `lines[i]` shows the fact coded `f{i+1}`."""
+
+    codes: dict[str, str]
+    lines: tuple[str, ...]
+
+    def resolve(self, code: object) -> Optional[str]:
+        """The fact id behind `code`, or None when the list did not show it.
+        Surrounding whitespace and brackets are tolerated (`[f3]`, ` F3 `)."""
+        if not isinstance(code, str):
+            return None
+        return self.codes.get(code.strip().strip("[]").strip().lower())
+
+    def code_of(self, fact_id: str) -> Optional[str]:
+        """The code the list gives `fact_id`, or None."""
+        return next((code for code, fid in self.codes.items() if fid == fact_id), None)
+
+
+def code_facts(db: Session, fact_ids: Iterable[str]) -> CodedFacts:
+    """Code `fact_ids` in order, first occurrence wins; an id with no `fact`
+    row is skipped. Each line is `f<n> — <the fact's rendered text>`."""
+    ordered: list[str] = []
+    for fact_id in fact_ids:
+        if fact_id and fact_id not in ordered:
+            ordered.append(fact_id)
+    facts = [fact for fact in (db.get(Fact, fid) for fid in ordered) if fact is not None]
+    codes: dict[str, str] = {}
+    lines: list[str] = []
+    for index, (fact, text) in enumerate(zip(facts, fact_texts(db, facts)), start=1):
+        code = f"{CODE_PREFIX}{index}"
+        codes[code] = fact.id
+        lines.append(f"{code} — {text}")
+    return CodedFacts(codes=codes, lines=tuple(lines))
diff --git a/src/world_engine/tick.py b/src/world_engine/tick.py
index 08ce669..f54a28f 100644
--- a/src/world_engine/tick.py
+++ b/src/world_engine/tick.py
@@ -23,6 +23,7 @@ from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
 from .analyzer import load_analysis_prompt
+from .fact_refs import knowledge_key
 from .models import Agenda, Character, Entity, FactionMembership, Knowledge, ProposedMutation
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
@@ -139,9 +140,9 @@ def _tick_npc_dedup_note(mutation_type: str, payload: dict, state: dict[str, Any
             return f"duplicate goal_change dropped: {payload['action']} {payload['goal']!r}"
         state["goal"].add(key)
     elif mutation_type == "new_knowledge":
-        key = (payload["entity_id"], payload["subject"])
+        key = (payload["entity_id"], knowledge_key(payload))
         if key in state["knowledge"]:
-            return f"duplicate new_knowledge dropped: subject={payload['subject']!r}"
+            return f"duplicate new_knowledge dropped: {key[1][1]!r}"
         state["knowledge"].add(key)
     elif mutation_type == "npc_move":
         if state["move"]:
diff --git a/src/world_engine/tick_normalize.py b/src/world_engine/tick_normalize.py
index a9c17d9..30dfd42 100644
--- a/src/world_engine/tick_normalize.py
+++ b/src/world_engine/tick_normalize.py
@@ -23,7 +23,8 @@ from typing import Any
 
 from sqlmodel import Session, select
 
-from .analyzer import _GOAL_ACTION_MAP, _MUTATION_TYPE_MAP, _content_to_subject_slug
+from .analyzer import _GOAL_ACTION_MAP, _MUTATION_TYPE_MAP
+from .fact_refs import text_key
 from .models import Agenda, AgendaStep, Character, Entity, Faction, Relation
 from .tick_context import _perceived_target
 
@@ -715,7 +716,7 @@ def _tick_normalize_new_knowledge(
     if not content:
         _log.warning("[tick] dropped new_knowledge: empty content")
         return None
-    subject = str(payload_in.get("subject") or "").strip() or _content_to_subject_slug(content)
+    subject = str(payload_in.get("subject") or "").strip() or text_key(content)
 
     # Z3 floor (verbatim mechanics) — mechanical provenance only, never
     # touches is_secret: confidentiality is the receiving NPC's disposition
diff --git a/src/world_engine/writes/knowledge.py b/src/world_engine/writes/knowledge.py
index 5656c62..e224404 100644
--- a/src/world_engine/writes/knowledge.py
+++ b/src/world_engine/writes/knowledge.py
@@ -23,8 +23,11 @@ call site (`_apply_mutation`'s `new_knowledge`/`resource_change` branches,
 knowledge, and the creator CRUD) passes through this one function, so the
 fallback lives here rather than being duplicated at each caller — an
 explicit `fact_id` attaches to that existing fact; omitting it auto-creates
-a free-standing one (`writes/facts.py::create_fact`) with `content =
-subject`, matching the creator CRUD's documented behaviour exactly.
+a free-standing one (`writes/facts.py::create_fact`) whose content is the
+row's own stored text (TICKET-0097, M1: a fact born here carries the
+sentence, not a slug) -- the given `subject` only when the row has no text.
+`subject` is optional and derived: absent, the column takes the fact's
+stored content (v2.10 drops the column; nothing reads it as a key).
 
 `subject_entity_ids` (TICKET-0087, BRIEF-0087-a) attaches participants to
 the row's fact on create only, with no `role`; a participant IS the
@@ -188,7 +191,8 @@ def _build_knowledge_update(
     (matches the analyzer's default for unreliable local-model output).
     On create, `fact_id` attaches to an existing fact; omitting it
     auto-creates a free-standing one via `writes/facts.py::create_fact`
-    with `content = subject` (see module docstring). `subject_entity_ids`
+    whose content is the row's stored text (see module docstring).
+    `subject_entity_ids`
     is attached to that fact on create only (see module docstring); ignored
     when updating an existing row.
     """
@@ -213,13 +217,14 @@ def _build_knowledge_update(
 
     if not entity_id:
         raise ValueError("write_knowledge: entity_id is required to create")
-    resolved_subject = subject or "unknown"
+    stored, pending = _tokenized_content(db, entity_id, content)
     if fact_id is None:
         entity = db.get(Entity, entity_id)
         if entity is None:
             raise ValueError(f"write_knowledge: entity {entity_id!r} not found")
+        text = stored if isinstance(stored, str) and stored.strip() else (subject or "unknown")
         fact = create_fact(
-            db, world_id=entity.world_id, content=resolved_subject, created_by=changed_by,
+            db, world_id=entity.world_id, content=text, created_by=changed_by,
             facet="information",
         )
     else:
@@ -227,9 +232,8 @@ def _build_knowledge_update(
         if fact is None:
             raise ValueError(f"write_knowledge: fact {fact_id!r} not found")
     _attach_subject_participants(db, fact=fact, subject_entity_ids=subject_entity_ids)
-    stored, pending = _tokenized_content(db, entity_id, content)
     return Knowledge(
-        entity_id=entity_id, fact_id=fact.id, subject=resolved_subject, level=norm_level,
+        entity_id=entity_id, fact_id=fact.id, subject=subject or fact.content_raw, level=norm_level,
         content_raw=stored, source=source, is_incorrect=bool(is_incorrect),
         is_secret=bool(is_secret), share_threshold=threshold, session_id=session_id,
     ), pending
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index a4e6fd9..e6ae707 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17050,6 +17050,39 @@ reference, so a new reader of `subject` is red.
 
 **Also closed here.** TICKET-0096 passed its live gate (Nia, 2026-09-28).
 
+## KNOWLEDGE IDENTITY IN THE MUTATION PIPELINE (TICKET-0097) -- A PROPOSAL NAMES A FACT OR CARRIES A SENTENCE (BRIEF-0097-b, no schema change)
+
+**`fact_refs.py` is the one place knowledge identity is computed.**
+`knowledge_key(payload)` is `("fact", fact_id)` when a payload names an
+existing fact, `("text", text_key(content))` otherwise; `text_key` is the
+former `_content_to_subject_slug`, moved unchanged, computed at compare time
+and never stored. `find_held(db, entity_id, payload)` is the row a payload
+would duplicate. Every dedup that keyed on `(entity_id, subject)` --
+`_mutation_match_key`, the tick emit-time note, `_dup_tick_new_knowledge`,
+the conversation-sourced duplicate guard, `_knowledge_leg_already_applied`,
+the resource leg's held-row guard -- keys on these instead.
+
+**M1 -- a fact born from a proposal carries the sentence.** `write_knowledge`
+without `fact_id` creates the fact from the row's own stored text; a model
+never names a fact: `subject` and `fact_id` leave every model-built
+`new_knowledge` payload and `resource_change` leg (a subject with no content
+becomes the content, so no model text is lost).
+
+**N1 -- a model cannot raise a level.** A `knowledge_change` the window
+analysis emits is dropped and logged; upgrades come only from code-built
+proposals that carry a `fact_id` (overhearing, BRIEF-0097-c; the day lead,
+BRIEF-0097-d). `_mutation_apply_knowledge_change` finds its row by
+`(entity_id, fact_id)` and refuses a payload without `fact_id`: the one such
+row in prod (approved, never applied) stays visible in the queue.
+
+**`fact_id` is re-checked at apply.** A `new_knowledge` `fact_id` is written
+only by code, yet `_payload_fact` refuses a fact of another world or one the
+entity already knows (the unique index would otherwise abort the SAVEPOINT).
+
+**H1, apply half.** The first approved discovery of a detail sets
+`discoverable_detail.fact_id` to the fact its knowledge row created; every
+later discovery of that detail attaches to that fact.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index a0af6f0..910e82e 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -26,6 +26,19 @@ K3 -- census. The `subject` references of `src/world_engine` (an attribute
    `subject` parameter), counted per file, equal `_SUBJECT_CENSUS` exactly.
    Each brief of TICKET-0097 lowers it in the same commit that removes a
    reference; a new reference is red until someone decides it belongs.
+K4 -- the mutation pipeline keys knowledge by fact (C-01, C-02):
+   a. `knowledge_key` on the `_KEY_CASES` table;
+   b. `new_knowledge` without `fact_id` creates a fact whose content is the
+      row's stored text (M1);
+   c. `new_knowledge` with a `fact_id` attaches to it once; a second apply
+      for the same entity, or a fact of another world, is refused;
+   d. `knowledge_change` finds its row by `fact_id`; a payload without one
+      is refused;
+   e. two approved discoveries of one detail share the detail's fact (H1);
+   f. a `resource_change` knowledge leg the buyer already holds (same text)
+      is refused; a leg without content is refused;
+   g. window normalization drops a model-emitted `knowledge_change` (N1)
+      and strips `subject` / `fact_id` from a model `new_knowledge`.
 
 Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB.
@@ -49,15 +62,13 @@ FAILURES: list[str] = []
 
 _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/analyzer.py": 2,
-    "src/world_engine/analyzer_transcript.py": 13,
+    "src/world_engine/analyzer_transcript.py": 10,
     "src/world_engine/cockpit/crud/_shared.py": 3,
     "src/world_engine/cockpit/crud/knowledge.py": 8,
     "src/world_engine/cockpit/crud/locations.py": 7,
-    "src/world_engine/cockpit/mutations.py": 11,
     "src/world_engine/cockpit/play_discovery.py": 3,
     "src/world_engine/cockpit/routes/creator.py": 2,
     "src/world_engine/cockpit/routes/day.py": 2,
-    "src/world_engine/cockpit/routes/mutations.py": 6,
     "src/world_engine/cockpit/routes/npc_agent.py": 2,
     "src/world_engine/context.py": 4,
     "src/world_engine/day_mutations.py": 4,
@@ -71,7 +82,7 @@ _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/models/canon_knowledge.py": 1,
     "src/world_engine/scene_format.py": 3,
     "src/world_engine/subject_resolve.py": 4,
-    "src/world_engine/tick.py": 4,
+    "src/world_engine/tick.py": 2,
     "src/world_engine/tick_context.py": 1,
     "src/world_engine/tick_normalize.py": 2,
     "src/world_engine/writes/facets.py": 1,
@@ -144,7 +155,7 @@ def _fresh_engine():
             del sys.modules[name]
     from world_engine.db import create_db_and_tables, engine
     create_db_and_tables()
-    return engine, pathlib.Path(tmp_dir) / "check.db"
+    return engine
 
 
 def rule_k1(tables) -> None:
@@ -175,7 +186,14 @@ def _insert(cursor, rows) -> None:
         cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))
 
 
-def _v2_08_database(db_path: pathlib.Path) -> sqlite3.Connection:
+def _v2_08_database() -> sqlite3.Connection:
+    """A second database, built from the current metadata, then taken back
+    to the v2.08 shape of the two objects v2.09 creates."""
+    from sqlalchemy import create_engine
+    from sqlmodel import SQLModel
+
+    db_path = pathlib.Path(tempfile.mkdtemp()) / "v2_08.db"
+    SQLModel.metadata.create_all(create_engine(f"sqlite:///{db_path}"))
     conn = sqlite3.connect(db_path, isolation_level=None)
     conn.execute("DROP INDEX idx_knowledge_entity_fact")
     conn.execute("DROP TABLE discoverable_detail")
@@ -249,9 +267,9 @@ def _k2b_to_f(conn) -> None:
         fail(f"K2f gates are {gates!r}")
 
 
-def rule_k2(db_path: pathlib.Path) -> None:
+def rule_k2() -> None:
     migration = _load_migration()
-    conn = _v2_08_database(db_path)
+    conn = _v2_08_database()
     _k2a(conn, migration)
     try:
         _run(conn, migration)
@@ -266,6 +284,144 @@ def rule_k2(db_path: pathlib.Path) -> None:
         fail(f"K2g the second run changed something: {report!r}")
 
 
+_KEY_CASES: tuple[tuple[dict, tuple[str, str]], ...] = (
+    ({"fact_id": "f-9"}, ("fact", "f-9")),
+    ({"fact_id": "f-9", "content": "Le Conseil ment"}, ("fact", "f-9")),
+    ({"content": "Le Conseil cache l'un de ses membres."}, ("text", "le_conseil_cache_lun_de")),
+    ({"content": ""}, ("text", "unknown")),
+    ({}, ("text", "unknown")),
+)
+
+
+def _k4_world(session):
+    from world_engine.models import Character, DiscoverableDetail, Entity, World
+
+    ids = {}
+    for key, name in (("w", "W"), ("w2", "W2")):
+        world = World(name=name)
+        session.add(world)
+        session.flush()
+        ids[key] = world.id
+    for key, world_key, etype, name in (
+        ("ana", "w", "character", "Ana"), ("bel", "w", "character", "Bel"),
+        ("loc", "w", "location", "Lieu"), ("out", "w2", "character", "Out"),
+    ):
+        entity = Entity(world_id=ids[world_key], type=etype, name=name)
+        session.add(entity)
+        session.flush()
+        ids[key] = entity.id
+        if etype == "character":
+            session.add(Character(id=entity.id, world_id=ids[world_key], character_type="npc"))
+    detail = DiscoverableDetail(world_id=ids["w"], location_id=ids["loc"], subject="lettre",
+                                content="Une lettre cachée sous le comptoir.")
+    session.add(detail)
+    session.flush()
+    ids["detail"] = detail.id
+    return ids
+
+
+def _k4_mutation(session, world_id: str, mutation_type: str):
+    from world_engine.models import ProposedMutation
+
+    mut = ProposedMutation(world_id=world_id, source_type="conversation", mutation_type=mutation_type,
+                           payload={}, status="proposed", proposed_by="check")
+    session.add(mut)
+    session.flush()
+    return mut
+
+
+def _k4_apply(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.cockpit.mutations import (
+        _mutation_apply_knowledge_change, _mutation_apply_new_knowledge,
+        _mutation_apply_resource_change,
+    )
+    from world_engine.models import DiscoverableDetail, Fact, Knowledge
+    from world_engine.writes import create_fact
+
+    new = _k4_mutation(session, ids["w"], "new_knowledge")
+    err = _mutation_apply_new_knowledge(new, {"entity_id": ids["ana"], "content": "La mer est rouge."}, session)
+    row = session.exec(select(Knowledge).where(Knowledge.entity_id == ids["ana"])).one()
+    fact = session.get(Fact, row.fact_id)
+    if err or fact.content_raw != row.content_raw:
+        fail(f"K4b a new fact does not carry the row's text: err={err!r} fact={fact.content_raw!r}")
+    shared = create_fact(session, world_id=ids["w"], content="Le port ferme.", created_by="check",
+                         facet="information")
+    foreign = create_fact(session, world_id=ids["w2"], content="Ailleurs.", created_by="check",
+                          facet="information")
+    session.flush()
+    for entity, fact_id, expect in ((ids["bel"], shared.id, None), (ids["bel"], shared.id, "already knows"),
+                                    (ids["bel"], foreign.id, "not a fact of this world")):
+        err = _mutation_apply_new_knowledge(
+            new, {"entity_id": entity, "fact_id": fact_id, "content": "x", "level": "rumor"}, session)
+        if (err is None) != (expect is None) or (expect and expect not in err):
+            fail(f"K4c new_knowledge on fact {fact_id[:6]}: got {err!r}, expected {expect!r}")
+    session.flush()
+    change = _k4_mutation(session, ids["w"], "knowledge_change")
+    err = _mutation_apply_knowledge_change(
+        change, {"entity_id": ids["bel"], "fact_id": shared.id, "to_level": "knows"}, session)
+    level = session.exec(select(Knowledge.level).where(
+        Knowledge.entity_id == ids["bel"], Knowledge.fact_id == shared.id)).one()
+    if err or level != "knows":
+        fail(f"K4d knowledge_change by fact_id: err={err!r} level={level!r}")
+    err = _mutation_apply_knowledge_change(
+        change, {"entity_id": ids["bel"], "subject": "Le port ferme.", "to_level": "fully_understands"}, session)
+    if not err or "fact_id" not in err:
+        fail(f"K4d a knowledge_change without fact_id was not refused: {err!r}")
+    for learner in ("ana", "bel"):
+        err = _mutation_apply_new_knowledge(new, {
+            "entity_id": ids[learner], "content": "Une lettre cachée sous le comptoir.",
+            "level": "knows", "discoverable_detail_id": ids["detail"]}, session)
+        if err:
+            fail(f"K4e discovery by {learner} refused: {err!r}")
+        session.flush()
+    detail = session.get(DiscoverableDetail, ids["detail"])
+    holders = session.exec(select(Knowledge.entity_id).where(Knowledge.fact_id == detail.fact_id)).all()
+    if not detail.discovered or sorted(holders) != sorted([ids["ana"], ids["bel"]]):
+        fail(f"K4e the detail's fact is not shared by both discoverers: {holders!r}")
+    buy = _k4_mutation(session, ids["w"], "resource_change")
+    for leg, expect in (({"entity_id": ids["ana"], "content": "La mer est rouge."}, "already held"),
+                        ({"entity_id": ids["ana"], "subject": "mer_rouge"}, "content")):
+        err = _mutation_apply_resource_change(buy, {"entity_id": ids["ana"], "amount": 0,
+                                                    "knowledge": leg}, session)
+        if not err or expect not in err:
+            fail(f"K4f resource leg {leg!r}: got {err!r}, expected {expect!r}")
+
+
+def _k4_window() -> None:
+    from world_engine.analyzer_transcript import AttributionContext, _normalize_to_schema
+
+    attribution = AttributionContext(default_subject_id="npc", default_counterparty_id="pc")
+    item, _u, _mt = _normalize_to_schema(
+        {"mutation_type": "knowledge_change", "payload": {"entity_id": "pc", "subject": "x"}},
+        "w", attribution, None)
+    if item is not None:
+        fail("K4g a model-emitted knowledge_change was not dropped (N1)")
+    item, _u, _mt = _normalize_to_schema(
+        {"mutation_type": "new_knowledge", "target_table": "knowledge",
+         "payload": {"entity_id": "pc", "subject": "mer_rouge", "fact_id": "forged", "content": ""}},
+        "w", attribution, None)
+    payload = item["payload"] if item else {}
+    if "subject" in payload or "fact_id" in payload or payload.get("content") != "mer_rouge":
+        fail(f"K4g a model new_knowledge payload kept a fact name: {payload!r}")
+
+
+def rule_k4(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.fact_refs import knowledge_key
+
+    for payload, expected in _KEY_CASES:
+        if knowledge_key(payload) != expected:
+            fail(f"K4a knowledge_key({payload!r}) = {knowledge_key(payload)!r}, expected {expected!r}")
+    with Session(engine) as session:
+        ids = _k4_world(session)
+        _k4_apply(session, ids)
+        session.rollback()
+    _k4_window()
+
+
 def census() -> dict[str, int]:
     counts: dict[str, int] = {}
     for path in sorted((SRC / "world_engine").rglob("*.py")):
@@ -291,14 +447,15 @@ def rule_k3() -> None:
 
 
 def main() -> int:
-    _engine, db_path = _fresh_engine()
+    engine = _fresh_engine()
     from sqlmodel import SQLModel
 
     import world_engine.models  # noqa: F401 -- registers every table
 
     rule_k1(SQLModel.metadata.tables)
-    rule_k2(db_path)
+    rule_k2()
     rule_k3()
+    rule_k4(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
```

## Scope OUT

- Overhearing and the tick (C) — they still pass a subject until C; B keeps them working because `write_knowledge` still accepts `subject`.
- Day gates (D), link agent (E), creator surface (F), dropping the column (G).
- Refusing or rewriting the one approved-unapplied `knowledge_change` in prod: it is refused at apply and stays visible (N1).
- Every later brief of the lot: BRIEF-0097-C, BRIEF-0097-D, BRIEF-0097-E, BRIEF-0097-F, BRIEF-0097-G.

## Invariants to defend

**`new_knowledge` / `status_change` are idempotent facts** — the dedup key changes shape (C-01) but stays identity-based and conversation-scoped. **Knowledge levels never decrease** — `_mutation_apply_knowledge_change` keeps its monotone guard. **`resource_change` writes two canon tables in one SAVEPOINT** — the leg's guard still refuses the whole mutation. **`new_knowledge`'s `subject_entity_id` is untrusted** — untouched. **Commit before touching any canon-writing path** — hard.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A test outside `knowledge_identity.py` needs a model `knowledge_change` to apply.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `knowledge_identity.py` K3 fails only on counts, with every reported file named in this brief's diff: re-run the census (see Done means) and report the table.

REPORT-ONLY:
- Any other file still naming `subject` in a comment or docstring.
- Timing of the corpus run.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` of the commit lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` (regenerated).
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/knowledge_identity.py` → `PASS`.
- Mutation test: in `_payload_fact`, replace the `find_held(...) is not None` test by `False`; `knowledge_identity.py` no longer passes (IntegrityError); revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

Decision entry `KNOWLEDGE IDENTITY IN THE MUTATION PIPELINE … (BRIEF-0097-b, no schema change)`. CLAUDE.md's dedup invariant is updated in F, with the file-structure line.
