# CHANGELOG

## TICKET-0010 — 2026-07-04 (no schema change)

CLAUDE.md rewritten to a law-only, budgeted file (1366 -> 467 lines) with a structural freshness contract (`tooling/verify/checks/claude_md_contract.py`); see `tooling/standards/ARCHITECTURE_DECISIONS.md`.

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

---

### Correctif : attribution entity_a_id des relation_change en contexte gathering

**Périmètre :** `src/world_engine/analyzer.py`, `src/world_engine/cockpit/app.py`.
Aucun changement de schéma.

#### Problème

`_normalize_to_schema` utilisait `conv.npc_id` comme valeur par défaut pour
`entity_a_id` dans les payloads `relation_change`.  En conversation gathering,
`conv.npc_id` vaut `None` (pas de PNJ unique propriétaire de la conversation) →
les mutations `relation_change` produites par `analyze_single_turn` portaient
`entity_a_id=None`, rendant ces lignes inutilisables.

#### Correctif

`_normalize_to_schema` reçoit un nouveau paramètre optionnel `npc_entity_id`
(`str | None = None`).  Quand il est fourni, il prend priorité sur `conv.npc_id`
comme valeur par défaut pour `entity_a_id` dans `relation_change`.  `conv.npc_id`
reste le fallback pour les conversations 1:1 existantes (rétrocompatible).

`analyze_single_turn` expose le même paramètre et le transmet à
`_normalize_to_schema`.

Les deux call sites dans `_stream()` sont mis à jour :
- Tour principal : `npc_entity_id=responder_id` (entity_id du PNJ qui a répondu).
- Tour initiative : `npc_entity_id=initiative_initiator_id` (entity_id du PNJ
  qui a pris l'initiative — capturé dans la variable `initiative_initiator_id`
  introduite en même temps).

#### Périmètre strict — autres types non corrigés

`_normalize_to_schema` utilise aussi `conv.npc_id` pour deux autres types, qui
présentent le même problème en gathering mais sont hors périmètre de ce correctif :
- `new_knowledge` : fallback `entity_id = conv.npc_id` quand le sujet n'est pas
  le joueur → `entity_id=None` pour une connaissance acquise par un PNJ gathering.
- `event_creation` : `involved_entities = [conv.player_id, conv.npc_id]` →
  `None` dans la liste pour les événements en gathering.

Ces deux cas ne sont pas corrigés ici ; ils doivent faire l'objet d'une tâche
séparée si les mutations `new_knowledge` et `event_creation` sont activées en
contexte gathering.

#### Pass final non affecté

`analyze_conversation` filtre tous les `relation_change` à la fin (ligne ~501) ;
même si `entity_a_id` était `None`, ces lignes ne seraient jamais proposées par
le pass final.

---

#### Scénario de test fondateur

Entrer dans la taverne (Reike en gathering, relation basse/nerveux). Jouer
agressif. Le vote MJ doit pouvoir déclencher Reike spontanément ; sa ligne
est narrée par le MJ avec un bubble visuel distinct (barre grise gauche +
préfixe ↩) ; son `gathering_member` reste inchangé.
