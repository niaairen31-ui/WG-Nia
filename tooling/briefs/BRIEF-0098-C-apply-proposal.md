<!-- slug: apply-proposal -->
# BRIEF 0098-C — "Apply a confirmed proposal in one transaction"

Lot: LOT-0098-lore-writing.md (authoritative on conflict)
Depends on: BRIEF-0098-B (the record tables)
Commit header for decisions: `(BRIEF-0098-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0098`, on the tree the previous brief left, before applying anything. Halt if one has moved.

- `src/world_engine/writes/facets.py:44` → `SCOPE_TYPES = ("none", "world", "location", "faction", "rencontre")`
- `src/world_engine/writes/facets.py:93` → `def add_entity_fact(`; `:266` → `def _descriptive_fact(db: Session, fact_id: str) -> Fact:` (the new block goes just above this line)
- `src/world_engine/writes/facts.py:158` → `def attach_participants(`; `:187` → `def create_fact_default(`
- `src/world_engine/writes/knowledge.py:72` → `KNOWLEDGE_LEVEL_LADDER: tuple[str, ...] = (`; `:241` → `def write_knowledge(`
- `src/world_engine/writes/factions.py:108` → `        db.add(membership)` inside `write_membership(mode="open")`
- `src/world_engine/writes/relations.py:144` → `def _birth_typed_fact(db: Session, rel: Relation, changed_by: str) -> Optional[Fact]:`
- `src/world_engine/fact_refs.py:57` → `def find_held(db: Session, entity_id: Optional[str], payload: dict) -> Optional[Knowledge]:`
- `tooling/verify/checks/lore_write.py:44` → `_LORE_WRITE_FILES: frozenset[str] = frozenset()`

## Facts carried

### R-06 — the entity-fact writer [M]
Opened: `src/world_engine/writes/facets.py:1-147` (docstring,
`SCOPE_TYPES` at 44, `_check_scope` 73, `_bloc_exists` 83, `add_entity_fact`
93-146), `:266-300`; `tooling/verify/checks/fact_facets.py:1-40` (R2, R3).
Finding: `add_entity_fact` writes one DESCRIPTIVE fact about ONE entity
with one scope; it tokenizes (`names_only` for an appellation, owner
excluded) and records unresolved names. R3: a `create_fact(` whose facet is
descriptive or non-literal appears only in `writes/facets.py`.
Consequence: a lore fact (several participants, `information`, zero
participants, several defaults) needs a new function IN `writes/facets.py`
(C-03), reusing `_check_scope`, `_bloc_exists`, `tokenize`,
`record_unresolved`.

### R-07 — fact rows [M]
Opened: `src/world_engine/writes/facts.py:50-215`.
Finding: `create_fact` validates the facet (`_check_facet`), refuses NULL,
unknown, and typed-on-free; `attach_participants` refuses a typed fact and
does not read before writing; `create_fact_default` writes with no
duplicate guard; `update_fact_content` appends history. None commits.
Consequence: C reads existing participants and defaults before writing
(`idx_fact_participant_unique` would abort the transaction).

### R-08 — knowledge rows [M]
Opened: `src/world_engine/writes/knowledge.py:65-74` (levels, ladder),
`:180-260` (`_build_knowledge_update`, `write_knowledge`);
`src/world_engine/fact_refs.py:57-76` (`find_held`);
`models/canon_knowledge.py:198-212` (`idx_knowledge_entity_fact` UNIQUE).
Finding: `write_knowledge` accepts a `fact_id` alone for a new row; an
unknown `level` falls back SILENTLY to `rumor`; it adds the row itself.
Consequence: C validates `level` against `KNOWLEDGE_LEVEL_LADDER` before
writing, and calls `find_held` first.

### R-09 — memberships [M]
Opened: `src/world_engine/writes/factions.py:61-120`;
`src/world_engine/models/canon_faction.py:95-110`.
Finding: `write_membership(mode="open")` adds the row itself (`:108`); the
model declares `idx_membership_unique_active` on `(entity_id, faction_id)`
(`:104`, partial on active rows), so a second active membership aborts the
transaction.
Consequence: C reads for an active membership first and never `db.add`s the
returned row again.

### R-10 — `controls` [M]
Opened: `src/world_engine/writes/relations.py:1-40` (docstring), `:242-310`.
Finding: `controls` is structural; `_birth_typed_fact` (`:144-158`) creates
a `lien` fact for a social type and for `connects_to`, and returns None for
any other structural type, `controls` included.
Consequence: P1 — possession is the relation (for A2) plus a `statut` fact
(learnable).

### R-16 — defaults cannot carry a secret [M]
Opened: `src/world_engine/models/canon_knowledge.py:163-196` (`FactDefault`:
`scope_type`, `scope_id`, `level`, `created_by`; CHECKs on scope);
`src/world_engine/knowledge_resolve.py:140-215` (tiers).
Finding: `fact_default` has no `is_secret` column; resolution reads
`level` only.
Consequence: a secret or a false belief is always a stored `knowledge` row
for a checked entity (E1); a default never mints one.

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

### C-03 — `add_lore_fact`
Produced by: C   Consumed by: C (`apply_proposal`)
`writes/facets.py::add_lore_fact(db, *, world_id, facet, content,
created_by, participant_ids, aspect=None, scopes=(), mentions=None) ->
LoreFactRows(fact, participants, defaults)`. `ValueError` on an unknown or
typed facet, empty content, a participant outside the world or twice, a
`bloc`/`appellation` fact without exactly one participant, a second `bloc`
fact (same aspect), a `none`/malformed scope, a scope twice. Tokenizes
(`names_only` without the owner for an appellation), records unresolved
names and declared mentions, writes `knows` defaults. Never commits.

### C-04 — the source record
Produced by: B (tables), C (writer)   Consumed by: C, E (`lore_write_read`)
- `lore_entry(id, world_id FK, statement NOT NULL, questions, answers,
  created_at)`, index `idx_lore_entry_world(world_id, created_at)`.
- `lore_entry_row(id, entry_id FK, row_table CHECK in
  LORE_ENTRY_ROW_TABLES, row_id, action CHECK in created|updated)`, UNIQUE
  `idx_lore_entry_row_entry(entry_id, row_table, row_id)`.
- `writes/lore_entries.py`: `write_lore_entry(db, *, world_id, statement,
  questions=None, answers=None)` (empty statement -> ValueError, blanks ->
  NULL); `record_entry_row(db, *, entry_id, row_table, row_id,
  action="created")` (values outside the CHECK lists -> ValueError).
- `migrate_v2_11_lore_entry.py`: refuses below v2.10; creates both tables;
  idempotent; zero rows; converges `schema_meta` to v2.11.

## Context

The heart of the lot, with no model: what the creator confirmed is validated against her world, then written through the existing chokepoints in one transaction, every row recorded against its story. Existing rows are skipped and reported, never duplicated.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: adds `LoreFactRows`, `_lore_participants` and `add_lore_fact` (C-03) to `writes/facets.py` (imports `FACETS`, `FactDefault`); creates `writes/lore_entries.py` (C-04's writer) and `lore_write_apply.py` (C-02); extends `lore_write.py` (census: two files; C1, C2); appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): apply a confirmed lore proposal in one transaction (BRIEF-0098-c)`.

````diff
diff --git a/src/world_engine/lore_write_apply.py b/src/world_engine/lore_write_apply.py
new file mode 100644
index 0000000..6b84628
--- /dev/null
+++ b/src/world_engine/lore_write_apply.py
@@ -0,0 +1,343 @@
+"""Validate and apply a lore proposal (TICKET-0098, BRIEF-0098-C, C-02).
+
+A proposal is what the creator confirmed in the Lore shell's writing panel:
+entities to create or reuse, facts to create, extend or rewrite, who knows
+them, faction memberships and `controls` edges (decisions C1, D1, E1, P1,
+R1, S1). This module never calls a model and never commits. `validate`
+reads only; `apply_proposal` validates first, then writes through the
+chokepoints (`writes/facets.py`, `writes/knowledge.py`,
+`writes/factions.py`, `writes/relations.py`, `writes/lore_entries.py`) in
+one caller-owned transaction, and records every row it wrote against one
+`lore_entry`. A row that already exists (a knower already holding the fact,
+a participant already attached, an active membership, a `controls` edge) is
+skipped and reported, never duplicated.
+
+Entities are created through a callable the caller injects
+(`create_entity(name, type) -> Entity`, flushed): the commit-free creation
+core lives with the creator CRUD, which this module does not import.
+Every id in a proposal is re-read here against the proposal's world.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Any, Callable, Optional
+
+from sqlmodel import Session, select
+
+from .facets import DESCRIPTIVE_FACETS, FACETS
+from .fact_refs import find_held
+from .models import Entity, Fact, FactDefault, FactionMembership, FactParticipant, Relation
+from .writes.facets import ScopeChoice, add_lore_fact, edit_entity_fact
+from .writes.facts import attach_participants, create_fact_default
+from .writes.factions import write_membership
+from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER, write_knowledge
+from .writes.lore_entries import record_entry_row, write_lore_entry
+from .writes.relations import write_relation
+
+CREATED_BY = "creator_lore"
+ENTITY_TYPES: tuple[str, ...] = ("character", "location", "faction", "item")
+FACT_ACTIONS: tuple[str, ...] = ("create", "existing", "rewrite")
+SCOPE_TYPES: tuple[str, ...] = ("world", "faction", "location", "rencontre")
+_SCOPE_ENTITY_TYPE: dict[str, Optional[str]] = {
+    "world": None, "faction": "faction", "location": "location", "rencontre": None,
+}
+
+
+class ProposalError(ValueError):
+    """The proposal cannot be written; the message is shown to the creator."""
+
+
+@dataclass
+class ApplyResult:
+    entry_id: str
+    written: dict[str, int] = field(default_factory=dict)
+    skipped: list[str] = field(default_factory=list)
+
+
+def _list(proposal: dict, key: str) -> list[dict]:
+    value = proposal.get(key) or []
+    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
+        raise ProposalError(f"« {key} » doit être une liste d'objets.")
+    return value
+
+
+def _text(item: dict, key: str, where: str) -> str:
+    value = item.get(key)
+    if not isinstance(value, str) or not value.strip():
+        raise ProposalError(f"{where} : « {key} » est vide.")
+    return value.strip()
+
+
+def _validate_entities(db: Session, world_id: str, entities: list[dict]) -> dict[str, dict]:
+    """ref -> the entity item, with `_type` set (the type an existing entity has)."""
+    refs: dict[str, dict] = {}
+    for item in entities:
+        ref = _text(item, "ref", "Entité")
+        if ref in refs:
+            raise ProposalError(f"Entité « {ref} » déclarée deux fois.")
+        action = item.get("action")
+        if action == "create":
+            _text(item, "name", f"Entité {ref}")
+            if item.get("type") not in ENTITY_TYPES:
+                raise ProposalError(f"Entité {ref} : type {item.get('type')!r} non permis.")
+            item["_type"] = item["type"]
+        elif action == "existing":
+            entity = db.get(Entity, item.get("entity_id") or "")
+            if entity is None or entity.world_id != world_id or entity.status != "active":
+                raise ProposalError(f"Entité {ref} : aucune entité active de ce monde.")
+            item["_type"] = entity.type
+        else:
+            raise ProposalError(f"Entité {ref} : action {action!r} inconnue.")
+        refs[ref] = item
+    return refs
+
+
+def _entity_ref(refs: dict[str, dict], ref: Any, where: str, want: Optional[str] = None) -> str:
+    if ref not in refs:
+        raise ProposalError(f"{where} : l'entité « {ref} » n'est pas dans la proposition.")
+    if want is not None and refs[ref]["_type"] != want:
+        raise ProposalError(f"{where} : « {ref} » doit être de type {want}.")
+    return ref
+
+
+def _validate_scopes(refs: dict[str, dict], item: dict, where: str) -> None:
+    seen = set()
+    for scope in _list(item, "defaults"):
+        scope_type = scope.get("scope_type")
+        if scope_type not in SCOPE_TYPES:
+            raise ProposalError(f"{where} : portée {scope_type!r} inconnue.")
+        if scope_type == "world":
+            if scope.get("scope_ref") is not None:
+                raise ProposalError(f"{where} : la portée monde ne nomme pas d'entité.")
+        else:
+            _entity_ref(refs, scope.get("scope_ref"), where, _SCOPE_ENTITY_TYPE[scope_type])
+        key = (scope_type, scope.get("scope_ref"))
+        if key in seen:
+            raise ProposalError(f"{where} : la même portée est listée deux fois.")
+        seen.add(key)
+
+
+def _validate_knowers(refs: dict[str, dict], item: dict, where: str) -> None:
+    seen = set()
+    for knower in _list(item, "knowers"):
+        ref = _entity_ref(refs, knower.get("entity_ref"), where)
+        if ref in seen:
+            raise ProposalError(f"{where} : « {ref} » sait deux fois le même fait.")
+        seen.add(ref)
+        if knower.get("level") not in KNOWLEDGE_LEVEL_LADDER:
+            raise ProposalError(f"{where} : niveau {knower.get('level')!r} inconnu.")
+        for flag in ("is_secret", "is_incorrect"):
+            if not isinstance(knower.get(flag, False), bool):
+                raise ProposalError(f"{where} : « {flag} » doit être vrai ou faux.")
+
+
+def _world_fact(db: Session, world_id: str, fact_id: Any, where: str) -> Fact:
+    fact = db.get(Fact, fact_id or "")
+    if fact is None or fact.world_id != world_id:
+        raise ProposalError(f"{where} : aucun fait de ce monde ne porte cet identifiant.")
+    return fact
+
+
+def _validate_fact(db: Session, world_id: str, refs: dict[str, dict], item: dict) -> None:
+    ref = _text(item, "ref", "Fait")
+    where = f"Fait {ref}"
+    action = item.get("action")
+    if action not in FACT_ACTIONS:
+        raise ProposalError(f"{where} : action {action!r} inconnue.")
+    participants = item.get("participants") or []
+    if not isinstance(participants, list):
+        raise ProposalError(f"{where} : « participants » doit être une liste.")
+    for participant in participants:
+        _entity_ref(refs, participant, where)
+    if action == "create":
+        _text(item, "content", where)
+        spec = FACETS.get(item.get("facet"))
+        if spec is None or spec.granularity == "typed":
+            raise ProposalError(f"{where} : facette {item.get('facet')!r} non permise.")
+        if (spec.granularity == "bloc" or item["facet"] == "appellation") and len(participants) != 1:
+            raise ProposalError(f"{where} : une facette {item['facet']} a un seul participant.")
+    else:
+        fact = _world_fact(db, world_id, item.get("fact_id"), where)
+        typed = fact.relation_id or fact.event_id or fact.world_law_id
+        if participants and typed:
+            raise ProposalError(f"{where} : un fait typé ne reçoit pas de participant.")
+        if action == "rewrite":
+            _text(item, "content", where)
+            spec = FACETS.get(fact.facet or "")
+            if fact.facet not in DESCRIPTIVE_FACETS or spec is None or spec.granularity != "bloc":
+                raise ProposalError(f"{where} : seul un fait « bloc » se réécrit.")
+    _validate_scopes(refs, item, where)
+    _validate_knowers(refs, item, where)
+
+
+def validate(db: Session, world_id: str, proposal: dict) -> dict[str, dict]:
+    """Raise `ProposalError` on the first defect; return the entity refs.
+    Reads only."""
+    if not isinstance(proposal, dict):
+        raise ProposalError("La proposition doit être un objet.")
+    _text(proposal, "statement", "Proposition")
+    refs = _validate_entities(db, world_id, _list(proposal, "entities"))
+    fact_refs: set[str] = set()
+    for item in _list(proposal, "facts"):
+        _validate_fact(db, world_id, refs, item)
+        if item["ref"] in fact_refs:
+            raise ProposalError(f"Fait « {item['ref']} » déclaré deux fois.")
+        fact_refs.add(item["ref"])
+    for item in _list(proposal, "memberships"):
+        _entity_ref(refs, item.get("entity_ref"), "Appartenance", "character")
+        _entity_ref(refs, item.get("faction_ref"), "Appartenance", "faction")
+    for item in _list(proposal, "controls"):
+        _entity_ref(refs, item.get("owner_ref"), "Possession")
+        _entity_ref(refs, item.get("location_ref"), "Possession", "location")
+    if not (fact_refs or proposal.get("memberships") or proposal.get("controls")):
+        raise ProposalError("La proposition n'écrit rien.")
+    return refs
+
+
+class _Writer:
+    """Applies one validated proposal; every written row is recorded."""
+
+    def __init__(self, db: Session, world_id: str, entry_id: str) -> None:
+        self.db, self.world_id = db, world_id
+        self.result = ApplyResult(entry_id=entry_id)
+        self.ids: dict[str, str] = {}
+
+    def record(self, table: str, row_id: str, action: str = "created") -> None:
+        record_entry_row(self.db, entry_id=self.result.entry_id, row_table=table,
+                         row_id=row_id, action=action)
+        key = f"{table}:{action}"
+        self.result.written[key] = self.result.written.get(key, 0) + 1
+
+    def entities(self, refs: dict[str, dict], create_entity: Callable[[str, str], Entity]) -> None:
+        for ref, item in refs.items():
+            if item["action"] == "existing":
+                self.ids[ref] = item["entity_id"]
+                continue
+            entity = create_entity(item["name"].strip(), item["type"])
+            self.ids[ref] = entity.id
+            self.record("entity", entity.id)
+        self.db.flush()
+
+    def scopes(self, item: dict) -> tuple[ScopeChoice, ...]:
+        return tuple(
+            ScopeChoice(s["scope_type"], None if s["scope_type"] == "world" else self.ids[s["scope_ref"]])
+            for s in _list(item, "defaults")
+        )
+
+    def add_defaults(self, fact: Fact, scopes: tuple[ScopeChoice, ...]) -> None:
+        for scope in scopes:
+            held = self.db.exec(select(FactDefault).where(
+                FactDefault.fact_id == fact.id, FactDefault.scope_type == scope.scope_type,
+                FactDefault.scope_id == scope.scope_id)).first()
+            if held is not None:
+                self.result.skipped.append(f"portée {scope.scope_type} déjà présente sur un fait")
+                continue
+            row = create_fact_default(self.db, world_id=self.world_id, fact_id=fact.id,
+                                      scope_type=scope.scope_type, scope_id=scope.scope_id,
+                                      level="knows", created_by=CREATED_BY)
+            self.db.flush()
+            self.record("fact_default", row.id)
+
+    def add_participants(self, fact: Fact, entity_ids: list[str]) -> None:
+        held = set(self.db.exec(select(FactParticipant.entity_id).where(
+            FactParticipant.fact_id == fact.id)).all())
+        fresh = [eid for eid in entity_ids if eid not in held]
+        if len(fresh) < len(entity_ids):
+            self.result.skipped.append("participant déjà rattaché à un fait")
+        for row in attach_participants(self.db, fact=fact, entity_ids=fresh) if fresh else []:
+            self.db.flush()
+            self.record("fact_participant", row.id)
+
+    def knowers(self, fact: Fact, item: dict) -> None:
+        for knower in _list(item, "knowers"):
+            entity_id = self.ids[knower["entity_ref"]]
+            if find_held(self.db, entity_id, {"fact_id": fact.id}) is not None:
+                self.result.skipped.append("une entité connaissait déjà un fait")
+                continue
+            row = write_knowledge(
+                self.db, mode="update", entity_id=entity_id, fact_id=fact.id,
+                level=knower["level"], is_secret=bool(knower.get("is_secret", False)),
+                is_incorrect=bool(knower.get("is_incorrect", False)), changed_by=CREATED_BY,
+            )
+            self.db.flush()
+            self.record("knowledge", row.id)
+
+    def fact(self, item: dict) -> None:
+        participants = [self.ids[ref] for ref in item.get("participants") or []]
+        if item["action"] == "create":
+            rows = add_lore_fact(
+                self.db, world_id=self.world_id, facet=item["facet"], content=item["content"],
+                created_by=CREATED_BY, participant_ids=participants, aspect=item.get("aspect"),
+                scopes=self.scopes(item), mentions=item.get("mentions") or None,
+            )
+            self.db.flush()
+            fact = rows.fact
+            self.record("fact", fact.id)
+            for row in rows.participants:
+                self.record("fact_participant", row.id)
+            for row in rows.defaults:
+                self.record("fact_default", row.id)
+        else:
+            fact = self.db.get(Fact, item["fact_id"])
+            if item["action"] == "rewrite":
+                edit_entity_fact(self.db, fact_id=fact.id, content=item["content"],
+                                 changed_by=CREATED_BY)
+                self.record("fact", fact.id, "updated")
+            self.add_participants(fact, participants)
+            self.add_defaults(fact, self.scopes(item))
+        self.knowers(fact, item)
+
+    def membership(self, item: dict) -> None:
+        entity_id, faction_id = self.ids[item["entity_ref"]], self.ids[item["faction_ref"]]
+        held = self.db.exec(select(FactionMembership).where(
+            FactionMembership.entity_id == entity_id, FactionMembership.faction_id == faction_id,
+            FactionMembership.left_at.is_(None))).first()
+        if held is not None:
+            self.result.skipped.append("appartenance déjà active")
+            return
+        row = write_membership(self.db, mode="open", world_id=self.world_id,
+                               entity_id=entity_id, faction_id=faction_id)
+        self.db.flush()
+        self.record("faction_membership", row.id)
+
+    def control(self, item: dict) -> None:
+        owner_id, location_id = self.ids[item["owner_ref"]], self.ids[item["location_ref"]]
+        held = self.db.exec(select(Relation).where(
+            Relation.type == "controls", Relation.entity_a_id == owner_id,
+            Relation.entity_b_id == location_id)).first()
+        if held is not None:
+            self.result.skipped.append("possession déjà enregistrée")
+            return
+        row = write_relation(self.db, mode="set", world_id=self.world_id, entity_a_id=owner_id,
+                             entity_b_id=location_id, type="controls", value=50,
+                             changed_by=CREATED_BY)
+        self.db.flush()
+        self.record("relation", row.id)
+
+
+def apply_proposal(
+    db: Session, world_id: str, proposal: dict,
+    create_entity: Callable[[str, str], Entity],
+) -> ApplyResult:
+    """Validate, then write the whole proposal. Never commits: the caller
+    commits once on success and rolls back on any exception. A write-site
+    `ValueError` surfaces as `ProposalError`."""
+    refs = validate(db, world_id, proposal)
+    entry = write_lore_entry(db, world_id=world_id, statement=proposal["statement"],
+                             questions=proposal.get("questions"), answers=proposal.get("answers"))
+    db.flush()
+    writer = _Writer(db, world_id, entry.id)
+    try:
+        writer.entities(refs, create_entity)
+        for item in _list(proposal, "facts"):
+            writer.fact(item)
+        for item in _list(proposal, "memberships"):
+            writer.membership(item)
+        for item in _list(proposal, "controls"):
+            writer.control(item)
+    except ProposalError:
+        raise
+    except ValueError as exc:
+        raise ProposalError(f"Écriture refusée : {exc}") from exc
+    return writer.result
diff --git a/src/world_engine/writes/facets.py b/src/world_engine/writes/facets.py
index 9c16956..6687762 100644
--- a/src/world_engine/writes/facets.py
+++ b/src/world_engine/writes/facets.py
@@ -25,8 +25,8 @@ from typing import Any, Optional
 
 from sqlmodel import Session, select
 
-from ..facets import DESCRIPTIVE_FACETS, facet_spec, normalize_aspect
-from ..models import Entity, Fact, FactParticipant
+from ..facets import DESCRIPTIVE_FACETS, FACETS, facet_spec, normalize_aspect
+from ..models import Entity, Fact, FactDefault, FactParticipant
 from ..lore_resolve import normalize_surface
 from ..name_index import CREATOR, PROSE, NameScope, surfaces
 from ..prose_render import fact_text
@@ -263,6 +263,85 @@ def record_appellation(
                            created_by=created_by, scope=scope)
 
 
+@dataclass(frozen=True)
+class LoreFactRows:
+    """What `add_lore_fact` wrote: the fact, its participant rows, its default rows."""
+
+    fact: Fact
+    participants: tuple[FactParticipant, ...]
+    defaults: tuple[FactDefault, ...]
+
+
+def _lore_participants(
+    db: Session, *, world_id: str, facet: str, participant_ids: list[str],
+) -> None:
+    if len(set(participant_ids)) != len(participant_ids):
+        raise ValueError("a participant is listed twice")
+    for entity_id in participant_ids:
+        entity = db.get(Entity, entity_id)
+        if entity is None or entity.world_id != world_id:
+            raise ValueError(f"participant {entity_id!r} is not an entity of this world")
+    spec = facet_spec(facet)
+    if (spec.granularity == "bloc" or facet == "appellation") and len(participant_ids) != 1:
+        raise ValueError(f"a {facet!r} fact takes exactly one participant")
+
+
+def add_lore_fact(
+    db: Session,
+    *,
+    world_id: str,
+    facet: str,
+    content: str,
+    created_by: str,
+    participant_ids: list[str],
+    aspect: Optional[str] = None,
+    scopes: tuple[ScopeChoice, ...] = (),
+    mentions: Optional[list] = None,
+) -> LoreFactRows:
+    """One free fact from the lore writing path (TICKET-0098, BRIEF-0098-C,
+    C-03): any non-typed facet, zero or more participants, zero or more
+    `knows` defaults. `ValueError` on an unknown or typed facet, empty
+    content, a participant outside `world_id` or listed twice, a `bloc` or
+    `appellation` fact without exactly one participant, a second `bloc`
+    fact with the same aspect, a `none` or malformed scope, or the same
+    scope twice. Names in `content` become identity tokens (an appellation
+    on names alone, its owner excluded); the unresolved ones and the
+    declared `mentions` are recorded against the new fact."""
+    spec = FACETS.get(facet)
+    if spec is None or spec.granularity == "typed":
+        raise ValueError(f"facet {facet!r} is not a free-fact facet")
+    if not isinstance(content, str) or not content.strip():
+        raise ValueError("fact content is empty")
+    _lore_participants(db, world_id=world_id, facet=facet, participant_ids=participant_ids)
+    norm_aspect = normalize_aspect(aspect)
+    if spec.granularity == "bloc" and _bloc_exists(
+            db, entity_id=participant_ids[0], facet=facet, aspect=norm_aspect):
+        raise ValueError("bloc facet already has a fact")
+    keys = [(scope.scope_type, scope.scope_id) for scope in scopes]
+    if len(set(keys)) != len(keys):
+        raise ValueError("the same default scope is listed twice")
+    for scope in scopes:
+        _check_scope(scope)
+        if scope.scope_type == "none":
+            raise ValueError("a default scope cannot be 'none'")
+    name_scope = (NameScope("names_only", exclude_entity_id=participant_ids[0])
+                  if facet == "appellation" else PROSE)
+    tokens = tokenize(db, world_id=world_id, text=content, mentions=mentions, scope=name_scope)
+    fact = create_fact(db, world_id=world_id, content=tokens.text, created_by=created_by,
+                       facet=facet, aspect=norm_aspect)
+    db.flush()
+    if tokens.unresolved:
+        record_unresolved(db, world_id=world_id, fact_id=fact.id, items=tokens.unresolved)
+    participants = (attach_participants(db, fact=fact, entity_ids=participant_ids)
+                    if participant_ids else [])
+    defaults = [
+        create_fact_default(db, world_id=world_id, fact_id=fact.id, scope_type=scope.scope_type,
+                            scope_id=scope.scope_id, level="knows", created_by=created_by)
+        for scope in scopes
+    ]
+    return LoreFactRows(fact=fact, participants=tuple(participants), defaults=tuple(defaults))
+
+
 def _descriptive_fact(db: Session, fact_id: str) -> Fact:
     fact = db.get(Fact, fact_id)
     if fact is None:
diff --git a/src/world_engine/writes/lore_entries.py b/src/world_engine/writes/lore_entries.py
new file mode 100644
index 0000000..5b4586a
--- /dev/null
+++ b/src/world_engine/writes/lore_entries.py
@@ -0,0 +1,47 @@
+"""The lore source record's writer (TICKET-0098, BRIEF-0098-B/-C, C-04).
+
+`lore_entry` and `lore_entry_row` are non-canon (they record where canon rows
+came from) and append-only: this module inserts, never updates or deletes;
+the world cascade is their only delete. Nothing here commits; the caller owns
+the transaction.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session
+
+from ..models import LoreEntry, LoreEntryRow
+from ..models.pipeline import LORE_ENTRY_ROW_ACTIONS, LORE_ENTRY_ROW_TABLES
+
+
+def write_lore_entry(
+    db: Session, *, world_id: str, statement: str,
+    questions: Optional[str] = None, answers: Optional[str] = None,
+) -> LoreEntry:
+    """Insert one `lore_entry`. `ValueError` on an empty statement. Blank
+    `questions` / `answers` are stored as NULL."""
+    if not isinstance(statement, str) or not statement.strip():
+        raise ValueError("lore_entry: the statement is empty")
+    entry = LoreEntry(
+        world_id=world_id, statement=statement.strip(),
+        questions=(questions or "").strip() or None,
+        answers=(answers or "").strip() or None,
+    )
+    db.add(entry)
+    return entry
+
+
+def record_entry_row(
+    db: Session, *, entry_id: str, row_table: str, row_id: str, action: str = "created",
+) -> LoreEntryRow:
+    """Insert one `lore_entry_row`. `ValueError` on a table or action outside
+    the schema's CHECK lists."""
+    if row_table not in LORE_ENTRY_ROW_TABLES:
+        raise ValueError(f"lore_entry_row: unknown row_table {row_table!r}")
+    if action not in LORE_ENTRY_ROW_ACTIONS:
+        raise ValueError(f"lore_entry_row: unknown action {action!r}")
+    row = LoreEntryRow(entry_id=entry_id, row_table=row_table, row_id=row_id, action=action)
+    db.add(row)
+    return row
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 91cdd4c..4ef36dc 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17256,6 +17256,33 @@ first injection the creator wants to take back. B3 (typed links between
 facts): reactivates if the day chain (A2) must follow a "why" from fact to
 fact.
 
+## A LORE PROPOSAL IS WRITTEN WHOLE OR NOT AT ALL (TICKET-0098) -- ADD_LORE_FACT AND APPLY_PROPOSAL (BRIEF-0098-c, no schema change)
+
+**What one statement can write (R1, S1, P1).** A proposal holds entities to
+create (character, location, faction, item -- G3) or reuse, facts to create
+(any non-typed facet, zero or more participants), to extend (participants,
+knowers, defaults) or to rewrite (a `bloc` fact only, Q19d), `knows`
+defaults at world/faction/location/rencontre scope (E1), knowers the creator
+checked (level, secret, false belief), faction memberships and `controls`
+edges. Social relations, events and world laws are out (R2).
+
+**One chokepoint for a lore fact.** `writes/facets.py::add_lore_fact`
+extends the entity-fact writer to any free facet and any number of
+participants, because `fact_facets.py` R3 keeps every non-literal facet in
+that module. It tokenizes, guards `bloc`, and writes the defaults.
+
+**All or nothing.** `lore_write_apply.apply_proposal` validates every ref,
+id, facet, scope and level against the proposal's world before writing,
+then writes through the chokepoints in the caller's transaction and records
+each row in `lore_entry_row`. A row that already exists is skipped and
+reported, never duplicated (`find_held`, the participant and membership
+reads, the `controls` pair). Entities are created through an injected
+callable: the commit-free creation core stays with the creator CRUD, which
+this module does not import. No model is called here.
+
+**Rejected.** R2 (relations, laws, events in the first cut): reactivates
+when a story loses its sense without its relation or law.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 809f25c..1c12d65 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -19,6 +19,26 @@ W2 -- migration `scripts/migrate_v2_11_lore_entry.py`, on a v2.10-shaped
    b. at v2.10 it creates both tables, empty, and moves `schema_meta` to
       v2.11;
    c. a second run changes nothing and exits zero.
+C1 -- apply (BRIEF-0098-C, C-02), on a fixture world, through
+   `lore_write_apply.apply_proposal` with an injected entity creator:
+   a. `_GOOD` creates one entity, three facts (an `information` fact with a
+      `world` default and no participant; a multi-participant `coutume` with
+      a `location` default; an `aversion` known by a checked NPC, secret),
+      one knower on an existing fact, one membership and one `controls`
+      edge; every written row has exactly one `lore_entry_row`, and the
+      new entity's name is an identity token in the fact that names it;
+   b. applied twice, the second run writes only its new facts and entity
+      and reports the existing knower, participant, membership, default and
+      `controls` edge as skipped;
+   c. a `rewrite` of a `bloc` fact changes its text, appends the previous
+      one to `change_history`, and records `updated`;
+   d. every row of `_REFUSALS` raises `ProposalError` before any write:
+      the row counts of every recorded table are unchanged;
+   e. a proposal refused by a write site (a second `bloc` fact on the same
+      entity) raises `ProposalError`; after the rollback nothing remains.
+C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
+   `chat(`, no `.commit(`, and import neither `ollama_client` nor any
+   `cockpit` module.
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -41,7 +61,12 @@ MIGRATION = ROOT / "scripts" / "migrate_v2_11_lore_entry.py"
 FAILURES: list[str] = []
 
 _CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
-_LORE_WRITE_FILES: frozenset[str] = frozenset()
+_LORE_WRITE_FILES: frozenset[str] = frozenset({
+    "lore_write_apply.py", "writes/lore_entries.py",
+})
+_PURE_FILES = ("lore_write_apply.py", "writes/lore_entries.py")
+_COUNTED_TABLES = ("entity", "fact", "fact_participant", "fact_default", "knowledge",
+                   "relation", "faction_membership", "lore_entry", "lore_entry_row")
 
 
 def fail(msg: str) -> None:
@@ -140,6 +165,196 @@ def check_w2(db_path: str) -> None:
         fail(f"W2c: second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
 
 
+def _fixture(db):
+    """A world with an NPC (Maëlle), a manor (location), a guild (faction)
+    and Maëlle's `description` (bloc) fact."""
+    from world_engine.models import Character, Entity, Faction, Location, World
+    from world_engine.writes.facets import add_entity_fact
+
+    world = World(name="Fixture 0098")
+    db.add(world)
+    db.flush()
+    ids = {}
+    for key, etype, name, ext in (("npc", "character", "Maëlle", Character),
+                                  ("manor", "location", "Manoir Gris", Location),
+                                  ("guild", "faction", "Guilde des Passeurs", Faction)):
+        entity = Entity(world_id=world.id, type=etype, name=name)
+        db.add(entity)
+        db.flush()
+        kwargs = {"world_id": world.id, "character_type": "npc"} if ext is Character else {}
+        db.add(ext(id=entity.id, **kwargs))
+        ids[key] = entity.id
+    db.flush()
+    bloc = add_entity_fact(db, entity_id=ids["npc"], facet="description",
+                           content="Une passeuse discrète.", created_by="fixture")
+    old = add_entity_fact(db, entity_id=ids["manor"], facet="description",
+                          content="Un manoir aux volets gris.", created_by="fixture")
+    db.commit()
+    ids.update(world=world.id, bloc=bloc.id, old=old.id)
+    return ids
+
+
+def _creator(db, world_id):
+    from world_engine.models import Character, Entity, Faction, Item, Location
+
+    ext = {"character": Character, "location": Location, "faction": Faction, "item": Item}
+
+    def create(name, etype):
+        entity = Entity(world_id=world_id, type=etype, name=name)
+        db.add(entity)
+        db.flush()
+        kwargs = {"world_id": world_id, "character_type": "npc"} if etype == "character" else {}
+        db.add(ext[etype](id=entity.id, **kwargs))
+        return entity
+    return create
+
+
+def _good(ids):
+    return {
+        "statement": "Un tunnel relie le Manoir Gris au port ; la vimm y transite.",
+        "entities": [
+            {"ref": "e1", "action": "existing", "entity_id": ids["npc"]},
+            {"ref": "e2", "action": "existing", "entity_id": ids["manor"]},
+            {"ref": "e3", "action": "existing", "entity_id": ids["guild"]},
+            {"ref": "e4", "action": "create", "name": "Vimm", "type": "item"},
+        ],
+        "facts": [
+            {"ref": "f1", "action": "create", "facet": "information",
+             "content": "La Vimm est interdite dans tout le royaume.", "participants": [],
+             "defaults": [{"scope_type": "world"}]},
+            {"ref": "f2", "action": "create", "facet": "coutume", "aspect": "values",
+             "content": "Au manoir, on attend la permission avant de parler.",
+             "participants": ["e2", "e1"],
+             "defaults": [{"scope_type": "location", "scope_ref": "e2"}]},
+            {"ref": "f3", "action": "create", "facet": "aversion",
+             "content": "Maëlle hait qu'on lui coupe la parole.", "participants": ["e1"],
+             "knowers": [{"entity_ref": "e1", "level": "knows", "is_secret": True}]},
+            {"ref": "f4", "action": "existing", "fact_id": ids["old"], "participants": ["e3"],
+             "defaults": [{"scope_type": "faction", "scope_ref": "e3"}],
+             "knowers": [{"entity_ref": "e1", "level": "partial"}]},
+        ],
+        "memberships": [{"entity_ref": "e1", "faction_ref": "e3"}],
+        "controls": [{"owner_ref": "e1", "location_ref": "e2"}],
+    }
+
+
+_REFUSALS = (
+    ("no statement", lambda p: p.pop("statement")),
+    ("entity type not allowed", lambda p: p["entities"][3].update(type="magic")),
+    ("unknown existing entity", lambda p: p["entities"][0].update(entity_id="nope")),
+    ("duplicate entity ref", lambda p: p["entities"].append(dict(p["entities"][0]))),
+    ("typed facet", lambda p: p["facts"][0].update(facet="lien")),
+    ("unknown facet", lambda p: p["facts"][0].update(facet="humeur")),
+    ("bloc with two participants", lambda p: p["facts"][1].update(facet="description")),
+    ("unknown participant ref", lambda p: p["facts"][2].update(participants=["e9"])),
+    ("unknown level", lambda p: p["facts"][2]["knowers"][0].update(level="certain")),
+    ("secret not a bool", lambda p: p["facts"][2]["knowers"][0].update(is_secret="oui")),
+    ("same knower twice", lambda p: p["facts"][2]["knowers"].append(dict(p["facts"][2]["knowers"][0]))),
+    ("faction scope on a location", lambda p: p["facts"][3]["defaults"][0].update(scope_ref="e2")),
+    ("world scope with a ref", lambda p: p["facts"][0]["defaults"][0].update(scope_ref="e1")),
+    ("unknown scope", lambda p: p["facts"][0]["defaults"][0].update(scope_type="ville")),
+    ("same scope twice", lambda p: p["facts"][0]["defaults"].append({"scope_type": "world"})),
+    ("fact of another world", lambda p: p["facts"][3].update(fact_id="nope")),
+    ("rewrite of a non-bloc fact", lambda p: p["facts"].append(
+        {"ref": "f9", "action": "rewrite", "fact_id": "__f3__", "content": "x"})),
+    ("membership of a location", lambda p: p["memberships"][0].update(entity_ref="e2")),
+    ("control of a faction", lambda p: p["controls"][0].update(location_ref="e3")),
+    ("nothing to write", lambda p: [p.update(facts=[], memberships=[], controls=[])]),
+)
+
+
+def _counts(db) -> dict:
+    from sqlalchemy import text
+
+    return {t: db.exec(text(f"SELECT COUNT(*) FROM {t}")).one()[0] for t in _COUNTED_TABLES}
+
+
+def check_c1() -> None:
+    import copy
+
+    from sqlmodel import Session
+
+    from world_engine import lore_write_apply as lwa
+    from world_engine.db import engine
+    from world_engine.models import Fact, LoreEntryRow
+    from world_engine.prose_render import fact_text
+
+    with Session(engine) as db:
+        ids = _fixture(db)
+        before = _counts(db)
+        result = lwa.apply_proposal(db, ids["world"], _good(ids), _creator(db, ids["world"]))
+        db.commit()
+        after = _counts(db)
+        grown = {t: after[t] - before[t] for t in _COUNTED_TABLES}
+        want = {"entity": 1, "fact": 3, "fact_participant": 4, "fact_default": 3, "knowledge": 2,
+                "relation": 1, "faction_membership": 1, "lore_entry": 1}
+        for table, n in want.items():
+            if grown[table] != n:
+                fail(f"C1a: {table} grew by {grown[table]}, expected {n}")
+        recorded = sum(n for t, n in grown.items() if t not in ("lore_entry", "lore_entry_row"))
+        if grown["lore_entry_row"] != recorded:
+            fail(f"C1a: {grown['lore_entry_row']} lore_entry_row for {recorded} written rows")
+        facts = db.exec(__import__("sqlmodel").select(Fact).where(Fact.created_by == "creator_lore")).all()
+        interdite = [f for f in facts if "interdite" in fact_text(db, f)]
+        if not interdite or "[[e:" not in interdite[0].content_raw:
+            fail("C1a: the new entity's name is not an identity token in the fact naming it")
+        f3 = next((f for f in facts if f.facet == "aversion"), None)
+        again = _good(ids)
+        again["entities"][3]["name"] = "Vimm noire"
+        lwa.apply_proposal(db, ids["world"], again, _creator(db, ids["world"]))
+        second = lwa.apply_proposal(db, ids["world"], _good(ids), _creator(db, ids["world"]))
+        db.commit()
+        if len(second.skipped) < 4:
+            fail(f"C1b: a second apply skipped {second.skipped}, expected the existing rows")
+        rewrite = {"statement": "Maëlle a changé.", "entities": [], "facts": [
+            {"ref": "f1", "action": "rewrite", "fact_id": ids["bloc"],
+             "content": "Une passeuse devenue célèbre."}]}
+        res = lwa.apply_proposal(db, ids["world"], rewrite, _creator(db, ids["world"]))
+        db.commit()
+        bloc = db.get(Fact, ids["bloc"])
+        rows = db.exec(__import__("sqlmodel").select(LoreEntryRow).where(
+            LoreEntryRow.entry_id == res.entry_id)).all()
+        if ("célèbre" not in fact_text(db, bloc) or not bloc.change_history
+                or [(r.row_table, r.action) for r in rows] != [("fact", "updated")]):
+            fail("C1c: the bloc rewrite did not update in place with history and one row")
+        for label, mutate in _REFUSALS:
+            proposal = copy.deepcopy(_good(ids))
+            mutate(proposal)
+            for item in proposal.get("facts") or []:
+                if item.get("fact_id") == "__f3__":
+                    item["fact_id"] = f3.id if f3 else "nope"
+            before = _counts(db)
+            try:
+                lwa.apply_proposal(db, ids["world"], proposal, _creator(db, ids["world"]))
+                fail(f"C1d: {label}: accepted")
+            except lwa.ProposalError:
+                pass
+            db.rollback()
+            if _counts(db) != before:
+                fail(f"C1d: {label}: rows changed")
+        before = _counts(db)
+        second_bloc = {"statement": "Encore.", "entities": [
+            {"ref": "e1", "action": "existing", "entity_id": ids["npc"]}], "facts": [
+            {"ref": "f1", "action": "create", "facet": "description", "content": "Autre.",
+             "participants": ["e1"]}]}
+        try:
+            lwa.apply_proposal(db, ids["world"], second_bloc, _creator(db, ids["world"]))
+            fail("C1e: a second bloc fact was accepted")
+        except lwa.ProposalError:
+            pass
+        db.rollback()
+        if _counts(db) != before:
+            fail("C1e: a refused write left rows behind")
+
+
+def check_c2() -> None:
+    for rel in _PURE_FILES:
+        text = (SRC / rel).read_text(encoding="utf-8")
+        for needle in ("chat(", ".commit(", "ollama_client", "cockpit"):
+            if needle in text:
+                fail(f"C2: {rel} contains {needle!r}")
+
+
 def main() -> int:
     tmp = tempfile.mkdtemp(prefix="lore_write_")
     db_path = f"{tmp}/w.db"
@@ -149,12 +364,15 @@ def main() -> int:
     check_l0()
     check_w1()
     check_w2(db_path)
+    check_c1()
+    check_c2()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
-          "v2.11 declares the source record and migrates from v2.10 only")
+          "v2.11 declares the source record and migrates from v2.10 only; a proposal "
+          "writes all or nothing, each row recorded, existing rows skipped")
     return 0
 
 
````

## Scope OUT

- Any model call, prompt or route (D, E).
- Social relations, events, world laws (R2).
- New entity types (G2) or creating entities in this module: the creator is injected (the route wires `_create_entity_core` in E).
- Deduplicating facts by text: two identical sentences are two facts, as in creator CRUD.
- A default level other than `knows`.
- Every later brief of the lot: BRIEF-0098-D, BRIEF-0098-E, BRIEF-0098-F.

## Invariants to defend

**Two canon-write paths for rows:** this is creator CRUD; every canon row goes through `writes/` (`add_lore_fact`, `write_knowledge`, `write_membership`, `write_relation`, `edit_entity_fact`), never a bare `db.add` on a canon table. **A `fact_participant` row is the aboutness claim; `(fact_id, entity_id)` is unique, so every writer reads before it writes.** **A `knowledge` row is identified by its fact:** `find_held` before `write_knowledge`. **Secrets are structural:** a secret is a stored row; defaults carry none (R-16). **History is sacred:** a `bloc` rewrite goes through `edit_entity_fact` (history appended).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `fact_facets.py` R3 flags a `create_fact(` outside `writes/facets.py`.
- `single_canon_write.py` flags a site in `lore_write_apply.py`.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- Any existing caller of `add_entity_fact` whose behaviour could have used `add_lore_fact` (not to be changed).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `lore_write.py` → `PASS … a proposal writes all or nothing, each row recorded, existing rows skipped`.
- `fact_facets.py`, `single_canon_write.py`, `identity_tokens.py`, `knowledge_identity.py`, `module_budget.py`, `function_length.py` → `PASS`.
- Mutation test: in `_Writer.knowers`, replace the `find_held(...) is not None` test by `False`; `lore_write.py` no longer passes (the second apply raises `IntegrityError` on `idx_knowledge_entity_fact`); revert.
- `corpus_gate.py` → 128/128.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A LORE PROPOSAL IS WRITTEN WHOLE OR NOT AT ALL (TICKET-0098) … (BRIEF-0098-c, no schema change)`. No schema change; the CLAUDE.md invariant lands with the route (E).
