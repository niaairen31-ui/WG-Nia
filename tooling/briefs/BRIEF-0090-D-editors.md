# BRIEF 0090-D — "editors"

Lot: LOT-0090-oriented-relations.md (authoritative on conflict)
Depends on: BRIEF-0090-C (payload C-10, routes C-13)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `GET /api/entities/{id}` returns relations carrying `perceiver_id`,
  `perceiver_name`, `target_id`, `target_name`, `sheet_side`, `is_social`
  and `target_knows` (brief C).
- `PUT /api/relations/{id}/target-knows` exists and takes `{"knows": bool}`.
- `creation/RelationsEditor.svelte:14` — `const RELATION_DIRECTIONS =
  ['mutual', 'a_to_b', 'b_to_a']`; `:22-31` maps rows and drops `role`;
  `:98-103` and `:136-141` are the two direction selects; `:106-108` and
  `:144-146` are the "Visible to B" checkboxes.
- `creation/RelationsEditor.svelte:51-60` — `saveRow` sends `type`,
  `direction`, `intensity`, `visible_to_b`, `notes`.
- `creation/DoorsEditor.svelte:34-36` — reads `type`, `other_entity_id`,
  `other_entity_name` from the same `relations` prop.
- `graph/consumers/relations.js:84` — the node-info line printing
  `intensité … · direction`; `:109-124` — the edge form's direction select;
  `:139-146` — the save body.
- `Sheet.svelte:698-699` — `RelationsEditor` receives `relations`,
  `entityId`, `entities`, `typeOptions`.
- `checks/module_budget.py:58` — `FRONTEND_MAX_LINES = 1000`;
  `RelationsEditor.svelte` is 152 lines, `graph/consumers/relations.js` 252.

## Facts carried

**R-10** — the three frontend surfaces print the raw vocabulary:
`RelationsEditor.svelte` (`:14`, `:98-103`, `:106-108`, `:136-141`,
`:144-146`), `graph/consumers/relations.js` (`:84`, `:109-124`, `:143`),
`LinkAgent.svelte:137-151`. `DoorsEditor.svelte:34-36` reads three keys of
the same payload, so the payload stayed additive.

**R-09** — the sheet gets its relations inside the entity payload
(`crud/entities.py:512, 800, 850, 875`), not from a dedicated endpoint;
`RelationsEditor` reloads by re-fetching `/api/entities/{id}`
(`:47-49`).

**R-18** — `module_budget.py` caps a frontend file at 1000 lines;
`frontend_build_fresh.py` and `static_asset_freshness.py` require the
bundle to be rebuilt and committed.

## Contracts

Consumed verbatim from the lot header:

### C-10 — the relation payload
`_relation_dict` keeps `id`, `role`, `other_entity_id`, `other_entity_name`,
`other_entity_type`, `type`, `direction`, `intensity`, `visible_to_b`,
`notes`, `last_evolved_at`, and adds `perceiver_id`, `perceiver_name`,
`target_id`, `target_name`, `sheet_side` (`"perceiver"` or `"target"`),
`is_social`, `target_knows`.

### C-13 — the target-knows route
`PUT /api/relations/{relation_id}/target-knows`, body `{"knows": bool}`.
404 unknown relation; 409 structural relation; returns the relation dict.

## Context

The data and the API now speak in perceivers. This brief is the reason the
ticket exists: from any sheet, a relation must read as a sentence that names
who feels what toward whom, and a reciprocal feeling must be two rows the
creator can edit apart.

## Scope IN

1. `creation/RelationsEditor.svelte` — existing rows:
   - Delete the `RELATION_DIRECTIONS` constant, both direction selects and
     both "Visible to B" checkboxes.
   - Carry `perceiver_name`, `target_name`, `sheet_side`, `is_social` and
     `target_knows` through the `$effect` mapping at `:22-31`.
   - Render each social row's heading as a sentence:
     `{perceiver_name} → {type} → {target_name}`, with the sheet's own side
     emphasised (a `badge` on the name equal to `entityId`'s). Structural
     rows (`is_social === false`) render `{other_entity_name} ({type})` and
     show no knows control.
   - `type`, `intensity` and `notes` stay editable; `saveRow` sends
     `type`, `intensity`, `notes` only.
   - Add, per social row, a checkbox labelled `{target_name} le sait`, bound
     to `target_knows`, whose change calls
     `PUT /api/relations/{id}/target-knows` through `sheetRequest` and
     reloads the entity like the other controls.
2. `creation/RelationsEditor.svelte` — the add form:
   - Replace the direction select with a checkbox `Réciproque (crée deux
     relations)`, default off, sent as `reciprocal`.
   - The "With" select keeps its candidate list; the form's sentence preview
     reads `{sheet entity name} → {type ou « … »} → {selected name}`.
   - Remove `visible_to_b` from the POST body; send `other_entity_id`,
     `type`, `intensity`, `notes`, `reciprocal`.
   - A 409 surfaces through the existing `sheetRequest` status path; do not
     add a bespoke alert.
3. `graph/consumers/relations.js`:
   - `:84` — replace `· ${escapeHtml(e.direction)}` with the oriented
     sentence built from the edge's own endpoints, using the node names
     already in `lastData.nodes`.
   - `:109-124` — delete the direction select. On create, add a
     `Réciproque` checkbox sent as `reciprocal`; on edit, no direction
     field at all.
   - `:139-146` — the save body becomes `type`, `intensity`, `notes`
     (+ `reciprocal` on create only).
   - Leave the delete button, the reload helpers and `lieux.js` untouched.
4. Rebuild the frontend bundle and commit the build output, so
   `frontend_build_fresh.py` and `static_asset_freshness.py` stay green.
5. Update the component header comment of `RelationsEditor.svelte`: the
   TICKET-0059 port note stays, followed by a TICKET-0090 note saying the
   direction vocabulary is gone because a social relation is always the
   perceiver's row, and that "réciproque" writes two independent rows.

## Scope OUT

- `LinkAgent.svelte` — brief E owns it.
- Any backend file. If the payload lacks something the editor needs, that is
  a STOP, not a route edit.
- `DoorsEditor.svelte`, `lieux.js`, and anything about doors or map edges.
- Showing `target_knows` on the graph edge form — the control lives on the
  sheet this ticket.
- Any restyling beyond the classes already used by these files
  (`stylesheet_partition.py` rule 7 allows only classes with a base rule).
- Adding a modal, a confirm, or a new primary action to the Creation tab.

## Invariants to defend

- **Every Création page is a `CREATION_TABS` registry entry rendered by the
  generic dispatcher** — this brief edits an existing island's component
  only; no registry entry, no container, no mount site changes.
- `effect_self_write` — the `$effect` at `:21-32` assigns `rows` from props;
  keep it assigning only, never reading `rows` back inside the same effect.
- `stylesheet_partition.py` rule 7 — every class used must already have a
  base rule in `shared.css`, `creation.css` or the file's own `<style>`.
- `module_budget.py` — both files stay under 1000 lines.

## Decision rights

STOP:
- Any anchor above has moved.
- The payload does not carry a key C-10 promises.
- The sentence cannot be rendered for a row because `perceiver_name` or
  `target_name` is null.

ADAPT (do it, then report):
- A class you need has no base rule: use an existing one from the panel
  vocabulary (`row-card`, `field-row`, `field-grid`, `badge`, `btn-ghost`,
  `btn-end`, `btn-send`) rather than adding CSS.
- `RelationsEditor.svelte` passes 1000 lines: extract the row into a sibling
  component under `frontend/src/creation/`.
- The graph consumer's node-info block needs a node name it does not have in
  `lastData`: fall back to the id and report.
- The build emits a warning about an unused import after the deletions:
  remove the import.

REPORT-ONLY:
- Structural rows (`connects_to`, `controls`) still editable from the sheet
  with their type field.
- The graph edge payload still carrying `direction`.
- Any row whose `type` is free text outside the datalist.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] On a character sheet, every social relation reads as
      `A → type → B (intensité N)`, and the same relation reads identically
      from B's sheet.
- [ ] No `a_to_b`, `b_to_a`, `mutual` or "Visible to B" string remains in
      `frontend/src/creation/RelationsEditor.svelte` or
      `frontend/src/graph/consumers/relations.js`
      (`grep -n "a_to_b\|b_to_a\|mutual\|Visible to B"` returns nothing).
- [ ] Adding a relation with `Réciproque` checked produces two rows on the
      sheet; editing one leaves the other's intensity unchanged after a
      reload.
- [ ] Ticking `{target} le sait` and reloading the sheet keeps it ticked;
      unticking it and reloading keeps it unticked.
- [ ] The graph edge form has no direction control and saves type,
      intensity and notes.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py`,
      `static_asset_freshness.py`, `stylesheet_partition.py`,
      `effect_self_write.py`, `module_budget.py`, `page_contract.py` and
      `corpus_gate.py` print PASS.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- The `RelationsEditor.svelte` header comment (Scope IN 5). No schema,
  ARCHITECTURE_DECISIONS or CLAUDE.md change in this brief.
