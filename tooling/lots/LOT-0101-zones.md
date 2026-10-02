# LOT — TICKET-0101 "Zones and visitable places — the `borde` relation, automatic promotion, three graph modes"

## Objective and cut

Nia builds Aestia with districts (the Secte du Phoenix and its workshops) and
will subdivide the Forêt verte. A location that holds other locations is a
**zone**: a piece of geography one never stands in. Only a location without
an active child is **visitable**; only `connects_to` is traversable and it
joins two visitable places; any link touching a zone is the new type
`borde`. When a visitable place gets its first child, what can only sit in a
visitable place moves to that child, after a dialog that lists it.

The lot writes the rule and the link type (A), refuses a zone at every
placement write (B), promotes a parent on its first child behind a
confirmation (C), migrates existing data to v2.12 (D), offers the parent's
neighbours when a child is created, in the fiche and in the room batch (E),
and gives the Lieux graph three modes (F).

It stops before any reader rolls a location up to its zones (« being in the
atelier is being in the quarter ») and before any notion of border: both are
carried forward in the ticket. It changes no traversal reader.

## Briefs in this lot

- **A — `borde` and the derived link type** (no schema change):
  `zone_rules.py` (C-01); `relation_orientation.py` gains `borde` in the
  structural tuple, `MAP_TOPOLOGY_TYPES`, `borde_fact_content` (C-03);
  `write_relation` judges L1/V1 (C-02); `spatial_author.link_locations`
  (C-04), used by the relation route, the room batch and (as
  `geographic_link_type`) the region commit; the two literal exclusions;
  CLAUDE.md; `zone_map_links.py`.
- **B — placement guards** (no schema change): `require_visitable` at the
  seven placement writes and in the NPC batch vocabulary (C-05);
  `zone_placement.py`.
- **C — promotion** (no schema change): `writes/zone_promotion.py`
  (C-06, C-07), `cockpit/crud/zone_hooks.py` (C-08), the preview route,
  `EntityWriteBody.confirm_promotion`, the AI `status_change` refusal,
  `PromotionModal.svelte` in the fiche; `zone_promotion.py`.
- **D — migration v2.12** (schema v2.12): the index predicate (model, doc,
  migration), in-place conversion, report; `zone_migration.py`.
- **E — neighbours of a zone's children** (no schema change):
  `GET …/neighbours`, `EntityWriteBody.link_to`, `NeighbourPicker.svelte`;
  the room batch's `confirm_promotion` and `room_links` (C-09);
  `zone_children.py`.
- **F — three graph modes** (no schema change): `GET /api/locations/graph
  ?mode=` (C-10), the primitive's `node.r` and `emptyText` axes (C-11), the
  Lieux consumer's three buttons; `zone_graph.py`.

## Dependency graph

Strictly sequential, A → B → C → D → E → F.

- **B, C, D, E, F all need A** (C-01's `zone_rules`, C-02's guard, C-04).
- **C needs B**: the promotion moves beings through
  `write_character_location` and schedules through `write_npc_schedule`,
  whose B guard is what makes the first child a legal destination and the
  zone an illegal one.
- **D needs A and C only through the files it shares** (`zone_rules`,
  `write_relation`). D before C would be possible; the order D after C is
  **chosen**, so the migration ships with the code that keeps the data it
  fixes from reappearing. An executor who finds D independent of C is not
  finding a defect.
- **E needs C** (`promote_for_child`, `take_promotion_gatherings`,
  `PromotionModal.gate`).
- **F needs A** (`zone_ids`, `MAP_TOPOLOGY_TYPES`) and touches no file of
  B–E except `crud/locations.py` (another route) and the decision registry.
  Its place last is **chosen**: the interface comes after the writes.
- Every brief appends one entry just above the footer of
  `tooling/standards/ARCHITECTURE_DECISIONS.md`, which chains them textually.

## RECON

Opened on `main` at `ec925ef` (merge of PR #131, `ticket/0100`): corpus
129/129 green; `npm run build` byte-reproducible (only the manifest's
`built_at` moves). Prototyped on a copy (branch `proto/0101`), one commit per
brief, the full corpus green after each (130, 131, 132, 133, 134, 135 — one
new check per brief), every named mutation measured. The Forêt verte example
was driven in headless Chromium against a scratch database (Forêt verte with
a neighbour, the Secte du Phoenix with two workshops, an NPC with a
schedule, an item, a detail, Millys). Then the ticket, this header and the
six briefs were deposited, each brief's diff was extracted from its own
fence and applied in order on a clean `main`: the tree equals the
prototype's, and `run.py --ticket TICKET-0101-zones` is green. Findings
tagged [M] were measured, [I] inferred from code read in full.

### R-01 — `Relation` model [M]
Opened: `src/world_engine/models/canon_knowledge.py:23-61` (the model).
Finding: no status column; `type` a free `str`; `change_history` a non-null
JSON list. `idx_relation_oriented_social (entity_a_id, entity_b_id)`, unique,
`sqlite_where=text("type NOT IN ('connects_to','controls')")` (`:36-39`),
commented as a re-typing of `RELATION_GRAPH_EXCLUDED_TYPES`.
Consequence: a relation is retyped in place or hard-deleted, never closed
(N1). `borde` in the structural split is DDL on this index (D).

### R-02 — the social/structural split [M]
Opened: `src/world_engine/relation_orientation.py:20-43` (the module that
declares it; `context.py:114` re-exports).
Finding: `RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to",
"controls")` (`:23`); `is_social(t)` = `t not in` the tuple (`:26-30`);
`connects_to_fact_content(a, b)` → `"{a} communique avec {b}."` (`:38-43`).
Consequence: absent from the tuple, `borde` would be social — forced
`a_to_b` (`writes/relations.py:120-123`), a lien fact « éprouve « borde » »
at `unaware`, an encounter between two places (`:161-168`), and the social
unique index. It joins the tuple (A) and the index (D).

### R-03 — `write_relation` [M]
Opened: `src/world_engine/writes/relations.py` (whole, 387 lines).
Finding: `mode="set", relation_id=…` snapshots the row (`_append_history_
snapshot`) then overwrites `type` in place (`_build_relation_set`,
`:213-229`). A new row births its typed fact (`_birth_typed_fact`,
`:144-158`: social → lien `unaware`, `connects_to` → `knows`, else none). A
`set` that changes a type refreshes the fact only social → social
(`_refresh_lien_content`, `:172-186`). The new-row/existing-row switch is
`is_new = sa_inspect(rel).transient` (`:307`). `write_relation` was 78 lines
on `main` (`function_length.py` cap 80).
Consequence: N1 is an in-place retype plus a structural refresh through
`writes/facts.py::update_typed_fact_content` (`:142-154`, keeps the
previous content in `fact.change_history`). The L1 judgment for a type
change runs before any mutation, in a helper, to stay under 80 lines.

### R-04 — the delete path [M]
Opened: `cockpit/crud/relations.py:232-263`; `tooling/verify/checks/
single_canon_write.py:49-80` (the closed list).
Finding: `delete_relation` is a creator-correction hard delete, listed.
Consequence: close-and-recreate (N2) is rejected; nothing in the lot deletes.

### R-05 — who writes a geographic link [M]
Opened: grep of `write_relation(` and `connect_locations(` over `src/` (E3).
Finding: `spatial_author.connect_locations` (`:110-131`, edge + doors) is
called by `crud/relations.create_relation` (`:174-181`) and the room batch
(`room_batch.py:166`, `:190`); the region commit writes `connects_to`
directly (`regions.py:271-279`); `lore_write_apply` writes `controls` only
(`:312`); the two `mutations.py` sites write `relation_change` deltas
(`:171`, `:347`). `PUT /relations/{id}` passes any type to
`write_relation` (`crud/relations.py:204-227`).
Consequence: L1 lives in `write_relation` (C-02), the single writer, so
every path above is judged; the creator paths derive the type before
writing (C-04).

### R-06 — the room batch nests and links each room to its parent [M]
Opened: `cockpit/routes/room_batch.py:101-262`.
Finding: K1 — every committed room's parent–child adjacency is written as a
link (`_commit_batch_tree_edges`, `:159-168`); a room's parent can be a
batch room (`_commit_batch_rooms`, `:109-157`); rooms are created through
`crud._create_entity_core` (`:151`); the commit catches `HTTPException` and
returns `{"ok": False, "error": str(exc.detail)}` (`:246-248`).
Consequence: the anchor, and any room that receives one, becomes a zone;
tree edges are `borde` once the type is derived (A). The anchor's
promotion goes through the S1 confirmation (C, E).

### R-07 — the region commit [M]
Opened: `cockpit/routes/regions.py:183-215`, `:217-290`.
Finding: creates a tree of NEW locations, then the confirmed `connection`
links as `connects_to`, whatever the tree; `_touched_location_ids` keeps
only `type == "connects_to"` links for door materialization (`:294-305`).
Consequence: the region writes the derived type (A); a new parent moves
nothing, so no confirmation is ever needed there.

### R-08 — placement writes, enumerated [M]
Opened: grep of `current_location_id\s*=[^=]` and `Character(` over `src/`
(E1); the registry `cockpit/crud/entities.py:123-140`; `writes/config.py:
412-490`; `crud/locations.py:130-155`; `npc_agent.py:59-110`;
`npc_group_author.py:54-81, 195-209`.
Finding: three sites assign `character.current_location_id` —
`writes/characters.py:48` (`write_character_location`, called only by
`mutations._mutation_apply_npc_move`, `:680`), `play_stream.py:457`
(`_perform_travel`, `:383`, shared by `routes/play.py:285, 389, 459`), and
`routes/creator.py:675-681` (the PC constructor). The registry declares
three `entity_ref` location fields: `character.current_location_id`
(`:132`), `location.parent_location_id`, `item.location_id` (`:136`), all
coerced in `_build_extension_kwargs` (`:336-356`) on create and update — the
NPC batch commit (`npc_agent.py:205-220`) and every fiche reach it. The
schedule has one writer (`write_npc_schedule`, the sole `NpcSchedule(`).
Discoverable details are created at `create_discoverable_detail` only;
their update never moves them. The NPC batch offers `expanded_location_ids`
(root + descendants) and falls back to the root (`:208-209`).
Consequence: seven guard points (B, C-05); the NPC batch vocabulary keeps
visitable members, and a zone root is no fallback.

### R-09 — what sits at a location [M]
Opened: `models/canon.py:143-175` (`character`), `:482-500` (`event`),
`:527-540` (`artifact`), `:548-566` (`item`), `:678-695`
(`discoverable_detail`); `models/ephemeral.py:44-62` (`gathering`),
`:83-100` (`conversation`), `:143-155` (`visit`); `models/schedule.py:40-62`.
Consequence: K's table, row family by row family (C-07).

### R-10 — leaving a place closes gatherings [M]
Opened: `cockpit/crud/entities.py:770-792` (`update_entity`'s location
change); `gathering.py:283-305, 308-358, 361-` (the three functions).
Finding: a fiche location change runs `close_open_memberships`, then
`attach_on_arrival`, and after the commit `dissolve_emptied`, which
analyses an emptied gathering's open conversation (`analyze_window`, errors
logged) and dissolves it.
Consequence: the promotion moves beings with this exact recipe (C-08); « a
journey closes them » is satisfied without a new close path.

### R-11 — where a location gains or loses an active child [M]
Opened: `cockpit/crud/entities.py:525-660` (create cores), `:737-830`
(`update_entity`, `delete_entity`); `cockpit/mutations.py:429-451`
(`status_change`); grep of `parent_location_id\s*=[^=]` and `\.status\s*=`
over `src/` (E2).
Finding: gain — a location created with a parent (`_create_static_entity_
core`), an `update_entity` that re-parents a location or sets it back to
`active`, an approved AI `status_change` that reactivates one. Loss — the
same three, the other way, and `delete_entity` (soft). `update_entity` was
78 lines and `_create_static_entity_core` 72 on `main`.
Consequence: one seam (`promote_for_child`) for the two CRUD sites; the AI
path never shows a dialog, so it is refused when one would be needed.

### R-12 — travel and reachability readers [M]
Opened: each site (E4).
Finding: every traversal reads `type == "connects_to"` and nothing else.
Consequence: L1 holds by construction; none of these lines changes.

### R-13 — structural-exclusion readers [M]
Opened: grep (E5).
Finding: the tuple serves `crud/relations.py:341,365,401`,
`link_context.py:85`, `link_author.py:228,545` and every `is_social`; two
scans spell `!= "connects_to"`: `lore_selectors.py:140` (the dossier, keeps
`controls` on purpose) and `day_concordance.py:301` (keyed on a character).
`regions.py:302` filters links for door materialization, not a scan.
Consequence: the tuple covers the first group; the two scans exclude
`MAP_TOPOLOGY_TYPES` (A).

### R-14 — checks that read this vocabulary [M]
Opened: `tooling/verify/checks/relation_graph.py:83-120` (implementation);
`known_reachability.py:303-335` (`DOCUMENTED_MODULES`);
`knowledge_identity.py:31-35, 109-113` (`_SUBJECT_CENSUS`);
`lore_write.py:185-210` (W2); `migrate_v2_11_lore_entry.py:142-156`
(`_converge_schema_meta`).
Finding: `relation_graph.py` resolves the tuple by regex on a literal;
`known_reachability.py` fails on any new module spelling `"connects_to"`
until it is listed (and classified in `tooling/tickets/connects-to-readers-
TICKET-0082.md`); `knowledge_identity.py` pins every file's count of
`subject` references; `lore_write.py` W2b pinned `"v2.11"` as the version
the v2.11 migration converges to — the migration converges to the code
constant.
Consequence: the tuple stays a literal; `zone_rules.py` (A) and
`writes/zone_promotion.py` (C) are listed and classified; the latter's three
`discoverable_detail.subject` reads join the census; W2b compares to the
constant (D).

### R-15 — the canon-write policy [M]
Opened: `tooling/verify/canon_write_policy.txt`; `single_canon_write.py`
(implementation, function-scoped attribution).
Finding: `write_character_location`, `write_npc_schedule`, `write_relation`
are listed; a new function writing `item` or `discoverable_detail` is not.
Consequence: `writes/zone_promotion.py::apply_promotion item
discoverable_detail` is added, with its reason (C).

### R-16 — schema version and migrations [M]
Opened: `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3,
562-585, 2462-2468`; `world-engine-schema-changelog.md:14-20`;
`scripts/migrate_v2_11_lore_entry.py` (whole); `migrate_v2_00_
connects_to_facts.py:1-35` (data-only migration bumped the version).
Finding: v2.11; migrations refuse an older `schema_meta`, are idempotent,
post-check before converging `schema_meta` to the constant.
Consequence: v2.12, same shape (D).

### R-17 — the lore guarantee [M]
Opened: `lore_write_apply.py:250-330`; `cockpit/routes/lore_write.py:82-89`.
Finding: the Lore tool writes facts, participants, defaults, knowledge,
memberships and `controls`; its entity creator makes a location without a
parent and an NPC without a location.
Consequence: no B guard reaches it; asking about and writing on a zone stay
open. Held by the live gate.

### R-18 — the Lieux graph [M]
Opened: `crud/locations.py:219-261`; `frontend/src/graph/consumers/lieux.js`
(whole, 69 lines); `Graph.svelte` (whole, 337 lines: `NODE_R = 20` `:45`,
clamps `:120-121`, empty text `:297`, circle `:327`, label `:331`);
`mount.js:89-112` (controls: `button` | `checkbox`), `:166-185` (props);
`consumers/relations.js:185-258` (modes through `controls`,
`capabilities(meta)`, `defaultMeta`, `onNodeDblClick → {id}`).
Finding: one mode, every active location, `connects_to` edges.
Consequence: F, with two new optional primitive axes both exercised by
Lieux (`node.r`, `emptyText`).

### R-19 — the fiche's location save [M]
Opened: `frontend/src/creation/Sheet.svelte:451-486` (`saveSheet`, the
location-type gate opening `LocationTypeModal`), `:558-640`
(`submitEntity`); `LocationTypeModal.svelte` (whole); `Modal.svelte`
(whole); `Field.svelte:27, 89-106` (`id = author-x-<name>`, `entity_ref`
select); `factsDraft.svelte.js` (the create-draft store pattern).
Consequence: `PromotionModal` follows `LocationTypeModal`'s instance shape;
the neighbour picker listens to `#author-x-parent_location_id` and keeps its
draft in a store like `factsDraft`.

### R-20 — budgets [M]
Opened: `module_budget.py:57-58`; `function_length.py` + baseline;
`claude_md_contract.py:69-71`.
Finding: 40 functions / 1000 lines per module, 80 lines per function,
CLAUDE.md 38 000 characters and 100 per line, no `TICKET-` in Invariants.
Consequence: new modules for zones and promotion; `_perform_travel`'s
refusals extracted (`_travel_refusal`); `write_npc_schedule`'s docstring
tightened; the CLAUDE.md bullet names no ticket.

## Contract sheet

### C-01 — `zone_rules.py` (family)
Produced by: A   Consumed by: A, B, C, D, E, F
Pure reads, a session's pending rows included (autoflush).
| function | returns | rule |
|---|---|---|
| `active_child_ids(db, location_id, *, exclude_id=None)` | `list[str]` | ids of ACTIVE `location` entities whose `parent_location_id` is `location_id`, oldest first (`entity.created_at`, then id), `exclude_id` left out |
| `is_zone(db, location_id)` | `bool` | at least one active child; None → False |
| `zone_ids(db, world_id)` | `set[str]` | distinct non-null parents of the world's active locations |
| `geographic_link_type(db, a, b)` | `"borde"` \| `"connects_to"` | `borde` iff either end is a zone |
| `require_visitable(db, location_id, *, what)` | `None` | raises `ZoneRefusal(ValueError)` « {what} : « {name} » est une zone, on ne peut s'y trouver que dans l'un de ses lieux » when a zone; None passes |
Written before any member; re-read after `require_visitable` (B's use).

### C-02 — L1/V1 in `write_relation`
Produced by: A   Consumed by: every caller of `write_relation`
Judged on a NEW row and on a `mode="set"` row whose type changes, before
anything is mutated (`_require_map_shape`): a retype into or out of
`MAP_TOPOLOGY_TYPES` raises; a geographic row whose two ends are not both
`location` entities raises; a geographic type other than
`geographic_link_type(a, b)` raises — all `ValueError`. An existing row
whose type does not change is never judged. A new `borde` row births one
fact, `borde_fact_content(token_a, token_b)`, `facet='lien'`,
`default_level='knows'`; a `connects_to` ↔ `borde` change rewrites the fact
through `update_typed_fact_content`.

### C-03 — the vocabulary
Produced by: A   Consumed by: A, D, F
`RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to",
"borde", "controls")` (a literal); `MAP_TOPOLOGY_TYPES: tuple[str, str] =
("connects_to", "borde")`; `borde_fact_content(a, b) -> f"{a} borde {b}."`.

### C-04 — `spatial_author.link_locations`
Produced by: A   Consumed by: A (`create_relation`, room batch), E
`link_locations(db, *, world_id, entity_a_id, entity_b_id, changed_by) ->
Relation`, commit-free. Type = `geographic_link_type`. The pair's existing
geographic row (`find_map_relation`, either order, oldest) is returned
as is when its type matches, retyped in place otherwise; else a new row
(`connects_to` through `connect_locations`, doors for both ends; `borde`
through `write_relation`, no door). A row retyped to `connects_to` gets
`materialize_doors`. `ValueError` (C-02) propagates.
`create_relation` routes any `MAP_TOPOLOGY_TYPES` body through it (422 on
`ValueError`); `update_relation` maps `ValueError` to 409.

### C-05 — the placement guard sites
Produced by: B   Consumed by: C (the moves land on a visitable child)
| site | refusal |
|---|---|
| `play_stream._travel_refusal` (from `_perform_travel`) | `{"status": "zone_destination", "location_id", "detail"}`, nothing written; `POST /api/travel` → 409 `detail` |
| `mutations._mutation_apply_npc_move` | returns the `ZoneRefusal` text ("Needs attention") |
| `routes/creator._validate_pc_creation` | 409 |
| `crud/entities._require_placement_visitable` (character `current_location_id`, item `location_id`) | 409, only when the value is set and differs from the stored one |
| `writes/config.write_npc_schedule` | `ZoneRefusal` (a `ValueError`; the route maps it to 422) |
| `crud/locations.create_discoverable_detail` | 409 |
| `npc_group_author.resolve_vocabulary` / `_resolve_unit_location` | zones left out; a zone root is no fallback (note « Placement non résolu — la racine est une zone, PNJ sans lieu », location None) |

### C-06 — `promotion_preview` (the dict)
Produced by: C   Consumed by: C (route, 409, modal), E (room batch gate)
`promotion_preview(db, parent_id, *, child_id=None) -> dict`:
`{"location_id", "location_name", "promotes": bool, "needs_confirmation":
bool, "target_is_zone": bool, "links": [{id, other_id, other_name}], "beings": [{id, name,
character_type}], "schedules": [{npc_id, npc_name, phase}], "items": [{id,
name}], "details": [{id, subject}], "gatherings": [{id, label}]}`.
`promotes` False (every list empty) when `parent_id` is None, not a
location, or has an active child other than `child_id`. `links` are the
parent's `connects_to` rows only. `needs_confirmation` = `promotes` and any
list non-empty. `target_is_zone` = `is_zone(child_id)` (False without a
`child_id`). Served read-only by `GET /api/locations/{id}/promotion-
preview?child_id=`.
Amended by AMENDMENT-0101-01 (`target_is_zone` added).

### C-07 — `apply_promotion`
Produced by: C   Consumed by: C-08
`apply_promotion(db, *, parent_id, child_id, changed_by) -> dict` (the
preview it applied), commit-free, `child_id` already in the session: each
`links` row → `write_relation(mode="set", relation_id, type="borde", …)`;
each being → `write_character_location(… child_id)`; each NPC with a
schedule row at the parent → one full-replace `write_npc_schedule` of its
whole schedule with that location swapped; each item and detail →
`location_id = child_id`. Gatherings: listed, never touched here.

### C-08 — the CRUD seam and S1
Produced by: C   Consumed by: C, E
`EntityWriteBody.confirm_promotion: bool = False`.
`promote_for_child(db, entity, ext, *, confirmed, prior_parent_id=None,
prior_status=None)`: acts when `entity` is an active location whose
`ext.parent_location_id` is set and either differs from `prior_parent_id`
or `prior_status != "active"`; calls `promote_parent`:
| preview | `confirmed` | result |
|---|---|---|
| `promotes` False | any | nothing |
| `needs_confirmation` False | any | applied |
| `needs_confirmation` True, `target_is_zone` True | any | 409, detail a string: « « {child} » est déjà une zone : le contenu de « {parent} » ne peut pas y être déplacé. Rattachez d'abord un lieu visitable à « {parent} », ou videz « {parent} ». »; nothing written |
| `needs_confirmation` True | False | 409 `{"code": "promotion_required", "preview": <C-06>}` |
| `needs_confirmation` True | True | applied; moved beings `close_open_memberships` + `attach_on_arrival(child)` |
Gathering ids to dissolve (emptied ones, the parent's open ones) are parked
on `db.info`; `take_promotion_gatherings(db)` returns and removes them; the
caller passes them to `dissolve_emptied` after its commit.
`_mutation_apply_status_change` refuses a reactivation whose preview needs
confirmation. `PromotionModal.gate` opens no dialog when `target_is_zone`:
the save goes through and the 409 message reaches the fiche's status line.
Amended by AMENDMENT-0101-01 (the `target_is_zone` row).

### C-09 — children take the parent's neighbours
Produced by: E   Consumed by: E
`GET /api/locations/{id}/neighbours` → `[{id, name, is_zone}]`, the active
locations joined to `id` by a geographic row, by name.
`EntityWriteBody.link_to: list[str] = []`; on a location create, after any
promotion, each id (deduplicated, self skipped) goes through
`link_locations` (422 on `ValueError`).
`RoomBatchCommitBody.confirm_promotion: bool = False` (passed into every
room's `EntityWriteBody`) and `room_links: dict[str, list[str]] = {}`
(local_id → ids, linked after the tree and supplementary edges, rooms not
committed skipped); after the commit, `dissolve_emptied(take_promotion_
gatherings(db))`; an `HTTPException` whose detail is a dict reports its
`code` as `error`.

### C-10 — `GET /api/locations/graph?mode=&center=`
Produced by: F   Consumed by: `consumers/lieux.js`
| mode | nodes | edges |
|---|---|---|
| `visitable` (default) | active locations not in `zone_ids` | `connects_to`, both ends kept |
| `zones` | active zones; `r = 30` when no parent | `borde`, both ends kept |
| `ego` | `center` (`r = 30`) and its active children | both types, both ends kept |
| `ego`, `center` not a zone | none; `"empty_text": "Ouvrez une zone."` | none |
| other | 422 | — |
Node `{id, name, coord_x, coord_y, is_zone[, r]}`; edge `{id, entity_a_id,
entity_b_id, direction, kind}`.

### C-11 — two primitive axes
Produced by: F   Consumed by: Lieux (the only consumer passing them)
`Graph.svelte`: a node's optional `r` sizes its circle and offsets its
label (`radiusOf(node) = node.r ?? NODE_R`); prop `emptyText = 'Aucun
nœud'`. `mount.js` passes `emptyText: data.emptyText` (undefined keeps the
default).

## Gate output

### (a) Property trace
| property asserted by the lot | finding | declaring file opened |
|---|---|---|
| relation has no status; type is free | R-01 | `models/canon_knowledge.py:23-61` |
| the social index predicate | R-01 | `models/canon_knowledge.py:36-39` |
| `is_social` = not in the tuple | R-02 | `relation_orientation.py:20-30` |
| `connects_to` fact template | R-02 | `relation_orientation.py:38-43` |
| set-mode retypes in place with history | R-03 | `writes/relations.py:213-229` |
| fact refresh is social → social only | R-03 | `writes/relations.py:172-186` |
| typed fact at birth by class | R-03 | `writes/relations.py:144-158` |
| `update_typed_fact_content` keeps history | R-03 | `writes/facts.py:142-154` |
| `delete_relation` is in the closed list | R-04 | `single_canon_write.py:49-80` |
| `connect_locations` writes edge + doors | R-05 | `spatial_author.py:110-131` |
| region writes `connects_to` directly | R-07 | `routes/regions.py:271-279` |
| room tree edges and nesting | R-06 | `routes/room_batch.py:109-168` |
| batch reports `HTTPException` detail | R-06 | `routes/room_batch.py:246-248` |
| three `current_location_id` assignment sites | R-08 | E1 |
| registry location `entity_ref` fields | R-08 | `crud/entities.py:123-140` |
| extension kwargs built in one function | R-08 | `crud/entities.py:336-356` |
| one schedule writer, raw full replace | R-08 | `writes/config.py:412-490` |
| detail created in one route | R-08 | `crud/locations.py:130-155` |
| NPC batch vocabulary and root fallback | R-08 | `npc_group_author.py:54-81, 195-209` |
| location columns by table | R-09 | the model modules listed in R-09 |
| fiche move recipe for gatherings | R-10 | `crud/entities.py:770-792`, `gathering.py:283-358` |
| child gain/loss sites | R-11 | E2, `crud/entities.py`, `mutations.py:429-451` |
| traversal readers read `connects_to` only | R-12 | E4 |
| exclusion readers | R-13 | E5 |
| `relation_graph.py` needs a literal | R-14 | `relation_graph.py:83-120` |
| new `connects_to` module must be listed | R-14 | `known_reachability.py:303-335` |
| subject census per file | R-14 | `knowledge_identity.py:109-113` |
| v2.11 migration converges to the constant | R-14 | `migrate_v2_11_lore_entry.py:142-156` |
| new item/detail write site needs a policy line | R-15 | `single_canon_write.py` (implementation), policy file |
| version, migration shape | R-16 | `schema_version.py:15`, the v2.11 script |
| lore writes no placement | R-17 | `lore_write_apply.py:250-330`, `lore_write.py:82-89` |
| graph primitive props, radius constant | R-18 | `Graph.svelte` (whole) |
| control kinds | R-18 | `mount.js:89-112` |
| mode pattern of a consumer | R-18 | `consumers/relations.js:185-258` |
| fiche save path and modal shape | R-19 | `Sheet.svelte:451-640`, `LocationTypeModal.svelte`, `Modal.svelte` |
| field ids | R-19 | `Field.svelte:27` |
| budgets | R-20 | `module_budget.py:57-58`, `function_length.py`, `claude_md_contract.py:69-71` |

Presupposition sweep: no brief says "follow the convention" without naming
its source. Each "as" names it: the fiche's gathering recipe
(`crud/entities.py:770-792`), `LocationTypeModal`'s instance shape, the
relations consumer's modes (`consumers/relations.js:185-258`),
`factsDraft.svelte.js`'s store, the v2.11 migration's shape.

### (b) Case tables

**C-02, `write_relation`:**
| row | ends | type asked | result |
|---|---|---|---|
| new | two visitable | `connects_to` | written, fact `knows` |
| new | two visitable | `borde` | `ValueError` |
| new | a zone involved | `connects_to` | `ValueError` |
| new | a zone involved | `borde` | written, fact `knows`, no encounter |
| new | a non-location end | `connects_to` / `borde` | `ValueError` |
| set, same type | any (a demoted zone's `borde`) | unchanged | written, not judged |
| set, `connects_to` → `borde` | a zone involved | `borde` | retyped, fact rewritten, both histories +1 |
| set, social ↔ geographic | any | — | `ValueError`, nothing mutated |
| delta (social) | — | — | unchanged |

**C-08, the promotion trigger:**
| write | parent's other active children | something to move | `confirm_promotion` | result |
|---|---|---|---|---|
| create location with parent P | ≥ 1 | — | — | no promotion |
| create location with parent P | 0 | no | — | promoted silently |
| create location with parent P | 0 | yes | false | 409, nothing written |
| create location with parent P | 0 | yes | true | promoted, K applied |
| update: same parent, was active | — | — | — | nothing |
| update: new parent P | as above | | | as above |
| update: inactive → active | as above | | | as above |
| update or reactivation, the location itself a zone | 0 | yes | any | 409 « … est déjà une zone … » (AMENDMENT-0101-01) |
| update or reactivation, the location itself a zone | 0 | no | — | promoted silently |
| AI `status_change` → active | 0 | yes | — | "Needs attention" |
| delete / deactivate the last child | — | — | — | P visitable again, nothing moves, `borde` kept |

**C-05, a fiche's character location:**
| create/update | value | stored | result |
|---|---|---|---|
| create | zone | — | 409 |
| create | visitable / none | — | accepted |
| update | zone | other | 409 |
| update | zone | same zone | accepted (reported by D) |

**C-10:** written in the contract above.

### (c) Enumerations

E1 — `git grep -n -e "current_location_id\s*=[^=]" -e "Character(" ec925ef -- 'src/world_engine/*.py'` (class/select/isinstance lines dropped):
```
src/world_engine/cockpit/play_stream.py:457:    char.current_location_id = location_id
src/world_engine/cockpit/routes/creator.py:675:        character = Character(
src/world_engine/cockpit/routes/creator.py:680:            current_location_id=body.current_location_id,
src/world_engine/lore_selectors.py:97:                current_location_id=character.current_location_id,   (a read into a dict)
src/world_engine/writes/characters.py:48:    character.current_location_id = to_location_id
```
plus the generic `setattr(ext, key, value)` of `crud/entities.py:766` and the
create core's `ext_model(id=…, **ext_kwargs)` (`:607`), both fed by
`_build_extension_kwargs`.

E2 — `parent_location_id\s*=[^=]` and `\.status\s*=[^=]` over `src/` on
`main`: no assignment of `parent_location_id` outside the registry path;
entity `status` assigned at `crud/entities.py:333` (`_apply_base_fields`),
`:821` (`delete_entity`) and `cockpit/mutations.py:447` (`status_change`);
every other hit is a goal, step, agenda, run, batch, pass, conversation or
gathering status.

E3 — `git grep -n -e "write_relation(" -e "connect_locations(" ec925ef -- 'src/*.py'`:
```
cockpit/crud/relations.py:175 connect_locations   :186 write_relation   :216 write_relation
cockpit/mutations.py:171 write_relation   :347 write_relation
cockpit/routes/regions.py:271 write_relation (connects_to)   :281 write_relation (controls)
cockpit/routes/room_batch.py:166 connect_locations   :190 connect_locations
link_author.py:814 write_relation
lore_write_apply.py:312 write_relation (controls)
spatial_author.py:124 write_relation (connects_to)
writes/relations.py:348 write_relation (write_oriented_relations)
```

E4 — traversal readers on `main`, each `type == "connects_to"` only:
`cockpit/play.py:860,866`, `day_plan.py:239`, `day_concordance.py:193`,
`tick_context.py:554`, `spatial_author.py:35,41`,
`cockpit/spatial_doors.py:66,73`, `cockpit/routes/regions.py:342,345`,
`room_batch_author.py:147`, `cockpit/crud/entities.py:300,307`,
`writes/config.py:230,237`, `cockpit/crud/locations.py:248`.

E5 — `git grep -n -e "RELATION_GRAPH_EXCLUDED_TYPES)" -e '!= "connects_to"' ec925ef -- 'src/*.py'`:
```
cockpit/crud/relations.py:341,365,401   not_in(_RELATION_GRAPH_EXCLUDED_TYPES)
cockpit/routes/regions.py:302           link.get("type") != "connects_to"   (door materialization filter)
day_concordance.py:301                  Relation.type != "connects_to"
link_author.py:228,545                  not_in(RELATION_GRAPH_EXCLUDED_TYPES)
link_context.py:85                      not_in(RELATION_GRAPH_EXCLUDED_TYPES)
lore_selectors.py:140                   Relation.type != "connects_to"
```

### (d) Families
✓ C-01 (`zone_rules`) written before A's members and re-read after B's use
of `require_visitable`. ✓ C-05 (seven guard sites) written as one table
before B, re-read after C (the promotion's moves go through two of them).
✓ C-10 (three modes) written before F's route.

### (e) Gates and the module that satisfies each
| gate | status | satisfied by |
|---|---|---|
| `zone_map_links.py` | proposed (A) | `writes/relations.py`, `spatial_author.py`, `relation_orientation.py`, the two scans |
| `zone_placement.py` | proposed (B) | the seven sites of C-05 |
| `zone_promotion.py` | proposed (C) | `writes/zone_promotion.py`, `crud/zone_hooks.py`, `crud/entities.py`, `mutations.py` |
| `zone_migration.py` | proposed (D) | `scripts/migrate_v2_12_zone_borde.py` |
| `zone_children.py` | proposed (E) | `crud/zone_hooks.link_new_location`, `crud/locations.py`, `routes/room_batch.py` |
| `zone_graph.py` | proposed (F) | `crud/locations.get_locations_graph`, `Graph.svelte`, `mount.js`, `consumers/lieux.js` |
| `relation_graph.py` | passed (A) | the tuple stays a literal |
| `relation_orientation.py` | passed (A) | its fixture links two parentless locations: visitable |
| `known_reachability.py` | passed (A, C) | `zone_rules.py`, `writes/zone_promotion.py` listed and classified |
| `knowledge_identity.py` | passed (C) | `writes/zone_promotion.py: 3` in the census |
| `single_canon_write.py` | passed (C) | the policy line for `apply_promotion` |
| `function_length.py` | passed (A, B, C, E) | `_checked_old_type` (`write_relation` 77); `_travel_refusal`; `update_entity` 79, `_create_static_entity_core` 75 |
| `module_budget.py` | passed | new modules; `crud/entities.py` 915 lines |
| `claude_md_contract.py` | passed (A, B) | one bullet, no ticket id, under 38 000 characters |
| `lore_write.py` | passed (D) | W2b compares to `EXPECTED_STATIC_SCHEMA_VERSION` |
| `schema_version_agreement.py` | passed (D) | doc and constant both v2.12 |
| `graph_primitive.py` | passed (F) | no new spec key; the axes are props |
| `frontend_build_fresh.py`, `effect_self_write.py`, `import_cycle.py` | passed (C, E, F) | rebuild per brief; the room batch effect only assigns |
| `decisions_index.py` | passed (A–F) | one strict header per brief, index regenerated |

## Amendments

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0101-01 | C | a location that becomes a child while it is itself a zone received its new parent's contents (B1 broken, a 500 on schedules); P2-1: refused with a message, C-06 gains `target_is_zone`, C-08 a row, `zone_promotion.py` an assertion (f) | C (contracts, diff, Scope IN, Done means); D, E, F (diffs only: the decision registry's context lines moved) |
