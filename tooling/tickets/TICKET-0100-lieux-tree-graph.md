---
id: TICKET-0100
title: Lieux — in-place tree, « + lot » beside « + Nouveau », graph node selection
type: bug
status: exec
created: 2026-10-01
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
lot_id: LOT-0100-lieux-tree-graph.md
brief_ids: [A, B, C]
current_brief:
schema_version_touched:
retry_count: 0
slug: lieux-tree-graph
---

## Request (verbatim, as Nia stated it)

> Ticket 0100, live gate 0099 faite. Je suis en train de me créer une monde
> pour jouer dedans (Aestia). J'ai fait les compétences et je suis rendu aux
> lieux. Selon moi, il faut revoir quelques petites choses. Premièrement, je
> pense qu'il dois y avoir une différence entre les lieux ''parents'' et les
> lieux ''enfants''. Selon moi, les les seul lieux qui peuvent être visité
> sont des lieux qui n'ont pas de parents. Dans mon cas, j'ai la secte du
> Phoenix qui est un district (quartier) et plusieurs lieux enfants qui sont
> des lieux visitable dans le quartier. (atelier d'alchimie, intendance,
> pavillon des disciples, terrain d'entrainement. Si tu es dans l'une de ses
> places, tu es dans le quartier, mais si le joueur va directement dans le
> quartier, cela fait moins de sens. Deuxième chose, je veux que la section a
> gauche soit conforme a la section de gauche des autres. Troisièmement, Le
> graphique ne fonctionne pas comme il est supposé fonctionné. en bas c'est
> écrit cliquez un neud sélectionner, puis un second pour le connecter.
> Lorsque je clique sur noeud, il ne deviens pas sélectionné (et sa fiche ne
> s'affiche pas dans la section en bas a droit). Je ne peux donc pas lié les
> lieux par les graphique. Je veux pouvoir le faire.

On the left panel, later in the planning conversation:

> E j'aimerais que si je clique sur le ''3 enfants'', cela ne change pas ma
> barre, cela ajoute le nom des enfants, avec une indentation, mais je
> continue a voir le reste des nom. Si je re-click le ''3 enfants'' ils
> redispersaient et j'ai mon ''arboraissance allégé''. F1, mais il se met en
> deuxième bouton a coté de + nouveau. ''+ lot''.

## Clarifications resolved (intake)

- The request holds three asks. The first (zones vs visitable places) is
  carried by TICKET-0101; this ticket carries the second and the third,
  plus the room batch trigger the second displaces. Nia confirmed the split
  (I2).
- The graph defect is in the shared primitive, not in the Lieux consumer:
  a node's own `click` bubbled to the canvas handler, which cleared the
  selection in the same gesture. Measured in headless Chromium on `main`:
  no node ever stays selected, on the Lieux graph and on the relations
  graph's « Lier » arm alike (LOT R-01, R-02).
- « la section de gauche conforme aux autres » means the shared list rows
  (`.author-list-item`: name, meta line, the selected row highlighted),
  not a flat list: the hierarchy stays, unfolded in place.
- The typed buckets (Villes, Quartiers, …) disappear: they key on a fixed
  English list that a world's own location types never match (R-11). The
  type moves into each row's meta line. « Actifs seulement » stays. Nia
  confirmed both.
- « Générer un lot ici » lived in the descent view, which is removed; it
  becomes the « + lot » shell button, anchored on the location open in the
  fiche.

## Decisions locked (do not re-litigate without Nia)

- G1 — the graph primitive stops a node's click from reaching the canvas;
  the Lieux consumer declares `onNodeClick`, which opens that location's
  fiche. Both taps of a connection open a fiche: the second one stays open.
- E — the Lieux list is one tree on the shared rows; « N enfant(s) » unfolds
  the children in place, one indentation step deeper; a second click folds
  them; the rest of the list never moves. No breadcrumb, no descent, no
  typed buckets; « type · status » as meta; « Actifs seulement » kept.
- F1 + F-a — « + lot » is a second shell button beside « + Nouveau », a
  `secondaryAction` routed through `entitySheet` with the variant `'batch'`;
  it anchors the room batch on the saved location the fiche shows.
- I2 — two tickets. Zones, `borde`, the automatic promotion and the three
  graph modes are TICKET-0101.

## Carried forward / open

- **TICKET-0099's G2 condition fired** (a generic `actions: [...]` list, to
  reactivate "when a second tab asks for a second button"). Drafted as
  answered: Lieux needs exactly one extra button, which `secondaryAction`
  carries; G2 now reactivates when one tab asks for a third button. Flagged
  to Nia at delivery; reversing it regenerates brief B only.
- **A location opened from the graph is not revealed in the list** when one
  of its ancestors is folded: the fiche opens, no row is highlighted.
  Options: unfold the ancestors on selection, or leave it. Reactivates the
  first time Nia loses a location that way. Own ticket if taken.
- **Folding a parent hides a selected child row**; the fiche stays open.
  Same reactivation as above.
- **A class applied with no stylesheet rule passes `stylesheet_partition.py`.**
  Measured while drafting brief C: renaming `.lieux-children-btn` on its
  button left the check green — rule 7 only covers class names the legacy
  inline sheet also uses. Not this ticket's defect; deserves its own
  ticket if Nia wants every applied class proven styled.
- **Everything zone-related** — the visitable/zone rule, `borde`, the
  promotion dialog, the graph's three modes — is TICKET-0101.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] A node press never reaches the canvas; the primitive stays the one graph  -> verify/checks/graph_primitive.py
- [ ] Island registry, routed actions and secondaryAction pairing hold (2 paired)  -> verify/checks/creation_island.py
- [ ] The recursive location-tree render stays LocationTree.svelte's alone  -> verify/checks/location_tree.py
- [ ] Every Création page stays a registry entry, no tab-specific branch  -> verify/checks/page_contract.py
- [ ] The fiche picks its branch from sheetType  -> verify/checks/creation_tab_switch.py
- [ ] Stylesheets stay partitioned and their built copies fresh  -> verify/checks/stylesheet_partition.py
- [ ] No $effect reads a binding it just wrote  -> verify/checks/effect_self_write.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] The frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Every ticket's front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus runs green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] Lieux, « Voir le graphe »: clicking a node highlights it and opens its
      fiche below; clicking a second node draws the connection and leaves
      the second node's fiche open; clicking a connection still offers to
      delete it; dragging a node still moves it.
- [ ] NPC, « Voir le graphe », Global then « Lier »: two node clicks open the
      « Nouveau lien » form.
- [ ] Lieux list: only the top-level locations show at first, each as a
      standard row (name, « type · status »); « 4 enfants › » under the
      Secte du Phoenix unfolds its four children indented beneath it while
      the other rows stay; a child with children unfolds one step deeper;
      clicking « 4 enfants ⌄ » folds them again.
- [ ] Clicking a row (any depth) opens its fiche and highlights the row;
      « Actifs seulement » still hides inactive locations.
- [ ] The Lieux band shows « + lot » then « + Nouveau ». With a saved
      location open, « + lot » opens the room batch panel anchored on it;
      with no location open, the fiche's status line reads « Ouvrez un lieu
      pour y générer un lot. » and nothing opens.
- [ ] The NPC band shows only « + Nouveau »; Compétences still shows
      « + Ajouter un système » then « + Ajouter une compétence ».

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
