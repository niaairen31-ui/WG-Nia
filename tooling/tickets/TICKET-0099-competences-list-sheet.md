---
id: TICKET-0099
title: Compétences on the shared list and fiche — container sizing, add-system button
type: bug
status: exec
created: 2026-09-30
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
lot_id: LOT-0099-competences-list-sheet.md
brief_ids: [A, B, C]
current_brief: C
schema_version_touched:
retry_count: 0
slug: competences-list-sheet
---

## Request (verbatim, as Nia stated it)

> Ticket 0099: Je suis en train de travailler a la création d'un monde pour
> faire des tests. Dans l'onglet création - compétences, lorsque je rentre 3
> Systèmes, je ne voie plus le reste des informations et je ne peux plus en
> créer d'autres. Je voudrais que le visuelle soit cohérent avec ce qui existe
> déja avec les autres entitées. ( liste a gauche avec fiche a droite lorsque
> j'en clique 1).

## Clarifications resolved (intake)

- The symptom is a layout defect, not a data one: `#creation-competences` has
  no sizing rule, so past one window of content nothing scrolls and the rest
  is clipped by `.app-view`. Registre and Sujets carry the same latent defect.
- No standalone stop-gap brief for the symptom: Nia runs every brief of the
  lot before replaying her test world.
- « + Ajouter un système » sits beside « + Ajouter une compétence » in the
  shell band — not in the list, unlike the NPC goals card.
- The assistant cannot live in the empty fiche: an empty fiche has no
  `sheetType`, and a branch chosen by `activeTabKey` is what CLAUDE.md forbids.

## Decisions locked (do not re-litigate without Nia)

- A2 — the tab is rebuilt as list + fiche; the missing container rule dies with
  its container.
- B1 — Compétences becomes a record tab on the shared editor area (the shared
  entity list and entity fiche), the fourth after Intrigues and Événements.
- C1 — the list groups skills under their system; each system is a row of its
  own that opens the system's fiche; « Sans système » trails, only when non-empty.
- G1 — the second button is a `secondaryAction` registry field: same island
  route as the primary action, plus a variant string.
- D2 + H1 — Brouillons (the assistant entry first, then every draft) and Trous
  du lexique are sections of the list; a gap click creates a draft and opens it.
- E1 — the shell's Save button saves every record but the assistant.
- F1 — every single-container Création tab sizes its container, enforced by a
  new check; Registre and Sujets are fixed in this ticket.
- R1 — the `competences` island entry is removed; its ledger line moves whole
  into `entitySheet`, and the registry header names the exception.

## Carried forward / open

- **A covered gap stays listed.** `GET /api/skill-gaps` counts every
  `unmatched` verdict ever recorded; creating the skill does not hide its gap
  (the prototype shows « Crochetage » in both the catalogue and the gaps).
  Options for Nia: filter gaps whose `surface_form` now matches a catalogue
  name, or keep the telemetry raw. Deserves its own ticket; reactivates the
  first time a covered gap misleads her.
- **`lieux` is not examined by the sizing check** (two containers). Reactivates
  if the room batch panel ever clips its own content.
- **Rejected layouts.** B2 (copy the layout's CSS classes) reactivates if
  `Sheet.svelte` nears its 1000-line cap; B3 (a generic list-and-fiche
  component) when a third non-entity tab wants the same layout.
- **Rejected buttons.** G2 (an `actions: [...]` list) reactivates when a second
  tab asks for a second button, or this tab for a third; G3 (the button in the
  list header) only if Nia asks.
- **Rejected assistant placements.** H2 (a third shell button) reactivates with
  G2; H3 (amending the `sheetType` invariant) is not reopened.
- **Unchanged behaviours, named.** Generating drafts replaces the current
  drafts (as before); edits to a draft are kept only by saving it (the entity
  fiche's own rule); the shell Save button reads « Save » (pre-existing chrome).

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every single-container Création tab sizes its container  -> verify/checks/creation_container_sizing.py
- [ ] Compétences is a record tab on the shared shell; one « Ajouter » label each  -> verify/checks/page_contract.py
- [ ] Island registry, routed actions and secondaryAction pairing hold  -> verify/checks/creation_island.py
- [ ] The fiche picks its branch from sheetType, competences included  -> verify/checks/creation_tab_switch.py
- [ ] Stylesheets stay partitioned and their built copies fresh  -> verify/checks/stylesheet_partition.py
- [ ] Modal.svelte stays the one dialog primitive  -> verify/checks/modal_primitive.py
- [ ] No $effect reads a binding it just wrote  -> verify/checks/effect_self_write.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] The frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Every ticket's front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus runs green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] Test world: the Compétences tab shows the list on the left and the fiche
      on the right; with three systems or more, every row is reachable (the
      list scrolls) and both shell buttons stay visible.
- [ ] Clicking a system opens its fiche; renaming it and saving updates the
      list. Clicking a skill opens its fiche; moving it to another system and
      saving moves it under that system.
- [ ] « + Ajouter une compétence » opens a blank skill fiche; Save creates it.
      « + Ajouter un système » opens a blank system fiche; Save creates it.
- [ ] « ✦ Générer avec l'assistant » opens the assistant; a generation fills
      Brouillons; a draft opened, corrected and saved lands in the catalogue;
      « Retirer du brouillon » drops one.
- [ ] A gap click opens a draft named after it; saving without a domain is
      refused with « Domaine de base requis. ».
- [ ] Deleting a skill asks for « Oui »; deleting a system that still holds
      skills is refused inside the dialog; an empty system is deleted.
- [ ] Registre and Sujets scroll when their content is longer than the window.
- [ ] NPC, Intrigues and Événements still open and save as before.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
