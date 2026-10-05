<!-- slug: dated-resolution -->
# BRIEF 0105-D — "A default is learned by a contact after it, and kept"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: BRIEF-0105-C
Commit header for decisions: `(BRIEF-0105-d, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/knowledge_resolve.py:19` → `   location or any ancestor via \`location.parent_location_id\` — nearest`; `:104` → `def _resolve_tiers(`; `:219` → `def resolve_levels_for_entity(db: Session, entity_id: str) -> dict[str, str]:`; `:334` → `def resolve_default_rows(`.
- `src/world_engine/knowledge_resolve.py` imports `acquaintances` from `.encounters`; its public names are `meets_floor`, `KNOWN_EDGE_FLOOR`, `DEFAULT_SHARE_THRESHOLD`, `resolve_knowledge_level`, `resolve_levels_for_entity`, `resolve_public_level`, `resolve_public_levels`, `resolve_default_rows`.
- `src/world_engine/passages.py` and `src/world_engine/fact_versions.py` exist (B, C); `Rencontre.last_at` and `Passage` exist (A).
- `tooling/verify/checks/knowledge_resolution.py:139` → `    # Tier 2b — nearest ancestor beats a farther one.`; `:350` → `    cases[9] = (f9, C09_FALLBACK)`, the last case of `_build_c09_fixture`.
- `world-engine-schema.md:681` → `registry) at \`level\`.` (end of the `fact_default` resolution paragraph).

## Facts carried

### R-02 — the encounter registry [M]
Opened: `src/world_engine/models/ephemeral.py:156-183` (`Rencontre`,
`ENCOUNTER_SOURCES`); `src/world_engine/encounters.py:1-132`; enumeration
E2.
Finding: one row per unordered pair; `record_encounter` returns `None` and
writes nothing when the pair exists (`:57-58`); `first_at` is the earliest
encounter. Seven live sites call the three recorders: scene visit,
gathering creation and migration, conversation start, gathering join,
schedule co-presence, social relation birth (`writes/relations.py:222-230`).
Consequence: `last_at` is added; an existing pair's `last_at` moves forward
on every source but `relation` (L1). `record_encounter`'s return contract is
kept.

### R-03 — schedules name places without moving anyone [M]
Opened: `src/world_engine/models/schedule.py:32-60` (`NpcSchedule`);
`src/world_engine/writes/config.py:413-512` (`write_npc_schedule`: DELETE at
`:478`, `_record_schedule_encounters` at `:491`);
`src/world_engine/schedule_reads.py:116-161` (`where_is`, `who_is_at`:
position computed at read time).
Finding: a schedule never writes `current_location_id`; an NPC "at the forge
each evening" is never placed there. `write_npc_schedule` is at the
80-line ceiling, and `npc_schedule.py` requires its DELETE inside it;
`single_canon_write.py` allows `npc_schedule` writes only from it.
Consequence: the schedule's passages are recorded by a helper called before
the DELETE (old rows still readable), which also records the encounters;
read time treats schedule places and slot co-presence as a contact right
now.

### R-05 — resolution on `main` [M]
Opened: `src/world_engine/knowledge_resolve.py:1-363`.
Finding: seven tiers — stored row, self (participant of a descriptive
fact), `rencontre` (any acquaintance, no date), `location` (current place
and ancestors, NEAREST wins), `faction` (ACTIVE memberships, highest),
`world`, `fact.default_level`. `resolve_default_rows` builds transient rows
with the fact's current text. Resolution never writes.
Consequence: D replaces tiers 3-5 with dated contacts (B5, C1, J2) and adds
`as_of`; the public-floor functions keep tiers 6-7 only.

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

### R-17 — the checks the lot passes [M]
Opened: `tooling/verify/checks/encounter_registry.py:1-60` (R1-R4);
`knowledge_resolution.py:74-166, 247-352` (tier 2b nearest; C-09 case 4:
the encounter is recorded before the defaults); `lore_write.py:300-400`
(C1c, `_REFUSALS`, the `__f3__` substitution); `world_cascade.py:1-40,
67-120` (W1 coverage, W3 fixture); `fact_facets.py:116-145`;
`function_length.py` (80 lines); `npc_schedule.py`;
`single_canon_write.py`; `claude_md_contract.py` (38 000 characters, 100
per line); `frontend_build_fresh.py`; `effect_self_write.py`.
Finding: C-09 case 4 and tier 2b encode the rules B5 and C1 replace;
`passage` is world-scoped and must be cascaded.
Consequence: D amends the two fixtures (named in its Scope IN); A adds
`passage` to the cascade and its fixture.

## Contracts

### C-01 — the registries (schema v2.14)
Produced by: BRIEF-0105-A   Consumed by: BRIEF-0105-B, D
`passage(id TEXT PK, world_id FK world NOT NULL, entity_id FK entity NOT
NULL, location_id FK entity NOT NULL, last_at DATETIME NOT NULL)`, UNIQUE
`idx_passage_entity_location(entity_id, location_id)`, index
`idx_passage_location(location_id)`; model `Passage` in
`models/ephemeral.py`, exported by `models`. `rencontre.last_at DATETIME`
nullable in SQL, `Optional[datetime]` in the model. Both cascaded with the
world (`_DIRECT_WORLD_SCOPED_DELETES`).
Error and empty cases: the migration refuses below v2.13; leaves no NULL
`last_at`.

### C-02 — passages
Produced by: BRIEF-0105-B   Consumed by: BRIEF-0105-D (through C-01), E
`passages.record_passage(db, *, world_id, entity_id, location_id, at=None)
-> Passage`: creates the pair's row or moves `last_at` forward to `at`
(default now, UTC), never back; finds a pending row of the same flush.
`passages.record_passages(db, *, world_id, entity_id, location_ids,
at=None) -> None`: each distinct place. `passages.listener_registered() ->
bool`. The `before_flush` listener on `sqlalchemy.orm.Session` records, for
every `Character` new with a place or whose `current_location_id` changed,
the place entered and the place left, at the flush's time; `db.py` imports
`passages` at module end. `write_npc_schedule` records the passages of every
place its old and new rows name. No function commits.
Error and empty cases: a character without place records nothing.

### C-03 — the last contact of an encounter
Produced by: BRIEF-0105-B   Consumed by: BRIEF-0105-D
`encounters.record_encounter(...)` unchanged signature and return (new row
or `None`). A new row has `last_at = first_at = at`. An existing pair's
`last_at` moves forward to `at` unless `source == "relation"`; never back.

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

## Context

The registries are filled (B) and the version rule exists (C). This brief makes resolution read them: a `rencontre`, `location` or `faction` default is known through a contact at or after it was written, and kept (B5, J2); among places the highest level wins (C1); being at the same place or in the same schedule slot is a contact right now (O1, L1). Each resolution also says when its holder last saw the fact as it is (N1). The level-only functions keep their signatures, so no caller changes in this brief.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - rewrites `knowledge_resolve.py` up to `resolve_public_level` (C-06): docstring, `Known`, the `_Contacts` context built once per entity (passages and their ancestors, encounters, current place and schedule as contacts right now, co-location and schedule-slot co-presence, memberships with their `left_at`), `_tier_level`, `_as_of`, `_resolve_fact`, `resolve_knowledge`, `resolve_knowledge_level`, `resolve_known_for_entity`, `resolve_levels_for_entity`, `_public_tier` (the public floor keeps tiers 6-7); `resolve_default_rows` is unchanged here;
   - amends `tooling/verify/checks/knowledge_resolution.py`: tier 2b expects the highest level (root `knows`, child `partial` → `knows`); `_build_c09_fixture` records one more encounter with the friend after the last default (B5); docstring;
   - amends the `fact_default` resolution paragraph of `world-engine-schema.md`;
   - adds D1-D2 to `fact_learning.py`; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): resolution dated by contact, Known(level, as_of) (BRIEF-0105-d)`.

````diff
diff --git a/src/world_engine/knowledge_resolve.py b/src/world_engine/knowledge_resolve.py
index 1d66fc2..ecbd1cf 100644
--- a/src/world_engine/knowledge_resolve.py
+++ b/src/world_engine/knowledge_resolve.py
@@ -1,34 +1,47 @@
 """Scoped default knowledge-level resolution (TICKET-0082, BRIEF-0082-c,
-G2a).
+G2a), dated by contact (TICKET-0105, BRIEF-0105-D, B5).
 
-`resolve_knowledge_level` is the single resolution authority for "what level
-does this entity hold on this fact", total over the six-value ladder
-(`writes/knowledge.py::KNOWLEDGE_LEVEL_LADDER`) — precedence, most specific
-first:
+`resolve_knowledge` is the single resolution authority for "what does this
+entity hold of this fact": a `Known(level, as_of)`, total over the six-value
+ladder (`writes/knowledge.py::KNOWLEDGE_LEVEL_LADDER`). Precedence, most
+specific first:
 
-1. a stored `knowledge` row for `(entity_id, fact_id)` — wins outright,
+1. a stored `knowledge` row for `(entity_id, fact_id)` -- wins outright,
    including when it is `'unaware'`;
 2. self: the entity is a `fact_participant` of the fact AND the fact's
-   facet is in `facets.DESCRIPTIVE_FACETS` — `'knows'` (TICKET-0091, Q6a,
-   Q18a: an entity knows what is said of it, not every information it
-   takes part in);
-3. rencontre: a `fact_default` at `scope_type='rencontre'` whose
-   `scope_id` is one of the entity's acquaintances
-   (`encounters.acquaintances`) — the HIGHEST level across several wins;
-4. a `fact_default` at `scope_type='location'` for the entity's current
-   location or any ancestor via `location.parent_location_id` — nearest
-   ancestor wins;
-5. a `fact_default` at `scope_type='faction'` for any faction the entity
-   holds an ACTIVE membership in (`left_at IS NULL`) — the HIGHEST level
-   across several such memberships wins;
+   facet is in `facets.DESCRIPTIVE_FACETS` -- `'knows'` (TICKET-0091, Q6a,
+   Q18a);
+3. rencontre: a `fact_default` at `scope_type='rencontre'` whose `scope_id`
+   the entity met (`rencontre.last_at`) AT OR AFTER the default was written,
+   or is in contact with right now -- the HIGHEST level wins;
+4. location: a `fact_default` at `scope_type='location'` whose place, or a
+   place inside it, the entity was in (`passage.last_at`) at or after the
+   default was written, or is in right now -- the HIGHEST level wins (C1);
+5. faction: a `fact_default` at `scope_type='faction'` for a faction the
+   entity belongs to, or belonged to at or after the default was written
+   (J2) -- the HIGHEST level wins;
 6. a `fact_default` at `scope_type='world'`;
-7. `fact.default_level` — always present (NOT NULL), so this tier never
-   fails to produce a value.
+7. `fact.default_level` -- always present (NOT NULL).
 
-`resolve_levels_for_entity` is the batch companion: one pass over every
-fact in the entity's world, returning only the facts resolving above
-`'unaware'`, so a context assembler calls it once per assembly rather than
-once per fact.
+A fact once learned stays learned: tiers 3-5 read the LAST contact, so
+leaving a place, a group or a person forgets nothing.
+
+Contact "right now" (no date to compare, always in contact): being in a
+place or a place inside it (`current_location_id` and its ancestors), a
+place one's schedule names, an entity at the same exact current location
+(O1) or sharing one of one's schedule slots (L1), an active membership.
+
+`as_of` is when the entity last saw the fact as it is (N1): the latest
+contact with any of the fact's anchors -- its participants and the
+entities its non-world defaults name -- or, for a stored row, that or the
+row's `updated_at`, whichever is later. It is `None` (always current) for
+a fact with a `world` default, for one's own facts (tier 2), and at tiers
+6-7. `fact_versions.version_text` turns it into the text the entity knows.
+
+`resolve_known_for_entity` is the batch companion: every fact of the
+entity's world resolving above `'unaware'`, each context query run once.
+`resolve_knowledge_level` and `resolve_levels_for_entity` return the level
+alone.
 
 # A resolved default never carries is_secret. Secrecy is a property of a
 # stored knowledge row, structurally excluded at query level by the
@@ -41,14 +54,17 @@ is ever written back as a `knowledge` row.
 
 from __future__ import annotations
 
-from typing import Optional
+from dataclasses import dataclass, field
+from datetime import UTC, datetime
+from typing import Iterable, Optional
 
 from sqlmodel import Session, select
 
-from .encounters import acquaintances
+from .fact_versions import utc
 from .facets import DESCRIPTIVE_FACETS
 from .models import (
     Character, Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, Location,
+    NpcSchedule, Passage, Rencontre,
 )
 from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER
 
@@ -61,6 +77,14 @@ DEFAULT_SHARE_THRESHOLD = 50
 KNOWN_EDGE_FLOOR = "partial"
 
 
+@dataclass(frozen=True)
+class Known:
+    """What an entity holds of a fact: its level, and when it last saw the
+    fact as it is (`None`: always current)."""
+    level: str
+    as_of: Optional[datetime]
+
+
 def meets_floor(level: str, floor: str) -> bool:
     """True iff `level` is at or above `floor` on `KNOWLEDGE_LEVEL_LADDER`.
     The one place a floor comparison indexes the ladder — callers (e.g.
@@ -69,214 +93,202 @@ def meets_floor(level: str, floor: str) -> bool:
     return KNOWLEDGE_LEVEL_LADDER.index(level) >= KNOWLEDGE_LEVEL_LADDER.index(floor)
 
 
-def _location_ancestor_chain(db: Session, entity_id: str) -> list[str]:
-    """The entity's current location, then each ancestor up
-    `parent_location_id`, nearest first. Empty when the entity has no
-    `Character` row or no current location. Cycle-safe (stops on repeat)."""
-    character = db.get(Character, entity_id)
-    if character is None or not character.current_location_id:
-        return []
-    chain: list[str] = []
-    seen: set[str] = set()
-    current_id: Optional[str] = character.current_location_id
-    while current_id and current_id not in seen:
-        chain.append(current_id)
-        seen.add(current_id)
-        location = db.get(Location, current_id)
-        current_id = location.parent_location_id if location else None
-    return chain
+def _highest_level(levels: list[str]) -> str:
+    return max(levels, key=KNOWLEDGE_LEVEL_LADDER.index)
 
 
-def _active_faction_ids(db: Session, entity_id: str) -> list[str]:
-    rows = db.exec(
-        select(FactionMembership).where(
-            FactionMembership.entity_id == entity_id,
-            FactionMembership.left_at.is_(None),
-        )
-    ).all()
-    return [row.faction_id for row in rows]
+def _later(a: Optional[datetime], b: Optional[datetime]) -> Optional[datetime]:
+    if a is None:
+        return b
+    if b is None:
+        return a
+    return max(a, b)
 
 
-def _highest_level(levels: list[str]) -> str:
-    return max(levels, key=KNOWLEDGE_LEVEL_LADDER.index)
+@dataclass
+class _Contacts:
+    """The perceiver's dated contacts, fetched once. Each map holds the last
+    contact per entity id; `now` stands for contact right now."""
+    now: datetime
+    met: dict[str, datetime] = field(default_factory=dict)
+    places: dict[str, datetime] = field(default_factory=dict)
+    factions: dict[str, datetime] = field(default_factory=dict)
 
+    def any(self, entity_id: str) -> Optional[datetime]:
+        """The last contact with `entity_id` through any registry."""
+        return _later(_later(self.met.get(entity_id), self.places.get(entity_id)),
+                      self.factions.get(entity_id))
 
-def _resolve_tiers(
-    *,
-    stored_level: Optional[str],
-    self_level: Optional[str],
-    rencontre_levels: list[str],
-    location_chain: list[str],
-    location_defaults: dict[str, str],
-    faction_ids: list[str],
-    faction_defaults: dict[str, str],
-    world_default: Optional[str],
-    fallback_level: str,
-) -> str:
-    """Pure precedence resolution over already-fetched context (item 2/G2a).
-    Shared by the single-fact and batch entry points so both apply the
-    identical rule."""
-    if stored_level is not None:
-        return stored_level
-    if self_level is not None:
-        return self_level
-    if rencontre_levels:
-        return _highest_level(rencontre_levels)
-    for location_id in location_chain:
-        if location_id in location_defaults:
-            return location_defaults[location_id]
-    faction_levels = [
-        faction_defaults[faction_id]
-        for faction_id in faction_ids
-        if faction_id in faction_defaults
-    ]
-    if faction_levels:
-        return _highest_level(faction_levels)
-    if world_default is not None:
-        return world_default
-    return fallback_level
 
+def _keep(target: dict[str, datetime], key: str, at: datetime) -> None:
+    if key not in target or target[key] < at:
+        target[key] = at
 
-def resolve_knowledge_level(db: Session, entity_id: str, fact_id: str) -> str:
-    """Total: always returns one of the six `KNOWLEDGE_LEVEL_LADDER` values,
-    never `None` — tier 7 (`fact.default_level`) is NOT NULL by schema."""
-    fact = db.get(Fact, fact_id)
-    stored = db.exec(
-        select(Knowledge).where(
-            Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id,
-        )
-    ).first()
-    stored_level = stored.level if stored is not None else None
 
-    self_level: Optional[str] = None
-    if fact is not None and fact.facet in DESCRIPTIVE_FACETS:
-        participant = db.exec(
-            select(FactParticipant).where(
-                FactParticipant.fact_id == fact_id, FactParticipant.entity_id == entity_id,
-            )
-        ).first()
-        if participant is not None:
-            self_level = "knows"
-
-    rencontre_levels: list[str] = []
-    known_ids = acquaintances(db, entity_id)
-    if known_ids:
-        rows = db.exec(
-            select(FactDefault).where(
-                FactDefault.fact_id == fact_id,
-                FactDefault.scope_type == "rencontre",
-                FactDefault.scope_id.in_(known_ids),
-            )
-        ).all()
-        rencontre_levels = [row.level for row in rows]
-
-    location_chain = _location_ancestor_chain(db, entity_id)
-    location_defaults: dict[str, str] = {}
-    if location_chain:
-        rows = db.exec(
-            select(FactDefault).where(
-                FactDefault.fact_id == fact_id,
-                FactDefault.scope_type == "location",
-                FactDefault.scope_id.in_(location_chain),
-            )
-        ).all()
-        location_defaults = {row.scope_id: row.level for row in rows}
-
-    faction_ids = _active_faction_ids(db, entity_id)
-    faction_defaults: dict[str, str] = {}
-    if faction_ids:
-        rows = db.exec(
-            select(FactDefault).where(
-                FactDefault.fact_id == fact_id,
-                FactDefault.scope_type == "faction",
-                FactDefault.scope_id.in_(faction_ids),
-            )
-        ).all()
-        faction_defaults = {row.scope_id: row.level for row in rows}
+def _ancestors(db: Session, location_id: str, memo: dict[str, list[str]]) -> list[str]:
+    """`location_id` then each ancestor up `parent_location_id`; cycle-safe."""
+    if location_id in memo:
+        return memo[location_id]
+    chain: list[str] = []
+    current: Optional[str] = location_id
+    while current and current not in chain:
+        chain.append(current)
+        row = db.get(Location, current)
+        current = row.parent_location_id if row else None
+    memo[location_id] = chain
+    return chain
 
-    world_row = db.exec(
-        select(FactDefault).where(
-            FactDefault.fact_id == fact_id, FactDefault.scope_type == "world",
-        )
-    ).first()
-    world_default = world_row.level if world_row is not None else None
 
-    fallback_level = fact.default_level if fact is not None else "unaware"
+def _place_contacts(db: Session, entity_id: str, char: Optional[Character],
+                    schedule: list[NpcSchedule], ctx: _Contacts) -> None:
+    memo: dict[str, list[str]] = {}
+    for row in db.exec(select(Passage).where(Passage.entity_id == entity_id)).all():
+        for place in _ancestors(db, row.location_id, memo):
+            _keep(ctx.places, place, utc(row.last_at))
+    now_places = [s.location_id for s in schedule]
+    if char is not None and char.current_location_id:
+        now_places.append(char.current_location_id)
+    for location_id in now_places:
+        for place in _ancestors(db, location_id, memo):
+            ctx.places[place] = ctx.now
+
+
+def _met_contacts(db: Session, entity_id: str, char: Optional[Character],
+                  schedule: list[NpcSchedule], ctx: _Contacts) -> None:
+    for row in db.exec(select(Rencontre).where(
+            (Rencontre.entity_lo_id == entity_id) | (Rencontre.entity_hi_id == entity_id))).all():
+        other = row.entity_hi_id if row.entity_lo_id == entity_id else row.entity_lo_id
+        _keep(ctx.met, other, utc(row.last_at or row.first_at))
+    present: set[str] = set()
+    if char is not None and char.current_location_id:
+        present.update(db.exec(select(Character.id).where(
+            Character.current_location_id == char.current_location_id)).all())
+    for slot in schedule:
+        present.update(db.exec(select(NpcSchedule.npc_id).where(
+            NpcSchedule.location_id == slot.location_id, NpcSchedule.phase == slot.phase)).all())
+    present.discard(entity_id)
+    for other in present:
+        ctx.met[other] = ctx.now
+
+
+def _contacts(db: Session, entity_id: str) -> _Contacts:
+    ctx = _Contacts(now=datetime.now(UTC))
+    char = db.get(Character, entity_id)
+    schedule = list(db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == entity_id)).all())
+    _place_contacts(db, entity_id, char, schedule, ctx)
+    _met_contacts(db, entity_id, char, schedule, ctx)
+    for row in db.exec(select(FactionMembership).where(
+            FactionMembership.entity_id == entity_id)).all():
+        _keep(ctx.factions, row.faction_id, ctx.now if row.left_at is None else utc(row.left_at))
+    return ctx
+
+
+_SCOPE_CONTACTS = {"rencontre": "met", "location": "places", "faction": "factions"}
+
+
+def _tier_level(ctx: _Contacts, defaults: list[FactDefault], scope_type: str) -> Optional[str]:
+    """The highest level among `scope_type` defaults whose scope the entity
+    was in contact with at or after the default was written."""
+    contacts = getattr(ctx, _SCOPE_CONTACTS[scope_type])
+    levels = []
+    for row in defaults:
+        if row.scope_type != scope_type:
+            continue
+        seen = contacts.get(row.scope_id)
+        if seen is not None and seen >= utc(row.created_at):
+            levels.append(row.level)
+    return _highest_level(levels) if levels else None
+
+
+def _as_of(ctx: _Contacts, defaults: list[FactDefault], participants: Iterable[str],
+           stored: Optional[Knowledge]) -> Optional[datetime]:
+    """When the entity last saw the fact as it is (N1); `None`: current."""
+    if any(row.scope_type == "world" for row in defaults):
+        return None
+    anchors = set(participants) | {row.scope_id for row in defaults if row.scope_id}
+    seen: Optional[datetime] = None
+    for anchor in anchors:
+        seen = _later(seen, ctx.any(anchor))
+    if stored is not None and stored.updated_at is not None:
+        seen = _later(seen, utc(stored.updated_at))
+    return seen
+
+
+def _resolve_fact(ctx: _Contacts, entity_id: str, fact: Fact, defaults: list[FactDefault],
+                  participants: set[str], stored: Optional[Knowledge]) -> Known:
+    """Tiers 1-7 for one fact over already-fetched context (module docstring)."""
+    if stored is not None:
+        return Known(stored.level, _as_of(ctx, defaults, participants, stored))
+    if entity_id in participants and fact.facet in DESCRIPTIVE_FACETS:
+        return Known("knows", None)
+    for scope_type in ("rencontre", "location", "faction"):
+        level = _tier_level(ctx, defaults, scope_type)
+        if level is not None:
+            return Known(level, _as_of(ctx, defaults, participants, None))
+    world = [row.level for row in defaults if row.scope_type == "world"]
+    if world:
+        return Known(world[0], None)
+    return Known(fact.default_level, None)
+
+
+def resolve_knowledge(db: Session, entity_id: str, fact_id: str) -> Known:
+    """Total: one of the six `KNOWLEDGE_LEVEL_LADDER` values, never `None`;
+    `Known("unaware", None)` for an unknown fact id."""
+    fact = db.get(Fact, fact_id)
+    if fact is None:
+        return Known("unaware", None)
+    stored = db.exec(select(Knowledge).where(
+        Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
+    defaults = list(db.exec(select(FactDefault).where(FactDefault.fact_id == fact_id)).all())
+    participants = set(db.exec(select(FactParticipant.entity_id).where(
+        FactParticipant.fact_id == fact_id)).all())
+    return _resolve_fact(_contacts(db, entity_id), entity_id, fact, defaults, participants, stored)
 
-    return _resolve_tiers(
-        stored_level=stored_level,
-        self_level=self_level,
-        rencontre_levels=rencontre_levels,
-        location_chain=location_chain,
-        location_defaults=location_defaults,
-        faction_ids=faction_ids,
-        faction_defaults=faction_defaults,
-        world_default=world_default,
-        fallback_level=fallback_level,
-    )
 
+def resolve_knowledge_level(db: Session, entity_id: str, fact_id: str) -> str:
+    """The level of `resolve_knowledge`."""
+    return resolve_knowledge(db, entity_id, fact_id).level
 
-def resolve_levels_for_entity(db: Session, entity_id: str) -> dict[str, str]:
-    """`fact_id -> level` for every fact in the entity's world resolving
-    above `'unaware'`. One pass: stored rows, participant fact ids,
-    acquaintances, location chain, faction memberships and every
-    `fact_default` for the world are each fetched once, then every fact is
-    resolved against that shared context — never one query per fact."""
+
+def resolve_known_for_entity(db: Session, entity_id: str) -> dict[str, Known]:
+    """`fact_id -> Known` for every fact in the entity's world resolving
+    above `'unaware'`. One pass: stored rows, participants, defaults and the
+    entity's contacts are each fetched once."""
     entity = db.get(Entity, entity_id)
     if entity is None:
         return {}
-
     facts = db.exec(select(Fact).where(Fact.world_id == entity.world_id)).all()
     if not facts:
         return {}
+    fact_ids = [fact.id for fact in facts]
+    stored = {row.fact_id: row for row in db.exec(
+        select(Knowledge).where(Knowledge.entity_id == entity_id)).all()}
+    defaults: dict[str, list[FactDefault]] = {}
+    for row in db.exec(select(FactDefault).where(FactDefault.fact_id.in_(fact_ids))).all():
+        defaults.setdefault(row.fact_id, []).append(row)
+    participants: dict[str, set[str]] = {}
+    for fact_id, member in db.exec(select(FactParticipant.fact_id, FactParticipant.entity_id).where(
+            FactParticipant.fact_id.in_(fact_ids))).all():
+        participants.setdefault(fact_id, set()).add(member)
+    ctx = _contacts(db, entity_id)
+    resolved: dict[str, Known] = {}
+    for fact in facts:
+        known = _resolve_fact(ctx, entity_id, fact, defaults.get(fact.id, []),
+                              participants.get(fact.id, set()), stored.get(fact.id))
+        if known.level != "unaware":
+            resolved[fact.id] = known
+    return resolved
 
-    stored_rows = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id)).all()
-    stored_by_fact = {row.fact_id: row.level for row in stored_rows}
 
-    participant_fact_ids = set(
-        db.exec(
-            select(FactParticipant.fact_id).where(FactParticipant.entity_id == entity_id)
-        ).all()
-    )
-    known_ids = acquaintances(db, entity_id)
-    location_chain = _location_ancestor_chain(db, entity_id)
-    faction_ids = _active_faction_ids(db, entity_id)
+def resolve_levels_for_entity(db: Session, entity_id: str) -> dict[str, str]:
+    """`fact_id -> level` of `resolve_known_for_entity`."""
+    return {fact_id: known.level for fact_id, known in resolve_known_for_entity(db, entity_id).items()}
 
-    fact_ids = [fact.id for fact in facts]
-    defaults = db.exec(select(FactDefault).where(FactDefault.fact_id.in_(fact_ids))).all()
 
-    rencontre_levels_by_fact: dict[str, list[str]] = {}
-    location_defaults_by_fact: dict[str, dict[str, str]] = {}
-    faction_defaults_by_fact: dict[str, dict[str, str]] = {}
-    world_default_by_fact: dict[str, str] = {}
-    for row in defaults:
-        if row.scope_type == "rencontre":
-            if row.scope_id in known_ids:
-                rencontre_levels_by_fact.setdefault(row.fact_id, []).append(row.level)
-        elif row.scope_type == "location":
-            location_defaults_by_fact.setdefault(row.fact_id, {})[row.scope_id] = row.level
-        elif row.scope_type == "faction":
-            faction_defaults_by_fact.setdefault(row.fact_id, {})[row.scope_id] = row.level
-        elif row.scope_type == "world":
-            world_default_by_fact[row.fact_id] = row.level
-
-    resolved: dict[str, str] = {}
-    for fact in facts:
-        is_self = fact.id in participant_fact_ids and fact.facet in DESCRIPTIVE_FACETS
-        level = _resolve_tiers(
-            stored_level=stored_by_fact.get(fact.id),
-            self_level="knows" if is_self else None,
-            rencontre_levels=rencontre_levels_by_fact.get(fact.id, []),
-            location_chain=location_chain,
-            location_defaults=location_defaults_by_fact.get(fact.id, {}),
-            faction_ids=faction_ids,
-            faction_defaults=faction_defaults_by_fact.get(fact.id, {}),
-            world_default=world_default_by_fact.get(fact.id),
-            fallback_level=fact.default_level,
-        )
-        if level != "unaware":
-            resolved[fact.id] = level
-    return resolved
+def _public_tier(world_default: Optional[str], fallback_level: str) -> str:
+    """Tiers 6-7 alone: the public floor has no entity, so no stored row,
+    no self, no contact."""
+    return world_default if world_default is not None else fallback_level
 
 
 def resolve_public_level(db: Session, fact_id: str) -> str:
@@ -294,12 +306,7 @@ def resolve_public_level(db: Session, fact_id: str) -> str:
     world_default = world_row.level if world_row is not None else None
     fact = db.get(Fact, fact_id)
     fallback_level = fact.default_level if fact is not None else "unaware"
-    return _resolve_tiers(
-        stored_level=None, self_level=None, rencontre_levels=[],
-        location_chain=[], location_defaults={},
-        faction_ids=[], faction_defaults={},
-        world_default=world_default, fallback_level=fallback_level,
-    )
+    return _public_tier(world_default, fallback_level)
 
 
 def resolve_public_levels(db: Session, world_id: str) -> dict[str, str]:
@@ -320,13 +327,7 @@ def resolve_public_levels(db: Session, world_id: str) -> dict[str, str]:
     ).all()
     world_default_by_fact = {row.fact_id: row.level for row in world_rows}
     return {
-        fact.id: _resolve_tiers(
-            stored_level=None, self_level=None, rencontre_levels=[],
-            location_chain=[], location_defaults={},
-            faction_ids=[], faction_defaults={},
-            world_default=world_default_by_fact.get(fact.id),
-            fallback_level=fact.default_level,
-        )
+        fact.id: _public_tier(world_default_by_fact.get(fact.id), fact.default_level)
         for fact in facts
     }
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 946a2e5..467f68e 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17790,6 +17790,34 @@ follows the zones (`connects_to` <-> `borde`) and a name bound to its entity
 are corrections. Until BRIEF-0105-F, the fiche and the Lore panel pass
 `correction`, which is today's behaviour.
 
+
+## A DEFAULT IS LEARNED BY A CONTACT AFTER IT, AND KEPT (TICKET-0105) -- RESOLUTION DATED BY CONTACT (BRIEF-0105-d, no schema change)
+
+**B5.** `knowledge_resolve.resolve_knowledge` returns `Known(level, as_of)`.
+A `rencontre`, `location` or `faction` default is known through a contact
+at or after its `created_at`: an encounter with its entity
+(`rencontre.last_at`), a passage in its place or in a place inside it
+(`passage.last_at`), a membership open now or closed after it (J2). A
+contact right now needs no date: the current place and its ancestors, the
+places one's schedule names, an entity at the same exact current place (O1)
+or in the same schedule slot (L1), an active membership. Reading the last
+contact means a fact once learned stays learned.
+
+**C1.** Among several applicable `location` defaults the highest level
+wins, like `faction` and `rencontre`; the nearest-ancestor rule is gone.
+
+**N1.** `as_of` is the last contact with any anchor of the fact -- its
+participants and the entities its non-world defaults name -- or a stored
+row's `updated_at` if later. A fact with a `world` default, one's own facts
+and the tiers without a scope are always current (`as_of = None`).
+`resolve_knowledge_level` and `resolve_levels_for_entity` keep their
+signatures and return the level alone.
+
+**Rejected.** C2, the current place first and the past ones after: it ranks
+contacts the model of a collection does not rank. N2, only the anchor of
+the tier that gave the level: meeting the wearer would not refresh an
+outfit known through a place.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
index 0ebced5..00f6631 100644
--- a/tooling/verify/checks/fact_learning.py
+++ b/tooling/verify/checks/fact_learning.py
@@ -59,6 +59,25 @@ C3 -- the version known (`fact_versions.version_text`, pure). History:
    as of t2.5 and t3.5 -> "v2b"; as of t4.5 and t6 -> "v3"; as of None ->
    "v3".
 
+D1 -- resolution dated by contact (BRIEF-0105-D, fixture, times t0 < t1 <
+   t2 < t3 before now), each row on `resolve_knowledge` AND
+   `resolve_known_for_entity` (absent from the batch = `unaware`):
+   a. a place passed at t1, its default written at t2 -> unaware;
+   b. a place passed at t1, its default written at t0 -> its level, kept
+      after leaving;
+   c. a zone's default at t0, a place inside it passed at t1 -> known;
+   d. two passed places, `rumor` and `knows` -> `knows` (C1);
+   e. an entity met at t1, its rencontre default at t2 -> unaware; at t0 ->
+      known;
+   f. a faction left at t1: its default at t0 -> known (J2), at t2 ->
+      unaware; an active membership -> known whatever the date;
+   g. an entity never met but at the same current place (O1), or sharing a
+      schedule slot (L1), its rencontre default at t3 -> known.
+D2 -- `as_of` (N1). A `tenue` of A with a rencontre default on A at t0, A
+   met at t1, then rewritten as a `changement`: `as_of == t1` and the
+   version known is the old text; after a new encounter, the current one.
+   A fact with a `world` default and one's own description -> `as_of` None.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -489,6 +508,151 @@ def check_c3() -> None:
             fail(f"C3: as of {as_of} -> {got!r}, expected {want!r}")
 
 
+# --- D1-D2 ---------------------------------------------------------------------
+
+def _d_world(session):
+    from datetime import UTC, datetime, timedelta
+
+    from world_engine.models import Character, Entity, Faction, Location, World
+
+    world = World(name="D1", is_active=False)
+    session.add(world)
+    session.flush()
+    ids: dict = {"world": world.id}
+    now = datetime.now(UTC)
+    ids.update({f"t{i}": now - timedelta(days=4 - i) for i in range(4)})
+
+    def entity(etype: str, name: str) -> str:
+        row = Entity(world_id=world.id, type=etype, name=f"D1 {name}")
+        session.add(row)
+        session.flush()
+        return row.id
+
+    for key, parent in (("Z", None), ("C", "Z"), ("L", None), ("M", None), ("Q", None)):
+        ids[key] = entity("location", key)
+        session.add(Location(id=ids[key], parent_location_id=ids[parent] if parent else None))
+    for key in ("F1", "F2", "F3"):
+        ids[key] = entity("faction", key)
+        session.add(Faction(id=ids[key]))
+    for key in ("P", "A", "B", "S"):
+        ids[key] = entity("character", key)
+        session.add(Character(id=ids[key], world_id=world.id, character_type="npc"))
+    session.commit()
+    return ids
+
+
+def _d_fact(session, ids, label, facet="information", about=None, scopes=()):
+    from world_engine.writes import attach_participants, create_fact, create_fact_default
+
+    fact = create_fact(session, world_id=ids["world"], content=f"D1 {label}", created_by="check",
+                       facet=facet)
+    session.flush()
+    if about:
+        attach_participants(session, fact=fact, entity_ids=[ids[about]])
+    for scope_type, key, level, at in scopes:
+        row = create_fact_default(session, world_id=ids["world"], fact_id=fact.id,
+                                  scope_type=scope_type, scope_id=ids[key] if key else None,
+                                  level=level, created_by="check")
+        session.flush()
+        row.created_at = ids[at] if at else row.created_at
+        session.add(row)
+    session.commit()
+    return fact.id
+
+
+def _d_cases(session, ids) -> dict:
+    from world_engine.encounters import record_encounter
+    from world_engine.models import Character, FactionMembership
+    from world_engine.passages import record_passage
+    from world_engine.writes import write_npc_schedule
+
+    w = ids["world"]
+    for key, at in (("L", "t1"), ("M", "t1"), ("C", "t1")):
+        record_passage(session, world_id=w, entity_id=ids["P"], location_id=ids[key], at=ids[at])
+    record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="visit", at=ids["t1"])
+    session.add(FactionMembership(world_id=w, entity_id=ids["P"], faction_id=ids["F1"], left_at=ids["t1"]))
+    session.add(FactionMembership(world_id=w, entity_id=ids["P"], faction_id=ids["F2"], left_at=ids["t1"]))
+    session.add(FactionMembership(world_id=w, entity_id=ids["P"], faction_id=ids["F3"]))
+    session.commit()
+    cases = {
+        "a": (_d_fact(session, ids, "a", scopes=[("location", "L", "knows", "t2")]), "unaware"),
+        "b": (_d_fact(session, ids, "b", scopes=[("location", "M", "partial", "t0")]), "partial"),
+        "c": (_d_fact(session, ids, "c", scopes=[("location", "Z", "knows", "t0")]), "knows"),
+        "d": (_d_fact(session, ids, "d", scopes=[("location", "L", "rumor", "t0"),
+                                                 ("location", "M", "knows", "t0")]), "knows"),
+        "e-late": (_d_fact(session, ids, "e1", scopes=[("rencontre", "A", "knows", "t2")]), "unaware"),
+        "e-early": (_d_fact(session, ids, "e2", scopes=[("rencontre", "A", "rumor", "t0")]), "rumor"),
+        "f-early": (_d_fact(session, ids, "f1", scopes=[("faction", "F1", "knows", "t0")]), "knows"),
+        "f-late": (_d_fact(session, ids, "f2", scopes=[("faction", "F2", "knows", "t2")]), "unaware"),
+        "f-active": (_d_fact(session, ids, "f3", scopes=[("faction", "F3", "rumor", "t3")]), "rumor"),
+        "g-place": (_d_fact(session, ids, "g1", scopes=[("rencontre", "B", "knows", "t3")]), "knows"),
+        "g-slot": (_d_fact(session, ids, "g2", scopes=[("rencontre", "S", "partial", "t3")]), "partial"),
+    }
+    for key in ("P", "B"):
+        char = session.get(Character, ids[key])
+        char.current_location_id = ids["Q"]
+        session.add(char)
+    for key in ("P", "S"):
+        session.add_all(write_npc_schedule(session, world_id=w, npc_id=ids[key],
+                                           rows=[{"phase": "soir", "location_id": ids["M"]}],
+                                           changed_by="check"))
+    session.commit()
+    return cases
+
+
+def check_d1(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.knowledge_resolve import resolve_known_for_entity, resolve_knowledge
+
+    with Session(engine) as session:
+        ids = _d_world(session)
+        cases = _d_cases(session, ids)
+        batch = resolve_known_for_entity(session, ids["P"])
+        for case, (fact_id, want) in sorted(cases.items()):
+            single = resolve_knowledge(session, ids["P"], fact_id).level
+            batched = batch[fact_id].level if fact_id in batch else "unaware"
+            if single != want or batched != want:
+                fail(f"D1 {case}: expected {want!r}, got {single!r} / {batched!r}")
+
+
+def check_d2(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.encounters import record_encounter
+    from world_engine.fact_versions import version_text
+    from world_engine.knowledge_resolve import resolve_known_for_entity, resolve_knowledge
+    from world_engine.models import Fact
+    from world_engine.writes.facts import update_fact_content
+
+    with Session(engine) as session:
+        ids = _d_world(session)
+        w = ids["world"]
+        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="visit", at=ids["t1"])
+        session.commit()
+        tenue = _d_fact(session, ids, "noir", facet="tenue", about="A",
+                        scopes=[("rencontre", "A", "knows", "t0")])
+        fact = session.get(Fact, tenue)
+        update_fact_content(session, fact=fact, content="D1 rouge", changed_by="check", kind="changement")
+        session.commit()
+        known = resolve_knowledge(session, ids["P"], tenue)
+        batched = resolve_known_for_entity(session, ids["P"]).get(tenue)
+        if known.as_of != ids["t1"] or batched is None or batched.as_of != ids["t1"]:
+            fail(f"D2: as_of is {known.as_of} / {batched}, expected {ids['t1']}")
+        elif version_text(fact.change_history, fact.content_raw, known.as_of) != "D1 noir":
+            fail("D2: the version known before the new encounter is not the old text")
+        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="gathering")
+        session.commit()
+        again = resolve_knowledge(session, ids["P"], tenue)
+        if version_text(fact.change_history, fact.content_raw, again.as_of) != "D1 rouge":
+            fail("D2: a new encounter did not bring the current text")
+        public = _d_fact(session, ids, "public", scopes=[("world", None, "rumor", None)])
+        own = _d_fact(session, ids, "own", facet="physique", about="P")
+        for label, fact_id in (("world", public), ("own", own)):
+            if resolve_knowledge(session, ids["P"], fact_id).as_of is not None:
+                fail(f"D2: a {label} fact is not always current")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -502,6 +666,8 @@ def main() -> int:
     check_c1(engine)
     check_c2()
     check_c3()
+    check_d1(engine)
+    check_d2(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -510,7 +676,8 @@ def main() -> int:
           "contact, presets tenue to rencontre, and migrates from v2.13 only; every "
           "placement and every encounter moves its last contact, through one writer each; "
           "every rewrite says whether it corrects or changes the world, and the version "
-          "known follows the changes alone")
+          "known follows the changes alone; a default is learned by a contact after it, kept "
+          "after leaving, and dated by the last contact with its anchors")
     return 0
 
 
diff --git a/tooling/verify/checks/knowledge_resolution.py b/tooling/verify/checks/knowledge_resolution.py
index 968e662..9422c26 100644
--- a/tooling/verify/checks/knowledge_resolution.py
+++ b/tooling/verify/checks/knowledge_resolution.py
@@ -29,6 +29,8 @@ Four assertions:
        - **first-membership-wins**: the level of whichever faction was
          joined first, ignoring the others — also `'rumor'` here (Faction A
          joined first).
+  Tier 2b follows C1 (TICKET-0105): the highest location default among the
+  places one is in wins, no longer the nearest ancestor's.
   5. C-09 case table (TICKET-0091, BRIEF-0091-D): the seven-tier order
      (stored > self > rencontre > location > faction > world >
      fact.default_level), rows 1-9 of the lot's table, each built through
@@ -136,9 +138,10 @@ def _build_fixture(session):
     create_fact_default(session, world_id=world_id, fact_id=fact_loc_vs_world, scope_type="location", scope_id=child_id, level="knows", created_by="check")
     session.commit()
 
-    # Tier 2b — nearest ancestor beats a farther one.
-    fact_loc_nearest = _fact("tier2b: nearest location ancestor wins")
-    create_fact_default(session, world_id=world_id, fact_id=fact_loc_nearest, scope_type="location", scope_id=root_id, level="suspicious", created_by="check")
+    # Tier 2b — the HIGHEST level across the places one is in wins (C1,
+    # TICKET-0105): the farther ancestor's `knows` beats the nearer `partial`.
+    fact_loc_nearest = _fact("tier2b: highest location default wins")
+    create_fact_default(session, world_id=world_id, fact_id=fact_loc_nearest, scope_type="location", scope_id=root_id, level="knows", created_by="check")
     create_fact_default(session, world_id=world_id, fact_id=fact_loc_nearest, scope_type="location", scope_id=child_id, level="partial", created_by="check")
     session.commit()
 
@@ -171,7 +174,7 @@ def check_precedence_and_vacuous_proof(session, alice_id, facts) -> None:
     expected = {
         "stored": "partial",
         "loc_vs_world": "knows",
-        "loc_nearest": "partial",
+        "loc_nearest": "knows",
         "faction_highest": "knows",
         "no_default": "suspicious",
     }
@@ -349,6 +352,11 @@ def _build_c09_fixture(session):
     _default(f9, "rencontre", stranger_id, "knows")
     cases[9] = (f9, C09_FALLBACK)
 
+    # A contact with the friend AFTER every default was written (TICKET-0105,
+    # B5): a rencontre default is known only by a contact at or after it.
+    record_encounter(session, world_id=wid, a_id=perceiver_id, b_id=friend_id, source="visit")
+    session.commit()
+
     return perceiver_id, cases
 
 
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 6a4a94a..db203f2 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -678,7 +678,13 @@ no second column and no polymorphic type tag. Ships empty; the creator
 surface (`cockpit/crud/knowledge.py`) is its first writer. Scope
 `rencontre` (schema v2.05, TICKET-0091, BRIEF-0091-A): `scope_id` is an
 entity; the fact is known to that entity's acquaintances (the `rencontre`
-registry) at `level`.
+registry) at `level`. Since TICKET-0105 (BRIEF-0105-D) a `rencontre`,
+`location` or `faction` default is known only through a contact AT OR AFTER
+the row's `created_at` -- an encounter (`rencontre.last_at`), a passage in
+the place or a place inside it (`passage.last_at`), a membership open or
+closed after it -- or a contact right now; what is learned stays learned,
+and among several such defaults the HIGHEST level wins
+(`knowledge_resolve.py` docstring).
 
 ```sql
 CREATE TABLE fact_default (
````

## Scope OUT

- Rendering versions in any reader (E): `resolve_default_rows` still builds rows from the current text.
- The public floor (`resolve_public_level(s)`): no entity, no contact.
- Caching contacts across calls.
- Writing anything: resolution stays a read.
- Every later brief of this lot.

## Invariants to defend

**Secrets are structurally excluded:** a resolved default still never carries `is_secret`. **Resolution is a read:** no `db.add` in the module. **The MJ context is scoped to the player's perception:** the player's contacts decide what the player knows; nothing here widens what a context assembles. **Knowledge levels never decrease through the mutation pipeline:** untouched — no stored row changes.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `known_reachability.py`, `day_concordance*.py`, `tick*` or `context*` checks fail on a level the old rules gave (a reader that relied on presence-only semantics).
- `function_length.py` or `module_budget.py` fails on `knowledge_resolve.py`.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- The corpus run time against `main`'s (resolution now reads three more registries).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- … a default is learned by a contact after it, kept after leaving, and dated by the last contact with its anchors`.
- `knowledge_resolution.py`, `known_reachability.py`, `fact_facets.py`, `identity_tokens.py`, `function_length.py`, `module_budget.py` → `PASS`.
- Mutation tests, each red then reverted: in `_tier_level`, `if seen is not None and seen >= utc(row.created_at):` → `if seen is not None:` → `D1 a`, `D1 e-late`, `D1 f-late`; in `_as_of`, the `anchors = …` line → `anchors = set()` → `D2`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

`world-engine-schema.md`, `fact_default` paragraph — in the diff (no version change). Decision entry `A DEFAULT IS LEARNED BY A CONTACT AFTER IT, AND KEPT (TICKET-0105) -- RESOLUTION DATED BY CONTACT (BRIEF-0105-d, no schema change)` — in the diff.
