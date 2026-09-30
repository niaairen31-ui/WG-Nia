<!-- slug: play-readers -->
# BRIEF 0097-E — "Play readers know facts, not subjects"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: D
Commit header for decisions: `(BRIEF-0097-e, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/link_author.py:310` → `"subject": f"npc:{other_id}",`
- `src/world_engine/link_context.py:69` → `npc_subjects = {f"npc:{i}" for i in npc_ids}`
- `src/world_engine/scene_format.py:44` → `cluster_subjects: dict[str, list[str]] = {}`
- `src/world_engine/writes/facets.py:187` → `subject=CREATOR_META_KEY,`
- `src/world_engine/writes/relations.py:384` → `subject=render(db, lien.content_raw), …`
- `src/world_engine/knowledge_resolve.py:359` → `subject=render(db, fact.content_raw),`
- `tooling/verify/checks/link_agent_strata.py` rule 3 → requires a `"subject"` f-string with the `npc:` literal

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

### R-10 — link agent
Opened: `link_author.py:150-320, 500-615, 880-915`, `link_context.py:55-125`,
`tooling/verify/checks/link_agent_strata.py:150-215`.
Finding: the stamp `"subject": f"npc:{other_id}"` is built in one function;
rule 3 requires exactly that shape; `commit_batch` calls
`write_knowledge(db, **row.payload)` and refuses before coherence ran.
Consequence: E stamps `"subject_entity_ids": [other_id]` (a kwarg
`write_knowledge` already takes) and retargets rule 3.

### R-11 — `discoverable_detail`
Opened: `models/canon.py:670-700`, `scene_format.py:17-80`,
`cockpit/play_discovery.py`, `cockpit/mutations._mutation_apply_new_knowledge`.
Finding: `subject` is the detail's own label (`DiscDetailsEditor`); the
discovery proposal copies it; `active_signposts` compares it to
`knowledge.subject`.
Consequence: `detail.subject` stays (not a knowledge key); H1 adds `fact_id`.

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

### C-07 — link agent stamp
Produced by: E   Consumed by: nothing later
Staged knowledge payload: `"subject_entity_ids": [other_id]`, no `subject`.
Canon graph knowledge row: `"about_entity_ids": [sorted participant ids]`.

## Context

Every play-side reader that showed or matched a subject now reads the fact: labels are its text, the link agent's aboutness is its participant (G1), signposts compare facts (H1). Writers stop naming a subject.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: shows fact text in the NPC and MJ contexts (MJ snapshot key `fact`) and the Lore dossier (`fact`); stamps `subject_entity_ids` in the link agent (C-07), reads shared knowledge and the canon graph by participant, renames the coherence stamp check `_about_stamp_findings`; silences signposts by fact; stops the lien, creator-note and resolver rows from naming a subject; retargets `link_agent_strata.py` rule 3; drops the subject from `fact_facets.py` R5; adds K7.
2. Regenerate the index.
3. Message: `feat(knowledge): play readers know facts, not subjects (BRIEF-0097-e)`.

```diff
diff --git a/src/world_engine/context.py b/src/world_engine/context.py
index 9430a15..2085a98 100644
--- a/src/world_engine/context.py
+++ b/src/world_engine/context.py
@@ -34,6 +34,7 @@ from .models import (
     Character,
     Entity,
     Event,
+    Fact,
     FactionMembership,
     Gathering,
     GatheringMember,
@@ -49,7 +50,7 @@ from .models import (
 from .facet_reads import facts_of, joined, known_facts_of
 from .facets import FACETS
 from .knowledge_resolve import resolve_default_rows
-from .prose_render import knowledge_texts
+from .prose_render import fact_texts, knowledge_texts
 from .schedule_reads import where_is
 from .context_describe import (
     _mj_context_co_presents,
@@ -121,9 +122,16 @@ def _section(title: str, body: str) -> str:
     return f"=== {title} ===\n{body.rstrip()}\n"
 
 
-def _knowledge_line(k: Knowledge, content: str | None) -> str:
-    """`content` is `k`'s rendered text (`prose_render.knowledge_texts`)."""
-    text = content or f"{k.subject} ({k.level})"
+def _row_fact_texts(session: Session, rows: list[Knowledge]) -> list[str]:
+    """The rendered text of each row's fact, one entity query (TICKET-0097:
+    the fallback label of a row with no text of its own)."""
+    return fact_texts(session, [session.get(Fact, k.fact_id) for k in rows])
+
+
+def _knowledge_line(k: Knowledge, content: str | None, fact: str) -> str:
+    """`content` is `k`'s rendered text (`prose_render.knowledge_texts`),
+    `fact` its fact's rendered text."""
+    text = content or f"{fact} ({k.level})"
     if k.is_incorrect:
         text += " (tu en es convaincu, mais c'est faux)"
     return f"- {text}"
@@ -363,7 +371,8 @@ def _npc_context_speak(npc_id: str, disclosure_intensity: int, session: Session)
             "Tu peux parler librement de ce qui suit, si la conversation s'y prête :\n"
         )
         speak_body += "\n".join(
-            _knowledge_line(k, text) for k, text in zip(allowed, knowledge_texts(session, allowed))
+            _knowledge_line(k, text, fact) for k, text, fact
+            in zip(allowed, knowledge_texts(session, allowed), _row_fact_texts(session, allowed))
         )
         return speak_body
     return "Tu n'as rien de particulier à partager spontanément."
@@ -679,8 +688,10 @@ def _mj_context_player_knowledge(player_character_id: str, db: Session) -> list[
         db, player_character_id, {k.fact_id for k in knowledge_rows}
     )
     return [
-        {"subject": k.subject, "level": k.level, "content": text}
-        for k, text in zip(knowledge_rows, knowledge_texts(db, knowledge_rows))
+        {"fact": fact, "level": k.level, "content": text}
+        for k, text, fact in zip(
+            knowledge_rows, knowledge_texts(db, knowledge_rows), _row_fact_texts(db, knowledge_rows),
+        )
     ]
 
 
@@ -751,7 +762,7 @@ def assemble_mj_context(
       `location.magic_status` is deliberately excluded (not directly
       perceivable).
     - `player_knowledge` (static): all `knowledge` rows belonging to the
-      player character (subject, level, content) — these are the player's
+      player character (fact text, level, content) — these are the player's
       own, so no further filtering is applied (a player's own `is_secret`
       row is something they already know, not a leak).
     - `public_events` (static): `event` rows with `knowledge_status IN
@@ -806,7 +817,7 @@ def assemble_mj_context(
 
 
 def _mj_knowledge_line(k: dict) -> str:
-    text = k.get("content") or f"{k.get('subject')} ({k.get('level')})"
+    text = k.get("content") or f"{k.get('fact')} ({k.get('level')})"
     return f"- {text}"
 
 
diff --git a/src/world_engine/knowledge_resolve.py b/src/world_engine/knowledge_resolve.py
index 86757d7..1d66fc2 100644
--- a/src/world_engine/knowledge_resolve.py
+++ b/src/world_engine/knowledge_resolve.py
@@ -50,7 +50,6 @@ from .facets import DESCRIPTIVE_FACETS
 from .models import (
     Character, Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, Location,
 )
-from .prose_render import render
 from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER
 
 DEFAULT_SHARE_THRESHOLD = 50
@@ -356,7 +355,7 @@ def resolve_default_rows(
             continue
         rows.append(
             Knowledge(
-                entity_id=entity_id, fact_id=fact_id, subject=render(db, fact.content_raw),
+                entity_id=entity_id, fact_id=fact_id,
                 level=level, content_raw=fact.content_raw, is_secret=False,
                 share_threshold=DEFAULT_SHARE_THRESHOLD,
             )
diff --git a/src/world_engine/link_author.py b/src/world_engine/link_author.py
index 53c2fef..8a3178e 100644
--- a/src/world_engine/link_author.py
+++ b/src/world_engine/link_author.py
@@ -46,6 +46,7 @@ from .link_sheet import _npc_sheet
 from .models import (
     Character,
     Entity,
+    FactParticipant,
     Knowledge,
     LinkBatch,
     LinkBatchRow,
@@ -150,16 +151,16 @@ def _load_pair_template(db: Session) -> PromptTemplate | None:
 
 
 def _shared_knowledge_lines(db: Session, holder_id: str, other_id: str, holder_name: str) -> list[str]:
-    """Existing knowledge `holder_id` holds ABOUT `other_id`, via the D3
-    `npc:{entity_id}` subject convention — the same stamp this pass writes.
-    is_secret=TRUE rows MAY enter (creator-surface exception, RECON-0036
-    R-4); rows about anyone else (third parties) never match this subject
-    and are excluded by construction."""
+    """Existing knowledge `holder_id` holds ABOUT `other_id`: every row on a
+    fact `other_id` participates in (TICKET-0097, G1 — the participant this
+    pass stamps, D3). is_secret=TRUE rows MAY enter (creator-surface
+    exception, RECON-0036 R-4); rows about anyone else (third parties) never
+    match and are excluded by construction."""
     rows = db.exec(
-        select(Knowledge).where(
-            Knowledge.entity_id == holder_id,
-            Knowledge.subject == f"npc:{other_id}",
-        )
+        select(Knowledge)
+        .join(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
+        .where(Knowledge.entity_id == holder_id, FactParticipant.entity_id == other_id)
+        .order_by(Knowledge.id)
     ).all()
     return [
         f"- {holder_name} already knows (level={r.level}, secret={r.is_secret}): "
@@ -305,9 +306,11 @@ def _build_knowledge_row(batch: LinkBatch, a_id: str, b_id: str, item: dict) ->
 
     payload = {
         "mode": "update", "knowledge_id": None, "entity_id": holder_id,
-        # D3, code-stamped: the model never emits "subject" — this is the
-        # single construction site (link_agent_strata.py asserts it).
-        "subject": f"npc:{other_id}",
+        # D3, code-stamped: the model never names who the row is about —
+        # this is the single construction site (link_agent_strata.py asserts
+        # it). `write_knowledge` attaches `other_id` as the new fact's
+        # participant (TICKET-0097, G1).
+        "subject_entity_ids": [other_id],
         "level": level,
         "content": item.get("content"), "source": item.get("source"),
         "is_incorrect": bool(item.get("is_incorrect", False)),
@@ -430,7 +433,7 @@ def patch_row(
     """Edits ONE staged row's payload fields and/or row_status (0036-d's
     one backend addition) — staging only, batch must be open. Payload
     fields reuse `_coerce_patch_value`'s vocab/clamp rules, the same gate
-    the coherence patch pipeline uses (W); ids/mode/subject/session
+    the coherence patch pipeline uses (W); ids/mode/participant stamp/session
     bookkeeping stay unpatchable here too. row_status is reversible while
     the batch stays open (reject / un-reject)."""
     if batch.status != "open":
@@ -505,13 +508,17 @@ def _flag(target_scope: str, target_id: str, problem: str) -> dict:
 
 def _duplicate_pair_findings(rows: list[LinkBatchRow]) -> list[dict]:
     """Duplicate staged rows for the same pair + kind + discriminator
-    (relation type, or knowledge subject) — flags every row past the
-    first in each group, in deterministic (created_at, id) order."""
+    (relation type, or knowledge holder and stamped participant) — flags
+    every row past the first in each group, in deterministic (created_at,
+    id) order."""
     groups: dict[tuple, list[LinkBatchRow]] = {}
     for row in rows:
         if row.kind == "no_links":
             continue
-        discriminator = row.payload.get("type") if row.kind == "relation" else row.payload.get("subject")
+        discriminator = (
+            row.payload.get("type") if row.kind == "relation"
+            else (row.payload.get("entity_id"), tuple(row.payload.get("subject_entity_ids") or ()))
+        )
         key = (frozenset((row.pair_a_id, row.pair_b_id)), row.kind, discriminator)
         groups.setdefault(key, []).append(row)
 
@@ -575,20 +582,20 @@ def _vocab_findings(rows: list[LinkBatchRow]) -> list[dict]:
     return findings
 
 
-def _subject_stamp_findings(rows: list[LinkBatchRow]) -> list[dict]:
-    """D3 defense in depth: a staged knowledge row whose subject doesn't
-    match npc:{other_id} for its own pair."""
+def _about_stamp_findings(rows: list[LinkBatchRow]) -> list[dict]:
+    """D3 defense in depth: a staged knowledge row whose stamped participant
+    isn't exactly the other side of its own pair."""
     findings = []
     for row in rows:
         if row.kind != "knowledge":
             continue
         holder_id = row.payload.get("entity_id")
         other_id = row.pair_b_id if holder_id == row.pair_a_id else row.pair_a_id
-        expected = f"npc:{other_id}"
-        if row.payload.get("subject") != expected:
+        about = row.payload.get("subject_entity_ids")
+        if about != [other_id]:
             findings.append(_flag(
                 "staged", row.id,
-                f"knowledge subject {row.payload.get('subject')!r} does not match expected {expected!r}",
+                f"knowledge row about {about!r} does not match expected {[other_id]!r}",
             ))
     return findings
 
@@ -604,7 +611,7 @@ def _mechanical_findings(db: Session, batch: LinkBatch) -> list[dict]:
         _duplicate_pair_findings(rows)
         + _stale_relation_findings(db, rows)
         + _vocab_findings(rows)
-        + _subject_stamp_findings(rows)
+        + _about_stamp_findings(rows)
     )
 
 
@@ -622,7 +629,7 @@ def _coerce_patch_value(domain: str, field: str, value):
     'canon_knowledge') — staged relation payloads name the intensity field
     'value' (write_relation's kwarg); canon patches name it 'intensity'
     (the schema column / creator-facing whitelist). Identity fields (ids,
-    mode, subject, session bookkeeping) are NEVER patchable, on either
+    mode, participant stamp, session bookkeeping) are NEVER patchable, on either
     side — "ids and subjects are NEVER patchable" applies structurally,
     not just to the canon whitelist that states it explicitly.
     Returns (ok, reason, coerced_value)."""
diff --git a/src/world_engine/link_context.py b/src/world_engine/link_context.py
index 47e208e..450ccf0 100644
--- a/src/world_engine/link_context.py
+++ b/src/world_engine/link_context.py
@@ -19,7 +19,7 @@ import json
 from sqlmodel import Session, select
 
 from .context import RELATION_GRAPH_EXCLUDED_TYPES
-from .models import Entity, Knowledge, LinkBatch, LinkBatchRow, PromptTemplate, Relation
+from .models import Entity, FactParticipant, Knowledge, LinkBatch, LinkBatchRow, PromptTemplate, Relation
 from .prompt_store import current_prompt
 from .prose_render import knowledge_texts
 
@@ -62,11 +62,12 @@ def _canon_entries(db: Session, batch: LinkBatch) -> list[tuple[int, str, str, d
     """(touch_priority, kind, id, row) for every candidate canon row —
     relations between active characters of the world (structural exclusion,
     RECON-0036 E1-tout-le-graphe) plus knowledge rows touching the batch
-    roster (subject npc:{id} OR entity_id in the roster, RECON-0036 s.8/D3).
+    roster (a fact whose participant is in the roster OR entity_id in the
+    roster, RECON-0036 s.8/D3; TICKET-0097, G1: aboutness is the fact's
+    participants, never a `npc:{id}` subject).
     touch_priority = how many endpoints are in the batch's NPC roster —
     higher sorts first (RECON-0036 R-1: "rows touching batch NPCs first")."""
     npc_ids = set(batch.scope.get("npc_ids", []))
-    npc_subjects = {f"npc:{i}" for i in npc_ids}
 
     active_ids = set(
         db.exec(
@@ -86,9 +87,10 @@ def _canon_entries(db: Session, batch: LinkBatch) -> list[tuple[int, str, str, d
             Relation.entity_b_id.in_(active_ids),
         )
     ).all()
+    about = _participants_by_fact(db, npc_ids)
     know_rows = db.exec(
         select(Knowledge).where(
-            (Knowledge.subject.in_(npc_subjects)) | (Knowledge.entity_id.in_(npc_ids))
+            (Knowledge.fact_id.in_(about)) | (Knowledge.entity_id.in_(npc_ids))
         )
     ).all()
 
@@ -103,11 +105,12 @@ def _canon_entries(db: Session, batch: LinkBatch) -> list[tuple[int, str, str, d
             "visible_to_b": r.visible_to_b, "notes": r.notes,
         }))
     for k, text in zip(know_rows, knowledge_texts(db, know_rows)):
-        touch = (k.entity_id in npc_ids) + (k.subject in npc_subjects)
+        about_ids = about.get(k.fact_id, [])
+        touch = (k.entity_id in npc_ids) + bool(set(about_ids) & npc_ids)
         entries.append((touch, "knowledge", k.id, {
             "kind": "knowledge", "id": k.id,
             "entity_id": k.entity_id, "entity_name": _entity_name(db, k.entity_id),
-            "subject": k.subject, "level": k.level, "content": text,
+            "about_entity_ids": about_ids, "level": k.level, "content": text,
             "source": k.source, "is_incorrect": k.is_incorrect,
             "is_secret": k.is_secret, "share_threshold": k.share_threshold,
         }))
@@ -116,6 +119,22 @@ def _canon_entries(db: Session, batch: LinkBatch) -> list[tuple[int, str, str, d
     return entries
 
 
+def _participants_by_fact(db: Session, npc_ids: set[str]) -> dict[str, list[str]]:
+    """fact id -> its sorted participant ids, for every fact one of
+    `npc_ids` participates in."""
+    fact_ids = set(db.exec(
+        select(FactParticipant.fact_id).where(FactParticipant.entity_id.in_(npc_ids))
+    ).all()) if npc_ids else set()
+    about: dict[str, list[str]] = {fact_id: [] for fact_id in fact_ids}
+    for fact_id, entity_id in db.exec(
+        select(FactParticipant.fact_id, FactParticipant.entity_id)
+        .where(FactParticipant.fact_id.in_(fact_ids))
+        .order_by(FactParticipant.entity_id)
+    ).all():
+        about[fact_id].append(entity_id)
+    return about
+
+
 def serialize_canon_graph(db: Session, batch: LinkBatch) -> tuple[str, bool]:
     """Returns (json_text, truncated). Rows are added in priority order
     until the next row would push the blob past CANON_SERIAL_BUDGET
diff --git a/src/world_engine/lore_render.py b/src/world_engine/lore_render.py
index fc760a2..92fe5e4 100644
--- a/src/world_engine/lore_render.py
+++ b/src/world_engine/lore_render.py
@@ -59,7 +59,7 @@ def _format_relations(row: dict) -> str:
 
 def _format_knowledge(row: dict) -> str:
     suffix = " (croyance fausse)" if row.get("is_incorrect") else ""
-    return f"{row.get('subject')} — {row.get('level')} : {row.get('content')}{suffix}"
+    return f"{row.get('fact')} — {row.get('level')} : {row.get('content')}{suffix}"
 
 
 def _format_memberships(row: dict) -> str:
diff --git a/src/world_engine/lore_selectors.py b/src/world_engine/lore_selectors.py
index 7360af3..c674ee8 100644
--- a/src/world_engine/lore_selectors.py
+++ b/src/world_engine/lore_selectors.py
@@ -18,8 +18,8 @@ from sqlmodel import Session, func, select
 from .context import read_public_memberships
 from .facet_reads import creator_only_fact_ids, facts_of, joined
 from .facets import DESCRIPTIVE_FACETS, FACETS
-from .models import Character, Entity, FactParticipant, Faction, Knowledge, NpcGoal, Relation
-from .prose_render import knowledge_texts
+from .models import Character, Entity, Fact, FactParticipant, Faction, Knowledge, NpcGoal, Relation
+from .prose_render import fact_texts, knowledge_texts
 from .writes.knowledge import knowledge_level_rank
 
 
@@ -176,17 +176,18 @@ def _knowledge_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
             Entity.world_id == world_id,
         )
     ).all()
+    facts = fact_texts(db, [db.get(Fact, k.fact_id) for k in rows])
     return [
         {
             "section": "knowledge",
-            "subject": k.subject,
+            "fact": fact,
             "level": k.level,
             "content": text,
             "source": k.source,
             "is_incorrect": k.is_incorrect,
             "is_secret": k.is_secret,
         }
-        for k, text in zip(rows, knowledge_texts(db, rows))
+        for k, text, fact in zip(rows, knowledge_texts(db, rows), facts)
     ]
 
 
diff --git a/src/world_engine/scene_format.py b/src/world_engine/scene_format.py
index 6261e03..2a68032 100644
--- a/src/world_engine/scene_format.py
+++ b/src/world_engine/scene_format.py
@@ -21,12 +21,15 @@ def active_signposts(db: Session, location_id: str, player_character_id: str) ->
     Runs BEFORE any assembler, never through `assemble_mj_context`: this is
     the I3 code-predicate doctrine — the exhaustion judgment is a code
     predicate, never a prompt instruction. Returns ONLY ambient `content`
-    prose; no `subject` or `signpost_group` value ever leaves this function.
+    prose; no `signpost_group` value ever leaves this function.
 
     - Ungrouped ambient rows (`signpost_group IS NULL`) are always active.
     - Grouped ambient rows are silent iff the player holds a `knowledge` row
-      (any level — existence only) for EVERY `hidden` row sharing that
-      `signpost_group` (E1: silent only when the whole cluster is known).
+      (any level — existence only) on the fact of EVERY `hidden` row sharing
+      that `signpost_group` (E1: silent only when the whole cluster is
+      known). A hidden row's fact is `discoverable_detail.fact_id`, set by
+      its first approved discovery (TICKET-0097, H1); a row without one is
+      not known yet.
 
     `discovered` is NOT a filter here — ambient panels are not "discovered";
     their visibility is governed by the cluster predicate above.
@@ -41,7 +44,7 @@ def active_signposts(db: Session, location_id: str, player_character_id: str) ->
         return []
 
     groups_needed = {row.signpost_group for row in ambient_rows if row.signpost_group}
-    cluster_subjects: dict[str, list[str]] = {}
+    cluster_facts: dict[str, list[str | None]] = {}
     if groups_needed:
         hidden_rows = db.exec(
             select(DiscoverableDetail).where(
@@ -51,16 +54,16 @@ def active_signposts(db: Session, location_id: str, player_character_id: str) ->
             )
         ).all()
         for row in hidden_rows:
-            cluster_subjects.setdefault(row.signpost_group, []).append(row.subject)
+            cluster_facts.setdefault(row.signpost_group, []).append(row.fact_id)
 
-    all_subjects = {s for subs in cluster_subjects.values() for s in subs}
-    known_subjects: set[str] = set()
-    if all_subjects:
-        known_subjects = set(
+    all_facts = {f for facts in cluster_facts.values() for f in facts if f}
+    known_facts: set[str] = set()
+    if all_facts:
+        known_facts = set(
             db.exec(
-                select(Knowledge.subject).where(
+                select(Knowledge.fact_id).where(
                     Knowledge.entity_id == player_character_id,
-                    Knowledge.subject.in_(all_subjects),
+                    Knowledge.fact_id.in_(all_facts),
                 )
             ).all()
         )
@@ -70,8 +73,8 @@ def active_signposts(db: Session, location_id: str, player_character_id: str) ->
         if not row.signpost_group:
             active.append(row.content)
             continue
-        subjects = cluster_subjects.get(row.signpost_group, [])
-        if subjects and all(s in known_subjects for s in subjects):
+        facts = cluster_facts.get(row.signpost_group, [])
+        if facts and all(f in known_facts for f in facts):
             continue  # E1: whole cluster known — silent
         active.append(row.content)
     return active
diff --git a/src/world_engine/writes/facets.py b/src/world_engine/writes/facets.py
index bbf1426..9c16956 100644
--- a/src/world_engine/writes/facets.py
+++ b/src/world_engine/writes/facets.py
@@ -184,7 +184,7 @@ def _write_creator_meta(
         scope=ScopeChoice("none"), mentions=mentions,
     )
     write_knowledge(
-        db, entity_id=entity_id, fact_id=fact.id, subject=CREATOR_META_KEY,
+        db, entity_id=entity_id, fact_id=fact.id,
         level="unaware", is_secret=True, changed_by=created_by,
     )
     return [fact]
diff --git a/src/world_engine/writes/relations.py b/src/world_engine/writes/relations.py
index ae50819..ea2834d 100644
--- a/src/world_engine/writes/relations.py
+++ b/src/world_engine/writes/relations.py
@@ -60,7 +60,7 @@ from sqlmodel import Session, select
 
 from ..encounters import record_encounter
 from ..models import Entity, Fact, Knowledge, Relation
-from ..prose_render import entity_token, render
+from ..prose_render import entity_token
 from ..relation_orientation import (
     connects_to_fact_content,
     is_social,
@@ -381,7 +381,7 @@ def set_target_knows(db: Session, *, rel: Relation, knows: bool, changed_by: str
         return existing
     return write_knowledge(
         db, mode="update", entity_id=rel.entity_b_id, fact_id=lien.id,
-        subject=render(db, lien.content_raw), content=lien.content_raw, level="knows",
+        content=lien.content_raw, level="knows",
         source=f"relation {rel.id}", is_secret=False, is_incorrect=False,
         share_threshold=50, changed_by=changed_by,
     )
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index ebe2cc3..76643ec 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17141,6 +17141,37 @@ carries its participants. Journée shows `fact`.
 **Prompt.** `pt-day-plan`'s requirement line asks for the code of a fact
 from the appended list (`apply_ticket_0097_fact_code_prompts.py`).
 
+## PLAY READERS KNOW FACTS, NOT SUBJECTS (TICKET-0097) -- CONTEXTS, LORE, LINK AGENT, SIGNPOSTS (BRIEF-0097-e, no schema change)
+
+**A label is the fact's text.** Where a reader showed a row's `subject`
+because the row had no text of its own -- the NPC context, the MJ
+context's player knowledge, the tick briefing -- it shows the fact's
+rendered text. The Lore dossier's knowledge row and the link agent's canon
+graph carry `fact` / `about_entity_ids` instead of `subject`. The MJ
+snapshot key is `fact`; a snapshot taken before 0097 still shows its
+content, which every row but a legacy empty one has.
+
+**G1 -- the link agent's aboutness is a participant.** A staged knowledge
+row stamps `subject_entity_ids = [other side]` (the one construction site,
+D3, `link_agent_strata.py` rule 3 retargeted); `write_knowledge` attaches
+it to the row's new fact. `_shared_knowledge_lines` reads what the holder
+knows on any fact the other side participates in -- a little more than the
+old `npc:<id>` rows, which is the point: what a character knows about
+someone is everything about them, not one bucket. The coherence stamp check
+becomes `_about_stamp_findings`; duplicate detection keys on holder and
+stamp.
+
+**Writers stop naming a subject.** The lien knowledge of an oriented
+relation, the creator note (`creator_meta` is identified by its
+`unaware` + `is_secret` row, never by a label -- `fact_facets.py` R5 no
+longer asserts one), and the resolver's derived default rows pass no
+`subject`; until v2.10 drops the column, `write_knowledge` fills it from
+the fact.
+
+**H1, read half.** `active_signposts` silences a cluster once the player
+holds a row on the fact of every hidden detail in it; a detail no approved
+discovery has linked to a fact is, by construction, not known yet.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_facets.py b/tooling/verify/checks/fact_facets.py
index 8835dc9..3ed6e50 100644
--- a/tooling/verify/checks/fact_facets.py
+++ b/tooling/verify/checks/fact_facets.py
@@ -293,8 +293,7 @@ def check_entity_facets_writer(engine) -> None:
             fail(f"R5: write_entity_facets created {[f.facet for f in facts]!r}")
         else:
             rows = session.exec(select(Knowledge).where(Knowledge.fact_id == meta[0].id)).all()
-            if [(k.entity_id, k.level, k.is_secret, k.subject) for k in rows] != [
-                    (npc.id, "unaware", True, "creator_meta")]:
+            if [(k.entity_id, k.level, k.is_secret) for k in rows] != [(npc.id, "unaware", True)]:
                 fail("R5: creator_meta is not one unaware, secret knowledge row of its own entity")
             if session.exec(select(FactDefault).where(FactDefault.fact_id == meta[0].id)).first():
                 fail("R5: creator_meta fact carries a default")
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index d29ed6d..ed7b31c 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -61,6 +61,15 @@ K6 -- day gates name facts (D1'a, C-06):
    c. `_eval_knowledge` judges by fact id and carries the fact's text as
       `required_label`, which `requirement_detail_fr` shows instead of the id;
    d. a blocked step's lead is a `new_knowledge` on the gate's fact.
+K7 -- aboutness is the fact's participants (G1, H1):
+   a. a staged link-agent knowledge row stamps `subject_entity_ids =
+      [other side]`; committed, its new fact carries that participant;
+   b. `_shared_knowledge_lines` shows what the holder knows on facts the
+      other side participates in, and nothing about a third party;
+   c. the link canon graph lists a roster-touching knowledge row with its
+      fact's `about_entity_ids`;
+   d. a signpost cluster is silent once the player knows the fact of every
+      hidden detail in it, and speaks while one detail has no fact yet.
 
 Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB.
@@ -90,19 +99,10 @@ _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/cockpit/play_discovery.py": 3,
     "src/world_engine/cockpit/routes/creator.py": 2,
     "src/world_engine/cockpit/routes/npc_agent.py": 2,
-    "src/world_engine/context.py": 4,
     "src/world_engine/entity_author.py": 4,
-    "src/world_engine/knowledge_resolve.py": 1,
-    "src/world_engine/link_author.py": 5,
-    "src/world_engine/link_context.py": 4,
-    "src/world_engine/lore_render.py": 1,
-    "src/world_engine/lore_selectors.py": 2,
     "src/world_engine/models/canon_knowledge.py": 1,
-    "src/world_engine/scene_format.py": 3,
     "src/world_engine/subject_resolve.py": 4,
-    "src/world_engine/writes/facets.py": 1,
     "src/world_engine/writes/knowledge.py": 8,
-    "src/world_engine/writes/relations.py": 1,
 }
 
 A = "11111111-1111-1111-1111-111111111111"
@@ -637,6 +637,76 @@ def rule_k6(engine) -> None:
         session.rollback()
 
 
+def _k7_link(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.link_author import _build_knowledge_row, _shared_knowledge_lines, commit_batch
+    from world_engine.link_context import _canon_entries
+    from world_engine.models import FactParticipant, Knowledge, LinkBatch
+    from world_engine.writes import write_knowledge
+
+    batch = LinkBatch(world_id=ids["w"], scope={"npc_ids": [ids["ana"], ids["bel"]]},
+                      coherence_status="complete")
+    session.add(batch)
+    session.flush()
+    row = _build_knowledge_row(batch, ids["ana"], ids["bel"], {
+        "holder": "a", "level": "knows", "content": "Bel ment souvent.", "share_threshold": 50})
+    if row.payload.get("subject_entity_ids") != [ids["bel"]] or "subject" in row.payload:
+        fail(f"K7a staged payload is {row.payload!r}")
+    session.add(row)
+    session.flush()
+    commit_batch(session, batch)
+    known = session.exec(select(Knowledge).where(Knowledge.entity_id == ids["ana"])).all()
+    about = {p.entity_id for k in known for p in session.exec(
+        select(FactParticipant).where(FactParticipant.fact_id == k.fact_id)).all()}
+    if about != {ids["bel"]}:
+        fail(f"K7a the committed fact's participants are {about!r}")
+    write_knowledge(session, entity_id=ids["ana"], content="Le marché ouvre.", level="knows")
+    lines = _shared_knowledge_lines(session, ids["ana"], ids["bel"], "Ana")
+    if len(lines) != 1 or "Bel ment souvent." not in lines[0]:
+        fail(f"K7b shared knowledge lines are {lines!r}")
+    rows = [entry[3] for entry in _canon_entries(session, batch) if entry[1] == "knowledge"]
+    abouts = sorted(tuple(r["about_entity_ids"]) for r in rows)
+    if (ids["bel"],) not in abouts or any("subject" in r for r in rows):
+        fail(f"K7c canon graph knowledge rows are {rows!r}")
+
+
+def _k7_signposts(session, ids) -> None:
+    from world_engine.models import DiscoverableDetail
+    from world_engine.scene_format import active_signposts
+    from world_engine.writes import write_knowledge
+
+    for key, level in (("panel", "ambient"), ("h1", "hidden"), ("h2", "hidden")):
+        detail = DiscoverableDetail(world_id=ids["w"], location_id=ids["loc"], subject=key,
+                                    content=f"Texte {key}.", access_level=level, signpost_group="g")
+        session.add(detail)
+        session.flush()
+        ids[key] = detail
+    h1_fact = write_knowledge(session, entity_id=ids["bel"], content="Texte h1.", level="knows").fact_id
+    write_knowledge(session, entity_id=ids["ana"], fact_id=h1_fact, content="x", level="rumor")
+    session.flush()
+    ids["h1"].fact_id = h1_fact
+    session.flush()
+    if active_signposts(session, ids["loc"], ids["ana"]) != ["Texte panel."]:
+        fail("K7d the cluster fell silent while a detail had no fact")
+    h2_fact = write_knowledge(session, entity_id=ids["ana"], content="Texte h2.", level="rumor").fact_id
+    session.flush()
+    ids["h2"].fact_id = h2_fact
+    session.flush()
+    if active_signposts(session, ids["loc"], ids["ana"]) != []:
+        fail("K7d the cluster still speaks although every hidden fact is known")
+
+
+def rule_k7(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _k4_world(session)
+        _k7_link(session, ids)
+        _k7_signposts(session, ids)
+        session.rollback()
+
+
 def rule_k4(engine) -> None:
     from sqlmodel import Session
 
@@ -688,6 +758,7 @@ def main() -> int:
     rule_k4(engine)
     rule_k5(engine)
     rule_k6(engine)
+    rule_k7(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
diff --git a/tooling/verify/checks/link_agent_strata.py b/tooling/verify/checks/link_agent_strata.py
index 82932b0..88ca8b0 100644
--- a/tooling/verify/checks/link_agent_strata.py
+++ b/tooling/verify/checks/link_agent_strata.py
@@ -14,11 +14,12 @@ Four structural guarantees, all fail-closed:
      `link_context.py` (BRIEF-0036-c's serializers), `models/ephemeral.py`
      (definition), `models/__init__.py` (package re-export surface, same
      as every other model), and `cockpit/app.py` (the retention purge).
-  3. D3 (BRIEF-0036-b): every staged knowledge payload's "subject" key is
-     built in exactly ONE function in `link_author.py`, as a code-stamped
-     f-string carrying the `npc:` literal prefix — never a passthrough of
-     the model's own `item.get(...)` output. The model proposes a
-     "holder"; code alone derives "subject".
+  3. D3 (BRIEF-0036-b; retargeted TICKET-0097, BRIEF-0097-e, G1): every
+     staged knowledge payload's "subject_entity_ids" key is built in exactly
+     ONE function in `link_author.py`, as a one-element list of a bare name
+     (the pair's other side) — never a passthrough of the model's own
+     `item.get(...)` output. The model proposes a "holder"; code alone
+     derives who the row is about.
   4. BRIEF-0036-c: `cockpit/routes/link_agent.py` and `link_author.py`
      contain no direct `db.add(Relation(...))` / `db.add(Knowledge(...))`
      and no raw SQL INSERT/UPDATE touching `relation`/`knowledge` — the
@@ -152,8 +153,8 @@ def _check_reference_scope() -> bool:
 
 
 class _SubjectKeyVisitor(ast.NodeVisitor):
-    """Finds every dict literal `"subject": <value>` and tags it with its
-    innermost enclosing function name."""
+    """Finds every dict literal `"subject_entity_ids": <value>` and tags it
+    with its innermost enclosing function name."""
 
     def __init__(self) -> None:
         self.func_stack: list[str] = []
@@ -166,18 +167,18 @@ class _SubjectKeyVisitor(ast.NodeVisitor):
 
     def visit_Dict(self, node: ast.Dict) -> None:
         for key, value in zip(node.keys, node.values):
-            if isinstance(key, ast.Constant) and key.value == "subject":
+            if isinstance(key, ast.Constant) and key.value == "subject_entity_ids":
                 fname = self.func_stack[-1] if self.func_stack else "<module>"
                 self.hits.append((fname, value))
         self.generic_visit(node)
 
 
 def _check_knowledge_subject_stamp() -> None:
-    """D3: the "subject" key of a staged knowledge payload must be built in
-    exactly one function, as an f-string carrying the `npc:` stamp — never
-    a passthrough of the model's own `item.get(...)` output."""
+    """D3: the "subject_entity_ids" key of a staged knowledge payload must be
+    built in exactly one function, as `[<name>]` — never a passthrough of the
+    model's own `item.get(...)` output."""
     if not LINK_AUTHOR_FILE.exists():
-        fail(f"{LINK_AUTHOR_FILE} not found — D3 subject stamp cannot be verified")
+        fail(f"{LINK_AUTHOR_FILE} not found — D3 participant stamp cannot be verified")
         return
 
     tree = ast.parse(LINK_AUTHOR_FILE.read_text(encoding="utf-8"), filename=str(LINK_AUTHOR_FILE))
@@ -185,23 +186,22 @@ def _check_knowledge_subject_stamp() -> None:
     visitor.visit(tree)
 
     if not visitor.hits:
-        fail(f"{LINK_AUTHOR_FILE}: no 'subject' key construction found for a knowledge payload — vacuous proof, not a pass")
+        fail(f"{LINK_AUTHOR_FILE}: no 'subject_entity_ids' key construction found for a knowledge payload — vacuous proof, not a pass")
         return
 
     functions = {fname for fname, _ in visitor.hits}
     if len(functions) != 1:
         fail(
-            f"{LINK_AUTHOR_FILE}: 'subject' key constructed in multiple functions "
+            f"{LINK_AUTHOR_FILE}: 'subject_entity_ids' key constructed in multiple functions "
             f"{sorted(functions)} — D3 stamp must be a single chokepoint"
         )
 
     for fname, value_node in visitor.hits:
-        if not isinstance(value_node, ast.JoinedStr):
-            fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject' value is not an f-string — D3 stamp must be code-derived")
+        if not (isinstance(value_node, ast.List) and len(value_node.elts) == 1
+                and isinstance(value_node.elts[0], ast.Name)):
+            fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject_entity_ids' value is not "
+                 "a one-element list of a name — D3 stamp must be code-derived")
             continue
-        literal_parts = [v.value for v in value_node.values if isinstance(v, ast.Constant)]
-        if not any(part.startswith("npc:") for part in literal_parts):
-            fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject' f-string does not carry the 'npc:' stamp literal")
         for sub in ast.walk(value_node):
             if (
                 isinstance(sub, ast.Call)
@@ -210,7 +210,7 @@ def _check_knowledge_subject_stamp() -> None:
                 and isinstance(sub.func.value, ast.Name)
                 and sub.func.value.id == "item"
             ):
-                fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject' reads item.get(...) — the model must never supply the subject")
+                fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject_entity_ids' reads item.get(...) — the model must never supply it")
 
 
 class _DirectWriteVisitor(ast.NodeVisitor):
```

## Scope OUT

- The creator surface (F).
- The Lore consultation pipeline beyond the dossier's knowledge row.
- Grouping « connaît X » under one fact (G2, rejected).
- Every later brief of the lot: BRIEF-0097-F, BRIEF-0097-G.

## Invariants to defend

**The MJ context assembler is scoped to the player's perception** — only the label of the player's own rows changes. **Secrets are structurally excluded** — `creator_meta` stays identified by its `unaware` + `is_secret` row; R5 still checks that. The link agent's secret exception (RECON-0036 R-4) is unchanged. **`discoverable_detail` is excluded from every assembler** — `active_signposts` stays a pure predicate.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/link_agent_strata.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_facets.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

Decision entry `PLAY READERS KNOW FACTS, NOT SUBJECTS … (BRIEF-0097-e, no schema change)`.
