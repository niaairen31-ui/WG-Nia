---
paths:
  - "frontend/src/**/*.svelte"
  - "frontend/src/**/*.js"
  - "frontend/public/*.css"
---

# Frontend (Svelte shell)

Any `frontend/` edit is rebuilt (`npm run build` in `frontend/`) and the
built output under `src/world_engine/cockpit/static/` is committed with it.
Creation's Compétences tab reads `skill_system`: a list grouped by system
beside one fiche; `Sans système` is a rendered group, never a stored row.

## Invariants

- **INV-49** Every Création page is a `CREATION_TABS` registry entry rendered
  by the generic dispatcher; no page/tab-specific branch exists outside it.
  -- enforced by `page_contract.py`
- **INV-50** Every Création surface mounts as a `CREATION_ISLANDS` entry
  declaring its origin (`migration` or `new`) through `mount.js` alone;
  `Creation.svelte` imports and renders no component. -- enforced by
  `creation_island.py`
- **INV-51** The review tree (`review*`,
  `frontend/src/creation/review/registry.js`) is a generic accept/reject
  component, never driven by consumer globals. -- enforced by
  `review_component.py`
- **INV-52** The graph primitive (`frontend/src/graph/Graph.svelte`) is the
  ONE graph component; a second engine is constructible only by defeating
  the check's fail-closed lock. -- enforced by `graph_primitive.py`
- **INV-53** A Creation sub-tab change clears the entity sheet from the
  single dispatcher (`showCreationSubTab`), BEFORE `activeTabKey` moves and
  on every change, never per registry entry; `Sheet.svelte` selects its
  render branch from `sheetType`, the same fact that feeds it, never from
  `activeTabKey`. -- enforced by `creation_tab_switch.py`
- **INV-54** A Création tab that owns a single container sizes it in
  `frontend/public/creation.css` (`flex: 1; min-height: 0`), so its content
  scrolls instead of being clipped. -- enforced by
  `creation_container_sizing.py`
- **INV-55** Inside a `$effect` body, a `$state` binding assigned there is
  never read afterwards in the same body. -- enforced by
  `effect_self_write.py`
