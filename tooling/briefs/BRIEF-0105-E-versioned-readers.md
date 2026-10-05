<!-- slug: versioned-readers -->
# BRIEF 0105-E — "Every knower reader gives the version known; the scene shows the outfit"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: BRIEF-0105-D
Commit header for decisions: `(BRIEF-0105-e, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/knowledge_resolve.py` defines `Known`, `resolve_known_for_entity` and `resolve_default_rows`, the latter building rows with `content_raw=fact.content_raw` (D left it unchanged).
- `src/world_engine/facet_reads.py:108` → `def known_facts_of(`; `:122` → `    known = resolve_levels_for_entity(db, perceiver_id)`.
- `src/world_engine/day_choice.py:77` → `def _candidates(ids: list[str], known: dict[str, str], db: Session) -> tuple[Candidate, ...]:`; `:100` → `    known = resolve_levels_for_entity(db, character.id)`.
- `src/world_engine/context.py:125` → `def _row_fact_texts(session: Session, rows: list[Knowledge]) -> list[str]:`; `:843` → `            + (f" {c['physique']}" if c.get("physique") else "")`.
- `src/world_engine/tick_context.py:281` → `def _tick_knowledge_block(npc_id: str, session: Session) -> str:`; `:286` → `    facts = fact_texts(session, [session.get(Fact, k.fact_id) for k in knowledge])`.
- `src/world_engine/context_describe.py:55` → `def _npc_context_company(`; `:79` → `            facets=("physique", "description"),`; `:92` → `def _mj_context_co_presents(`.
- `src/world_engine/prose_render.py` defines `fact_texts_at` (C).

## Facts carried

### R-08 — who reads a fact as someone knows it [M]
Opened: enumeration E4; `src/world_engine/facet_reads.py:108-123`
(`known_facts_of`); `src/world_engine/day_choice.py:77-101`;
`src/world_engine/context.py:125-137` (`_row_fact_texts`,
`_knowledge_line`), `:352-380`, `:680-697`;
`src/world_engine/tick_context.py:262-290`;
`src/world_engine/context_describe.py:55-127`.
Finding: the text of a fact reaches a holder through: default rows
(`resolve_default_rows`), `known_facts_of` (self identity, co-present
physique), day-choice evidence (`facts_of` filtered by the known ids), and
the fallback label of a stored row with no text of its own (NPC speak
block, MJ player knowledge, tick briefing). `day_concordance` and
`tick_context._reachable_locations` read ids and levels only.
Consequence: E versions exactly these; the id/level readers need nothing.

### R-09 — a stored row's own text [M]
Opened: `src/world_engine/models/canon_knowledge.py:199-239` (`Knowledge`:
nullable `content`, `updated_at`); `src/world_engine/lore_write_apply.py:
252-264` (Lore knowers are written without text);
`src/world_engine/prose_render.py:62-77`.
Finding: a row with its own text renders it; a row without falls back to
its fact's text.
Consequence: only the fallback is versioned; a row's own text is the
holder's version and is never rewritten.

### R-11 — the outfit has no play reader [M]
Opened: enumeration E5; `src/world_engine/context_describe.py:55-127`
(`_npc_context_company`: `physique`, `description`;
`_mj_context_co_presents`: `description`, `physique`);
`src/world_engine/context.py:839-846` (MJ co-present line).
Finding: `tenue` is read nowhere outside the registry and the creator
editors.
Consequence: E adds it to both scene descriptions (V1).

### R-16 — where raw fact text may be read [M]
Opened: `tooling/verify/checks/identity_tokens.py:7-14, 56-63` (R1:
`content_raw` only in `models/canon_knowledge.py`, `writes/*.py`,
`prose_render.py`, `knowledge_resolve.py`, migrations).
Consequence: `fact_versions.py` takes the history and the current text as
arguments; `prose_render.fact_texts_at` / `fact_is_stale` pass them.

## Contracts

### C-05 — the version known
Produced by: BRIEF-0105-C   Consumed by: BRIEF-0105-D, E, G
`fact_versions.utc(value) -> datetime` (naive = UTC).
`fact_versions.version_text(history, current, as_of) -> str`: `as_of` None
→ `current`; else the `content` of the first `changement` entry whose `at`
is after `as_of`, else `current`. Pure.
`prose_render.fact_texts_at(db, pairs: list[(Fact, as_of)]) -> list[str]`
(rendered, one entity query); `prose_render.fact_is_stale(fact, as_of) ->
bool`.

### C-06 — resolution dated by contact
Produced by: BRIEF-0105-D   Consumed by: BRIEF-0105-E, G
`knowledge_resolve.Known(level: str, as_of: Optional[datetime])` (frozen).
`resolve_knowledge(db, entity_id, fact_id) -> Known` (total; unknown fact →
`Known("unaware", None)`); `resolve_known_for_entity(db, entity_id) ->
dict[fact_id, Known]` (above `unaware` only); `resolve_knowledge_level` and
`resolve_levels_for_entity` keep their signatures and return levels.
Rules: tiers 1-7 as in the module docstring; tiers 3-5 need a contact with
the scope at or after the default's `created_at` (rencontre: met; location:
the place or a place inside it; faction: membership open, or closed after);
contact right now: the current place and its ancestors, schedule places and
their ancestors, an entity at the same current place, an entity sharing a
schedule slot, an active membership; highest level per tier. `as_of`:
`None` for a fact with a `world` default, for tier 2, tiers 6-7; otherwise
the latest contact with any anchor (participants, non-world scope ids) and,
for a stored row, its `updated_at` if later.
Error and empty cases: unknown entity → `{}` from the batch.

### C-07 — the knower readers (family contract)
Produced by: BRIEF-0105-E   Consumed by: Play, ticks, day choice
A reader that shows a fact as one holder knows it renders
`version_text(...)` at that holder's `as_of` (C-06): `resolve_default_rows`
(rows' `content_raw`), `facet_reads.known_facts_of` (through
`facet_reads.versioned(db, rows, known) -> list[FactRow]`), day choice
evidence (`versioned`), and the fallback label of a stored row with no text
(`facet_reads.known_fact_texts(db, perceiver_id, facts) -> list[str]`, used
by `context._row_fact_texts` and `tick_context._tick_knowledge_block`). A
row with its own text is never rewritten. The scene's co-present lines
carry the known `tenue` (NPC context: with the physique; MJ context: key
`tenue`, `None` when blindfolded).
Members, re-read after the last: the five readers above, and BRIEF-0105-G's
dossier rows, which apply the same `as_of` to mark rather than replace.

## Context

Resolution now says when each holder last saw a fact as it is (D). This brief makes every reader that shows a fact as someone knows it render that version (C-07): the default rows of the NPC, MJ and tick contexts, `known_facts_of`, the day-choice evidence, and the fallback label of a stored row with no text of its own. It also puts the outfit in the scene (V1). Readers that speak for the creator or for no one keep the current text.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `knowledge_resolve.resolve_default_rows` iterates `resolve_known_for_entity` and builds each row's `content_raw` with `version_text` at its `as_of`;
   - `facet_reads.py`: `known_facts_of` uses `resolve_known_for_entity` and returns `versioned(...)`; new `versioned(db, rows, known)` and `known_fact_texts(db, perceiver_id, facts)` (C-07); docstring;
   - `day_choice.py`: `known` is `resolve_known_for_entity(...)`; `_candidates` versions its rows with `versioned`; docstring;
   - `context._row_fact_texts` and `tick_context._tick_knowledge_block` call `known_fact_texts` (the rows of one call belong to one holder); `fact_texts` imports removed where unused;
   - `context_describe._npc_context_company` reads `physique`, `tenue`, `description` and shows physique and outfit together; `_mj_context_co_presents` adds a `tenue` key (`None` when blindfolded); `context.py`'s MJ co-present line prints `Tenue : …` when present;
   - adds E1-E3 to `fact_learning.py`; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): knower readers give the version known; the outfit in the scene (BRIEF-0105-e)`.

````diff
diff --git a/src/world_engine/context.py b/src/world_engine/context.py
index 2085a98..265adf7 100644
--- a/src/world_engine/context.py
+++ b/src/world_engine/context.py
@@ -47,10 +47,10 @@ from .models import (
     SkillDefinition,
     World,
 )
-from .facet_reads import facts_of, joined, known_facts_of
+from .facet_reads import facts_of, joined, known_fact_texts, known_facts_of
 from .facets import FACETS
 from .knowledge_resolve import resolve_default_rows
-from .prose_render import fact_texts, knowledge_texts
+from .prose_render import knowledge_texts
 from .schedule_reads import where_is
 from .context_describe import (
     _mj_context_co_presents,
@@ -123,9 +123,12 @@ def _section(title: str, body: str) -> str:
 
 
 def _row_fact_texts(session: Session, rows: list[Knowledge]) -> list[str]:
-    """The rendered text of each row's fact, one entity query (TICKET-0097:
-    the fallback label of a row with no text of its own)."""
-    return fact_texts(session, [session.get(Fact, k.fact_id) for k in rows])
+    """The text of each row's fact as the row's holder knows it (TICKET-0097:
+    the fallback label of a row with no text of its own; TICKET-0105: the
+    version known). The rows of one call belong to one holder."""
+    if not rows:
+        return []
+    return known_fact_texts(session, rows[0].entity_id, [session.get(Fact, k.fact_id) for k in rows])
 
 
 def _knowledge_line(k: Knowledge, content: str | None, fact: str) -> str:
@@ -841,6 +844,7 @@ def format_mj_context(mj_context: dict) -> str:
         body = "\n".join(
             f"- {c['name']} : {c.get('description') or '(pas de description)'}"
             + (f" {c['physique']}" if c.get("physique") else "")
+            + (f" Tenue : {c['tenue']}" if c.get("tenue") else "")
             for c in co_presents
         )
         blocks.append(_section(H_MJ_PRESENT, body))
diff --git a/src/world_engine/context_describe.py b/src/world_engine/context_describe.py
index 353ae52..4f11bef 100644
--- a/src/world_engine/context_describe.py
+++ b/src/world_engine/context_describe.py
@@ -76,10 +76,11 @@ def _npc_context_company(
             continue
         seen = known_facts_of(
             session, perceiver_id=npc_id, entity_id=co_entity.id,
-            facets=("physique", "description"),
+            facets=("physique", "tenue", "description"),
         )
+        # What one sees of them: physique and outfit as known (TICKET-0105, V1).
         description = (
-            joined([row for row in seen if row.facet == "physique"], sep=" ")
+            joined([row for row in seen if row.facet in ("physique", "tenue")], sep=" ")
             or joined([row for row in seen if row.facet == "description"], sep=" ")
             or "(pas de description)"
         )
@@ -121,5 +122,10 @@ def _mj_context_co_presents(
                 db, perceiver_id=player_character_id, entity_id=co_entity.id,
                 facets=("physique",),
             ), sep=" "),
+            # Outfit as the player last saw it (TICKET-0105, V1).
+            "tenue": None if blindfolded else joined(known_facts_of(
+                db, perceiver_id=player_character_id, entity_id=co_entity.id,
+                facets=("tenue",),
+            ), sep=" "),
         })
     return co_presents
diff --git a/src/world_engine/day_choice.py b/src/world_engine/day_choice.py
index 9349195..57f178e 100644
--- a/src/world_engine/day_choice.py
+++ b/src/world_engine/day_choice.py
@@ -8,9 +8,10 @@ character's own name surfaces produced, and only when the judge accepts it.
 Every call is recorded (`writes.write_day_mention_choices`).
 
 Evidence is what the character knows about each candidate, read through
-`facet_reads.facts_of` (creator-only facts excluded by construction) and
-filtered by one `resolve_levels_for_entity` call. The gameplay model is
-abliterated: nothing the character does not know is ever assembled.
+`facet_reads.facts_of` (creator-only facts excluded by construction),
+filtered by one `resolve_known_for_entity` call and given in the version the
+character knows (`facet_reads.versioned`, TICKET-0105). The gameplay model
+is abliterated: nothing the character does not know is ever assembled.
 """
 
 from __future__ import annotations
@@ -23,9 +24,9 @@ from sqlmodel import Session, select
 from . import llm_parse, ollama_client
 from .day_concordance import ConcordanceResult, MatchedMention
 from .day_extract import Mention
-from .facet_reads import facts_of
+from .facet_reads import facts_of, versioned
 from .facets import FACETS
-from .knowledge_resolve import resolve_levels_for_entity
+from .knowledge_resolve import Known, resolve_known_for_entity
 from .lore_resolve import category_of_type, near_in_surfaces, normalize_surface, rung_named_partial
 from .models import Character, Entity, PromptTemplate
 from .name_index import NameScope, surfaces as name_surfaces
@@ -74,7 +75,7 @@ def _near_ids(mention: Mention, surfaces: tuple) -> list[str]:
     return ids[:MAX_CANDIDATES]
 
 
-def _candidates(ids: list[str], known: dict[str, str], db: Session) -> tuple[Candidate, ...]:
+def _candidates(ids: list[str], known: dict[str, Known], db: Session) -> tuple[Candidate, ...]:
     """C-05 step 3: evidence per candidate, known facts only."""
     out: list[Candidate] = []
     for entity_id in ids:
@@ -82,7 +83,7 @@ def _candidates(ids: list[str], known: dict[str, str], db: Session) -> tuple[Can
         if entity is None:
             continue
         rows = [r for r in facts_of(db, entity_id=entity_id, facets=tuple(FACETS)) if r.fact_id in known]
-        rows = rows[:MAX_FACTS_PER_CANDIDATE]
+        rows = versioned(db, rows[:MAX_FACTS_PER_CANDIDATE], known)
         out.append(Candidate(
             entity_id=entity_id, name=entity.name,
             facts=tuple(r.content for r in rows), fact_ids=tuple(r.fact_id for r in rows),
@@ -97,7 +98,7 @@ def choice_requests(result: ConcordanceResult, character: Character, db: Session
     near_mentions = [um.mention for um in result.unmatched if um.mention.kind == "named"]
     if not result.ambiguous and not near_mentions:
         return ()
-    known = resolve_levels_for_entity(db, character.id)
+    known = resolve_known_for_entity(db, character.id)
     requests: list[ChoiceRequest] = []
     for am in result.ambiguous:
         candidates = _candidates(list(am.candidate_ids), known, db)
diff --git a/src/world_engine/facet_reads.py b/src/world_engine/facet_reads.py
index 640ddf7..6187eef 100644
--- a/src/world_engine/facet_reads.py
+++ b/src/world_engine/facet_reads.py
@@ -5,7 +5,9 @@ said of an entity, facet by facet.
 R-06 — `role` never filters) whose facet is one of `facets`, in the order of
 `facets`, then `created_at`, then `fact_id`. `known_facts_of` narrows that
 list to the facts a perceiver resolves above `'unaware'`
-(`knowledge_resolve.resolve_levels_for_entity`, one batch call).
+(`knowledge_resolve.resolve_known_for_entity`, one batch call), each with
+the text the perceiver knows (TICKET-0105, BRIEF-0105-E: `versioned`).
+`known_fact_texts` gives that text for any list of facts.
 
 Creator-only facts (AMENDMENT-0091-01) are excluded by query construction:
 a fact is creator-only when a stored `knowledge` row on it belongs to one of
@@ -18,16 +20,16 @@ Resolution is a read: no function here ever calls `db.add`.
 
 from __future__ import annotations
 
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 from datetime import datetime
 from typing import Iterable, Optional
 
 from sqlmodel import Session, select
 
 from .facets import normalize_aspect
-from .knowledge_resolve import resolve_levels_for_entity
+from .knowledge_resolve import Known, resolve_known_for_entity
 from .models import Fact, FactDefault, FactParticipant, Knowledge
-from .prose_render import fact_texts
+from .prose_render import fact_texts, fact_texts_at
 
 
 @dataclass(frozen=True)
@@ -115,12 +117,35 @@ def known_facts_of(
 ) -> list[FactRow]:
     """`facts_of` (creator-only facts always excluded, no override), filtered
     to the facts `perceiver_id` resolves above `'unaware'` — one
-    `resolve_levels_for_entity` call, never one per fact."""
+    `resolve_known_for_entity` call, never one per fact — each with the text
+    the perceiver knows (`versioned`)."""
     rows = facts_of(db, entity_id=entity_id, facets=facets, aspect=aspect)
     if not rows:
         return []
-    known = resolve_levels_for_entity(db, perceiver_id)
-    return [row for row in rows if row.fact_id in known]
+    known = resolve_known_for_entity(db, perceiver_id)
+    return versioned(db, [row for row in rows if row.fact_id in known], known)
+
+
+def versioned(db: Session, rows: list[FactRow], known: dict[str, Known]) -> list[FactRow]:
+    """`rows` with each content replaced by the version known at its
+    `known[fact_id].as_of` (TICKET-0105); a row absent from `known` keeps the
+    current text. One fact query, one entity query."""
+    if not rows:
+        return []
+    facts = {f.id: f for f in db.exec(select(Fact).where(Fact.id.in_([r.fact_id for r in rows]))).all()}
+    texts = fact_texts_at(db, [
+        (facts[r.fact_id], known[r.fact_id].as_of if r.fact_id in known else None) for r in rows
+    ])
+    return [replace(row, content=text) for row, text in zip(rows, texts)]
+
+
+def known_fact_texts(db: Session, perceiver_id: str, facts: list[Fact]) -> list[str]:
+    """Each fact's text as `perceiver_id` knows it (TICKET-0105): the
+    fallback label of a stored knowledge row with no text of its own."""
+    if not facts:
+        return []
+    known = resolve_known_for_entity(db, perceiver_id)
+    return fact_texts_at(db, [(f, known[f.id].as_of if f.id in known else None) for f in facts])
 
 
 def joined(rows: list[FactRow], sep: str = "\n") -> Optional[str]:
diff --git a/src/world_engine/knowledge_resolve.py b/src/world_engine/knowledge_resolve.py
index ecbd1cf..a9fb588 100644
--- a/src/world_engine/knowledge_resolve.py
+++ b/src/world_engine/knowledge_resolve.py
@@ -60,7 +60,7 @@ from typing import Iterable, Optional
 
 from sqlmodel import Session, select
 
-from .fact_versions import utc
+from .fact_versions import utc, version_text
 from .facets import DESCRIPTIVE_FACETS
 from .models import (
     Character, Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, Location,
@@ -345,10 +345,11 @@ def resolve_default_rows(
     three readers already use for a stored row. A fact whose facet is in
     `DESCRIPTIVE_FACETS` is skipped: what is said of an entity is read
     through `facet_reads`, never as speakable knowledge, so the three
-    readers' knowledge section is unchanged (TICKET-0091, Q13a)."""
-    levels = resolve_levels_for_entity(db, entity_id)
+    readers' knowledge section is unchanged (TICKET-0091, Q13a). Each row's
+    text is the version of the fact the entity knows (TICKET-0105,
+    `fact_versions.version_text` at its `as_of`)."""
     rows: list[Knowledge] = []
-    for fact_id, level in levels.items():
+    for fact_id, known in resolve_known_for_entity(db, entity_id).items():
         if fact_id in exclude_fact_ids:
             continue
         fact = db.get(Fact, fact_id)
@@ -356,9 +357,9 @@ def resolve_default_rows(
             continue
         rows.append(
             Knowledge(
-                entity_id=entity_id, fact_id=fact_id,
-                level=level, content_raw=fact.content_raw, is_secret=False,
-                share_threshold=DEFAULT_SHARE_THRESHOLD,
+                entity_id=entity_id, fact_id=fact_id, level=known.level,
+                content_raw=version_text(fact.change_history, fact.content_raw, known.as_of),
+                is_secret=False, share_threshold=DEFAULT_SHARE_THRESHOLD,
             )
         )
     return rows
diff --git a/src/world_engine/tick_context.py b/src/world_engine/tick_context.py
index 6503f18..45cacd7 100644
--- a/src/world_engine/tick_context.py
+++ b/src/world_engine/tick_context.py
@@ -36,9 +36,9 @@ from .knowledge_resolve import (
     resolve_levels_for_entity,
     resolve_public_levels,
 )
-from .facet_reads import facts_of, joined
+from .facet_reads import facts_of, joined, known_fact_texts
 from .fact_refs import CodedFacts, code_facts
-from .prose_render import fact_texts, knowledge_texts
+from .prose_render import knowledge_texts
 from .ledger import get_balance
 from .models import (
     Agenda,
@@ -283,7 +283,7 @@ def _tick_knowledge_block(npc_id: str, session: Session) -> str:
     if not knowledge:
         return "(aucune connaissance)"
     codes = code_facts(session, [k.fact_id for k in knowledge])
-    facts = fact_texts(session, [session.get(Fact, k.fact_id) for k in knowledge])
+    facts = known_fact_texts(session, npc_id, [session.get(Fact, k.fact_id) for k in knowledge])
     return "\n".join(
         _knowledge_line(k, text, fact, codes.code_of(k.fact_id))
         for k, text, fact in zip(knowledge, knowledge_texts(session, knowledge), facts)
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 467f68e..a9127eb 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17818,6 +17818,27 @@ contacts the model of a collection does not rank. N2, only the anchor of
 the tier that gave the level: meeting the wearer would not refresh an
 outfit known through a place.
 
+
+## EVERY KNOWER READER GIVES THE VERSION KNOWN (TICKET-0105) -- AND THE SCENE SHOWS THE OUTFIT (BRIEF-0105-e, no schema change)
+
+**G1, N1.** The readers that show a fact as some entity knows it render the
+version known at that entity's `as_of`: the default rows of the NPC, MJ and
+tick contexts (`resolve_default_rows`), `facet_reads.known_facts_of` and
+its new `versioned`, the day-choice evidence, and the fallback label of a
+stored knowledge row with no text of its own (`facet_reads.
+known_fact_texts`, used by `context._row_fact_texts` and the tick
+briefing). A stored row with its own text is the holder's own version and
+is never rewritten. Readers that speak for the creator or for no one
+(`facts_of`, the authoring assistants, the dossier's facet rows) keep the
+current text.
+
+**V1.** The scene shows the outfit: a co-present NPC's line in the NPC
+context carries its known physique and outfit, and the MJ context's
+co-present entry gains a `tenue` key, known through the player's contact,
+absent when blindfolded. Being at the same place is a contact right now
+(O1), so the outfit shown in a scene is the current one; the versions
+matter for whoever is elsewhere.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
index 00f6631..880e039 100644
--- a/tooling/verify/checks/fact_learning.py
+++ b/tooling/verify/checks/fact_learning.py
@@ -78,6 +78,25 @@ D2 -- `as_of` (N1). A `tenue` of A with a rencontre default on A at t0, A
    version known is the old text; after a new encounter, the current one.
    A fact with a `world` default and one's own description -> `as_of` None.
 
+E1 -- the readers give the version known (BRIEF-0105-E, fixture). P passed
+   a place at t1 whose `information` default dates from t0, and met A at t1
+   whose `tenue` has a rencontre default from t0; both facts are then
+   rewritten as a `changement`. `resolve_default_rows(P)` carries the old
+   information text, `known_facts_of(P, A, ("tenue",))` and
+   `known_fact_texts(P, [tenue])` the old outfit; after a new encounter with
+   A, the new outfit.
+E2 -- every knower reader goes through the version (AST):
+   `knowledge_resolve.resolve_default_rows` calls `version_text`;
+   `facet_reads.known_facts_of` and `day_choice._candidates` call
+   `versioned`; `context._row_fact_texts` and
+   `tick_context._tick_knowledge_block` call `known_fact_texts`;
+   `context_describe._npc_context_company` and `_mj_context_co_presents`
+   name the `tenue` facet.
+E3 -- the outfit in the scene (V1, fixture). A public NPC wearing a `tenue`
+   with its rencontre default, in an open gathering with the player at the
+   same place: `_mj_context_co_presents` gives its `tenue` text; blindfolded,
+   `None`.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -653,6 +672,110 @@ def check_d2(engine) -> None:
                 fail(f"D2: a {label} fact is not always current")
 
 
+# --- E1-E3 ---------------------------------------------------------------------
+
+def check_e1(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.encounters import record_encounter
+    from world_engine.facet_reads import known_fact_texts, known_facts_of
+    from world_engine.knowledge_resolve import resolve_default_rows
+    from world_engine.models import Fact
+    from world_engine.passages import record_passage
+    from world_engine.writes.facts import update_fact_content
+
+    with Session(engine) as session:
+        ids = _d_world(session)
+        w = ids["world"]
+        record_passage(session, world_id=w, entity_id=ids["P"], location_id=ids["L"], at=ids["t1"])
+        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="visit", at=ids["t1"])
+        session.commit()
+        info = _d_fact(session, ids, "info-old", scopes=[("location", "L", "knows", "t0")])
+        tenue = _d_fact(session, ids, "tenue-old", facet="tenue", about="A",
+                        scopes=[("rencontre", "A", "knows", "t0")])
+        for fact_id, text in ((info, "D1 info-new"), (tenue, "D1 tenue-new")):
+            update_fact_content(session, fact=session.get(Fact, fact_id), content=text,
+                                changed_by="check", kind="changement")
+        session.commit()
+        rows = {k.fact_id: k.content_raw for k in resolve_default_rows(session, ids["P"], set())}
+        if rows.get(info) != "D1 info-old":
+            fail(f"E1: resolve_default_rows gives {rows.get(info)!r}")
+        seen = [r.content for r in known_facts_of(session, perceiver_id=ids["P"], entity_id=ids["A"],
+                                                   facets=("tenue",))]
+        label = known_fact_texts(session, ids["P"], [session.get(Fact, tenue)])
+        if seen != ["D1 tenue-old"] or label != ["D1 tenue-old"]:
+            fail(f"E1: the outfit known before a new encounter is {seen} / {label}")
+        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="conversation")
+        session.commit()
+        seen = [r.content for r in known_facts_of(session, perceiver_id=ids["P"], entity_id=ids["A"],
+                                                   facets=("tenue",))]
+        if seen != ["D1 tenue-new"]:
+            fail(f"E1: after a new encounter the outfit known is {seen}")
+
+
+_E2_CALLS = (
+    ("knowledge_resolve.py", "resolve_default_rows", "version_text"),
+    ("facet_reads.py", "known_facts_of", "versioned"),
+    ("day_choice.py", "_candidates", "versioned"),
+    ("context.py", "_row_fact_texts", "known_fact_texts"),
+    ("tick_context.py", "_tick_knowledge_block", "known_fact_texts"),
+)
+
+
+def check_e2() -> None:
+    import ast
+
+    for module, function, callee in _E2_CALLS:
+        tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
+        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == function), None)
+        if fn is None:
+            fail(f"E2: {module}::{function} is missing")
+            continue
+        names = {n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", None)
+                 for n in ast.walk(fn) if isinstance(n, ast.Call)}
+        if callee not in names:
+            fail(f"E2: {module}::{function} does not call {callee}")
+    tree = ast.parse((SRC / "context_describe.py").read_text(encoding="utf-8"))
+    for function in ("_npc_context_company", "_mj_context_co_presents"):
+        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == function), None)
+        if fn is None or not any(isinstance(n, ast.Constant) and n.value == "tenue" for n in ast.walk(fn)):
+            fail(f"E2: context_describe.py::{function} does not name the tenue facet")
+
+
+def check_e3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.context_describe import _mj_context_co_presents
+    from world_engine.models import Character, Entity, Gathering, GatheringMember
+    from world_engine.models import Session as PlaySession
+
+    with Session(engine) as session:
+        ids = _d_world(session)
+        w = ids["world"]
+        for key in ("P", "A"):
+            char = session.get(Character, ids[key])
+            char.current_location_id = ids["Q"]
+            session.add(char)
+        session.get(Entity, ids["A"]).is_public = True
+        play = PlaySession(world_id=w, number=1)
+        session.add(play)
+        session.flush()
+        gathering = Gathering(world_id=w, session_id=play.id, location_id=ids["Q"], label="g")
+        session.add(gathering)
+        session.flush()
+        for key in ("P", "A"):
+            session.add(GatheringMember(gathering_id=gathering.id, entity_id=ids[key]))
+        session.commit()
+        _d_fact(session, ids, "veste verte", facet="tenue", about="A",
+                scopes=[("rencontre", "A", "knows", "t0")])
+        seen = _mj_context_co_presents(gathering.id, ids["P"], False, session)
+        blind = _mj_context_co_presents(gathering.id, ids["P"], True, session)
+        if [c.get("tenue") for c in seen] != ["D1 veste verte"]:
+            fail(f"E3: the scene shows {seen}")
+        if [c.get("tenue") for c in blind] != [None]:
+            fail(f"E3: blindfolded, the scene shows {blind}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -668,6 +791,9 @@ def main() -> int:
     check_c3()
     check_d1(engine)
     check_d2(engine)
+    check_e1(engine)
+    check_e2()
+    check_e3(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -677,7 +803,8 @@ def main() -> int:
           "placement and every encounter moves its last contact, through one writer each; "
           "every rewrite says whether it corrects or changes the world, and the version "
           "known follows the changes alone; a default is learned by a contact after it, kept "
-          "after leaving, and dated by the last contact with its anchors")
+          "after leaving, and dated by the last contact with its anchors; every knower "
+          "reader gives the version known, and the scene shows the outfit")
     return 0
 
 
````

## Scope OUT

- `facts_of`, the authoring assistants, the region/batch authors, `lore_candidates`, the creator routes: they speak for the creator and keep the current text.
- An NPC's own identity block (`context._npc_context_identity`) listing its outfit (Carried forward).
- Rewriting a stored row's own text.
- The dossier (G).
- Any prompt template change: the scene line gains text, not a rule.
- Every later brief of this lot.

## Invariants to defend

**The MJ context assembler is scoped to the player's perception boundary:** the outfit enters only through `known_facts_of` with the player as perceiver, and not when blindfolded. **Secrets are structurally excluded:** versions come from the fact's own history; nothing reads a secret row. **Creator-only facts never reach a prompt:** `known_facts_of` still starts from `facts_of`'s exclusion.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A context or tick check fails on a line's shape (a reader that pins the old co-present line).

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- … every knower reader gives the version known, and the scene shows the outfit`.
- `fact_facets.py`, `context_disclosure_floor.py`, `day_choice.py`, `identity_tokens.py`, `import_cycle.py` → `PASS`.
- Mutation test: in `facet_reads.known_facts_of`, return `[row for row in rows if row.fact_id in known]` → `E1`, `E2`; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `EVERY KNOWER READER GIVES THE VERSION KNOWN (TICKET-0105) -- AND THE SCENE SHOWS THE OUTFIT (BRIEF-0105-e, no schema change)` — in the diff.
