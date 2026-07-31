# BRIEF — Step "island seam + Constructeur pilot"

Ticket: TICKET-0058. Relies on RECON-0058-a M5, M6, M7.

## Context

Bloc A1 is locked: for this ticket and the next, the legacy document keeps
`CREATION_TABS` (`index.html:4274`), the dispatcher (`index.html:4463`) and
the tab bar, while migrated surfaces become Svelte islands mounted into the
legacy containers they already own. TICKET-0057 proved the mechanism on
graphs; this step generalises it to arbitrary panels and locks it, so that
briefs -e..-j have one way to mount and only one.

The pilot is Constructeur: five functions (`index.html:7196..7259`), its own
container (`#creation-constructeur`, `index.html:1429`), no shared state
with the sheet engine, and it is the feature that motivated the whole
workstream - creating entity types from the UI. A pilot that proves nothing
is a pilot that was chosen for being easy; this one is both small and
load-bearing.

The seam is deliberately shaped like `graph/mount.js`
(`frontend/src/graph/mount.js:129`) rather than beside it: same one-way
legacy -> shell CustomEvent, same registry-of-consumers shape, same
fail-closed check idiom. A second mounting mechanism is the thing this step
exists to make unconstructible.

## Scope IN

1. **`frontend/src/creation/registry.js` - the island registry.** A frozen
   object, one entry per migrated surface:
   `<key>: { containerId, component, migratedBy }`, where `migratedBy`
   matches `^TICKET-\d{4}$`. Unlike the legacy and graph registries this one
   GROWS - it is the record of what has moved, not of what remains. Its
   comment must say so explicitly, so no reader mistakes it for a
   shrink-only list. Seed it with the Constructeur entry only.

2. **`frontend/src/creation/mount.js` - the mount seam.** Modelled on
   `graph/mount.js`. Responsibilities, and no others:
   - `initCreationMount(legacyDoc)` registers the SINGLE listener for
     `island:slot` CustomEvents on the legacy document.
   - `mountIsland(key)` resolves the registry entry, obtains its container
     through `legacyContainer(containerId)` (`legacy/bridge.js:105`) and
     mounts the component with `svelteMount`.
   - `unmountIsland(key)` tears down explicitly, never leaving an orphaned
     instance when a panel re-emits its markup - the failure
     `graph/mount.js:96-105` already documents.
   - Mount/unmount lifecycle follows exactly what RECON-0058-a M5 measured:
     mount-once if the island survives `style.display` toggling, mount-per-
     activation if it does not. Copy the working form; do not choose.
   - A failed mount renders a visible message into the container, never a
     silent catch (`graph/mount.js:54-58` is the pattern).
   `contentWindow` never appears here: the token stays confined to
   `legacy/bridge.js` and `LegacyFrame.svelte`, which `legacy_mount.py`
   assertion 5 enforces.

3. **`frontend/src/App.svelte` - call `initCreationMount(legacyDocument())`**
   in `onLegacyReady()`, immediately after `initGraphMount(...)`
   (`App.svelte:37`).

4. **`index.html` - the signal, and only the signal.** `CREATION_TABS`
   entries gain an optional field `island: { key }`. When
   `_creationActivateTab()` (`index.html:4433`) activates an entry declaring
   `island`, it dispatches
   `document.dispatchEvent(new CustomEvent('island:slot', { detail: { key: entry.island.key, open: true } }))`
   and performs no rendering of its own for that entry. The legacy document
   signals intent; it never loads, draws, or knows what a Svelte component
   is. Extend the `CREATION_TABS` entry-contract comment
   (`index.html:4061-4086`) to document the `island` field verbatim:

   ```
   //   island:       { key } | undefined — when present, this tab's body is
   //                 a Svelte island (TICKET-0058). The legacy document
   //                 dispatches 'island:slot' and renders nothing itself;
   //                 the shell owns the panel. Declared in
   //                 frontend/src/creation/registry.js.
   ```

5. **`frontend/src/creation/Constructeur.svelte` - the pilot component.**
   A faithful port of `constructeurRender` (`index.html:7196`),
   `constructeurSubmit` (`7220`), `constructeurOnNameInput` (`7183`),
   `constructeurOnSlugInput` (`7192`) and `constructeurResetForm` (`7247`).
   Behaviour that must be preserved exactly:
   - The trait palette is read from `authorRegistry.checkable_traits`,
     server-sourced. **Never a hardcoded trait list** - a trait added in
     `traits.py` must appear with no frontend edit. The component fetches
     `GET /api/entity-types` itself rather than reading the legacy global.
   - Slug auto-derives from the name until the slug field is touched.
   - Submit posts to `POST /api/entity-types` and, on success, causes the
     runtime tab factory to re-run so the new type's sub-tab appears in the
     same session (TICKET-0046's guarantee).
   - Errors render in the panel, in the existing refusal style.
   Since the legacy `refreshCreationTabs()` (`index.html:7301`) still owns
   the tab bar under A1, the component signals it through a CustomEvent the
   legacy document listens for - the reverse-direction call the bridge does
   not offer. Add exactly one such listener in `index.html`, calling
   `refreshCreationTabs()` and nothing else.

6. **Delete the five legacy `constructeur*` functions** and the
   `constructeurSlugTouched` global (`index.html:7181`). `#creation-constructeur`
   remains as the empty mount container.

7. **`tooling/verify/checks/creation_island.py` - the lock.** Same idiom as
   `legacy_mount.py` / `graph_primitive.py`: module-level `FAILURES`,
   `fail()`, `_report_and_exit(counts)`, `ROOT` via `parents[3]`, stdlib
   only, no DB, no subprocess. Each rule vacuous-proof:
   1. `creation/registry.js` parses and is non-empty.
   2. Every entry declares a well-formed `migratedBy`, a non-empty
      `containerId` and a non-empty `component`.
   3. Every declared `component` file exists under `frontend/src/creation/`.
   4. Every declared `containerId` exists as an element id in `index.html`.
   5. Every registry key is declared by exactly one `island: { key }` in
      `index.html`'s `CREATION_TABS`, and every `island: { key }` in
      `index.html` resolves to a registry key. Zero collected on either side
      is a failure.
   6. `svelteMount` / `mount(` from `svelte` is called on a legacy-document
      target in exactly one file: `frontend/src/creation/mount.js`
      (`graph/mount.js` excepted by name, and only that file). This is the
      no-second-mechanism rule.
   7. The migrated surface's legacy functions are gone: for every registry
      entry, a recorded `retiredPrefix` (add the field) has zero occurrences
      in `index.html`, in any context.
   8. `island:slot` is dispatched only from `index.html` and listened for
      only in `frontend/src/creation/mount.js`.

## Scope OUT

- **Migrating the sheet engine, the entity list, the review queue, region,
  evenements or the faction roster.** Briefs -e..-j, each consuming this
  seam.
- **Moving `CREATION_TABS`, the dispatcher, the tab bar or the runtime tab
  factory into Svelte.** They stay legacy for this ticket and the next.
- **Retiring `creation` from `legacy/registry.js`.** TICKET-0059.
- **Continuous route sync.** Brief -k.
- **Generalising `island:slot` to carry per-instance data.** The Constructeur
  needs none. An axis no consumer exercises is a lie in the contract
  (TICKET-0057 E1). Later briefs may extend `detail` when they have a reader.
- **A shared island base class, layout wrapper, or store abstraction.** Two
  islands do not justify a framework; brief -j may propose one with evidence.
- **Any backend change.** `POST /api/entity-types` is used as it stands.

## Invariants to defend

- **Exclusion is structural, never instructional** - unaffected here, but
  the Constructeur must not gain any trait-filtering logic of its own: the
  server decides what is checkable.
- **No structure without a reader (E2).** Every registry field has a reader
  in this commit or it is not added.
- **Single canon-write authority.** The Constructeur writes through the
  existing creator-CRUD endpoint only; the governed DDL runtime
  (TICKET-0044) is untouched.
- **Fail-closed over advisory.** `creation_island.py` lands in the same
  commit as the first island, not after.
- **No `<svg` under `frontend/src/` outside `graph/`** - per M6, any icon in
  the ported panel becomes a text glyph.

## Done means

- [ ] `python tooling/verify/checks/creation_island.py` exits 0 and reports
      1 island.
- [ ] On a scratch copy with a second `svelteMount` added to any other file
      under `frontend/src/creation/`, the check exits 1.
- [ ] On a scratch copy with the registry entry removed but `island: { key }`
      left in `index.html`, the check exits 1.
- [ ] `grep -c constructeur src/world_engine/cockpit/index.html` returns only
      the container id, the `island` declaration and the tab registration -
      no function bodies.
- [ ] `python tooling/verify/checks/page_contract.py` exits 0.
- [ ] `python tooling/verify/checks/legacy_mount.py` exits 0.
- [ ] Live: Constructeur tab renders the trait palette from the server;
      typing a name fills the slug; editing the slug stops the auto-fill;
      creating a type shows the success line WITH the physical table name and
      the new sub-tab appears in the tab bar in the same session; clicking it
      lists that type's entities.
- [ ] Live: submitting with an empty name shows the refusal, and no type is
      created.
- [ ] Live: switching worlds and returning leaves the Constructeur usable.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `CLAUDE.md`: none yet - the seam is described once, in brief -l.
- `tooling/standards/code_standards.md`: no change.
