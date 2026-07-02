# BRIEF — Step "Standard shell for bespoke Création tabs"

Ticket: TICKET-0005. Brief c of c. Depends on briefs -a and -b. Anchors
from RECON-0005 result; re-anchor against the post-(-b) tree.

## Context

D′2-shell (locked): every Création page — entity or bespoke — renders under
one standard shell: the tab title plus a single, fixed-position primary-
action zone. The entity archetype got this in -a/-b. Four bespoke tabs
still place their primary gesture ad hoc: Compétences' inline add-row
control (index.html:1312-1314), Registre's always-open add form
(index.html:1339-1370), Région's wizard entry, Review Queue's filter/batch
controls in the body. After this brief, "the same functionality is always
in the same place" holds on all ten pages, and any future archetype
inherits the shell by construction.

## Scope IN

1. **Shell renderer.** New `renderCreationShell(entry)` called by the
   dispatcher for every tab: a header band above the tab body containing
   the entry's `label` (title) and, iff the entry declares
   `primaryAction: { label, handler }`, exactly one button in a fixed
   position (same position for all ten tabs; for entity entries this IS the
   existing `+ Nouveau`, re-expressed as `primaryAction` so entity and
   bespoke share one mechanism — `#creation-new-row`'s markup becomes the
   shell band). Registry entry contract comment (from -a) is updated to
   replace `createPanel` presence-implies-button with:
   `primaryAction: {label, handler} | null` (entity default:
   `{ label: '+ Nouveau', handler: <createPanel opener> }`).
2. **Compétences.** Remove the in-body "+ Ajouter une compétence" control
   (index.html:1312-1314); the competences entry declares
   `primaryAction: { label: '+ Ajouter une compétence', handler:
   <existing blank-row push> }`. Inline-editable table body unchanged.
3. **Registre.** The always-visible add form (index.html:1339-1370)
   becomes collapsed by default; the registre entry declares
   `primaryAction: { label: '+ Nouvelle entrée', handler: <toggle form
   visibility> }`. `authorAddLedgerEntry()` (index.html:3240) and the
   append-only `POST /api/ledger` path unchanged; after a successful
   append the form collapses again.
4. **Région.** The region entry declares `primaryAction: { label:
   'Nouvelle région', handler: <regionRestart() then focus the brief
   input> }` (`regionRestart` per RECON/BRIEF-38 nulls
   `regionManifest`/draft state). The wizard body (brief → manifest →
   draft → commit) is otherwise untouched.
5. **Review Queue.** `primaryAction: null` (rows are never created here —
   append-only by design, RECON question 2). The status filter and the
   batch bar move into the shell band's right side (markup relocation
   only; `loadQueue`, batch endpoints, card rendering unchanged).
6. **Artefacts.** `primaryAction: null` (already degenerate from -a); the
   shell title renders like everywhere else. When artifact creation ships
   backend-side, enabling it = filling `primaryAction` on this entry.
7. **Verify check extension.** `page_contract.py` adds: (f) every
   `CREATION_TABS` entry contains a `primaryAction` key (value may be
   null); (g) the legacy in-body control strings
   (`Ajouter une compétence` outside the registry literal, the Registre
   form's always-open state) are gone — concretely: the Registre form
   element carries the collapsed-by-default class/attribute in static
   markup.

## Scope OUT

- **A `catalogue` archetype** unifying Compétences/Registre table bodies —
  a future chantier if a third table page appears; this brief touches only
  their shell, never their body rendering.
- **Any Review Queue workflow change** (statuses, batch semantics, card
  layout).
- **Any Région wizard-flow change** beyond the entry-point button.
- **Secondary actions in the shell** (filters as a generic shell concept,
  action menus): the queue's filter relocation is a one-off markup move,
  not a shell API.
- **Backend**: `POST /api/ledger` (append-only), skill-definition CRUD,
  region routes, mutation routes — all untouched.

## Invariants to defend

- **No canon-write path touched** (frontend-only diff).
- **Ledger append-only posture**: the Registre change is visibility only;
  no edit/delete affordance may appear on existing rows.
- **Structural over disciplinary**: after this brief the shell is the only
  place a primary action can render — a future page cannot put its main
  button elsewhere because no other mechanism exists.

## Done means

- [ ] Live: all ten tabs show the shell header; every tab that has a
      primary action shows it at the identical position (visual sweep
      across the ten tabs in one session)
- [ ] Live: Compétences — add a skill via the shell button, edit inline,
      save: unchanged end state
- [ ] Live: Registre — form hidden on entry; shell button opens it; a
      successful append collapses it; ledger table renders the new row
- [ ] Live: Région — shell button resets to a fresh brief input with focus;
      an in-progress draft is discarded only via this explicit gesture
- [ ] Live: Review Queue — filtering and batch approve/reject work from the
      shell band exactly as before
- [ ] `page_contract.py` passes including (f)/(g); full verify suite green;
      /review-step and /close-step run

## Docs to update

- ARCHITECTURE_DECISIONS.md: close the "CRÉATION PAGE CONTRACT" section —
  D′2-shell fully realized; record the `primaryAction` contract and the
  Registre collapsed-by-default decision; note the deferred `catalogue`
  archetype with its trigger condition (a third table-shaped page).
- CLAUDE.md: amend the -a convention line to mention the shell — "…rendered
  by the generic dispatcher under the standard shell; a page's primary
  action exists only as its registry `primaryAction`."
- No schema change; no changelog entry.
