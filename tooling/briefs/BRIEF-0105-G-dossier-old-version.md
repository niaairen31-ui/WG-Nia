<!-- slug: dossier-old-version -->
# BRIEF 0105-G — "The Lore dossier marks an old version"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: BRIEF-0105-F
Commit header for decisions: `(BRIEF-0105-g, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/lore_selectors.py:174` → `def _knowledge_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:`; `:237` → `def who_knows_about(entity_id: str, world_id: str, db: Session) -> list[dict]:`; both set `"content": text` from `knowledge_texts`.
- `src/world_engine/lore_selectors.py` imports `from .prose_render import fact_texts, knowledge_texts` and nothing from `knowledge_resolve`.
- `src/world_engine/knowledge_resolve.py` defines `resolve_knowledge` (D); `src/world_engine/prose_render.py` defines `fact_texts_at` and `fact_is_stale` (C).
- `src/world_engine/lore_render.py:78` → `def _format_knowers(row: dict) -> str:` prints `content`.

## Facts carried

### R-09 — a stored row's own text [M]
Opened: `src/world_engine/models/canon_knowledge.py:199-239` (`Knowledge`:
nullable `content`, `updated_at`); `src/world_engine/lore_write_apply.py:
252-264` (Lore knowers are written without text);
`src/world_engine/prose_render.py:62-77`.
Finding: a row with its own text renders it; a row without falls back to
its fact's text.
Consequence: only the fallback is versioned; a row's own text is the
holder's version and is never rewritten.

### R-12 — the Lore dossier and its renderer [M]
Opened: `src/world_engine/lore_selectors.py:174-192` (`_knowledge_rows`),
`:237-275` (`who_knows_about`); `src/world_engine/lore_render.py:61-63,
78-84`; `scripts/seed_pilot.py:1796-1798` (the prompt's `is_incorrect`
rule); `tooling/verify/checks/lore_isolation.py` R2 (every `select(` in
`lore_selectors.py` is world-scoped).
Finding: both selectors list stored rows only; `content` is the row's own
text, `None` when it has none; the template prints `content`.
Consequence: G fills `content` with the marked old version for a stale row
without text, through resolver calls (no new `select(`), the prompt
unchanged (T1).

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

### C-09 — the dossier's old-version mark
Produced by: BRIEF-0105-G   Consumed by: the Lore renderer
In `entity_dossier` (section `knowledge`) and `who_knows_about` (section
`knowers`), a row whose own text is `None` and whose holder knows an older
version gets `content = "<old> (version ancienne — actuelle : <current>)"`
(both rendered); otherwise unchanged.

## Context

Nia locked K1 and T1: an outdated version is shown in the Lore dossier only, and the mark travels in the row's text, as the secret marker did in 0087, so the Lore prompt does not change. Play prompts never carry it: there, the old version is simply what the character knows.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `lore_selectors.py`: `_stale_label(db, knower_id, fact)` (C-09) through `resolve_knowledge`, `fact_is_stale` and `fact_texts_at` — no new `select(`; `_knowledge_rows` and `who_knows_about` use it when a row's own text is `None`;
   - adds G1 to `fact_learning.py`; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): the dossier marks an old version (BRIEF-0105-g)`.

````diff
diff --git a/src/world_engine/lore_selectors.py b/src/world_engine/lore_selectors.py
index ab91ef1..990563d 100644
--- a/src/world_engine/lore_selectors.py
+++ b/src/world_engine/lore_selectors.py
@@ -11,15 +11,16 @@ adding a question type.
 from __future__ import annotations
 
 from dataclasses import dataclass
-from typing import Callable
+from typing import Callable, Optional
 
 from sqlmodel import Session, func, select
 
 from .context import read_public_memberships
 from .facet_reads import creator_only_fact_ids, facts_of, joined
 from .facets import DESCRIPTIVE_FACETS, FACETS
+from .knowledge_resolve import resolve_knowledge
 from .models import Character, Entity, Fact, FactParticipant, Faction, Knowledge, NpcGoal, Relation
-from .prose_render import fact_texts, knowledge_texts
+from .prose_render import fact_is_stale, fact_texts, fact_texts_at, knowledge_texts
 from .relation_orientation import MAP_TOPOLOGY_TYPES
 from .writes.knowledge import knowledge_level_rank
 
@@ -171,6 +172,21 @@ def _relation_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
     return result
 
 
+def _stale_label(db: Session, knower_id: str, fact: Optional[Fact]) -> Optional[str]:
+    """K1/T1 (TICKET-0105, BRIEF-0105-G): for a knowledge row with no text
+    of its own, the version its holder knows when it is not the current one,
+    written « <old> (version ancienne — actuelle : <current>) »; `None` when
+    the holder knows the current version. The prompt is unchanged: the mark
+    travels in the row's text."""
+    if fact is None:
+        return None
+    known = resolve_knowledge(db, knower_id, fact.id)
+    if not fact_is_stale(fact, known.as_of):
+        return None
+    old, current = fact_texts_at(db, [(fact, known.as_of), (fact, None)])
+    return f"{old} (version ancienne — actuelle : {current})"
+
+
 def _knowledge_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
     rows = db.exec(
         select(Knowledge).join(Entity, Entity.id == Knowledge.entity_id).where(
@@ -178,18 +194,19 @@ def _knowledge_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
             Entity.world_id == world_id,
         )
     ).all()
-    facts = fact_texts(db, [db.get(Fact, k.fact_id) for k in rows])
+    fact_rows = [db.get(Fact, k.fact_id) for k in rows]
+    facts = fact_texts(db, fact_rows)
     return [
         {
             "section": "knowledge",
             "fact": fact,
             "level": k.level,
-            "content": text,
+            "content": text if text is not None else _stale_label(db, entity_id, fact_row),
             "source": k.source,
             "is_incorrect": k.is_incorrect,
             "is_secret": k.is_secret,
         }
-        for k, text, fact in zip(rows, knowledge_texts(db, rows), facts)
+        for k, text, fact, fact_row in zip(rows, knowledge_texts(db, rows), facts, fact_rows)
     ]
 
 
@@ -264,7 +281,7 @@ def who_knows_about(entity_id: str, world_id: str, db: Session) -> list[dict]:
             "knower_entity_id": knower.id,
             "knower_name": knower.name,
             "level": k.level,
-            "content": text,
+            "content": text if text is not None else _stale_label(db, knower.id, db.get(Fact, k.fact_id)),
             "source": k.source,
             "is_incorrect": k.is_incorrect,
             "is_secret": k.is_secret,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 1ef5062..dff431f 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17856,6 +17856,25 @@ put on a rewrite by the Lore draft.
 **Rejected.** H2, no preselection: every outfit change would need a click
 the facet already answers.
 
+
+## THE LORE DOSSIER MARKS AN OLD VERSION (TICKET-0105) -- IN THE ROW'S TEXT, PROMPT UNCHANGED (BRIEF-0105-g, no schema change)
+
+**K1, T1.** In `entity_dossier` and `who_knows_about`, a stored knowledge
+row with no text of its own whose holder knows an older version of its
+fact carries, as its `content`, « <old> (version ancienne — actuelle :
+<current>) », built by code (`lore_selectors._stale_label`). The template
+renderer prints it and the model receives it as text, so the Lore prompt
+does not change -- the precedent of the secret marker (0087, P1). A row
+with its own text, or whose holder knows the current version, is
+unchanged. Play prompts never carry the mark: there, the old version is
+simply what the character knows.
+
+**Carried forward.** What a character knows only through a default is not
+in the dossier (it lists stored rows); showing it is its own ticket.
+
+**Rejected.** T2, a rule in the Lore prompt (a new prompt version) for a
+mark the code already writes.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
index f518073..f65887d 100644
--- a/tooling/verify/checks/fact_learning.py
+++ b/tooling/verify/checks/fact_learning.py
@@ -113,6 +113,13 @@ F3 -- the panels send it (static). `FactsEditor.svelte` sends
    `writePanel.svelte.js` puts `kind` on a rewrite in `toProposal`; the
    built bundle carries « Changement dans le monde ».
 
+G1 -- the dossier marks an old version (BRIEF-0105-G, K1/T1, fixture). P
+   holds a stored row with no text of its own on A's `tenue`; the outfit is
+   then rewritten as a `changement`. In `entity_dossier(P)` and
+   `who_knows_about(A)`, that row's `content` is « <old> (version ancienne —
+   actuelle : <new>) »; a row on an unchanged fact keeps `content` None;
+   after an encounter of P with A, the outfit row's `content` is None again.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -874,6 +881,46 @@ def check_f3() -> None:
         fail("F3: the built bundle does not carry the choice (rebuild the frontend)")
 
 
+# --- G1 ------------------------------------------------------------------------
+
+def check_g1(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.encounters import record_encounter
+    from world_engine.lore_selectors import entity_dossier, who_knows_about
+    from world_engine.models import Fact
+    from world_engine.writes import write_knowledge
+    from world_engine.writes.facts import update_fact_content
+
+    with Session(engine) as session:
+        ids = _d_world(session)
+        w = ids["world"]
+        tenue = _d_fact(session, ids, "cape grise", facet="tenue", about="A")
+        still = _d_fact(session, ids, "rien de neuf", about="A")
+        for fact_id in (tenue, still):
+            write_knowledge(session, entity_id=ids["P"], fact_id=fact_id, level="knows")
+        session.commit()
+        update_fact_content(session, fact=session.get(Fact, tenue), content="D1 cape rouge",
+                            changed_by="check", kind="changement")
+        session.commit()
+        want = "D1 cape grise (version ancienne — actuelle : D1 cape rouge)"
+
+        def contents():
+            mine = [r["content"] for r in entity_dossier(ids["P"], w, session) if r["section"] == "knowledge"]
+            theirs = [r["content"] for r in who_knows_about(ids["A"], w, session) if r["section"] == "knowers"]
+            order = lambda v: (v is not None, v or "")  # noqa: E731
+            return sorted(mine, key=order), sorted(theirs, key=order)
+
+        mine, theirs = contents()
+        if mine != [None, want] or theirs != [None, want]:
+            fail(f"G1: the dossier shows {mine} / {theirs}")
+        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="conversation")
+        session.commit()
+        mine, theirs = contents()
+        if mine != [None, None] or theirs != [None, None]:
+            fail(f"G1: after an encounter the dossier shows {mine} / {theirs}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -895,6 +942,7 @@ def main() -> int:
     check_f1(engine)
     check_f2(engine)
     check_f3()
+    check_g1(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -906,7 +954,8 @@ def main() -> int:
           "known follows the changes alone; a default is learned by a contact after it, kept "
           "after leaving, and dated by the last contact with its anchors; every knower "
           "reader gives the version known, and the scene shows the outfit; both editors make "
-          "the creator say whether a rewrite corrects or changes the world")
+          "the creator say whether a rewrite corrects or changes the world; the Lore dossier "
+          "marks an old version")
     return 0
 
 
````

## Scope OUT

- Any change to `lore_render.py` or to the Lore prompts (T2, rejected).
- Showing in the dossier what a character knows only by default (Carried forward).
- A mark on a row that has its own text.
- Any Play surface.
- Every later brief of this lot.

## Invariants to defend

**The Lore consultation pipeline stays pure and world-scoped** (`lore_isolation.py` R1, R2): no model call, no write, no unscoped `select(`. **The lore renderer receives rows, never a `Session`:** the mark is built in the selector. **Secrets and false beliefs are still returned and marked** by the renderer; the old-version mark is added to `content`, the flags are untouched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `lore_isolation.py` or `lore_selectors.py` fails.

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- … the Lore dossier marks an old version`.
- `lore_isolation.py`, `lore_selectors.py`, `identity_tokens.py` → `PASS`.
- Mutation test: in `_stale_label`, return `None` first → `G1`; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `python tooling/verify/run.py --ticket TICKET-0105-fact-learning` → every Machine arrow `PASS`.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE LORE DOSSIER MARKS AN OLD VERSION (TICKET-0105) -- IN THE ROW'S TEXT, PROMPT UNCHANGED (BRIEF-0105-g, no schema change)` — in the diff.
