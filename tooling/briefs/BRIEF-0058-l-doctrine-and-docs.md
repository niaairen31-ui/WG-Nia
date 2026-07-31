# BRIEF — Step "doctrine + docs seal"

Ticket: TICKET-0058. Requires BRIEF-0058-k landed. Last brief of the ticket.

## Context

Eleven briefs changed what is true about this codebase: a graph registry
that is now empty, a lock that proves convergence instead of presence, a
second mount seam with its own fail-closed check, a Creation surface that is
part Svelte and part legacy, and a named deferral from TICKET-0056 that has
been discharged. None of it is written down yet, deliberately - each brief
was told not to pre-write this entry, because a doctrine written in
fragments across eleven commits is how doctrine drifts.

This step is the write-down. It touches no runtime code.

## Scope IN

1. **`tooling/standards/ARCHITECTURE_DECISIONS.md` - one new section**, at
   the end, with a header matching the strict pattern
   `decisions_index.py` enforces:

   `## CREATION SPINE — island seam, graph convergence, closure-driven scope (BRIEF-0058-a, BRIEF-0058-b, BRIEF-0058-c, BRIEF-0058-d, BRIEF-0058-e, BRIEF-0058-f, BRIEF-0058-g, BRIEF-0058-h, BRIEF-0058-i, BRIEF-0058-j, BRIEF-0058-k, BRIEF-0058-l, no schema change)`

   It records, in prose, and only what is now TRUE:
   - **A1, and why the seam runs legacy-hosts-Svelte.** The alternative put
     two tab bars in the tree for two tickets with a synchronization
     contract between them. Also record the forcing fact:
     `frontend/src/legacy/registry.js` already declared
     `creation: retiredBy TICKET-0059`, so shell-owned Creation chrome was
     not constructible here without defeating a registry.
   - **B2, and the correction to the workstream map.** The map's
     spine/periphery cut was by label; measurement showed `evenements` and
     `region` calling the sheet engine. Scope followed the call graph.
     Record the final residual - the tabs left for TICKET-0059 - as measured
     by brief -j, not as predicted here.
   - **C2, and the cost paid on purpose.** One renderer, not two behind one
     API. Cytoscape and its 435 KB left the tree. Ego/global modes, buckets,
     zoom/pan and the edge panel were reimplemented. Record the force-layout
     parameters' provenance (RECON-0058-a M1, measured) and any `DROP` Nia
     approved.
   - **D1, and the shape of the amended lock.** The rule changed direction:
     from "each declared implementation is present at its locus" to "each
     baselined implementation is absent from its locus". `graph_impls.retired`
     is append-only and is now the load-bearing half of the guarantee. State
     plainly that the graph registry is empty and what that means: a second
     graph engine is constructible only by defeating a fail-closed check.
   - **E1 discharged.** The TICKET-0056 named deferral - continuous route
     sync - landed at brief -k, via the same one-way CustomEvent channel,
     with `replaceState` and no `popstate` re-entry.
   - **The island registry GROWS.** Unlike the legacy and graph registries,
     `frontend/src/creation/registry.js` is a record of what has moved. Say
     so, so no later reader applies a shrink-only rule to it.
   - **Every check re-homed, and where.** The cross-cutting rule held: no
     guard lapsed between commits. Name each check and its new locus.
   - **What is still deferred, by name.** `graph_spec_for(entity_type)`
     (TICKET-0057 D2, still no reader); the `index.html` rename
     (TICKET-0061); the link agent and `npcAgent*` (TICKET-0059); the
     3D coordinate guard-rail - cross-reference only, NOT restated, since
     restating doctrine is how doctrine drifts.
   - **Anything RECON-0058-a refuted or corrected.** A surprising finding
     that changed the plan is the most valuable line in this entry.

2. **Regenerate `DECISIONS_INDEX.md`** via `tooling/glue/gen_decisions_index.py`
   so the committed index equals a fresh render. Do not hand-edit it.

3. **`CLAUDE.md` - amend the law, within budget.** The file is capped at 500
   lines and its "### File structure" section at 80, with an archaeology ban
   inside that section (`claude_md_contract.py`). Update:
   - The frontend doctrine lines to state the current law: a built Svelte
     shell serves the cockpit; Creation is partly Svelte islands mounted into
     the legacy document through a single seam; Play and the remaining
     Creation tabs are legacy until their own tickets.
   - The file-structure note to name `frontend/src/creation/` and its
     registry - with no `BRIEF-`, no `schema v`, no version numbers inside
     that section.
   - Add the two new checks (`creation_island.py`, and the amended
     `graph_primitive.py` semantics) wherever checks are enumerated.
   Every `tooling/...` path mentioned must exist on disk (assertion 4).

4. **`docs/launch-procedure.md`** - update only if the build or run steps
   changed. If nothing changed, state that in the commit message rather than
   editing the file to look busy.

## Scope OUT

- **Any runtime code, any check logic.** This step is documentation.
- **Restating the 3D guard-rail.** Cross-reference only; TICKET-0055 already
  re-nailed it and TICKET-0057 recorded why restating is harmful.
- **Pre-writing TICKET-0059's decisions.** Record the residual as a fact;
  its resolution belongs to that ticket's own conversation.
- **Rewriting earlier ARCHITECTURE_DECISIONS sections.** History is sacred
  here too - correct a prior record only if it is factually wrong, and say
  so explicitly if you do.
- **Editing `graph_impls.baseline` or `legacy_mounts.baseline`.**

## Invariants to defend

- **CLAUDE.md is law-only and budgeted** - narrative goes to
  ARCHITECTURE_DECISIONS.
- **Deferred items are named explicitly, never silently dropped.**
- **History is sacred** - this entry appends.

## Done means

- [ ] `python tooling/verify/checks/decisions_index.py` exits 0 - the
      committed index equals a fresh regeneration and the new header matches
      the strict pattern.
- [ ] `python tooling/verify/checks/claude_md_contract.py` exits 0 - section
      whitelist, both budgets, archaeology ban, and every `tooling/...`
      pointer resolving on disk.
- [ ] The new ARCHITECTURE_DECISIONS section names every one of: A1, B2, C2,
      D1, E1-discharged, the growing island registry, each re-homed check,
      and each named deferral.
- [ ] The residual tab list in the entry matches brief -j's reported list
      exactly.
- [ ] A full `/verify` run passes on the ticket branch.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

This step IS the doc update.
