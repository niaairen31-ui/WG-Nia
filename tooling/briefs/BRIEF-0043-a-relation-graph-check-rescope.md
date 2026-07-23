# BRIEF — Step "Rescope relation_graph.py's stale detections"

## Context
While closing TICKET-0041, two of `relation_graph.py`'s four assertions broke
for reasons unrelated to that ticket. (1) `_RELATION_GRAPH_EXCLUDED_TYPES` now
lives in `context.py:108` and is imported with an alias into
`crud/relations.py:18`, so the check's literal-tuple regex no longer matches.
(2) The check's relGraph* JS section detection is a slice between two comment
anchors (`"cytoscape, display-only, on-demand"` .. `"Generic modal
(BRIEF-41)"`) that has, since TICKET-0041 or earlier, come to also contain
~20 `npcAgent*` and ~16 `linkAgent*` functions unrelated to the relation
graph — their POST/PUT/DELETE fetches get misattributed as relGraph*
violations. Both invariants the check protects still hold; only the detection
mechanics are stale.

## Scope IN
1. In `tooling/verify/checks/relation_graph.py`, the constant-detection step
   (currently `re.search(r"_RELATION_GRAPH_EXCLUDED_TYPES\s*=\s*\(([^)]*)\)",
   crud_src)`): extend detection to also recognize an import of
   `RELATION_GRAPH_EXCLUDED_TYPES` from `...context` (aliased or not) in
   `crud/relations.py`. When the constant is imported rather than defined
   locally, resolve and validate its actual tuple contents by reading
   `src/world_engine/context.py` (must contain both `"connects_to"` and
   `"controls"`) instead of failing outright.
2. In the same file, the write-confinement scan (currently
   `section_m = re.search(r"cytoscape, display-only, on-demand.*?(?=Generic
   modal \(BRIEF-41\))", html_src, re.S)`): replace the comment-anchored slice
   with a function-name-based collection — gather every function in
   `index.html` whose name matches `relGraph\w+` (reuse the existing
   `_braced_function` helper per match) and run the existing POST/PUT/DELETE
   confinement scan (total vs. confined to `relGraphSaveEdgePanel` /
   `relGraphDeleteEdge`) only across the concatenation of those collected
   function bodies. Do not change the confinement logic itself — only the
   input text it scans.
3. Leave part 1 (vendor file + `/vendor/{filename}` route) and part 5 (Lieux
   graph byte-identical to `main`) untouched.
4. Update the module docstring's item 4 to describe the function-name-based
   scan instead of the comment-anchored slice.

## Scope OUT
- No change to `crud/relations.py`, `context.py`, or any product code — this
  is verify-tooling only.
- No change to which JS functions are sanctioned writers
  (`relGraphSaveEdgePanel` / `relGraphDeleteEdge` stay the only two).
- Do not touch parts 1 or 5 of the check.
- Do not add a new anchor comment to `index.html` — function-name collection
  is the chosen approach specifically so the check no longer depends on
  comment placement at all.

## Invariants to defend
- The ego and global relation-graph endpoints must stay read-only and
  structurally exclude `connects_to`/`controls` — relocating where the check
  looks must not weaken what it asserts.
- Fail-closed: if zero `relGraph\w+` functions are found at all, that is a
  failure, not a vacuous pass — mirror the existing
  `if not body: failures.append(...)` pattern already used for the two
  sanctioned writers.

## Done means
- [ ] `python tooling/verify/checks/relation_graph.py` exits 0 on current
      `main`.
- [ ] Manually confirm, then revert before commit: moving
      `_RELATION_GRAPH_EXCLUDED_TYPES` back to a local tuple literal still
      passes; a stray POST fetch added inside a non-relGraph function that
      sits between the old comment anchors does NOT cause a failure; a stray
      POST fetch added inside an actual `relGraph\w+` function DOES cause a
      failure.
- [ ] `/review-step` run on this brief's diff is clean (touches only
      `tooling/verify/checks/relation_graph.py`).

## Docs to update
- This step IS the doc update (docstring only) — no schema change, no
  `ARCHITECTURE_DECISIONS.md` entry (no design decision changes, only
  verify-tooling catching up to already-shipped code).
