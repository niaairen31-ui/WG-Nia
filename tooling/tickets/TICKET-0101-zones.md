---
id: TICKET-0101
title: Zones and visitable places — the `borde` relation, automatic promotion, three graph modes
type: feature
status: live-gate
created: 2026-10-01
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large
lot_id: LOT-0101-zones.md
brief_ids: [A, B, C, D, E, F]
current_brief:
schema_version_touched: v2.12
retry_count: 0
slug: zones
---

## Request (verbatim, as Nia stated it)

> Premièrement, je pense qu'il dois y avoir une différence entre les lieux
> ''parents'' et les lieux ''enfants''. Selon moi, les les seul lieux qui
> peuvent être visité sont des lieux qui n'ont pas de parents. Dans mon cas,
> j'ai la secte du Phoenix qui est un district (quartier) et plusieurs lieux
> enfants qui sont des lieux visitable dans le quartier. (atelier
> d'alchimie, intendance, pavillon des disciples, terrain d'entrainement. Si
> tu es dans l'une de ses places, tu es dans le quartier, mais si le joueur
> va directement dans le quartier, cela fait moins de sens.

Planning answers, in order:

> A1, B1 mais je veux être certaine que cela ne m'empêchera pas de posé des
> questions sur la ''zone'' a mon outil de lore. ou écrire des chose sur
> cette zone dans ce même outil. C2 absolument, je veux que les Zone soit
> connecté ensemble, cela peut rester arbitraire pour le moment la notion
> de frontière n'existant pas encore. D on accepte, mais on résoud les
> conflits. automatiquement. Ex : j'ai la forêt verte dans mon jeu pour le
> moment. Éventuellement, je vais vouloir le subdivisé. Je vais avoir
> l'entrée de la forêt, les ombres de la forêts et le coeur de la forêt. Je
> veux que la forêt gagne un promotion en tant que Zone, ses voisins sont
> maintenant voisins de la Zone. a la création d'un enfant, on me propose
> les voisins et le peut coché celles qui sont aussi voisine de mon lieu
> enfant. […] Applique la même logique pour tous les autres conflits
> possible et propose moi une résolution. […] H1 pour le moment.

> J Je pense que j'ai fait un erreur dans mon exemple, tu as raison. Je veux
> que les Zones deviennent des lieux géographique seulement. On ne voyage
> qu'entre deux lieux visitable. Les lieux visitables sont : tous les lieux
> n'ayant PAS de lieux parents. Le zone sont tous les lieux qui ONT au moins
> un lieu enfant. H est-ce que l'on peut avoir plusieurs Graphs qui nous
> montre différentes choses (1- les lieux visitables, 2- Les Zones (Les
> zones parentes qui n'ont pas de parent sont un peu plus grosse que les
> Zone qui ont un parent, 3- Ego graph des lieux parents ) F-a. K c'est
> bien, E oui, I parfait en deux ticket.

> Oui, c'est cela la définition. L1 oui pour borde, Je suis d'accord avec
> les ajouts. M1 ok pour tes proposition. Je confirme la separationé

## Clarifications resolved (intake)

- **The definition, confirmed by Nia:** a **zone** is a location with at
  least one active child; a **visitable** location is a location with no
  active child. Her wording « n'ayant pas de parents » was read back to
  her as « pas d'enfants » (the Atelier d'alchimie has a parent and is
  visitable) and she confirmed.
- **The Lore tool is unaffected.** A zone stays a full location entity. The
  rule blocks only *placing a being* in a zone. Measured at intake:
  `lore_write_apply.py` writes facts, memberships and `controls` relations
  (`:266-318`) and never a character's location. Asking about a zone,
  writing facts about it, or saying a faction controls it stay open. The
  0101 RECON re-verifies this and the lot carries it as a criterion.
- **Travel never goes through a zone** (J3): zones are geography only.
- **Example to replay at the live gate:** the Forêt verte, a visitable
  location with neighbours, gets a first child « Entrée de la forêt »; it
  becomes a zone, its connections become `borde`, the creation proposes
  its neighbours as checkboxes for the child; then « Les ombres de la
  forêt » and « Le cœur de la forêt » with no neighbour ticked.

## Decisions locked (do not re-litigate without Nia)

- **A1** — zone/visitable is derived from the tree (≥ 1 active child), never
  stored; no zone flag, no per-type setting.
- **B1** — every path that places a being refuses a zone: the player's
  travel, an NPC move applied from a mutation, the fiche's current
  location, PC creation, NPC schedules (the RECON enumerates the paths;
  that list is a starting point, not a closed set). Existing data is
  reported, never silently corrected.
- **C2** — zones connect to each other; the adjacency is arbitrary for now
  (no notion of border yet).
- **J3** — zones are geographic only; travel happens only between two
  visitable locations.
- **L1** — a second relation type, `borde`. `connects_to` links two
  visitable locations only and is the only traversable link; the write
  refuses a `connects_to` touching a zone. `borde` is the geographic link
  whenever a zone is involved (zone–zone or zone–location). The type is
  derived from the two endpoints; the creator never chooses it. The
  travel and reachability readers (`_location_neighbours`, `day_plan`,
  `day_concordance`, `tick_context`, measured at intake; the RECON
  enumerates) change no line: no `connects_to` can reach a zone. `borde` gets a lore fact, as `connects_to` already does.
- **D + K** — adding a first child to a visitable location is accepted and
  its conflicts are resolved automatically, after a confirmation dialog
  listing everything that will move:

  | what touches the promoted location | resolution |
  |---|---|
  | its connections | become `borde`, staying on the zone; the dialog lists them |
  | creating any child of a zone | the zone's neighbours are offered as checkboxes; a visitable one ticked → `connects_to`, a zone ticked → `borde` |
  | beings present (PC, NPC) | moved to the first child |
  | NPC schedules | retargeted to the first child |
  | items lying there, discoverable details | moved to the first child |
  | open gatherings | closed, as a journey closes them |
  | inner plan (bounds, obstacles, doors) | kept untouched and dormant; doors pointing at it go dormant on their own (the engine already hides a door whose edge is gone); doors are not copied to the child |
  | events, facts, knowledge, faction control, artefacts | untouched: they now describe the zone |
  | a zone losing its last active child | becomes visitable again; nothing moves; its links stay |

- **Migration** — at deploy, every existing `connects_to` touching a
  location that is already a zone becomes `borde`; the run reports each one.
- **M1** — one « Voir le graphe » slot with three modes in its head:
  **Lieux visitables** (visitable nodes, `connects_to` edges — the travel
  map), **Zones** (zone nodes, `borde` edges; top-level zones drawn larger
  than nested ones), **Ego** (one zone centred, its children around it, the
  links among them). Linking two nodes in any mode creates the type the two
  endpoints dictate. Node size is a new optional per-node radius on the
  graph primitive, first used by the Zones mode. The Ego centre is the zone
  open in the fiche; a double-click on a child zone recentres; a fiche that
  is not a zone shows « Ouvrez une zone ».
- **I2** — TICKET-0100 carries the list, « + lot » and the graph click fix;
  this ticket carries everything about zones.

- **N1** (lot RECON R-01, R-03) — a `connects_to` becomes `borde` by an
  in-place type change through `write_relation(mode="set")`: the previous row
  state goes to `relation.change_history`, the typed fact is rewritten through
  `update_typed_fact_content` (its old content kept in `fact.change_history`).
  No delete. Rejected: close-and-recreate (needs a hard-delete path, loses
  history; reactivates if `relation` ever gets a status column).
- **O1** (R-01, R-02, R-19) — `borde` joins the structural split:
  `RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "borde", "controls")`, kept a
  literal; migration v2.12 rebuilds `idx_relation_oriented_social` with the
  matching predicate; the two literal exclusions (`lore_selectors.py`,
  `day_concordance.py`) exclude `borde` too. Rejected: tuple only (schema lies).
- **P1** (R-11, R-12) — one guard, `require_visitable`, called at every
  placement write site, plus a DB-backed G1 check that drives each path into a
  zone and expects a refusal. Rejected: funnelling every write through
  `write_character_location` (reactivates when a seventh write site appears).
- **Q1** (R-14) — items lying somewhere and discoverable details refuse a zone
  too, with the same guard.
- **R1** (R-09, R-10) — room-batch and region commits derive every link's type
  from its endpoints; the room-batch anchor goes through the promotion dialog;
  the batch review offers the anchor's neighbours as checkboxes for each
  top-level room. A room that receives a room becomes a zone (accepted).
  Rejected: flattening batches (reactivates if R1 makes buildings unmanageable).
- **S1** — a read-only endpoint computes what a promotion moves; any write that
  would promote is refused (409 with that preview) unless it carries
  `confirm_promotion`. Rejected: a client-only dialog.
- **T1** — the v2.12 migration report lists beings, schedules, items and
  details already sitting in a zone; Nia corrects them through the fiche.
- **V1** — the fiche relation form offers one geographic entry; the server
  derives `connects_to`/`borde`; retyping to or from either is refused.
- **P2-1** (AMENDMENT-0101-01) — a location that becomes a child while it
  is itself a zone receives nothing: when the promotion would move
  something, the write is refused with a message, confirmed or not.
  Rejected: re-targeting to the first visitable descendant (arbitrary;
  reactivates if Nia wants to graft an inhabited subtree in one step) and
  deferring (ships a B1 breach).
- **Cut confirmed:** A vocabulary and L1 guard; B placement guards; C promotion
  preview, apply and dialog; D migration v2.12; E neighbour checkboxes, room
  batch and region; F three graph modes.

## Carried forward / open

Deferred, each its own ticket when it comes:

- **« Being in the atelier is being in the quarter »** — no reader rolls a
  location up to its zones yet (MJ context, lore, « who is in the Secte? »).
  Reactivates the first time play or lore needs the containing zone.
- **Borders** — a real notion of frontier between zones (C2 keeps
  adjacency arbitrary). Reactivates when Nia defines one.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every ticket's front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus runs green  -> verify/checks/corpus_gate.py
- [ ] A geographic link's type follows its endpoints; `borde` is structural and excluded wherever `connects_to` is  -> verify/checks/zone_map_links.py
- [ ] Every travel or reachability reader stays documented and reads `connects_to` only  -> verify/checks/known_reachability.py
- [ ] No placement path accepts a zone  -> verify/checks/zone_placement.py
- [ ] A first child promotes its parent, behind the confirmation  -> verify/checks/zone_promotion.py
- [ ] Migration v2.12 rebuilds the index, converts in place, reports, is idempotent  -> verify/checks/zone_migration.py
- [ ] A zone's children take its neighbours; the room batch promotes its anchor  -> verify/checks/zone_children.py
- [ ] The Lieux graph serves its three modes  -> verify/checks/zone_graph.py

### Live  ->  human gate (Nia)
- [ ] The Forêt verte example above, end to end: the dialog lists what
      moves; the forest becomes a zone; its links are `borde`; the first
      child receives the beings, schedules and items; the neighbour
      checkboxes create the right link type.
- [ ] Millys cannot travel to the Secte du Phoenix itself; she can travel
      between two visitable places linked by `connects_to`.
- [ ] The Lore tool answers a question about the Secte du Phoenix and
      writes a fact about it, as before.
- [ ] The graph's three modes show what M1 says; top-level zones are drawn
      larger; Ego follows the zone open in the fiche.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0101-01 | C | a child that is itself a zone received its new parent's contents; P2-1: refused with a message | C; D, E, F (diffs) |
