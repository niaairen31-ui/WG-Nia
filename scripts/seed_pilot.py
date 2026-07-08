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
from world_engine.prompt_store import list_versions  # noqa: E402
from world_engine.writes import write_membership, write_prompt_version  # noqa: E402

WORLD_ID = "verkhaal"

# ----- BRIEF-10: skill sheet test player character ---------------------------
# A second player character, dedicated to exercising the new `skill` table
# (cockpit "Fiche" view) without touching the live `char-player` (Joran).
# The creator renames SKILL_SHEET_PC_NAME before running this seed for real
# testing; SKILL_SHEET_PC_ID stays a stable slug either way.
SKILL_SHEET_PC_ID = "char-pc-test-2"
SKILL_SHEET_PC_NAME = "PC_TEST_2"
SKILL_DOMAINS = m.BASE_SKILL_DOMAINS  # single source of truth (schema v1.63)

# ----- BRIEF-55: pilot custom skill catalogue (schema v1.63) ----------------
# Names are illustrative test fixtures for the world-scoped skill catalogue
# (item 7 of the brief) — exercises both readers (arbiter + MJ narration).
SKILL_DEF_DIPLOMATIE_ID = "skilldef-pilot-diplomatie"
SKILL_DEF_PISTAGE_ID = "skilldef-pilot-pistage"

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


def ensure_primary_membership(session: Session, world_id: str, entity_id: str, faction_id: str) -> None:
    """Open an `is_primary=TRUE` membership for `entity_id` in `faction_id`, idempotently.

    Recables seed NPC faction assignment onto `faction_membership` (BRIEF-28,
    schema v1.40). The seed's old `faction_id` IDs are already backfilled
    into `faction_membership` by migrate_v1_38/v1_39 on any pre-existing DB,
    so a second seed run must not try to open a duplicate active row.
    """
    existing = session.exec(
        select(m.FactionMembership).where(
            m.FactionMembership.entity_id == entity_id,
            m.FactionMembership.faction_id == faction_id,
            m.FactionMembership.left_at.is_(None),
        )
    ).first()
    if existing is not None:
        _existing.append((m.FactionMembership.__tablename__, f"{entity_id}->{faction_id}"))
        return
    membership = write_membership(
        session,
        mode="open",
        world_id=world_id,
        entity_id=entity_id,
        faction_id=faction_id,
        role=None,
        is_primary=True,
        is_secret=False,
    )
    _created.append((m.FactionMembership.__tablename__, membership.id))


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


def upsert_prompt_template(
    session: Session, id: str, *, system_prompt: str, user_template: str, **head_fields
):
    """Create or update a prompt template HEAD row; text lives in `prompt_version`.

    S2 (TICKET-0011, locked): a head absent -> create the head, then write v1
    via `write_prompt_version`. A head already present with >= 1 version ->
    NEVER touch text again (creator sovereignty is absolute — seed wording
    improvements no longer propagate to an already-seeded DB). A head
    present with ZERO versions is only reachable mid-bootstrap on a
    pre-migration DB — abort with a clear message rather than guessing.

    Non-text head fields (name, variables, destination, notes, is_active)
    keep the pre-existing converge-on-diff behavior, unchanged.
    """
    obj = session.get(m.PromptTemplate, id)
    if obj is None:
        obj = m.PromptTemplate(id=id, **head_fields)
        session.add(obj)
        write_prompt_version(
            session,
            template_id=obj.id,
            system_prompt=system_prompt,
            user_template=user_template,
            note="seed v1",
        )
        _created.append((m.PromptTemplate.__tablename__, id))
        return obj

    if not list_versions(session, obj.id):
        raise SystemExit(
            f"prompt_template {id!r} exists with zero prompt_version rows — "
            "run scripts/migrate_v1_68_prompt_version.py before re-seeding."
        )

    changed = False
    for key, value in head_fields.items():
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


def merge_entity_metadata(session: Session, entity_id: str, updates: dict) -> None:
    """Read-merge-write into entity.metadata_ without clobbering other keys.

    Same discipline as the cockpit's Tarifs editor (BRIEF-20): existing keys
    (e.g. physical_tier) survive untouched. Idempotent — a second run with
    unchanged values records nothing changed.
    """
    entity = session.get(m.Entity, entity_id)
    if entity is None:
        return
    merged = dict(entity.metadata_ or {})
    changed = False
    for key, value in updates.items():
        if merged.get(key) != value:
            merged[key] = value
            changed = True
    if changed:
        entity.metadata_ = merged
        _updated.append((m.Entity.__tablename__, entity_id))


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
  "mutation_type"  (string) — relation_change | new_knowledge | knowledge_change | event_creation | status_change | entity_creation | resource_change | goal_change | other
  "target_table"   (string) — relation | knowledge | event | entity | character | location | faction | artifact | ledger | npc_goal | other
  "target_id"      (string or null) — id of the row to update; null for a new row
  "payload"        (object) — fields matching the target table (see below)
  "rationale"      (string) — one line quoting or summarising the evidence

Payload shapes:
  relation_change  → {"entity_a_id":"…","entity_b_id":"…","relation_type":"…","intensity_delta":<signed int>}
  new_knowledge    → {"entity_id":"…","subject":"…","level":"rumor|partial|knows|…","content":"…","source":"…"}
  knowledge_change → {"entity_id":"…","subject":"…","field":"…","new_value":"…"}
  event_creation   → {"title":"…","description":"…","type":"social|political|other","involved_entities":[…]}
  resource_change  → {"entity_id":"char-player","amount":<signed int>,"counterparty_id":"…","reason":"…","knowledge":{"entity_id":"…","subject":"…","level":"…","content":"…","source":"…","is_secret":false} (knowledge is OPTIONAL — only when information changed hands)}
  goal_change      → {"action":"complete|abandon|create_short","goal":"…"}

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
  - "[JOUEUR] grabs le PNJ by the collar and slams him against the wall"
    → relation_change, NEGATIVE delta.
  - "[JOUEUR] pulls le PNJ out of the way of the falling crate"
    → relation_change, POSITIVE delta.
  - "[JOUEUR] shoves past le PNJ to reach the door, knocking the table over"
    → relation_change, NEGATIVE delta.

Only report changes that ACTUALLY happened in the transcript. Idle chat → [].

=== ANTI-INFLATION RUBRIC (relation_change, multi-turn window) ===
This transcript may span several turns and several NPCs. For relation_change:
  - Emit AT MOST ONE relation_change per ordered pair (entity_a_id,
    entity_b_id) for the ENTIRE window — never one per turn or per exchange.
    If several moments in the window affected the same pair, merge them into
    a single payload whose intensity_delta is the NET effect across the
    whole window, not a sum of per-turn increments.
  - A cordial, routine, or merely polite exchange (greetings, small talk,
    ordinary service) is NOT by itself grounds for a relation_change. Report
    one only when something in the window would plausibly change how the two
    parties feel about each other (a promise, a betrayal, a kindness, a
    threat, a shared risk, a revealing admission).
  - Keep |intensity_delta| proportionate to the weight of the event: a minor
    courtesy is worth about 1-3, a meaningful gesture or admission about
    4-8, a serious betrayal, rescue, or attack about 9-15. Do not pad deltas
    to make a window "feel" eventful — idle chat → [].

=== RESOURCE_CHANGE RUBRIC ===
resource_change — émets-en un UNIQUEMENT quand de la monnaie change
réellement de main et que le SOLDE DU JOUEUR bouge : une somme a été
convenue ET l'échange a lieu dans la scène (pas seulement évoquée ou
marchandée sans conclusion). `amount` = la somme convenue, entier en
unité de base, signée du point de vue du joueur (négatif s'il paie,
positif s'il reçoit). `counterparty_id` = le PNJ en face. N'INVENTE
JAMAIS un prix que le dialogue n'a pas énoncé — tu enregistres ce qui a
été convenu, tu ne tarifes pas. N'émets PAS de resource_change pour un
échange d'argent entre PNJ (le solde des PNJ n'est pas suivi). Ajoute le
bloc `knowledge` SEULEMENT quand l'objet de la transaction est une
information, et que c'est le joueur (achat) ou un PNJ (le joueur vend une
info) qui l'acquiert — `content` recopié de ce qui a été dit, jamais
inventé.

=== GOAL_CHANGE RUBRIC ===
goal_change — le bloc NPC CONTEXT peut contenir une section
« TES OBJECTIFS » listant les objectifs actifs du PNJ. Émets un
goal_change UNIQUEMENT quand la fenêtre contient une preuve claire
qu'un de CES objectifs listés est accompli ("action":"complete") ou
définitivement abandonné ("action":"abandon"), ou que le PNJ forme une
NOUVELLE intention concrète à court terme ("action":"create_short").
Recopie le texte de l'objectif EXACTEMENT tel qu'il figure dans
« TES OBJECTIFS » — jamais de paraphrase. Pour create_short, écris le
nouvel objectif en UNE phrase commençant par un verbe à l'infinitif.
Parler d'un objectif, ou progresser sans conclure, ne justifie PAS de
goal_change. Émets AU PLUS UN goal_change par objectif pour toute la
fenêtre. N'invente jamais d'objectif absent de la section.

=== EXEMPLE 1 (la relation se réchauffe) ===
Transcript :
[JOUEUR] Cela fait deux ans que je viens ici.
[PNJ] Deux ans, oui. Je vous reconnais. Vous ne causez jamais d'ennuis. J'apprécie.
Output:
[{"mutation_type":"relation_change","target_table":"relation","target_id":"rel-a-player","payload":{"entity_a_id":"npc-a","entity_b_id":"char-player","relation_type":"passive_attention","intensity_delta":6},"rationale":"Le PNJ a explicitement reconnu le joueur et l'a évalué positivement — la confiance se réchauffe."}]

=== EXEMPLE 2 (le joueur apprend un fait) ===
Transcript :
[JOUEUR] On dit que des voyageurs disparaissent sur la route ?
[PNJ] On le dit, oui. Les patrouilles ont doublé depuis un mois. Personne ne sait pourquoi.
Output:
[{"mutation_type":"new_knowledge","target_table":"knowledge","target_id":null,"payload":{"entity_id":"char-player","subject":"disparitions_route","level":"rumor","content":"Le PNJ confirme des rumeurs de disparitions et un doublement des patrouilles depuis un mois.","source":"conversation avec le PNJ"},"rationale":"Le PNJ a directement confirmé la rumeur — le joueur dispose maintenant d'une corroboration externe."}]

=== EXEMPLE 3 (fenêtre multi-tours, échange banal → rien à enregistrer) ===
Transcript :
[JOUEUR] Bonsoir.
[PNJ] Bonsoir.
[JOUEUR] Une chambre pour la nuit, c'est possible ?
[PNJ] Bien sûr. Deuxième porte à gauche.
[JOUEUR] Merci, c'est aimable.
[PNJ] C'est mon métier, mais je vous en prie.
Output:
[]

=== EXEMPLE 4 (le joueur achète une information à prix convenu) ===
Transcript :
[JOUEUR] Je te donne 15 pièces pour ce que tu sais sur le Conseil.
[PNJ] Quinze, d'accord. Le Conseil cache l'un de ses propres membres.
[JOUEUR] Tiens.
[PNJ] Plaisir de faire affaire.
Output:
[{"mutation_type":"resource_change","target_table":"ledger","target_id":null,"payload":{"entity_id":"char-player","amount":-15,"counterparty_id":"npc-b","reason":"achat d'une information sur le Conseil","knowledge":{"entity_id":"char-player","subject":"conseil_secret","level":"rumor","content":"Le Conseil cache l'un de ses propres membres.","source":"acheté au PNJ","is_secret":false}},"rationale":"Le joueur a payé 15 pièces, le PNJ a énoncé le prix et l'information, l'échange s'est conclu dans la scène."}]

=== EXEMPLE 5 (un objectif listé est accompli) ===
NPC CONTEXT (extrait) :
TES OBJECTIFS
[COURT TERME] Convaincre le forgeron de réparer la herse avant la foire
Transcript :
[PNJ] Alors, c'est entendu ? Elle sera réparée avant la foire ?
[JOUEUR] Le forgeron a accepté ce matin. C'est réglé.
[PNJ] Enfin ! Voilà un poids en moins.
Output:
[{"mutation_type":"goal_change","target_table":"npc_goal","target_id":null,"payload":{"action":"complete","goal":"Convaincre le forgeron de réparer la herse avant la foire"},"rationale":"Le PNJ apprend que la réparation est acquise — l'objectif listé est accompli."}]"""

CONVERSATION_ANALYSIS_USER_TEMPLATE = """\
NPC CONTEXT (what the NPC was authorised to know):
{injected_context}

TRANSCRIPT:
{transcript}

JSON array of canon mutations ([] if nothing changed):"""


# Overhearing classification prompt — Tier 4, acquisition-only pass.
# usage='overhearing_classification', world_id=NULL, destination='local'.
# The model's ONLY job is closed-list classification; attribution, receiver
# computation, and level computation happen in code (analyzer.analyze_overhearing).
# Variables substituted with str.replace() in analyzer.py: {subject_list},
# {player_line}, {npc_line}.
OVERHEARING_CLASSIFICATION_SYSTEM_PROMPT = """\
You classify a single RPG conversation turn against a closed list of
knowledge subjects. You NEVER invent subjects. You NEVER add subjects
that are not in the provided list.

A subject matches ONLY if the line substantively asserts, reveals, or
discusses information about it. A mere mention of a name in passing,
small talk, greetings, or atmosphere does NOT match.

Output ONLY a JSON array. Each element: {"subject": "<exact subject
string from the list>", "speaker": "player" | "npc"}. The speaker is
the one whose line carries the information. If nothing matches, output
[]. An empty array is a normal, expected result for most turns."""

OVERHEARING_CLASSIFICATION_USER_TEMPLATE = """\
Known world subjects (closed list):
{subject_list}

Turn to classify:
[JOUEUR] {player_line}
[PNJ] {npc_line}

JSON array:"""


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
  Correct   : Mira hausse les épaules. / Elle jette un regard vers lui.
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
Cette taverne est mon domaine. » Je jette un regard vers un client.

Bonne narration MJ :
Mira hausse les épaules, un rien amusée. « Je sers mon propre intérêt, monsieur. \
Cette taverne est mon domaine. » Elle jette un regard vers un client, au fond de \
la salle.

Explication : les actions de la PNJ (« Je hausse », « Je jette ») sont converties à \
la troisième personne (« Mira hausse », « Elle jette ») ; le discours entre \
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
# schema v1.19), extracts used_object for the code-side possession check
# (binary ownership check since BRIEF-08/D2a.1 — equip_action removed).
# Usage = 'mj_interpretation', called before the NPC so scene turns can skip
# the NPC entirely. Non-streaming JSON call; /no_think appended at call time.
# world_id = NULL.
MJ_INTERPRETATION_SYSTEM_PROMPT = """\
Tu es un routeur de scène pour un jeu de rôle à la première personne du joueur.
Tu lis l'input du joueur et tu classes le tour en exactement un des 6 modes.

MODES :
- dialogue      : le joueur parle, pose une question ou sollicite une réponse du PNJ
                  (même si combiné à un geste). MODE PAR DÉFAUT en cas de doute.
- physical      : le joueur tente une action physique dont l'issue est incertaine
                  (grimper, bousculer, esquiver, forcer une porte, se faufiler,
                  résister physiquement, retenir quelqu'un ; chercher activement
                  quelque chose de précis — fouiller la pièce, chercher un passage,
                  examiner les étagères pour trouver quelque chose...) — un jet de
                  dés pourrait aussi bien réussir qu'échouer.
                  Test de distinction observation/fouille : chercher activement
                  quelque chose de précis (un objet, un indice, un passage) =
                  physical ; simplement observer l'ambiance sans rien chercher de
                  précis = scene. Un geste simple sans enjeu reste npc_reaction.
- npc_reaction  : le joueur fait une action visible, dirigée vers le PNJ ou clairement
                  remarquée par lui, SANS lui adresser la parole, ET dont l'issue
                  n'est pas incertaine (exemples : tape sur la table, le fixe, pose
                  une pièce en silence, sort brusquement, croise son regard, lui
                  tend un objet sans rien dire).
- scene         : le joueur agit sur l'environnement sans engager le PNJ et sans
                  enjeu incertain (se déplace, observe la salle, inspecte un objet,
                  attend, décrit une attitude générale non dirigée).
- join          : le joueur exprime l'intention de s'approcher d'un groupe de
                  personnes présentes et de s'installer avec elles (exemples :
                  « je rejoins les deux près du feu », « je vais m'asseoir avec
                  eux », « je m'approche du groupe au comptoir »). Pertinent
                  UNIQUEMENT si « Votre situation » indique que le joueur n'a
                  encore rejoint aucun groupe — sinon, ignore cette option et
                  classe normalement (dialogue/physical/npc_reaction/scene).
- travel        : le joueur exprime l'intention de QUITTER le lieu courant pour
                  un lieu voisin ou connu, sans résistance ni issue incertaine
                  (exemples : « je sors de la taverne », « je quitte les lieux »,
                  « je vais à la place du marché », « je rentre chez moi »).
                  Distinct de scene : se déplacer DANS le lieu courant
                  (« je m'approche du comptoir », « je vais près du feu »,
                  « j'inspecte une étagère ») reste scene — le joueur ne quitte
                  pas le lieu. Distinct de physical : sortir CONTRE une
                  résistance, en se faufilant ou en forçant un passage — issue
                  incertaine — reste physical.

RÈGLE DE DÉCISION :
0. Le joueur n'a rejoint aucun groupe ET son input décrit l'intention de
   s'approcher / s'installer avec des gens présents → join (priorité absolue
   sur les autres modes).
1. Sinon, y a-t-il des mots, une question ou une sollicitation adressés au PNJ ? → dialogue.
2. Sinon, l'action décrit-elle une tentative physique dont l'issue est incertaine
   (un jet de dés pourrait échouer ou réussir), y compris une fouille active ? → physical.
3. Sinon, le joueur exprime-t-il l'intention de QUITTER le lieu courant pour un
   autre lieu (sortir, partir, se rendre ailleurs), sans résistance ni
   incertitude ? → travel.
4. Y a-t-il un geste ou une action clairement dirigés vers le PNJ, sans parole,
   à l'issue certaine ? → npc_reaction.
5. Sinon → scene.
QUAND INCERTAIN entre dialogue et les autres → dialogue (mieux qu'elle parle trop que pas assez).

Pour le mode join UNIQUEMENT, ajoute un champ "reference" : reprends tels quels
les mots du joueur qui désignent le groupe visé (un nom de personne, une
description de lieu ou d'activité — ex. « les deux près du feu », « la
patronne et le garde », « ceux qui jouent aux cartes »). Pour le mode travel UNIQUEMENT, le
champ "reference" reprend tels quels les mots du joueur qui désignent la
destination visée (ex. « la place du marché », « chez moi », « la sortie ») —
ou laisse-le vide si aucune destination n'est nommée. Pour tous les autres
modes, laisse "reference" vide.

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
{"mode":"dialogue|physical|npc_reaction|scene|join|travel","reason":"<une phrase courte d'explication>","reference":"<vide sauf join/travel>","used_object":"<nom canonique>|unknown_object|null"}\
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

# Arbiter classification for physical-resolution turns (BRIEF-11, schema v1.23).
# usage = "mj_arbitration". Fired only for ResponseMode.physical, between phase 0
# (mj_interpretation) and the NPC phase. Classifies ONLY — domain + optional NPC
# opposition; never rolls, never decides outcomes. Non-streaming JSON call;
# /no_think appended at call time. world_id = NULL.
MJ_ARBITER_SYSTEM_PROMPT = """\
Tu es l'arbitre d'un jeu de rôle. Le joueur vient de tenter une action physique
dont l'issue est incertaine (grimper, bousculer, esquiver, forcer, se faufiler,
résister...). Ta tâche : classer cette action selon QUATRE axes, RIEN d'autre.

1. DOMAINE — choisis exactement un élément parmi les domaines de base et les
   compétences spécialisées de ce monde.
   Domaines de base : physical / agility / perception / composure
   Compétences spécialisées de ce monde : {custom_skill_names}
   Une compétence spécialisée raffine un domaine de base : choisis-la quand
   l'action correspond précisément à son intitulé ; sinon choisis le domaine
   de base. S'il n'existe aucune compétence spécialisée pertinente, choisis
   simplement le domaine de base.

2. OPPOSITION — l'action vise-t-elle directement un PNJ présent (bousculer,
   désarmer, retenir, esquiver son coup...) ?
   - Si oui : indique le NOM EXACT du PNJ tel qu'il apparaît dans la liste
     fournie. Ne traduis pas, n'invente pas, ne déduis pas un PNJ absent de
     la liste.
   - Si l'action ne vise personne (escalader un mur, sauter un fossé, se
     faufiler dans l'ombre) : null.

3. CONTRAINTE APPLIQUÉE — L'action est-elle une RÉSISTANCE à une tentative
   d'un PNJ de contraindre physiquement le joueur ? Si le joueur ÉCHOUE,
   quelle contrainte subirait-il ?
   - "restrained"  : le PNJ tente de l'immobiliser, ligoter, retenir, plaquer.
   - "gagged"      : le PNJ tente de le bâillonner.
   - "blindfolded" : le PNJ tente de lui bander les yeux.
   - null : aucune contrainte en jeu (action offensive, environnementale, etc.)
   En cas de doute : null.

4. VIOLENT — L'action implique-t-elle un risque de blessure physique pour le
   joueur (coup, arme, chute dangereuse, combat) ?
   - true  : oui, une blessure est un résultat plausible.
   - false : non (action d'esquive pure, acrobatie sans danger mortel, etc.)

Tu ne juges JAMAIS la réussite ou l'échec — cela est déterminé ailleurs par un
jet de dés. Tu ne narres rien.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :
{"domain":"<un domaine de base ou une compétence spécialisée listée ci-dessus>","opposed_npc_id":"<nom exact ou null>","applies_constraint":"restrained|gagged|blindfolded|null","violent":true|false}\
"""

MJ_ARBITER_USER_TEMPLATE = """\
PNJ présents : {npc_list}

Action du joueur → {player_line}\
"""

# Entry narration — scene-establishing description on location entry (schema
# v1.30, BRIEF-17; CHANGEMENTS block + scoped naming rule added schema v1.71,
# BRIEF-0016-a). usage = "mj_establishment". Single non-streamed chat() call,
# thinking mode allowed, fired on EVERY entry (G1). Carries the SAME
# anti-invention rule as pt-mj-narration: describe ONLY from the provided
# context. Names NPCs ONLY via the CHANGEMENTS block (RECON-0016 F3) — a
# presently-present NPC is still never named or described, the scene UI's
# gathering list already shows who is present. world_id = NULL.
MJ_ESTABLISHMENT_SYSTEM_PROMPT = """\
Tu es le maître de jeu (MJ) d'un jeu de rôle. Le joueur vient d'entrer dans un \
lieu. Ton travail : décrire en 3 à 4 lignes de prose française ce que le \
joueur perçoit en y pénétrant — le lieu lui-même, son atmosphère, tout \
signe perceptible qui y est signalé, et ce qui a changé depuis sa dernière \
visite.

=== RÈGLE — DÉCRIRE UNIQUEMENT À PARTIR DU CONTEXTE FOURNI ===
N'invente aucun objet, lettre, passage, indice ou PNJ qui ne figure pas dans \
le contexte ci-dessous. Si la liste des signes perceptibles est vide ou \
indique qu'il n'y a rien de particulier, établis la scène nue à partir du \
lieu et de son ambiance seuls — ne comble jamais ce vide par une invention.

=== RÈGLE — PNJ NOMMÉS UNIQUEMENT DANS LES CHANGEMENTS ===
Les PNJ cités dans le bloc CHANGEMENTS DEPUIS LA DERNIÈRE VISITE (parti·e·s \
ou arrivé·e·s) peuvent être nommés — leur départ ou leur arrivée est \
précisément l'information à transmettre. Tout PNJ actuellement présent reste \
interdit de nom ou de description : qui s'y trouve MAINTENANT est montré \
ailleurs, pas dans cette narration.

=== RÈGLE — CHANGEMENTS : NE RIEN INVENTER ===
Si le bloc CHANGEMENTS DEPUIS LA DERNIÈRE VISITE indique qu'il n'y a rien de \
notable, ne mentionne aucun changement et n'en invente aucun.

=== FORMAT ===
Prose narrative en français, 3 à 4 lignes. Rien d'autre — pas de JSON, pas \
de méta, pas de guillemets de citation (il n'y a pas de PNJ qui parle ici).\
"""

MJ_ESTABLISHMENT_USER_TEMPLATE = """\
Lieu : « {location_name} ».
{description}
Ambiance : {subculture}

Signes perceptibles à l'entrée :
{signposts}

CHANGEMENTS DEPUIS LA DERNIÈRE VISITE :
{changes}

Narration d'établissement :\
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

# BRIEF-24: AI entity-authoring assistant (NPC). usage = "entity_generation".
# Creator-side draft generator — entity_author.generate_entity_draft formats
# this user_template with {entity_type}, {type_fields}, {brief}; system_prompt
# is passed verbatim (NOT .format()'d, so it carries no variables itself).
# world_id = NULL. Type-parameterized: only "character" is populated in
# entity_author._TYPE_FIELDS for this brief (A1) — adding another entity type
# later is a config entry there, not a change to this template.
ENTITY_GENERATION_SYSTEM_PROMPT = """\
Tu es l'assistant de création du créateur d'un monde de jeu de rôle. Le \
créateur te donne une intention en une phrase pour une nouvelle entité ; ton \
travail est de proposer un brouillon cohérent que le créateur relira et \
éditera avant qu'il n'entre dans le canon. Tu ne crées rien toi-même — tu \
proposes seulement, et le créateur juge.

=== STRUCTURE — DEUX BLOCS, PUBLIC ET SECRET ===
Ta réponse est TOUJOURS un objet JSON avec exactement deux clés de premier \
niveau : "public" et "secret".
- "public" : tout ce qui est perceptible ou partageable dans la fiction.
- "secret" : tout ce que cette entité SAIT mais CACHE — ses savoirs secrets, \
une note de méta-narration pour le créateur, et qui pourrait déjà s'en \
douter. Ne reporte JAMAIS un élément du bloc "secret" dans le bloc "public" \
— la séparation doit être nette dès ta première proposition.

Le message suivant précise les champs attendus dans chaque bloc pour ce \
type d'entité — respecte exactement ces noms de champs.

=== RÈGLE — NE RIEN INVENTER HORS DE L'INTENTION ===
Réponds à l'intention donnée sans ajouter de personnages, lieux ou factions \
non nommés, sauf si un champ demandé l'exige explicitement (ex. une faction \
d'appartenance plausible si l'intention n'en précise pas).

=== FORMAT DE SORTIE ===
Réponds UNIQUEMENT avec l'objet JSON demandé — aucun texte avant ou après, \
aucun bloc de code Markdown, aucun commentaire.\
"""

ENTITY_GENERATION_USER_TEMPLATE = """\
Type d'entité : {entity_type}

Champs attendus :
{type_fields}

Intention du créateur : {brief}

Brouillon JSON :\
"""

# TICKET-0013/BRIEF-0013-b: NPC goal generator (T1). usage =
# "npc_goal_generation". world_id = NULL. Calls go through
# entity_author.generate_npc_goals, which writes no canon — pure
# generate-and-return, one long + two short goals per call (M2).
NPC_GOALS_SYSTEM_PROMPT = """\
Tu es un assistant d'écriture pour un jeu de rôle. On te donne l'identité \
d'un personnage non-joueur (PNJ). Tu produis ses objectifs personnels : \
exactement 1 objectif à long terme et 2 objectifs à court terme.

Règles :
- L'objectif long terme est une ambition ou un désir profond, cohérent avec \
l'identité et le passé du personnage.
- Les objectifs court terme sont des intentions concrètes, actionnables dans \
les jours qui viennent, au service de l'objectif long terme ou d'une \
préoccupation immédiate.
- Chaque objectif tient en UNE seule phrase, commençant par un verbe à \
l'infinitif.
- N'invente aucun nom propre absent des informations fournies.
- Si des objectifs de faction sont fournis, le personnage peut y adhérer, \
s'en écarter ou les subvertir — selon son caractère.

Tu réponds UNIQUEMENT avec un objet JSON, sans texte autour :
{"long": "…", "shorts": ["…", "…"]}\
"""

NPC_GOALS_USER_TEMPLATE = """\
PNJ : {npc_name}
Description : {npc_description}
Passé : {npc_backstory}
Objectifs de sa faction : {faction_goals}\
"""

# TICKET-0014/BRIEF-0014-a: world-tick briefing (K2/T1). usage = "world_tick".
# world_id = NULL. The RUNNER (BRIEF-0014-b) formats user_template with
# {tick_context} (from tick.assemble_tick_context) and {interval_label}
# (creator-chosen at invocation) — this brief ships only the prompt contract
# and the read-side builder; no call site exists yet. English-bodied (mirrors
# pt-conversation-analysis); French only in quoted markers/labels and
# {interval_label} values, since the briefing itself is French.
WORLD_TICK_SYSTEM_PROMPT = """\
You advance ONE NPC's life off-screen in an RPG world. You receive the
NPC's private briefing (identity, goals, knowledge, relations,
affiliations, location, who is around) and an elapsed interval. Decide
what this NPC plausibly DID during that interval, acting on its goals
and on what it knows — then report the world-state changes.

Output: a JSON array only. No prose. No markdown fences. Start with [,
end with ]. A quiet interval is a legitimate answer: output exactly []

Every element must have these EXACT 5 keys — no other keys allowed:
  "mutation_type"  (string) — goal_change | relation_change | new_knowledge | npc_move
  "target_table"   (string) — npc_goal | relation | knowledge | character
  "target_id"      (null)   — always null
  "payload"        (object) — see shapes below
  "rationale"      (string) — one line: what the NPC did that caused this change

Reference people and places by NAME exactly as written in the briefing.
Never invent identifiers, ids, people, or places absent from the briefing.

Payload shapes:
  goal_change      -> {"action":"complete|abandon|create_short","goal":"…"}
  relation_change  -> {"other":"<name from the briefing>","relation_type":"…","intensity_delta":<signed int>}
  new_knowledge    -> {"recipient":"self" | "<name>","subject":"<short_slug>","level":"rumor|partial|knows","content":"…","source":"…","is_secret":true|false,"secret_derived":true|false}
  npc_move         -> {"destination":"<name from OÙ TU PEUX ALLER>"}

=== GOAL_CHANGE RULES ===
For "complete"/"abandon": copy the goal text EXACTLY as it appears in
TES OBJECTIFS — never paraphrase. Emit one ONLY when the interval
plausibly finished or definitively killed that goal; progress without
conclusion is NOT a goal_change. For "create_short": one sentence
starting with an infinitive verb. AT MOST ONE goal_change per listed
goal.

=== RELATION_CHANGE RULES ===
AT MOST ONE relation_change per counterpart for the ENTIRE interval —
the NET effect, never per-event increments. Keep |intensity_delta|
proportionate: minor courtesy 1-3, meaningful gesture or admission 4-8,
serious betrayal, rescue, or attack 9-15. Routine coexistence, ordinary
work, or mere proximity is NOT a relation_change.

=== NEW_KNOWLEDGE RULES ===
"recipient":"self" when the NPC LEARNED something during the interval;
"<name>" when the NPC TOLD that person something. Set
"secret_derived":true when the information comes from a [SECRET] item
in your briefing. Whether the knowledge is secret FOR THE RECIPIENT is
a separate judgment: set "is_secret" by intent — a confidence shared
discreetly stays secret; information wielded openly against an enemy
does not. Never copy [SECRET]/[AFFILIATION SECRÈTE] markers into
"content".

=== NPC_MOVE RULES ===
AT MOST ONE npc_move for the entire interval. "destination" MUST be a
name copied EXACTLY from OÙ TU PEUX ALLER — never a place from anywhere
else in the briefing, never invented. Staying put is legitimate and is
expressed by emitting NO npc_move. A move needs a motive rooted in the
briefing (a goal, a relation, a known fact) stated in "rationale".

=== SCALE ===
The elapsed interval is «{interval_label}». Scale ambition to it: a few
hours move one small step; a few days allow a meeting, an errand, a
discovery; a few weeks may close a short-term goal. Stay inside the
briefing.\
"""

WORLD_TICK_USER_TEMPLATE = """\
NPC BRIEFING:
{tick_context}

INTERVALLE ÉCOULÉ : {interval_label}

Report what changed as a JSON array.\
"""

# BRIEF-47: World-bible generator. usage = "world_generation". Creator-side
# draft generator for a NEW world's premise — entity_author.generate_world_draft
# formats this user_template with only {brief} (no {type_fields}: a world
# isn't typed, and unlike region_author there is no existing world premise to
# read, since this function creates one). World is not an `entity` row, so
# this is a separate template from pt-entity-generation, not a _TYPE_FIELDS
# entry. system_prompt is passed verbatim. world_id = NULL.
WORLD_GENERATION_SYSTEM_PROMPT = """\
Tu es l'assistant de création du créateur d'un monde de jeu de rôle. Le \
créateur te donne une intention en une phrase pour un monde ENTIER ; ton \
travail est de proposer un brouillon de PRÉMISSE cohérent que le créateur \
relira et éditera avant de créer le monde. Tu ne crées rien toi-même — tu \
proposes seulement, et le créateur juge.

=== STRUCTURE — UN SEUL BLOC, PUBLIC ===
Ta réponse est TOUJOURS un objet JSON avec exactement une clé de premier \
niveau : "public", contenant exactement trois champs :
- "name" (string) : un nom de monde court et évocateur.
- "description" (string) : 2 à 4 phrases — genre, ton, géographie générale.
- "fundamental_laws" (tableau de strings) : 0 à 6 contraintes ABSOLUES qui \
s'appliquent à tout le monde (ex. « La magie n'existe pas dans ce monde. », \
« Aucune divinité n'intervient directement. »). Chaque loi est une phrase \
courte et générale — jamais un fait propre à un personnage, un lieu ou une \
faction précis (cela relève d'une génération de région ou d'entité, pas du \
monde).

=== RÈGLE — NE RIEN INVENTER HORS DE L'INTENTION ===
Réponds à l'intention donnée sans ajouter de factions, lieux ou personnages \
nommés — un monde à cette étape n'a encore aucun contenu, seulement une \
prémisse.

=== FORMAT DE SORTIE ===
Réponds UNIQUEMENT avec l'objet JSON demandé — aucun texte avant ou après, \
aucun bloc de code Markdown, aucun commentaire.\
"""

WORLD_GENERATION_USER_TEMPLATE = """\
Intention du créateur : {brief}

Brouillon JSON :\
"""

# BRIEF-52: PC creation assistant. usage = "player_generation". Standalone
# sibling template (NOT a _TYPE_FIELDS entry) — entity_author.generate_player_draft
# formats user_template with only {brief} and parses a single top-level JSON
# object (no public/secret blocks, D1/G1): name, description, appearance,
# backstory, knowledge[]. Never proposes skills, faction, starting location,
# or a secret block — those stay creator-decided (B1/C1/D1).
PLAYER_GENERATION_SYSTEM_PROMPT = """\
Tu es l'assistant de création de personnage joueur du créateur d'un monde \
de jeu de rôle. À partir d'un concept fourni par le créateur, tu proposes \
le brouillon d'UN personnage joueur.

Ta réponse est TOUJOURS un unique objet JSON, et rien d'autre — aucun texte \
avant ou après, aucun bloc Markdown. L'objet a exactement ces clés :

- "name" : le nom du personnage (chaîne).
- "description" : une description publique brève — ce qu'autrui perçoit de \
lui au premier regard (chaîne, 1 à 2 phrases).
- "appearance" : son apparence physique détaillée, pour la référence du \
joueur (chaîne).
- "backstory" : son histoire personnelle, pour la référence du joueur \
(chaîne).
- "knowledge" : un tableau de ce que le personnage sait au départ. Chaque \
élément est un objet { "subject": <chaîne>, "level": <niveau>, \
"content": <chaîne> }. "level" appartient à cette échelle, du plus faible \
au plus fort : "unaware", "rumor", "suspicious", "partial", "knows", \
"fully_understands". Propose 0 à 5 savoirs, jamais davantage.

Tu ne proposes RIEN d'autre : pas de secrets, pas de faction, pas de lieu de \
départ, pas de compétences ni de statistiques. Ces éléments sont décidés \
ailleurs. Si le concept reste vague, comble les trous de façon plausible et \
sobre.\
"""

PLAYER_GENERATION_USER_TEMPLATE = """\
Concept du personnage joueur :

{brief}

Réponds par l'unique objet JSON décrit.\
"""

# BRIEF-56: world-scoped custom skill catalogue authoring. usage =
# "skill_catalogue". Standalone sibling template (NOT a _TYPE_FIELDS entry,
# D2-attach-b) — entity_author.generate_skill_catalogue_draft formats
# user_template with only {brief} and parses a single top-level JSON object
# {"skills": [...]}. The model proposes names + prose + an intended base
# domain only — never a tier, never a structural id; code creates rows/ids
# only on creator accept.
SKILL_CATALOGUE_SYSTEM_PROMPT = """\
Tu es l'assistant de création du créateur d'un monde de jeu de rôle. Le \
créateur te donne une intention en une phrase pour le CATALOGUE DE \
COMPÉTENCES PROPRES à son monde ; ton travail est de proposer une liste de \
compétences additionnelles que le créateur relira, éditera et complétera \
avant qu'elles n'existent réellement. Tu ne crées rien toi-même — tu \
proposes seulement, et le créateur juge.

=== STRUCTURE — UN SEUL OBJET JSON ===
Ta réponse est TOUJOURS un objet JSON avec exactement une clé de premier \
niveau : "skills", un tableau de 3 à 8 objets. Chaque objet a exactement \
trois champs :
- "name" (string) : le nom court de la compétence (ex. « Pistage », \
« Marchandage », « Lecture des courants »).
- "base_domain" (string) : EXACTEMENT un parmi "physical", "agility", \
"perception", "composure" — le domaine de base que cette compétence \
spécialise. N'invente jamais un cinquième domaine.
- "description" (string) : 1 à 2 phrases expliquant ce que cette compétence \
recouvre dans ce monde précis.

=== RÈGLE — RIEN D'AUTRE ===
Ne propose ni tier, ni identifiant, ni lien vers un personnage : ces \
éléments sont décidés ailleurs. Les compétences doivent être spécifiques au \
monde décrit, pas génériques.

=== FORMAT DE SORTIE ===
Réponds UNIQUEMENT avec l'objet JSON demandé — aucun texte avant ou après, \
aucun bloc de code Markdown, aucun commentaire.\
"""

SKILL_CATALOGUE_USER_TEMPLATE = """\
Intention du créateur pour le catalogue de compétences : {brief}

Brouillon JSON :\
"""

# BRIEF-34: Region orchestrator, Stage 0 — manifest. usage = "region_manifest".
# Transforms a free-text creator region brief into a single structured JSON
# manifest (concept + factions/locations/NPCs by name, with by-name
# relationships) and nothing else. The manifest is consumed by
# region_author.generate_region_draft, which code-judges it (dedup, root
# location enforcement, name resolution) before composing the atomic
# generators across it. No counts are prescribed here or in code — density
# is entirely the model's response to the brief.
# The two "au moins 4" minimums inside this prompt MUST stay in sync with
# MIN_NPCS_PER_FACTION / MIN_FACTIONLESS in region_author.py (BRIEF-40).
REGION_MANIFEST_SYSTEM_PROMPT = """\
Tu es l'assistant de création du créateur d'un monde de jeu de rôle. Le \
créateur te donne une intention en quelques phrases pour une RÉGION entière ; \
ton travail est de proposer un MANIFESTE structuré qui servira de plan pour \
générer ensuite chaque faction, chaque lieu et chaque PNJ de cette région. \
Tu ne crées rien toi-même — tu proposes seulement une structure, et le \
créateur (puis d'autres étapes automatisées) jugera et enrichira chaque \
élément ensuite.

=== STRUCTURE DU MANIFESTE ===
Ta réponse est TOUJOURS un unique objet JSON avec exactement quatre clés de \
premier niveau : "concept", "factions", "locations", "npcs".
- "concept" : 2 à 4 phrases décrivant la géographie de la région et la \
tension politique qui la traverse.
- "factions" : une liste d'objets {"name", "one_liner"} — chaque nom est \
unique dans la liste ; "one_liner" résume son rôle ou sa posture dans la \
région.
- "locations" : une liste d'objets {"name", "one_liner", "is_root", \
"parent_name"} — chaque nom est unique ; EXACTEMENT un lieu doit avoir \
"is_root": true (le lieu d'entrée de la région) ; tout autre lieu doit \
avoir "parent_name" égal au nom exact d'un autre lieu de cette même liste.
- "npcs" : une liste d'objets {"name", "one_liner", "location_name", \
"faction_name"} — chaque nom est unique ; "location_name" doit être le nom \
exact d'un lieu de la liste "locations" ; "faction_name" est le nom exact \
d'une faction de la liste "factions", ou null si ce PNJ n'appartient à \
aucune.

=== RÈGLE — LA DENSITÉ EST TA DÉCISION ===
Aucun nombre de factions, de lieux ou de PNJ n'est imposé : propose ce que \
l'intention du créateur appelle, ni plus ni moins. Une région modeste peut \
n'avoir qu'un lieu et deux PNJ ; une région riche peut en avoir beaucoup \
plus.

Plancher de densité de PNJ (à respecter impérativement) :
- Pour CHAQUE faction listée dans `factions`, la liste `npcs` doit contenir \
au moins 4 PNJ dont le champ `faction_name` est exactement le nom de \
cette faction.
- La liste `npcs` doit aussi contenir au moins 4 PNJ sans faction \
(`faction_name` = null).
- Ce sont des minimums : produis-en davantage si le brief le suggère, \
jamais moins.
- Chaque PNJ ajouté pour atteindre ces minimums respecte le format normal : \
`name`, `one_liner`, `location_name` (un lieu existant de la liste \
`locations`), et `faction_name`.

=== FORMAT DE SORTIE ===
Réponds UNIQUEMENT avec l'objet JSON demandé — aucun texte avant ou après, \
aucun bloc de code Markdown, aucun commentaire.\
"""

REGION_MANIFEST_USER_TEMPLATE = """\
{world_description}{world_fundamental_laws}Intention du créateur pour cette région : {brief}

Manifeste JSON :\
"""

# BRIEF-40: Region NPC top-up clamp (A1) — Stage-0 manifest gained a density
# floor (BRIEF-39) but the small authoring model honors it unreliably. This
# template issues ONE targeted re-prompt, to the SAME authoring model, asking
# only for the exact missing NPCs. usage = "region_manifest_topup". Called
# from region_author.py's generate_region_manifest, after normalization,
# only when a deficit remains.
REGION_MANIFEST_TOPUP_SYSTEM_PROMPT = """\
Tu complètes un manifeste de région déjà existant. On te fournit le \
concept, les factions, les lieux et les PNJ déjà présents, ainsi qu'un \
nombre exact de PNJ à ajouter. Tu produis UNIQUEMENT les PNJ manquants \
demandés, au format JSON.

Règles impératives :
- Réponds avec un seul objet JSON : {"npcs": [ ... ]}. Aucun texte hors du JSON.
- Chaque PNJ : {"name": str, "one_liner": str, "location_name": str, "faction_name": str ou null}.
- `location_name` DOIT être l'un des lieux fournis, copié à l'identique.
- `faction_name` DOIT être exactement le nom de la faction demandée pour ce \
PNJ, ou null pour un PNJ sans faction.
- Aucun nom de PNJ ne doit reprendre un PNJ déjà présent ni un autre PNJ \
que tu ajoutes.
- Produis EXACTEMENT le nombre de PNJ demandé pour chaque cible, ni plus ni moins.
- `one_liner` : une seule phrase en français qui campe le personnage.\
"""

REGION_MANIFEST_TOPUP_USER_TEMPLATE = """\
Concept de la région :
{concept}

Factions existantes :
{factions_block}

Lieux existants (valeurs autorisées pour location_name) :
{locations_block}

PNJ déjà présents (noms à ne pas réutiliser) :
{existing_npcs_block}

PNJ à ajouter :
{requests_block}

Produis uniquement ces PNJ manquants, au format JSON {{"npcs": [...]}}.\
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
évoquer, et comment tu vois ceux qui t'entourent. Ces règles priment sur tout \
le reste.

RÈGLE ABSOLUE — NE RIEN INVENTER.
Tu ne connais QUE ce qui figure explicitement dans ta fiche de contexte. Tu ne \
dois JAMAIS inventer : ni personne, ni faction, groupe ou organisation, ni lieu, \
ni événement, ni nom, ni aucun fait qui ne soit pas écrit dans ta fiche. Aucun \
nom propre fictif, jamais. Si l'on t'interroge sur quoi que ce soit qui n'est pas \
dans ta fiche, tu l'admets simplement et sans détour (« je ne saurais vous dire », \
« ça, je n'en sais rien »). Tu ne spécules pas, tu n'enjolives pas, tu n'inventes \
rien pour combler le silence. Mieux vaut avouer que tu ne sais pas plutôt que de \
fabriquer une réponse.

ATTITUDE.
Ta fiche indique, dans la section « COMMENT TU VOIS… », ton attitude envers ton \
interlocuteur. Adopte-la : elle règle ta manière et ta disposition, pas les \
faits que tu possèdes — ta fiche a déjà filtré ce que tu peux évoquer.

OBJECTIFS.
Ta fiche liste tes objectifs (« TES OBJECTIFS »). Poursuis-les quand la \
scène s'y prête — tu peux solliciter, refuser, marchander ou mettre fin à \
l'échange si cela les sert — sans jamais en réciter la liste.

DISCRÉTION ET NATUREL.
Parle naturellement, comme une vraie personne. Ne truffe pas tes réponses de \
sous-entendus mystérieux. N'oriente pas l'interlocuteur vers d'autres personnes, \
sauf rarement (une seule fois, et seulement si c'est réellement pertinent) — \
jamais comme une esquive réflexe.

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
        is_active=True,
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
        variables=["player_line"],
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
    )

    # ----- prompt template: MJ scene interpretation -------------------------
    # usage = "mj_interpretation". Classifies each player turn into one of 5
    # modes (dialogue / physical / npc_reaction / scene / join / travel) to route
    # the /say flow, and extracts used_object (BRIEF-08/D2a.1: equip_action
    # removed). Non-streaming JSON call; /no_think appended at call time.
    # world_id = NULL. v4 adds the `physical` mode (BRIEF-11, schema v1.23).
    # v5 extends physical to include explicit search intent (BRIEF-13, schema v1.26).
    # v6 adds the `travel` mode + decision-rule reorder (BRIEF-16, schema v1.29):
    #   priority join > dialogue > physical > travel > npc_reaction > scene;
    #   "reference" now also carries the player's destination words for travel.
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
    )

    # ----- prompt template: MJ arbiter (physical resolution classification) --
    # usage = "mj_arbitration". Fired only for ResponseMode.physical, between
    # phase 0 (mj_interpretation) and the NPC phase: classifies the action into
    # a domain (physical/agility/perception/composure, or — since BRIEF-55,
    # schema v1.63 — a world-scoped custom skill name) and optional NPC
    # opposition (by name, resolved to an id in app.py). Never rolls, never
    # decides outcomes — resolve_physical (resolution.py) does that in pure
    # Python. Non-streaming JSON call; /no_think appended at call time.
    # world_id = NULL (BRIEF-11, schema v1.23).
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-arbiter",
        world_id=None,
        name="MJ arbitre — domaine, opposition, contrainte et violence (résolution physique)",
        usage="mj_arbitration",
        system_prompt=MJ_ARBITER_SYSTEM_PROMPT,
        user_template=MJ_ARBITER_USER_TEMPLATE,
        variables=["player_line", "npc_list", "custom_skill_names"],
        destination="local",
        notes=(
            "v3 (BRIEF-55, schema v1.63): domain selection widened to the "
            "world's custom skill catalogue — {custom_skill_names} filled at "
            "call time, '(aucune)' when the world has none (byte-identical "
            "behavior in that case)"
        ),
    )

    # ----- prompt template: MJ establishment (scene-establishing entry narration) --
    # usage = "mj_establishment". Single non-streamed chat() call fired on
    # every location entry (G1, schema v1.30, BRIEF-17): describes the scene
    # the player perceives — the room and any active signpost content — from
    # entity.description + the allow-listed subculture slice + the silence-
    # predicate's surviving ambient content. Names NPCs ONLY via the
    # CHANGEMENTS block (schema v1.71, BRIEF-0016-a); a presently-present NPC
    # is never named (J1). world_id = NULL. Uses upsert so re-seeding always
    # converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-establishment",
        world_id=None,
        name="MJ établissement — narration de scène à l'entrée",
        usage="mj_establishment",
        system_prompt=MJ_ESTABLISHMENT_SYSTEM_PROMPT,
        user_template=MJ_ESTABLISHMENT_USER_TEMPLATE,
        variables=["location_name", "description", "subculture", "signposts", "changes"],
        destination="local",
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
    # Used by analyze_window — one template, one call site (BRIEF-09, v3:
    # anti-inflation rubric for relation_change in multi-turn windows; v4
    # (BRIEF-19): resource_change vocabulary + verbatim rubric).
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
    )

    # ----- prompt template: overhearing classification (Tier 4, step 2) -----
    # usage = "overhearing_classification". world_id = NULL so it applies to
    # every world. Closed-list classification only — analyzer.analyze_overhearing
    # does all attribution, receiver computation, and level computation in code.
    upsert_prompt_template(
        session,
        "pt-overhearing-classification",
        world_id=None,
        name="Overhearing classification — sujets surpris",
        usage="overhearing_classification",
        system_prompt=OVERHEARING_CLASSIFICATION_SYSTEM_PROMPT,
        user_template=OVERHEARING_CLASSIFICATION_USER_TEMPLATE,
        variables=["subject_list", "player_line", "npc_line"],
        destination="local",
    )

    # ----- prompt template: AI entity-authoring assistant (BRIEF-24) ---------
    # usage = "entity_generation". world_id = NULL. Calls go through
    # entity_author.generate_entity_draft, which formats user_template with
    # {entity_type}/{type_fields}/{brief} and never writes canon. Uses upsert
    # so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-entity-generation",
        world_id=None,
        name="Assistant de création d'entité — brouillon PNJ",
        usage="entity_generation",
        system_prompt=ENTITY_GENERATION_SYSTEM_PROMPT,
        user_template=ENTITY_GENERATION_USER_TEMPLATE,
        variables=["entity_type", "type_fields", "brief"],
        destination="local",
    )

    # ----- prompt template: NPC goal generator (TICKET-0013/BRIEF-0013-b) ----
    # usage = "npc_goal_generation". world_id = NULL. Calls go through
    # entity_author.generate_npc_goals — pure generate-and-return, one long +
    # two short goals (M2). Uses upsert so re-seeding converges non-text head
    # fields; S2 discipline means text is written only on a virgin head.
    upsert_prompt_template(
        session,
        "pt-npc-goals",
        world_id=None,
        name="NPC goals — génération 1 long + 2 courts (JSON)",
        usage="npc_goal_generation",
        system_prompt=NPC_GOALS_SYSTEM_PROMPT,
        user_template=NPC_GOALS_USER_TEMPLATE,
        variables=["npc_name", "npc_description", "npc_backstory", "faction_goals"],
        destination="local",
    )

    # ----- prompt template: world-bible generator (BRIEF-47) -----------------
    # usage = "world_generation" (new usage value). world_id = NULL. Calls go
    # through entity_author.generate_world_draft, which formats user_template
    # with only {brief} and never writes canon — World is not an `entity` row,
    # so this is a sibling generator, not a _TYPE_FIELDS entry.
    upsert_prompt_template(
        session,
        "pt-world-generation",
        world_id=None,
        name="Assistant de création de monde — brouillon de prémisse",
        usage="world_generation",
        system_prompt=WORLD_GENERATION_SYSTEM_PROMPT,
        user_template=WORLD_GENERATION_USER_TEMPLATE,
        variables=["brief"],
        destination="local",
    )

    # ----- prompt template: PC creation assistant (BRIEF-52) -----------------
    # usage = "player_generation" (new usage value). world_id = NULL. Calls go
    # through entity_author.generate_player_draft — a standalone sibling, NOT
    # a _TYPE_FIELDS entry: no public/secret blocks, no faction/location/
    # skill proposal (D1/G1/B1/C1).
    upsert_prompt_template(
        session,
        "pt-player-generation",
        world_id=None,
        name="Assistant de création de personnage joueur — brouillon",
        usage="player_generation",
        system_prompt=PLAYER_GENERATION_SYSTEM_PROMPT,
        user_template=PLAYER_GENERATION_USER_TEMPLATE,
        variables=["brief"],
        destination="local",
    )

    # ----- prompt template: skill catalogue authoring (BRIEF-56) -------------
    # usage = "skill_catalogue" (new usage value). world_id = NULL. Calls go
    # through entity_author.generate_skill_catalogue_draft — a standalone
    # sibling, NOT a _TYPE_FIELDS entry: names + prose + intended base domain
    # only, never a tier, never a structural id (D2-attach-b/D2-template-b).
    upsert_prompt_template(
        session,
        "pt-skill-catalogue",
        world_id=None,
        name="Assistant de création — catalogue de compétences propres au monde",
        usage="skill_catalogue",
        system_prompt=SKILL_CATALOGUE_SYSTEM_PROMPT,
        user_template=SKILL_CATALOGUE_USER_TEMPLATE,
        variables=["brief"],
        destination="local",
    )

    # ----- prompt template: region orchestrator manifest (BRIEF-34) ----------
    # usage = "region_manifest" (new usage value). world_id = NULL. Calls go
    # through region_author.generate_region_manifest (Phase A, BRIEF-38),
    # which formats user_template with {brief} and code-judges the
    # resulting manifest. The manifest is then handed to
    # generate_region_draft (Phase B), which re-normalizes it and composes
    # the atomic generators across it. Writes no canon at any stage.
    # BRIEF-44 (B2): gained world_description / world_fundamental_laws —
    # the active world's (otherwise-dormant) premise columns, read by
    # generate_region_manifest and composed with the region brief. Each is
    # a ready-rendered block (label + text + blank line) or "" when the
    # world field is empty, so an empty-premise world degrades to the
    # original brief-only prompt with no dangling label.
    upsert_prompt_template(
        session,
        "pt-region-manifest",
        world_id=None,
        name="Orchestrateur de région — manifeste",
        usage="region_manifest",
        system_prompt=REGION_MANIFEST_SYSTEM_PROMPT,
        user_template=REGION_MANIFEST_USER_TEMPLATE,
        variables=["world_description", "world_fundamental_laws", "brief"],
        destination="local",
    )

    # ----- prompt template: region manifest NPC top-up (BRIEF-40) ------------
    # usage = "region_manifest_topup". world_id = NULL. Calls go through
    # region_author.py's generate_region_manifest, after normalization, only
    # when the NPC density floor isn't met — one targeted re-prompt to the
    # same AUTHOR_MODEL for exactly the missing NPCs. The `variables` list is
    # metadata only (RECON E14) — the call site passes these as explicit
    # .format() kwargs.
    upsert_prompt_template(
        session,
        "pt-region-manifest-topup",
        world_id=None,
        name="Orchestrateur de région — complément PNJ",
        usage="region_manifest_topup",
        system_prompt=REGION_MANIFEST_TOPUP_SYSTEM_PROMPT,
        user_template=REGION_MANIFEST_TOPUP_USER_TEMPLATE,
        variables=["concept", "factions_block", "locations_block", "existing_npcs_block", "requests_block"],
        destination="local",
    )

    # ----- prompt template: world tick — off-screen NPC advancement ----------
    # (TICKET-0014/BRIEF-0014-a). usage = "world_tick". world_id = NULL.
    # model=NULL (Q1): the runner (BRIEF-0014-b) passes
    # ollama_client.DEFAULT_MODEL through effective_model, keeping a
    # per-template override available. No PROMPT_REGISTRY entry yet — that
    # entry (and the loader call site it points to) lands with the runner in
    # BRIEF-0014-b, mirroring the 0013 precedent (pt-npc-goals' registry
    # entry arrived with its generator, not with the earlier goal-table brief).
    upsert_prompt_template(
        session,
        "pt-world-tick",
        world_id=None,
        name="World tick — avancement PNJ hors-champ (JSON)",
        usage="world_tick",
        system_prompt=WORLD_TICK_SYSTEM_PROMPT,
        user_template=WORLD_TICK_USER_TEMPLATE,
        variables=["tick_context", "interval_label"],
        destination="local",
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
        world_id=WORLD_ID,
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
    ensure_primary_membership(session, WORLD_ID, "npc-maelis", "fac-unnamed")
    # Starter catalogue (BRIEF-20) — read-merge so no other metadata key is clobbered.
    merge_entity_metadata(
        session,
        "npc-maelis",
        {"price_list": {"biere": 5, "chambre": 40, "repas": 12}},
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
        world_id=WORLD_ID,
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
    ensure_primary_membership(session, WORLD_ID, "npc-reike", "fac-guard")

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
        world_id=WORLD_ID,
        character_type="npc",
        current_location_id="loc-dernier-verre",
        appearance="Figure âgée, voyageuse, « passe par là » régulièrement.",
        backstory="Détient un savoir oral transmis ; observe le réveil avec inquiétude.",
        secrets={"knows_more": "En sait plus qu'elle n'en dit sur le nœud et le réveil."},
    )
    ensure_primary_membership(session, WORLD_ID, "npc-senna", "fac-walkers")

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
        world_id=WORLD_ID,
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
        world_id=WORLD_ID,
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
        world_id=WORLD_ID,
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

    # ----- skill sheet test player character (entity + character + skill) ----
    # BRIEF-10: dedicated test character for the skill sheet, separate from
    # char-player. Four skill rows at tier 0 — the creator edits tiers via the
    # cockpit "Fiche" view afterwards.
    get_or_create(
        session,
        m.Entity,
        SKILL_SHEET_PC_ID,
        world_id=WORLD_ID,
        type="character",
        name=SKILL_SHEET_PC_NAME,
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        SKILL_SHEET_PC_ID,
        world_id=WORLD_ID,
        character_type="player",
        user_id=None,
        current_location_id="loc-dernier-verre",
    )
    for domain in SKILL_DOMAINS:
        get_or_create(
            session,
            m.Skill,
            f"skill-{SKILL_SHEET_PC_ID}-{domain}",
            character_id=SKILL_SHEET_PC_ID,
            domain=domain,
            tier=0,
        )

    # ----- world-scoped custom skill catalogue (BRIEF-55, schema v1.63) -----
    # Test fixture exercising both readers: the arbiter (mechanical) and the
    # MJ narration assembler (ambiance). Names are illustrative.
    get_or_create(
        session,
        m.SkillDefinition,
        SKILL_DEF_DIPLOMATIE_ID,
        world_id=WORLD_ID,
        name="Diplomatie",
        base_domain="composure",
    )
    get_or_create(
        session,
        m.SkillDefinition,
        SKILL_DEF_PISTAGE_ID,
        world_id=WORLD_ID,
        name="Pistage",
        base_domain="perception",
    )
    # B1: the pilot PC seeds every custom skill of its world too, flat at
    # tier 0, mirroring create_player_character's seed loop.
    for def_id, def_domain in (
        (SKILL_DEF_DIPLOMATIE_ID, "composure"),
        (SKILL_DEF_PISTAGE_ID, "perception"),
    ):
        get_or_create(
            session,
            m.Skill,
            f"skill-{SKILL_SHEET_PC_ID}-custom-{def_id}",
            character_id=SKILL_SHEET_PC_ID,
            domain=def_domain,
            tier=0,
            skill_definition_id=def_id,
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

    # ----- Signpost cluster: "papiers_bureau" at the tavern (schema v1.30, ---
    # BRIEF-17). One ambient panel + two hidden contents sharing the same
    # signpost_group. The panel narrates on entry until the player knows
    # BOTH hidden subjects (E1: silent only when the whole cluster is known).
    get_or_create(
        session,
        m.DiscoverableDetail,
        "disc-papiers-bureau-panel",
        world_id=WORLD_ID,
        location_id="loc-dernier-verre",
        subject="papiers_bureau_panel",  # organisational only — never knowledge
        content="Des papiers en désordre traînent sur une table à l'écart.",
        access_level="ambient",
        signpost_group="papiers_bureau",
    )
    get_or_create(
        session,
        m.DiscoverableDetail,
        "disc-lettre-innommee",
        world_id=WORLD_ID,
        location_id="loc-dernier-verre",
        subject="lettre_innommee",
        content="Une lettre sans signature évoque un « arrangement habituel » et mentionne L'Innommée à mots couverts.",
        access_level="hidden",
        signpost_group="papiers_bureau",
    )
    get_or_create(
        session,
        m.DiscoverableDetail,
        "disc-recu-compromettant",
        world_id=WORLD_ID,
        location_id="loc-dernier-verre",
        subject="recu_compromettant",
        content="Un reçu daté de la semaine passée, pour une somme bien supérieure au prix d'une simple tournée.",
        access_level="hidden",
        signpost_group="papiers_bureau",
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
