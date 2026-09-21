# BRIEF 0089-F — "An entity_ref select never silently loses its current value"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `frontend/src/creation/Field.svelte:89-98`, verbatim:
  ```
  {:else if field.kind === 'entity_ref'}
    {@const candidates = (ctx.entities || []).filter((e) => e.type === field.ref_type && !(field.exclude_self && ctx.entityId && e.id === ctx.entityId))}
    <div class="field-row"><label for={id}>{label}</label>
      <select {id} data-field={field.name} data-kind="entity_ref" disabled={!!field.readonly}>
        <option value="">—</option>
        {#each candidates as e (e.id)}
          <option value={e.id} selected={e.id === resolvedValue}>{e.name}</option>
        {/each}
      </select>
    </div>
  ```
- `Field.svelte:30` -> `const resolvedValue = $derived(value === undefined &&
  field.default !== undefined ? field.default : value);`
- `frontend/src/creation/fields.js:15-29` -> `readFieldValue` resolves
  `doc.getElementById(\`${idPrefix}-${field.name}\`)` and returns `el.value`
  for every kind other than `bool`, `number` and `json`.
- `frontend/src/creation/EntityList.svelte` -> `creationState.entities` is
  assigned from an unfiltered `await api('/api/entities')`.
- `frontend/src/creation/Field.svelte` is 102 lines against a 1000-line cap.
- `frontend/package.json` -> `"build": "vite build && node
  scripts/write-manifest.mjs"`.

## Facts carried

**R-12 — the `entity_ref` select has no option for a current value absent from
its candidates.** The markup above emits one `<option value="">` plus one per
candidate; `ctx.entities` is `creationState.entities`. Consequence: when
`resolvedValue` matches no candidate, no option is selected, the browser keeps
the first one (`value=""`), and the next save writes NULL through
`_build_extension_kwargs`.

**R-11 — the sheet sends the complete registry field set, or fails before
sending.** `readFieldValue` dereferences `.value` with no null guard, so a
missing element aborts the save. Consequence: the defect here is a present
key carrying `""`, not an absent key.

**R-28 — the frontend build is committed and hash-checked.** Four
vacuous-proof assertions: sources exist; output exists under
`src/world_engine/cockpit/static/` with at least one `*.js` and an
`index.html`; `.build-manifest.json` parses and carries a 64-hex
`source_hash`; and the recomputed source hash equals the manifest's.
Consequence: this brief is not done when `Field.svelte` changes; it is done
when the rebuilt output and manifest are committed with it.

## Contracts

This brief produces and consumes no `C-NN`. Its contract is a rendering rule:
**a select that carries a value renders an option for it.**

## Context

The backend half of the silent NULL is closed by brief E. This is the client
half: a location the candidate list does not contain -- because the list was
never loaded in this session, because it was loaded for another world, or
because the entity was created after the load -- makes the control display
the em-dash placeholder as though the field were empty. Nia sees a blank
Current location, saves the sheet for an unrelated reason, and the value is
gone with no error and no trace.

## Scope IN

1. In `Field.svelte`'s `entity_ref` branch, add a second `{@const}` computing
   whether `resolvedValue` is a non-empty value absent from `candidates`.
2. When it is, emit one extra `<option>` before the `{#each}`, carrying
   `value={resolvedValue}` and `selected`, whose text is the id itself
   prefixed by a marker the creator reads as "this is set, and I cannot show
   you its name from here" -- use `⚠ {resolvedValue}`. Do not invent a name
   for it and do not fetch one.
3. Leave the `<option value="">—</option>` placeholder first in the list, so
   clearing the field is still one click.
4. Add a comment above the branch stating the rule and why: the select is
   read back verbatim by `readFieldValue`, so an unrepresented current value
   is silently rewritten to `""` on the next save.
5. Rebuild the frontend (`cd frontend && npm run build`) and commit the
   regenerated output under `src/world_engine/cockpit/static/`, including
   `.build-manifest.json`, in the same commit as the source change.

## Scope OUT

- Fetching the missing entity's name. It would turn a render into a network
  call, and the id is enough to tell the creator the field is not empty.
- Reloading `creationState.entities` when a value is missing from it, or
  changing when `EntityList.svelte` loads. That is a data-freshness question
  of its own and it borders the world-switch behaviour.
- The `select` and `datalist` branches of the same component. Only
  `entity_ref` points at an entity id that the backend then clears.
- `readFieldValue`'s missing-element behaviour. It aborts the save, which is
  the correct failure; hardening it would hide a real defect.
- `Sheet.svelte`'s save loop, the payload shape, and anything backend. Brief E
  owns the write semantics.
- Every other brief in this lot: A, B, C, D, E, G.

## Invariants to defend

- **Structural over disciplinary.** The fix is in the control that produces
  the value, not a warning in a docstring or a rule the creator must
  remember.
- **Exclusion is structural.** The extra option exposes an id the creator
  already owns on a creator-only surface; it introduces no new read of
  anything filtered elsewhere.
- No new CSS class or id: `stylesheet_partition.py` rule 7 requires a strict
  base rule for every applied class, and this brief applies none.

## Decision rights

STOP:
- `Field.svelte` no longer holds the `entity_ref` branch in the anchor's
  shape.
- `npm run build` fails, or the build output it produces differs from the
  committed one in files this change does not explain.

ADAPT:
- Svelte rejects a second `{@const}` at that position: compute both values in
  a single `{@const}` object, or lift the computation into the component's
  `$derived` block at the top, and report.
- The `⚠` character is mangled by the build or by the `.gitattributes`
  `text eol=lf` normalisation: use the ASCII fallback `(id) ` prefix and
  report.

REPORT-ONLY:
- Whether any other `entity_ref` field in the registry is currently rendering
  a value its candidate list does not contain, on the worlds you can reach.
- The size of the rebuilt bundle relative to the committed one.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `Field.svelte`'s `entity_ref` branch emits a selected option for a
      current value absent from `candidates`, and emits nothing extra when the
      value is empty or already present.
- [ ] `frontend/src/creation/Field.svelte` is at most 110 lines.
- [ ] `cd frontend && npm run build` completes, and the regenerated
      `src/world_engine/cockpit/static/` output plus `.build-manifest.json`
      are committed in this commit.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/checks/static_asset_freshness.py` passes.
- [ ] `python tooling/verify/checks/stylesheet_partition.py` passes.
- [ ] `python tooling/verify/checks/module_budget.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes.
- [ ] Manually, on the test database: open an NPC sheet whose
      `current_location_id` points at a location, clear
      `creationState.entities` by loading the sheet without the list having
      been fetched, and confirm the field shows the marked id rather than the
      em-dash; then save and confirm the stored value is unchanged.
- [ ] `/review-step` then `/close-step`.

## Docs to update

None. The rule lives in the comment added at the branch; it decides nothing
that belongs in the decision registry, and the write-side rule it protects is
recorded by brief E.
