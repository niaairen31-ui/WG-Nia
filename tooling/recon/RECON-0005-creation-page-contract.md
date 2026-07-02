# RECON — Création sub-tab layout map (page contract groundwork)

Ticket: TICKET-0005. Report-only. Findings are never acted on during this
RECON — no fix, no refactor, no "while I'm here." Every finding carries a
`file:line` citation against the live codebase. Output: a findings report
deposited per pipeline convention.

## Purpose

TICKET-0005 will introduce a config-driven page template for the Création
sub-tabs (decision B2) with tab-specific features as slots (C1). Before any
brief is written, map the current reality of all seven sub-tabs so the slot
contract is derived from what exists, not guessed.

## Questions to answer (all seven sub-tabs: NPC, Personnage joueur, Lieux, Factions, Objets, Artefacts, Review Queue)

1. **Rendering reality.** For each sub-tab: where does its markup live
   (static HTML, JS-built DOM, HTMX fragment)? Which function(s) render it?
   One shared file or several? Cite `file:line` for each tab's entry point.
2. **`+ Nouveau` inventory.** For each tab that has one: exact element,
   position in the layout, the handler it triggers, and what opens (inline
   panel, modal via `genericModalOpen`, collapsed block like
   `#pj-create-block`). Note tabs that have no create control (expected:
   Artefacts, Review Queue) and why.
3. **List → detail binding.** For each tab: which endpoint feeds the list,
   what happens on list-item click, and where the detail/edit panel gets its
   data. Specifically confirm or refute that the PJ Fiche is bound to
   `skillCharacters[0]` and identify every site that would need rewiring for
   list-selection binding (deferred A2 / open decision E).
4. **Endpoint map.** Per tab: list endpoint, create endpoint, edit/update
   endpoint(s). Flag which tabs share the generic entity CRUD and which use
   dedicated routes. (Backend is out of scope for change — this map exists so
   the tab-config schema knows what shapes it must absorb.)
5. **Slot candidates.** Enumerate every tab-specific block that is neither
   the list nor the standard create panel: PJ Fiche (`#skill-main`), Lieux
   discoverable-details editor, Lieux hierarchy browse (breadcrumb rail,
   "Actifs seulement" toggle), faction roles editor, anything else found.
   For each: where it renders today and what data/state it depends on.
6. **Shared state & refresh.** What client state each tab holds (e.g.
   `lieuxBrowseParentId`, `pjCreateOpen`, `regionManifest`-style globals),
   what resets on tab activation, and what the world-switch refresh
   (BRIEF-48) touches per tab — the template must not break either.
7. **Existing shared helpers.** Any function already used by 2+ tabs
   (modal helpers, list renderers, fetch wrappers) that the template should
   absorb rather than duplicate.
8. **Divergence catalogue.** A concise table: per tab, where its layout
   deviates from the NPC/Lieux pattern (button position, open behavior,
   panel shape). This is the direct answer to the observed problem.

## Explicitly out of scope during this RECON

- Any code change, however small (including the A2 rewire).
- Any backend/route change or opinion on merging endpoints.
- Designing the tab-config schema itself — that happens at brief time, from
  these findings.
- Review Queue redesign: it is mapped (question 1–3 coverage) solely to
  inform open decision D (in or out of contract); no proposal beyond the map.

## Report format

Findings grouped by question number, `file:line` on every claim, ending with
a one-paragraph "surprises" section for anything the questions did not
anticipate. No recommendations section — decisions D, E, F are locked in
chat afterwards, from this map.
