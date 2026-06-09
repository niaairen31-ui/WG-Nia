# CHANGELOG

## Addendum applicatif — 2026-06-09 (pas de bump de schéma)

### Initiative PNJ — Phase d'initiative dans /say (Palier 3, étape 1 — C1)

**Périmètre :** `scripts/seed_pilot.py`, `src/world_engine/cockpit/app.py`,
`src/world_engine/cockpit/index.html`. Aucun changement de schéma.

#### Nouvelles capacités

- **Phase 3 — Vote MJ (bon marché, non-streamé).**  
  Après la réponse du/des PNJ du tour et la narration MJ principale, un appel
  JSON léger demande au MJ si un PNJ bystander veut intervenir spontanément, et
  lequel. Sortie : `{"act": false}` ou `{"act": true, "npc": "<nom>"}`. Le nom
  est résolu contre les membres actifs du gathering (A2 — exact,
  insensible à la casse) ; non résolu → traité comme `act: false`.

- **Phase 4 — Génération (coûteuse, conditionnelle).**  
  Seulement si le vote retourne `act: true`. Le PNJ désigné produit une
  intervention en texte libre (parole, geste, interpellation). Contexte assemblé
  à frais (D1 — même pipeline que les répondants normaux). Ligne canonique
  persistée `speaker='npc'` / `speaker_id=<entity_id>` au `turn_order+3`.
  Narration MJ streamée au joueur puis persistée au `turn_order+4`.

- **Cadence E1.** Au plus un PNJ prend l'initiative par tour. Le répondant
  principal du tour est exclu du vote (il vient de parler).

- **Canal B1.** Texte libre (parole, geste, acte). Aucun vocabulaire d'actions
  typé. Narration MJ identique au flux normal (contrat verbatim).

- **Mutations D1.** L'acte lui-même ne crée aucune mutation. Ses conséquences
  passent par `_analyze_single_turn` (appel séparé, `player_line=""`, même
  pipeline).

#### Nouveau template de prompt

`pt-mj-initiative` (`usage='mj_initiative'`, `world_id=NULL`) — upsert via
`seed_pilot.py`. Signaux fournis au vote : mode interprété du tour joueur,
ligne joueur, et pour chaque PNJ sa relation vers le joueur (intensité + type)
et son `entity.status`. Pas de seuil codé en dur — jugement MJ.

#### Nouveaux événements SSE (avant `[DONE]`)

| Événement | Format |
|---|---|
| Annonce initiative | `{"initiative_start": {"npc_name": "..."}}` |
| Tokens narration initiative | `"<chunk>"` (même format que les tokens MJ normaux) |
| Ligne brute PNJ initiative | `{"initiative_npc_raw": "..."}` |

#### Préparation C2 (sans le construire)

- **(a)** `_active_members` est l'unique source de vérité pour les rosters ;
  docstring mise à jour.
- **(b)** Invariant d'unicité par-PNJ documenté dans le docstring de
  `_active_members`.
- **(c)** Le `gathering_member` du PNJ initiant ne bouge pas. C2 = lever
  uniquement cette restriction.

#### Scénario de test fondateur

Entrer dans la taverne (Reike en gathering, relation basse/nerveux). Jouer
agressif. Le vote MJ doit pouvoir déclencher Reike spontanément ; sa ligne
est narrée par le MJ avec un bubble visuel distinct (barre grise gauche +
préfixe ↩) ; son `gathering_member` reste inchangé.
