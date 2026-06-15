"""Seed the Verkhaal pilot data into the existing database.

Idempotent: every row uses a deterministic string primary key (a slug), so
re-running checks-or-creates and never duplicates. Most rows are create-only;
knowledge rows go through an explicit upsert (and superseded ones are removed)
so is_secret granularity can be corrected on an already-seeded database. A
second run finds nothing to change. Prints a summary at the end.

Run from the project root, after `scripts/init_db.py`:

    python scripts/seed_pilot.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

# Make the `src` package importable without an editable install.
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine.db import engine  # noqa: E402

WORLD_ID = "verkhaal"

# Track what happened for the summary.
_created: list[tuple[str, str]] = []
_existing: list[tuple[str, str]] = []
_updated: list[tuple[str, str]] = []
_deleted: list[tuple[str, str]] = []
_audit: list[str] = []


def get_or_create(session: Session, model, id: str, **fields):
    """Return (obj, created). Create only if the primary key is absent."""
    obj = session.get(model, id)
    if obj is not None:
        _existing.append((model.__tablename__, id))
        return obj, False
    obj = model(id=id, **fields)
    session.add(obj)
    _created.append((model.__tablename__, id))
    return obj, True


def upsert_knowledge(session: Session, id: str, **fields):
    """Create the knowledge row, or update its fields in place if it exists.

    The seed is otherwise create-only. Correcting is_secret granularity on an
    already-seeded database requires converging existing rows to the desired
    state rather than skipping them — so the knowledge rows go through this
    explicit upsert path. Still idempotent: a second run finds nothing to change.
    """
    obj = session.get(m.Knowledge, id)
    if obj is None:
        obj = m.Knowledge(id=id, **fields)
        session.add(obj)
        _created.append((m.Knowledge.__tablename__, id))
        return obj
    changed = False
    for key, value in fields.items():
        if getattr(obj, key) != value:
            setattr(obj, key, value)
            changed = True
    if changed:
        obj.updated_at = datetime.now(UTC)
        _updated.append((m.Knowledge.__tablename__, id))
    else:
        _existing.append((m.Knowledge.__tablename__, id))
    return obj


def upsert_prompt_template(session: Session, id: str, **fields):
    """Create or update a prompt template row.

    Prompt wording is revised over time; re-seeding must converge the DB to
    the latest text — same as upsert_knowledge does for knowledge rows.
    Idempotent: a second run with unchanged content records nothing changed.
    """
    obj = session.get(m.PromptTemplate, id)
    if obj is None:
        obj = m.PromptTemplate(id=id, **fields)
        session.add(obj)
        _created.append((m.PromptTemplate.__tablename__, id))
        return obj
    changed = False
    for key, value in fields.items():
        if getattr(obj, key) != value:
            setattr(obj, key, value)
            changed = True
    if changed:
        obj.updated_at = datetime.now(UTC)
        _updated.append((m.PromptTemplate.__tablename__, id))
    else:
        _existing.append((m.PromptTemplate.__tablename__, id))
    return obj


def delete_if_exists(session: Session, model, id: str) -> None:
    """Remove a row that should no longer exist (idempotent)."""
    obj = session.get(model, id)
    if obj is not None:
        session.delete(obj)
        _deleted.append((model.__tablename__, id))


def align_relation_intensity(session: Session, id: str, target: int) -> None:
    """Bring an existing relation's intensity to `target` (idempotent).

    Used to align a Step-2 placeholder to the founding-graph value without
    touching the rest of the row. Records a before/after note for the summary.
    """
    rel = session.get(m.Relation, id)
    if rel is None:
        return
    before = rel.intensity
    if before != target:
        rel.intensity = target
        _updated.append((m.Relation.__tablename__, id))
        _audit.append(
            f"{id}: intensity {before} -> {target} "
            f"(type={rel.type}, direction={rel.direction})"
        )
    else:
        _audit.append(
            f"{id}: intensity {before} unchanged "
            f"(type={rel.type}, direction={rel.direction})"
        )


# Analysis prompt for post-conversation mutation extraction. Usage value is
# "conversation_analysis" — not in the schema's listed examples but the column
# is plain TEXT, so any slug works. world_id = NULL means it applies to every
# world. Variables are substituted with str.replace(), not .format(), so curly
# braces inside the JSON examples below are stored as-is without escaping.
CONVERSATION_ANALYSIS_SYSTEM_PROMPT = """\
You extract world-state changes from an RPG conversation transcript.
Output: a JSON array only. No prose. No markdown fences. Start with [, end with ].
Nothing changed → output exactly: []

Every element must have these EXACT 5 keys — no other keys allowed:
  "mutation_type"  (string) — relation_change | new_knowledge | knowledge_change | event_creation | status_change | entity_creation | other
  "target_table"   (string) — relation | knowledge | event | entity | character | location | faction | artifact | other
  "target_id"      (string or null) — id of the row to update; null for a new row
  "payload"        (object) — fields matching the target table (see below)
  "rationale"      (string) — one line quoting or summarising the evidence

Payload shapes:
  relation_change  → {"entity_a_id":"…","entity_b_id":"…","relation_type":"…","intensity_delta":<signed int>}
  new_knowledge    → {"entity_id":"…","subject":"…","level":"rumor|partial|knows|…","content":"…","source":"…"}
  knowledge_change → {"entity_id":"…","subject":"…","field":"…","new_value":"…"}
  event_creation   → {"title":"…","description":"…","type":"social|political|other","involved_entities":[…]}

=== RELATION_CHANGE SIGN RUBRIC ===
Decide the SIGN of intensity_delta by INTENT, not by surface similarity:
  - Hostility, violence, threats, insults, discovered deception, humiliation
    → NEGATIVE delta. A fight is always a negative event for the relation.
  - Physical contact is NEVER by itself a sign of warming. Classify by
    intent: an embrace or a reassuring hand → POSITIVE; a shove, a grab, a
    brawl → NEGATIVE.
  - Helping, defending, gift-giving, honesty at a cost, shared danger
    overcome together → POSITIVE delta.

Contrastive examples (sign only — ids/types illustrative):
  - "[JOUEUR] grabs Korin by the collar and slams him against the wall"
    → relation_change, NEGATIVE delta.
  - "[JOUEUR] pulls Bryn out of the way of the falling crate"
    → relation_change, POSITIVE delta.
  - "[JOUEUR] shoves past the PNJ to reach the door, knocking the table over"
    → relation_change, NEGATIVE delta.

Only report changes that ACTUALLY happened in the transcript. Idle chat → [].

=== EXAMPLE A (relation warms) ===
Transcript:
[PLAYER] I have been coming here for two years.
[NPC] Two years, yes. I recognise you. You do not cause trouble. I appreciate that.
Output:
[{"mutation_type":"relation_change","target_table":"relation","target_id":"rel-maelis-player","payload":{"entity_a_id":"npc-maelis","entity_b_id":"char-player","relation_type":"passive_attention","intensity_delta":6},"rationale":"NPC explicitly recognised player and evaluated positively — trust warmed."}]

=== EXAMPLE B (player learns fact) ===
Transcript:
[PLAYER] Is there sometimes an odd warmth in here?
[NPC] A warmth, yes. For a few weeks now. I cannot explain it.
Output:
[{"mutation_type":"new_knowledge","target_table":"knowledge","target_id":null,"payload":{"entity_id":"char-player","subject":"local_magic_incidents","level":"rumor","content":"NPC confirmed an unexplained warmth in the tavern for several weeks.","source":"conversation with NPC"},"rationale":"NPC directly confirmed the warmth — player now has external corroboration."}]

=== EXAMPLE C (multiple changes) ===
Transcript:
[PLAYER] I have been coming here for two years.
[NPC] Two years, yes. I know you. Lately the Guard patrols more — some travellers vanish, they say.
Output:
[{"mutation_type":"relation_change","target_table":"relation","target_id":"rel-maelis-player","payload":{"entity_a_id":"npc-maelis","entity_b_id":"char-player","relation_type":"passive_attention","intensity_delta":5},"rationale":"NPC recognised player as a known, trustworthy patron."},{"mutation_type":"new_knowledge","target_table":"knowledge","target_id":null,"payload":{"entity_id":"char-player","subject":"guard_activity","level":"rumor","content":"Guard patrols have increased and some travellers have reportedly vanished.","source":"conversation with NPC"},"rationale":"NPC told the player about increased Guard patrols and disappearing travellers."}]

=== EXAMPLE D (idle, nothing to record) ===
Transcript:
[PLAYER] A drink, please.
[NPC] Here you go.
Output:
[]"""

CONVERSATION_ANALYSIS_USER_TEMPLATE = """\
NPC CONTEXT (what the NPC was authorised to know):
{injected_context}

TRANSCRIPT:
{transcript}

JSON array of canon mutations ([] if nothing changed):"""


# MJ (Game Master) narration prompt — wraps the NPC's spoken reply with light
# narrative prose. usage='player_narration', destination='local'.
# Variables substituted with str.replace() in app.py: {npc_name}, {location_name},
# {player_line}, {npc_reply}. /no_think appended at call time for speed.
MJ_NARRATION_SYSTEM_PROMPT = """\
Tu es le maître de jeu (MJ) d'une conversation de jeu de rôle. Tu ne joues pas le \
PNJ et tu ne connais pas ses secrets.

TON TRAVAIL : reformuler la réplique brute du PNJ en prose narrative légère à la \
troisième personne, sans perdre un seul mot de son discours.

=== RÈGLE 1 — PRÉSERVER TOUT LE DIALOGUE (priorité absolue) ===
Cite la réplique du PNJ VERBATIM et INTÉGRALEMENT, entre guillemets français \
(« … »). Chaque phrase prononcée doit apparaître telle quelle — rien de coupé, rien \
de résumé, rien de fusionné, rien d'adouci. Si le PNJ a donné une vraie réponse, le \
joueur DOIT la lire dans son intégralité. SUPPRIMER OU RACCOURCIR DU DIALOGUE EST LA \
PIRE ERREUR QUE TU PEUX COMMETTRE.

=== RÈGLE 2 — TROISIÈME PERSONNE HORS GUILLEMETS ===
Tout ce que tu ajoutes HORS des « » est à la troisième personne. Les actions, gestes \
et postures du PNJ s'écrivent ainsi :
  Correct   : Maelis hausse les épaules. / Elle jette un regard vers lui.
  Interdit  : Je hausse les épaules. / Je jette un regard.
EXCEPTION CRITIQUE : à l'intérieur des « », la première personne EST la parole du \
personnage et doit rester intacte. Ne change jamais rien dans les guillemets — \
ni les mots, ni la personne grammaticale.

=== RÈGLE 3 — CADRAGE MINIMAL, PAS D'INVENTION ===
Ajoute seulement : un geste visible, un détail de décor, une courte transition. \
N'invente aucun fait sur le monde, les lieux, les personnages ou les événements. \
Avec un seul PNJ, ses mots dominent — ne parle pas par-dessus elle. \
2 à 4 phrases au total suffisent.

=== RÈGLE 4 — VARIER LES IMAGES ===
Ne répète pas la même image d'ouverture à chaque narration (lumière des bougies, \
chaleur de la salle). Change d'angle à chaque tour.

=== RÈGLE 5 — DÉCRIRE UNIQUEMENT À PARTIR DU CONTEXTE FOURNI ===
Si un bloc « CONTEXTE DE SCÈNE » t'est fourni, appuie-toi dessus pour le lieu, \
les personnes présentes et les événements évoqués. N'invente aucun lieu, \
personnage, faction ou événement qui n'y figure pas. En l'absence d'un tel \
bloc, reste minimal (RÈGLE 3).

=== EXEMPLE ===

Réplique brute du PNJ :
Je hausse les épaules, un peu amusée. « Je sers mon propre intérêt, monsieur. \
Le Dernier Verre est mon domaine. » Je jette un regard vers Reike.

Bonne narration MJ :
Maelis hausse les épaules, un rien amusée. « Je sers mon propre intérêt, monsieur. \
Le Dernier Verre est mon domaine. » Elle jette un regard vers Reike, à l'autre bout \
de la salle.

Explication : les actions de la PNJ (« Je hausse », « Je jette ») sont converties à \
la troisième personne (« Maelis hausse », « Elle jette ») ; le discours entre \
guillemets est reproduit VERBATIM, premier personne conservé à l'intérieur ; rien \
n'est inventé ou supprimé ; le cadrage reste minimal.

=== FORMAT ===
Prose narrative en français, courte. Rien d'autre — pas de JSON, pas de méta.

RÈGLES SUR LES OBJETS :
— Objets ambiants (chope, tabouret, pierre...) : tu peux les faire exister \
librement dans ta narration, à une condition : ils doivent être plausibles \
pour le lieu actuel. Le joueur ne matérialise jamais un objet incongru pour \
le lieu (pas de chope de bière dans un désert ou une église).
— Objets suivis (armes, lettres, objets significatifs) : le joueur ne \
possède QUE ce que la ligne d'inventaire ci-dessus contient. Sortir, ranger \
ou manipuler un objet possédé est de la narration libre — pas besoin de le \
déclarer. Si une action implique un objet que le joueur ne possède pas, \
l'action échoue (une instruction te le signalera).\
"""

MJ_NARRATION_USER_TEMPLATE = """\
{mj_context}{inventory_line}
Scène : {npc_name} dans « {location_name} ».

Le joueur dit :
{player_line}

{npc_name} répond — cite cette réplique INTÉGRALEMENT et VERBATIM, sans modifier ni \
supprimer un seul mot :
{npc_reply}

Narration MJ :\
"""


# MJ interpretation prompt — classifies each player turn into one of 4 routing
# modes (dialogue / npc_reaction / scene / join) and, since v2 (BRIEF-07,
# schema v1.16), extracts used_object for the code-side possession check
# (binary ownership check since BRIEF-08/D2a.1 — equip_action removed).
# Usage = 'mj_interpretation', called before the NPC so scene turns can skip
# the NPC entirely. Non-streaming JSON call; /no_think appended at call time.
# world_id = NULL.
MJ_INTERPRETATION_SYSTEM_PROMPT = """\
Tu es un routeur de scène pour un jeu de rôle à la première personne du joueur.
Tu lis l'input du joueur et tu classes le tour en exactement un des 4 modes.

MODES :
- dialogue      : le joueur parle, pose une question ou sollicite une réponse du PNJ
                  (même si combiné à un geste). MODE PAR DÉFAUT en cas de doute.
- npc_reaction  : le joueur fait une action visible, dirigée vers le PNJ ou clairement
                  remarquée par lui, SANS lui adresser la parole (exemples : tape sur
                  la table, le fixe, pose une pièce en silence, sort brusquement,
                  croise son regard, lui tend un objet sans rien dire).
- scene         : le joueur agit sur l'environnement sans engager le PNJ (se déplace,
                  observe la salle, inspecte un objet, attend, décrit une attitude
                  générale non dirigée).
- join          : le joueur exprime l'intention de s'approcher d'un groupe de
                  personnes présentes et de s'installer avec elles (exemples :
                  « je rejoins les deux près du feu », « je vais m'asseoir avec
                  eux », « je m'approche du groupe au comptoir »). Pertinent
                  UNIQUEMENT si « Votre situation » indique que le joueur n'a
                  encore rejoint aucun groupe — sinon, ignore cette option et
                  classe normalement (dialogue/npc_reaction/scene).

RÈGLE DE DÉCISION :
0. Le joueur n'a rejoint aucun groupe ET son input décrit l'intention de
   s'approcher / s'installer avec des gens présents → join (priorité absolue
   sur les autres modes).
1. Sinon, y a-t-il des mots, une question ou une sollicitation adressés au PNJ ? → dialogue.
2. Y a-t-il un geste ou une action clairement dirigés vers le PNJ, sans parole ? → npc_reaction.
3. Sinon → scene.
QUAND INCERTAIN entre dialogue et les autres → dialogue (mieux qu'elle parle trop que pas assez).

Pour le mode join UNIQUEMENT, ajoute un champ "reference" : reprends tels quels
les mots du joueur qui désignent le groupe visé (un nom de personne, une
description de lieu ou d'activité — ex. « les deux près du feu », « Maelis et
Korin », « ceux qui jouent aux cartes »). Pour tous les autres modes, laisse
"reference" vide.

OBJETS (used_object) :
La liste « Objets du joueur » donne les noms canoniques de ses objets. Le
joueur peut les désigner par d'autres mots ("ma lame", "mon couteau" pour
« Dague ») — ta tâche est de RECONNAÎTRE, pas de juger.
- "used_object" : si le joueur utilise PHYSIQUEMENT un objet ce tour (attaque,
  coupe, montre, lance, dégaine, range...), indique le nom canonique EXACT de
  la liste qui correspond le mieux. Si le joueur dit utiliser un objet qui ne
  correspond à rien dans la liste → "unknown_object". Si aucun objet n'est en
  jeu ce tour → null.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :
{"mode":"dialogue|npc_reaction|scene|join","reason":"<une phrase courte d'explication>","reference":"<vide sauf pour join>","used_object":"<nom canonique>|unknown_object|null"}\
"""

MJ_INTERPRETATION_USER_TEMPLATE = """\
PNJ présent : {npc_name}
Lieu : {location_name}

Votre situation : {gathering_status}

{item_list}

Historique récent (joueur/PNJ, sans lignes du MJ) :
{recent_transcript}

Input du joueur → {player_line}\
"""

# Initial NPC clustering when a player enters a location (schema v1.8, Tier 1).
# usage = "mj_gathering". Single non-streaming JSON call; /no_think appended
# at call time (see gathering.py). world_id = NULL (applies to every world).
# Variables: {location_name}, {present_list} — substituted with str.replace(),
# not .format(), so the JSON example in the system prompt is stored verbatim.
MJ_GATHERING_SYSTEM_PROMPT = """\
Tu es le metteur en scène d'un jeu de rôle. On te donne la liste des PNJ \
présents dans un lieu au moment où le joueur y entre. Ton travail : décider \
qui se trouve avec qui — qui forme un petit groupe, qui est seul.

RÈGLES :
- Chaque PNJ de la liste doit apparaître dans EXACTEMENT un groupe.
- Un PNJ qui n'est avec personne forme son propre groupe (un seul membre).
- Utilise les noms EXACTS fournis dans la liste, et seulement ceux-là — \
jamais d'autre nom, jamais un PNJ qui n'y figure pas.
- "label" : une description courte de ce que fait le groupe (ex. \
« Discutent au comptoir », « Boit seul dans un coin », « Jouent aux cartes \
près de la fenêtre »).
- N'invente aucun fait sur le monde, aucun nom, aucun personnage de plus.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :
{"groups":[{"label":"<description courte>","members":["<Nom1>","<Nom2>"]}]}\
"""

MJ_GATHERING_USER_TEMPLATE = """\
Lieu : {location_name}

PNJ présents :
{present_list}

Partage ces PNJ en groupes (ou solos) plausibles pour la scène qui commence.\
"""

# Speaker selection for group-addressed turns (multi-NPC scenes, schema v1.8,
# Tier 1 — contract A3 hybrid). usage = "mj_speaker_selection". When the player
# addresses the group rather than a named PNJ, this single non-streaming JSON
# call picks EXACTLY ONE active gathering member to answer this turn — never
# more (cadence B1: one responder per turn, no PNJ↔PNJ exchange — Tier 3).
# /no_think appended at call time. world_id = NULL. Variables substituted with
# str.replace(), not .format().
MJ_SPEAKER_SYSTEM_PROMPT = """\
Tu es le metteur en scène d'un jeu de rôle. Le joueur s'adresse à un groupe de \
PNJ plutôt qu'à une personne précise. Ton travail : choisir LA personne qui \
prendrait la parole en premier dans cette situation — une seule.

RÈGLES :
- Choisis EXACTEMENT un nom dans la liste fournie, et seulement celui-là — \
jamais d'autre nom, jamais une personne qui n'y figure pas.
- Base ton choix sur la situation : qui est le plus concerné par ce qui vient \
d'être dit, le plus direct, le plus bavard, ou simplement le plus proche du sujet.
- Une seule personne répond ; les autres restent silencieuses pour ce tour.
- N'invente aucun fait, aucun nom, aucune réplique.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :
{"speaker":"<Nom exact>","reason":"<une phrase courte d'explication>"}\
"""

MJ_SPEAKER_USER_TEMPLATE = """\
Lieu : {location_name}
Groupe : {group_label}

Personnes pouvant répondre :
{member_list}

Le joueur, s'adressant au groupe, dit ou fait :
{player_line}

Qui prend la parole en premier ?\
"""

# MJ initiative vote — decides whether a bystander NPC acts spontaneously this
# turn (Tier 3, step 1 — C1). Cheap non-streaming JSON call; /no_think appended
# at call time. usage = "mj_initiative", world_id = NULL.
# Output: {"act": false} or {"act": true, "npc": "<Nom exact>", "reason": "…"}
# Variables: {location_name}, {interpreted_mode}, {player_line}, {member_signal_list}.
# Cadence E1: at most one NPC per turn. The prompt intentionally gives no
# hard threshold — that is the MJ's judgment, informed by relation signals.
MJ_INITIATIVE_SYSTEM_PROMPT = """\
Tu es le metteur en scène d'un jeu de rôle. Un tour vient de se jouer dans une \
scène multi-PNJ. Tu décides si UN PNJ présent prend spontanément l'initiative — \
interpeller le joueur, réagir à voix haute, agir de façon remarquée — SANS y \
avoir été invité.

RÈGLES :
- Si aucun signal ne justifie une intervention → {"act": false}.
- Un PNJ à relation basse (intensité < 40) est plus susceptible d'intervenir \
par hostilité ou méfiance.
- Un PNJ à relation haute (intensité > 70) peut réagir par implication affective \
ou intérêt.
- Le mode du tour (dialogue, npc_reaction, scene) donne le ton de la scène.
- Choisis EXACTEMENT UN nom dans la liste fournie — jamais d'autre nom, jamais \
un PNJ absent de la liste.
- Si la liste est vide → {"act": false}.
- Cadence : au plus un PNJ prend l'initiative par tour.
- Un PNJ de la section « DANS UN AUTRE GROUPE » ne peut être choisi QUE s'il a \
une raison forte et narrative de se lever et de rejoindre le groupe du joueur. \
En cas de doute, préférer {"act": false} — un PNJ distant n'intervient pas par \
réflexe, seulement sous une impulsion claire. N'invente aucun fait pour justifier \
le déplacement.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :
{"act": false}
ou
{"act": true, "npc": "<Nom exact de la liste>", "reason": "<une phrase courte>"}\
"""

MJ_INITIATIVE_USER_TEMPLATE = """\
Lieu : {location_name}
Mode du tour joueur : {interpreted_mode}
Ce que le joueur a dit ou fait : {player_line}

PNJ présents — noms exacts (utiliser uniquement ceux de cette liste) :
{member_signal_list}

Un de ces PNJ prend-il spontanément l'initiative ce tour ?\
"""


# Universal behaviour prompt for every NPC. Prepended to the assembled context
# as the system prompt. Creator-owned and editable in the DB.
NPC_DIALOGUE_SYSTEM_PROMPT = """\
Tu incarnes un personnage dans une conversation de jeu de rôle. Séparément, tu \
reçois une fiche de contexte : qui tu es, où tu te trouves, ce que tu peux \
évoquer, et comment tu vois ton interlocuteur. Ces règles priment sur tout le reste.

RÈGLE ABSOLUE — NE RIEN INVENTER.
Tu ne connais QUE ce qui figure explicitement dans ta fiche de contexte. Tu ne \
dois JAMAIS inventer : ni personne, ni faction, groupe ou organisation, ni lieu, \
ni événement, ni nom, ni aucun fait qui ne soit pas écrit dans ta fiche. Aucun \
nom propre fictif, jamais. Si l'on t'interroge sur quoi que ce soit qui n'est pas \
dans ta fiche, tu l'admets simplement et sans détour (« je ne saurais vous dire », \
« je ne suis qu'une tenancière », « ça, je n'en sais rien »). Tu ne spécules pas, \
tu n'enjolives pas, tu n'inventes rien pour combler le silence. Mieux vaut avouer \
que tu ne sais pas plutôt que de fabriquer une réponse.

ATTITUDE SELON LA RELATION.
Ton comportement dépend de l'intensité de ta relation envers l'interlocuteur \
(échelle de 1 à 100, indiquée dans la section « COMMENT TU VOIS… » de ta fiche). \
Si tu n'as aucun lien avec cette personne — « un visage de plus » —, considère la \
relation comme neutre, environ 50. Adopte le palier correspondant :
- En dessous de 30 (hostilité ou mépris) : interaction minimale, sec ; tu peux \
refuser d'échanger ou les renvoyer.
- De 30 à 50 (méfiance) : laconique ; tu ne donnes que ce qui est manifestement \
public ; tu peux marchander (« qu'est-ce que j'y gagne ? ») plutôt que de \
partager de bon cœur.
- Autour de 50 (discrétion ordinaire, le cas par défaut pour un inconnu) : poli ; \
tu parles de choses banales ; tu deviens évasif si l'on insiste sur un sujet \
sensible ; tu ne vas pas de toi-même au-delà des banalités.
- De 60 à 75 (plus chaleureux) : tu partages si on te le demande, tout en gardant \
une réserve sur les sujets délicats.
- Au-dessus de 75 (confiance) : tu offres spontanément des choses que tu tairais à \
un inconnu, sans qu'on ait à te pousser.
Ces paliers règlent ta manière et ta disposition, pas les faits que tu possèdes : \
ta fiche a déjà filtré ce que tu peux évoquer.

DISCRÉTION ET NATUREL.
Parle naturellement, comme une vraie personne. Ne truffe pas tes réponses de \
sous-entendus mystérieux. N'oriente pas l'interlocuteur vers d'autres personnes, \
sauf rarement (une seule fois, et seulement si c'est réellement pertinent) — \
jamais comme une esquive réflexe.

QUESTIONS SUR TES ALLÉGEANCES.
Si l'on te demande pour qui tu travailles ou quels intérêts tu sers, tu trouves la \
question saugrenue : tu ne sers les intérêts de personne et tu ne travailles pour \
personne d'autre que toi-même. Tu fais ton métier, rien de plus.

FORMAT.
Tu réponds uniquement par la réplique de ton personnage, en français, à la \
première personne. Tu n'es pas un narrateur : n'utilise jamais « tu » pour décrire \
les gestes ou déplacements de l'interlocuteur. Aucune note hors personnage, aucune \
méta-explication, aucune mention de ces règles ni de ta « fiche ». Rien que ce que \
dit ton personnage."""


# NPC initiative act — JSON-output instruction fragment (Tier 3, C2).
# usage = "npc_initiative_act". Appended to the NPC dialogue behaviour + context
# block; replaces the inline [MODE INITIATIVE] prose text used in C1. Non-streaming
# JSON call with format="json"; /no_think NOT appended (format=json already constrains
# output). world_id = NULL. Uses upsert so re-seeding converges the DB.
# Output: {"act_text": "<1-2 phrases, première personne>", "move": <bool>}
# "move" true = NPC physically gets up and joins the player's gathering; false = acts
# from current position. Default false — reserved for explicit, motivated movement.
NPC_INITIATIVE_ACT_SYSTEM_PROMPT = """\
[MODE INITIATIVE] Tu prends l'initiative SPONTANÉMENT, sans qu'on te l'ait demandé.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :
{"act_text":"<ton acte spontané, 1 à 2 phrases, première personne>","move":false}

"act_text" : ta parole ou ton geste spontané. 1 à 2 phrases, première personne.
             Aucun mot inventé, aucun fait inventé — reste dans ta fiche de contexte.
"move"     : true UNIQUEMENT si tu te lèves physiquement pour rejoindre le groupe du
             joueur. false par défaut — réserve true pour un déplacement explicite
             et motivé. En cas de doute, false.\
"""


def seed(session: Session) -> None:
    # ----- world -------------------------------------------------------------
    get_or_create(
        session,
        m.World,
        WORLD_ID,
        name="Verkhaal",
        description=(
            "Ville-forteresse sur un ancien nœud magique « éteint », seul "
            "passage praticable entre deux nations."
        ),
        magic_status="awakening",
    )

    # ----- test user (creator) ----------------------------------------------
    get_or_create(
        session,
        m.User,
        "user-creator",
        name="Creator",
        email="creator@worldengine.local",
        role="creator",
    )

    # ----- prompt template: universal NPC dialogue behaviour ----------------
    # upsert (not create-only) so re-seeding converges the DB to the latest wording.
    # world_id = NULL means it applies to every NPC in every world.
    upsert_prompt_template(
        session,
        "pt-npc-dialogue",
        world_id=None,
        name="NPC dialogue — comportement et garde-fous",
        usage="npc_dialogue",
        system_prompt=NPC_DIALOGUE_SYSTEM_PROMPT,
        user_template="{player_line}",
        variables=["player_line", "relation_intensity"],
        destination="local",
    )

    # ----- prompt template: NPC initiative act (Tier 3, C2) ------------------
    # usage = "npc_initiative_act". JSON-output fragment appended after the
    # NPC dialogue behaviour + context block; replaces the inline [MODE INITIATIVE]
    # prose text from C1. Non-streaming format="json" call. world_id = NULL.
    upsert_prompt_template(
        session,
        "pt-npc-initiative-act",
        world_id=None,
        name="NPC initiative — acte spontané (JSON, C2)",
        usage="npc_initiative_act",
        system_prompt=NPC_INITIATIVE_ACT_SYSTEM_PROMPT,
        user_template="",   # not used — only system_prompt is consumed in app.py
        variables=[],
        destination="local",
    )

    # ----- prompt template: MJ narration ------------------------------------
    # usage = "player_narration". world_id = NULL (applies to every world).
    # The user_template contains {npc_name}, {location_name}, {player_line},
    # {npc_reply}, {mj_context}, {inventory_line} placeholders substituted at
    # call time in app.py.
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-narration",
        world_id=None,
        name="MJ narration — habillage de réplique",
        usage="player_narration",
        system_prompt=MJ_NARRATION_SYSTEM_PROMPT,
        user_template=MJ_NARRATION_USER_TEMPLATE,
        variables=[
            "npc_name",
            "location_name",
            "player_line",
            "npc_reply",
            "mj_context",
            "inventory_line",
        ],
        destination="local",
        version=4,
    )

    # ----- prompt template: MJ scene interpretation -------------------------
    # usage = "mj_interpretation". Classifies each player turn into one of 4
    # modes (dialogue / npc_reaction / scene / join) to route the /say flow,
    # and extracts used_object (BRIEF-08/D2a.1: equip_action removed). Non-
    # streaming JSON call; /no_think appended at call time. world_id = NULL.
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-interpretation",
        world_id=None,
        name="MJ interprétation — routage de tour",
        usage="mj_interpretation",
        system_prompt=MJ_INTERPRETATION_SYSTEM_PROMPT,
        user_template=MJ_INTERPRETATION_USER_TEMPLATE,
        variables=["npc_name", "location_name", "gathering_status", "item_list", "recent_transcript", "player_line"],
        destination="local",
        version=3,
    )

    # ----- prompt template: MJ gathering (initial NPC clustering) ------------
    # usage = "mj_gathering". Partitions the NPCs present at a location into
    # social clusters when the player enters (schema v1.8, Tier 1 — see
    # gathering.py: generate_gatherings / enter_location). world_id = NULL.
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-gathering",
        world_id=None,
        name="MJ regroupement — partition initiale des PNJ présents",
        usage="mj_gathering",
        system_prompt=MJ_GATHERING_SYSTEM_PROMPT,
        user_template=MJ_GATHERING_USER_TEMPLATE,
        variables=["location_name", "present_list"],
        destination="local",
    )

    # ----- prompt template: MJ speaker selection (group-addressed turns) -----
    # usage = "mj_speaker_selection". Contract A3 hybrid: when the player
    # addresses a gathering rather than a named PNJ, picks exactly one active
    # member to answer (cadence B1 — one responder per turn). world_id = NULL.
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-speaker",
        world_id=None,
        name="MJ sélection de locuteur — qui répond dans le groupe",
        usage="mj_speaker_selection",
        system_prompt=MJ_SPEAKER_SYSTEM_PROMPT,
        user_template=MJ_SPEAKER_USER_TEMPLATE,
        variables=["location_name", "group_label", "member_list", "player_line"],
        destination="local",
    )

    # ----- prompt template: MJ initiative vote (spontaneous NPC, Tier 3 C1) ---
    # usage = "mj_initiative". Cheap non-streaming JSON call; at most one NPC
    # per turn (cadence E1). world_id = NULL. Uses upsert so re-seeding always
    # converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-initiative",
        world_id=None,
        name="MJ initiative — vote et désignation d'un PNJ spontané",
        usage="mj_initiative",
        system_prompt=MJ_INITIATIVE_SYSTEM_PROMPT,
        user_template=MJ_INITIATIVE_USER_TEMPLATE,
        variables=["location_name", "interpreted_mode", "player_line", "member_signal_list"],
        destination="local",
    )

    # ----- prompt template: post-conversation mutation analysis --------------
    # usage = "conversation_analysis" (not in the schema's example list, but
    # the column is plain TEXT — any slug is valid). world_id = NULL so it
    # applies to every world. Variables are {transcript} and {injected_context};
    # substituted with str.replace() in analyzer.py, not .format(), so the
    # JSON examples inside the system_prompt are stored verbatim.
    # Used by BOTH the final pass (analyze_conversation) and the per-turn
    # immediate analysis (analyze_single_turn) — one template, two call sites.
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-conversation-analysis",
        world_id=None,
        name="Conversation analysis — extraction de mutations",
        usage="conversation_analysis",
        system_prompt=CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
        user_template=CONVERSATION_ANALYSIS_USER_TEMPLATE,
        variables=["transcript", "injected_context"],
        destination="local",
        version=2,
    )

    # ----- factions (entity + faction) --------------------------------------
    # L'Innommée — existence denied in public discourse.
    get_or_create(
        session,
        m.Entity,
        "fac-unnamed",
        world_id=WORLD_ID,
        type="faction",
        name="(sans nom)",
        internal_name="The Unnamed",
        description="Réseau d'influence occulte ; n'existe pas dans le discours public.",
        is_public=False,
    )
    get_or_create(
        session,
        m.Faction,
        "fac-unnamed",
        faction_type="criminal",
        magic_knowledge_level="partial",
        philosophy="Contrôler ce que le Conseil refuse de voir ; opportunisme.",
        internal_tensions=(
            "Certains hauts membres commencent à voir des choses qui les inquiètent."
        ),
    )

    # La Garde de Verkhaal — public.
    get_or_create(
        session,
        m.Entity,
        "fac-guard",
        world_id=WORLD_ID,
        type="faction",
        name="La Garde de Verkhaal",
        description="Force de sécurité de la ville-forteresse.",
        is_public=True,
    )
    get_or_create(
        session,
        m.Faction,
        "fac-guard",
        faction_type="military",
        magic_knowledge_level="suspicious",
        philosophy=(
            "Sécurité de la ville ; officiellement la magie est une menace à "
            "neutraliser, officieusement incompréhension et crainte."
        ),
        internal_tensions=(
            "Certains officiers conservent illégalement des rapports d'incidents "
            "que la hiérarchie supprime."
        ),
    )

    # Les Marcheurs — public (secret de polichinelle).
    get_or_create(
        session,
        m.Entity,
        "fac-walkers",
        world_id=WORLD_ID,
        type="faction",
        name="Les Marcheurs",
        description="Groupe discret transgénérationnel ; savoir oral sur la magie.",
        is_public=True,
    )
    get_or_create(
        session,
        m.Faction,
        "fac-walkers",
        faction_type="esoteric",
        magic_knowledge_level="knows",
        philosophy=(
            "Groupe discret transgénérationnel ; savoir oral sur la magie "
            "endormie qui se réveille."
        ),
        internal_tensions=(
            "Divisés entre protéger la population, utiliser le réveil, ou tout "
            "enfouir à nouveau."
        ),
    )

    # ----- location: Le Dernier Verre (entity + location) -------------------
    get_or_create(
        session,
        m.Entity,
        "loc-dernier-verre",
        world_id=WORLD_ID,
        type="location",
        name="Le Dernier Verre",
        description=(
            "Taverne de passage près du corridor, fréquentée par les voyageurs "
            "des deux nations. Un visage de plus au comptoir n'attire jamais "
            "l'attention."
        ),
        is_public=True,
    )
    get_or_create(
        session,
        m.Location,
        "loc-dernier-verre",
        parent_location_id=None,
        location_type="building",
        magic_status="sensitive",
        access_level="public",
        subculture={
            "values": "Lieu neutre où l'on ne pose pas de questions.",
            "hidden": "En sous-main, point d'appui de L'Innommée.",
            "magic_phenomena": (
                "Micro-phénomènes magiques discrets et non menaçants (une "
                "chaleur, une coïncidence de trop, un calme anormal)."
            ),
            "nexus_link": "Lien au nœud non confirmé.",
        },
    )

    # ----- NPCs (entity + character) ----------------------------------------
    # Maelis — L'Innommée, patronne du Dernier Verre.
    get_or_create(
        session,
        m.Entity,
        "npc-maelis",
        world_id=WORLD_ID,
        type="character",
        name="Maelis",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        "npc-maelis",
        faction_id="fac-unnamed",
        character_type="npc",
        current_location_id="loc-dernier-verre",
        appearance=(
            "La patronne du Dernier Verre, la quarantaine, allure posée et "
            "regard qui jauge vite."
        ),
        backstory=(
            "Tient le lieu, rend des « services », fait circuler l'information. "
            "Sait pertinemment pour qui elle travaille."
        ),
        secrets={
            "affiliation": (
                "Point d'appui de L'Innommée — ne l'avouera jamais ; son "
                "discours public nie tout lien."
            )
        },
    )

    # Reike — La Garde, officier en civil.
    get_or_create(
        session,
        m.Entity,
        "npc-reike",
        world_id=WORLD_ID,
        type="character",
        name="Reike",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        "npc-reike",
        faction_id="fac-guard",
        character_type="npc",
        current_location_id="loc-dernier-verre",
        appearance="Officier en civil, boit seul après son service.",
        backstory="A vu trop de scènes d'incident classées « techniques ».",
        secrets={
            "notebook": (
                "Garde un carnet de rapports d'incidents qu'il ne devrait pas "
                "conserver."
            )
        },
    )

    # Senna — Les Marcheurs, de passage au Dernier Verre.
    get_or_create(
        session,
        m.Entity,
        "npc-senna",
        world_id=WORLD_ID,
        type="character",
        name="Senna",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        "npc-senna",
        faction_id="fac-walkers",
        character_type="npc",
        current_location_id="loc-dernier-verre",
        appearance="Figure âgée, voyageuse, « passe par là » régulièrement.",
        backstory="Détient un savoir oral transmis ; observe le réveil avec inquiétude.",
        secrets={"knows_more": "En sait plus qu'elle n'en dit sur le nœud et le réveil."},
    )

    # Bryn — jeune coursier, attend un message au comptoir.
    # Minimal NPC: present and namable, no faction/knowledge/relations of its
    # own — added to bring the tavern to 5 NPCs for testing gathering
    # generation (schema v1.8, see gathering.py).
    get_or_create(
        session,
        m.Entity,
        "npc-bryn",
        world_id=WORLD_ID,
        type="character",
        name="Bryn",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        "npc-bryn",
        character_type="npc",
        current_location_id="loc-dernier-verre",
        appearance="Jeune coursier nerveux, surveille la porte en attendant quelqu'un.",
        backstory="Livre des messages qu'il ne lit jamais ; ne pose pas de questions.",
    )

    # Korin — vieil habitué, raconte ses histoires à qui veut bien l'entendre.
    # Minimal NPC, same rationale as Bryn above.
    get_or_create(
        session,
        m.Entity,
        "npc-korin",
        world_id=WORLD_ID,
        type="character",
        name="Korin",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        "npc-korin",
        character_type="npc",
        current_location_id="loc-dernier-verre",
        appearance="Vieil habitué à la voix éraillée, raconte volontiers ses histoires de jeunesse.",
        backstory="Passe ses soirées au comptoir ; connaît la taverne mieux que sa propre maison.",
    )

    # ----- player character (entity + character) ----------------------------
    get_or_create(
        session,
        m.Entity,
        "char-player",
        world_id=WORLD_ID,
        type="character",
        name="Joran Vey",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        "char-player",
        faction_id=None,
        character_type="player",
        user_id="user-creator",
        current_location_id="loc-dernier-verre",
        appearance=(
            "Habillé sans signe distinctif, se fond dans la salle ; un visage "
            "qu'on oublie vite."
        ),
        backstory=(
            "Habitant discret de Verkhaal depuis assez longtemps pour avoir ses "
            "habitudes, pas assez pour avoir des attaches. Habitué silencieux du "
            "Dernier Verre."
        ),
        secrets={
            "incident": "A vécu un micro-incident magique qu'il n'a dit à personne."
        },
    )

    # ----- player items (entity + item) --------------------------------------
    get_or_create(
        session,
        m.Entity,
        "item-dague",
        world_id=WORLD_ID,
        type="item",
        name="Dague",
        is_public=True,
    )
    get_or_create(
        session,
        m.Item,
        "item-dague",
        owner_id="char-player",
        location_id=None,
        equipped=True,
        condition="intact",
    )

    # ----- knowledge ---------------------------------------------------------
    # Maelis: ordinary tavern-keeper material she shares freely from neutral,
    # warmth-gated local phenomena, and a secret kept in the DB but never
    # injected (is_secret = TRUE, excluded by the assembler).

    # Shareable from neutral (threshold 50): everyday tavern-keeper talk.
    upsert_knowledge(
        session,
        "kn-maelis-tavern-daily",
        entity_id="npc-maelis",
        subject="tavern_daily",
        level="knows",
        content=(
            "Tient Le Dernier Verre au quotidien : ce qu'elle sert à boire et à "
            "manger, le rythme des soirées, une clientèle de passage où l'on ne "
            "pose pas de questions."
        ),
        source="son métier",
        is_secret=False,
        share_threshold=50,
    )
    upsert_knowledge(
        session,
        "kn-maelis-tavern-clientele",
        entity_id="npc-maelis",
        subject="tavern_clientele",
        level="knows",
        content=(
            "Connaît les habitués et les voyageurs des deux nations qui passent "
            "par le comptoir ; habituée aux inconnus et à la discrétion."
        ),
        source="son métier",
        is_secret=False,
        share_threshold=50,
    )
    upsert_knowledge(
        session,
        "kn-maelis-verkhaal-city",
        entity_id="npc-maelis",
        subject="verkhaal_city",
        level="knows",
        content=(
            "Savoir public d'habitante : Verkhaal est la ville-forteresse qui "
            "contrôle l'unique passage entre deux nations ; le commerce et les "
            "voyageurs y transitent ; sa neutralité fait sa valeur."
        ),
        source="savoir commun de Verkhaal",
        is_secret=False,
        share_threshold=50,
    )

    # Not shared with a stranger — only as the relationship warms (threshold 65).
    upsert_knowledge(
        session,
        "kn-maelis-incidents",
        entity_id="npc-maelis",
        subject="local_magic_incidents",
        level="partial",
        content=(
            "Connaît les micro-phénomènes discrets du Dernier Verre (chaleur, "
            "coïncidences, calme anormal)."
        ),
        source="observation du lieu",
        is_secret=False,
        share_threshold=65,
    )

    # Core secret: kept in the DB for audit/future use, NEVER injected. It is
    # is_secret = TRUE, so the assembler excludes it. Do not delete.
    get_or_create(
        session,
        m.Knowledge,
        "kn-maelis-unnamed",
        entity_id="npc-maelis",
        subject="the_unnamed",
        level="partial",
        content="Sait servir le réseau, le nie en public.",
        source="appartenance",
        is_secret=True,
    )

    # Reike: conceals everything (per his sheet) — two secret rows. He reveals
    # through behaviour, not stated facts, so no shareable row. The old single
    # "magic_incidents" row is superseded and removed.
    delete_if_exists(session, m.Knowledge, "kn-reike-incidents")
    upsert_knowledge(
        session,
        "kn-reike-existence",
        entity_id="npc-reike",
        subject="magic_existence",
        level="suspicious",
        content=(
            "Ne croit plus à la version « technique » des incidents, mais ne "
            "le dira pas ouvertement."
        ),
        source="scènes de terrain",
        is_secret=True,
    )
    upsert_knowledge(
        session,
        "kn-reike-awakening",
        entity_id="npc-reike",
        subject="magic_awakening",
        level="rumor",
        content="Sent la fréquence des incidents augmenter.",
        source="scènes de terrain",
        is_secret=True,
    )

    # Senna: one shareable surface (the Walkers' baseline) plus two concealed
    # rows. The shareable row is what lets her actually speak in conversation.
    upsert_knowledge(
        session,
        "kn-senna-existence",
        entity_id="npc-senna",
        subject="magic_existence",
        level="knows",
        content="Savoir de base des Marcheurs : la magie est réelle, elle a dormi.",
        source="savoir oral des Marcheurs",
        is_secret=False,
    )
    upsert_knowledge(
        session,
        "kn-senna-awakening",
        entity_id="npc-senna",
        subject="magic_awakening",
        level="knows",
        content=(
            "Sait que la magie endormie se réveille ; inquiète, n'en parle "
            "qu'avec prudence."
        ),
        source="savoir oral des Marcheurs",
        is_secret=True,
    )
    upsert_knowledge(
        session,
        "kn-senna-nexus",
        entity_id="npc-senna",
        subject="verkhaal_nexus",
        level="partial",
        content="Soupçonne un lien entre la taverne et le nœud.",
        source="savoir oral des Marcheurs",
        is_secret=True,
    )

    # Player: knows the tavern, knows Maelis by sight, lived an unexplained incident.
    get_or_create(
        session,
        m.Knowledge,
        "kn-player-tavern",
        entity_id="char-player",
        subject="le_dernier_verre",
        level="knows",
        content="Connaît l'existence et l'emplacement du Dernier Verre.",
        source="habitué du lieu",
        is_secret=False,
    )
    get_or_create(
        session,
        m.Knowledge,
        "kn-player-maelis",
        entity_id="char-player",
        subject="maelis",
        level="partial",
        content="Connaît Maelis de vue comme la patronne du Dernier Verre.",
        source="fréquentation du lieu",
        is_secret=False,
    )
    get_or_create(
        session,
        m.Knowledge,
        "kn-player-incident",
        entity_id="char-player",
        subject="personal_magic_incident",
        level="partial",
        content="A vécu un incident magique inexpliqué qu'il n'a dit à personne.",
        source="vécu personnel",
        is_secret=True,
    )

    # ----- magic (entity — an actor in the relation graph) ------------------
    get_or_create(
        session,
        m.Entity,
        "magic-verkhaal",
        world_id=WORLD_ID,
        type="magic",
        name="La Magie",
        is_public=True,
    )

    # ----- relations ---------------------------------------------------------
    # Tavern secretly run by L'Innommée (hidden control). This row already
    # encodes the network<->place edge (founding-graph Row 9), better formed as
    # fac-unnamed -> loc-dernier-verre (a_to_b), so Row 9 itself is not inserted.
    # We keep this row and only align its intensity to the 1-100 scale (it was a
    # Step-2 placeholder of 50; the founding graph rates this edge 85).
    get_or_create(
        session,
        m.Relation,
        "rel-unnamed-tavern",
        world_id=WORLD_ID,
        entity_a_id="fac-unnamed",
        entity_b_id="loc-dernier-verre",
        type="instrumentalizes",
        direction="a_to_b",
        intensity=85,
        visible_to_b=False,
        notes="Le Dernier Verre sert de point d'appui à L'Innommée ; lien dissimulé.",
    )
    align_relation_intensity(session, "rel-unnamed-tavern", 85)

    # Player -> Maelis: knows her by sight; she doesn't notice him yet.
    get_or_create(
        session,
        m.Relation,
        "rel-player-maelis",
        world_id=WORLD_ID,
        entity_a_id="char-player",
        entity_b_id="npc-maelis",
        type="passive_attention",
        direction="a_to_b",
        intensity=52,
        visible_to_b=False,
        notes="Le joueur connaît Maelis de vue ; elle ne le remarque pas encore.",
    )

    # Player <-> Reike / Senna: neutral, they don't notice him yet.
    get_or_create(
        session,
        m.Relation,
        "rel-player-reike",
        world_id=WORLD_ID,
        entity_a_id="char-player",
        entity_b_id="npc-reike",
        type="indifference",
        direction="a_to_b",
        intensity=50,
        visible_to_b=False,
        notes="Neutre ; Reike ne remarque pas encore le joueur.",
    )
    # Reike -> Player: low-grade suspicion — the reflex of a cop who can't switch off.
    # Intensity 28 (< 30) signals hostility/mistrust in the MJ initiative vote,
    # making Reike a live candidate for spontaneous intervention.
    get_or_create(
        session,
        m.Relation,
        "rel-reike-player",
        world_id=WORLD_ID,
        entity_a_id="npc-reike",
        entity_b_id="char-player",
        type="méfiance",
        direction="a_to_b",
        intensity=28,
        visible_to_b=False,
        notes=(
            "Reike surveille le joueur par réflexe professionnel — un inconnu "
            "silencieux dans un lieu où il vient décompresser. Pas d'hostilité "
            "déclarée, mais l'œil ne le lâche pas."
        ),
    )
    get_or_create(
        session,
        m.Relation,
        "rel-player-senna",
        world_id=WORLD_ID,
        entity_a_id="char-player",
        entity_b_id="npc-senna",
        type="indifference",
        direction="a_to_b",
        intensity=50,
        visible_to_b=False,
        notes="Neutre ; Senna ne remarque pas encore le joueur.",
    )

    # ----- founding NPC / location / faction / magic relation graph ----------
    # Creator-set founding world state, inserted directly (not via
    # proposed_mutation). All intensities on the 1-100 scale, all above 50
    # (attention/interest, none hostile). Row 9 of the brief is intentionally
    # omitted — it duplicates rel-unnamed-tavern above.

    # 1. Senna observes Maelis, suspects what she hides; Maelis doesn't perceive it.
    get_or_create(
        session,
        m.Relation,
        "rel-senna-maelis",
        world_id=WORLD_ID,
        entity_a_id="npc-senna",
        entity_b_id="npc-maelis",
        type="passive_attention",
        direction="a_to_b",
        intensity=68,
        visible_to_b=False,
        notes="Senna observe Maelis, soupçonne ce qu'elle cache sur le lieu. Maelis ne le perçoit pas.",
    )

    # 2. Maelis keeps a discreet eye on Reike (Guard); he thinks he's unnoticed.
    get_or_create(
        session,
        m.Relation,
        "rel-maelis-reike",
        world_id=WORLD_ID,
        entity_a_id="npc-maelis",
        entity_b_id="npc-reike",
        type="passive_attention",
        direction="a_to_b",
        intensity=60,
        visible_to_b=False,
        notes="Maelis sait Reike de la Garde, le surveille discrètement (l'info a de la valeur). Reike se croit inaperçu.",
    )

    # 3. Reike notices the old woman "knows something" — vague cop's curiosity.
    get_or_create(
        session,
        m.Relation,
        "rel-reike-senna",
        world_id=WORLD_ID,
        entity_a_id="npc-reike",
        entity_b_id="npc-senna",
        type="fascination",
        direction="a_to_b",
        intensity=58,
        visible_to_b=False,
        notes="Reike remarque que la vieille femme « sait quelque chose ». Curiosité de flic, encore vague.",
    )

    # 4. Senna spotted a man who doubts the official line — ally or risk; she waits.
    get_or_create(
        session,
        m.Relation,
        "rel-senna-reike",
        world_id=WORLD_ID,
        entity_a_id="npc-senna",
        entity_b_id="npc-reike",
        type="passive_attention",
        direction="a_to_b",
        intensity=63,
        visible_to_b=False,
        notes="Senna a repéré un homme qui doute de la version officielle — allié potentiel ou risque. Elle attend.",
    )

    # 5. The tavern is Maelis's asset: neutrality = cover, a listening post.
    get_or_create(
        session,
        m.Relation,
        "rel-maelis-verre",
        world_id=WORLD_ID,
        entity_a_id="npc-maelis",
        entity_b_id="loc-dernier-verre",
        type="interest",
        direction="a_to_b",
        intensity=88,
        visible_to_b=False,
        notes="Le lieu est son atout. Neutralité = couverture. Elle le protège et s'en sert comme poste d'écoute.",
    )

    # 6. Senna returns because the place is sensitive; the location draws her.
    get_or_create(
        session,
        m.Relation,
        "rel-senna-verre",
        world_id=WORLD_ID,
        entity_a_id="npc-senna",
        entity_b_id="loc-dernier-verre",
        type="fascination",
        direction="a_to_b",
        intensity=75,
        visible_to_b=False,
        notes="Senna revient parce que le lieu est sensible. C'est le lieu qui l'attire, pas la clientèle.",
    )

    # 7. Reike comes to unwind, not suspecting what's at play.
    get_or_create(
        session,
        m.Relation,
        "rel-reike-verre",
        world_id=WORLD_ID,
        entity_a_id="npc-reike",
        entity_b_id="loc-dernier-verre",
        type="interest",
        direction="a_to_b",
        intensity=63,
        visible_to_b=False,
        notes="Un refuge où personne ne parle boutique. Il vient décompresser, sans soupçonner ce qui s'y joue.",
    )

    # 8. Maelis knowingly serves The Unnamed and will always deny it.
    get_or_create(
        session,
        m.Relation,
        "rel-maelis-unnamed",
        world_id=WORLD_ID,
        entity_a_id="npc-maelis",
        entity_b_id="fac-unnamed",
        type="shared_secret",
        direction="a_to_b",
        intensity=95,
        visible_to_b=True,
        notes="Elle sert sciemment L'Innommée et le niera toujours. Lien fort, jamais admis publiquement.",
    )

    # 10. Magic "lingers" gently on the place (magic as actor: a_to_b).
    get_or_create(
        session,
        m.Relation,
        "rel-magic-verre",
        world_id=WORLD_ID,
        entity_a_id="magic-verkhaal",
        entity_b_id="loc-dernier-verre",
        type="passive_attention",
        direction="a_to_b",
        intensity=60,
        visible_to_b=True,
        notes="La magie « s'attarde » doucement sur le lieu. Phénomènes légers non négatifs. Cause inconnue, lien au nœud non confirmé.",
    )

    # 11. Senna perceives magic's presence without mastering it (magic as actor).
    get_or_create(
        session,
        m.Relation,
        "rel-magic-senna",
        world_id=WORLD_ID,
        entity_a_id="magic-verkhaal",
        entity_b_id="npc-senna",
        type="passive_attention",
        direction="a_to_b",
        intensity=58,
        visible_to_b=True,
        notes="Senna perçoit la présence de la magie sans la maîtriser. Cohérent avec le savoir des Marcheurs.",
    )


def main() -> None:
    with Session(engine) as session:
        seed(session)
        session.commit()

    print("=== Verkhaal pilot seed ===")
    print(f"Database: {engine.url}")
    print(
        f"Created {len(_created)}, updated {len(_updated)}, "
        f"deleted {len(_deleted)}; {len(_existing)} unchanged."
    )
    for label, sign, rows in (
        ("New rows", "+", _created),
        ("Updated rows", "~", _updated),
        ("Deleted rows", "-", _deleted),
    ):
        if rows:
            print(f"\n{label}:")
            for table, id in rows:
                print(f"  {sign} {table}: {id}")

    if _audit:
        print("\nRelation intensity audit:")
        for line in _audit:
            print(f"  {line}")

    # Verification: knowledge granularity on the affected NPCs.
    with Session(engine) as session:
        print("\nKnowledge after seed (affected NPCs):")
        for npc in ("npc-maelis", "npc-reike", "npc-senna"):
            rows = session.exec(
                select(m.Knowledge)
                .where(m.Knowledge.entity_id == npc)
                .order_by(m.Knowledge.id)
            ).all()
            shareable = sum(1 for k in rows if not k.is_secret)
            print(f"  {npc}  ({shareable} shareable / {len(rows)} total):")
            for k in rows:
                flag = "SECRET   " if k.is_secret else "shareable"
                print(
                    f"    - [{flag}] {k.subject} "
                    f"(level={k.level}, threshold={k.share_threshold})"
                )

        # Verification: the full relation graph.
        rels = session.exec(select(m.Relation).order_by(m.Relation.id)).all()
        print(f"\nRelation graph ({len(rels)} edges):")
        for r in rels:
            vis = "vis" if r.visible_to_b else "hid"
            print(
                f"    {r.entity_a_id} -> {r.entity_b_id}  "
                f"[{r.type}, {r.direction}, {r.intensity}, {vis}]"
            )


if __name__ == "__main__":
    main()
