# BRIEF — Step "doctrine and docs: one graph, structurally"

## Context

The primitive exists, three consumers use it, the lock holds. This step
writes it down once, describing the finished shape rather than the journey
- which is why -b, -c and -d each deliberately updated no documentation.

Three things must be recorded that are NOT visible in the diff: the third
implementation RECON found and the workstream map missed; the fail-open
guard F fixed; and the named deferral D1, so that `graph_spec_for` on the
trait registry is a decision that was taken, not a thing nobody thought of.

## Scope IN

1. **`CLAUDE.md` - three amendments, all in the frontend law section.**

   (a) `CLAUDE.md:59` currently lists the review component's twelve
   generics. `reviewGraphRender` is no longer one of them. Amend that
   sentence so the enumeration is accurate, and add, in the same sentence's
   register (law, not rationale): the review component no longer knows how
   a graph is drawn - it declares a `graph` spec and the primitive renders
   it.

   (b) Add the graph law, adjacent to the review-component law, in the same
   compressed style. It must state, at minimum: there is ONE graph
   component (`frontend/src/graph/Graph.svelte`); it never fetches and
   never writes, reporting interactions through callbacks whose presence IS
   the capability declaration; every other graph implementation is
   enumerated in `frontend/src/graph/registry.js`, may only shrink against
   `tooling/verify/baselines/graph_impls.baseline`, and the whole of it is
   enforced fail-closed by `tooling/verify/checks/graph_primitive.py`.
   Cross-reference `ARCHITECTURE_DECISIONS.md` for rationale; do not
   restate rationale in CLAUDE.md.

   (c) The check inventory / file-tree notes gain
   `tooling/verify/checks/graph_primitive.py`,
   `tooling/verify/baselines/graph_impls.baseline` and the
   `frontend/src/graph/` directory. `CLAUDE.md:411`'s `index.html` line
   should no longer imply the legacy document owns any graph.

   Respect `claude_md_contract.py`'s freshness contract and the file's
   budget: this is an amendment, not an expansion. If the budget is at
   risk, REPORT rather than silently trimming unrelated law.

2. **`tooling/standards/ARCHITECTURE_DECISIONS.md` - one new section**,
   placed after the TICKET-0056 cockpit-shell section, headed in the
   established style:

   `## GRAPH PRIMITIVE — one component, three consumers, a shrinking registry (BRIEF-0057-a .. BRIEF-0057-e, no schema change)`

   It records, each as its own bolded paragraph:

   - **There were three implementations, not two (RECON finding).** The
     workstream map named the Lieux SVG editor and the cytoscape relation
     graph. RECON found a third: `reviewGraphRender`, the pre-commit
     preview, with two consumers of its own (region and room batch). It
     already called `graphAutoPlace` from the Lieux implementation and then
     re-emitted its own SVG - placement shared, rendering diverged. That is
     what "plusieurs choses qui font la meme chose" looks like from the
     inside: not a decision to duplicate, a convergence abandoned halfway.
   - **A1 - the pilot renders as an in-frame island, and why nothing else
     was constructible.** All four graph surfaces live in Creation, a
     legacy mount until TICKET-0059; TICKET-0056 deferred continuous route
     sync to TICKET-0058, so the shell cannot know which sub-tab is active.
     A shell-side graph pane was therefore not an option, and reordering
     after 0058 would have defeated the locked strategy of proving the
     primitive BEFORE broad migration while inflating 0058.
   - **B3 - three consumers, not one.** A primitive with one consumer
     proves nothing; the second is what tests the contract. The two SVG
     implementations also carried no cytoscape dependency and no scoped-CSS
     problem. Accepted and recorded cost: the contract is frozen without
     ever exercising a force layout. `force` arrives with its consumer at
     TICKET-0058.
   - **The contract, and why capability is a callback and not a boolean.**
     `onConnect` / `onDeleteEdge` / `onMoveNode` absent means the
     interaction is structurally off. Boolean axes (`editable`,
     `persistsPositions`) would have had to be invented in pairs that only
     one consumer sets, and never independently - an axis nobody varies is
     a lie in the contract and the first plank of a leaky union type.
   - **G, and the axis that evaporated.** `graphAutoPlace` entered the
     primitive as its single placement strategy. It already handled both
     stored coordinates and null-coordinate fallback, so `placement` never
     became an axis at all: one strategy, data-driven branch. Recorded
     because it is the cleanest evidence that E1 was the right discipline -
     the axis the map proposed did not survive contact with the code.
   - **D2 - the declaration site is the slot descriptor, not the trait
     registry. NAMED DEFERRAL: `graph_spec_for(entity_type)`.**
     `CREATION_TABS` slots and the review descriptor already had live
     readers and a structural assertion; `traits.py` had none - no entity
     type declares a graph today, so `graph_spec_for` would have been
     structure without a reader (E2). It is deferred, not dropped: the day
     a runtime entity type wants to declare a graph, that is a ticket with
     a real consumer.
   - **C1 - the lock, and what a shrinking registry buys.** Modelled on
     TICKET-0056's legacy-mount registry. The guarantee is measurable
     during the transition - a counter that can only decrease - rather than
     promised for the end. Rule 5 (every entry must still describe real
     code) is what keeps rule 3 honest: the registry is forced to shrink
     when its code goes, instead of rotting into a stale list.
   - **F - a guard that was fail-open, named.** `relation_graph.py`'s
     clause 5 asserted the Lieux functions were byte-identical to `main`
     via `git show`. On a branch it bit; once merged, `main == HEAD` and it
     passed trivially forever. Recorded rather than quietly deleted,
     because the failure mode is general: any check comparing the working
     tree to `main` is a branch freeze, not an invariant. Replaced by
     `graph_primitive.py`, which holds after merge.
   - **Zero dormant code, made structural.** The creator's constraint was
     that no converged implementation survive at close. It is enforced by
     the lock's rule 1 as raw-substring absence, any context - a
     commented-out body is dormant code. This matters more than usual here
     because `undefined_names.py` covers Python only: there is no automated
     safety net for a dangling JS reference in `index.html`.
   - **Finding handed forward to TICKET-0060.** Observation renders no
     graph. Zero `<svg>` elements and zero graph calls in the thirteen
     `observation*` functions. TICKET-0060's open decision D-A is answered
     in advance: it is not a primitive consumer.
   - **The 3D guard rail: cross-reference only.** TICKET-0055's entry
     nailed it and TICKET-0056 declined to restate it on the grounds that
     restating doctrine is how doctrine drifts. That reasoning holds here
     too. Cross-reference, do not restate.

3. **`CHANGELOG.md`** - one entry at the top, matching the file's existing
   form, dated the merge day, marked no schema change. Two short
   paragraphs: what a reader of the cockpit will notice (nothing - the
   Lieux map and both pre-commit previews behave identically), and what
   changed underneath (one component, three consumers, a shrinking registry
   and a fail-closed check). Point to `ARCHITECTURE_DECISIONS.md` for the
   per-brief decisions.

4. **`decisions_index.py` reconciliation.** The new
   ARCHITECTURE_DECISIONS section header must be reflected in
   `tooling/verify/baselines/decisions_headers.baseline`. Run
   `python tooling/verify/checks/decisions_index.py` FIRST, observe how it
   fails on the unregistered header, then add the header, in the same
   commit. Do not pre-emptively edit the baseline from the shape of the
   check - let the check tell you the exact expected string.

5. **`tooling/standards/DECISIONS_INDEX.md`** - add the new section per the
   file's existing convention.

6. **Ticket file.** Set `status: done` in `TICKET-0057-graph-primitive.md`
   and tick the machine-checkable acceptance criteria. Leave the live gate
   boxes for Nia.

## Scope OUT

- **Any code change.** This step touches documentation and one baseline
  file only. If a doc cannot be written truthfully because the code does
  not do what it should, that is an ESCALATION back to the relevant brief,
  never a doc that describes an intention.
- **Rewriting the TICKET-0058 entry, or pre-writing its decisions.** The
  registry entry says `retiredBy: TICKET-0058`; that is the whole of what
  this ticket may say about it. Do not draft 0058's open decisions here.
- **Amending `Active_project.md` or any workstream map.** The map's A3 is
  now known to be incomplete (two implementations, not three) and its
  TICKET-0056 line about HTMX and the 3D guard-rail duplication were
  already corrected at 0055/0056. Those corrections live in
  ARCHITECTURE_DECISIONS, which is authoritative; the map is a planning
  artifact Nia maintains.
- **Restating the 3D guard rail.** Cross-reference only - see Scope IN 2.
- **Broadening CLAUDE.md.** Amend the existing law; do not add a new
  section, and do not import rationale from ARCHITECTURE_DECISIONS.
- **Renaming `index.html`.** TICKET-0061's named deferral.
- **Retiring `legacy_mounts.baseline`'s `creation` entry.** Creation is
  still a legacy mount until TICKET-0059; this ticket converged a
  component inside it, not the surface.

## Invariants to defend

- **Deferred items are named, never silently dropped.** D1
  (`graph_spec_for`) must appear as an explicit named deferral. A reader
  six months from now must be able to tell that it was decided against, not
  overlooked.
- **CLAUDE.md is law, ARCHITECTURE_DECISIONS is rationale.** Do not blur
  them. `claude_md_contract.py` polices the former's shape.
- **Restating doctrine is how doctrine drifts.** The 3D guard rail is
  cross-referenced, not repeated. This is itself a precedent set at
  TICKET-0056 and honoured here.
- **Docs describe what shipped.** No aspirational tense, no "will be".

## Done means

- [ ] `python tooling/verify/checks/claude_md_contract.py` -> PASS.
- [ ] `python tooling/verify/checks/decisions_index.py` -> PASS.
- [ ] `grep -n 'reviewGraphRender' CLAUDE.md` returns nothing.
- [ ] `grep -n 'graph_primitive' CLAUDE.md` returns the new law line and
      the check inventory entry.
- [ ] `ARCHITECTURE_DECISIONS.md` contains the new section, and it contains
      the literal strings `NAMED DEFERRAL`, `graph_spec_for`,
      `TICKET-0060` and `fail-open`.
- [ ] `grep -c '3D' ` on the new ARCHITECTURE_DECISIONS section shows the
      guard rail is referenced, not restated as doctrine.
- [ ] `CHANGELOG.md` carries a TICKET-0057 entry marked no schema change.
- [ ] `TICKET-0057-graph-primitive.md` has `status: done` and every
      machine-checkable box ticked.
- [ ] Full verify suite green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

This step IS the doc update.
