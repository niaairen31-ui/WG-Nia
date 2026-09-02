---
id: TICKET-0082
title: Fact spine — structural anchor for knowledge
type: feature
status: brief
created: 2026-09-01
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large
brief_ids: [BRIEF-0082-a, BRIEF-0082-b, BRIEF-0082-c, BRIEF-0082-d]
schema_version_touched:   # Claude Code assigns; v1.97 is current
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> On reflechissais aux ''knowledge'' et aux ''relations''. Les relations
> servent a lie n'importe quels entitees entre-elles de differentes facons.
> Par exemples les connecte to , ally.... On pourrais dire que chaque
> relation est une knowledge?. Est-ce que l'on ne pourrais pas dire que
> relations devrais plustot etre un fait a propos des entitees. On pourrait
> mettre une descrition dans fait qui n'est pas lie a un autre entitee. On
> derive les knowledge correspondant sous differentes formes (rumor,
> partial...)

Follow-up answers that shaped the design:

> 1. connects_to peut etre conaissable. J'essaye de m'aider en effectuant
>    cela, entre-autre aider a determiner si un joueur a les connaissance
>    pour se rendre a une place qu'il desir. Je sais que le manoir se
>    connecte au chemin qui se connecte au marche ou je peut vraisemblablement
>    trouver un marchande de fleurs.
> 2. world low pourrait etre que la mage n'existe pas, mais cela fait que je
>    ne cerai pas le lore sur la magie ou de competence magique.
> 3. Un secret partage a trois est un bon exemple de ce que je veux. Meme un
>    secret partage par la faction au complet.

## Clarifications resolved (intake)

The reframing that came out of intake: the structural hole is not on
`relation`, it is on `knowledge`. `Knowledge.subject` is free text
(`models/canon.py:453`) with no foreign key to what is known. That string is
already load-bearing as an identity key in ten call sites and has already
grown an ad-hoc namespace convention (`link_author.py:193` matches on
`f"npc:{other_id}"` — a foreign key encoded in a string). `fact` gives
`knowledge` something structural to point at.

Locked decisions, in the codes Nia returned:

- **A3b** — `knowledge` points at a thin `fact` spine. The spine carries
  `exactly-one-of (relation_id, event_id, world_law_id)` OR all NULL
  (free-standing fact). `situation_id` is reserved for the future
  `situation` table and is NOT created here (no table to reference yet).
  Amendment accepted during intake: **no `entity_id` on the spine** — an
  arity-1 fact is a nu spine with one `fact_participant` row, so there is
  exactly one way to express each arity.
- **B2** — **truth resolves, belief deliberates.** Deliberation readers
  (tick briefing, day-plan proposals) traverse a knowledge-filtered graph;
  resolution readers (`location_reachable`, `relation_gte` in
  `day_resolve.py`) read canon directly. Additive: a new BFS is added, the
  existing truth readers are not rewritten.
- **C2** — `default_level` lives on the fact, not as one `knowledge` row per
  knower. Knowing an edge does not require having travelled it.
- **D1** — typed expectation ("a market probably has merchants") is a
  `location_type_catalog` inference, never a `knowledge` row.
  **Out of this ticket entirely.**
- **E1** — `fact` is the perception layer only. Mechanics keep reading typed
  tables (`relation_gte` already proves the type-plus-threshold pattern,
  `writes/goals_agendas.py:67`). A `world_law` acts as an authoring
  constraint, not a runtime gate — which is already the measured behaviour
  (`region_author.py:236` reads it as prompt input).
- **F2** — hybrid arity: typed spine for facts that ARE an existing row;
  `fact_participant` only when every typed FK is NULL.
- **G2a** — scoped defaults `fact_default(fact_id, scope_type, scope_id,
  level)` over `world | faction | location`; most specific scope wins;
  across multiple active faction memberships the **highest** level on the
  ordered scale wins; a stored `knowledge` row overrides everything.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `models/canon.py` is under the module_budget cap with headroom, and
      `SQLModel.metadata` table set is byte-identical across the pure move
      -> verify/checks/module_budget.py + schema_reconciliation.py
- [ ] No `fact_participant` row exists whose `fact` has any typed FK set
      (vacuous-proof: zero facts collected = FAIL) -> verify/checks/fact_spine.py
- [ ] Every `knowledge` row has a non-NULL `fact_id` after migration; pre/post
      row counts equal -> verify/checks/fact_spine.py
- [ ] `fact.default_level` and `fact_default.level` are constrained to the six
      values in `writes/knowledge.py:34` -> schema CHECK + verify check
- [ ] Level resolution is total: every (entity, fact) pair resolves to exactly
      one level, never None -> verify/checks/knowledge_resolution.py
- [ ] Every `connects_to` relation has exactly one backing fact, and the
      knowledge-filtered BFS returns a set identical to the truth BFS on a
      world where no default has been lowered -> verify/checks/known_reachability.py
- [ ] Every `connects_to` read site is classified resolution or deliberation
      in an explicit table; an unclassified site fails the check
      -> verify/checks/known_reachability.py
- [ ] Corpus gate green; `/review-step` and `/close-step` run on every brief
      that touches engine code

### Live  ->  human gate (Nia)

- [ ] In Creation, adding a knowledge row to an NPC creates or attaches a
      fact, and the row reads back with its participants
- [ ] A secret authored once, with a faction-scoped default, appears in the
      briefing of every active member of that faction without one stored row
      per member; a member who leaves stops resolving it
- [ ] A three-participant secret (three conspirators) is authored as one fact
      with three participants, distinct from who knows it
- [ ] Lowering the default on one `connects_to` fact to `unaware` makes that
      edge disappear from an NPC's deliberation without changing what the
      resolution path considers legal
- [ ] Nothing an NPC says or plans references a place it has no level on

## Named deferrals (verifiable reactivation conditions)

- **E2 — mechanical effect on a fact.** Reactivates when
  `NPC_GOAL_PREREQUISITE_TYPES` (`writes/goals_agendas.py:67`) gains a member
  whose target resolves to a `world_law.id`.
- **Subsumption of `faction.magic_knowledge_level`** (`models/canon_faction.py:31`,
  read at `tick_context.py:543`). It is a hardcoded, faction-scoped default
  knowledge level on a single subject — the ancestor of `fact_default`.
  Reactivates when a `world_law`-backed fact about magic exists AND a
  `fact_default` row with `scope_type = 'faction'` exists: at that point two
  structures mean the same thing.
- **Cutover of `Knowledge.subject`.** Ten identity-key sites survive this
  ticket (enumerated in BRIEF-0082-b). Reactivates immediately on close of
  this ticket — successor ticket required before any new reader is written
  against `subject`.
- **`situation` table.** The spine reserves the slot; the table itself is a
  separate ticket. Reactivates when a durable-background-fact reader is named.
