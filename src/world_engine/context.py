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

from .models import Character, Entity, Knowledge, Location, Relation

# Section headers (kept stable so a harness can split the output reliably).
H_IDENTITY = "QUI TU ES"
H_SETTING = "OÙ TU TE TROUVES"
H_SPEAK = "CE QUE TU PEUX ÉVOQUER"
H_PERCEPTION = "COMMENT TU VOIS CEUX QUI T'ENTOURENT"
H_BOUNDARIES = "LIMITES STRICTES"

# Neutral relation intensity assumed when the NPC has no read on the interlocutor.
NEUTRAL_INTENSITY = 50

# Subculture keys safe to surface as ambient atmosphere. Anything else
# (e.g. "hidden", "secret") is deliberately withheld from the Setting section.
_SAFE_SUBCULTURE_KEYS = ("values", "magic_phenomena", "nexus_link")

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
    return (
        f"- {name} : {rel.notes} "
        f"(perception : {rel.type}, intensité {rel.intensity}/100)"
    )


def assemble_npc_context(
    npc_id: str,
    interlocutor_id: str,
    location_id: str,
    session: Session,
) -> str:
    """Assemble the text briefing that drives this NPC's dialogue.

    Secrets are excluded outright; non-secret knowledge is gated by the
    NPC→interlocutor relation intensity against each row's share_threshold.
    """
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
    if npc_entity.description:
        identity_lines.append(npc_entity.description)
    identity = " ".join(identity_lines)

    # ----- 2. Setting -------------------------------------------------------
    loc_entity = session.get(Entity, location_id)
    location = session.get(Location, location_id)
    loc_name = loc_entity.name if loc_entity else location_id
    setting_lines = [f"Tu te trouves dans un lieu nommé « {loc_name} »."]
    if loc_entity and loc_entity.description:
        setting_lines.append(loc_entity.description)
    if location:
        atmo = f"L'atmosphère y est magiquement « {location.magic_status} »"
        phenomena = None
        if isinstance(location.subculture, dict):
            # Only surface allow-listed, non-sensitive subculture fields.
            phenomena = location.subculture.get("magic_phenomena")
        if phenomena:
            atmo += f" : {phenomena.rstrip(' .')}"
        atmo += "."
        setting_lines.append(atmo)
        if isinstance(location.subculture, dict):
            values = location.subculture.get("values")
            if values:
                setting_lines.append(values)
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

    # ----- 5. Hard boundaries ----------------------------------------------
    boundaries = (
        "Tu ne sais que ce qui est écrit ci-dessus. N'invente aucun fait sur le "
        "monde, sur les autres personnes, ou sur des événements au-delà de ce "
        "contexte. Si l'on t'interroge sur quelque chose que tu ignores, réagis "
        "comme quelqu'un qui, simplement, ne sait pas."
    )

    return (
        _section(H_IDENTITY, identity)
        + "\n"
        + _section(H_SETTING, setting)
        + "\n"
        + _section(H_SPEAK, speak_body)
        + "\n"
        + _section(H_PERCEPTION, perception)
        + "\n"
        + _section(H_BOUNDARIES, boundaries)
    )
