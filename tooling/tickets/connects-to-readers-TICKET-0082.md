# connects-to-readers (TICKET-0082) — `connects_to` read-site classification

BRIEF-0082-d, Scope IN item 1 (amended by
`BRIEF-0082-d-amendment-1-public-floor-reader.md`, H3: the label set is
five, not four). The brief's own text names this file
`tooling/tickets/TICKET-0082-connects-to-readers.md` — deviated on
disk to `tooling/tickets/connects-to-readers-TICKET-0082.md` because a
`TICKET-` prefix in `tooling/tickets/` makes `pipeline_state.py` parse it
as a full ticket (front matter, `### Machine-checkable`/`### Live`
sections) and makes `/pipeline`'s slug-resolution glob
(`TICKET-0082-*.md`) ambiguous against the real ticket file. Same content,
same location, filename only. This table is the durable artifact:
`tooling/verify/checks/known_reachability.py` reads it — an unclassified
site is a FAIL, and a thirteenth `connects_to`-referencing module makes the
check fail before it even reaches the table.

Labels, verbatim (amendment 1):

```
resolution     — decides whether something that has been proposed is
                 legal. Reads canon. Must NOT be knowledge-filtered.
deliberation   — decides what a CHARACTER considers, proposes or is
                 offered. Filtered by that character's resolved level.
                 A site with this label always passes an entity_id.
public         — feeds a prompt that no single character governs.
                 Filtered by the PUBLIC FLOOR: the same resolution
                 authority entered at its world tier, with no entity.
                 A site with this label NEVER passes an entity_id.
authoring      — creator or generator building the graph itself. Reads
                 and writes canon. Not filtered.
vocabulary     — a type literal or exclusion list, not a traversal.
```

Two kinds of row below. **Module rows** are the twelve modules the
mini-RECON measured (module-count invariant — a thirteenth module with a
literal `connects_to` string is a FAIL, checked independently of this
table). **Call-site rows** exist only for `tick_context._reachable_locations`,
whose one internal query (`tick_context.py:492`) is shared by two callers
in two different files with two different filter semantics — the module
count stays twelve (`tick.py` contains no literal `"connects_to"` string;
it only calls the reader by name), but the classification and the
knower_id AST check (assertion 4) both operate at call-site granularity for
this one reader.

## Module rows (twelve)

| # | Module : line(s) | Label | Why |
|---|---|---|---|
| 1 | `room_batch_author.py:141` | `authoring` | Assembles a room-batch manifest's existing `connects_to` edges among siblings for the generator; reads truth, writes nothing here but is squarely the authoring pipeline. |
| 2 | `day_concordance.py:239` (`_concord_reachable_ids`) | `resolution` | Disambiguates a place MENTIONED in the player's own day-declaration text against the reachable candidate set. Reads canon truth about what the text could mean; filtering by the player's belief would make disambiguation of their own words depend on what they're assumed to know, which is backwards. Not the BFS this brief converts (day_plan.py's is; see the escalation below for why the player path stays unfiltered end to end). |
| 3 | `day_concordance.py:343` (`_cast_relation`) | `vocabulary` | `Relation.type != "connects_to"` — an exclusion, not a traversal (the function scans social relations and structurally excludes map topology). |
| 4 | `tick_context.py:492` (`_reachable_locations`, the query itself) | *(see call-site rows)* | One query, two callers with different `knower_id` — classified per call site, not here. |
| 5 | `writes/config.py:280,287` (`write_location_doors`) | `resolution` | B1 gate: rejects a door write when no active `connects_to` edge touches both endpoints. Decides whether a proposed write is legal; doors are physical structure, never knowledge-filtered. |
| 6 | `cockpit/spatial_doors.py:66,73` (`location_doors`) | `resolution` | PLAY-SIDE door resolution — B1's read half. A door resolves live only if canon still backs it. Physical reality, not belief; must not be knowledge-filtered. |
| 7 | `cockpit/crud/entities.py:323,330` (`_location_doors_rows`) | `authoring` | Explicitly "CREATOR-FACING" per its own docstring — returns orphaned doors (`edge_live: false`) so the creator can fix them. Creator sees everything. |
| 8 | `cockpit/crud/relations.py:123` | `authoring` | Creator CRUD write dispatch: `type == "connects_to"` routes to `connect_locations`. Write path. |
| 9 | `cockpit/crud/locations.py:250` | `authoring` | "Active location nodes + connects_to edges — read-only, creator surface" per its own docstring. |
| 10 | `cockpit/play.py:861,867` (`_location_neighbours`) | `resolution` | Legacy Play surface (sealed, TICKET-0061): offers travel candidates AND validates a chosen destination is a live neighbour. Unfiltered truth reader, untouched by this brief — see the escalation below; the player has no deliberation stage this ticket fixes. |
| 11 | `cockpit/routes/regions.py:285,288,313,353,356` | `authoring` | Region-commit write path (`write_relation(type="connects_to", ...)`), the `_touched_location_ids` door-materialization bookkeeping, and the building-shell street-access advisory note. All creator-commit-time, all truth reads, none filtered. |
| 12 | `day_plan.py:228` (`_day_reachable_ids`) | `resolution` | **NOT repointed by this brief** (amendment 1: repointing it would violate D1 — see below). Feeds `_eval_location_reachable`, the day chain's step-precondition judge: reads canon, decides legality of an already-proposed step. This is the resolution reader B2 says stays untouched — the escalation below is why leaving it unfiltered is a real, named gap, not an oversight. |
| 13 | `spatial_author.py:35,41` (`_live_neighbour_ids`) | `authoring` | "Active-location connects_to neighbours" feeding `materialize_doors`, the creation-side door generator. |
| 14 | `spatial_author.py:127` (`connect_locations`) | `authoring` | Writes a `connects_to` edge and materializes doors for both endpoints — the single write point for this edge type. |

(Rows 13/14 are both `spatial_author.py`, one module — twelve modules
total: room_batch_author, day_concordance, tick_context, writes/config,
cockpit/spatial_doors, cockpit/crud/entities, cockpit/crud/relations,
cockpit/crud/locations, cockpit/play, cockpit/routes/regions, day_plan,
spatial_author.)

## Call-site rows — `tick_context._reachable_locations` (two callers)

| Call site | `knower_id` | Label | Why |
|---|---|---|---|
| `tick.py:73` (`_tick_npc_setup`) | the NPC's own `entity_id` | `deliberation` | Feeds `assemble_tick_context`'s `destinations` — what THIS NPC's own tick briefing offers it. A specific character governs. |
| `tick_context.py:566` (`assemble_location_event_context`) | `None`, always | `public` | Feeds the "LES ENVIRONS" section of a location-scope event briefing, consumed by `_tick_run_scope_events` -> `_tick_call_scope_model`. No single character governs an ambient scope-event proposal; the other two filtered sections of the same function (`is_hidden`, `knowledge_status`) already apply a non-character, structural filter — the public floor is the same kind of filter for the topology section. |

Assertion 4 (the AST check) verifies exactly this: every `_reachable_locations(`
call site passing a bare NPC/entity id keyword is `deliberation`-shaped
(`knower_id=<not None>`), every one passing `knower_id=None` is
`public`-shaped, and flipping either breaks the check (amendment 1's fifth
named mutation).

## Vocabulary sites (not traversals — reported, not classified as readers)

- `context.py:110` — `RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "controls")`.
- `cockpit/crud/_shared.py:137` — the relation-type datalist literal.
- `link_author.py:68` — `assert "connects_to" not in _LINK_RELATION_TYPES`.

These three are outside the twelve-module traversal count (they hold a type
literal, never execute a `connects_to` traversal) but are listed here for
completeness since they reference the string; `known_reachability.py` does
not require them to carry one of the five labels — only actual read/write
sites do (rows 1-14 above).

## Escalation on record — the player has no deliberation stage

Row 12 (`day_plan.py:228`) and row 10 (`cockpit/play.py:861,867`) are both
classified `resolution` and are both, deliberately, left unfiltered by this
brief. B2's safety composition ("deliberation narrows, resolution
verifies") holds for an NPC, which has a briefing to narrow. It does not
hold for the player, who has no deliberation stage — a day declaration is
free text with no structured "destinations offered" step, and the legacy
Play surface offers/validates travel through the same unfiltered
`_location_neighbours`. TICKET-0082 delivers knowledge-gated reachability
for NPCs (`tick.py:73`, `deliberation`) and for location-scope generation
(`tick_context.py:566`, `public`) — it does NOT deliver it for the player.
Filtering either player-facing reader would be a perception-layer fact
producing a mechanical verdict (E2), explicitly deferred by this ticket.
Recorded here, per `BRIEF-0082-d-amendment-1-public-floor-reader.md`'s
instruction, as the reactivation condition for a successor ticket — not
implemented, not widened, here.
