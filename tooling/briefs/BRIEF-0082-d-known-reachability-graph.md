# BRIEF — Step "Known-reachability graph for deliberation"

## Mini-RECON (measured on tarball of `main`, schema v1.97)

- `tick_context._reachable_locations` (`tick_context.py:405-448`): BFS over
  `connects_to` among ACTIVE locations from an origin, bounded by
  `INTERVAL_HOP_RADIUS[interval_label]`, origin excluded, returns
  `(entity_id, name)` pairs [M]. It is **knowledge-blind** — the god's-eye
  graph. Called at `tick_context.py:489`; the result reaches the NPC through
  `assemble_tick_context` (`tick.py:220`, `destinations=setup["reachable"]`,
  `tick.py:69-74`) [M].
- `day_plan.py:218-236`: a **second, separate** BFS over `connects_to` —
  whole connected component, origin INCLUDED, bare ids, feeding
  `evaluate_requirements` [M]. Its docstring says membership only is needed.
- The `_reachable_locations` docstring claims it is "the third reader" of
  `connects_to` as of RECON-0015 [M]. **That is stale.** The measured
  enumeration is **twelve modules**: `room_batch_author.py:141`,
  `day_concordance.py:239` and `:343`, `tick_context.py:433`,
  `writes/config.py:280` and `:287`, `cockpit/spatial_doors.py:66` and `:73`,
  `cockpit/crud/entities.py:323` and `:330`, `cockpit/crud/relations.py:123`,
  `cockpit/crud/locations.py:250`, `cockpit/play.py:861` and `:867`,
  `cockpit/routes/regions.py:285/288/313/353/356`, `day_plan.py:228`,
  `spatial_author.py:35/41/127`. Plus two vocabulary sites that are not
  traversals: `cockpit/crud/_shared.py:137` (the datalist) and
  `context.py:109` (`RELATION_GRAPH_EXCLUDED_TYPES`), and one assertion,
  `link_author.py:68` [M].
- `day_resolve.py:260-261`: `_BLOCKED_DETAIL_FR` maps `relation_gte` and
  `location_reachable` to player-facing French, and is "the ONLY source of a
  blocked step's rendered reason" [M].
- `writes/goals_agendas.py:598`: `entity_gated = req.type in ("relation_gte",
  "location_reachable")` [M].
- `tooling/verify/checks/relation_graph.py` and `graph_primitive.py` already
  exist [M] — check whether either already constrains `connects_to` readers
  before adding a new one.

## Context

This is the reader Nia named: deciding whether a character has the knowledge
to reach a place. Today both BFS implementations traverse the full graph, so
an NPC can plan a route through a passage it has never heard of. B2 fixes
that by adding a knowledge-filtered traversal for **deliberation only**,
leaving every truth reader untouched.

The safety property that makes this step tractable: the migration in item 2
gives every existing `connects_to` fact `default_level = 'knows'`, so on
arrival the known graph is **identical** to the truth graph for every entity.
Behaviour is preserved by construction. Secret passages become expressible
afterwards, by lowering one default — not by this step changing what anyone
currently knows.

## Scope IN

1. **Classification table.** Before any code: produce
   `tooling/tickets/TICKET-0082-connects-to-readers.md` listing every
   `connects_to` read site from the mini-RECON above, each classified as
   exactly one of `resolution`, `deliberation`, `authoring`, `vocabulary`.
   Definitions, verbatim:
   ```
   resolution     — decides whether something that has been proposed is
                    legal. Reads canon. Must NOT be knowledge-filtered.
   deliberation   — decides what a character considers, proposes or is
                    offered. Must be knowledge-filtered.
   authoring      — creator or generator building the graph itself. Reads
                    and writes canon. Not filtered.
   vocabulary     — a type literal or exclusion list, not a traversal.
   ```
   The table is the artifact the next brief and the check both read.
2. **Migration** `scripts/migrate_v1_NN_connects_to_facts.py` (Claude Code
   assigns NN), in one transaction: for every `relation` row with
   `type = 'connects_to'`, insert one `fact` with `relation_id` set,
   `content` = a generated French statement of the edge in the exact form
   `"{name_a} communique avec {name_b}."`, `default_level = 'knows'`,
   `created_by = 'migrate_v1_NN'`. Assert one fact per such relation, no
   more, no fewer; assert zero `fact_participant` rows created (these are
   typed facts, `ck_fact_spine_exclusive` forbids participants). Roll back
   on any assertion failure.
3. **`known_reachable_locations(db, entity_id, origin_location_id, interval_label)`**
   in `src/world_engine/knowledge_reach.py`. Same BFS shape and same
   `INTERVAL_HOP_RADIUS` bound as `_reachable_locations`, with one added
   predicate: an edge is traversable iff
   `resolve_knowledge_level(db, entity_id, fact_of_that_relation)` is at or
   above `'partial'` on the ordered tuple. **Fail-closed: a `connects_to`
   relation with no backing fact is NOT traversable**, and the function
   records it in a returned diagnostic list rather than silently skipping it.
   `'partial'` is the floor because that is the first level at which the
   character can be said to know where the way goes; write that sentence
   into the module docstring so the choice is anchored and reversible.
4. **Wire deliberation only.** Repoint exactly the sites the item-1 table
   classifies as `deliberation` — expected to be `tick_context.py:433`
   (inside `_reachable_locations`, via a knower-aware variant) and
   `day_plan.py:228`, but the table decides, not this brief. Every site
   classified `resolution`, `authoring` or `vocabulary` is left byte-identical.
5. **Diagnostic surface.** When deliberation drops an edge the truth graph
   contains, log one structured line naming entity, edge, resolved level.
   No player-facing text: `_BLOCKED_DETAIL_FR` is untouched, because a
   deliberation filter produces no blocked step — the character simply never
   proposes that route.
6. **Verify check** `tooling/verify/checks/known_reachability.py`, house
   idiom, vacuous-proof, with three assertions:
   - every `connects_to` relation has exactly one backing fact (zero
     relations collected = FAIL);
   - every `connects_to` read site in `src/` appears in the item-1
     classification table with one of the four labels — an **unclassified
     site is a FAIL**, so the check fails the moment a thirteenth reader
     appears;
   - **golden case, mutation-sensitive**: on a fixture world where no
     default has been lowered, `known_reachable_locations` returns a set
     **exactly equal** to `_reachable_locations` for the same origin and
     interval. Then assert the check FAILS under each of two named
     mutations: (a) the floor lowered to `'unaware'`, which would admit
     unknown edges; (b) the missing-fact case treated as traversable
     instead of fail-closed.

## Scope OUT

- **Do not change any `resolution` site.** `day_resolve.py`'s
  `location_reachable` keeps reading canon. The composition is the point:
  deliberation narrows, resolution verifies, and a route the character never
  proposes never reaches resolution.
- **Do not unify the two BFS implementations.** `_reachable_locations`
  (origin excluded, hop-bounded, returns names) and `day_plan.py:218`
  (origin included, unbounded, returns ids) differ deliberately. Merging
  them is an extraction ticket; doing it inside a semantics change would
  make a regression unattributable.
- **Do not lower any `default_level`** in the migration or in a seed. Every
  edge arrives at `'knows'`. Authoring a secret passage is a creator action
  after this ships.
- Do not touch `_BLOCKED_DETAIL_FR` (`day_resolve.py:257-262`) or add a
  fifth entry to it.
- Do not add a `location_known` requirement type to
  `NPC_GOAL_PREREQUISITE_TYPES` — that would be a mechanical effect on the
  perception layer, which is E2 and deferred.
- Do not extend the filter to `controls` or any other relation type. Only
  `connects_to`.
- Do not convert any `Knowledge.subject` reader. Still the successor ticket.
- Do not touch `context.py:109` `RELATION_GRAPH_EXCLUDED_TYPES` or
  `cockpit/crud/_shared.py:137` — vocabulary, not traversal.
- Do not implement the typed expectation ("a market probably has merchants").
  That is D1 and it is out of TICKET-0082 entirely.

## Invariants to defend

- **Fail-closed.** Item 3's missing-fact case and item 6's second named
  mutation. An edge whose knowability cannot be established is not
  traversable.
- **Structural over disciplinary.** The classification table is enforced by
  the check in item 6, not by a convention that future readers will remember
  to look it up.
- **Enumeration scope discipline.** Twelve modules were measured. The check
  makes the count self-maintaining; the brief must not claim coverage the
  check does not enforce.
- **Model proposes, code judges.** The filter is code over stored levels. No
  model call decides reachability.
- **History is sacred.** The migration inserts facts; it must not modify a
  single `relation` row. Assert a checksum over `relation` pre and post.
- **No structure without a reader.** The `fact` rows created in item 2 have
  their reader in item 3, in the same brief.

## Done means

- [ ] `tooling/tickets/TICKET-0082-connects-to-readers.md` exists and
      classifies every site from the mini-RECON, with no site unlabelled.
- [ ] Every `connects_to` relation has exactly one backing fact. Paste the
      relation count and the fact count; they are equal.
- [ ] Checksum over the `relation` table is identical pre and post migration.
- [ ] On the dev world with no default lowered,
      `known_reachable_locations(entity, origin, interval)` returns a set
      **exactly equal** to `_reachable_locations(origin, interval)` for at
      least five distinct (entity, origin) pairs. Paste the five comparisons.
- [ ] Deleting the fact behind one `connects_to` relation makes that edge
      untraversable in deliberation and records it in the diagnostic list —
      demonstrated on a scratch copy.
- [ ] `known_reachability.py` PASS on the dev database, and FAIL under both
      named mutations (floor lowered to `'unaware'`; missing fact treated as
      traversable). Paste all three verdicts.
- [ ] Adding a thirteenth `connects_to` read site to a scratch branch makes
      the check FAIL. Demonstrate.
- [ ] `module_budget.py`, `function_length.py`, `import_cycle.py`,
      `relation_graph.py`, `graph_primitive.py`, `world_tick.py`,
      `day_plan.py` checks all PASS.
- [ ] Corpus gate green. `/review-step` and `/close-step` run.
- [ ] Live, and this is the acceptance that matters: run a tick before this
      step and after it on the same world and confirm the destination list
      offered to an NPC is unchanged. Then lower one `connects_to` fact to
      `'unaware'` for one faction, and confirm that edge disappears from the
      deliberation of that faction's members and from no one else's, while
      the resolution path still treats a move along it as legal if it is
      somehow proposed. Transcript of all three states.

## Docs to update

- `world-engine-schema.md` and `world-engine-schema-changelog.md` if the
  migration counts as a version bump (it adds rows, not structure — **ask
  before assigning a version**; Claude Code owns the number).
- `ARCHITECTURE_DECISIONS.md`: B2 written out as the standing rule —
  "truth resolves, belief deliberates" — with the four classification labels
  verbatim, so the next reader of `connects_to` knows which side it is on
  before writing the query.
- The stale docstring at `tick_context.py:410-413` claiming three readers:
  correct it to point at the classification table rather than a count that
  will go stale again.

## STOP conditions

- If the classification of any site is genuinely ambiguous — a call site
  that both proposes and validates — **stop and escalate**. Do not pick.
  That ambiguity is a design question about where deliberation ends, and it
  belongs to Nia.
- If `known_reachable_locations` and `_reachable_locations` do not return
  identical sets on an unmodified world, stop: the migration or the floor is
  wrong, and no amount of live testing will make a silent divergence safe.
- If `relation_graph.py` or `graph_primitive.py` already constrains
  `connects_to` readers in a way that conflicts with the new check, stop and
  report both before writing a second authority over the same sites.
- If the `connects_to` reader count differs from the twelve modules measured
  here, stop before item 2 and report the delta.
