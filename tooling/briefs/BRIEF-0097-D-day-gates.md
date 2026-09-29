<!-- slug: day-gates -->
# BRIEF 0097-D — "Day gates name facts"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: C
Commit header for decisions: `(BRIEF-0097-d, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/day_plan.py:81` → `MAX_HELD_SUBJECTS_SHOWN: int = 40`
- `src/world_engine/day_plan.py:337` → `def _anchorable_subjects(character: Character, db: Session) -> frozenset[str]:`
- `src/world_engine/day_plan.py:446` → `def held_subjects_summary(character: Character, db: Session) -> str:`
- `src/world_engine/day_mutations.py:170` → `"subject": req.target_key,`
- `src/world_engine/day_resolve.py:272` → `return template.format(required=verdict.required)`
- `emit_plan(` call sites → `cockpit/day_reconcile_apply.py:156, 200`, `cockpit/routes/day.py:681`

## Facts carried

### R-09 — the day chain
Opened: `day_plan.py:78-560`, `day_mutations.py:100-300`,
`day_resolve.py:253-272`, `cockpit/routes/day.py:44-56, 245-262, 545-690`,
`cockpit/day_reconcile_apply.py:156, 200`, `models/config.py:104-146`,
`writes/goals_agendas.py:590-625`, `tooling/verify/checks/day_plan.py:985-1100`.
Finding: the planner never sees a list of learnable subjects; it guesses a
`target_key`, and `anchor_requirements` drops any key that is not an existing
subject; `emit_plan` has three call sites; `Verdict` has no label field;
`requirement_detail_fr` formats `required`; `agenda_step_requirement.target_key`
is free text (CHECK only NOT NULL for knowledge).
Consequence: D builds the list inside `emit_plan` (every call site gets it),
stores fact ids in `target_key`, adds `Verdict.required_label`.

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

### C-06 — day gates
Produced by: D   Consumed by: nothing later
`learnable_facts(character, db) -> CodedFacts` (anchorable minus held,
ordered by text then id, cap `MAX_LEARNABLE_FACTS_SHOWN = 40`);
`learnable_facts_summary(character_name, learnable) -> str` ("" when empty);
`emit_plan(declaration, character, db, standing_steps_summary="")` returns
knowledge requirements with the code resolved to a fact id, an unknown code
kept as emitted; `Verdict.required_label: Optional[str] = None`, set by
`_eval_knowledge` to the fact's rendered text; `requirement_detail_fr` uses
it. Day proposals carry `fact_id` (+ `fact_label` on a `knowledge_change`).

## Context

The day planner gets what it never had: the coded list of facts the player can learn (D1′a). A gate stores a fact id; a blocked step's lead and a completed step's deepening carry that fact. Nia accepted that gates will hold more often.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: builds `learnable_facts` / `learnable_facts_summary` and resolves codes inside `emit_plan` (every call site); drops `held_subjects_summary` and its route argument; anchors and evaluates gates by fact id; adds `Verdict.required_label`; carries `fact_id` (+ `fact_label`) on the day chain's proposals; shows `g.fact` in `Journee.svelte`; rewords `DAY_PLAN_SYSTEM_PROMPT`'s knowledge requirement; adds `pt-day-plan` to the apply script; retargets `day_plan.py` R26/R28; adds K6.
2. Rebuild the frontend: `cd frontend && npm ci && npm run build`; commit `src/world_engine/cockpit/static/`.
3. Regenerate the index.
4. Message: `feat(day): knowledge gates name facts (BRIEF-0097-d)`.

```diff
diff --git a/frontend/src/journee/Journee.svelte b/frontend/src/journee/Journee.svelte
index b6c758b..c44f550 100644
--- a/frontend/src/journee/Journee.svelte
+++ b/frontend/src/journee/Journee.svelte
@@ -148,7 +148,7 @@
                   <li><span class="badge b-other">ressource</span> {g.status} — {JSON.stringify(g.detail)}</li>
                 {/each}
                 {#each account.gains.knowledge as g}
-                  <li><span class="badge b-other">connaissance</span> {g.subject} → {g.to_level} ({g.status})</li>
+                  <li><span class="badge b-other">connaissance</span> {g.fact} → {g.to_level} ({g.status})</li>
                 {/each}
                 {#each account.gains.relation as g}
                   <li><span class="badge b-other">relation</span> {g.status} — {JSON.stringify(g.detail)}</li>
diff --git a/scripts/apply_ticket_0097_fact_code_prompts.py b/scripts/apply_ticket_0097_fact_code_prompts.py
index ac89de7..10d1ea5 100644
--- a/scripts/apply_ticket_0097_fact_code_prompts.py
+++ b/scripts/apply_ticket_0097_fact_code_prompts.py
@@ -6,6 +6,8 @@ live DB: models name facts by code, never by a free-text subject.
   `npc_line`.
 - `pt-world-tick` (BRIEF-0097-C, Z2): a `new_knowledge` names what the NPC
   passes on by its briefing code (`source_fact`).
+- `pt-day-plan` (BRIEF-0097-D, D1'a): a `knowledge` requirement's
+  `target_key` is the code of a fact from the appended learnable list.
 
 Embeds NO prompt text of its own; it imports each text from
 `scripts/seed_pilot.py` (single source of text). History is sacred: a changed
@@ -57,6 +59,13 @@ _UPDATES: tuple[tuple[str, str, str, list[str], str], ...] = (
         ["tick_context", "interval_label"],
         "TICKET-0097 BRIEF-0097-C -- new_knowledge names its source fact by code (Z2)",
     ),
+    (
+        "pt-day-plan",
+        seed_pilot.DAY_PLAN_SYSTEM_PROMPT,
+        seed_pilot.DAY_PLAN_USER_TEMPLATE,
+        ["character_name", "declaration"],
+        "TICKET-0097 BRIEF-0097-D -- a knowledge gate names its fact by code (D1'a)",
+    ),
 )
 
 
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 4d4092c..c957e77 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -1841,8 +1841,9 @@ EXACTEMENT parmi "physical", "agility", "perception", "composure" ; sinon \
 mets null.
 - Chaque étape a un tableau "requires", vide si l'étape n'a pas de condition \
 préalable. Utilise UNIQUEMENT ces deux formes :
-  - {"type":"knowledge","target_key":"<étiquette courte>"} — le personnage \
-doit déjà savoir quelque chose.
+  - {"type":"knowledge","target_key":"<code d'un fait>"} — le personnage \
+doit déjà savoir ce fait ; le code vient de la liste des faits qu'il peut \
+apprendre, donnée après la déclaration.
   - {"type":"resource","target_key":"<étiquette courte>","threshold":<entier>} \
 — le personnage doit disposer d'au moins ce montant de ressource.
 - Émets au maximum 12 étapes.
diff --git a/src/world_engine/cockpit/routes/day.py b/src/world_engine/cockpit/routes/day.py
index 180d400..bda2b01 100644
--- a/src/world_engine/cockpit/routes/day.py
+++ b/src/world_engine/cockpit/routes/day.py
@@ -50,7 +50,6 @@ from ...day_plan import (
     budget_cut,
     emit_plan,
     evaluate_requirements,
-    held_subjects_summary,
 )
 from ...day_resolve import (
     FactSheet,
@@ -254,7 +253,7 @@ def _account_gains(mutations: list[ProposedMutation]) -> dict:
         elif m.mutation_type == "knowledge_change":
             knowledge.append({
                 "mutation_id": m.id, "status": m.status,
-                "subject": payload.get("subject"), "to_level": payload.get("to_level"),
+                "fact": payload.get("fact_label"), "to_level": payload.get("to_level"),
             })
     return {
         "resource": resource,
@@ -678,10 +677,7 @@ def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
     else:
         day_plans.park_active_plan(character, db)
         try:
-            raw_steps = emit_plan(
-                rendered, character, db,
-                held_subjects_summary=held_subjects_summary(character, db),
-            )
+            raw_steps = emit_plan(rendered, character, db)
         except LlmParseError as exc:
             raise HTTPException(status_code=502, detail=f"plan emission failed: {exc}") from exc
         result = _finalize_plan(world_id, character, pass_play, raw_steps, db)
diff --git a/src/world_engine/day_mutations.py b/src/world_engine/day_mutations.py
index 6796446..dcab7fb 100644
--- a/src/world_engine/day_mutations.py
+++ b/src/world_engine/day_mutations.py
@@ -48,7 +48,7 @@ documented no-op so the dispatch is a literal bijection with the constant
 The armed rendezvous (I1, corrected by BRIEF-0075-e-amendment-1): not
 detected by inventing a marker. `AgendaStepRequirement` already has a
 `knowledge` requirement type (`_eval_knowledge`, `day_plan.py`) gating a
-step on the player ALREADY holding some `Knowledge` subject — meaning that
+step on the player ALREADY holding a `Knowledge` row on its fact — meaning that
 row must already exist for the step to have been attemptable at all. This
 module treats successfully completing such a step as Nia's "a contact
 found, an appointment made": deepening that SAME existing knowledge row to
@@ -68,13 +68,13 @@ approved in `step_order`, or the stale guard rejects the out-of-order one.
 Nothing here works around that — O1 stands.
 
 `new_knowledge` (BRIEF-0078-c, decision D3): a blocked step (BLOCKED_BAND,
-BRIEF-0078-b) proposes a `rumor`-level lead on the exact subject that
+BRIEF-0078-b) proposes a `rumor`-level lead on the exact fact that
 blocked it, so the gate can open through play on a later day. `_emit_new_
 knowledge`'s duplicate guard (`_blocked_lead_already_proposed`) is a
 DELIBERATE duplicate of `cockpit/mutations.py`'s `_knowledge_already_
 applied`, not a call into it: that guard is conversation-scoped and scans
 APPLIED rows, a different question with a different key from "is this
-subject already sitting in the open review queue for this world."
+fact already sitting in the open review queue for this world."
 """
 
 from __future__ import annotations
@@ -84,8 +84,8 @@ from typing import Callable, Optional
 from sqlmodel import Session, select
 
 from .day_resolve import BLOCKED_BAND, StepOutcome, outcome_line
-from .models import AgendaStepRequirement, Character, PassPlay, ProposedMutation
-from .subject_resolve import resolve_subject
+from .models import AgendaStepRequirement, Character, Fact, PassPlay, ProposedMutation
+from .prose_render import fact_text
 
 EMITTED_MUTATION_TYPES: tuple[str, ...] = (
     "knowledge_change", "relation_change", "agenda_step_change", "entity_creation", "new_knowledge",
@@ -160,6 +160,7 @@ def _emit_knowledge_change(
     ).all()
     mutations: list[ProposedMutation] = []
     for req in requirements:
+        label = _fact_label(req.target_key, db)
         mutations.append(ProposedMutation(
             world_id=world_id,
             source_type="pass_play",
@@ -167,7 +168,8 @@ def _emit_knowledge_change(
             mutation_type="knowledge_change",
             payload={
                 "entity_id": character.id,
-                "subject": req.target_key,
+                "fact_id": req.target_key,
+                "fact_label": label,
                 "to_level": _KNOWLEDGE_DEEPEN_LEVEL,
                 "source": "day resolution",
             },
@@ -175,12 +177,19 @@ def _emit_knowledge_change(
             proposed_by="local_ai",
             rationale=(
                 f"step {outcome.step_order} ({outcome.objective}) resolved — "
-                f"deepens knowledge of {req.target_key!r}"
+                f"deepens knowledge of {label!r}"
             ),
         ))
     return mutations
 
 
+def _fact_label(fact_id: Optional[str], db: Session) -> str:
+    """The rendered text of a gate's fact (TICKET-0097: `target_key` is a
+    fact id), or the key itself when no fact carries it."""
+    fact = db.get(Fact, fact_id) if fact_id else None
+    return fact_text(db, fact) if fact is not None else str(fact_id)
+
+
 def _emit_relation_change(
     outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
 ) -> list[ProposedMutation]:
@@ -190,7 +199,7 @@ def _emit_relation_change(
     return []
 
 
-def _blocked_lead_already_proposed(character: Character, subject: str, db: Session) -> bool:
+def _blocked_lead_already_proposed(character: Character, fact_id: str, db: Session) -> bool:
     """Re-resolving the same blocked day before Nia clears the queue must
     not stack identical proposals. Scans the OPEN review queue in Python —
     `payload` is JSON, SQLite cannot filter it in the WHERE clause — bounded
@@ -207,7 +216,7 @@ def _blocked_lead_already_proposed(character: Character, subject: str, db: Sessi
         )
     ).all()
     return any(
-        row.payload.get("entity_id") == character.id and row.payload.get("subject") == subject
+        row.payload.get("entity_id") == character.id and row.payload.get("fact_id") == fact_id
         for row in rows
     )
 
@@ -219,7 +228,9 @@ def _emit_new_knowledge(
     hit. Returns `[]` unless `outcome.band == BLOCKED_BAND` — a successful,
     partial or failed step proposes nothing here. For a blocked outcome,
     walks `outcome.requirement_verdicts` and emits one proposal per unmet
-    `knowledge` verdict, taking the subject from `v.required`. Does NOT
+    `knowledge` verdict, on the fact `v.required` names (TICKET-0097: the
+    lead attaches the character to that very fact, which opens the gate
+    once approved; the fact already carries its participants). Does NOT
     re-query `AgendaStepRequirement`: `Verdict.type` (BRIEF-0078-a) already
     makes the verdicts self-describing, and re-deriving the same fact from a
     second source would be a second authority for it."""
@@ -229,23 +240,21 @@ def _emit_new_knowledge(
     for v in outcome.requirement_verdicts:
         if v.type != "knowledge" or v.met:
             continue
-        subject = v.required
-        if _blocked_lead_already_proposed(character, subject, db):
+        fact_id = v.required
+        if _blocked_lead_already_proposed(character, fact_id, db):
             continue
+        label = _fact_label(fact_id, db)
         payload = {
             "entity_id": character.id,
-            "subject": subject,
+            "fact_id": fact_id,
             "level": _BLOCKED_LEAD_LEVEL,
             "content": (
                 f"Piste entrevue en butant sur « {outcome.objective} » : "
-                f"il reste quelque chose à apprendre au sujet de « {subject} »."
+                f"il reste quelque chose à apprendre au sujet de « {label} »."
             ),
             "source": "journée bloquée",
             "is_secret": False,
         }
-        resolution = resolve_subject(subject, world_id, db)
-        if resolution.verdict == "matched":
-            payload["subject_entity_id"] = resolution.entity_id
         mutations.append(ProposedMutation(
             world_id=world_id,
             source_type="pass_play",
@@ -256,7 +265,7 @@ def _emit_new_knowledge(
             proposed_by="local_ai",
             rationale=(
                 f"step {outcome.step_order} ({outcome.objective}) blocked on unheld "
-                f"knowledge {subject!r} -- proposes a rumor-level lead so the gate can "
+                f"knowledge {label!r} -- proposes a rumor-level lead so the gate can "
                 f"open through play (TICKET-0078, D3)"
             ),
         ))
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 512347c..94dae4a 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -46,6 +46,7 @@ from typing import Callable, Optional
 from sqlmodel import Session, func, select
 
 from . import llm_parse, ollama_client
+from .fact_refs import CodedFacts, code_facts
 from .models import (
     BASE_SKILL_DOMAINS,
     SCHEDULE_PHASES,
@@ -53,6 +54,7 @@ from .models import (
     AgendaStepRequirement,
     Character,
     Entity,
+    Fact,
     Knowledge,
     Ledger,
     PromptTemplate,
@@ -60,6 +62,7 @@ from .models import (
 )
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
+from .prose_render import fact_text, fact_texts
 
 _log = logging.getLogger(__name__)
 
@@ -75,10 +78,10 @@ REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "
 # reported count (logged), not silently dropped.
 MAX_PLAN_STEPS = 12
 
-# BRIEF-0078-a Scope IN item 6: bound on how many held subjects are listed
-# in held_subjects_summary(). Anything beyond is truncated with a reported
-# count (logged), not silently dropped.
-MAX_HELD_SUBJECTS_SHOWN: int = 40
+# BRIEF-0078-a Scope IN item 6, re-aimed by TICKET-0097 (D1'a): bound on how
+# many learnable facts `learnable_facts` codes for the model. Anything beyond
+# is truncated with a reported count (logged), not silently dropped.
+MAX_LEARNABLE_FACTS_SHOWN: int = 40
 
 # Same mild repetition controls as MJ gathering — short, low-drift JSON output.
 DAY_PLAN_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}
@@ -110,6 +113,9 @@ class Verdict:
     current: object
     required: object
     reason: str
+    # TICKET-0097: the player-facing text of `required` when it is an id
+    # (a `knowledge` gate's fact); None when `required` is already readable.
+    required_label: Optional[str] = None
 
 
 @dataclass(frozen=True)
@@ -136,19 +142,24 @@ class BudgetResult:
 # keeps `_EVALUATORS` directly callable without a special case.
 
 def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a fact id (TICKET-0097, D1'a): met iff the character
+    holds a row on that fact."""
     del reachable_ids
     row = db.exec(
         select(Knowledge).where(
-            Knowledge.entity_id == character.id, Knowledge.subject == req.target_key,
+            Knowledge.entity_id == character.id, Knowledge.fact_id == req.target_key,
         )
     ).first()
     met = row is not None
+    fact = db.get(Fact, req.target_key) if req.target_key else None
+    label = fact_text(db, fact) if fact is not None else req.target_key
     reason = (
-        f"knowledge {req.target_key!r} already held" if met
-        else f"prerequisite not met — knowledge {req.target_key!r} not held"
+        f"knowledge {label!r} already held" if met
+        else f"prerequisite not met — knowledge {label!r} not held"
     )
     return Verdict(
         type=req.type, met=met, current=("held" if met else "unheld"), required=req.target_key, reason=reason,
+        required_label=label,
     )
 
 
@@ -318,30 +329,28 @@ def budget_cut(steps: list[EvaluatedStep], budget: int) -> BudgetResult:
 
 # ── requirement anchoring (BRIEF-0078-a, decisions A5(A1b)/B3) ──────────────
 #
-# B3: a gate is legitimate only on a subject that exists to be learned --
+# B3: a gate is legitimate only on a fact that exists to be learned --
 # held in this world by an entity OTHER than the player, on a non-secret
 # row. `is_secret` is excluded because a gate on a secret is both
 # unsatisfiable and a disclosure: the reject message would reveal that the
 # secret exists.
 
-def _held_subjects(character: Character, db: Session) -> frozenset[str]:
-    """The player's own held subjects (A1b) — handed to the emission model
-    via `held_subjects_summary` so it stops proposing a dead gate on
-    something already held. Called at most once per emission (F3)."""
+def _held_facts(character: Character, db: Session) -> frozenset[str]:
+    """The fact ids the player already holds (A1b) — left out of the coded
+    list the emission model sees, so it cannot propose a dead gate."""
     rows = db.exec(
-        select(Knowledge.subject).where(Knowledge.entity_id == character.id).distinct()
+        select(Knowledge.fact_id).where(Knowledge.entity_id == character.id).distinct()
     ).all()
     return frozenset(rows)
 
 
-def _anchorable_subjects(character: Character, db: Session) -> frozenset[str]:
-    """The B3 predicate, and nowhere else: subjects that legitimately anchor
+def _anchorable_facts(character: Character, db: Session) -> frozenset[str]:
+    """The B3 predicate, and nowhere else: fact ids that legitimately anchor
     a `knowledge` requirement — held in this world (`Entity.world_id`), by an
     entity OTHER than the player (`Knowledge.entity_id != character.id`), on
-    a non-secret row (`Knowledge.is_secret == False`). Called at most once
-    per emission (F3)."""
+    a non-secret row (`Knowledge.is_secret == False`)."""
     rows = db.exec(
-        select(Knowledge.subject)
+        select(Knowledge.fact_id)
         .join(Entity, Entity.id == Knowledge.entity_id)
         .where(
             Entity.world_id == character.world_id,
@@ -356,12 +365,13 @@ def _anchorable_subjects(character: Character, db: Session) -> frozenset[str]:
 def anchor_requirements(
     steps: list[PlanStep], character: Character, db: Session,
 ) -> tuple[list[PlanStep], list[dict]]:
-    """Drop every `knowledge` requirement whose `target_key` is not anchored
-    (B3) — REQUIREMENTS are dropped, never steps: the returned step count
-    always equals the input count. A step whose only requirement was dropped
-    becomes an ungated step, the intended outcome, not a degradation.
-    `_anchorable_subjects` is called ONCE for the whole plan (F3)."""
-    anchorable = _anchorable_subjects(character, db)
+    """Drop every `knowledge` requirement whose `target_key` is not an
+    anchored fact id (B3) — REQUIREMENTS are dropped, never steps: the
+    returned step count always equals the input count. A step whose only
+    requirement was dropped becomes an ungated step, the intended outcome,
+    not a degradation. `_anchorable_facts` is called ONCE for the whole plan
+    (F3)."""
+    anchorable = _anchorable_facts(character, db)
     dropped: list[dict] = []
     anchored_steps: list[PlanStep] = []
     for step_index, step in enumerate(steps):
@@ -443,36 +453,52 @@ def _validate_step(raw: object) -> PlanStep:
     return PlanStep(objective=objective.strip(), cost=cost, domain=domain, requirements=requirements)
 
 
-def held_subjects_summary(character: Character, db: Session) -> str:
-    """A short French summary of the subjects `character` already holds
-    (BRIEF-0078-a Scope IN item 6, decision A1b) — appended to `emit_plan`'s
-    user message so the model stops proposing a `knowledge` gate on a
-    subject already held (a dead gate). Positive form only — the gameplay
-    model is abliterated. Returns "" when the player holds no subject at
-    all. Calls `_held_subjects` once."""
-    subjects = sorted(_held_subjects(character, db))
-    if not subjects:
-        return ""
-    truncated = 0
-    if len(subjects) > MAX_HELD_SUBJECTS_SHOWN:
-        truncated = len(subjects) - MAX_HELD_SUBJECTS_SHOWN
-        subjects = subjects[:MAX_HELD_SUBJECTS_SHOWN]
+def learnable_facts(character: Character, db: Session) -> CodedFacts:
+    """D1'a (TICKET-0097): the coded list of facts a `knowledge` gate may
+    name — anchorable (B3) and not already held (A1b), ordered by their
+    rendered text, at most `MAX_LEARNABLE_FACTS_SHOWN` (the rest is counted
+    in a log line, never silently dropped)."""
+    fact_ids = _anchorable_facts(character, db) - _held_facts(character, db)
+    facts = [fact for fact in (db.get(Fact, fid) for fid in fact_ids) if fact is not None]
+    ordered = [fact for _text, fact in sorted(zip(fact_texts(db, facts), facts), key=lambda p: (p[0], p[1].id))]
+    if len(ordered) > MAX_LEARNABLE_FACTS_SHOWN:
         _log.info(
-            "day_plan: held_subjects_summary truncated %d subject(s) beyond MAX_HELD_SUBJECTS_SHOWN=%d",
-            truncated, MAX_HELD_SUBJECTS_SHOWN,
+            "day_plan: learnable_facts truncated %d fact(s) beyond MAX_LEARNABLE_FACTS_SHOWN=%d",
+            len(ordered) - MAX_LEARNABLE_FACTS_SHOWN, MAX_LEARNABLE_FACTS_SHOWN,
         )
-    character_entity = db.get(Entity, character.id)
-    character_name = character_entity.name if character_entity is not None else character.id
-    liste = ", ".join(subjects)
+    return code_facts(db, [fact.id for fact in ordered[:MAX_LEARNABLE_FACTS_SHOWN]])
+
+
+def learnable_facts_summary(character_name: str, learnable: CodedFacts) -> str:
+    """The French text `emit_plan` appends for `learnable` (BRIEF-0078-a's
+    appended-text shape, never a template placeholder). Positive form only —
+    the gameplay model is abliterated. "" when the list is empty."""
+    if not learnable.lines:
+        return ""
+    liste = "\n".join(learnable.lines)
     return (
-        f"Sujets que {character_name} connaît déjà : {liste}.\n"
-        "Une condition « knowledge » porte sur un sujet absent de cette liste."
+        f"Faits que {character_name} peut apprendre (code — fait) :\n{liste}\n"
+        "Une condition « knowledge » donne comme target_key le code d'un de ces faits."
     )
 
 
+def _resolve_knowledge_codes(steps: list[PlanStep], learnable: CodedFacts) -> list[PlanStep]:
+    """Each `knowledge` requirement's code becomes its fact id; a code the
+    list did not show is kept as emitted, for `anchor_requirements` to drop
+    and report."""
+    resolved_steps = []
+    for step in steps:
+        requirements = tuple(
+            replace(req, target_key=learnable.resolve(req.target_key) or req.target_key)
+            if req.type == "knowledge" else req
+            for req in step.requirements
+        )
+        resolved_steps.append(replace(step, requirements=requirements))
+    return resolved_steps
+
+
 def emit_plan(
-    declaration: str, character: Character, db: Session,
-    standing_steps_summary: str = "", held_subjects_summary: str = "",
+    declaration: str, character: Character, db: Session, standing_steps_summary: str = "",
 ) -> list[PlanStep]:
     """ONE model call (F1). Parses through `llm_parse.extract_object`;
     domain/shape validation stays here per M9's contract. A parse failure or
@@ -484,12 +510,10 @@ def emit_plan(
     `day_rewrite.render`'s output, participants already named), never the
     raw `pass_play.declared_action` — every call site passes the rewrite.
     `standing_steps_summary` (BRIEF-0075-f, `modify`'s reconciliation path)
-    and `held_subjects_summary` (BRIEF-0078-a, item 6) are appended verbatim
-    to the user message, never woven into the seeded template text — text a
-    Python pass already built, not a new prompt-template placeholder that a
-    virgin-head-only seed (S2) could never retrofit onto an already-
-    provisioned world. Each defaults to "" (a no-op) so every pre-existing
-    call site is byte-identical."""
+    and the learnable-facts summary (TICKET-0097, D1'a — built here, on every
+    call site) are appended verbatim to the user message, never woven into
+    the seeded template text. Every `knowledge` requirement comes back with
+    its code resolved to a fact id (`_resolve_knowledge_codes`)."""
     template = _load_day_plan_template(character.world_id, db)
     if template is None:
         raise llm_parse.LlmParseError("day_plan: no active prompt_template for usage='day_plan'")
@@ -502,10 +526,12 @@ def emit_plan(
         .replace("{character_name}", character_name)
         .replace("{declaration}", declaration)
     )
+    learnable = learnable_facts(character, db)
+    learnable_summary = learnable_facts_summary(character_name, learnable)
     if standing_steps_summary:
         user_msg += f"\n\n{standing_steps_summary}"
-    if held_subjects_summary:
-        user_msg += f"\n\n{held_subjects_summary}"
+    if learnable_summary:
+        user_msg += f"\n\n{learnable_summary}"
     user_msg += "\n/no_think"
     raw = ollama_client.chat(
         [
@@ -527,7 +553,7 @@ def emit_plan(
         truncated = len(raw_steps) - MAX_PLAN_STEPS
         raw_steps = raw_steps[:MAX_PLAN_STEPS]
 
-    steps = [_validate_step(item) for item in raw_steps]
+    steps = _resolve_knowledge_codes([_validate_step(item) for item in raw_steps], learnable)
     if truncated:
         _log.info("day_plan: emitted plan truncated by %d step(s) beyond MAX_PLAN_STEPS=%d", truncated, MAX_PLAN_STEPS)
     return steps
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 5f9a08b..d65aa4c 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -269,7 +269,7 @@ def requirement_detail_fr(verdict: RequirementVerdict) -> str:
     template = _BLOCKED_DETAIL_FR.get(verdict.type)
     if template is None:
         raise ValueError(f"day_resolve: unknown requirement type {verdict.type!r}")
-    return template.format(required=verdict.required)
+    return template.format(required=getattr(verdict, "required_label", None) or verdict.required)
 
 
 def _append_blocked_step(
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 314b11a..ebe2cc3 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17112,6 +17112,35 @@ born after 0097 (a sentence), which is why the code is the primary signal.
 `pt-overhearing-classification` (and full-replaces its variables) and to
 `pt-world-tick`, text imported from `seed_pilot.py`.
 
+## DAY GATES NAME FACTS (TICKET-0097) -- THE PLANNER CHOOSES FROM WHAT CAN BE LEARNED (BRIEF-0097-d, no schema change)
+
+**D1'a -- the planner is given the list.** Before 0097 the day planner saw
+only the subjects the player already held and guessed a `target_key`;
+`anchor_requirements` kept a gate only when the guess equalled an existing
+subject, so knowledge gates rarely survived. `emit_plan` now appends, on
+every call site (the plan route and both reconciliation paths),
+`learnable_facts`: the facts another entity of the world holds on a
+non-secret row (B3) and the player does not hold (A1b), coded, ordered by
+text, capped at `MAX_LEARNABLE_FACTS_SHOWN` (40, truncation logged). A
+knowledge requirement's code comes back from `emit_plan` as its fact id; an
+unknown code is kept as emitted and dropped by `anchor_requirements`, which
+now compares fact ids. More gates will hold: that is the intent of 0078's
+B3, and Nia accepted the gameplay change.
+
+**The fact id is what is stored.** `agenda_step_requirement.target_key`
+holds the fact id for a `knowledge` row (v2.09 rekeyed the existing ones);
+`_eval_knowledge` compares `Knowledge.fact_id`. A verdict carries the fact's
+text as `required_label`, which `requirement_detail_fr` shows the player,
+never the id.
+
+**The day chain follows.** The completed step's `knowledge_change` and the
+blocked step's `rumor` lead carry `fact_id` (and the change a display
+`fact_label`); the lead no longer resolves an entity, since the fact already
+carries its participants. Journée shows `fact`.
+
+**Prompt.** `pt-day-plan`'s requirement line asks for the code of a fact
+from the appended list (`apply_ticket_0097_fact_code_prompts.py`).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index b9c014b..a124054 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -127,16 +127,18 @@ R24 (new): `day_plan_select.py` contains no `db.add(`, no
 R25: `Verdict`'s field list starts with `type`, and all four `Verdict(`
 constructions in `day_plan.py` pass a `type=` keyword. Zero constructions
 collected is a FAILURE.
-R26: `_anchorable_subjects` exists and its body references all three of
+R26: `_anchorable_facts` exists and its body references all three of
 `world_id`, `is_secret` and a `!=`/`is_not` comparison against
-`character.id`; `_held_subjects` exists. Zero located is a FAILURE.
+`character.id`; `_held_facts` exists. Zero located is a FAILURE.
+(Retargeted TICKET-0097, BRIEF-0097-d: the gate names a fact, not a subject.)
 R27: `anchor_requirements` is called in `cockpit/routes/day.py` and the call
 appears in `_finalize_plan` BEFORE the first reference to
 `evaluate_requirements` in that function (compare `lineno`).
-R28: `emit_plan` appends `held_subjects_summary` with `+=` to the user
-message and `held_subjects_summary` appears in NO seeded prompt constant in
+R28: `emit_plan` appends `learnable_summary` with `+=` to the user
+message and `learnable_facts_summary` appears in NO seeded prompt constant in
 `scripts/seed_pilot.py` — proving it is appended text, not a template
-placeholder.
+placeholder. (Retargeted TICKET-0097, BRIEF-0097-d: the appended text is the
+coded learnable-fact list, D1'a.)
 
 --- BRIEF-0080-b (continue-guard verdict split) ---
 
@@ -986,29 +988,29 @@ def check_verdict_type_field() -> None:
 
 
 def check_anchoring_readers() -> None:
-    """R26 (BRIEF-0078-a item 4): `_anchorable_subjects` exists and its body
-    references all three of `world_id`, `is_secret` and a `!=`/`is_not`
-    comparison against `character.id`; `_held_subjects` exists. Zero located
-    is a FAILURE."""
+    """R26 (BRIEF-0078-a item 4, retargeted BRIEF-0097-d): `_anchorable_facts`
+    exists and its body references all three of `world_id`, `is_secret` and a
+    `!=`/`is_not` comparison against `character.id`; `_held_facts` exists.
+    Zero located is a FAILURE."""
     tree = _parse(DAY_PLAN_FILE)
     if tree is None:
         return
-    held = _find_function(tree, "_held_subjects")
-    anchorable = _find_function(tree, "_anchorable_subjects")
+    held = _find_function(tree, "_held_facts")
+    anchorable = _find_function(tree, "_anchorable_facts")
     if held is None and anchorable is None:
-        fail(f"day_plan R26: neither _held_subjects nor _anchorable_subjects found in {_rel(DAY_PLAN_FILE)} — vacuous")
+        fail(f"day_plan R26: neither _held_facts nor _anchorable_facts found in {_rel(DAY_PLAN_FILE)} — vacuous")
         return
     if held is None:
-        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _held_subjects not found")
+        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _held_facts not found")
     if anchorable is None:
-        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_subjects not found")
+        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_facts not found")
         return
 
     attrs = {node.attr for node in ast.walk(anchorable) if isinstance(node, ast.Attribute)}
     if "world_id" not in attrs:
-        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_subjects does not reference world_id")
+        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_facts does not reference world_id")
     if "is_secret" not in attrs:
-        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_subjects does not reference is_secret")
+        fail(f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_facts does not reference is_secret")
 
     has_player_exclusion = False
     for node in ast.walk(anchorable):
@@ -1022,7 +1024,7 @@ def check_anchoring_readers() -> None:
                 has_player_exclusion = True
     if not has_player_exclusion:
         fail(
-            f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_subjects has no != / is not "
+            f"day_plan R26: {_rel(DAY_PLAN_FILE)}: _anchorable_facts has no != / is not "
             "comparison against character.id"
         )
 
@@ -1060,10 +1062,11 @@ def check_anchor_requirements_wiring() -> None:
 
 
 def check_held_subjects_summary_append() -> None:
-    """R28 (BRIEF-0078-a item 6): `emit_plan` appends `held_subjects_summary`
-    with `+=` to the user message and `held_subjects_summary` appears in NO
-    seeded prompt constant in `scripts/seed_pilot.py` — proving it is
-    appended text, not a template placeholder."""
+    """R28 (BRIEF-0078-a item 6, retargeted BRIEF-0097-d): `emit_plan`
+    appends `learnable_summary` with `+=` to the user message and
+    `learnable_facts_summary` appears in NO seeded prompt constant in
+    `scripts/seed_pilot.py` — proving it is appended text, not a template
+    placeholder."""
     tree = _parse(DAY_PLAN_FILE)
     if tree is None:
         return
@@ -1078,23 +1081,23 @@ def check_held_subjects_summary_append() -> None:
             and isinstance(node.target, ast.Name) and node.target.id == "user_msg"
         ):
             if any(
-                isinstance(sub, ast.Name) and sub.id == "held_subjects_summary"
+                isinstance(sub, ast.Name) and sub.id == "learnable_summary"
                 for sub in ast.walk(node.value)
             ):
                 found = True
     if not found:
-        fail(f"day_plan R28: {_rel(DAY_PLAN_FILE)}: emit_plan does not append held_subjects_summary with +=")
+        fail(f"day_plan R28: {_rel(DAY_PLAN_FILE)}: emit_plan does not append learnable_summary with +=")
 
     seed_tree = _parse(SEED_PILOT_FILE)
     if seed_tree is not None:
         for node in ast.walk(seed_tree):
             if (
                 isinstance(node, ast.Constant) and isinstance(node.value, str)
-                and "held_subjects_summary" in node.value
+                and "learnable_facts_summary" in node.value
             ):
                 fail(
                     f"day_plan R28: {_rel(SEED_PILOT_FILE)}:{node.lineno} — a seeded prompt string "
-                    "contains 'held_subjects_summary' as a template placeholder"
+                    "contains 'learnable_facts_summary' as a template placeholder"
                 )
 
 
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index 45c584b..d29ed6d 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -51,6 +51,16 @@ K5 -- models name facts by code (C-03, C-04, C-05):
       `secret_derived` and the `fact_id`, never `is_secret`; an unknown code
       sets neither; a content containing a secret's text sets
       `secret_derived`.
+K6 -- day gates name facts (D1'a, C-06):
+   a. `learnable_facts` codes exactly the facts another entity of the world
+      holds on a non-secret row and the character does not hold, ordered by
+      text;
+   b. `emit_plan` appends that list, and a `knowledge` requirement's code
+      comes back as its fact id; an unknown code comes back as emitted, and
+      `anchor_requirements` drops it;
+   c. `_eval_knowledge` judges by fact id and carries the fact's text as
+      `required_label`, which `requirement_detail_fr` shows instead of the id;
+   d. a blocked step's lead is a `new_knowledge` on the gate's fact.
 
 Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB.
@@ -79,11 +89,8 @@ _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/cockpit/crud/locations.py": 7,
     "src/world_engine/cockpit/play_discovery.py": 3,
     "src/world_engine/cockpit/routes/creator.py": 2,
-    "src/world_engine/cockpit/routes/day.py": 2,
     "src/world_engine/cockpit/routes/npc_agent.py": 2,
     "src/world_engine/context.py": 4,
-    "src/world_engine/day_mutations.py": 4,
-    "src/world_engine/day_plan.py": 3,
     "src/world_engine/entity_author.py": 4,
     "src/world_engine/knowledge_resolve.py": 1,
     "src/world_engine/link_author.py": 5,
@@ -537,6 +544,99 @@ def rule_k5(engine) -> None:
         session.rollback()
 
 
+def _k6_world(session, ids) -> dict:
+    from world_engine.models import Character, Entity, PromptTemplate
+    from world_engine.writes import write_knowledge, write_prompt_variables, write_prompt_version
+
+    pc = Entity(world_id=ids["w"], type="character", name="Pia")
+    session.add(pc)
+    session.flush()
+    session.add(Character(id=pc.id, world_id=ids["w"], character_type="player"))
+    facts = {}
+    for key, text, holder, secret in (
+        ("port", "Le port ferme.", "ana", False), ("mer", "La mer monte.", "bel", False),
+        ("vol", "Bel vole.", "bel", True), ("held", "Il pleut.", "ana", False),
+        ("far", "Ailleurs.", "out", False),
+    ):
+        facts[key] = write_knowledge(session, entity_id=ids[holder], content=text, level="knows",
+                                     is_secret=secret).fact_id
+    write_knowledge(session, entity_id=pc.id, fact_id=facts["held"], content="Il pleut.", level="knows")
+    head = PromptTemplate(world_id=None, name="check-day-plan", usage="day_plan", is_active=True)
+    session.add(head)
+    session.flush()
+    write_prompt_variables(session, template_id=head.id, variables=["character_name", "declaration"])
+    write_prompt_version(session, template_id=head.id, system_prompt="sys",
+                         user_template="{character_name}: {declaration}")
+    session.flush()
+    return {"pc": pc.id, **facts}
+
+
+def _k6_plan(session, day) -> None:
+    import json as _json
+
+    from world_engine import ollama_client
+    from world_engine.day_plan import anchor_requirements, emit_plan, learnable_facts
+    from world_engine.models import Character
+
+    character = session.get(Character, day["pc"])
+    learnable = learnable_facts(character, session)
+    if learnable.lines != ("f1 — La mer monte.", "f2 — Le port ferme."):
+        fail(f"K6a learnable facts are {learnable.lines!r}")
+    sent: list[str] = []
+    plan = {"title": "t", "steps": [{"objective": "o", "cost": 1, "domain": None, "requires": [
+        {"type": "knowledge", "target_key": "f2"}, {"type": "knowledge", "target_key": "f9"}]}]}
+
+    def stub(messages, **_kw):
+        sent.append(messages[-1]["content"])
+        return _json.dumps(plan)
+
+    original = ollama_client.chat
+    ollama_client.chat = stub
+    try:
+        steps = emit_plan("déclaration", character, session)
+    finally:
+        ollama_client.chat = original
+    keys = [req.target_key for req in steps[0].requirements]
+    if not sent or "f2 — Le port ferme." not in sent[0] or keys != [day["port"], "f9"]:
+        fail(f"K6b emit_plan sent {sent[:1]!r} and returned keys {keys!r}")
+    anchored, dropped = anchor_requirements(steps, character, session)
+    if [r.target_key for r in anchored[0].requirements] != [day["port"]] \
+            or [d["target_key"] for d in dropped] != ["f9"]:
+        fail(f"K6b anchoring kept {anchored[0].requirements!r}, dropped {dropped!r}")
+
+
+def _k6_verdicts(session, day) -> None:
+    from types import SimpleNamespace
+
+    from world_engine.day_mutations import _emit_new_knowledge
+    from world_engine.day_plan import RequirementSpec, _eval_knowledge
+    from world_engine.day_resolve import BLOCKED_BAND, requirement_detail_fr
+    from world_engine.models import Character
+
+    character = session.get(Character, day["pc"])
+    held = _eval_knowledge(RequirementSpec(type="knowledge", target_key=day["held"]), character, session, None)
+    unheld = _eval_knowledge(RequirementSpec(type="knowledge", target_key=day["port"]), character, session, None)
+    detail = requirement_detail_fr(unheld)
+    if not held.met or unheld.met or unheld.required_label != "Le port ferme." \
+            or "Le port ferme." not in detail or day["port"] in detail:
+        fail(f"K6c verdicts: held={held!r} unheld={unheld!r} detail={detail!r}")
+    outcome = SimpleNamespace(band=BLOCKED_BAND, requirement_verdicts=(unheld,), objective="o", step_order=1)
+    leads = _emit_new_knowledge(outcome, SimpleNamespace(id="pp"), character, character.world_id, session)
+    if [m.payload.get("fact_id") for m in leads] != [day["port"]] or any("subject" in m.payload for m in leads):
+        fail(f"K6d blocked lead payloads are {[m.payload for m in leads]!r}")
+
+
+def rule_k6(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _k4_world(session)
+        day = _k6_world(session, ids)
+        _k6_plan(session, day)
+        _k6_verdicts(session, day)
+        session.rollback()
+
+
 def rule_k4(engine) -> None:
     from sqlmodel import Session
 
@@ -587,6 +687,7 @@ def main() -> int:
     rule_k3()
     rule_k4(engine)
     rule_k5(engine)
+    rule_k6(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
```

## Scope OUT

- The N6a day-chain widening (Y6b, its own ticket).
- Gates on resources, relations or reachability — untouched.
- Showing the learnable list anywhere in the UI.
- Every later brief of the lot: BRIEF-0097-E, BRIEF-0097-F, BRIEF-0097-G.

## Invariants to defend

**Secrets are structurally excluded** — the list is built from non-secret rows of other entities only (B3); a gate on a secret stays impossible. **The positional wall** — untouched. No English machine text reaches a player: `requirement_detail_fr` shows the fact's text, never the id.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A seeded prompt string contains `learnable_facts_summary` (R28 forbids it).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `knowledge_identity.py` K3 fails only on counts, with every reported file named in this brief's diff: re-run the census (see Done means) and report the table.
- `frontend_build_fresh.py` fails after the build only on `.build-manifest.json` timestamps: rebuild once and commit what the build writes.

REPORT-ONLY:
- Any other file still naming `subject` in a comment or docstring.
- Timing of the corpus run.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` of the commit lists exactly the files of the embedded diff, plus `src/world_engine/cockpit/static/` (rebuilt), plus `tooling/standards/DECISIONS_INDEX.md` (regenerated).
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/knowledge_identity.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/day_plan.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/frontend_build_fresh.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

Decision entry `DAY GATES NAME FACTS … (BRIEF-0097-d, no schema change)`.
