# BRIEF-0082-d — AMENDMENT 1: public-floor reader and D1 conformance

**Amends:** `tooling/briefs/BRIEF-0082-d-known-reachability-graph.md` — the
Mini-RECON's caller record, Scope IN items 1, 3 and 4, and Scope OUT's
`location_known` bullet.
**Date:** 2026-09-02
**Trigger:** Claude Code escalation under this brief's STOP condition ("If the
classification of any site is genuinely ambiguous ... stop and escalate. Do
not pick.").
**Author:** Claude (design), owning the error.
**Status of the original:** unchanged on disk. This artifact supersedes three
Scope IN items and adds one escalation the original did not anticipate.
**Decisions locked by Nia before authoring:** H3 (fifth label `public`), I1
(one floor constant, shared).

## The escalation was correct

The brief's Mini-RECON recorded one caller of `_reachable_locations`:

> Called at `tick_context.py:489`; the result reaches the NPC through
> `assemble_tick_context`.

There are two. Measured 2026-09-02 on `main` @ v1.99:

1. `tick.py:69` — the per-NPC tick briefing. A single `entity_id` governs.
2. `tick_context.py:494`, inside `assemble_location_event_context` — the
   `LES ENVIRONS` section of the location-scope event briefing, consumed by
   `_tick_run_scope_events` (`tick.py:409`) via `_tick_call_scope_model`
   (`tick.py:307`). No single character governs.

Claude Code stopped rather than assigning a label. That is the STOP protocol
working as intended and is treated as correct behaviour, not a failure.

## What the corrected RECON shows

`assemble_location_event_context` is **already not omniscient**. Two of its
four sections carry a perception filter:

- `tick_context.py:477` — `LocationSubculture.is_hidden == False`, the same
  creator-only exclusion as `room_batch_author.py:103` and
  `tick_context.py:321`.
- `tick_context.py:505` — `Event.knowledge_status.in_(("public","confirmed"))`,
  excluding secret and rumoured events.

`LES ENVIRONS` (line 494) is the only section in that function reading raw
canon. It is not a principled omniscient reader; it is a public-view
assembler whose topology section was never filtered, because before the fact
spine there was no way to filter it. Leaving it unfiltered would make the
graph the one thing in that prompt that ignores the discipline the same
function applies twice over.

The filter it needs is not a character's belief. It is the **public floor**,
which the G2a ladder already expresses: tiers 4 and 5 of
`knowledge_resolve._resolve_tiers` — `fact_default` at `scope_type='world'`,
falling through to `fact.default_level`, with tiers 1 through 3 skipped
because they require an entity.

## Corrected instruction — Scope IN item 1 (classification labels)

The four-label vocabulary gains a fifth. Full corrected list, verbatim:

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

`tick_context.py:494` is classified `public`. `tick.py:69` stays
`deliberation`. The fifth label exists to make one specific error detectable
rather than to describe the world more finely: with both sites labelled
`deliberation`, nothing would stop a future reader from passing an
`entity_id` to the location assembler, which would silently make a location's
ambient events depend on one arbitrary character. The label earns its place
because a check can assert against it.

## Corrected instruction — Scope IN item 3 (D1 conformance)

The original item 3 instructed a new module `knowledge_reach.py` holding
`known_reachable_locations`, and item 4 repointed both `tick_context.py:433`
and `day_plan.py:228` at it. **That instructs a D1 violation**, the same
family of error as BRIEF-0075-b AMENDMENT 1: decision D1 (BRIEF-19) is that
each `connects_to` consumer holds its OWN traversal, and a dedup opportunity
is REPORTED, never acted on. One shared traversal serving both the tick and
the day chain is exactly what D1 forbids, and `_day_reachable_ids` was
authored under that amendment precisely to avoid it.

Two axes are in play here and the original brief collapsed them:

- **Traversal is governed by D1** — independent readers per consumer, never
  shared.
- **Resolution is governed by the single-authority rule** (BRIEF-0082-c) —
  `resolve_knowledge_level` is the ONE place the ladder is applied, and every
  traversal must call it rather than reimplement a comparison.

Sharing the resolution authority is required. Sharing the traversal is
forbidden. Corrected instruction:

- **Do NOT create `src/world_engine/knowledge_reach.py`.** No new module, no
  new BFS.
- Add the filter **inside `_reachable_locations`** (`tick_context.py:410`),
  which stays the tick-local reader it is documented to be. Signature becomes
  `_reachable_locations(session, origin_location_id, interval_label, *, knower_id: Optional[str])`.
  `knower_id` is keyword-only so no call site can pass it positionally by
  accident.
- `tick.py:69`'s path passes the NPC's `entity_id`. `tick_context.py:494`
  passes `knower_id=None`.
- When `knower_id` is None, the edge test calls
  `knowledge_resolve._resolve_tiers` with `stored_level=None`,
  `location_chain=[]`, `faction_ids=[]`, and the fact's `default_level` as
  `fallback_level`. **Not a parallel omniscient branch, not a second
  function** — the same authority entered at its world tier.
- Expose that entry as `resolve_public_level(db, fact_id) -> str` in
  `knowledge_resolve.py`, alongside a batch companion in the shape of
  `resolve_levels_for_entity`. `_reachable_locations` calls one of the two
  batch helpers depending on `knower_id`, then does membership tests — it
  never indexes `KNOWLEDGE_LEVEL_LADDER` itself.
- **`day_plan.py`'s `_day_reachable_ids` (line ~218) is NOT repointed and
  NOT filtered by this brief.** See the escalation below for why that is not
  a deferral of convenience.

## Corrected instruction — Scope IN item 3 (floor constant, I1)

One constant, one home: `KNOWN_EDGE_FLOOR = "partial"` in
`knowledge_resolve.py`, imported by `tick_context.py`. Both the
`deliberation` and the `public` path compare against it. The floor is
resolution policy, not traversal shape, so it does not fall under D1 and must
not be duplicated per reader. The module docstring states, verbatim:

```
# `partial` is the floor at which an edge becomes traversable: the first
# level on the ladder at which the knower can be said to know where the way
# goes. One constant, shared by the character path and the public path — a
# second floor would drift.
```

Fail-closed is unchanged: a `connects_to` relation with no backing fact is
not traversable on either path, and is recorded in the diagnostic list.

## Check change

Scope IN item 6's three assertions stand. Two changes:

- Assertion 2 now requires one of **five** labels, not four. An unclassified
  site is still a FAIL.
- **Add a fourth assertion, AST-based**: no call site classified `public`
  passes a non-None `knower_id`, and no call site classified `deliberation`
  passes `knower_id=None`. Vacuous-proof: zero classified call sites found is
  a FAILURE, not a pass. This is the assertion that makes the fifth label
  worth its existence; without it, H3 is a comment.
- **Add a fifth named mutation** to item 6's golden case, alongside the two
  already there: flipping `tick_context.py:494` to pass an `entity_id` must
  make the check FAIL.
- **Do NOT** author any check asserting that `tick_context.py` and
  `day_plan.py` share a traversal. Such a check would encode the superseded
  instruction.

## Escalation — the player has no deliberation stage

This is not a finding the original brief anticipated, and it must be read
before this step is considered to close TICKET-0082's stated purpose.

B2's safety argument is a composition: deliberation narrows, resolution
verifies, so a route a character never proposes never reaches resolution.
That composition holds for an NPC, which has a briefing. **It does not hold
for the player**, who declares a day in free natural language with no
deliberation stage in between. For the player, the only place to catch "you
do not know that route" is the resolution path — `location_reachable`, fed by
`_day_reachable_ids`.

Filtering that path would be a perception-layer fact producing a mechanical
verdict, which is **E2**, explicitly deferred by TICKET-0082, and named in
this brief's own Scope OUT ("Do not add a `location_known` requirement type —
that would be a mechanical effect on the perception layer, which is E2 and
deferred").

The consequence to state plainly: **TICKET-0082 delivers knowledge-gated
reachability for NPCs and for location-scope generation, and does NOT deliver
it for the player.** Nia's originally stated use case — "aider a determiner
si un joueur a les connaissances pour se rendre a une place qu'il desir" — is
not satisfied by this ticket. E2's reactivation condition is now satisfiable
and the successor ticket is the place for it.

Do not implement it here. Do not widen this brief. Report the gap in the
execution notes and stop.

## Report only

1. **The dedup opportunity**, as D1 requires: state the current
   `connects_to` reader count and leave it.
2. **`tick_context.py:410-413`'s docstring** still claims it is "the third
   reader" of `connects_to` as of RECON-0015 F3. Twelve modules read it.
   Correcting that docstring is in the original brief's Docs section; note
   that the count will go stale again and that the classification table, not
   a number, is the durable anchor.
3. **`_reachable_locations` now has two call sites with different filter
   semantics.** Whether that makes it one consumer or two under D1 is a
   genuine question the doctrine does not settle. It is treated here as one
   tick-local consumer with two call sites, which is how the function has
   always been documented. Record the reading; do not act on it.

## Unaffected

Every other decision in BRIEF-0082-d stands: the classification table as the
durable artifact (item 1), the `connects_to` fact migration at
`default_level = 'knows'` and its behaviour-preserving property (item 2), the
fail-closed missing-fact rule, the diagnostic surface (item 5), the
`_BLOCKED_DETAIL_FR` prohibition, the ban on unifying the two BFS
implementations — reinforced, not weakened, by this amendment — the ban on
lowering any default in a seed, and the whole of Scope OUT. The live gate is
unchanged except that the before/after tick comparison must now be run for
both an NPC briefing and a location-scope event briefing.
