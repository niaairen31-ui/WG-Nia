# BRIEF — Step "Scoped knowledge defaults and level resolution"

## Mini-RECON (measured on tarball of `main`, schema v1.97)

- `writes/knowledge.py:34` — `KNOWLEDGE_LEVELS` frozenset; line 42 — the same
  six values as an **ordered tuple** [M]. G2a's "highest wins" is computable
  from that tuple; nothing new is needed to order the scale.
- `faction.magic_knowledge_level` (`models/canon_faction.py:31`), default
  `'unaware'`, on exactly this six-value scale, rendered into the NPC
  briefing at `tick_context.py:543` as `("Connaissance de la magie : ", ...)` [M].
  This is a hardcoded, faction-scoped default knowledge level on a single
  subject — the ancestor of `fact_default`. It is **not** touched here; its
  subsumption is a named deferral.
- `FactionMembership` (`models/canon_faction.py:98+`): a membership is ACTIVE
  iff `left_at IS NULL`; `idx_membership_unique_active` forbids duplicate
  active membership of the same member in the same faction, but
  `idx_membership_one_primary` shows a member may hold **several** active
  memberships, only one of them primary [M]. Multi-faction resolution is
  therefore a real case, not a hypothetical.
- `faction_membership.is_secret` is DORMANT and its exclusion "is NOT
  enforced this step" per the model comment; `read_public_memberships` is the
  named routing chokepoint (`models/canon_faction.py` comment, and
  ARCHITECTURE_DECISIONS) [M].
- Knowledge is listed into prompts at three sites [M]:
  `context.py:376-378` (NPC), `context.py:720-722` (player character),
  `tick_context.py:240` (tick briefing). Rendering goes through
  `_knowledge_line` (`context.py:120`, `tick_context.py:116`).
- `location.parent_location_id` exists (containment tree, `models/canon.py:216+`)
  and `tooling/verify/checks/location_tree.py` exists [M] — hierarchical
  location scope has a traversal precedent.

## Context

BRIEF-0082-b gave every fact a single `default_level` valid for the whole
world. Nia's target case is a secret known by an entire faction, and by new
members as they join, without one stored row per member. This step adds the
scope and the resolution rule (G2a), and makes the three prompt-assembly
readers consume it.

## Scope IN

1. **Table `fact_default`** in `models/canon_knowledge.py`:
   `id`, `world_id` (FK `world.id`, NOT NULL),
   `fact_id` (FK `fact.id`, NOT NULL),
   `scope_type` (str, NOT NULL),
   `scope_id` (FK `entity.id`, nullable — NULL only when
   `scope_type = 'world'`),
   `level` (str, NOT NULL),
   `created_at`, `created_by`.
   Constraints, with these exact names:
   - `ck_fact_default_scope_type`: `scope_type IN ('world','faction','location')`
   - `ck_fact_default_scope_shape`:
     `(scope_type = 'world' AND scope_id IS NULL) OR (scope_type <> 'world' AND scope_id IS NOT NULL)`
   - `ck_fact_default_level`: the same six-value list as `ck_fact_default_level`
     on `fact`
   Unique index `idx_fact_default_unique` on `(fact_id, scope_type, scope_id)`.
   Index `idx_fact_default_fact` on `fact_id`.
   A faction scope uses the faction's `entity.id` — `Faction.id` is already a
   FK to `entity.id`, so no second column and no polymorphic type tag.
2. **Resolution function** `resolve_knowledge_level(db, entity_id, fact_id) -> str`
   in a new `src/world_engine/knowledge_resolve.py`. Precedence, most
   specific first — the function returns at the **first** tier that produces
   a value:
   1. a stored `knowledge` row for `(entity_id, fact_id)` — its `level` wins
      outright, including when it is `'unaware'`;
   2. `fact_default` where `scope_type = 'location'` and `scope_id` is the
      entity's current location, or any ancestor of it via
      `location.parent_location_id` — nearest ancestor wins;
   3. `fact_default` where `scope_type = 'faction'` and `scope_id` is any
      faction in which the entity holds an ACTIVE membership
      (`left_at IS NULL`). **Across several such memberships the HIGHEST
      level on the ordered tuple wins** (G2a);
   4. `fact_default` where `scope_type = 'world'`;
   5. `fact.default_level`.
   The function is **total**: it always returns one of the six values, never
   `None`, because tier 5 is NOT NULL. Import the ordered tuple from
   `writes/knowledge.py` — never re-type the six values in this module.
3. **Batch companion** `resolve_levels_for_entity(db, entity_id) -> dict[str, str]`
   returning `fact_id -> level` for every fact the entity resolves above
   `'unaware'`. The three readers in item 4 call this once per assembly, not
   once per fact.
4. **Readers.** At `context.py:376-378`, `context.py:720-722` and
   `tick_context.py:240`, the knowledge listing becomes the union of stored
   rows and resolved defaults. A resolved default renders through the same
   `_knowledge_line` shape, using the fact's `content` as the subject text
   and the resolved level.
5. **Secrecy.** A fact reached by a resolved default renders with
   `is_secret = False` and the default `share_threshold` of 50. Rationale,
   to be written verbatim into the module docstring of
   `knowledge_resolve.py`:
   ```
   # A resolved default never carries is_secret. Secrecy is a property of a
   # stored knowledge row, structurally excluded at query level by the
   # existing readers. A default that could mint secret knowledge would put
   # a second, weaker authority behind that exclusion.
   ```
6. **Creator surface.** In `cockpit/crud/knowledge.py`, endpoints to list,
   add and remove `fact_default` rows on a fact, with the scope picker
   restricted to the three scope types and, for faction and location, to
   entities of the matching kind. Adding a duplicate `(fact_id, scope_type,
   scope_id)` returns 409, not a silent upsert.
7. **Verify check** `tooling/verify/checks/knowledge_resolution.py`, house
   idiom, vacuous-proof:
   - for every `(entity, fact)` pair sampled from the live database,
     `resolve_knowledge_level` returns a value in the six-value vocabulary —
     never `None`, never an unknown string (zero pairs collected = FAIL);
   - no `fact_default` row violates its shape constraint;
   - the six-value vocabulary in this module and in `knowledge_resolve.py`
     is imported from `writes/knowledge.py`, asserted by AST scan — no
     re-typed literal list anywhere in the resolution path;
   - **mutation-sensitivity**: golden cases are *failing* inputs. Build a
     fixture where a member of two factions has levels `rumor` and `knows`;
     assert exact equality with `knows`. Then assert that flipping the
     resolution to lowest-wins, and separately to first-membership-wins,
     each make the check FAIL. Name both mutations in the check docstring.

## Scope OUT

- **Do not touch `faction.magic_knowledge_level`** and do not remove its
  render at `tick_context.py:543`. Subsuming it is a named deferral with a
  stated condition; doing it here would make this brief two chantiers.
- **Do not touch `faction_membership.is_secret`** or route anything new
  through `read_public_memberships`. A secret membership resolving a
  faction-scoped default is a real question and it is **REPORT ONLY** here.
- **Do not add `scope_type = 'entity_type'`, `'role'`, `'region'` or any
  fourth scope.** Three scopes, matching the locked G2 decision.
- Do not convert any `Knowledge.subject` reader. Still the successor ticket.
- Do not add knowledge-filtered reachability — BRIEF-0082-d.
- Do not write a migration that seeds any `fact_default` row. The table
  ships empty; the creator surface in item 6 is its first writer.
- Do not let a resolved default create a stored `knowledge` row as a side
  effect. Resolution is a read. If a caller wants to persist, that is an
  explicit creator or mutation action, not a cache warmed on read.
- Do not add caching or memoisation across requests.

## Invariants to defend

- **Model proposes, code judges.** Resolution is pure code over stored rows.
  No model call anywhere in `knowledge_resolve.py`.
- **Exclusion of secrets is structural.** Item 5 is the defence: defaults
  cannot mint secrets, so the existing query-level exclusions remain the
  only authority.
- **No structure without a reader.** `fact_default` ships with three
  readers named in item 4. `scope_type = 'location'` in particular must be
  demonstrated live, or it is dormant structure and must be cut from this
  brief rather than shipped.
- **Fail-closed and vacuous-proof.** Item 7, including the two named
  mutations.
- **Single canon-write authority.** `fact_default` is canon; register it in
  `[CANON_TABLES]` and route its writes through `writes/facts.py`.
- **Module budget.** `context.py` and `tick_context.py` are both large.
  Check both against the cap before editing; if either would cross,
  **STOP** and report rather than inlining the union logic there — the
  batch helper in item 3 exists so the readers stay thin.

## Done means

- [ ] Table `fact_default` exists and appears in `static_table_names()`.
- [ ] `python -m world_engine.schema_reconcile` reports no orphan.
- [ ] A unit-level demonstration of each of the five precedence tiers, run
      and pasted: a stored `unaware` row beating a faction `knows` default;
      a location default beating a world default; a nearest-ancestor
      location default beating a farther one; two active memberships at
      `rumor` and `knows` resolving to `knows`; a fact with no default at
      all resolving to its `fact.default_level`.
- [ ] `resolve_knowledge_level` returns a six-value string for every sampled
      pair, and returns `fact.default_level` when the entity has no
      membership, no location and no stored row.
- [ ] `knowledge_resolution.py` PASS on the dev database, and FAIL on each
      of the two named mutations (lowest-wins, first-membership-wins). Paste
      all three verdicts.
- [ ] Emptying `fact_default` and `fact` makes the check FAIL, not PASS
      (demonstrated on a scratch copy).
- [ ] `module_budget.py`, `function_length.py`, `single_canon_write.py`,
      `import_cycle.py`, `undefined_names.py` PASS.
- [ ] Corpus gate green. `/review-step` and `/close-step` run.
- [ ] Live, and this is the acceptance that matters: author one free-standing
      fact with `default_level = 'unaware'`, add one `fact_default` at
      faction scope with level `knows`, and confirm it appears in the tick
      briefing of **every** active member of that faction with **zero**
      stored `knowledge` rows. Then close one member's membership
      (`left_at`) and confirm it stops appearing for that member and still
      appears for the others. Transcript of both states.
- [ ] Live: a location-scoped default on a parent location resolves for an
      NPC standing in a child location.

## Docs to update

- `world-engine-schema.md` (new table, `Current schema version:` line) and
  `world-engine-schema-changelog.md` — **Claude Code assigns the version**.
- `src/world_engine/schema_version.py` constant, kept equal by
  `schema_version_agreement.py`.
- `tooling/verify/canon_write_policy.txt`: `fact_default` into `[CANON_TABLES]`.
- `ARCHITECTURE_DECISIONS.md`: the G2a precedence ladder written out as the
  single authority on level resolution, plus the deferral entry for
  `faction.magic_knowledge_level` with its reactivation condition — which
  this step makes satisfiable, so it must be logged here even though it is
  not acted on.

## STOP conditions

- If a location-scoped default cannot be demonstrated live against a real
  world, cut `scope_type = 'location'` from this brief and report. Shipping
  it unread is dormant structure.
- If either `context.py` or `tick_context.py` would cross the module budget
  cap, stop and report; do not exempt, do not inline.
- If any entity in the dev database holds an active membership in a faction
  whose row is missing from `entity`, stop and report — the faction-as-entity
  assumption this brief rests on would be broken.
- If a secret membership (`faction_membership.is_secret = TRUE`) exists in
  the dev database, stop before the live gate and report it: whether such a
  member resolves the faction's defaults is an unsettled design question and
  must not be decided by whichever code path happens to run first.
