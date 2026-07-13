"""NPC context assembly — the engine's structural control over what an NPC may say.

`assemble_npc_context` builds the briefing that drives an NPC's dialogue. The
control model is *exclusion, not restraint*: the model can only reveal what is
actually in its prompt, so anything the NPC must not say is simply never put
there. This replaces the earlier "under guard" design (a section telling the
model to hold a secret it was nonetheless shown), which leaked under pressure
with an abliterated model.

Two filters decide what reaches the prompt (see world-engine-schema.md v1.3):

- **Secrets are excluded outright.** Every knowledge row with is_secret = TRUE is
  dropped, regardless of the relation. There is no concealed section.
- **Non-secret rows are relation-gated.** A row is included only if the
  NPC→interlocutor relation intensity (1-100) is >= its share_threshold. Warmer
  relations unlock more; a stranger hears only what sits at/below neutral (50).

The NPC→interlocutor relation is the one where THIS NPC is the perceiver (NPC as
entity_a with direction a_to_b, entity_b with b_to_a, or mutual). When no such
relation exists, intensity defaults to 50 (neutral), per the schema convention.

It reads only the NPC's own rows — never another entity's secrets, never the
interlocutor's knowledge. Output is a French text block (not JSON): a briefing
addressed to the NPC. Behaviour/tone instructions live in the prompt template,
not here.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import (
    Agenda,
    Character,
    DiscoverableDetail,
    Entity,
    Event,
    FactionMembership,
    Gathering,
    GatheringMember,
    GoalAgendaLink,
    Item,
    Knowledge,
    Location,
    LocationSubculture,
    NpcGoal,
    NpcPrice,
    Relation,
    SkillDefinition,
)

# Section headers (kept stable so a harness can split the output reliably).
H_IDENTITY = "QUI TU ES"
H_GOALS = "TES OBJECTIFS"
H_SETTING = "OÙ TU TE TROUVES"
H_SPEAK = "CE QUE TU PEUX ÉVOQUER"
H_PERCEPTION = "COMMENT TU VOIS CEUX QUI T'ENTOURENT"
H_COMPANY = "AVEC QUI TU TE TROUVES EN CE MOMENT"
H_BOUNDARIES = "LIMITES STRICTES"
H_MJ_CUSTOM_SKILLS = "COMPÉTENCES PROPRES À CE MONDE"

# Neutral relation intensity assumed when the NPC has no read on the interlocutor.
NEUTRAL_INTENSITY = 50

# Affinity tiers (TICKET-0012, A1/H2): resolved in code, never by the model.
# The prompt-side 5-tier table was removed from NPC_DIALOGUE_SYSTEM_PROMPT;
# these boundaries and texts are the sole authority.
_AFFINITY_TIERS = (
    # (upper_bound_exclusive, adjective, directive)
    (30, "hostile",
     "Ton attitude envers cette personne : hostile ou méprisante. "
     "Interaction minimale, ton sec ; tu peux refuser d'échanger ou la renvoyer."),
    (50, "méfiante",
     "Ton attitude envers cette personne : méfiante. Laconique ; tu ne donnes "
     "que ce qui est manifestement public ; tu peux marchander "
     "(« qu'est-ce que j'y gagne ? ») plutôt que de partager de bon cœur."),
    (60, "neutre",
     "Ton attitude envers cette personne : discrétion ordinaire. Poli ; tu "
     "parles de choses banales ; tu deviens évasif si l'on insiste sur un "
     "sujet sensible ; tu ne vas pas de toi-même au-delà des banalités."),
    (76, "chaleureuse",
     "Ton attitude envers cette personne : chaleureuse. Tu partages si l'on "
     "te le demande, tout en gardant une réserve sur les sujets délicats."),
    (101, "confiante",
     "Ton attitude envers cette personne : confiante. Tu offres spontanément "
     "des choses que tu tairais à un inconnu, sans qu'on ait à te pousser."),
)


def _affinity_tier(intensity: int) -> tuple[str, str]:
    """(adjective, directive) for an intensity 1-100. Code-side authority."""
    for upper, adjective, directive in _AFFINITY_TIERS:
        if intensity < upper:
            return adjective, directive
    return _AFFINITY_TIERS[-1][1], _AFFINITY_TIERS[-1][2]


# Subculture keys safe to surface as ambient atmosphere. Anything else
# (e.g. "hidden", "secret") is deliberately withheld from the Setting section.
_SAFE_SUBCULTURE_KEYS = ("values",)

# Directions under which `entity_a` / `entity_b` is the perceiving side.
_A_PERCEIVES = ("a_to_b", "mutual")
_B_PERCEIVES = ("b_to_a", "mutual")


def _section(title: str, body: str) -> str:
    return f"=== {title} ===\n{body.rstrip()}\n"


def _knowledge_line(k: Knowledge) -> str:
    text = k.content or f"{k.subject} ({k.level})"
    if k.is_incorrect:
        text += " (tu en es convaincu, mais c'est faux)"
    return f"- {text}"


def _perceived_target(rel: Relation, npc_id: str) -> str | None:
    """Return the id this relation lets `npc_id` perceive, or None."""
    if rel.entity_a_id == npc_id and rel.entity_b_id != npc_id and rel.direction in _A_PERCEIVES:
        return rel.entity_b_id
    if rel.entity_b_id == npc_id and rel.entity_a_id != npc_id and rel.direction in _B_PERCEIVES:
        return rel.entity_a_id
    return None


def _render_perception(name: str, rel: Relation) -> str:
    adjective, _ = _affinity_tier(rel.intensity)
    return (
        f"- {name} : {rel.notes} "
        f"(perception : {rel.type}, disposition : {adjective})"
    )


def read_public_memberships(
    entity_id: str, session: Session
) -> list[tuple[str, str | None]]:
    """Return this entity's own public, active faction memberships.

    The structural choke-point for membership-in-prompts, with TWO
    guarantees enforced in the query/resolution itself, never by
    instruction: `is_secret = FALSE` (no secret membership in any prompt)
    and `cover_role ?? role` (schema v1.41, BRIEF-30 — when a `cover_role`
    is set, the true `role` never crosses this boundary). No caller can opt
    into secret rows or the raw true role — there is no parameter for
    either. This is the only path through which `faction_membership` may
    ever reach a model prompt.

    Returns `(faction_name, promptable_role)` pairs, primary first then
    oldest-joined. `promptable_role` is `cover_role if cover_role is not
    None else role`. A row whose `faction_id` doesn't resolve to an
    `Entity` is skipped — a raw id must never render into a prompt.
    """
    rows = session.exec(
        select(FactionMembership)
        .where(
            FactionMembership.entity_id == entity_id,
            FactionMembership.left_at.is_(None),
            FactionMembership.is_secret == False,  # noqa: E712
        )
        .order_by(FactionMembership.is_primary.desc(), FactionMembership.joined_at.asc())
    ).all()

    memberships: list[tuple[str, str | None]] = []
    for row in rows:
        faction_entity = session.get(Entity, row.faction_id)
        if faction_entity is None:
            continue
        promptable_role = row.cover_role if row.cover_role is not None else row.role
        memberships.append((faction_entity.name, promptable_role))
    return memberships


def read_public_membership_faction_ids(entity_id: str, session: Session) -> set[str]:
    """Return the faction ids this entity holds a public, active membership
    in (TICKET-0020, BRIEF-0020-b) — the SECOND sanctioned reader of
    `faction_membership` for prompts, existing solely as the D1 dialogue
    goal-provenance gate. Same structural WHERE triplet as
    `read_public_memberships` (`entity_id` match, `left_at IS NULL`,
    `is_secret == False`) — no caller can opt into secret rows; there is no
    parameter for it."""
    rows = session.exec(
        select(FactionMembership).where(
            FactionMembership.entity_id == entity_id,
            FactionMembership.left_at.is_(None),
            FactionMembership.is_secret == False,  # noqa: E712
        )
    ).all()
    return {row.faction_id for row in rows}


def _goal_provenance_suffix(goal: NpcGoal, npc_id: str, session: Session) -> str:
    """` (sert : « <title> »[, « <title> »...])` for each ACTIVE link
    (`detached_at IS NULL`) to a still-ACTIVE agenda the goal serves, D1
    GATED (TICKET-0020, BRIEF-0020-b): a title renders only when the
    agenda's owner IS this NPC (its own intrigue) OR the owner faction is
    among `read_public_membership_faction_ids(npc_id, session)` — the
    query-mechanical D1 choke-point, never a model instruction. A link
    failing the gate contributes NOTHING; the goal then appears bare,
    exactly as it did before this brief."""
    links = session.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.goal_id == goal.id, GoalAgendaLink.detached_at.is_(None)
        )
    ).all()
    if not links:
        return ""
    public_faction_ids = read_public_membership_faction_ids(npc_id, session)
    titles = []
    for link in links:
        agenda = session.get(Agenda, link.agenda_id)
        if agenda is None or agenda.status != "active":
            continue
        if agenda.owner_entity_id == npc_id or agenda.owner_entity_id in public_faction_ids:
            titles.append(agenda.title)
    if not titles:
        return ""
    return " (sert : " + ", ".join(f"« {t} »" for t in titles) + ")"


def assemble_npc_context(
    npc_id: str,
    interlocutor_id: str,
    location_id: str,
    session: Session,
    gathering_id: str | None = None,
    relevance_hint: str | None = None,
    player_condition: str = "unharmed",
) -> str:
    """Assemble the text briefing that drives this NPC's dialogue.

    Secrets are excluded outright; non-secret knowledge is gated by the
    NPC→interlocutor relation intensity against each row's share_threshold.

    `gathering_id` (multi-NPC scenes, schema v1.8 — contract D1): when given,
    a "AVEC QUI TU TE TROUVES EN CE MOMENT" section lists the NPC's current
    co-participants (active members of the same gathering, excluding itself
    and the interlocutor) by name and *public* description only — appearance
    and entity description, never knowledge or relations. Simple co-presence,
    no relation-based modulation (that stays in the perception section above;
    modulating who an NPC notices in a crowd by relation warmth is a later
    refinement, not built now).

    `relevance_hint` (schema v1.12, prepared/inert): reserved for a future
    relevance-selection stage that may only NARROW the security-scoped set
    above, never widen it. Inert until context size measurably hurts.
    """
    del relevance_hint  # reserved, inert (schema v1.12)
    npc_entity = session.get(Entity, npc_id)
    npc_char = session.get(Character, npc_id)
    if npc_entity is None or npc_char is None:
        raise ValueError(f"No NPC character found for id {npc_id!r}")

    inter_entity = session.get(Entity, interlocutor_id)
    inter_name = inter_entity.name if inter_entity else "un inconnu"

    def name_of(entity_id: str) -> str:
        e = session.get(Entity, entity_id)
        return e.name if e else entity_id

    # ----- 1. Identity ------------------------------------------------------
    identity_lines = [f"Tu es {npc_entity.name}."]
    if npc_char.appearance:
        identity_lines.append(npc_char.appearance)
    if npc_char.backstory:
        identity_lines.append(npc_char.backstory)
    if npc_char.aversion:
        identity_lines.append(npc_char.aversion)
    if npc_entity.description:
        identity_lines.append(npc_entity.description)
    identity = " ".join(identity_lines)

    # ----- 1b. Goals (BRIEF-0013-a, Q1/S1/N1) — the long goal + the 2 most
    # recent active shorts, newest first within each horizon. Read-side LIMIT
    # is the S1 bound; no write-side cap exists anywhere on active shorts.
    long_goal = session.exec(
        select(NpcGoal)
        .where(NpcGoal.npc_id == npc_id, NpcGoal.status == "active", NpcGoal.horizon == "long")
        .order_by(NpcGoal.created_at.desc())
        .limit(1)
    ).first()
    short_goals = session.exec(
        select(NpcGoal)
        .where(NpcGoal.npc_id == npc_id, NpcGoal.status == "active", NpcGoal.horizon == "short")
        .order_by(NpcGoal.created_at.desc())
        .limit(2)
    ).all()
    goal_lines = []
    if long_goal:
        goal_lines.append(f"[LONG TERME] {long_goal.description}{_goal_provenance_suffix(long_goal, npc_id, session)}")
    for g in short_goals:
        goal_lines.append(f"[COURT TERME] {g.description}{_goal_provenance_suffix(g, npc_id, session)}")
    goals_section = (_section(H_GOALS, "\n".join(goal_lines)) + "\n") if goal_lines else ""

    # ----- 2. Setting -------------------------------------------------------
    loc_entity = session.get(Entity, location_id)
    location = session.get(Location, location_id)
    loc_name = loc_entity.name if loc_entity else location_id
    setting_lines = [f"Tu te trouves dans un lieu nommé « {loc_name} »."]
    if loc_entity and loc_entity.description:
        setting_lines.append(loc_entity.description)
    # Inject player condition so the NPC can observe the player's state.
    if player_condition != "unharmed":
        _condition_labels = {
            "bruised": "légèrement blessé / meurtri",
            "injured": "blessé, en mauvais état",
            "neutralized": "hors de combat / inconscient",
        }
        setting_lines.append(
            f"[ÉTAT DU JOUEUR] Le joueur est actuellement : "
            f"{_condition_labels.get(player_condition, player_condition)}."
        )
    if location:
        values_row = session.exec(
            select(LocationSubculture).where(
                LocationSubculture.location_id == location_id,
                LocationSubculture.key == "values",
                LocationSubculture.is_hidden == False,  # noqa: E712
            )
        ).first()
        if values_row and values_row.value:
            setting_lines.append(values_row.value)
    setting = " ".join(setting_lines)

    # ----- Relations: who this NPC perceives, and how warmly toward whom ----
    relations = session.exec(
        select(Relation).where(
            (Relation.entity_a_id == npc_id) | (Relation.entity_b_id == npc_id)
        )
    ).all()
    perceived: dict[str, Relation] = {}
    for rel in relations:
        target = _perceived_target(rel, npc_id)
        if target and target not in perceived:
            perceived[target] = rel

    # NPC→interlocutor relation intensity drives disclosure (neutral if none).
    inter_relation = perceived.get(interlocutor_id)
    intensity = inter_relation.intensity if inter_relation else NEUTRAL_INTENSITY

    # ----- 3. What this NPC may speak about (secret-excluded, relation-gated)-
    knowledge = session.exec(
        select(Knowledge)
        .where(Knowledge.entity_id == npc_id)
        .order_by(Knowledge.id)
    ).all()
    allowed = [
        k for k in knowledge
        if not k.is_secret and intensity >= k.share_threshold
    ]
    if allowed:
        speak_body = (
            "Tu peux parler librement de ce qui suit, si la conversation s'y prête :\n"
        )
        speak_body += "\n".join(_knowledge_line(k) for k in allowed)
    else:
        speak_body = "Tu n'as rien de particulier à partager spontanément."

    # ----- 4. Perception of those present -----------------------------------
    present = session.exec(
        select(Character).where(Character.current_location_id == location_id)
    ).all()
    present_ids = [c.id for c in present]

    perception_lines = [f"Face à toi : {inter_name}."]
    if inter_relation is not None:
        perception_lines.append("  " + _render_perception(inter_name, inter_relation))
    else:
        perception_lines.append(
            "  Cette personne n'est qu'un visage de plus pour toi ; tu n'as ni "
            "lien ni opinion particulière à son sujet."
        )
    _, directive = _affinity_tier(intensity)
    perception_lines.append("  " + directive)

    others = [cid for cid in present_ids if cid not in (npc_id, interlocutor_id)]
    perceived_others = [cid for cid in others if cid in perceived]
    neutral_others = [cid for cid in others if cid not in perceived]

    if perceived_others:
        perception_lines.append("")
        perception_lines.append("Autres personnes présentes que tu remarques :")
        for cid in perceived_others:
            perception_lines.append("  " + _render_perception(name_of(cid), perceived[cid]))
    if neutral_others:
        names = ", ".join(name_of(cid) for cid in neutral_others)
        perception_lines.append("")
        perception_lines.append(
            f"Également présents, sans que tu y prêtes attention particulière : {names}."
        )
    perception = "\n".join(perception_lines)

    # ----- 4b. Gathering co-presence (D1 — simple, no relation modulation) --
    company: str | None = None
    if gathering_id:
        co_rows = session.exec(
            select(GatheringMember, Entity, Character)
            .join(Entity, Entity.id == GatheringMember.entity_id)
            .join(Character, Character.id == GatheringMember.entity_id)
            .where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
                Character.character_type != "player",
                Entity.status == "active",
                Character.vital_status == "alive",
            )
        ).all()
        co_lines = []
        for _member, co_entity, co_char in co_rows:
            if co_entity.id in (npc_id, interlocutor_id):
                continue
            description = co_char.appearance or co_entity.description or "(pas de description)"
            co_lines.append(f"- {co_entity.name} : {description}")
        if co_lines:
            company = (
                "Sont avec vous, dans le même groupe :\n" + "\n".join(co_lines)
            )

    # ----- 5. Hard boundaries ----------------------------------------------
    boundaries = (
        "Tu ne sais que ce qui est écrit ci-dessus. N'invente aucun fait sur le "
        "monde, sur les autres personnes, ou sur des événements au-delà de ce "
        "contexte. Si l'on t'interroge sur quelque chose que tu ignores, réagis "
        "comme quelqu'un qui, simplement, ne sait pas."
    )

    company_section = _section(H_COMPANY, company) + "\n" if company else ""

    # ----- 4b. Affiliations (BRIEF-29) — this NPC's own public memberships --
    memberships = read_public_memberships(npc_id, session)
    affiliations_section = ""
    if memberships:
        affiliation_lines = ["TES AFFILIATIONS :"]
        for faction_name, role in memberships:
            if role:
                affiliation_lines.append(f"- {faction_name} ({role})")
            else:
                affiliation_lines.append(f"- {faction_name}")
        affiliations_section = "\n".join(affiliation_lines) + "\n\n"

    # ----- 4c. Seller tariffs (BRIEF-20, relationalized TICKET-0025,
    # BRIEF-0025-a) — this NPC's own npc_price rows only -------------------
    price_rows = session.exec(
        select(NpcPrice).where(NpcPrice.entity_id == npc_id)
    ).all()
    pricing_section = ""
    if price_rows:
        tariff_lines = ["TES TARIFS (prix fermes) :"]
        for row in price_rows:
            tariff_lines.append(f"- {row.tag} : {row.amount}")
        tariff_lines.append("")
        tariff_lines.append("RÈGLES DE TARIFICATION :")
        tariff_lines.append(
            "- Tes prix affichés ci-dessus sont FERMES et identiques pour tout le monde : "
            "tu les énonces tels quels, sans marchander."
        )
        tariff_lines.append(
            "- Pour une chose qui n'est PAS dans tes tarifs (objet rare, service "
            "inhabituel, faveur), tu proposes toi-même un prix, en te servant de tes "
            "tarifs comme ÉCHELLE de référence : reste dans le même ordre de grandeur, ne "
            "lance pas un nombre absurde. Tu peux laisser ta relation avec la personne "
            "l'influencer — plus bas pour quelqu'un que tu apprécies, plus haut pour "
            "quelqu'un dont tu te méfies. Annonce UN seul prix (pas de marchandage en "
            "va-et-vient pour l'instant)."
        )
        tariff_lines.append(
            "- Tu ne vends que ce que tu possèdes ou peux raisonnablement fournir ; tu "
            "n'inventes pas un stock que tu n'as pas."
        )
        tariff_lines.append("- Les montants sont dans la monnaie du lieu.")
        pricing_section = "\n".join(tariff_lines) + "\n\n"

    return (
        _section(H_IDENTITY, identity)
        + "\n"
        + goals_section
        + _section(H_SETTING, setting)
        + "\n"
        + _section(H_SPEAK, speak_body)
        + "\n"
        + _section(H_PERCEPTION, perception)
        + "\n"
        + company_section
        + affiliations_section
        + pricing_section
        + _section(H_BOUNDARIES, boundaries)
    )


# -----------------------------------------------------------------------------
# MJ context assembler — the player's perception boundary (schema v1.12,
# scope D-b3)
# -----------------------------------------------------------------------------

H_MJ_LOCATION = "LIEU"
H_MJ_PRESENT = "PERSONNES PRÉSENTES"
H_MJ_PLAYER_KNOWLEDGE = "CE QUE LE JOUEUR SAIT DÉJÀ"
H_MJ_EVENTS = "ÉVÉNEMENTS CONNUS DU PUBLIC"

# Cap on public/confirmed events surfaced to the MJ (schema v1.12).
_MJ_EVENT_CAP = 5


def assemble_mj_context(
    db: Session,
    player_character_id: str,
    location_id: str,
    gathering_id: str | None = None,
    relevance_hint: str | None = None,
    blindfolded: bool = False,
    player_condition: str = "unharmed",
) -> dict:
    """Assemble the MJ's narration context — the player's perception boundary.

    The MJ contains ONLY what the player may perceive or already knows. Three
    static parts (assembled once at conversation start, snapshotted under
    `conversation.injected_context["mj"]`) plus one dynamic part (read fresh
    at every narration phase, never snapshotted):

    - `location` (static): the current location's `entity.name` +
      `entity.description`, plus the allow-listed (`_SAFE_SUBCULTURE_KEYS`)
      non-hidden `location_subculture` rows — ambiance is perceptible.
      `location.magic_status` is deliberately excluded (not directly
      perceivable).
    - `player_knowledge` (static): all `knowledge` rows belonging to the
      player character (subject, level, content) — these are the player's
      own, so no further filtering is applied (a player's own `is_secret`
      row is something they already know, not a leak).
    - `public_events` (static): `event` rows with `knowledge_status IN
      ('public', 'confirmed')` for this world, ordered by `occurred_at DESC`,
      capped at `_MJ_EVENT_CAP`; events whose `location_id` matches
      `location_id` are preferred (listed first within the cap).
    - `co_presents` (dynamic): public name + public `entity.description` of
      NPCs currently present, read fresh from the gathering roster
      (`GatheringMember` with `left_at IS NULL` for `gathering_id` — the
      single source of truth, since C2 migrations change co-presence
      mid-conversation). Entities with `is_public = FALSE` are excluded.

    Structural exclusions (by query construction, never by instruction): no
    NPC `knowledge` row (only the player's own are read), no
    `character.secrets`, no `entity.internal_name`, no non-public entities,
    no `event` rows with `knowledge_status = 'secret'`. (An event either
    happened or did not; uncertainty about it lives on `knowledge.level =
    'rumor'`, never on `event.knowledge_status` — TICKET-0022, R1.)

    `blindfolded` (BRIEF-12): when True, visual information is structurally
    excluded — `location.description` is set to None and `co_presents` entries
    carry no `description`. Sound/touch context stays. Same doctrine as secrets:
    the data is simply absent from the prompt, never guarded by instruction.

    `player_condition` (BRIEF-12): the player's current scene condition
    (unharmed | bruised | injured | neutralized). Injected into the returned
    dict so the MJ narration is bound by the mechanical reality.

    `relevance_hint` (schema v1.12, prepared/inert): reserved for a future
    relevance-selection stage that may only NARROW the security-scoped set
    above, never widen it. Inert until context size measurably hurts.
    """
    del relevance_hint  # reserved, inert (schema v1.12)

    loc_entity = db.get(Entity, location_id)
    location = db.get(Location, location_id)

    subculture: dict = {}
    if location:
        subculture_rows = db.exec(
            select(LocationSubculture).where(
                LocationSubculture.location_id == location_id,
                LocationSubculture.key.in_(_SAFE_SUBCULTURE_KEYS),
                LocationSubculture.is_hidden == False,  # noqa: E712
            )
        ).all()
        subculture = {row.key: row.value for row in subculture_rows if row.value}

    location_block = {
        "name": loc_entity.name if loc_entity else location_id,
        # Excluded when blindfolded — visual data structurally absent (BRIEF-12).
        "description": None if blindfolded else (loc_entity.description if loc_entity else None),
        "subculture": subculture,
    }

    # ----- Player knowledge — the player's own rows, no further filtering ---
    knowledge_rows = db.exec(
        select(Knowledge)
        .where(Knowledge.entity_id == player_character_id)
        .order_by(Knowledge.id)
    ).all()
    player_knowledge = [
        {"subject": k.subject, "level": k.level, "content": k.content}
        for k in knowledge_rows
    ]

    # ----- Public events — public/confirmed only, location-matched first ----
    public_events: list[dict] = []
    world_id = loc_entity.world_id if loc_entity else None
    if world_id:
        events = db.exec(
            select(Event)
            .where(
                Event.world_id == world_id,
                Event.knowledge_status.in_(("public", "confirmed")),
            )
            # `occurred_at` is written by nobody (in-fiction time, dormant
            # column) — order by `recorded_at`, aligning with tick.py and
            # app.py's return-visit delta (TICKET-0022, RECON finding 7).
            .order_by(Event.recorded_at.desc())
        ).all()
        local = [e for e in events if e.location_id == location_id]
        other = [e for e in events if e.location_id != location_id]
        for e in (local + other)[:_MJ_EVENT_CAP]:
            public_events.append({
                "title": e.title,
                "description": e.description,
                "type": e.type,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "location_id": e.location_id,
            })

    # ----- Co-presents (dynamic) — gathering roster, public entities only ---
    co_presents: list[dict] = []
    if gathering_id:
        co_rows = db.exec(
            select(GatheringMember, Entity)
            .join(Entity, Entity.id == GatheringMember.entity_id)
            .join(Character, Character.id == Entity.id)
            .where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
                Entity.status == "active",
                Character.vital_status == "alive",
            )
        ).all()
        for _member, co_entity in co_rows:
            if co_entity.id == player_character_id or not co_entity.is_public:
                continue
            co_presents.append({
                "name": co_entity.name,
                # Appearance excluded when blindfolded — visual data structurally
                # absent; sound/touch context (names) stays (BRIEF-12).
                "description": None if blindfolded else co_entity.description,
            })

    # ----- Custom skill vocabulary (BRIEF-55, schema v1.63) — names only ----
    # World-scoped at query construction, mirroring list_entities' pattern.
    # Names ONLY — no description, no tier, no per-PC data (Scope OUT 4/7).
    custom_skills: list[str] = []
    if world_id:
        custom_skills = [
            d.name
            for d in db.exec(
                select(SkillDefinition)
                .where(SkillDefinition.world_id == world_id)
                .order_by(SkillDefinition.name)
            ).all()
        ]

    return {
        "location": location_block,
        "player_knowledge": player_knowledge,
        "public_events": public_events,
        "co_presents": co_presents,
        "player_condition": player_condition,
        "custom_skills": custom_skills,
    }


def _mj_knowledge_line(k: dict) -> str:
    text = k.get("content") or f"{k.get('subject')} ({k.get('level')})"
    return f"- {text}"


def format_mj_context(mj_context: dict) -> str:
    """Render an `assemble_mj_context` dict as a French text block for the MJ prompt."""
    blocks: list[str] = []

    location = mj_context.get("location") or {}
    if location:
        loc_lines = [f"« {location.get('name', '?')} »."]
        if location.get("description"):
            loc_lines.append(location["description"])
        subculture = location.get("subculture") or {}
        ambiance = " ".join(str(v) for v in subculture.values() if v)
        if ambiance:
            loc_lines.append(f"Ambiance : {ambiance}")
        blocks.append(_section(H_MJ_LOCATION, " ".join(loc_lines)))

    co_presents = mj_context.get("co_presents") or []
    if co_presents:
        body = "\n".join(
            f"- {c['name']} : {c.get('description') or '(pas de description)'}"
            for c in co_presents
        )
        blocks.append(_section(H_MJ_PRESENT, body))

    player_knowledge = mj_context.get("player_knowledge") or []
    if player_knowledge:
        body = "\n".join(_mj_knowledge_line(k) for k in player_knowledge)
        blocks.append(_section(H_MJ_PLAYER_KNOWLEDGE, body))

    public_events = mj_context.get("public_events") or []
    if public_events:
        body = "\n".join(
            f"- {e['title']}" + (f" — {e['description']}" if e.get("description") else "")
            for e in public_events
        )
        blocks.append(_section(H_MJ_EVENTS, body))

    # Custom skill vocabulary (BRIEF-55) — names only, omitted entirely when
    # the world has none (no empty header).
    custom_skills = mj_context.get("custom_skills") or []
    if custom_skills:
        blocks.append(_section(H_MJ_CUSTOM_SKILLS, ", ".join(custom_skills)))

    # Player condition (BRIEF-12) — injected when not unharmed so the MJ
    # narration is aware of the mechanical reality and cannot contradict it.
    condition = mj_context.get("player_condition", "unharmed")
    if condition and condition != "unharmed":
        _condition_labels = {
            "bruised": "légèrement blessé / meurtri",
            "injured": "blessé, en mauvais état",
            "neutralized": "hors de combat / inconscient",
        }
        blocks.append(
            _section(
                "ÉTAT DU JOUEUR",
                f"Le joueur est actuellement : {_condition_labels.get(condition, condition)}.",
            )
        )

    if not blocks:
        return ""
    return "\n".join(blocks) + "\n"


def active_signposts(db: Session, location_id: str, player_character_id: str) -> list[str]:
    """Return the `content` strings of ambient signpost rows that should be
    narrated on entry (schema v1.30, BRIEF-17).

    Runs BEFORE any assembler, never through `assemble_mj_context`: this is
    the I3 code-predicate doctrine — the exhaustion judgment is a code
    predicate, never a prompt instruction. Returns ONLY ambient `content`
    prose; no `subject` or `signpost_group` value ever leaves this function.

    - Ungrouped ambient rows (`signpost_group IS NULL`) are always active.
    - Grouped ambient rows are silent iff the player holds a `knowledge` row
      (any level — existence only) for EVERY `hidden` row sharing that
      `signpost_group` (E1: silent only when the whole cluster is known).

    `discovered` is NOT a filter here — ambient panels are not "discovered";
    their visibility is governed by the cluster predicate above.
    """
    ambient_rows = db.exec(
        select(DiscoverableDetail).where(
            DiscoverableDetail.location_id == location_id,
            DiscoverableDetail.access_level == "ambient",
        )
    ).all()
    if not ambient_rows:
        return []

    groups_needed = {row.signpost_group for row in ambient_rows if row.signpost_group}
    cluster_subjects: dict[str, list[str]] = {}
    if groups_needed:
        hidden_rows = db.exec(
            select(DiscoverableDetail).where(
                DiscoverableDetail.location_id == location_id,
                DiscoverableDetail.access_level == "hidden",
                DiscoverableDetail.signpost_group.in_(groups_needed),
            )
        ).all()
        for row in hidden_rows:
            cluster_subjects.setdefault(row.signpost_group, []).append(row.subject)

    all_subjects = {s for subs in cluster_subjects.values() for s in subs}
    known_subjects: set[str] = set()
    if all_subjects:
        known_subjects = set(
            db.exec(
                select(Knowledge.subject).where(
                    Knowledge.entity_id == player_character_id,
                    Knowledge.subject.in_(all_subjects),
                )
            ).all()
        )

    active: list[str] = []
    for row in ambient_rows:
        if not row.signpost_group:
            active.append(row.content)
            continue
        subjects = cluster_subjects.get(row.signpost_group, [])
        if subjects and all(s in known_subjects for s in subjects):
            continue  # E1: whole cluster known — silent
        active.append(row.content)
    return active


def format_inventory_line(db: Session, player_character_id: str) -> str:
    """Render the player's static inventory as one compact French line
    (BRIEF-08, D2a.1): a single comma-separated list of canonical item names —
    the equipped/stowed split went dormant in this step (`item.equipped`
    stays in the schema, cockpit-only; see ARCHITECTURE_DECISIONS.md).

    Read fresh from `item` at every turn (no caching).
    """
    rows = db.exec(
        select(Item, Entity)
        .join(Entity, Entity.id == Item.id)
        .where(Item.owner_id == player_character_id)
    ).all()

    if not rows:
        return "Objets du joueur : aucun."

    items = ", ".join(entity.name for item, entity in rows)
    return f"Objets du joueur : {items}."


def format_item_list_for_interpretation(db: Session, player_character_id: str) -> str:
    """Render the player's tracked items for the interpretation prompt
    (BRIEF-08, D2a.1): same single list as `format_inventory_line` — the
    equip-state annotation is dropped now that the possession check is
    binary (owned/not owned).
    """
    return format_inventory_line(db, player_character_id)
