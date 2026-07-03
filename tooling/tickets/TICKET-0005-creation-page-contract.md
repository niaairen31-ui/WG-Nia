---
id: TICKET-0005
title: Uniform config-driven page contract for Création sub-tabs
type: feature
status: live-gate
created: 2026-07-02
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # frontend-only; no canon-write path, no schema change expected
blast_radius: medium      # touches the layout of every Création sub-tab
brief_ids: [BRIEF-0005-a, BRIEF-0005-b, BRIEF-0005-c]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> « dans mes différents onglets disponible lorsque je suis en mode créateur,
> j'ai remarqué que les pages créées au même moment (Ex: NPC et lieux) sont
> très similaires (ex : le + nouveau est en haut à gauche et lorsque je clique
> dessus il m'affiche un peu la même chose). Alors que les onglets créés plus
> tard (ex : personnage joueur) sont différents. [...]
> Comportement désiré : il devrait toujours y avoir les mêmes choses pour
> toutes les pages ; la même fonctionnalité devrait toujours être à la même
> place dans chaque page par défaut. Plus tard, je vais pouvoir ajouter des
> fonctionnalités parmi lesquelles choisir et ajouter des pages facilement. »

## Clarifications resolved (intake)

- **Diagnosis (intake analysis):** divergence is frontend accretion — no shared
  page template exists; each Création sub-tab is hand-written per chantier.
  Backend endpoint heterogeneity (generic `GET /api/entities` for NPC/Lieux/
  Factions/Objets vs dedicated PJ routes) is legitimate and **stays untouched**;
  it enabled the drift but does not force it.
- **B2 (locked):** full config-driven page template, not surface harmonization.
  A tab-config registry + one shared render path; convergence becomes
  structural — a page *cannot* place its `+ Nouveau` elsewhere. Tab-specific
  features (Fiche, discoverable details, Lieux hierarchy browse) live in
  declared slots, never in place of the standard layout.
- **C1 (locked):** Personnage joueur conforms fully to the template; the skill
  Fiche becomes a slot (`extraSlots`), not a documented exception.
- **Priority:** pipeline glue is complete; this is the first full-pipeline
  test ticket (RECON → brief(s) → exec → verify → live gate).

## Open decisions (to be locked post-RECON, pre-brief — never embedded in a brief)

- **D — contract perimeter:** D1 = six entity pages (NPC, PJ, Lieux, Factions,
  Objets, Artefacts), Review Queue explicitly out of contract; D2 = all seven.
  Intake recommendation: D1.
- **E — deferred A2 (Fiche follows list selection):** E1 = folded into this
  ticket via the template's list-selection → detail contract; E2 = stays a
  separate debt. Intake recommendation: E1, pending RECON confirmation that
  the `skillCharacters[0]` binding is the only rewire point.
- **F — rendering mechanism:** decide after RECON maps the current rendering
  reality (vanilla JS / HTMX / file layout). Minimal-first default: a render
  function + config registry inside the existing stack, no new dependency.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] A single tab-config registry exists; every in-contract Création sub-tab
      is a registry entry rendered through the shared render path
      -> verify/checks/page_contract.py
- [ ] No in-contract sub-tab defines standard-layout markup (its own
      `+ Nouveau` control or create-panel shell) outside the shared render
      path -> verify/checks/page_contract.py
- [ ] No canon-write path, schema file, or `writes.py` helper is touched by
      the diff -> existing verify checks remain green

### Live  ->  human gate (Nia)
- [ ] Every in-contract sub-tab shows `+ Nouveau` at the same position; the
      create panel opens with the same shape and behavior on every page
- [ ] Tab-specific blocks (PJ Fiche, Lieux discoverable details + hierarchy
      browse, etc.) render in slots below/beside the standard layout without
      displacing it
- [ ] Existing flows unchanged in a live session: create an NPC, create a
      lieu, browse the Lieux hierarchy, create a PJ (toggle behavior of
      BRIEF-60 preserved), edit skills on the Fiche
- [ ] Adding a hypothetical new page = adding one registry entry (spot-checked
      by reading the config, not by building one)
