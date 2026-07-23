---
id: TICKET-0041
title: Shared review-tree component extraction
type: feature
status: live-gate
created: 2026-07-22
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0041-a, BRIEF-0041-b, BRIEF-0041-c]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"TICKET-0041 (celui-ci) - Shared review-tree component extraction. Sort des 31
fonctions region* d'index.html un composant de revue generique (arbre,
accept/reject, cascade, graphe pre-commit) pilote par un descripteur explicite
au lieu des globales regionDraft / regionAccepted. Zero fonctionnalite nouvelle :
le seul critere de succes est que la revue region se comporte a l'identique, et
que la regle de repli de la cascade devienne un parametre au lieu d'une
constante."

Framing: second of three tickets of the room-batch generation chantier.
TICKET-0040 (size templates + perimeter doors) is landed on `main` at schema
v1.85. TICKET-0042 (room batch generator) follows and is untouched here.

## Structural justification (not aesthetics)

`regionCascade` (`cockpit/index.html:5915`) re-attaches an orphaned location to
the ROOT of the region: `rootLocal` is computed inside the function body
(`:5917`) and hard-wired as the fallback parent (`:5924`). The future batch
generator must re-attach to the ANCHOR chosen by the creator. The two consumers
differ by the value of one parameter, not by behaviour: duplicating would ship
two cascades identical up to a constant, and two places to fix the next
reparenting bug. S-norme; C2 (refactor over exemption).

## Clarifications resolved (intake)

Locked in this session, against live `main` at schema v1.85 (RECON-0041):

- **A3** - mechanical non-regression is STATIC (name disappearance, blindness of
  the component to region state, parameterised fallback, boundary allow-list),
  plus a NAMED, SCRIPTED LIVE GATE. No JS runtime enters the verify toolchain:
  there is no `package.json`, no build step, and `tooling/verify/run.py` shells
  Python checks only. Rendering equivalence is asserted by a human at a live
  sequence, and the ticket says so instead of pretending otherwise.
- **B1** - the anti-vacuity teeth are NOT a caller count. A caller count cannot
  be green at this ticket's close: the second consumer IS TICKET-0042, and four
  of the nine generics would have exactly one caller here. A fail-closed gate
  that cannot structurally be green is a broken gate. The teeth are instead:
  (a) no `review*` function body may contain the token `region` in any form,
  and (b) `reviewCascade` must carry `fallbackParentId` as a parameter. A rename
  without mutualisation keeps the globals in the body and fails (a); a rename
  that keeps the root hard-wired fails (b).
- **B1 corollary, amended in drafting** - the "byte-identical to `main` via
  `_git_show`" footprint criterion (precedent: `relation_graph.py` criterion 5)
  is REJECTED here: it goes vacuous the moment the ticket merges, since the
  check would then compare `main` to itself. Replaced by a permanent
  BIDIRECTIONAL boundary: outside the `review*` block, exactly four named
  functions may reference a `review*` symbol. Precedent: `json_ui_boundary.py`'s
  named allow-list.
- **C1** - splitting `index.html` (11206 lines) is OUT OF SCOPE, and for a
  stronger reason than "that would be two things at once": the monolith is a
  DOCUMENTED convention (`CLAUDE.md:17`, "single-page HTMX/vanilla-JS
  cockpit/index.html. No build step"), and `module_budget.py` scans
  `src/**/*.py` only, so `index.html` is structurally exempt from the 1000-line
  cap BY CONSTRUCTION. Splitting it is a doctrine amendment plus a serving route
  (`/vendor/{filename}` explicitly rejects non-vendored assets, `app.py:150`)
  plus an evaluation-order decision (`const NODE_R` at `:9299` is in TDZ if the
  component loads before it). It gets its own ticket and its own
  ARCHITECTURE_DECISIONS entry.
- **D1** - the component is a single block inserted at `index.html:5870`, just
  before `let regionDraft` (`:5872`), prefix `review*`, descriptor contract
  written verbatim in a header comment.
- **E1 (drafting)** - inline `onclick` handlers are string literals and cannot
  carry a closure. The component therefore keeps a REGISTRY:
  `reviewRegister(key, descriptor)`, and every entry point reachable from the
  DOM takes the registry key as its first argument. `reviewCascade` and
  `reviewNotes` are pure and take no key.

## Perimeter corrections found in RECON (not in the intake statement)

The intake listed `regionRenderFactionsPanel` and `regionRenderSheet` under
"does not move". Both claims are false as written; both corrections are one
token wide and are IN SCOPE:

1. `regionRenderFactionsPanel` (`:6192`) calls three of the nine:
   `regionRenderNotes` (`:6206`), `regionIsAccepted` (`:6196`),
   `regionToggleAccept` (`:6202`). Its three call sites move; its structure,
   its faction colouring and its badge do not.
2. `_sheetEntityOptions` (`:10881`), the helper of the untouched
   `regionRenderSheet` (`:10936`), calls `regionIsAccepted` (`:10886`) to suffix
   " (rejete)". That one call site moves.

## Target shape

Nine functions disappear, replaced by their generic equivalents:

```
regionCascade()                        -> reviewCascade(descriptor)          [pure]
regionIsAccepted(id)                   -> reviewIsAccepted(key, id)
regionToggleAccept(id)                 -> reviewToggleAccept(key, id)
regionRenderNotes(notes)               -> reviewNotes(notes)                 [pure]
regionRenderLocationNode(l, c, byPar)  -> reviewNode(key, node, cascade, byPar)
regionRenderTree(cascade)              -> reviewTree(key, cascade)
regionToggleLocGraph()                 -> reviewToggleGraph(key)
regionLocGraphData()                   -> reviewGraphData(key)
regionLocGraphRender()                 -> reviewGraphRender(key)
```

Descriptor contract:

```
{
  key,               registry key; first argument of every DOM-reachable entry
  nodes,             [{ id, name, subtitle, parentId, description, notes[], extras }]
  accepted,          plain map id -> bool; absent or true means accepted
  fallbackParentId,  where an orphan re-attaches (region -> draft root;
                     batch -> the creator's anchor). THE parameter of this ticket.
  reparentedLabel,   badge text on a re-attached node
  graphSvgId,        DOM id of the <svg> the graph draws into
  graphOpen,         bool
  onToggleAccept(id), onToggleGraph(), onOpenSheet(id), onRender(),
  graphExtraEdges(acceptedIds, nodeById) -> [{id, entity_a_id, entity_b_id, kind}]
}
```

Do NOT move: the whole Factions panel structure (`regionRenderFactionsPanel`,
`regionFactionColor` - a room batch has no factions, there is nothing to
mutualise); the seven `regionManifest*`; `regionCommit`; `regionRenderSheet`;
the three `sensed_links` functions (`regionLinkKey`, `regionIsLinkConfirmed`,
`regionToggleLink`); `regionEntityNotes`; `regionRenderLinkToggles`;
`regionRenderCommitResult`; `regionRenderBriefForm`; `regionGenerate`;
`regionBuild`; `regionRestart`; `regionShellNewRegion`.

## Invariant to defend

The region review behaves identically. Same tree, same cascade re-attachment,
same badges, same accept/reject, same link toggles, same pre-commit graph, same
commit payload.

## Scope OUT

Any generation; any schema change; the Factions panel structure; the Lieux
browse rework; any visual enrichment of the graph (nodes stay circles - drawing
bounds-scaled rectangles was explicitly rejected, cf. TICKET-0042); any split of
`index.html` (C1, own ticket); removal of the dead `cascade` parameter of
`regionRenderFactionsPanel` (RECON found it unused in the body - REPORT ONLY).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] None of the nine `region*` names survives anywhere in `index.html`  -> verify/checks/review_component.py
- [ ] Each of the nine `review*` names is defined exactly once  -> verify/checks/review_component.py
- [ ] No `review*` function body contains the token `region` or `REGION_` in any form, including CSS class names  -> verify/checks/review_component.py
- [ ] `reviewCascade` takes exactly one parameter, references `fallbackParentId`, and touches no DOM (`document.`, `getElementById`)  -> verify/checks/review_component.py
- [ ] `regionReviewDescriptor` is defined exactly once and `reviewRegister('region'` appears exactly once  -> verify/checks/review_component.py
- [ ] Outside the `review*` functions, only `regionRenderAll`, `regionReviewDescriptor`, `regionRenderFactionsPanel` and `_sheetEntityOptions` reference a `review*` symbol  -> verify/checks/review_component.py
- [ ] The check is fail-closed: a missing `index.html`, an unparsable component block, or zero rules evaluated is a FAILURE, never a vacuous pass  -> verify/checks/review_component.py

### Live  ->  human gate (Nia)
Scripted sequence, run once end to end, Creation tab -> Region:
- [ ] Generate a region. The tree renders with the same indentation, the same type subtitles and the same descriptions as before the ticket.
- [ ] Reject an INTERMEDIATE location that has children. The children re-attach under the region root and each carries the "rattache a la racine" badge. The rejected node dims (opacity 0.5) and its own subtree stays visible.
- [ ] Reject the ROOT itself. Its children fall to no-parent and render at top level, unchanged from before.
- [ ] Re-accept everything. The tree returns to its original shape.
- [ ] Confirm one `connection` sensed_link and one `faction` sensed_link. The toggles read "Confirme" and the non-wirable links still render as plain notes.
- [ ] Open the pre-commit location graph. Hierarchy edges are solid, confirmed connection edges are dashed, rejected locations are absent from the graph, node labels sit under circles of radius NODE_R.
- [ ] Close and re-open the graph; toggle a rejection while it is open. It re-renders correctly both times.
- [ ] Open an entity full sheet by clicking its name. Reassign a parent from the sheet's select; rejected entities still show the " (rejete)" suffix in that select. Close the sheet: the tree refreshes.
- [ ] Commit the region. The commit response, the committed counts, the written/unresolved links and the notes are identical in shape to a pre-ticket commit.
