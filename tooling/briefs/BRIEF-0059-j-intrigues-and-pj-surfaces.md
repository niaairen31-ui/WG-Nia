# BRIEF — Step "intrigues bespoke surface + pj create panel and skill slot"

Ticket: TICKET-0059. Requires BRIEF-0059-i landed. Cites RECON-0059-a **M5**,
**M7**.

**Anchor convention.** Every line number below is indicative, read from a
tarball of `main` this session. Your working tree is ahead of it. **Locate by
function name; verify every line locally before acting on it.**

## Context

Two `archetype: 'entity'` tabs still carry bespoke legacy code inside
otherwise-migrated islands. Both are the same shape as the `pj` comment in
`CREATION_TABS` already describes: the generic entity engine is ported, but a
tab-specific create flow or slot renders into a legacy slot inside the mounted
island.

**Intrigues** (13 functions, ~4153 and ~4536-4842). The tab declares
`listLoader: loadAgendasList`, `sheetRenderer: renderAgendaSheet` and
`createPanel: intriguesRenderCreatePanel` — three legacy hooks the chrome
calls. Agendas are not generic entities: they carry ordered steps with their
own statuses, an owner, and links to NPC goals that the entity sheet's goals
editor also touches.

**PJ** (12 functions, ~5369-5660). Two separate legacy surfaces on one tab:
`pjRenderCreatePanel` + `pcCreate*`/`pcGenerateDraft`/`pcApplyDraft`
(a bespoke create flow hitting `/api/characters/player`, deliberately not the
generic `/api/entities` route), and the `fiche` slot
(`skillInit`, `skillLoadCharacters`, `skillSelectCharacter`, `skillRender`,
`skillSaveTier`, `pjFicheOnSelect`) rendering into `#creation-pj-skill`.

The `pj` entry's existing comment states the rule that governs both:
`creation_island.py` rule 11 pairs `primaryAction` and `createPanel` on the
same side. Porting a `createPanel` therefore obliges porting its
`primaryAction` handler in the same commit — `creationNewEntity` becomes
`_islandPrimaryAction('entitySheet')`.

## Scope IN

### Commit 1 — intrigues list and sheet

1. **`frontend/src/creation/Intrigues.svelte`** plus
   **`frontend/src/creation/intrigues.svelte.js`** for non-render logic. Port
   `loadAgendasList`, `renderAgendaSheet`, `_intriguesRenderStep`,
   `_intriguesRenderLinkedGoal`, `_intriguesRefreshSelection`,
   `_intriguesPopulateOwnerSelect`, `intriguesSetAgendaStatus`,
   `intriguesStepStatus`, `intriguesDetachLink`, `_intriguesTabEnterReset`.

   The tab keeps `islands: [entityList, entitySheet]`. `listLoader` and
   `sheetRenderer` become `null`, and the ported renderers become the sheet's
   per-type branch — read how `Region.svelte` and the `entitySheet` island
   already express type-specific sheets before inventing a new mechanism.

2. **`intriguesDetachLink` shares its endpoint with the entity sheet's goals
   editor** (`GoalsEditor.svelte`, ported in `-d`, calls the same
   goal-agenda-link detach route). Do not unify the two callers and do not
   move the call into `GoalsEditor`. Two surfaces legitimately act on one
   route; that is not divergence. Verify after porting that detaching from
   either side still updates the other on refresh.

### Commit 2 — intrigues create panel

3. Port `intriguesRenderCreatePanel`, `intriguesGenerateDraft`,
   `intriguesSubmitCreate`. Set `createPanel: null` and change
   `primaryAction.handler` from `creationNewEntity` to
   `() => _islandPrimaryAction('entitySheet')`, keeping the label
   `+ Nouvelle intrigue`. **Both changes land in this same commit** —
   `creation_island.py` rule 11 fails if they split.

   `intriguesGenerateDraft` produces a draft the creator submits; it does not
   write. Preserve that: generation fills the form, `intriguesSubmitCreate`
   posts it.

### Commit 3 — pj create panel

4. **`frontend/src/creation/PjCreatePanel.svelte`** — port
   `pjRenderCreatePanel`, `pcCreateLoadLocations`, `pcCreateSubmit`,
   `pcRenderDraftKnowledge`, `pcGenerateDraft`, `pcApplyDraft`.

   `pcCreateSubmit` posts to `/api/characters/player`, **not**
   `/api/entities`. That distinction is the reason this panel is bespoke and
   it must survive the port unchanged. Do not route it through the generic
   field engine.

5. Set `createPanel: null` and `primaryAction.handler` to
   `() => _islandPrimaryAction('entitySheet')`, label `+ Nouveau`, in this
   same commit (rule 11). **Delete the now-false explanatory comment** on the
   `pj` entry describing the legacy pairing, and replace it with one sentence
   recording that the bespoke endpoint survives while the panel no longer
   does.

### Commit 4 — pj skill slot

6. **`frontend/src/creation/PjSkillFiche.svelte`** — port `skillInit`,
   `skillLoadCharacters`, `skillSelectCharacter`, `skillRender`,
   `skillSaveTier`, `pjFicheOnSelect`.

   Register it as an island on `#creation-pj-skill`. The slot descriptor's
   `loader` and `onSelect` become `null`; the component reacts to the
   selected character itself. **Read how the `region` and `batch` slots
   express selection into a mounted island** before choosing the mechanism —
   `onSelect` exists precisely for this and its Svelte-side equivalent is
   already in use.

   `skillSaveTier` writes a player character's skill tier. It stays on its
   existing route. Confirm before porting whether it is gated by
   `role_capacity_chokepoint.py` or `role_closed_vocab.py`; if either greps
   `index.html`, re-homing it belongs to this brief and is a deviation to
   report.

### Every commit

7. **Delete each ported function from `index.html`** in the commit that
   replaces it. Extend the island entry's `retiredPrefixes` in `registry.js`
   **by name** for every deleted identifier — `loadAgendasList`,
   `renderAgendaSheet` and the whole `pc*` family are not covered by an
   `intrigues` or `pj` prefix scan. Add a `BRIEF-0059-j` comment per block.
   Extend `graph_primitive.py`'s `GONE_PLAIN`.

8. **Prune `legacy_calls.baseline`** of anything closed; add nothing.
   `legacy_call.py` rule 4 enforces it. Expected net: 0.

## Scope OUT

- **The Review Queue.** `-k`.
- **The chrome.** `creationNewEntity`, `creationSaveDispatch`,
  `creationRefreshList`, `creationSelectRecord`, `creationOpenEntityFrom`,
  `creationResolveEntityTab`, `creationReturnToOrigin`,
  `creationRenderReturnControl` all stay. `-l`.
- **Unifying `intriguesDetachLink` with `GoalsEditor`'s detach.** Item 2.
- **Routing `pcCreateSubmit` through `/api/entities`.** Item 4. It would be a
  canon-write path change disguised as a refactor.
- **Generalising the two create panels.** Intrigues and pj are bespoke for
  different reasons — ordered steps versus a distinct endpoint. A shared
  create-panel abstraction over two dissimilar cases is the union type this
  ticket keeps refusing.
- **The `evenements` tab.** Already migrated; its `_evenementsTabEnterReset`
  is not this brief's.
- **Any backend change.** Frontend-only.

## Invariants to defend

- **Model proposes, code judges.** `intriguesGenerateDraft` and
  `pcGenerateDraft` fill forms the creator submits. Neither may acquire a
  path that writes without submission.
- **Single canon-write authority.** `/api/characters/player` stays the pj
  create route; agenda and step status changes stay on their existing routes.
- **Rule 11 pairing.** `primaryAction` and `createPanel` move together, in
  one commit, per tab.
- **Assign-then-read is forbidden** (`effect_self_write.py`). Step lists,
  linked-goal rows, owner options and the skill table are `$derived`.
- **The seam only shrinks.**

## Done means

- [ ] `legacy_call.py`, `creation_island.py`, `page_contract.py`,
      `effect_self_write.py` and `review_component.py` all exit 0 after every
      commit, with `review_component.py`'s allow-list unchanged.
- [ ] Scratch: split `createPanel: null` and the `primaryAction` change
      across two commits on either tab; `creation_island.py` rule 11 must
      bite; revert.
- [ ] `grep -c "loadAgendasList\|renderAgendaSheet\|intriguesRenderCreatePanel\|pjRenderCreatePanel\|pcCreateSubmit\|skillInit\|skillSaveTier" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] Live — intrigues: the list renders; open an agenda; its steps render
      with statuses; change an agenda status and a step status; detach a
      linked goal; the sheet refreshes.
- [ ] Live — intrigues: detach a goal-agenda link from the **entity sheet's**
      goals editor instead, then reopen the agenda; the link is gone there
      too.
- [ ] Live — intrigues: `+ Nouvelle intrigue` opens the create panel;
      generate a draft; submit; the new agenda appears in the list.
- [ ] Live — pj: `+ Nouveau` opens the bespoke create panel; load locations;
      generate a knowledge draft and apply it; submit; the character is
      created and appears in the pj list (and only there, not in the generic
      npc list).
- [ ] Live — pj: select an existing player character; the fiche slot renders
      its skills; change a tier and save; reselect and confirm persistence.
- [ ] Live — pj: switching between two characters updates the fiche without
      a stale row from the previous one.
- [ ] Live — switch worlds on both tabs; state resets as before.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`.
