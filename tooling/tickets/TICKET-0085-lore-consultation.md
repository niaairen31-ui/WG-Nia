---
id: TICKET-0085
slug: lore-consultation
title: Natural-language lore consultation surface (read-only)
type: feature
status: live-gate
created: 2026-09-11
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0085-a, BRIEF-0085-b, BRIEF-0085-c, BRIEF-0085-d, BRIEF-0085-e]
schema_version_touched: none
retry_count: 1
---

## Request (verbatim, as Nia stated it)

> Je pense que je devrais être en mesure de posé des questions au ''lore'' en
> language naturelle et je recois une réponse en prose avec ce qui existe dans
> le lore. Ex : est-ce que tel personne connais tel personne. Qu'est-ce que tel
> personne connais sur tel chose. Éventuellement, je voudrais dire tel personne
> connais tel chose et cela s'ajoute au lore (cela peut passé par des
> mutations)

> je veux pouvoir poser n'importe quel question et avoir une reponse ( des
> questions sur les factions, les lieux, les NPC)

> je veux que même s'il n'y a pas de resultat, on me le dis

> je veux savoir ce que mara crois, mais qui est faux

> On me propose les deux, je choisis lequelle.

## Clarifications resolved (intake)

**Retrieval unit — declarative plan, not an intent catalogue.** The creator asks
anything. The model never writes SQL and never chooses a join: it emits a *plan*
— a list of selectors drawn from a whitelist, with arguments bound to mentions in
the question. Code validates the plan against the whitelist, resolves the
mentions to ids, executes the selectors under bounds, and hands the resulting
rows to the renderer. Coverage grows by adding selectors, never by adding
question types; the pipeline is untouched by each addition.

**Pipeline shape (7 steps).**
1. Question (FR) -> model -> plan draft: mentions (surface form + category) and
   requested selectors with arguments referring to those mentions symbolically.
2. Code resolves mentions -> `entity.id`, world-scoped, named rungs only.
3. Code validates the plan: every selector in the whitelist, every argument
   bound to a resolved mention.
4. Code executes the selectors, bounded row counts.
5. Code detects the empty cases.
6. Rows -> renderer -> prose. Renderer sees the rows and nothing else.
7. Trace returned alongside the prose.

**Selector set for this ticket (two only).** `entity_dossier(entity_id)` and
`world_factions()`. Every other selector — `location_contents`,
`faction_roster`, `region_locations`, `who_knows_about` — is a later ticket.

**"Knows" is answered in one voice, queried in two.** A question about one person
knowing another reads both the social link and the held information, and the
prose names both registers explicitly. The two tables stay distinct in mechanics;
they are never merged.

**Name resolution is a lookup, never the model.** Reuse the *named* rungs of
`day_concordance` (exact and token), world-scoped, extracted into a shared
function. The casting rungs (presence, relation, occupation) are play semantics
and are NOT used here: a creator's question must surface ambiguity, not have it
decided.

**The renderer is a third role.** Not proposing, not judging — rendering. It
receives only the rows the selectors returned, never a DB handle. Empty retrieval
is never filled in.

**Deterministic fallback.** When Ollama is unavailable, a template renderer
answers from the same rows. The surface stays usable with no model.

**False beliefs are rendered as beliefs.** The answer states what the entity
holds to be true and marks explicitly when that row is flagged incorrect. It does
not substitute the world's truth.

**The three empty messages are distinct.**
1. Name does not resolve -> the entity does not exist in this world, plus the
   near candidates the rungs found.
2. Name resolves, selectors return nothing on that point -> the entity exists and
   canon holds nothing on it. Silence of canon, not absence of entity.
3. The plan requires a selector outside the whitelist -> this cannot be queried
   yet. A limit of the tool, not of the world.
The trace accompanies all three.

**Ambiguous mention — the creator disambiguates, the surface never guesses.**
Two entities sharing a name in the active world is not one of the three empty
cases: retrieval succeeded, the referent did not. The surface answers nothing,
presents the candidates with enough detail to tell them apart, and waits for the
choice. When several mentions in one question are ambiguous, all of them are
presented in the same round, not one at a time. On the creator's choice the
question is NOT re-parsed: the plan built in step 1 is reused verbatim with the
mention now bound, so a disambiguation can never shift what was asked.

**The pending plan is client-held.** The plan travels back to the client with the
candidate list; the client echoes the plan plus the chosen bindings. No server
state, no table, no cache — consistent with the trace being displayed and not
persisted.

**Trace is shown, not persisted.** Prose plus a collapsible panel listing the
rows read — table, id, level, resolution rung. No new table in this ticket.

**Scope is always the active world.** `knowledge` carries no `world_id`; world
scoping goes through `entity`, at query construction, never post-fetch.

**Model.** Registered in `prompt_registry` like every other prompt, on the author
model rather than the game model, overridable by env as the others are.

**Read-only.** The assertion path — "this person knows this thing" becoming canon
— is out of scope and belongs to a later ticket.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The named-mention resolver (`lore_resolve.py`) is pure (no `chat(`, no
      `db.add(`/`.commit(`), never casts, `NAMED_RUNGS`/`_NAMED_RUNG_LOOKUPS`
      are in bijection, every `select(` is world-scoped at construction, and
      `_normalize_surface` is not duplicated in `day_concordance.py`
      -> verify/checks/lore_resolve.py
- [ ] Every selector the executor can dispatch is present in the whitelist
      constant, and dispatch happens only through the whitelist mapping
      (one-tuple/one-dict bijection, as `MATCHING_RUNGS`/`_RUNG_LOOKUPS`)
      -> verify/checks/lore_selectors.py
- [ ] A plan naming a selector outside the whitelist is rejected before any DB
      read occurs  -> verify/checks/lore_selectors.py
- [ ] Every selector declares a row cap and the executor enforces it
      -> verify/checks/lore_selectors.py
- [ ] The retrieval modules contain no `chat(` and no `db.add(`/`.commit(`; the
      renderer module contains no `select(`  -> verify/checks/lore_isolation.py
- [ ] Every selector query is world-scoped at construction, not filtered after
      fetch  -> verify/checks/lore_isolation.py
- [ ] An empty retrieval cannot reach the model renderer: the empty branch
      returns before any model call  -> verify/checks/lore_isolation.py
- [ ] `corpus_gate.py` passes  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] Asking whether one named NPC knows another returns prose naming both the
      social link and the held information, or stating the absence of each
- [ ] Asking what an NPC knows about a thing returns the held rows in prose, with
      a row flagged incorrect rendered as a belief and marked false
- [ ] Asking about the world's factions returns them without any entity named in
      the question
- [ ] A name absent from the world returns empty message 1 with near candidates
- [ ] An existing entity with nothing on the asked point returns empty message 2
- [ ] A question requiring an unbuilt selector returns empty message 3
- [ ] A name matching two entities in the active world returns no answer, lists
      the candidates distinguishably, and answers correctly once one is chosen
- [ ] The trace panel lists the rows read for each of the above
- [ ] With Ollama stopped, the same questions still answer via the template
      renderer
- [ ] `/review-step` and `/close-step` run clean on every commit touching engine
      code
