---
id: TICKET-0082
title: Fact spine — structural anchor for knowledge
type: feature
status: live-gate
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

## Escalations

### E-01 — archived — QUESTION-TICKET-0082.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0082.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0082
Trigger: D1-c
## Context

`/brief-exec 0082-c` (BRIEF-0082-c, "Scoped knowledge defaults and level
resolution") Scope IN item 1 mandates a new table, `fact_default`, in
`src/world_engine/models/canon_knowledge.py` — a schema-touching change.
Before writing any code, I checked the current schema-version headroom,
per CLAUDE.md's "Numbering & decisions governance":

> Schema versions are computed, never chosen: on any schema-touching step
> closure, new version = the `Current schema version:` line in
> `world-engine-schema.md`, minor + 1. [...] If the minor part reaches 99,
> stop and escalate (D1-c).

Measured, on `ticket/0082` at the current HEAD:

[M] `world-engine-schema.md:3` — `Current schema version: v1.98`
[M] `src/world_engine/schema_version.py:15` —
    `EXPECTED_STATIC_SCHEMA_VERSION: str = "v1.98"`
[M] `world-engine-schema-changelog.md:16` — the latest entry is
    `**v1.98** — TICKET-0082, BRIEF-0082-b: the fact spine, ...` — confirming
    BRIEF-0082-b is what consumed v1.97 -> v1.98 (TICKET-0082's own
    front-matter recorded v1.97 as current at ticket-creation time,
    `schema_version_touched:` comment).

Computed next version for this step, per the rule above: v1.98 minor + 1 =
**v1.99** — which is exactly the threshold the rule names. I have not
written any code for BRIEF-0082-c yet; I stopped at this measurement before
touching `models/canon_knowledge.py`, per `/brief-exec`'s own instruction
("If you find yourself needing a decision the brief did not settle (D1),
STOP and report — do not guess").

The rule's wording is ambiguous on exactly one point I cannot resolve
myself: whether "reaches 99" means the computed new version landing AT 99
is itself the trigger (my reading, and what fires here), or whether it
means only a rollover PAST 99 (i.e. a hypothetical v1.100, which stays
inside a clean two-digit minor only up to 99) should trigger it. Under the
second reading v1.99 would be an ordinary, un-escalated bump and this
question would not exist. I am not guessing which reading governs.

Nothing else about BRIEF-0082-c is unresolved — the mini-RECON, the
resolution-precedence design (G2a), and the scope are all fully specified.
This is purely the version-number governance question.

## Question

How should TICKET-0082's schema version be assigned for BRIEF-0082-c (and,
if relevant, for the remaining BRIEF-0082-d)?

## Options

A. Treat "reaches 99" as met by landing AT v1.99. Assign v1.99 to this
   step's schema change now, and treat this QUESTION as the required
   escalation-and-confirmation gate the rule intends — i.e. once answered,
   v1.99 is cleared to write, and the NEXT schema-touching change after
   this ticket (BRIEF-0082-d, or whatever comes after) is what actually
   needs the v2/v1.100 convention decided, in its own escalation. This is
   what I'd do absent other direction — it matches the literal wording
   most directly and defers the harder "what comes after 99" decision to
   when it is actually needed.

B. Decide the post-99 convention right now and assign THAT to this step
   instead of v1.99 (e.g. jump straight to `v2.0`, or allow a three-digit
   minor `v1.99` -> `v1.100`). Avoids a second escalation later but commits
   to a versioning-scheme decision ahead of when this ticket strictly
   requires it.

C. Hold BRIEF-0082-c's schema change (the `fact_default` table) out of this
   ticket entirely — implement the non-schema-touching parts nowhere in
   this brief since the table IS the Scope IN centerpiece, so in practice
   this means deferring the whole brief to a follow-up ticket, opened only
   once the version convention is settled. Slowest option; likely
   unnecessary given the ticket is already mid-flight with brief_ids
   `[..., BRIEF-0082-c, BRIEF-0082-d]` committed.

D. Something else Nia specifies.

## Response

### Resolution

Decision on QUESTION-TICKET-0082 — resolved. Stopping here was correct;
the literal reading of the 99 threshold is also correct.

VERDICT: option B, with the convention specified below. Option A is
rejected for a reason not in the write-up above: assigning v1.99 while
leaving the escalate-at-99 rule in place leaves the tripwire permanently
fired. Every later schema-touching step would re-trigger this same stop
with no defined resolution. Option C is rejected as disproportionate — the
numbering convention is orthogonal to the fact-default chantier.

1. This step's schema version is v1.99. Proceed with it.

2. Numbering convention, effective now. The existing schema version
   numbering clause in CLAUDE.md is replaced with:

   Schema version: `vMAJOR.MINOR`, MINOR two digits, 00-99. Next version:
   MINOR < 99  ->  `vMAJOR.(MINOR+1)` zero-padded; MINOR = 99  ->
   `v(MAJOR+1).00`. MAJOR counts MINOR overflows and carries no semantic
   meaning. Published changelog versions are never renumbered.

   This is a total function with no escalation branch — that is the point.
   The "stop and escalate (D1-c)" sentence is not preserved alongside it.

3. Sequencing. The CLAUDE.md edit and this appended section go in one
   commit of their own, before BRIEF-0082-c implementation resumes.
   Append only — the committed Options section above is not rewritten.

4. STOP conditions honored: the CLAUDE.md contract check (character
   budget, per-line ceiling) must pass after the edit without trimming the
   replacement text to fit; if the surrounding text made a clean splice
   impossible, that was to be reported rather than improvised.

5. REPORT ONLY, no fix: grep the tree for hardcoded `v1.` version
   assumptions (regexes like `v1\.\d{2}`, string literals, boot guards).
   Nothing there blocks v1.99 — the shape is unchanged — but it is the
   breakage surface for the v2.00 roll. Findings feed a separate ticket,
   not this one.

6. Scope OUT / named deferral: no verify check enforcing the version
   format or the increment rule in this ticket. That rule is currently
   disciplinary — it held this time because CLAUDE.md was read and
   complied with, not by construction. Reactivation condition: a
   schema_version_format check ticket is opened before the next
   schema-touching ticket enters exec.

Everything else in BRIEF-0082-c stands unchanged. Resume after the
convention commit.

---

# QUESTION 2 — TICKET-0082 (BRIEF-0082-d)
Trigger: D1-c
## Context

`/brief-exec 0082-d` (BRIEF-0082-d, "Known-reachability graph for
deliberation"). Before writing the classification table (Scope IN item 1),
I re-verified the mini-RECON's twelve-module `connects_to` reader count —
confirmed still accurate, no thirteenth site. `relation_graph.py` and
`graph_primitive.py` checked for conflict — none (different concern, the
social relation graph exclusion).

`tick_context._reachable_locations` — the function the brief names for
conversion to a knowledge-filtered `known_reachable_locations` (item 3,
"expected to be tick_context.py:433 ... via a knower-aware variant") — has
**two callers**, and the mini-RECON's enumeration recorded only one:

1. `tick.py:69` — feeds an NPC's own tick briefing (`destinations` in
   `assemble_tick_context`). Unambiguously **deliberation**: a specific
   `entity_id` exists to resolve knowledge against.
2. `tick_context.py:494`, inside `assemble_location_event_context` — feeds
   a location-scope event briefing ("LES ENVIRONS"), consumed by
   `_tick_run_scope_events` -> `_tick_call_scope_model` (`tick.py:412-417`).
   This caller has no single character whose knowledge would govern the
   filter — it is an omniscient, location-scoped generator proposing
   ambient events, not a character's belief.

None of the four classification labels (`resolution`, `deliberation`,
`authoring`, `vocabulary`) cleanly fits caller 2: it is not a legality
check, it does not build/write the graph, it is not a vocabulary literal,
and B2's "deliberation" is explicitly defined as *a character's* belief —
there is no character here. Per the brief's own STOP condition ("If the
classification of any site is genuinely ambiguous ... stop and escalate.
Do not pick. That ambiguity is a design question about where deliberation
ends, and it belongs to Nia."), I stopped before item 1's table and before
any code.

I raised this in-session (not async) and Nia's instruction was: open a PR
now with the work already completed on this ticket (BRIEF-0082-a,
BRIEF-0082-b, BRIEF-0082-c — all committed, verified PASS on
`module_budget.py`, `fact_spine.py`, `knowledge_resolution.py`), and she
will return with the classification answer separately. BRIEF-0082-d is
therefore NOT executed this session; `known_reachability.py` remains
MISSING and the ticket's verify result stays red on that one check.

## Question

How should `assemble_location_event_context`'s call to
`_reachable_locations` (the location-scope event briefing) be classified,
and should its call site be repointed to a knowledge-filtered reader?

## Options

A. `authoring` — leave it unfiltered. Treat it like region/room-batch
   generation: engine-internal content proposal, reads canon truth
   directly. Behaviour stays exactly as today (the safety property BRIEF-d
   asks for). `known_reachable_locations` is wired ONLY at `tick.py:69`
   (the NPC-destinations call).

B. Knowledge-filtered by the scope's own resolved defaults — stretch G2a's
   per-entity resolution into a per-location aggregate (e.g. highest
   default among entities present). No precedent in the locked design;
   likely out of this ticket's scope as decided.

C. Defer entirely — don't build `known_reachable_locations` for
   `tick_context.py` at all this ticket; wire `day_plan.py` only, and
   revisit the NPC-destinations (`tick.py:69`) and scope-event callers
   together in a follow-up once this question is settled.

D. Something else Nia specifies.

## Response

### Resolution

Answered by `tooling/briefs/BRIEF-0082-d-amendment-1-public-floor-reader.md`
(2026-09-02). Verdict: option A's shape (leave `tick_context.py:494`
unfiltered by any single character) was right in spirit, but the correct
label is a new fifth one, `public`, not `authoring` — the site is filtered
by the **public floor** (the resolution ladder entered at its world tier,
no entity), not left raw. `tick.py:69` stays `deliberation`.

Also corrects a second error the amendment caught: the original brief's
item 3/4 (a new shared `knowledge_reach.py` module used by both
`tick_context.py` and `day_plan.py`) would have violated D1 (BRIEF-19) —
each `connects_to` consumer keeps its own traversal. The filter goes
inside `_reachable_locations` itself via a keyword-only `knower_id`
parameter; no new module. `day_plan.py`'s `_day_reachable_ids` is NOT
touched by this brief.

Full corrected instructions in the amendment. Resuming BRIEF-0082-d
execution per the amendment.
~~~~
