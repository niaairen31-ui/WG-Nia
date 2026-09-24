# AMENDMENT-0091-04 — R-24 reader list incomplete; knowledge merge moves into writes/

Ticket: TICKET-0091   Lot: LOT-0091-lore-as-facts.md   Brief in flight: J
(stopped at Mini-RECON, nothing modified)
Decided by Nia (2026-09-22): option (b) for `link_author.py:814`.

## What deviated

R-24 enumerated `.content` readers by filtering receiver names. That is a
negative claim resting on an incomplete enumeration, the same defect class
as AMENDMENT-0091-02. The executor, whose findings are reported and not
re-measured by the lot (the `ticket/0091` branch was not fetchable), found:

- **Missed readers.**
  - `cockpit/crud/facets.py:53` (`_fact_dict`, a module added by E).
  - `context.py:678` (the PC knowledge list).
  - `link_author.py:162` (the "already knows" lines of the link-agent
    prompt).
  - `link_author.py:814` (`_apply_canon_knowledge_patch`: reads the content,
    merges a patch, writes back through `write_knowledge`).
- **False positive.** `scene_format.py:71,76` reads `discoverable_detail`,
  not `Knowledge`, so it is out of scope.
- **Drift.** The anchors shifted after E, G, H and I:
  - `knowledge_resolve.py:358-359`
  - `context.py:124`
  - `lore_selectors.py:183,263`
  - `writes/facts.py:110,116,147,153`
  - `writes/relations.py:374`
  - `_endpoint_names` at `:124` and `_birth_typed_fact` at `:134`
  
  These three still hold: `relation_orientation.py:33-35`,
  `lore_resolve.py:42,112` and `checks/relation_orientation.py:156`.

## Decision on `link_author.py:814`

Option (b) is chosen. The read-merge-write lines move, **unchanged in
logic**, into a new chokepoint `writes/knowledge.py::apply_knowledge_patch`,
which reads `content_raw`. `link_author.py` calls it and never touches raw
content. `identity_tokens.py` R1 is unchanged, so `writes/` remains the only
place that reads raw text.

Rejected alternatives:
- (a) Render, then re-tokenize. This loses a token when a name has become
  ambiguous since it was written. Reactivation: none.
- (c) Allow-list `link_author.py`. This widens the raw-text perimeter to an
  agent module. Reactivation: a second writer outside `writes/` that
  cannot be moved.

## Amended BRIEF-0091-J (regenerated)

- **Anchors.** Restated at the drifted lines, with the drift rule (same
  content shifted = drift, different content = STOP).
- **Scope IN item 3.**
  - It opens with a complete AST enumeration of every `.content` attribute in
    `src/world_engine/`, outside `models/`, classified Fact, Knowledge or
    other and pasted into the report **before any edit**.
  - The three missed readers are named.
  - `scene_format.py` is untouched.
- **Scope IN item 3b.** `apply_knowledge_patch`.
- **ADAPT.** A further Fact/Knowledge reader found by the enumeration is
  routed through the render and reported.
- **STOP.** Any other module outside `writes/` that needs raw text to write
  it back.

## Gate checks re-run

- (a) R-24 carries a correction line; its property trace now rests on the
  executor's AST enumeration, which item 3 requires to be pasted.
- (e) `identity_tokens.py` R1 is satisfied: `apply_knowledge_patch` lives
  in `writes/knowledge.py`.

## Downstream briefs

J (regenerated). K does not read fact or knowledge text directly beyond
C-16, which already goes through C-03, `write_knowledge` and the render.
