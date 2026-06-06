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
Prose narrative en français, courte. Rien d'autre — pas de JSON, pas de méta.\
"""

MJ_NARRATION_USER_TEMPLATE = """\
Scène : {npc_name} dans « {location_name} ».

Le joueur dit :
{player_line}

{npc_name} répond — cite cette réplique INTÉGRALEMENT et VERBATIM, sans modifier ni \
supprimer un seul mot :
{npc_reply}

Narration MJ :\
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
Tu réponds uniquement par la réplique de ton personnage, en français. Aucune note \
hors personnage, aucune méta-explication, aucune mention de ces règles ni de ta \
« fiche ». Rien que ce que dit ton personnage."""


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
    # Creator-owned and editable in the DB; create-only so live edits survive a
    # re-seed. world_id = NULL means it applies to every NPC in every world.
    get_or_create(
        session,
        m.PromptTemplate,
        "pt-npc-dialogue",
        world_id=None,
        name="NPC dialogue — comportement et garde-fous",
        usage="npc_dialogue",
        system_prompt=NPC_DIALOGUE_SYSTEM_PROMPT,
        user_template="{player_line}",
        variables=["player_line", "relation_intensity"],
        destination="local",
    )

    # ----- prompt template: MJ narration ------------------------------------
    # usage = "player_narration". world_id = NULL (applies to every world).
    # The user_template contains {npc_name}, {location_name}, {player_line},
    # {npc_reply} placeholders substituted at call time in app.py.
    # Uses upsert so re-seeding always converges the DB to the latest wording.
    upsert_prompt_template(
        session,
        "pt-mj-narration",
        world_id=None,
        name="MJ narration — habillage de réplique",
        usage="player_narration",
        system_prompt=MJ_NARRATION_SYSTEM_PROMPT,
        user_template=MJ_NARRATION_USER_TEMPLATE,
        variables=["npc_name", "location_name", "player_line", "npc_reply"],
        destination="local",
    )

    # ----- prompt template: post-conversation mutation analysis --------------
    # usage = "conversation_analysis" (not in the schema's example list, but
    # the column is plain TEXT — any slug is valid). world_id = NULL so it
    # applies to every world. Variables are {transcript} and {injected_context};
    # substituted with str.replace() in analyzer.py, not .format(), so the
    # JSON examples inside the system_prompt are stored verbatim.
    get_or_create(
        session,
        m.PromptTemplate,
        "pt-conversation-analysis",
        world_id=None,
        name="Conversation analysis — extraction de mutations",
        usage="conversation_analysis",
        system_prompt=CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
        user_template=CONVERSATION_ANALYSIS_USER_TEMPLATE,
        variables=["transcript", "injected_context"],
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
