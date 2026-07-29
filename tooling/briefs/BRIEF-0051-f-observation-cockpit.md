# BRIEF — Step "observation cockpit surface"

## Context

TICKET-0051 decision P1, plus the F3 visibility requirement: proposals from an
observed run are structurally isolated from the Review Queue, and isolation is
not invisibility — the creator must see them somewhere.

**Correction to carry into execution.** The intake conversation described P1 as
"a top-level tab in `TAB_KEYS`". RECON shows that is wrong:
`TAB_KEYS` (`tooling/verify/checks/page_contract.py:11`) governs the
**Creation** SUB-tabs — `npc`, `pj`, `lieux`, ..., `queue`, `prompts` — rendered
as `creation-sub-tab` buttons calling `showCreationSubTab(...)`
(`index.html:1202-1215`), each requiring a `primaryAction` key in
`CREATION_TABS`. Observation is not an entity-CRUD surface and does not belong
there. The top-level mechanism is the `mode-tab` button — e.g.
`index.html:1050`, `mode-tab-creation` calling `showCreationView()`.

The DECISION (a top-level surface, sibling of Jouer and Creation, not a
sub-surface of Play, not a separate port) is unchanged. Only the registry it
lands in is corrected. **`TAB_KEYS` and `CREATION_TABS` are NOT touched by this
brief.**

Depends on -a and -e.

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. If a finding contradicts this brief,
STOP and escalate.

1. **Top-level surface mechanism** — enumerate every `mode-tab` button in
   `index.html`, the view-switch function each calls, and everything one such
   function does (show/hide, state reset, data load). Report the complete
   contract a new mode-tab must satisfy.
2. **`page_contract` scope** — confirm which of its rules apply to mode-tabs
   versus Creation sub-tabs, and confirm a new mode-tab requires no
   `TAB_KEYS` / `CREATION_TABS` entry. If any rule DOES bind mode-tabs, report
   it verbatim; this brief must satisfy it.
3. **Route registration** — how `cockpit/routes/*.py` modules are mounted, and
   the naming convention for a new one.
4. **HTMX vs fetch** — which pattern the newest surfaces use, so the new one
   matches rather than introducing a third style.
5. **`index.html` budget** — current line count (11 984 at RECON time) and
   whether any check caps it. Report the projected count after this brief.
6. **Prompts tab** — how a `PromptTemplate` body is displayed and edited,
   since the run detail shows the pinned `template_id` + `version` and should
   link rather than duplicate.
7. **Runner routes** — the exact routes shipped by -e.

## Scope IN

### 1. A new top-level Observation surface

A `mode-tab` sibling of Jouer and Création, satisfying the contract reported
by mini-RECON item 1. Four regions:

**a. Launch.** Pick a location; the present NPCs are listed. Set `max_beats`,
`quiescence_limit`, `mj_narration`, `cooldown_beats`, `debt_weight`,
`propensity_mode`. Start.

The readiness gate's refusals are shown as-is, naming the failed condition and
the NPC concerned. Never a generic "cannot start" — the gate exists to tell
the creator WHICH precondition failed.

**b. Transcript.** Beats in order. Each row shows its `outcome` with the three
states VISUALLY DISTINCT — `acted`, `silence`, `degraded` — plus `event` rows
from K2. `degraded` must never look like `silence`; that visual distinction is
the surface-level form of the ticket's central measurement claim.

Per beat, expandable: every candidate's intent row with `act`, `urgency`,
`why`, `call_status`, and the four arbitration components. The
`not_selected_reason` is DERIVED at display time by the precedence documented
in `world-engine-schema.md`, and is labelled as derived — it is not a stored
column and must not be presented as one.

**c. Run detail (L).** The pinned arbitration parameters and, per usage, the
`template_id` + `version`. This is the surface that makes two runs comparable;
without it the pinning columns have no reader.

**d. Observed proposals (F3 visibility).** For the selected run, the proposals
it produced, reached through `observation_mutation_link`. Read-only in this
brief: shown, grouped by type, with the beat that produced them.

### 2. Controls

Start, step one beat (B1), stop, and inject an event (K2) at the current beat.
Injection is a free-text field; the text is stored verbatim as the beat line.

### 3. Verify check `tooling/verify/checks/observation_surface.py`

- **Rule 1**: `index.html` declares the Observation mode-tab and its
  view-switch function; the contract from mini-RECON item 1 is satisfied.
- **Rule 2**: no `TAB_KEYS` entry and no `CREATION_TABS` entry named
  `observation` exists — the surface did not leak into the Creation registry.
- **Rule 3**: the transcript renderer references all four `outcome` values;
  `degraded` and `silence` resolve to different CSS classes. Assert the class
  names differ, not merely that both strings appear.
- **Rule 4**: the run detail renderer references the pinned parameter fields
  and the template pinning table — the L columns have a reader.
- **Rule 5**: `json_ui_boundary` still passes — arbitration parameters are read
  from real columns, never from a JSON blob.
- **Rule 6**: no route in the observation route module writes an
  `observation_*` row directly; all writes go through `observation_writes.py`
  via the runner.
- **Rule 7, vacuous-proof guard**: if zero renderer functions or zero
  `outcome` literals were collected, FAIL.

## Scope OUT

- **`TAB_KEYS`, `CREATION_TABS`, `showCreationSubTab`,
  `_buildRuntimeCreationTabs`, `_creationActivateTab`.** Untouched. The
  Creation surface is not modified in any way.
- **The Review Queue.** Not modified, not extended, not given an
  "observed" filter toggle. The exclusion is structural in -a; adding a UI
  toggle here would suggest it is a view preference.
- **Approving or rejecting observed proposals.** Read-only display. Whether an
  observed proposal should ever be promotable to canon is a real question and
  is NOT answered here — report it as an open item rather than building a
  button.
- **Editing prompt templates.** Link to the Prompts tab; do not duplicate the
  editor.
- **Metrics and charts.** BRIEF-0051-g. No aggregation in this brief beyond
  what a single run's rows show directly.
- **Real-time streaming.** A bounded run returns and the transcript is read
  cold (B2). No polling loop, no SSE.
- **The `index.html` split.** A standing future decision. This brief adds to
  the existing file in the existing style; it does not start a migration.
- **`play*.py` and the played surface.**

## Invariants to defend

- **No structure without a reader.** This brief IS the reader for -a's pinning
  columns and for `observation_mutation_link`. Rules 4 and the proposals
  region are how that is proven.
- **JSON storage for UI-visible data is prohibited.** Parameters come from
  columns.
- **Fail-closed over advisory.** Gate refusals are shown with their specific
  cause.
- **Single canon-write authority.** This surface writes nothing to canon and
  offers no approval path.
- **Derived, not stored.** `not_selected_reason` is computed for display and
  labelled as such.

## Done means

- [ ] The Observation surface opens from the top-level nav and the Creation
      and Jouer surfaces are unaffected.
- [ ] Starting a run against an under-populated location shows the specific
      failed condition and the NPC concerned.
- [ ] A completed 30-beat run renders with `acted`, `silence` and any
      `degraded` beats visually distinguishable at a glance.
- [ ] Expanding a beat shows all five candidates with their four arbitration
      components, and the derived reason is labelled as derived.
- [ ] The run detail shows the arbitration parameters and per-usage template
      id + version.
- [ ] The run's proposals are listed on the Observation surface and remain
      absent from the Review Queue.
- [ ] `python tooling/verify/checks/observation_surface.py` exits 0 with
      non-zero collected counts.
- [ ] `page_contract` and `json_ui_boundary` both pass; full-tree verify
      passes.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: subsection recording P1 with the registry
correction — Observation is a top-level mode-tab, NOT a Creation sub-tab, and
why (`TAB_KEYS` governs entity-CRUD sub-surfaces requiring a `primaryAction`).
Record F3 visibility: isolated from the queue, visible on its own surface,
read-only, with the promotion question logged as open.
`DECISIONS_INDEX.md` entry. `world-engine-schema.md` unchanged (no schema
change).
