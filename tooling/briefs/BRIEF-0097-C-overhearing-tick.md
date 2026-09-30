<!-- slug: overhearing-tick -->
# BRIEF 0097-C — "Overhearing and the tick name facts by code"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: B
Commit header for decisions: `(BRIEF-0097-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/analyzer_transcript.py:666` (after B) → `def _overhearing_subject_set(world_id: str, db: Session) -> set[str]:`
- `src/world_engine/tick.py:103` (after B) → `secret_subjects = {` (a SetComp over `is_secret` rows)
- `scripts/seed_pilot.py` `OVERHEARING_CLASSIFICATION_USER_TEMPLATE` → contains `{subject_list}`
- `scripts/seed_pilot.py` `WORLD_TICK_SYSTEM_PROMPT` → new_knowledge shape contains `"subject":"<short_slug>"`
- `tooling/verify/checks/world_tick.py` `check_z3_floor` → looks for a SetComp assigned to `secret_subjects`
- `src/world_engine/fact_refs.py` → defines `code_facts`, `CodedFacts` (brief B)

## Facts carried

### R-07 — overhearing
Opened: `analyzer_transcript.py:659-900`, `analyzer.py:76-170`,
`scripts/seed_pilot.py:421-448` (prompt), `prompt_registry.py:148`.
Finding: the classifier receives every subject of the world
(`{subject_list}`), returns `{"subject","speaker"}`; only a speaker's
non-secret row can source a proposal (K2 guard, secret guard).
Consequence: L1's list (the speakers' non-secret facts) is the effective set
already; the placeholder becomes `{fact_list}`.

### R-08 — the tick
Opened: `tick.py:95-250`, `tick_normalize.py:700-817`, `tick_context.py:126-275`,
`seed_pilot.py:915-975` (prompt), `tooling/verify/checks/world_tick.py:310-392`
(rule 5's implementation).
Finding: `secret_subjects` is a SetComp over `is_secret` rows; the floor
sets `secret_derived` on a subject/substring match; rule 5 requires that
SetComp name, an `in` comparison on it, and no `is_secret` assignment from it.
Consequence: C renames to `secret_fact_ids` (+ `secret_texts`) and retargets
rule 5 in the same commit.

## Contracts

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

### C-04 — overhearing
Produced by: C   Consumed by: nothing later
List: the facts the two possible speakers hold on a non-secret row, NPC
first, each in `Knowledge.id` order. Answer: `[{"fact": "<code>", "speaker":
"player"|"npc"}]`. Proposals carry `fact_id` (and a `knowledge_change` a
display `fact_label`); never `subject`.

### C-05 — tick
Produced by: C   Consumed by: nothing later
`tick_context.tick_knowledge_rows(npc_id, session)` (stored rows by id,
then resolved defaults), `tick_fact_codes(npc_id, session)`; each briefing
knowledge line starts `- [f<n>] `. A `new_knowledge` item may carry
`"source_fact": "<code>"|null`; resolved, the payload gets `fact_id`, and
`secret_derived` is set when that fact is one of the NPC's secret facts or
the content contains a secret fact's rendered text. `is_secret` is never
set from either.

## Context

The two places a model already chose a known thing by copying a string now choose it by code (L1, Z2). A bystander learns the speaker's fact itself; the tick's `secret_derived` floor becomes exact on the code, with the substring test kept as a second net.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: codes the overhearing list (the speakers' non-secret facts) and parses `{"fact", "speaker"}`; carries `fact_id` (and a display `fact_label`) on overhearing proposals; keys `analyzer._overhearing_existing_keys` on C-01; tags each tick briefing knowledge line `[f<n>]` (`tick_knowledge_rows`, `tick_fact_codes`); resolves `source_fact` in `_tick_normalize_new_knowledge` and sets the Z3 floor from `secret_fact_ids`/`secret_texts`; retargets `world_tick.py` rule 5; rewrites the two prompts in `seed_pilot.py`; creates `scripts/apply_ticket_0097_fact_code_prompts.py`; updates `analyzer_seam.py`'s stubs; adds K5.
2. Regenerate the index.
3. Message: `feat(knowledge): overhearing and the tick name facts by code (BRIEF-0097-c)`.

```diff
diff --git a/scripts/apply_ticket_0097_fact_code_prompts.py b/scripts/apply_ticket_0097_fact_code_prompts.py
new file mode 100644
index 0000000..ac89de7
--- /dev/null
+++ b/scripts/apply_ticket_0097_fact_code_prompts.py
@@ -0,0 +1,89 @@
+"""One-shot, idempotent delivery of the TICKET-0097 prompt updates onto the
+live DB: models name facts by code, never by a free-text subject.
+
+- `pt-overhearing-classification` (BRIEF-0097-C, L1): classifies against a
+  coded fact list; its variables become `fact_list`, `player_line`,
+  `npc_line`.
+- `pt-world-tick` (BRIEF-0097-C, Z2): a `new_knowledge` names what the NPC
+  passes on by its briefing code (`source_fact`).
+
+Embeds NO prompt text of its own; it imports each text from
+`scripts/seed_pilot.py` (single source of text). History is sacred: a changed
+text lands as a new `prompt_version` row, the old one untouched. Variables
+are full-replaced through `write_prompt_variables`, as `seed_pilot.py` does.
+
+Touches nothing else. Safe to re-run: an unchanged head prints "unchanged".
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if _env not in ("prod", "test"):
+    print(
+        "apply_ticket_0097_fact_code_prompts.py refuses to run unless "
+        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
+    )
+    sys.exit(1)
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+
+from sqlmodel import Session  # noqa: E402
+
+import seed_pilot  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_variables, write_prompt_version  # noqa: E402
+
+# (head id, system prompt, user template, variables, version note)
+_UPDATES: tuple[tuple[str, str, str, list[str], str], ...] = (
+    (
+        "pt-overhearing-classification",
+        seed_pilot.OVERHEARING_CLASSIFICATION_SYSTEM_PROMPT,
+        seed_pilot.OVERHEARING_CLASSIFICATION_USER_TEMPLATE,
+        ["fact_list", "player_line", "npc_line"],
+        "TICKET-0097 BRIEF-0097-C -- classify against a coded fact list (L1)",
+    ),
+    (
+        "pt-world-tick",
+        seed_pilot.WORLD_TICK_SYSTEM_PROMPT,
+        seed_pilot.WORLD_TICK_USER_TEMPLATE,
+        ["tick_context", "interval_label"],
+        "TICKET-0097 BRIEF-0097-C -- new_knowledge names its source fact by code (Z2)",
+    ),
+)
+
+
+def _apply(session: Session, head_id: str, system_prompt: str, user_template: str,
+           variables: list[str], note: str) -> None:
+    head = session.get(PromptTemplate, head_id)
+    if head is None:
+        print(f"{head_id}: head not found — run scripts/seed_pilot.py first")
+        sys.exit(1)
+    write_prompt_variables(session, template_id=head.id, variables=variables)
+    current = current_prompt(session, head)
+    if current.system_prompt == system_prompt and current.user_template == user_template:
+        print(f"{head_id}: unchanged (v{current.version_number})")
+        return
+    version = write_prompt_version(
+        session, template_id=head.id, system_prompt=system_prompt,
+        user_template=user_template, note=note,
+    )
+    print(f"{head_id}: v{current.version_number} -> v{version.version_number}")
+
+
+def main() -> None:
+    with Session(engine) as session:
+        for update in _UPDATES:
+            _apply(session, *update)
+        session.commit()
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 703fce9..4d4092c 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -426,25 +426,27 @@ JSON array of canon mutations ([] if nothing changed):"""
 # usage='overhearing_classification', world_id=NULL, destination='local'.
 # The model's ONLY job is closed-list classification; attribution, receiver
 # computation, and level computation happen in code (analyzer.analyze_overhearing).
-# Variables substituted with str.replace() in analyzer.py: {subject_list},
-# {player_line}, {npc_line}.
+# Variables substituted with str.replace() in analyzer_transcript.py: {fact_list},
+# {player_line}, {npc_line}. {fact_list} is a coded list ("f1 — <text>",
+# TICKET-0097, L1): the model answers with a code, the code resolves it.
 OVERHEARING_CLASSIFICATION_SYSTEM_PROMPT = """\
-You classify a single RPG conversation turn against a closed list of
-knowledge subjects. You NEVER invent subjects. You NEVER add subjects
-that are not in the provided list.
+You classify a single RPG conversation turn against a closed, coded list
+of facts the speakers know. Each line of the list is a code, a dash, and
+the fact. You NEVER invent codes. You NEVER answer with a code that is
+not in the provided list.
 
-A subject matches ONLY if the line substantively asserts, reveals, or
-discusses information about it. A mere mention of a name in passing,
-small talk, greetings, or atmosphere does NOT match.
+A fact matches ONLY if the line substantively asserts, reveals, or
+discusses it. A mere mention of a name in passing, small talk,
+greetings, or atmosphere does NOT match.
 
-Output ONLY a JSON array. Each element: {"subject": "<exact subject
-string from the list>", "speaker": "player" | "npc"}. The speaker is
-the one whose line carries the information. If nothing matches, output
-[]. An empty array is a normal, expected result for most turns."""
+Output ONLY a JSON array. Each element: {"fact": "<code from the list,
+for example f3>", "speaker": "player" | "npc"}. The speaker is the one
+whose line carries the information. If nothing matches, output []. An
+empty array is a normal, expected result for most turns."""
 
 OVERHEARING_CLASSIFICATION_USER_TEMPLATE = """\
-Known world subjects (closed list):
-{subject_list}
+Facts the speakers know (closed, coded list):
+{fact_list}
 
 Turn to classify:
 [JOUEUR] {player_line}
@@ -936,7 +938,7 @@ Never invent identifiers, ids, people, or places absent from the briefing.
 Payload shapes:
   goal_change      -> {"action":"complete|abandon|create_short","goal":"…","agenda":"<optional: title from TON INTRIGUE, only when this new goal serves it>","effects":[<optional, "complete" only, see EFFECTS below>]}
   relation_change  -> {"other":"<name from the briefing>","relation_type":"…","intensity_delta":<signed int>}
-  new_knowledge    -> {"recipient":"self" | "<name>","subject":"<short_slug>","level":"rumor|partial|knows","content":"…","source":"…","is_secret":true|false,"secret_derived":true|false}
+  new_knowledge    -> {"recipient":"self" | "<name>","source_fact":"<code from CE QUE TU SAIS>" | null,"level":"rumor|partial|knows","content":"…","source":"…","is_secret":true|false,"secret_derived":true|false}
   npc_move         -> {"destination":"<name from OÙ TU PEUX ALLER>"}
   agenda_step_change -> {"agenda":"<title from TON INTRIGUE>","action":"complete|fail","outcome":"…","effects":[<optional, "complete" only, see EFFECTS below>]}
   agenda_creation  -> {"title":"<new intrigue title>","steps":["<objective 1>","<objective 2>",…]}
@@ -958,9 +960,11 @@ work, or mere proximity is NOT a relation_change.
 
 === NEW_KNOWLEDGE RULES ===
 "recipient":"self" when the NPC LEARNED something during the interval;
-"<name>" when the NPC TOLD that person something. Set
-"secret_derived":true when the information comes from a [SECRET] item
-in your briefing. Whether the knowledge is secret FOR THE RECIPIENT is
+"<name>" when the NPC TOLD that person something. When the NPC passes on
+something it already knows, set "source_fact" to the code in brackets at
+the start of that line of CE QUE TU SAIS (for example "f3"); otherwise
+"source_fact" is null. Set "secret_derived":true when the information
+comes from a [SECRET] item in your briefing. Whether the knowledge is secret FOR THE RECIPIENT is
 a separate judgment: set "is_secret" by intent — a confidence shared
 discreetly stays secret; information wielded openly against an enemy
 does not. Never copy [SECRET]/[AFFILIATION SECRÈTE] markers into
@@ -2548,7 +2552,7 @@ def seed(session: Session) -> None:
         usage="overhearing_classification",
         system_prompt=OVERHEARING_CLASSIFICATION_SYSTEM_PROMPT,
         user_template=OVERHEARING_CLASSIFICATION_USER_TEMPLATE,
-        variables=["subject_list", "player_line", "npc_line"],
+        variables=["fact_list", "player_line", "npc_line"],
         destination="local",
     )
 
diff --git a/src/world_engine/analyzer.py b/src/world_engine/analyzer.py
index e1d72cb..a56706c 100644
--- a/src/world_engine/analyzer.py
+++ b/src/world_engine/analyzer.py
@@ -7,7 +7,7 @@ resulting ProposedMutation rows, and advances conv.last_analyzed_turn — all in
 one transaction.
 
 analyze_overhearing() (Tier 4, separate pass) is unaffected by the above: it
-classifies a single turn against a closed subject list and proposes
+classifies a single turn against a closed, coded fact list and proposes
 acquisition/upgrade knowledge mutations for bystanders.
 
 Both are now thin, conversation-bound wrappers (TICKET-0051, BRIEF-0051-c):
@@ -51,6 +51,7 @@ from .analyzer_transcript import (
     analyze_transcript,
     load_analysis_prompt,
 )
+from .fact_refs import knowledge_key
 from .models import Conversation, ConversationMessage, GatheringMember, ProposedMutation
 
 _log = logging.getLogger(__name__)
@@ -75,7 +76,7 @@ def _overhearing_eligible_receivers(conv: Conversation, npc_entity_id: str | Non
 def _overhearing_existing_keys(conversation_id: str, db: Session) -> tuple[set, set]:
     """Existing 'proposed' new_knowledge/knowledge_change rows for this
     conversation, for the proposal-dedup guard (k) — keyed by
-    (entity_id, subject)."""
+    (entity_id, `knowledge_key`) (TICKET-0097)."""
     existing = db.exec(
         select(ProposedMutation).where(
             ProposedMutation.conversation_id == conversation_id,
@@ -86,7 +87,7 @@ def _overhearing_existing_keys(conversation_id: str, db: Session) -> tuple[set,
     proposed_keys: set[tuple] = set()
     for pm in existing:
         p = pm.payload if isinstance(pm.payload, dict) else {}
-        proposed_keys.add((p.get("entity_id"), p.get("subject")))
+        proposed_keys.add((p.get("entity_id"), knowledge_key(p)))
 
     existing_changes = db.exec(
         select(ProposedMutation).where(
@@ -98,7 +99,7 @@ def _overhearing_existing_keys(conversation_id: str, db: Session) -> tuple[set,
     proposed_change_keys: set[tuple] = set()
     for pm in existing_changes:
         p = pm.payload if isinstance(pm.payload, dict) else {}
-        proposed_change_keys.add((p.get("entity_id"), p.get("subject")))
+        proposed_change_keys.add((p.get("entity_id"), knowledge_key(p)))
 
     return proposed_keys, proposed_change_keys
 
diff --git a/src/world_engine/analyzer_transcript.py b/src/world_engine/analyzer_transcript.py
index e22396c..c176c48 100644
--- a/src/world_engine/analyzer_transcript.py
+++ b/src/world_engine/analyzer_transcript.py
@@ -59,11 +59,11 @@ from typing import Any, Optional
 from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
-from .models import Character, Entity, Knowledge, ProposedMutation, PromptTemplate
+from .models import Character, Entity, Fact, Knowledge, ProposedMutation, PromptTemplate
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
-from .fact_refs import knowledge_key
-from .prose_render import knowledge_text
+from .fact_refs import CodedFacts, code_facts, find_held, knowledge_key
+from .prose_render import fact_text, knowledge_text
 from .writes import knowledge_level_rank
 
 _log = logging.getLogger(__name__)
@@ -663,20 +663,26 @@ def analyze_transcript(
     )
 
 
-def _overhearing_subject_set(world_id: str, db: Session) -> set[str]:
-    """c. Subject list — closed list, scoped to the world."""
-    subjects = db.exec(
-        select(Knowledge.subject)
-        .join(Entity, Entity.id == Knowledge.entity_id)
-        .where(Entity.world_id == world_id)
-        .distinct()
-    ).all()
-    return set(subjects)
+def _overhearing_fact_codes(attribution: AttributionContext, db: Session) -> CodedFacts:
+    """c. The closed, coded fact list (L1, TICKET-0097): the facts the
+    possible speakers hold on a non-secret row -- the NPC's first, then the
+    counterparty's, each in `Knowledge.id` order. Only these can source a
+    proposal (K2 guard and secret guard below), so the list is exactly the
+    classifiable set, and a secret's text never reaches the classifier."""
+    speakers = [e for e in (attribution.default_subject_id, attribution.default_counterparty_id) if e]
+    fact_ids: list[str] = []
+    for speaker_id in speakers:
+        fact_ids += db.exec(
+            select(Knowledge.fact_id)
+            .where(Knowledge.entity_id == speaker_id, Knowledge.is_secret == False)  # noqa: E712
+            .order_by(Knowledge.id)
+        ).all()
+    return code_facts(db, fact_ids)
 
 
 def _overhearing_classify(
     db: Session, world_id: str, speaker_line: str, listener_line: str,
-    subject_set: set[str], model: str, host: str,
+    facts: CodedFacts, model: str, host: str,
 ) -> list | None:
     """d. Model call."""
     template = load_analysis_prompt(
@@ -685,7 +691,7 @@ def _overhearing_classify(
     version = current_prompt(db, template)
     user_message = (
         version.user_template
-        .replace("{subject_list}", "\n".join(sorted(subject_set)))
+        .replace("{fact_list}", "\n".join(facts.lines))
         .replace("{player_line}", speaker_line)
         .replace("{npc_line}", listener_line)
     )
@@ -699,22 +705,23 @@ def _overhearing_classify(
     return llm_parse.extract_array_or_none(raw)
 
 
-def _overhearing_parse_classifications(items: list, subject_set: set[str]) -> list[tuple[str, str]]:
-    """e. Normalization — exact closed-list match only, no fuzzy matching."""
+def _overhearing_parse_classifications(items: list, facts: CodedFacts) -> list[tuple[str, str]]:
+    """e. Normalization — a code the list showed, resolved to its fact id;
+    anything else is dropped. No fuzzy matching."""
     classified: list[tuple[str, str]] = []
     for raw_item in items:
         if not isinstance(raw_item, dict):
             _log.warning("[overhearing] dropped non-dict element: %r", raw_item)
             continue
-        subject = raw_item.get("subject")
+        fact_id = facts.resolve(raw_item.get("fact"))
         speaker = raw_item.get("speaker")
-        if subject not in subject_set:
-            _log.warning("[overhearing] dropped unknown subject: %r", subject)
+        if fact_id is None:
+            _log.warning("[overhearing] dropped unknown fact code: %r", raw_item.get("fact"))
             continue
         if speaker not in ("player", "npc"):
             _log.warning("[overhearing] dropped invalid speaker: %r", speaker)
             continue
-        classified.append((subject, speaker))
+        classified.append((fact_id, speaker))
     return classified
 
 
@@ -724,24 +731,21 @@ def _resolve_location_name(db: Session, location_id: str | None) -> str:
 
 
 def _overhearing_mutation_for_receiver(
-    receiver_id: str, subject: str, speaker_id: str, speaker_row: Knowledge,
+    receiver_id: str, fact_id: str, speaker_id: str, speaker_row: Knowledge,
     acquired_level: str, world_id: str, db: Session,
     proposed_keys: set, proposed_change_keys: set, location_name: str,
     name_fn, now: datetime,
 ) -> Optional[ProposedMutation]:
-    """j/k/l for one (subject, receiver) pair — acquisition or monotone
-    upgrade, proposal-deduped, or None (skipped silently, no queue noise)."""
-    existing_row = db.exec(
-        select(Knowledge).where(
-            Knowledge.entity_id == receiver_id,
-            Knowledge.subject == subject,
-        )
-    ).first()
+    """j/k/l for one (fact, receiver) pair — acquisition or monotone
+    upgrade, proposal-deduped, or None (skipped silently, no queue noise).
+    The receiver learns the speaker's fact itself (TICKET-0097)."""
+    identity = {"fact_id": fact_id}
+    existing_row = find_held(db, receiver_id, identity)
 
     if existing_row is not None:
         if knowledge_level_rank(acquired_level) <= knowledge_level_rank(existing_row.level):
             return None
-        change_key = (receiver_id, subject)
+        change_key = (receiver_id, knowledge_key(identity))
         if change_key in proposed_change_keys:
             return None
         proposed_change_keys.add(change_key)
@@ -754,7 +758,8 @@ def _overhearing_mutation_for_receiver(
             target_id=None,
             payload={
                 "entity_id": receiver_id,
-                "subject": subject,
+                "fact_id": fact_id,
+                "fact_label": fact_text(db, db.get(Fact, fact_id)),
                 "from_level": existing_row.level,
                 "to_level": acquired_level,
                 "source": f"overheard:{speaker_id}",
@@ -768,7 +773,7 @@ def _overhearing_mutation_for_receiver(
             proposed_at=now,
         )
 
-    key = (receiver_id, subject)
+    key = (receiver_id, knowledge_key(identity))
     if key in proposed_keys:
         return None
     proposed_keys.add(key)
@@ -782,7 +787,7 @@ def _overhearing_mutation_for_receiver(
         target_id=None,
         payload={
             "entity_id": receiver_id,
-            "subject": subject,
+            "fact_id": fact_id,
             "level": acquired_level,
             "content": knowledge_text(db, speaker_row),  # rendered (BRIEF-0091-J)
             "is_incorrect": speaker_row.is_incorrect,
@@ -820,7 +825,7 @@ def _overhearing_build_mutations(
     mutations: list[ProposedMutation] = []
     dropped_unattributed = 0
     dropped_by_type: dict[str, int] = {}
-    for subject, speaker in classified:
+    for fact_id, speaker in classified:
         # f. Speaker resolution via the refusable identity contract — an
         # NPC never overhears itself, and a "player spoke" classification
         # with no player in this transcript (an observed run) is a model
@@ -841,12 +846,7 @@ def _overhearing_build_mutations(
 
         # g. K2 guard (source authority) — the speaker's row is the only
         # authority; a speaker "knowing" without a row is model noise.
-        speaker_row = db.exec(
-            select(Knowledge).where(
-                Knowledge.entity_id == speaker_id,
-                Knowledge.subject == subject,
-            )
-        ).first()
+        speaker_row = find_held(db, speaker_id, {"fact_id": fact_id})
         if speaker_row is None:
             continue
 
@@ -860,7 +860,7 @@ def _overhearing_build_mutations(
 
         for receiver_id in receivers:
             mutation = _overhearing_mutation_for_receiver(
-                receiver_id, subject, speaker_id, speaker_row, acquired_level,
+                receiver_id, fact_id, speaker_id, speaker_row, acquired_level,
                 world_id, db, proposed_keys, proposed_change_keys,
                 location_name, _name, now,
             )
@@ -891,15 +891,15 @@ def analyze_overheard_lines(
     if not receiver_ids:
         return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})
 
-    subject_set = _overhearing_subject_set(world_id, db)
-    if not subject_set:
+    facts = _overhearing_fact_codes(attribution, db)
+    if not facts.lines:
         return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})
 
-    items = _overhearing_classify(db, world_id, speaker_line, listener_line, subject_set, model, host)
+    items = _overhearing_classify(db, world_id, speaker_line, listener_line, facts, model, host)
     if items is None:
         return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})
 
-    classified = _overhearing_parse_classifications(items, subject_set)
+    classified = _overhearing_parse_classifications(items, facts)
     if not classified:
         return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})
 
diff --git a/src/world_engine/tick.py b/src/world_engine/tick.py
index f54a28f..a770e5c 100644
--- a/src/world_engine/tick.py
+++ b/src/world_engine/tick.py
@@ -23,8 +23,9 @@ from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
 from .analyzer import load_analysis_prompt
-from .fact_refs import knowledge_key
-from .models import Agenda, Character, Entity, FactionMembership, Knowledge, ProposedMutation
+from .fact_refs import CodedFacts, knowledge_key
+from .prose_render import fact_texts
+from .models import Agenda, Character, Entity, Fact, FactionMembership, Knowledge, ProposedMutation
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
 from .tick_context import (
@@ -32,6 +33,7 @@ from .tick_context import (
     assemble_location_event_context,
     assemble_tick_context,
     _reachable_locations,
+    tick_fact_codes,
 )
 from .tick_normalize import (
     _build_effects_roster,
@@ -100,12 +102,14 @@ def _tick_call_npc_model(briefing: str, interval_label: str, template, version,
 def _tick_build_npc_indexes(db: Session, npc_id: str, npc_name: str, world_id: str, from_location_id: str | None) -> dict[str, Any]:
     roster = _build_roster(db, npc_id, npc_name, from_location_id)
     effects_roster = _build_effects_roster(db, world_id)
-    secret_subjects = {
-        k.subject.casefold()
-        for k in db.exec(
-            select(Knowledge).where(Knowledge.entity_id == npc_id, Knowledge.is_secret == True)  # noqa: E712
-        ).all()
-        if k.subject
+    # Z3 floor inputs (TICKET-0097, Z2): the NPC's secret facts, by id and
+    # by rendered text; the briefing's fact codes.
+    secret_rows = db.exec(
+        select(Knowledge).where(Knowledge.entity_id == npc_id, Knowledge.is_secret == True)  # noqa: E712
+    ).all()
+    secret_fact_ids = {k.fact_id for k in secret_rows if k.is_secret}
+    secret_texts = {
+        text.casefold() for text in fact_texts(db, [db.get(Fact, k.fact_id) for k in secret_rows]) if text
     }
     # Owner-restricted agendas_index (TICKET-0020, BRIEF-0020-b): name -> id
     # over ACTIVE agendas OWNED BY THIS NPC ONLY (zero or one, by the
@@ -121,7 +125,9 @@ def _tick_build_npc_indexes(db: Session, npc_id: str, npc_name: str, world_id: s
     return {
         "roster": roster,
         "effects_roster": effects_roster,
-        "secret_subjects": secret_subjects,
+        "fact_codes": tick_fact_codes(npc_id, db),
+        "secret_fact_ids": secret_fact_ids,
+        "secret_texts": secret_texts,
         "agendas_index": agendas_index,
     }
 
@@ -169,7 +175,8 @@ def _tick_npc_dedup_note(mutation_type: str, payload: dict, state: dict[str, Any
 
 
 def _tick_normalize_npc_items(
-    items: list, *, npc_id: str, world_id: str, roster: dict[str, str], secret_subjects: set[str],
+    items: list, *, npc_id: str, world_id: str, roster: dict[str, str], fact_codes: CodedFacts,
+    secret_fact_ids: set[str], secret_texts: set[str],
     destinations: dict[str, str], from_location_id: str | None, from_name: str | None,
     agendas_index: dict[str, str], effects_roster: dict[str, str], db: Session,
     tick_id: str, now: datetime,
@@ -182,8 +189,8 @@ def _tick_normalize_npc_items(
 
     for raw_item in items:
         normalized = _normalize_tick_item(
-            raw_item, npc_id=npc_id, world_id=world_id, roster=roster,
-            secret_subjects=secret_subjects, destinations=destinations,
+            raw_item, npc_id=npc_id, world_id=world_id, roster=roster, fact_codes=fact_codes,
+            secret_fact_ids=secret_fact_ids, secret_texts=secret_texts, destinations=destinations,
             from_location_id=from_location_id, from_name=from_name,
             agendas_index=agendas_index, effects_roster=effects_roster, db=db,
         )
@@ -236,7 +243,8 @@ def _tick_process_npc(
     indexes = _tick_build_npc_indexes(db, npc_id, npc_name, world_id, setup["from_location_id"])
     rows, proposed, dropped, notes = _tick_normalize_npc_items(
         items, npc_id=npc_id, world_id=world_id, roster=indexes["roster"],
-        secret_subjects=indexes["secret_subjects"], destinations=setup["destinations"],
+        fact_codes=indexes["fact_codes"], secret_fact_ids=indexes["secret_fact_ids"],
+        secret_texts=indexes["secret_texts"], destinations=setup["destinations"],
         from_location_id=setup["from_location_id"], from_name=setup["from_name"],
         agendas_index=indexes["agendas_index"], effects_roster=indexes["effects_roster"],
         db=db, tick_id=tick_id, now=now,
diff --git a/src/world_engine/tick_context.py b/src/world_engine/tick_context.py
index f55e8c2..6503f18 100644
--- a/src/world_engine/tick_context.py
+++ b/src/world_engine/tick_context.py
@@ -37,7 +37,8 @@ from .knowledge_resolve import (
     resolve_public_levels,
 )
 from .facet_reads import facts_of, joined
-from .prose_render import knowledge_texts
+from .fact_refs import CodedFacts, code_facts
+from .prose_render import fact_texts, knowledge_texts
 from .ledger import get_balance
 from .models import (
     Agenda,
@@ -123,13 +124,16 @@ def _render_perception(name: str, rel: Relation) -> str:
     return f"- {name} : {rel.notes} (perception : {rel.type}, disposition : {adjective})"
 
 
-def _knowledge_line(k: Knowledge, content: Optional[str]) -> str:
-    """`content` is `k`'s rendered text (`prose_render.knowledge_texts`)."""
-    text = content or f"{k.subject} ({k.level})"
+def _knowledge_line(k: Knowledge, content: Optional[str], fact: str, code: Optional[str]) -> str:
+    """`content` is `k`'s rendered text (`prose_render.knowledge_texts`),
+    `fact` its fact's rendered text, `code` its fact code in the briefing
+    (TICKET-0097, Z2), shown first so the model can name what it passes on."""
+    text = content or f"{fact} ({k.level})"
     if k.is_incorrect:
         text += " (tu en es convaincu, mais c'est faux)"
     prefix = "[SECRET] " if k.is_secret else ""
-    return f"- {prefix}{text}"
+    tag = f"[{code}] " if code else ""
+    return f"- {tag}{prefix}{text}"
 
 
 def _goal_provenance_suffix(goal_id: str, session: Session) -> str:
@@ -257,20 +261,32 @@ def _tick_intrigue_section(npc_id: str, session: Session) -> str:
     return _section(H_INTRIGUE, "\n".join(intrigue_lines)) + "\n"
 
 
-def _tick_knowledge_block(npc_id: str, session: Session) -> str:
+def tick_knowledge_rows(npc_id: str, session: Session) -> list[Knowledge]:
     """ALL knowledge, no share_threshold gating, no is_secret exclusion (T1
-    conscious exception): there is no interlocutor."""
+    conscious exception): there is no interlocutor. Stored rows in
+    `Knowledge.id` order, then the resolved scoped defaults (TICKET-0082,
+    BRIEF-0082-c, G2a) -- the one order the briefing and its fact codes
+    share."""
     knowledge = session.exec(
         select(Knowledge).where(Knowledge.entity_id == npc_id).order_by(Knowledge.id)
     ).all()
-    # Union with resolved scoped defaults (TICKET-0082, BRIEF-0082-c, G2a).
-    knowledge = knowledge + resolve_default_rows(
-        session, npc_id, {k.fact_id for k in knowledge}
-    )
+    return knowledge + resolve_default_rows(session, npc_id, {k.fact_id for k in knowledge})
+
+
+def tick_fact_codes(npc_id: str, session: Session) -> CodedFacts:
+    """The briefing's fact codes (Z2): one per `tick_knowledge_rows` row."""
+    return code_facts(session, [k.fact_id for k in tick_knowledge_rows(npc_id, session)])
+
+
+def _tick_knowledge_block(npc_id: str, session: Session) -> str:
+    knowledge = tick_knowledge_rows(npc_id, session)
     if not knowledge:
         return "(aucune connaissance)"
+    codes = code_facts(session, [k.fact_id for k in knowledge])
+    facts = fact_texts(session, [session.get(Fact, k.fact_id) for k in knowledge])
     return "\n".join(
-        _knowledge_line(k, text) for k, text in zip(knowledge, knowledge_texts(session, knowledge))
+        _knowledge_line(k, text, fact, codes.code_of(k.fact_id))
+        for k, text, fact in zip(knowledge, knowledge_texts(session, knowledge), facts)
     )
 
 
diff --git a/src/world_engine/tick_normalize.py b/src/world_engine/tick_normalize.py
index 30dfd42..fc79ca4 100644
--- a/src/world_engine/tick_normalize.py
+++ b/src/world_engine/tick_normalize.py
@@ -24,7 +24,7 @@ from typing import Any
 from sqlmodel import Session, select
 
 from .analyzer import _GOAL_ACTION_MAP, _MUTATION_TYPE_MAP
-from .fact_refs import text_key
+from .fact_refs import CodedFacts
 from .models import Agenda, AgendaStep, Character, Entity, Faction, Relation
 from .tick_context import _perceived_target
 
@@ -702,8 +702,13 @@ def _tick_normalize_npc_move(
 
 
 def _tick_normalize_new_knowledge(
-    payload_in: dict, *, npc_id: str, roster: dict[str, str], secret_subjects: set[str],
+    payload_in: dict, *, npc_id: str, roster: dict[str, str], fact_codes: CodedFacts,
+    secret_fact_ids: set[str], secret_texts: set[str],
 ) -> tuple[dict, str] | None:
+    """`source_fact` is the briefing code of what the NPC passes on (Z2,
+    TICKET-0097): resolved, the recipient learns that very fact. The Z3
+    floor marks `secret_derived` when that fact is one of the NPC's secrets,
+    and, as a second net, when the content contains a secret's text."""
     recipient = str(payload_in.get("recipient") or "self").strip()
     if recipient.casefold() == "self":
         entity_id = npc_id
@@ -716,26 +721,26 @@ def _tick_normalize_new_knowledge(
     if not content:
         _log.warning("[tick] dropped new_knowledge: empty content")
         return None
-    subject = str(payload_in.get("subject") or "").strip() or text_key(content)
+    source_fact = fact_codes.resolve(payload_in.get("source_fact"))
 
-    # Z3 floor (verbatim mechanics) — mechanical provenance only, never
-    # touches is_secret: confidentiality is the receiving NPC's disposition
-    # (model proposes, creator judges).
+    # Z3 floor — mechanical provenance only, never touches is_secret:
+    # confidentiality is the receiving NPC's disposition (model proposes,
+    # creator judges).
     secret_derived = bool(payload_in.get("secret_derived", False))
-    subject_cf = subject.casefold()
     content_cf = content.casefold()
-    if subject_cf in secret_subjects or any(s in content_cf for s in secret_subjects):
+    if source_fact in secret_fact_ids or any(t in content_cf for t in secret_texts):
         secret_derived = True
 
     payload = {
         "entity_id": entity_id,
-        "subject": subject,
         "level": str(payload_in.get("level") or "rumor"),
         "content": content,
         "source": str(payload_in.get("source") or "world_tick"),
         "is_secret": bool(payload_in.get("is_secret", False)),
         "secret_derived": secret_derived,
     }
+    if source_fact is not None:
+        payload["fact_id"] = source_fact
     return payload, "knowledge"
 
 
@@ -745,7 +750,8 @@ def _normalize_tick_item(
     npc_id: str,
     world_id: str,
     roster: dict[str, str],
-    secret_subjects: set[str],
+    fact_codes: CodedFacts,
+    secret_fact_ids: set[str], secret_texts: set[str],
     destinations: dict[str, str],
     from_location_id: str | None,
     from_name: str | None,
@@ -795,7 +801,8 @@ def _normalize_tick_item(
             destinations=destinations,
         )
     else:  # new_knowledge
-        outcome = _tick_normalize_new_knowledge(payload_in, npc_id=npc_id, roster=roster, secret_subjects=secret_subjects)
+        outcome = _tick_normalize_new_knowledge(payload_in, npc_id=npc_id, roster=roster, fact_codes=fact_codes,
+                                                secret_fact_ids=secret_fact_ids, secret_texts=secret_texts)
 
     if outcome is None:
         return None
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index e6ae707..314b11a 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17083,6 +17083,35 @@ entity already knows (the unique index would otherwise abort the SAVEPOINT).
 `discoverable_detail.fact_id` to the fact its knowledge row created; every
 later discovery of that detail attaches to that fact.
 
+## MODELS NAME FACTS BY CODE (TICKET-0097) -- OVERHEARING AND THE TICK (BRIEF-0097-c, no schema change)
+
+**The code list is the one way a model designates a fact.** `fact_refs.
+code_facts(db, fact_ids)` shows `f<n> — <the fact's rendered text>`;
+`CodedFacts.resolve` turns a code back into the fact id, and anything the
+list did not show into None. A model never emits a fact id and never copies
+a key, the same whitelist discipline as the Lore planner's selectors (0085).
+
+**L1 -- overhearing classifies against the speakers' facts.** The list is
+the facts the two possible speakers hold on a non-secret row. Before 0097
+it was every subject of the world, but only a speaker's non-secret row could
+source a proposal (K2 and secret guards), so the effective set is unchanged;
+the list is shorter, and a secret's text never reaches the classifier. A
+bystander now learns the speaker's fact itself -- one fact, several knowers
+-- which is what B3 is for. The prompt's placeholder is `{fact_list}`.
+
+**Z2 -- the tick names what an NPC passes on.** Every line of CE QUE TU SAIS
+carries its code; a `new_knowledge` may set `source_fact`. Resolved, the
+recipient learns that fact, and the Z3 floor marks `secret_derived` exactly
+when it is one of the NPC's secrets. The substring test survives as a second
+net, now on the rendered text of the NPC's secret facts: identical to the
+old test for a legacy fact (its text is its old subject), weaker for a fact
+born after 0097 (a sentence), which is why the code is the primary signal.
+`world_tick.py` rule 5 follows the rename (`secret_fact_ids`, `secret_texts`).
+
+**Prompts.** `apply_ticket_0097_fact_code_prompts.py` appends a version to
+`pt-overhearing-classification` (and full-replaces its variables) and to
+`pt-world-tick`, text imported from `seed_pilot.py`.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/analyzer_seam.py b/tooling/verify/checks/analyzer_seam.py
index 95e535f..d344249 100644
--- a/tooling/verify/checks/analyzer_seam.py
+++ b/tooling/verify/checks/analyzer_seam.py
@@ -457,7 +457,7 @@ def check_fail_closed_and_conversation_id(fixture, engine) -> None:
     import json as _json
 
     original_chat = oc.chat
-    oc.chat = lambda *a, **kw: _json.dumps([{"subject": "a_subject", "speaker": "player"}])
+    oc.chat = lambda *a, **kw: _json.dumps([{"fact": "f1", "speaker": "player"}])
     try:
         with DbSession(engine) as session:
             no_player_attr = AttributionContext(
@@ -509,7 +509,7 @@ def check_fail_closed_and_conversation_id(fixture, engine) -> None:
         with DbSession(engine) as session:
             window_mutations = analyze_window(fixture["conversation_id"], session)
         with DbSession(engine) as session:
-            oc.chat = lambda *a, **kw: _json.dumps([{"subject": "a_subject", "speaker": "npc"}])
+            oc.chat = lambda *a, **kw: _json.dumps([{"fact": "f1", "speaker": "npc"}])
             overhear_mutations = analyze_overhearing(
                 "bonjour", "salut", fixture["conversation_id"], session,
                 npc_entity_id=fixture["npc_id"],
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index 910e82e..45c584b 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -39,6 +39,18 @@ K4 -- the mutation pipeline keys knowledge by fact (C-01, C-02):
       is refused; a leg without content is refused;
    g. window normalization drops a model-emitted `knowledge_change` (N1)
       and strips `subject` / `fact_id` from a model `new_knowledge`.
+K5 -- models name facts by code (C-03, C-04, C-05):
+   a. `code_facts` / `CodedFacts` on the `_CODE_CASES` table;
+   b. overhearing (L1): the classifier's list shows the speaker's
+      non-secret fact and never the text of its secret one; the code the
+      model answers resolves to that fact -- an unaware bystander gets a
+      `new_knowledge` on it, a bystander holding it lower gets a
+      `knowledge_change` on it; an unknown code proposes nothing;
+   c. the tick briefing tags each knowledge line with its fact code, and
+      the tick normalizer (Z2) resolves `source_fact`: a secret source sets
+      `secret_derived` and the `fact_id`, never `is_secret`; an unknown code
+      sets neither; a content containing a secret's text sets
+      `secret_derived`.
 
 Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB.
@@ -61,8 +73,7 @@ MIGRATION_V2_09 = ROOT / "scripts" / "migrate_v2_09_knowledge_identity.py"
 FAILURES: list[str] = []
 
 _SUBJECT_CENSUS: dict[str, int] = {
-    "src/world_engine/analyzer.py": 2,
-    "src/world_engine/analyzer_transcript.py": 10,
+    "src/world_engine/analyzer_transcript.py": 3,
     "src/world_engine/cockpit/crud/_shared.py": 3,
     "src/world_engine/cockpit/crud/knowledge.py": 8,
     "src/world_engine/cockpit/crud/locations.py": 7,
@@ -82,9 +93,6 @@ _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/models/canon_knowledge.py": 1,
     "src/world_engine/scene_format.py": 3,
     "src/world_engine/subject_resolve.py": 4,
-    "src/world_engine/tick.py": 2,
-    "src/world_engine/tick_context.py": 1,
-    "src/world_engine/tick_normalize.py": 2,
     "src/world_engine/writes/facets.py": 1,
     "src/world_engine/writes/knowledge.py": 8,
     "src/world_engine/writes/relations.py": 1,
@@ -407,6 +415,128 @@ def _k4_window() -> None:
         fail(f"K4g a model new_knowledge payload kept a fact name: {payload!r}")
 
 
+def _k5_codes(session, ids) -> None:
+    from world_engine.fact_refs import code_facts
+    from world_engine.writes import create_fact
+
+    one = create_fact(session, world_id=ids["w"], content="Un.", created_by="check", facet="information")
+    two = create_fact(session, world_id=ids["w"], content="Deux.", created_by="check", facet="information")
+    session.flush()
+    coded = code_facts(session, [two.id, one.id, two.id, "no-such-fact"])
+    cases = (
+        (coded.lines, ("f1 — Deux.", "f2 — Un.")), (coded.resolve("f2"), one.id),
+        (coded.resolve("[F1]"), two.id), (coded.resolve(" f1 "), two.id), (coded.resolve("f3"), None),
+        (coded.resolve(1), None), (coded.code_of(one.id), "f2"), (coded.code_of("no-such-fact"), None),
+    )
+    for index, (got, expected) in enumerate(cases):
+        if got != expected:
+            fail(f"K5a case {index}: got {got!r}, expected {expected!r}")
+
+
+def _k5_prompt_head(session, usage: str) -> None:
+    from world_engine.models import PromptTemplate
+    from world_engine.writes import write_prompt_variables, write_prompt_version
+
+    head = PromptTemplate(world_id=None, name=f"check-{usage}", usage=usage, is_active=True)
+    session.add(head)
+    session.flush()
+    write_prompt_variables(session, template_id=head.id, variables=["fact_list", "player_line", "npc_line"])
+    write_prompt_version(session, template_id=head.id, system_prompt="sys",
+                         user_template="{fact_list}|{player_line}|{npc_line}")
+
+
+def _k5_overhearing(session, ids) -> None:
+    import json as _json
+
+    from world_engine import ollama_client
+    from world_engine.analyzer_transcript import AttributionContext, analyze_overheard_lines
+    from world_engine.writes import write_knowledge
+
+    spoken = write_knowledge(session, entity_id=ids["bel"], content="Le pont est tombé.", level="knows")
+    write_knowledge(session, entity_id=ids["bel"], content="Bel vole le trésor.", level="knows",
+                    is_secret=True)
+    write_knowledge(session, entity_id=ids["cid"], fact_id=spoken.fact_id, content="x", level="rumor")
+    _k5_prompt_head(session, "overhearing_classification")
+    session.flush()
+    seen: list[str] = []
+    original = ollama_client.chat
+
+    def stub(messages, **_kw):
+        seen.append(messages[-1]["content"])
+        return _json.dumps(answer)
+
+    ollama_client.chat = stub
+    try:
+        results = []
+        for answer in ([{"fact": "f1", "speaker": "npc"}], [{"fact": "f9", "speaker": "npc"}]):
+            results.append(analyze_overheard_lines(
+                speaker_line="...", listener_line="...", receiver_ids={ids["ana"], ids["cid"]},
+                world_id=ids["w"], location_id=None, existing_keys=(set(), set()),
+                attribution=AttributionContext(default_subject_id=ids["bel"], default_counterparty_id=None),
+                db=session))
+    finally:
+        ollama_client.chat = original
+    if not seen or "f1 — Le pont est tombé." not in seen[0] or "trésor" in seen[0]:
+        fail(f"K5b the classifier list is wrong: {seen[:1]!r}")
+    got = sorted((m.mutation_type, m.payload.get("entity_id"), m.payload.get("fact_id"))
+                 for m in results[0].mutations)
+    expected = sorted([("new_knowledge", ids["ana"], spoken.fact_id),
+                       ("knowledge_change", ids["cid"], spoken.fact_id)])
+    if got != expected or any("subject" in m.payload for m in results[0].mutations):
+        fail(f"K5b overhearing proposals are {got!r}, expected {expected!r}")
+    if results[1].mutations:
+        fail("K5b an unknown code proposed something")
+
+
+def _k5_tick(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Knowledge
+    from world_engine.tick_context import _tick_knowledge_block, tick_fact_codes
+    from world_engine.tick_normalize import _tick_normalize_new_knowledge
+
+    rows = session.exec(
+        select(Knowledge).where(Knowledge.entity_id == ids["bel"]).order_by(Knowledge.id)
+    ).all()
+    codes = tick_fact_codes(ids["bel"], session)
+    secret = next(k for k in rows if k.is_secret)
+    block = _tick_knowledge_block(ids["bel"], session)
+    if [line[:6] for line in block.splitlines()] != [f"- [f{i}]" for i in range(1, len(rows) + 1)]:
+        fail(f"K5c tick briefing lines are not code-tagged: {block!r}")
+    secret_code = codes.code_of(secret.fact_id)
+    cases = (
+        ({"source_fact": secret_code, "is_secret": False}, secret.fact_id, True),
+        ({"source_fact": "f99"}, None, False),
+        ({"content": "Il murmure que Bel vole le trésor."}, None, True),
+    )
+    for payload_in, fact_id, derived in cases:
+        payload_in = {"recipient": "self", "content": "Une nouvelle.", **payload_in}
+        payload, _t = _tick_normalize_new_knowledge(
+            payload_in, npc_id=ids["bel"], roster={}, fact_codes=codes,
+            secret_fact_ids={secret.fact_id}, secret_texts={"bel vole le trésor."})
+        if payload.get("fact_id") != fact_id or payload["secret_derived"] is not derived \
+                or payload["is_secret"] is not False:
+            fail(f"K5c tick normalizer on {payload_in!r} gave {payload!r}")
+
+
+def rule_k5(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity
+
+    with Session(engine) as session:
+        ids = _k4_world(session)
+        cid = Entity(world_id=ids["w"], type="character", name="Cid")
+        session.add(cid)
+        session.flush()
+        session.add(Character(id=cid.id, world_id=ids["w"], character_type="npc"))
+        ids["cid"] = cid.id
+        _k5_codes(session, ids)
+        _k5_overhearing(session, ids)
+        _k5_tick(session, ids)
+        session.rollback()
+
+
 def rule_k4(engine) -> None:
     from sqlmodel import Session
 
@@ -456,6 +586,7 @@ def main() -> int:
     rule_k2()
     rule_k3()
     rule_k4(engine)
+    rule_k5(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
diff --git a/tooling/verify/checks/world_tick.py b/tooling/verify/checks/world_tick.py
index 8453317..8326b24 100644
--- a/tooling/verify/checks/world_tick.py
+++ b/tooling/verify/checks/world_tick.py
@@ -26,11 +26,12 @@ relocation): `_find_applied_duplicate` decomposed into
 `_find_applied_duplicate_tick_sourced` (the tick_id-scoped branch itself)
 plus per-type `_dup_tick_*` helpers — the scan now walks that whole
 decomposed call graph, not just the top `_find_applied_duplicate` frame.
-Rule 5 (Z3 floor + decoupling, BRIEF-0014-b): `tick.py` builds
-`secret_subjects` as a set comprehension over `Knowledge` rows filtered on
-`is_secret`, and compares against it with `in`; within
-`_normalize_tick_item`, `is_secret` never appears on the LEFT side of an
-assignment or dict-literal key whose value references `secret_subjects` or
+Rule 5 (Z3 floor + decoupling, BRIEF-0014-b; retargeted TICKET-0097,
+BRIEF-0097-c, Z2): `tick.py` builds `secret_fact_ids` as a set
+comprehension over `Knowledge` rows filtered on `is_secret`, and the
+normalizer compares against it with `in`; within `_normalize_tick_item`,
+`is_secret` never appears on the LEFT side of an assignment or dict-literal
+key whose value references `secret_fact_ids`, `secret_texts` or
 `secret_derived` — the floor forces provenance only, never confidentiality.
 
 Rule 6 (analyzer boundary, TICKET-0015/BRIEF-0015-a): `analyzer.py`'s
@@ -320,13 +321,13 @@ def check_z3_floor() -> None:
         return
     rel = TICK_FILE.relative_to(ROOT).as_posix()
 
-    # secret_subjects = {... for k in ... if ... is_secret ...} — a SetComp
+    # secret_fact_ids = {... for k in ... if ... is_secret ...} — a SetComp
     # bound to that name, filtered (somewhere in its subtree) on is_secret.
     built = False
     for node in ast.walk(tree):
         if (
             isinstance(node, ast.Assign)
-            and any(isinstance(t, ast.Name) and t.id == "secret_subjects" for t in node.targets)
+            and any(isinstance(t, ast.Name) and t.id == "secret_fact_ids" for t in node.targets)
             and isinstance(node.value, ast.SetComp)
         ):
             has_is_secret = any(
@@ -337,7 +338,7 @@ def check_z3_floor() -> None:
             if has_is_secret:
                 built = True
     if not built:
-        fail(f"{rel}: no `secret_subjects` set comprehension filtered on is_secret found")
+        fail(f"{rel}: no `secret_fact_ids` set comprehension filtered on is_secret found")
 
     # The comparison (`in`/`not in` against secret_subjects) and the
     # decoupling guard both live inside the new_knowledge branch of the
@@ -353,23 +354,23 @@ def check_z3_floor() -> None:
         return
     norm_rel = TICK_NORMALIZE_FILE.relative_to(ROOT).as_posix()
 
-    # A comparison (`in`/`not in`) against secret_subjects somewhere.
+    # A comparison (`in`/`not in`) against secret_fact_ids somewhere.
     compared = False
     for node in ast.walk(norm_tree):
         if isinstance(node, ast.Compare):
             operands = [node.left, *node.comparators]
-            if any(isinstance(o, ast.Name) and o.id == "secret_subjects" for o in operands):
+            if any(isinstance(o, ast.Name) and o.id == "secret_fact_ids" for o in operands):
                 if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
                     compared = True
     if not compared:
-        fail(f"{norm_rel}: no `in`/`not in` comparison against `secret_subjects` found")
+        fail(f"{norm_rel}: no `in`/`not in` comparison against `secret_fact_ids` found")
 
     # Decoupling: is_secret never assigned (Name/Subscript target, or
-    # dict-literal key) from a value referencing secret_subjects or
-    # secret_derived — the floor cannot set confidentiality.
+    # dict-literal key) from a value referencing secret_fact_ids,
+    # secret_texts or secret_derived — the floor cannot set confidentiality.
     def _references_forbidden(value_node: ast.AST) -> bool:
         return any(
-            isinstance(n, ast.Name) and n.id in ("secret_subjects", "secret_derived")
+            isinstance(n, ast.Name) and n.id in ("secret_fact_ids", "secret_texts", "secret_derived")
             for n in ast.walk(value_node)
         )
 
@@ -385,11 +386,11 @@ def check_z3_floor() -> None:
     for node in ast.walk(norm_tree):
         if isinstance(node, ast.Assign):
             if any(_target_is_is_secret(t) for t in node.targets) and _references_forbidden(node.value):
-                fail(f"{norm_rel}:{node.lineno} — is_secret assigned from secret_subjects/secret_derived (floor must not set confidentiality)")
+                fail(f"{norm_rel}:{node.lineno} — is_secret assigned from secret_fact_ids/secret_texts/secret_derived (floor must not set confidentiality)")
         if isinstance(node, ast.Dict):
             for key, value in zip(node.keys, node.values):
                 if isinstance(key, ast.Constant) and key.value == "is_secret" and _references_forbidden(value):
-                    fail(f"{norm_rel}:{getattr(value, 'lineno', node.lineno)} — is_secret dict value references secret_subjects/secret_derived (floor must not set confidentiality)")
+                    fail(f"{norm_rel}:{getattr(value, 'lineno', node.lineno)} — is_secret dict value references secret_fact_ids/secret_texts/secret_derived (floor must not set confidentiality)")
 
 
 def _dict_assign_target(node: ast.AST):
```

## Scope OUT

- Running `apply_ticket_0097_fact_code_prompts.py` on Nia's DB — she runs it after G.
- Coding the window analysis context (N2, rejected).
- Day plan prompt and gates (D).
- Every later brief of the lot: BRIEF-0097-D, BRIEF-0097-E, BRIEF-0097-F, BRIEF-0097-G.

## Invariants to defend

**Secrets are structurally excluded** and **`analyze_overhearing` never sources a proposal from an `is_secret` row** — the list is built from non-secret rows only, so a secret's text never reaches the classifier. **Tick-sourced rows** — shape unchanged. The Z3 floor forces provenance only: `is_secret` is never assigned from it (rule 5). **All templated model calls resolve through `effective_model`** — untouched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `_normalize_tick_item` exceeds 80 lines after the diff (it must be exactly at the cap).

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/world_tick.py` → `PASS`.
- On a temp seeded DB, `apply_ticket_0097_fact_code_prompts.py` run twice prints `unchanged` for both heads each time (a fresh seed already carries the new text).
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

Decision entry `MODELS NAME FACTS BY CODE … (BRIEF-0097-c, no schema change)`.
