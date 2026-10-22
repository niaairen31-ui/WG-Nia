"""The deferrals the creator watches: each rejected or deferred choice whose reactivation condition she approved, where it is declared, and the dashboard metric that watches it, if any (TICKET-0115, BRIEF-0115-D; decisions F2, K2 and L of the conditions series' dashboard).

`DEFERRALS` is written by hand, entry by entry, from the choices Nia named
(L): a deferral enters this list only when a ticket's lot names it, never
by a scan of the decision registry. Each entry carries:

- `code`, `ticket`: the decision code and the ticket that locked it;
- `deferred_fr`, `condition_fr`: what waits, and when it comes back, in
  French for the « Suivi » tab;
- `source`, `anchor`: the file that declares it and a verbatim passage of
  it -- `dashboard_registry.py` (the check) finds the anchor there once, so
  a reworded or moved declaration is a red gate, never a stale line;
- `metric`: the key of the `dashboard_metrics.METRICS` entry that watches
  the condition, `EXPORT` when only the export can measure it (M1: the tab
  reads no JSON column), or None when no data can;
- `status`: `open`, or `reached` -- the condition is met and the decision
  is Nia's -- with `follow_up`, the ticket reserved for it, if any.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

EXPORT = "export"
DEFERRAL_STATUSES: tuple[str, ...] = ("open", "reached")


@dataclass(frozen=True)
class Deferral:
    code: str
    ticket: str
    deferred_fr: str
    condition_fr: str
    source: str
    anchor: str
    metric: Optional[str] = None
    status: str = "open"
    follow_up: Optional[str] = None


_T0111 = "tooling/tickets/TICKET-0111-condition-language.md"
_T0112 = "tooling/tickets/TICKET-0112-condition-interpreter.md"
_T0113 = "tooling/tickets/TICKET-0113-world-state.md"
_T0114 = "tooling/tickets/TICKET-0114-event-journal.md"
_T0119 = "tooling/tickets/TICKET-0119-event-producers.md"
_T0121 = "tooling/tickets/TICKET-0121-journee-quest-designer.md"
_T0124 = "tooling/tickets/TICKET-0124-world-premise.md"
_DECISIONS = "tooling/standards/ARCHITECTURE_DECISIONS.md"
_JSON_BOUNDARY = "tooling/verify/checks/json_ui_boundary.py"

DEFERRALS: tuple[Deferral, ...] = (
    Deferral("D2", "TICKET-0111",
             "Appliquer d'office les événements proposés par le MJ.",
             "Le taux d'acceptation tel quel des événements proposés est assez haut.",
             _T0111, "D2 (auto-applied; reactivation: an acceptance rate measured high enough under D1)",
             metric="event_reviews"),
    Deferral("M2", "TICKET-0111",
             "Une étape s'accomplit seule quand sa condition d'accomplissement est vraie.",
             "Le tableau de bord montre que Nia confirme ce que la condition dit déjà.",
             _T0111, "M2 (completing on its own; reactivation: a dashboard metric showing Nia confirms what "
                     "the condition already says)",
             metric="step_verdicts"),
    Deferral("A1", "TICKET-0119",
             "Le tick propose de nouveaux types d'événements.",
             "Nia retype souvent les événements proposés par le tick.",
             _T0119, "Reactivation: the dashboard (0115) shows the creator retyping the tick's domain-typed "
                     "events often.",
             metric="tick_retyped"),
    Deferral("Q2", "TICKET-0111",
             "Des champs explicites pour le PNJ de journée et les faits à approfondir.",
             "Une étape dont le PNJ de journée n'est la cible d'aucune relation atteinte par « toutes ».",
             _T0111, "Q2 (explicit step fields; reactivation: a step whose day's NPC is not the target of a "
                     "relation)",
             metric="steps_without_day_npc"),
    Deferral("absence", "TICKET-0114",
             "Une forme dédiée « sans être repéré ».",
             "Le tableau de bord montre le besoin : beaucoup de « non » sur un événement.",
             _T0114, "a dedicated form only if the dashboard shows the need.",
             metric="absence_leaves"),
    Deferral("A2", "TICKET-0111",
             "Des conditions écrites en SQL généré.",
             "Une condition réelle que l'arbre ne peut pas exprimer, même avec une nouvelle primitive.",
             _T0111, "A2 (generated SQL; reactivation: a real condition the tree cannot express even with a "
                     "new primitive)",
             metric=EXPORT),
    Deferral("F2", "TICKET-0111",
             "Une table « acte » à côté du journal d'événements.",
             "Un ralentissement mesuré de la chronique par le volume des traces.",
             _T0111, "F2 (a second table « acte »; reactivation: a measured slowdown of the chronicle by the "
                     "volume of traces)"),
    Deferral("IA2", "TICKET-0112",
             "L'interprète traduit aussi les coûts et les récompenses.",
             "Le journal de l'interprète montre Nia tapant des coûts dans l'interprète.",
             _T0112, "IA2 (terms too: a second judge; reactivation: the journal shows the creator typing costs "
                     "into the interpreter)",
             metric=EXPORT),
    Deferral("ID1b", "TICKET-0112",
             "Les offres de quête dans l'index des noms.",
             "Une offre de quête devient une entité.",
             _T0112, "ID1b (offers and skills in `name_index`; reactivation: a quest offer becomes an entity)"),
    Deferral("libellé", "TICKET-0113",
             "Ajouter depuis l'interprète un libellé qui manque à un état existant.",
             "Des propositions refusées parce que l'état existant n'a pas le libellé.",
             _T0113, "Reactivation: `condition_draft` rows whose `errors` name « n'est pas un libellé de ».",
             metric=EXPORT),
    Deferral("effets/sorte", "TICKET-0119",
             "Un effet qui vise une sorte (« les loups de Brume sont enragés »).",
             "Un type dont l'effet vise un rôle qui accepte une sorte, et Nia qui le demande.",
             _T0119, "Reactivation: a type whose effect targets a role that accepts a sorte, and the creator "
                     "asking for it."),
    Deferral("WH3", "TICKET-0113",
             "Un état visible lisible par un joueur sur les autres.",
             "Le journal d'événements sait qui a été témoin d'un changement.",
             _T0113, "WH2, WH3 (reactivation: TICKET-0114's journal knows who witnessed a change).",
             status="reached", follow_up="TICKET-0122"),
    Deferral("payload", "TICKET-0025",
             "Rendre relationnel le payload d'une proposition.",
             "Une interface le lit champ par champ : la carte de revue l'édite depuis TICKET-0119.",
             _JSON_BOUNDARY, "First structured UI consumer must relationalize.",
             status="reached"),
    Deferral("A1'b", "TICKET-0104",
             "Limiter `rencontre` aux paires de personnages.",
             "Une mesure de prod ne montre aucune paire `rencontre` hors deux personnages.",
             _DECISIONS, "Reactivates if a production measurement shows no `rencontre` pair involving anything "
                         "but two characters.",
             metric="rencontre_pairs"),
    Deferral("P2", "TICKET-0101",
             "Faire passer toute écriture de lieu par `write_character_location`.",
             "Un septième site d'écriture apparaît (le contrôle (c) de `zone_placement.py` échoue).",
             _DECISIONS, "Reactivates when a seventh write site appears (`zone_placement.py` (c) fails on it)."),
    Deferral("C3b", "TICKET-0084",
             "Alias, recherche approchée ou normalisation pour le lexique d'actions.",
             "Le nombre de formes non reconnues distinctes dépasse le seuil que Nia fixe.",
             _DECISIONS, "**C3b reactivation condition, made measurable.**",
             metric="lexicon_gaps"),
    Deferral("A2 (îlots)", "TICKET-0088",
             "Un deuxième registre d'îlots de Création.",
             "Le premier brief qui doit retirer une entrée de `CREATION_ISLANDS`.",
             _DECISIONS, "reactivate at the first brief that must remove an entry from `CREATION_ISLANDS`."),
    Deferral("A3 (îlots)", "TICKET-0088",
             "Retirer les règles 2 et 7 de `creation_island.py`.",
             "`legacy.html` est absent et `LEGACY_MOUNTS` est vide.",
             _DECISIONS, "reactivate when `legacy.html` is absent **and** `frontend/src/legacy/registry.js`'s "
                         "`LEGACY_MOUNTS` is empty."),
    Deferral("D-0088-rule6-alias", "TICKET-0088",
             "Chercher un alias nu de `mount(` / `hydrate(` importé de `'svelte'`.",
             "Un second import de `mount` / `hydrate` depuis `'svelte'` hors des trois fichiers permis.",
             _DECISIONS, "**D-0088-rule6-alias**: a bare `mount(`/ `hydrate(` alias imported from `'svelte'` "
                         "is not itself scanned for;"),
    Deferral("D-0088-rule11-unrouted", "TICKET-0088",
             "Vérifier une `primaryAction` sans champ `createPanel`.",
             "Un site `primaryAction: {` sans `createPanel` dans `tabs.js`.",
             _DECISIONS, "**D-0088-rule11-unrouted**: a non-routed `primaryAction` object with no "
                         "`createPanel` field at all passes rule 11 unchecked;"),
    Deferral("D2", "TICKET-0121",
             "Le concepteur invente un donneur, créé à l'approbation.",
             "Nia crée souvent un PNJ juste pour donner une offre proposée.",
             _T0121, "D2 (an invented giver; reactivation: the creator often creates a character just to "
                     "give a proposed offer)",
             metric="quest_requests"),
    Deferral("S3", "TICKET-0121",
             "Une recherche du lore par le sens.",
             "Des demandes où Nia répond que le lore le disait déjà.",
             _T0121, "S3 (a search by meaning; reactivation: requests the creator answers « the lore "
                     "already says it »)",
             metric="quest_requests"),
    Deferral("P1", "TICKET-0121",
             "Revoir l'outil de plan en plan global.",
             "La part des journées aiguillées vers une quête le demande.",
             _T0121, "P1 (the plan tool reworked; reactivation: the share of days routed to a quest asks "
                     "for it)",
             metric="quest_requests"),
    Deferral("H2", "TICKET-0124",
             "Le modèle reconnaît en jeu un personnage existant derrière un rôle.",
             "Des germes de Journée que Nia rattache à une fiche existante.",
             _T0124, "H2 (the model recognises an existing character in play; reactivation: Journée germs "
                     "the creator attaches to an existing character)",
             metric="germs"),
    Deferral("W2", "TICKET-0124",
             "Garder l'historique des lois du monde.",
             "Un writer passe world_law_id= à un fait.",
             _T0124, "W2 (law history; reactivation: a writer passes world_law_id= to a fact)"),
)


def deferral_dicts() -> list[dict]:
    """The registry as the « Suivi » tab and the export read it."""
    return [{"code": d.code, "ticket": d.ticket, "deferred": d.deferred_fr, "condition": d.condition_fr,
             "source": d.source, "metric": d.metric, "status": d.status, "follow_up": d.follow_up}
            for d in DEFERRALS]
