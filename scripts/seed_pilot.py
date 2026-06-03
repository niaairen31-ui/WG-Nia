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
from datetime import datetime
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
        obj.updated_at = datetime.utcnow()
        _updated.append((m.Knowledge.__tablename__, id))
    else:
        _existing.append((m.Knowledge.__tablename__, id))
    return obj


def delete_if_exists(session: Session, model, id: str) -> None:
    """Remove a row that should no longer exist (idempotent)."""
    obj = session.get(model, id)
    if obj is not None:
        session.delete(obj)
        _deleted.append((model.__tablename__, id))


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
    # Maelis: knows she serves the network (secret), and the local micro-incidents.
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
    get_or_create(
        session,
        m.Knowledge,
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

    # ----- relations ---------------------------------------------------------
    # Tavern is secretly run by L'Innommée (hidden control).
    get_or_create(
        session,
        m.Relation,
        "rel-unnamed-tavern",
        world_id=WORLD_ID,
        entity_a_id="fac-unnamed",
        entity_b_id="loc-dernier-verre",
        type="instrumentalizes",
        direction="a_to_b",
        intensity=50,
        visible_to_b=False,
        notes="Le Dernier Verre sert de point d'appui à L'Innommée ; lien dissimulé.",
    )

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
                print(f"    - [{flag}] {k.subject} (level={k.level})")


if __name__ == "__main__":
    main()
