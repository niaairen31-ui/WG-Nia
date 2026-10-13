<!-- slug: review-recording -->
# BRIEF 0115-B — "Every review path records its round -- writes/mutation_reviews.py, review_diff.py, review_verdict.py (no schema change)"

Lot: LOT-0115-creator-dashboard.md (authoritative on conflict)
Depends on: BRIEF-0115-A (C-01)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after the previous brief of this lot).

- `src/world_engine/cockpit/routes/mutations.py` -> `def reject_mutation(`, `def _approve_apply_edited_payload(mut: ProposedMutation, body: "ApproveBody") -> None:`, `def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session) -> Optional[dict]:`, `def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime) -> dict:`, `def approve_mutation(`, `def _batch_approve(`, `def _batch_reject(`; no `record_review`
- `src/world_engine/cockpit/skill_progress.py` -> `result = _approve_apply_and_commit(mut, db, datetime.now(UTC))`
- `src/world_engine/conditions.py` -> `def for_step(`, `def evaluate(`, `def read_condition(`; `src/world_engine/day_plan.py` -> `def plan_bindings(agenda_id: Optional[str], character: Character, db: Session) -> Bindings:`
- `MutationReview`, `MutationReviewChange` importable from `world_engine.models` (BRIEF-0115-A)
- No `src/world_engine/review_diff.py`, `review_verdict.py`, `writes/mutation_reviews.py`, `tooling/verify/checks/review_recording.py`.

## Facts carried

### R-01 — approving overwrites the producer's payload [M]
Opened: `routes/mutations.py:539`, `:631`; `frontend/src/creation/eventDraft.svelte.js:155` (`payloadFromDraft` writes every key of its form: `description: null`, a participant's `role_id`, `role`, `sorte_name`, `secret: null`).
Consequence: an empty value equals an absent one; a participant pairs by role NAME (the tick writes a role's name, the card adds its id).

### R-02 — the four review paths and their exits [M]
Opened: `routes/mutations.py` -- `reject_mutation` :508 (one commit), `_approve_entity_creation_shortcircuit` :552 (two exits, both `approved`), `_approve_apply_and_commit` :597 (applied, or `approved` with `[apply error]`), `_batch_approve` :678 (same two, per row), `_batch_reject` :730; `cockpit/skill_progress.py:101` (the auto-applied roll, INV-15, calls `_approve_apply_and_commit`).
Consequence: eight `record_review` calls, one per exit; `call` optional, None for the roll.

### R-03 — a step's condition and its bindings [M]
Opened: `conditions.py` (`for_step` :152, `evaluate` :397, `read_condition` :512); `day_plan.py:130` (`plan_bindings`: a `Character` doer); `cockpit/mutations.py:790` (`complete` | `fail`, the step must be active -- the apply moves it).
Consequence: the verdict is judged before the apply; `fail` reads `failure`; a faction owner is `not_judged`.

## Contracts

### C-01 — v2.27
Produced by: BRIEF-0115-A   Consumed by: this brief
(see the lot) `mutation_review`, `mutation_review_change`, `original_payload`, the five tuples.

### C-02 — recording a review
Produced by: BRIEF-0115-B   Consumed by: D
`writes.mutation_reviews.ReviewCall(action, via, before_payload, step_verdict=None)`; `record_review(db, mutation, call) -> MutationReview` -- after the status is set, before the commit; never commits; the round is 1 + the proposal's rounds; changes only on a unit approve; `original_payload` written on the first edited round only. `review_diff.diff_payloads(before, after) -> list[PayloadChange(path, field, kind, before_value, after_value)]`, `field_of(path)`, `IGNORED_KEYS`, `NATURAL_KEYS`, `ORDERED_LISTS`. `review_verdict.step_verdict(db, mutation_type, payload) -> str | None`. `_approve_apply_and_commit(mut, db, now, call=None)`.

## Context

Every review call becomes a round with what changed and, for a step change, its condition's verdict. Nothing about how a proposal is applied changes: the rows are written in each path's own transaction, right before its commit.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `review_diff.py` (new): the diff, H1a's natural keys;
   - `review_verdict.py` (new): a step's verdict before the apply;
   - `writes/mutation_reviews.py` (new, C-02): the one writer;
   - `cockpit/routes/mutations.py`: a `ReviewCall` built before anything is applied in each of the four paths, `record_review` at each of the eight exits; `_approve_apply_and_commit`'s `call` optional;
   - creates check `review_recording.py` (RD1-RD5); appends the decision entry above the footer.
   The files it touches, exactly:
   - src/world_engine/cockpit/routes/mutations.py
   - src/world_engine/review_diff.py
   - src/world_engine/review_verdict.py
   - src/world_engine/writes/mutation_reviews.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/review_recording.py

````diff
diff --git a/src/world_engine/cockpit/routes/mutations.py b/src/world_engine/cockpit/routes/mutations.py
index 4ae3c97..dd71017 100644
--- a/src/world_engine/cockpit/routes/mutations.py
+++ b/src/world_engine/cockpit/routes/mutations.py
@@ -10,6 +10,7 @@ to avoid a circular import, same pattern as before the split.
 
 from __future__ import annotations
 
+import copy
 import enum
 import json
 import logging
@@ -82,6 +83,7 @@ from ...models import (
     WorldLaw,
 )
 from ...resolution import resolve_physical
+from ...review_verdict import step_verdict
 from ...writes import (
     KNOWLEDGE_LEVELS,
     delete_world_cascade as _delete_world_cascade,
@@ -90,6 +92,7 @@ from ...writes import (
     write_relation,
     write_world_laws,
 )
+from ...writes.mutation_reviews import ReviewCall, record_review
 from .. import crud as _crud
 
 router = APIRouter()
@@ -519,11 +522,14 @@ def reject_mutation(
             detail="Cannot reject a mutation that has already been applied to canon.",
         )
 
+    call = ReviewCall("reject", "unit", copy.deepcopy(mut.payload),
+                      step_verdict(db, mut.mutation_type, mut.payload))
     mut.status = "rejected"
     mut.reviewed_at = datetime.now(UTC)
     if body.creator_notes:
         mut.creator_notes = body.creator_notes
     db.add(mut)
+    record_review(db, mut, call)
     db.commit()
     db.refresh(mut)
     return _mutation_dict(mut)
@@ -549,7 +555,7 @@ def _approve_apply_edited_payload(mut: ProposedMutation, body: "ApproveBody") ->
         mut.creator_notes = body.creator_notes
 
 
-def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session) -> Optional[dict]:
+def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session, call: ReviewCall) -> Optional[dict]:
     """entity_creation short-circuit (TICKET-0019, BRIEF-0019-a): approval
     PARKS the germ — it never reaches _apply_mutation, never a savepoint,
     never the "[apply error]" framing (RECON F3): I2 forbids any synchronous
@@ -574,6 +580,7 @@ def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session) ->
             mut.creator_notes, f"une entité active porte déjà ce nom : {name!r}"
         )
         db.add(mut)
+        record_review(db, mut, call)
         db.commit()
         db.refresh(mut)
         return {
@@ -585,6 +592,7 @@ def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session) ->
     mut.status = "approved"
     mut.creator_notes = _append_note(mut.creator_notes, "en attente de réalisation — onglet Création")
     db.add(mut)
+    record_review(db, mut, call)
     db.commit()
     db.refresh(mut)
     return {
@@ -594,9 +602,12 @@ def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session) ->
     }
 
 
-def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime) -> dict:
+def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime,
+                              call: Optional[ReviewCall] = None) -> dict:
     """SAVEPOINT: canon writes are rolled back on failure; the outer
-    transaction (mutation row update) stays live either way."""
+    transaction (mutation row update) stays live either way. `call` is the
+    creator's review (TICKET-0115), recorded with the status left; None for
+    an auto-applied `skill_progress` (INV-15), which nobody reviewed."""
     try:
         with db.begin_nested():
             error = _apply_mutation(mut, db)
@@ -607,6 +618,8 @@ def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime)
         mut.status = "applied"
         mut.applied_at = now
         db.add(mut)
+        if call is not None:
+            record_review(db, mut, call)
         db.commit()
         db.refresh(mut)
         return {"status": "applied", "mutation": _mutation_dict(mut)}
@@ -618,6 +631,8 @@ def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime)
         prior = mut.creator_notes or ""
         mut.creator_notes = f"{prior}\n[apply error] {error_msg}".strip()
         db.add(mut)
+        if call is not None:
+            record_review(db, mut, call)
         db.commit()
         db.refresh(mut)
         return {
@@ -650,16 +665,19 @@ def approve_mutation(
     if mut.status == "applied":
         return {"status": "already_applied", "mutation": _mutation_dict(mut)}
 
+    before = copy.deepcopy(mut.payload)
     _approve_apply_edited_payload(mut, body)
+    # TICKET-0115 (C1): the step's condition is judged before anything applies.
+    call = ReviewCall("approve", "unit", before, step_verdict(db, mut.mutation_type, mut.payload))
 
     now = datetime.now(UTC)
     mut.reviewed_at = now
 
-    shortcircuit = _approve_entity_creation_shortcircuit(mut, db)
+    shortcircuit = _approve_entity_creation_shortcircuit(mut, db, call)
     if shortcircuit is not None:
         return shortcircuit
 
-    return _approve_apply_and_commit(mut, db, now)
+    return _approve_apply_and_commit(mut, db, now, call)
 
 
 _BATCH_REVIEW_MARKER = "batch-review"
@@ -693,6 +711,8 @@ def _batch_approve(mutation_ids: list[str], now: datetime, db: Session) -> dict:
             continue
 
         mut.reviewed_at = now
+        call = ReviewCall("approve", "batch", copy.deepcopy(mut.payload),
+                          step_verdict(db, mut.mutation_type, mut.payload))
 
         try:
             with db.begin_nested():
@@ -704,6 +724,7 @@ def _batch_approve(mutation_ids: list[str], now: datetime, db: Session) -> dict:
             mut.applied_at = now
             mut.creator_notes = _append_note(mut.creator_notes, _BATCH_REVIEW_MARKER)
             db.add(mut)
+            record_review(db, mut, call)
             db.commit()
             applied += 1
 
@@ -715,6 +736,7 @@ def _batch_approve(mutation_ids: list[str], now: datetime, db: Session) -> dict:
                 _BATCH_REVIEW_MARKER,
             )
             db.add(mut)
+            record_review(db, mut, call)
             db.commit()
             needs_attention += 1
 
@@ -738,10 +760,13 @@ def _batch_reject(mutation_ids: list[str], now: datetime, db: Session) -> dict:
             skipped += 1
             continue
 
+        call = ReviewCall("reject", "batch", copy.deepcopy(mut.payload),
+                          step_verdict(db, mut.mutation_type, mut.payload))
         mut.status = "rejected"
         mut.reviewed_at = now
         mut.creator_notes = _append_note(mut.creator_notes, _BATCH_REVIEW_MARKER)
         db.add(mut)
+        record_review(db, mut, call)
         db.commit()
         rejected += 1
 
diff --git a/src/world_engine/review_diff.py b/src/world_engine/review_diff.py
new file mode 100644
index 0000000..65cd549
--- /dev/null
+++ b/src/world_engine/review_diff.py
@@ -0,0 +1,172 @@
+"""What the creator changed in a proposal before approving it: two payloads compared, value by value (TICKET-0115, BRIEF-0115-B; decision H1a of the conditions series' dashboard).
+
+Pure: no database, no model. `diff_payloads(before, after)` walks the
+payload stored before the review call and the one approved, and returns one
+`PayloadChange` per value that differs -- the rows
+`writes/mutation_reviews.py` records in `mutation_review_change`.
+
+- A **path** names the value: keys joined by `.`, a list element in
+  brackets -- `title`, `participants[Cible].entity_id`, `steps[2]`,
+  `involved_entities["e-1"]`. Its **field** is the same path without what
+  the brackets hold (`participants[].entity_id`): what the dashboard groups
+  by.
+- **Empty is absent**: `None`, `""`, `[]` and `{}` equal a missing key. The
+  review card writes every key of its form (`description: null`, a
+  participant's `secret: null`); none of that is a change.
+- **Never compared**: `IGNORED_KEYS` -- `type_name` (the card's label for
+  `type_id`, which is compared) and what an apply writes into a payload
+  (`applied_changes`, `created_entity_id`).
+- **A list pairs its elements** by `NATURAL_KEYS` (`participants` by role name -- the tick names a role, the card adds its id --,
+  `state_changes` by entity and state, `scopes` by kind and target, a type's
+  `roles` by name, completion `effects` by type); two elements sharing a key
+  are told apart by their order (`[Chasseur#2]`). A list of plain values is a
+  set (`involved_entities`, a role's `entity_types`) except `ORDERED_LISTS`
+  (`steps`), paired by position from 1; a list of objects with no natural
+  key is paired by position too (`[#1]`).
+- **Kinds**: `added` (absent before), `removed` (absent after), `changed`.
+  `before_value` / `after_value` hold a plain value as JSON text, and None
+  for a whole object or list added, removed or replaced by another kind.
+"""
+
+from __future__ import annotations
+
+import json
+import re
+from dataclasses import dataclass
+from typing import Any, Optional
+
+IGNORED_KEYS: frozenset[str] = frozenset({"type_name", "applied_changes", "created_entity_id"})
+NATURAL_KEYS: dict[str, tuple[tuple[str, ...], ...]] = {
+    "participants": (("role", "role_id"),),
+    "state_changes": (("entity_id",), ("attribute",)),
+    "scopes": (("scope_type",), ("scope_id",)),
+    "roles": (("name",),),
+    "effects": (("type",),),
+}
+ORDERED_LISTS: frozenset[str] = frozenset({"steps"})
+_BRACKETS = re.compile(r"\[[^\]]*\]")
+
+
+@dataclass(frozen=True)
+class PayloadChange:
+    path: str
+    field: str
+    kind: str  # added | removed | changed
+    before_value: Optional[str] = None
+    after_value: Optional[str] = None
+
+
+def field_of(path: str) -> str:
+    """The path without what its brackets hold."""
+    return _BRACKETS.sub("[]", path)
+
+
+def _empty(value: Any) -> bool:
+    return value is None or value == "" or value == [] or value == {}
+
+
+def _scalar(value: Any) -> bool:
+    return not isinstance(value, (dict, list))
+
+
+def _text(value: Any) -> Optional[str]:
+    return json.dumps(value, ensure_ascii=False, sort_keys=True) if _scalar(value) else None
+
+
+def _same(a: Any, b: Any) -> bool:
+    if isinstance(a, bool) != isinstance(b, bool):
+        return False
+    return a == b
+
+
+def _label(value: Any) -> str:
+    return str(value).replace("]", ")").replace("[", "(")
+
+
+def _join(prefix: str, key: str) -> str:
+    return f"{prefix}.{key}" if prefix else key
+
+
+def _change(path: str, kind: str, before: Any = None, after: Any = None) -> PayloadChange:
+    return PayloadChange(path=path, field=field_of(path), kind=kind,
+                         before_value=None if kind == "added" else _text(before),
+                         after_value=None if kind == "removed" else _text(after))
+
+
+def _natural_key(item: dict, parts: tuple[tuple[str, ...], ...]) -> str:
+    chosen = []
+    for alternatives in parts:
+        value = next((item.get(k) for k in alternatives if not _empty(item.get(k))), "")
+        chosen.append(_label(value))
+    return "|".join(chosen)
+
+
+def _keyed(items: list, name: str) -> dict[str, Any]:
+    """`name`'s elements by their label: a natural key, a position, or a
+    plain value."""
+    parts = NATURAL_KEYS.get(name)
+    if name in ORDERED_LISTS:
+        return {f"#{i}" if not _scalar(item) else str(i): item for i, item in enumerate(items, start=1)}
+    if all(_scalar(item) for item in items):
+        return {json.dumps(item, ensure_ascii=False, sort_keys=True): item for item in items}
+    out: dict[str, Any] = {}
+    seen: dict[str, int] = {}
+    for position, item in enumerate(items, start=1):
+        if parts is not None and isinstance(item, dict):
+            base = _natural_key(item, parts)
+            seen[base] = seen.get(base, 0) + 1
+            label = base if seen[base] == 1 else f"{base}#{seen[base]}"
+        else:
+            label = f"#{position}"
+        out[label] = item
+    return out
+
+
+def _walk_object(before: dict, after: dict, path: str, out: list[PayloadChange]) -> None:
+    for key in sorted(set(before) | set(after)):
+        if key not in IGNORED_KEYS:
+            _walk(before.get(key), after.get(key), _join(path, key), key, out)
+
+
+def _walk(before: Any, after: Any, path: str, name: str, out: list[PayloadChange]) -> None:
+    if _empty(before) and _empty(after):
+        return
+    if _empty(before):
+        out.append(_change(path, "added", after=after))
+        return
+    if _empty(after):
+        out.append(_change(path, "removed", before=before))
+        return
+    if isinstance(before, dict) and isinstance(after, dict):
+        _walk_object(before, after, path, out)
+        return
+    if isinstance(before, list) and isinstance(after, list):
+        if all(_scalar(i) for i in before + after) and name not in ORDERED_LISTS:
+            old, new = _keyed(before, name), _keyed(after, name)
+            for label in sorted(set(old) | set(new)):
+                if label not in new:
+                    out.append(_change(f"{path}[{_label(label)}]", "removed", before=old[label]))
+                elif label not in old:
+                    out.append(_change(f"{path}[{_label(label)}]", "added", after=new[label]))
+            return
+        old, new = _keyed(before, name), _keyed(after, name)
+        for label in sorted(set(old) | set(new), key=lambda k: (k not in old, k)):
+            _walk(old.get(label), new.get(label), f"{path}[{label}]", name, out)
+        return
+    if _scalar(before) and _scalar(after):
+        if not _same(before, after):
+            out.append(_change(path, "changed", before, after))
+        return
+    out.append(_change(path, "changed", before, after))
+
+
+def diff_payloads(before: Any, after: Any) -> list[PayloadChange]:
+    """Every value that differs between `before` and `after`, in path order
+    within each object. A payload that is not an object differs as a whole
+    (path `$`)."""
+    out: list[PayloadChange] = []
+    if isinstance(before, dict) and isinstance(after, dict):
+        _walk_object(before, after, "", out)
+    elif not (_empty(before) and _empty(after)) and not _same(before, after):
+        out.append(_change("$", "changed", before, after))
+    return out
diff --git a/src/world_engine/review_verdict.py b/src/world_engine/review_verdict.py
new file mode 100644
index 0000000..6e6d67b
--- /dev/null
+++ b/src/world_engine/review_verdict.py
@@ -0,0 +1,55 @@
+"""What a step's own condition said when the creator reviewed its change (TICKET-0115, BRIEF-0115-B; decision C1 of the conditions series' dashboard, for M2).
+
+`step_verdict(db, mutation_type, payload)` is read by the four review paths
+of `cockpit/routes/mutations.py` BEFORE anything is applied, so the verdict
+is the canon the creator was looking at:
+
+- not an `agenda_step_change`: None (the column stays NULL);
+- `complete` is judged on the step's `completion` condition, `fail` on its
+  `failure` condition (M1 and H1: shown, never acting), with the bindings
+  Journée uses (`day_plan.plan_bindings`, `conditions.for_step`): `met`,
+  `unmet` or `unknown` (R1);
+- `none`: the step has no such condition;
+- `not_judged`: no step id, no such step, an action that is neither, an
+  agenda whose owner is not a character (a faction's agenda has no one to
+  bind as `doer`), or a stored condition that cannot be read.
+
+Reads only.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional
+
+from sqlmodel import Session
+
+from .conditions import evaluate, for_step, read_condition
+from .day_plan import plan_bindings
+from .models import Agenda, AgendaStep, Character
+
+ROLE_BY_ACTION: dict[str, str] = {"complete": "completion", "fail": "failure"}
+NOT_JUDGED = "not_judged"
+NO_CONDITION = "none"
+
+
+def step_verdict(db: Session, mutation_type: str, payload: Any) -> Optional[str]:
+    """The verdict to record with a review (see the module docstring)."""
+    if mutation_type != "agenda_step_change":
+        return None
+    payload = payload if isinstance(payload, dict) else {}
+    role = ROLE_BY_ACTION.get(payload.get("action"))
+    step = db.get(AgendaStep, payload["step_id"]) if isinstance(payload.get("step_id"), str) else None
+    if role is None or step is None:
+        return NOT_JUDGED
+    agenda = db.get(Agenda, step.agenda_id)
+    character = db.get(Character, agenda.owner_entity_id) if agenda is not None else None
+    if character is None:
+        return NOT_JUDGED
+    try:
+        tree = read_condition(db, role=role, agenda_step_id=step.id)
+    except ValueError:
+        return NOT_JUDGED
+    if tree is None:
+        return NO_CONDITION
+    verdict = evaluate(tree, for_step(plan_bindings(agenda.id, character, db), step), db)
+    return verdict.state if verdict is not None else NO_CONDITION
diff --git a/src/world_engine/writes/mutation_reviews.py b/src/world_engine/writes/mutation_reviews.py
new file mode 100644
index 0000000..d93bc29
--- /dev/null
+++ b/src/world_engine/writes/mutation_reviews.py
@@ -0,0 +1,78 @@
+"""The creator's review of a proposal, recorded round by round -- the one writer of `mutation_review`, `mutation_review_change` and `proposed_mutation.original_payload` (TICKET-0115, BRIEF-0115-B; decisions A3, C1 and H1a of the conditions series' dashboard).
+
+The four review paths of `cockpit/routes/mutations.py` (approve, reject,
+and both in batch) call `record_review` once per proposal they move, after
+setting its status and before their commit, with a `ReviewCall` built
+before anything was applied:
+
+- `action` `approve` | `reject`, `via` `unit` | `batch`;
+- `before_payload`: the payload stored before the call -- a copy taken
+  before an edited one replaced it;
+- `step_verdict`: `review_verdict.step_verdict`, judged before the apply.
+
+`record_review` writes the next round (1 + the proposal's rounds so far),
+its status after the call, and -- for a unit approve only, the one call
+that carries a payload -- every value the creator changed
+(`review_diff.diff_payloads`), `edited` saying whether there was any. The
+first edited round also keeps the producer's payload in `original_payload`,
+never written again. Nothing here commits or deletes; the caller owns the
+transaction.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any, Optional
+
+from sqlalchemy import func
+from sqlmodel import Session, select
+
+from ..models import (
+    REVIEW_ACTIONS,
+    REVIEW_STATUSES,
+    REVIEW_VIAS,
+    STEP_VERDICTS,
+    MutationReview,
+    MutationReviewChange,
+    ProposedMutation,
+)
+from ..review_diff import diff_payloads
+
+
+@dataclass(frozen=True)
+class ReviewCall:
+    action: str
+    via: str
+    before_payload: Any
+    step_verdict: Optional[str] = None
+
+
+def record_review(db: Session, mutation: ProposedMutation, call: ReviewCall) -> MutationReview:
+    """Write one round of `mutation`'s review (see the module docstring).
+    `ValueError`, nothing written, on an action, via, status or verdict
+    outside its tuple, or a reject that did not leave `rejected`."""
+    if call.action not in REVIEW_ACTIONS or call.via not in REVIEW_VIAS:
+        raise ValueError(f"mutation_review: unknown action or via {call.action!r}/{call.via!r}")
+    if mutation.status not in REVIEW_STATUSES or (call.action == "reject") != (mutation.status == "rejected"):
+        raise ValueError(f"mutation_review: a {call.action} cannot leave the status {mutation.status!r}")
+    if call.step_verdict is not None and call.step_verdict not in STEP_VERDICTS:
+        raise ValueError(f"mutation_review: unknown step verdict {call.step_verdict!r}")
+    changes = diff_payloads(call.before_payload, mutation.payload) \
+        if (call.action, call.via) == ("approve", "unit") else []
+    rounds = db.exec(select(func.count()).select_from(MutationReview)
+                     .where(MutationReview.mutation_id == mutation.id)).one()
+    review = MutationReview(
+        world_id=mutation.world_id, mutation_id=mutation.id, round=rounds + 1, action=call.action, via=call.via,
+        status_after=mutation.status, edited=bool(changes), step_verdict=call.step_verdict,
+    )
+    db.add(review)
+    db.flush()
+    for change in changes:
+        db.add(MutationReviewChange(
+            world_id=mutation.world_id, review_id=review.id, path=change.path, field=change.field,
+            kind=change.kind, before_value=change.before_value, after_value=change.after_value,
+        ))
+    if changes and mutation.original_payload is None:
+        mutation.original_payload = call.before_payload
+        db.add(mutation)
+    return review
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 9f9a809..24b7bfc 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19696,6 +19696,34 @@ could never be measured. One review per proposal, rewritten on a second
 call: history is sacred. A JSON diff column: the dashboard reads what
 changed, and UI-visible data is relational (INV-20).
 
+## EVERY REVIEW PATH RECORDS ITS ROUND (TICKET-0115) -- `writes/mutation_reviews.py`, `review_diff.py`, `review_verdict.py` (BRIEF-0115-b, no schema change)
+
+**One writer, four paths.** Approve, reject, and both in batch build a
+`ReviewCall` before anything is applied -- the payload as stored (a copy,
+taken before an edited one replaces it) and, for an `agenda_step_change`,
+`review_verdict.step_verdict` -- and `record_review` writes the round with
+the status the call left, right before the path's own commit. Every status
+a path can leave (applied, « Needs attention », parked for realization,
+rejected) is recorded, so a round is never missing.
+
+**H1a -- the diff.** `review_diff.diff_payloads` compares the payload stored
+before the call and the one approved, value by value. An empty value equals
+an absent one (the card writes `description: null`); `type_name` and what an
+apply writes are never compared; a list pairs its elements by natural key
+(participants by role NAME -- the tick names a role, the card adds its id;
+state changes by entity and state; scopes by kind and target), a list of
+plain values as a set, `steps` by position. Only a unit approve carries an
+edit (`ck_mutation_review_edited`).
+
+**C1 -- the verdict before the apply.** `complete` reads the step's
+completion, `fail` its failure, with Journée's bindings. A faction's agenda
+has no `doer` to bind: `not_judged`, never a guess.
+
+**Rejected.** Recording only the final approve (a « Needs attention » round
+would vanish). A positional diff everywhere (a reordered list reads as a
+rewrite). The verdict after the apply (the apply moves the step: M2 would
+compare the condition with its own consequence).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/review_recording.py b/tooling/verify/checks/review_recording.py
new file mode 100644
index 0000000..46ec1a5
--- /dev/null
+++ b/tooling/verify/checks/review_recording.py
@@ -0,0 +1,375 @@
+"""G1 check for TICKET-0115 -- every review of a proposal is recorded: its round, what the creator changed, and what a step's condition said.
+
+BRIEF-0115-B's rules (A3, C1 and H1a of the conditions series' dashboard).
+
+RD1 -- the diff (pure). `review_diff.diff_payloads` on the cases of
+   `DIFF_CASES` returns exactly the expected `(path, field, kind, before,
+   after)` rows: an empty value equals an absent key; `type_name` and an
+   apply's `applied_changes` are never compared; participants pair by role
+   name (a role id added by the card is a change of that key only), a
+   retyped participant's entity is one `changed`, a list of plain values is
+   a set, `steps` pair by position, a second element of one role is
+   `[role#2]`, a nested object is walked, a boolean is not an integer.
+RD2 -- an edited approve (route functions, a fixture world). A
+   `relation_change` approved with its delta changed from 5 to 9 is applied;
+   it holds one `mutation_review` (round 1, approve, unit, applied, edited)
+   and one change (`intensity_delta`, changed, `5` -> `9`), and its
+   `original_payload` is the producer's payload. Approved unchanged, another
+   holds round 1 not edited, no change, `original_payload` NULL.
+RD3 -- rounds. A `relation_change` naming no `entity_b_id`, approved with
+   its delta changed from 5 to 6, fails to apply (round 1: approve, unit,
+   approved, edited, one change); approved again with the entity added it
+   applies (round 2, edited, one change `entity_b_id` added -- compared to
+   what round 1 stored), and `original_payload` is still the producer's
+   payload, delta 5. A unit reject, a batch reject and a batch approve each
+   write one round with their `via`, never edited, never a change. An
+   auto-apply (`_approve_apply_and_commit` with no `ReviewCall`, the path
+   of INV-15's `skill_progress`) applies and writes no round.
+RD4 -- a step's verdict (C1). Rejecting an `agenda_step_change` records
+   `met` when the step's completion is met (the character holds 10, the
+   leaf asks 5), `unmet` when it is not, `none`
+   when the step has no completion, `none` for `fail` on a step with no
+   failure condition, `not_judged` for a faction's agenda and for an unknown
+   step; any other type records NULL.
+RD5 -- the paths (AST of `cockpit/routes/mutations.py`). `reject_mutation`,
+   `approve_mutation`, `_batch_approve` and `_batch_reject` each build their
+   `ReviewCall` with `step_verdict(...)` BEFORE they apply or change the
+   status: in `approve_mutation` the `ReviewCall(` comes after
+   `_approve_apply_edited_payload(` and before
+   `_approve_apply_and_commit(`; `record_review(` is called exactly eight (one per status a path leaves)
+   times in the module, never outside those functions and the two approve
+   helpers.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import json
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+ROUTES = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "mutations.py"
+
+FAILURES: list[str] = []
+
+P1 = {"role_id": "r1", "role": "Chasseur", "entity_id": "e1", "sorte_id": None, "secret": None}
+DIFF_CASES: tuple[tuple[str, dict, dict, list], ...] = (
+    ("empty equals absent", {"title": "a"}, {"title": "a", "description": None, "scopes": [], "x": ""}, []),
+    ("type_name and applied_changes ignored", {"type_id": "t", "type_name": "A"},
+     {"type_id": "t", "type_name": "B", "applied_changes": [{"a": 1}]}, []),
+    ("a role id added", {"participants": [{"role": "Chasseur", "entity_id": "e1"}]},
+     {"participants": [P1]},
+     [("participants[Chasseur].role_id", "participants[].role_id", "added", None, '"r1"')]),
+    ("a participant's entity", {"participants": [P1]}, {"participants": [dict(P1, entity_id="e2")]},
+     [("participants[Chasseur].entity_id", "participants[].entity_id", "changed", '"e1"', '"e2"')]),
+    ("a second participant of one role", {"participants": [P1]},
+     {"participants": [P1, dict(P1, entity_id="e3")]},
+     [("participants[Chasseur#2]", "participants[]", "added", None, None)]),
+    ("a set of plain values", {"involved_entities": ["a", "b"]}, {"involved_entities": ["b", "c"]},
+     [('involved_entities["a"]', "involved_entities[]", "removed", '"a"', None),
+      ('involved_entities["c"]', "involved_entities[]", "added", None, '"c"')]),
+    ("steps by position", {"steps": ["x", "y"]}, {"steps": ["x", "z", "w"]},
+     [("steps[2]", "steps[]", "changed", '"y"', '"z"'), ("steps[3]", "steps[]", "added", None, '"w"')]),
+    ("a type changed, a nested object", {"type_id": "t1", "new_type": {"name": "A", "roles": [{"name": "R"}]}},
+     {"type_id": "t2", "new_type": {"name": "B", "roles": [{"name": "R"}]}},
+     [("new_type.name", "new_type.name", "changed", '"A"', '"B"'),
+      ("type_id", "type_id", "changed", '"t1"', '"t2"')]),
+    ("a boolean is not an integer", {"secret": 1}, {"secret": True},
+     [("secret", "secret", "changed", "1", "true")]),
+    ("a state change by entity and state",
+     {"state_changes": [{"entity_id": "e", "attribute": "a", "mode": "set", "value": "x"}]},
+     {"state_changes": [{"entity_id": "e", "attribute": "a", "mode": "set", "value": "y"}]},
+     [("state_changes[e|a].value", "state_changes[].value", "changed", '"x"', '"y"')]),
+)
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+
+
+# --- RD1 -------------------------------------------------------------------------
+
+def check_rd1() -> None:
+    from world_engine.review_diff import diff_payloads
+
+    if not DIFF_CASES:
+        fail("RD1: no case")
+    for label, before, after, want in DIFF_CASES:
+        got = [(c.path, c.field, c.kind, c.before_value, c.after_value) for c in diff_payloads(before, after)]
+        if sorted(got) != sorted(want):
+            fail(f"RD1: {label}: {got}")
+
+
+# --- fixture ---------------------------------------------------------------------
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, Faction, World
+    from world_engine.writes import write_ledger_entry
+
+    with Session(engine) as db:
+        world = World(name="Suivi", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind in (("brakk", "character"), ("odo", "character"), ("garde", "faction")):
+            row = Entity(world_id=world.id, type=kind, name=key.capitalize())
+            db.add(row)
+            db.flush()
+            ids[key] = row.id
+            db.add(Character(id=row.id, world_id=world.id, character_type="player" if key == "brakk" else "npc")
+                   if kind == "character" else Faction(id=row.id))
+        db.flush()
+        write_ledger_entry(db, world_id=world.id, entity_id=ids["brakk"], amount=10, reason="bourse")
+        db.commit()
+    return ids
+
+
+def _proposal(engine, ids: dict, mutation_type: str, payload: dict) -> str:
+    from sqlmodel import Session
+
+    from world_engine.models import ProposedMutation
+
+    with Session(engine) as db:
+        row = ProposedMutation(world_id=ids["world"], source_type="conversation", mutation_type=mutation_type,
+                               payload=payload, proposed_by="local_ai_window")
+        db.add(row)
+        db.commit()
+        return row.id
+
+
+def _reviews(engine, mut_id: str) -> list[tuple]:
+    from sqlmodel import Session, select
+
+    from world_engine.models import MutationReview, MutationReviewChange
+
+    with Session(engine) as db:
+        out = []
+        for r in db.exec(select(MutationReview).where(MutationReview.mutation_id == mut_id)
+                         .order_by(MutationReview.round)).all():
+            changes = [(c.path, c.kind, c.before_value, c.after_value) for c in
+                       db.exec(select(MutationReviewChange).where(MutationReviewChange.review_id == r.id)).all()]
+            out.append((r.round, r.action, r.via, r.status_after, r.edited, r.step_verdict, changes))
+        return out
+
+
+def _original(engine, mut_id: str):
+    from sqlmodel import Session
+
+    from world_engine.models import ProposedMutation
+
+    with Session(engine) as db:
+        return db.get(ProposedMutation, mut_id).original_payload
+
+
+def _relation(ids: dict, delta: int = 5, with_b: bool = True) -> dict:
+    payload = {"entity_a_id": ids["brakk"], "intensity_delta": delta, "relation_type": "trust"}
+    if with_b:
+        payload["entity_b_id"] = ids["odo"]
+    return payload
+
+
+# --- RD2, RD3 --------------------------------------------------------------------
+
+def check_rd2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import mutations as routes
+
+    edited = _proposal(engine, ids, "relation_change", _relation(ids))
+    plain = _proposal(engine, ids, "relation_change", _relation(ids))
+    with Session(engine) as db:
+        answer = routes.approve_mutation(edited, routes.ApproveBody(payload=json.dumps(_relation(ids, 9))), db)
+        routes.approve_mutation(plain, routes.ApproveBody(payload=json.dumps(_relation(ids))), db)
+    if answer.get("status") != "applied":
+        fail(f"RD2: the edited approve answered {answer.get('status')}: {answer.get('error')}")
+    want = [(1, "approve", "unit", "applied", True, None, [("intensity_delta", "changed", "5", "9")])]
+    if _reviews(engine, edited) != want:
+        fail(f"RD2: the edited review is {_reviews(engine, edited)}")
+    if _original(engine, edited) != _relation(ids):
+        fail(f"RD2: original_payload is {_original(engine, edited)}")
+    if _reviews(engine, plain) != [(1, "approve", "unit", "applied", False, None, [])] \
+            or _original(engine, plain) is not None:
+        fail(f"RD2: the unedited review is {_reviews(engine, plain)}, original {_original(engine, plain)}")
+
+
+def check_rd3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import mutations as routes
+
+    broken = _proposal(engine, ids, "relation_change", _relation(ids, with_b=False))
+    with Session(engine) as db:
+        first = routes.approve_mutation(broken, routes.ApproveBody(
+            payload=json.dumps(_relation(ids, 6, with_b=False))), db)
+        second = routes.approve_mutation(broken, routes.ApproveBody(payload=json.dumps(_relation(ids, 6))), db)
+    if (first.get("status"), second.get("status")) != ("approved", "applied"):
+        fail(f"RD3: the two approvals answered {first.get('status')}, {second.get('status')}")
+    want = [(1, "approve", "unit", "approved", True, None, [("intensity_delta", "changed", "5", "6")]),
+            (2, "approve", "unit", "applied", True, None, [("entity_b_id", "added", None, json.dumps(ids["odo"]))])]
+    if _reviews(engine, broken) != want:
+        fail(f"RD3: the rounds are {_reviews(engine, broken)}")
+    if _original(engine, broken) != _relation(ids, with_b=False):
+        fail(f"RD3: original_payload is {_original(engine, broken)}")
+
+    unit, batch_r, batch_a = (_proposal(engine, ids, "relation_change", _relation(ids)) for _ in range(3))
+    with Session(engine) as db:
+        routes.reject_mutation(unit, routes.RejectBody(), db)
+        routes.batch_review_mutations(routes.BatchReviewBody(action="reject", mutation_ids=[batch_r]), db)
+        routes.batch_review_mutations(routes.BatchReviewBody(action="approve", mutation_ids=[batch_a]), db)
+    for mut_id, want_row in ((unit, (1, "reject", "unit", "rejected", False, None, [])),
+                             (batch_r, (1, "reject", "batch", "rejected", False, None, [])),
+                             (batch_a, (1, "approve", "batch", "applied", False, None, []))):
+        if _reviews(engine, mut_id) != [want_row]:
+            fail(f"RD3: {want_row[1]} {want_row[2]} recorded {_reviews(engine, mut_id)}")
+    auto = _proposal(engine, ids, "relation_change", _relation(ids))
+    with Session(engine) as db:
+        from datetime import UTC, datetime
+
+        from world_engine.models import ProposedMutation
+
+        done = routes._approve_apply_and_commit(db.get(ProposedMutation, auto), db, datetime.now(UTC))
+    if done.get("status") != "applied" or _reviews(engine, auto):
+        fail(f"RD3: an auto-apply answered {done.get('status')} and recorded {_reviews(engine, auto)}")
+
+
+# --- RD4 -------------------------------------------------------------------------
+
+def _step(engine, ids: dict, owner: str, completion: dict | None) -> str:
+    from datetime import UTC, datetime
+
+    from sqlmodel import Session
+
+    from world_engine.conditions import node_from_dict
+    from world_engine.models import Agenda, AgendaStep
+    from world_engine.writes.conditions import write_condition
+
+    with Session(engine) as db:
+        agenda = Agenda(world_id=ids["world"], owner_entity_id=ids[owner], title="t", status="active")
+        db.add(agenda)
+        db.flush()
+        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="active",
+                          started_at=datetime.now(UTC))
+        db.add(step)
+        db.flush()
+        if completion is not None:
+            write_condition(db, world_id=ids["world"], role="completion", tree=node_from_dict(completion),
+                            agenda_step_id=step.id)
+        db.commit()
+        return step.id
+
+
+def check_rd4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import mutations as routes
+
+    def money(n: int) -> dict:
+        return {"op": "leaf", "type": "resource", "subject_role": "doer", "target_key": "or", "threshold": n}
+
+    cases = (
+        ("met", _step(engine, ids, "brakk", money(5)), "complete"),
+        ("unmet", _step(engine, ids, "brakk", money(1000)), "complete"),
+        ("none", _step(engine, ids, "brakk", None), "complete"),
+        ("none", _step(engine, ids, "brakk", money(5)), "fail"),
+        ("not_judged", _step(engine, ids, "garde", money(5)), "complete"),
+        ("not_judged", "no-such-step", "complete"),
+    )
+    for want, step_id, action in cases:
+        mut_id = _proposal(engine, ids, "agenda_step_change", {"step_id": step_id, "action": action})
+        with Session(engine) as db:
+            routes.reject_mutation(mut_id, routes.RejectBody(), db)
+        got = [r[5] for r in _reviews(engine, mut_id)]
+        if got != [want]:
+            fail(f"RD4: {action} on a step expecting {want} recorded {got}")
+    other = _proposal(engine, ids, "relation_change", _relation(ids))
+    with Session(engine) as db:
+        routes.reject_mutation(other, routes.RejectBody(), db)
+    if [r[5] for r in _reviews(engine, other)] != [None]:
+        fail(f"RD4: a relation_change recorded the verdict {_reviews(engine, other)}")
+
+
+# --- RD5 -------------------------------------------------------------------------
+
+def _calls(node: ast.AST, name: str) -> list[int]:
+    return sorted(n.lineno for n in ast.walk(node) if isinstance(n, ast.Call)
+                  and ((isinstance(n.func, ast.Name) and n.func.id == name)
+                       or (isinstance(n.func, ast.Attribute) and n.func.attr == name)))
+
+
+def check_rd5() -> None:
+    if not ROUTES.exists():
+        fail(f"RD5: {ROUTES} not found")
+        return
+    tree = ast.parse(ROUTES.read_text(encoding="utf-8"))
+    functions = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
+    for name in ("reject_mutation", "approve_mutation", "_batch_approve", "_batch_reject"):
+        f = functions.get(name)
+        if f is None:
+            fail(f"RD5: {name} not found")
+            continue
+        calls, verdicts = _calls(f, "ReviewCall"), _calls(f, "step_verdict")
+        if len(calls) != 1 or len(verdicts) != 1:
+            fail(f"RD5: {name} builds {len(calls)} ReviewCall with {len(verdicts)} step_verdict")
+            continue
+        applies = _calls(f, "_apply_mutation") + _calls(f, "_approve_apply_and_commit")
+        status_writes = sorted(n.lineno for n in ast.walk(f) if isinstance(n, ast.Assign)
+                               and any(isinstance(t, ast.Attribute) and t.attr == "status" for t in n.targets))
+        if any(line < calls[0] for line in applies + status_writes):
+            fail(f"RD5: {name} applies or sets a status before its ReviewCall")
+    approve = functions.get("approve_mutation")
+    if approve is not None:
+        edit, call, commit = (_calls(approve, n) for n in ("_approve_apply_edited_payload", "ReviewCall",
+                                                         "_approve_apply_and_commit"))
+        if not (edit and call and commit and edit[0] < call[0] < commit[0]):
+            fail("RD5: approve_mutation does not build its ReviewCall between the edit and the apply")
+    allowed = {"reject_mutation", "_batch_approve", "_batch_reject", "_approve_entity_creation_shortcircuit",
+               "_approve_apply_and_commit"}
+    total = 0
+    for f in tree.body:
+        if isinstance(f, ast.FunctionDef):
+            n = len(_calls(f, "record_review"))
+            total += n
+            if n and f.name not in allowed:
+                fail(f"RD5: {f.name} calls record_review")
+    if total != 8:
+        fail(f"RD5: record_review is called {total} times, not 8")
+
+
+def main() -> None:
+    _fresh_db()
+    from sqlmodel import SQLModel
+
+    from world_engine import models  # noqa: F401 -- registers every table
+    from world_engine.db import engine
+
+    SQLModel.metadata.create_all(engine)
+    check_rd1()
+    ids = _fixture(engine)
+    check_rd2(engine, ids)
+    check_rd3(engine, ids)
+    check_rd4(engine, ids)
+    check_rd5()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        sys.exit(1)
+    print("PASS: review_recording -- every review is a round with its changes and its step's verdict; "
+          "the diff pairs by natural key")
+
+
+if __name__ == "__main__":
+    main()
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- How a proposal is applied, its status rules, the batch's skip rule: unchanged.
- The producer list (BRIEF-0115-C); any reader of the rounds (D).
- Every later brief of this lot: BRIEF-0115-C to E.

## Invariants to defend

INV-08 (two canon-write paths): the review tables are not canon (`canon_write_policy.txt` unchanged); the writer never touches a canon table. INV-15: the auto-applied roll records no review. INV-11 / the SAVEPOINT rule of `_approve_apply_and_commit`: the review row joins the OUTER transaction, never the savepoint -- a failed apply still records its round.

## Decision rights

STOP:
- Recording a round would need a second commit, or would run inside the apply's savepoint.
- A path's status or apply behaviour would change.
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
- `python tooling/verify/checks/review_recording.py` -> `PASS`.
- `python tooling/verify/checks/mutation_reviews.py` -> `PASS`.
- `python tooling/verify/checks/skill_progression.py` -> `PASS`.
- `python tooling/verify/checks/single_canon_write.py` -> `PASS`.
- `python tooling/verify/checks/import_cycle.py` -> `PASS`.
- `python tooling/verify/checks/undefined_names.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (164 on the prototype; `lore_usage.py` may time out as on `main` -- REPORT-ONLY).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **RD1** -- `review_diff.py` `NATURAL_KEYS`: `    "participants": (("role", "role_id"),),` -> `    "participants": (("role_id", "role"),),`
  - **RD2, RD3** -- `routes/mutations.py` `approve_mutation`: `    before = copy.deepcopy(mut.payload)` (the line above `_approve_apply_edited_payload(mut, body)`) -> moved below `_approve_apply_edited_payload(mut, body)`
  - **RD3** -- `writes/mutation_reviews.py` `record_review`: `    if changes and mutation.original_payload is None:` -> `    if changes:`
  - **RD3** -- `writes/mutation_reviews.py` `record_review`: `round=rounds + 1,` -> `round=1,` (the check crashes on the unique index: red)
  - **RD3** -- `routes/mutations.py` `_approve_apply_and_commit`, the applied branch: `        if call is not None:` / `            record_review(db, mut, call)` -> `        record_review(db, mut, call)`
  - **RD4** -- `review_verdict.py` `ROLE_BY_ACTION`: `{"complete": "completion", "fail": "failure"}` -> `{"complete": "completion", "fail": "completion"}`
- Live gate (Nia): The review queue: approve one proposal unchanged, one after editing its title, reject a third; then (Claude Code, read-only on a copy) `SELECT round, action, via, status_after, edited FROM mutation_review` shows three rows, and `mutation_review_change` one `title` change.
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
