# BRIEF 0090-E — "link agent"

Lot: LOT-0090-oriented-relations.md (authoritative on conflict)
Depends on: BRIEF-0090-A (C-07). Placed after D **by a locked decision**,
not by a dependency: the creator surfaces are proven by hand before the
agent writes through the new path.

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `writes/relations.py` exports `write_oriented_relations` accepting
  `mode="set"` and `relation_id=None` as keys (brief A, C-07).
- `link_author.py:71` — `_LINK_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")`.
- `link_author.py:296-320` — `_build_relation_row` builds the staged payload
  `{"mode": "set", "relation_id": None, "world_id", "entity_a_id",
  "entity_b_id", "type", "value", "direction", "visible_to_b", "notes"}`.
- `link_author.py:942` — the commit loop calls
  `write_relation(db, **row.payload)`.
- `link_author.py:646` — `_CANON_RELATION_WHITELIST = {"intensity", "notes",
  "type", "direction", "visible_to_b"}`.
- `link_author.py:830-843` — `_apply_canon_relation_patch` merges the patch
  and writes through `write_relation`.
- `link_author.py:243` and `:561` — pair exclusion skips a pair already
  holding a relation in either direction.
- `creation/LinkAgent.svelte:137-151` — the staged relation row: a direction
  select with the three raw values and a "visible à B" checkbox.
- `checks/link_agent_strata.py:20-28` — `link_author.py` and
  `routes/link_agent.py` may contain no direct `db.add(Relation(...))` and
  no raw SQL touching `relation`/`knowledge`; commit and patch must route
  through `write_relation`/`write_knowledge`.
- `link_author.py` is 955 lines; `module_budget.py:58` caps it at 1000.

## Facts carried

**R-08** — the staged relation payload is exactly `write_relation`'s
kwargs; commit calls `write_relation(db, **row.payload)` (`:942`); the
coherence whitelist includes `direction` and `visible_to_b` (`:646`); pair
exclusion skips any pair holding a relation in either direction (`:243`,
`:561`); `link_agent_strata.py` forbids a bespoke write site here.

**R-12** — `visible_to_b` defaults TRUE in all three writers, including
`link_author.py:318`, and no play assembler reads it.

**R-19** — the link agent's prompt asks the model to prefer "a relation one
side hides" (`seed_pilot.py:1664`), and the staged checkbox is editable
before commit (`LinkAgent.svelte:150-151`). On directed rows the value is a
reviewed decision.

**R-20** — on a `b_to_a` row, "visible à B" names the side that already
feels; no code fixes the meaning. The migration reported those rows rather
than converting them (U3).

**R-18** — `link_author.py` has 45 lines of budget left; nothing new of
substance lands in it.

## Contracts

Consumed verbatim from the lot header:

### C-04 — `orient_legacy`
| direction | visible_to_b | returns |
|---|---|---|
| `a_to_b` | True | `[(a, b, True, False)]` |
| `a_to_b` | False | `[(a, b, False, False)]` |
| `b_to_a` | True | `[(b, a, False, True)]` |
| `b_to_a` | False | `[(b, a, False, False)]` |
| `mutual` | either | `[(a, b, False, False), (b, a, False, False)]` |
| anything else | any | `ValueError` naming the value |

### C-07 — `write_oriented_relations`
```
write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type,
                         value, direction, visible_to_b=False, notes=None,
                         changed_by, mode="set", relation_id=None) -> list[Relation]
```
Normalizes with C-04, one `write_relation(mode="set", direction="a_to_b")`
per spec in order, then `set_target_knows` for each spec whose
`target_knows` is True. `mode != "set"` or `relation_id is not None` ->
`ValueError`. `visibility_ambiguous` is ignored here.

## Context

The agent still proposes `mutual` and `b_to_a` links and still patches
`direction` on canon rows, which `write_relation` now refuses for a social
relation. The prompt and the staged vocabulary stay exactly as they are —
the model keeps proposing in the three-value language it was taught, and the
normalization happens once, at commit.

## Scope IN

1. `link_author.py` commit loop (`:930-946`): replace
   `write_relation(db, **row.payload)` with
   `write_oriented_relations(db, **row.payload, changed_by="link_agent")`
   (or the `changed_by` value already used there, if any). Import
   `write_oriented_relations` beside the existing `write_relation` import;
   keep `write_relation` imported for the canon patch path.
2. `link_author.py:646`: `_CANON_RELATION_WHITELIST` becomes
   `{"intensity", "notes", "type"}`. A coherence patch naming `direction`
   or `visible_to_b` is then refused by the existing "not a patchable
   relation field" branch (`:678`); leave that branch alone.
3. `link_author.py`: delete the now-dead `direction` and `visible_to_b`
   branches of `_coerce_patch_value` for the `canon_relation` domain ONLY if
   they are unreachable for the staged domain too; the staged domain still
   patches `direction` from the review screen, so keep them. Add a one-line
   comment above `_CANON_RELATION_WHITELIST` saying why canon direction is
   no longer patchable (TICKET-0090: a social row is always `a_to_b`).
4. `creation/LinkAgent.svelte:137-151`, staged relation row:
   - Keep the payload vocabulary (`mutual`, `a_to_b`, `b_to_a`) — the
     staging stratum is unchanged.
   - Relabel the select options with the pair's names:
     `{npcName(aId)} ressent` for `a_to_b`, `{npcName(bId)} ressent` for
     `b_to_a`, `Réciproque (deux relations)` for `mutual`.
   - Relabel the checkbox `{npcName(bId)} le sait`, and show it only when
     the row's `direction` is `a_to_b` — it is the only shape where the
     value has a defined meaning (R-20) and the only one commit converts.
5. Rebuild the frontend bundle and commit the build output.
6. Update `link_author.py`'s module docstring: the commit path normalizes a
   staged link into oriented rows through `write_oriented_relations`, and
   `visible_to_b` on an `a_to_b` row becomes the target's knowledge row.

## Scope OUT

- The prompt templates (`npc_link_pair`, `npc_link_coherence`) and anything
  in the prompts registry — the model keeps proposing in three directions.
- `_build_relation_row`'s validation and the staged payload shape.
- Pair exclusion (`:243`, `:561`): it stays "either direction". A pair that
  already holds A->B is still skipped even though B->A is now expressible.
- `link_context.py` and its `visible_to_b` serialization.
- Any backend file outside `link_author.py`.
- Any other frontend file (brief D owns `RelationsEditor.svelte` and the
  graph consumer).
- The `knowledge` staged rows and their `npc:` subject stamp.

## Invariants to defend

- **The link stratum is ephemeral and never canon** — `link_batch` /
  `link_batch_row` stay out of `writes/` and out of
  `canon_write_policy.txt` (`link_agent_strata.py` rule 1).
- **The commit and patch paths route through the chokepoints** — no
  `db.add(Relation(...))`, no raw SQL, in `link_author.py` or
  `routes/link_agent.py` (rule 4).
- **D3: the staged knowledge subject is code-stamped** — untouched here
  (rule 3).
- **`connects_to`/`controls` are outside the agent's vocabulary** — the
  asserts at `link_author.py:68-69` stay.

## Decision rights

STOP:
- Any anchor above has moved.
- `write_oriented_relations` cannot take `**row.payload` unchanged — the
  contract says it must; a mismatch means A and E disagree.
- The coherence pass has a second path that writes `direction` to a canon
  relation, outside `_apply_canon_relation_patch`.

ADAPT (do it, then report):
- `link_author.py` crosses 1000 lines: move the commit loop's body into a
  private helper in the same file, or, if that is not enough, into
  `link_context.py`'s module family, and report which.
- The commit loop's `changed_by` value differs from `"link_agent"`: keep the
  existing value.
- A staged row with `direction="b_to_a"` and `visible_to_b=True` reaches
  commit from an older batch: commit it as two facts of the case table
  (relation written, no knowledge row) and report the row id.
- `LinkAgent.svelte` has no `npcName` helper in scope for the checkbox
  label: use the existing group header's names.

REPORT-ONLY:
- Batches staged before this brief that still carry `mutual` rows.
- Any coherence finding that would have patched `direction` and is now
  refused.
- The prompt still asking for `visible_to_b` on every direction.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Committing a staged batch holding one `mutual`, one `a_to_b` with
      `visible_to_b` true and one `b_to_a` row produces: two rows for the
      `mutual` pair with no knowledge row, one row plus one knowledge row
      for the `a_to_b` pair, one row (endpoints swapped) with no knowledge
      row for the `b_to_a` pair.
- [ ] Every relation written by that commit has `direction = 'a_to_b'` and
      exactly one typed fact.
- [ ] A coherence patch naming `direction` is refused with the existing
      "not a patchable relation field" reason, and one naming `intensity`
      still applies.
- [ ] The review screen shows `X ressent` / `Y ressent` / `Réciproque`, and
      the knows checkbox appears only on an `a_to_b` row.
- [ ] `python tooling/verify/checks/link_agent_strata.py`,
      `relation_orientation.py`, `module_budget.py`,
      `frontend_build_fresh.py`, `static_asset_freshness.py` and
      `corpus_gate.py` print PASS.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `link_author.py` module docstring (Scope IN 6).
- The comment above `_CANON_RELATION_WHITELIST` (Scope IN 3).
- No schema or decisions-index change in this brief.
