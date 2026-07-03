# BRIEF — Step "Personnage joueur migrates to the entity archetype"

Ticket: TICKET-0005. Brief b of c. Depends on brief -a (registry +
dispatcher + entity archetype installed). `file:line` anchors from
RECON-0005 result; line numbers refer to pre-(-a) state and must be
re-anchored against the post-(-a) tree at execution.

## Context

PJ is the divergence that motivated the ticket: its own create button
(`#pj-create-new-btn`, index.html:1215) inside the Fiche block, the
standard `#creation-new-row` hidden for this tab (index.html:2982), a
collapsed create block (`#pj-create-block`, index.html:1217) with a
dedicated form and endpoint, and a hardcoded `pj` branch inside the shared
`authorSelectEntity` (index.html:4945-4949). Locked: C1 (PJ conforms fully;
Fiche is a slot) and E′1 (list-selection → slot wiring via a declared
`onSelect` hook, no tab-name conditionals in shared code).

## Scope IN

1. **Standard create control.** Stop hiding `#creation-new-row` for the pj
   tab (remove the special-case from the pj entry's activation config).
   `+ Nouveau` (`#creation-new-btn`) becomes PJ's only create control. The
   pj registry entry declares `createPanel: pjRenderCreatePanel` — a new
   function rendering the existing create form (fields exactly as today:
   name, starting-location dropdown, description/appearance/backstory,
   index.html:1233-1256, plus the AI-draft control `pcGenerateDraft()`
   index.html:5396 and its knowledge read-only list) into the detail region
   (`#author-main`), the same region where other tabs open their new-entity
   sheet. Submit path unchanged: `POST /api/characters/player`
   (index.html:5328; app.py:1123), re-bootstrap on success.
2. **Remove the parallel create machinery.** Delete `#pj-create-new-btn`,
   `#pj-create-block` as a separate collapsed block, `pjCreateNew()`
   (index.html:5378), and the `pjCreateOpen` state (index.html:5376) plus
   its `onTabEnter` reset. The BRIEF-60 *behavior* is preserved by the
   archetype itself: the Fiche is visible by default on tab entry, and the
   create form appears only after the creator clicks `+ Nouveau` —
   identical guarantee, standard mechanism.
3. **Fiche as declared slot (C1).** The pj entry declares
   `slots: [{ id: 'fiche', containerId: 'creation-pj-skill', loader:
   skillInit, onSelect: pjFicheOnSelect }]`. The `#creation-pj-skill` block
   (index.html:1208-1276) keeps its markup (character selector, mode
   toggle, `#skill-main`) minus the create form/button removed in item 2;
   it renders by default on tab entry (slot loader runs on activation —
   Fiche stays outside the create gate, as today).
4. **E′1 — generic onSelect hook.** In `authorSelectEntity(id)`
   (index.html:4939), after the detail fetch/render, iterate the active
   entry's `slots` and call each non-null `onSelect(id)`. Delete the
   hardcoded branch at index.html:4945-4949. New `pjFicheOnSelect(id)` does
   exactly what the deleted branch did: sync `#skill-character-select` to
   `id` and call `skillSelectCharacter(id)` (index.html:1266 dropdown
   behavior unchanged; `skillCharacters[0]` remains the initial/fallback
   default per index.html:5439-5443 — that logic is correct and untouched).
5. **Verify check extension.** `verify/checks/page_contract.py` adds: (d)
   the string `currentCreationSubTab === 'pj'` is absent from index.html;
   (e) the identifiers `pjCreateOpen` and `pjCreateNew` are absent.

## Scope OUT

- **Any change to the create endpoint or payload** — `POST
  /api/characters/player`, the one-PC-per-world invariant, skill-row
  seeding, and `generate_player_draft` are all untouched.
- **Fiche internals** — `skillRender`, `skillSelectCharacter`,
  `PATCH /api/skills/{id}`, the mode toggle: no change beyond the removal
  of the create block from the same container.
- **Multiple PCs, PC deletion/editing lifecycle, PC switcher** — still the
  standing deferrals from BRIEF-45/46.
- **Generalizing `onSelect` beyond slot hooks** (e.g., event bus,
  pub/sub): one loop over the entry's slots, nothing more.
- **Bespoke-tab shell** — brief -c.

## Invariants to defend

- **No canon-write path touched** (frontend-only diff, same rule as -a).
- **One PC per user per world** stays structurally defended by
  `idx_character_one_pc_per_user_world` — nothing in this brief may add a
  second client path to PC creation; there must be exactly one create
  affordance after the change.
- **Structural over disciplinary**: shared helpers contain no tab-name
  conditionals after this brief (verify-enforced).

## Done means

- [ ] Live: entering Personnage joueur shows the Fiche immediately (no
      click), list on the left, `+ Nouveau` top of sidebar — same position
      and look as NPC/Lieux/Factions/Objets
- [ ] Live: `+ Nouveau` opens the PJ create form in the detail region; AI
      draft, edit, submit → PC created, skills seeded, bootstrap refreshed
      (unchanged end state vs BRIEF-46/52 flow)
- [ ] Live: clicking a PC in the sidebar list loads its sheet AND switches
      the Fiche to that PC (dropdown syncs) — behavior identical to the
      deleted hardcoded branch
- [ ] Live: creating a second PC in the same world still fails exactly as
      before (invariant untouched)
- [ ] `page_contract.py` passes including the new (d)/(e) assertions;
      full verify suite green; /review-step and /close-step run

## Docs to update

- ARCHITECTURE_DECISIONS.md: extend the "CRÉATION PAGE CONTRACT" section —
  C1 realized (Fiche as slot), E′1 realized (onSelect hook contract, the
  pj branch removed), BRIEF-60 gate superseded by the archetype's standard
  create gesture with the same visible-by-default guarantee.
- No schema change; no changelog entry.
