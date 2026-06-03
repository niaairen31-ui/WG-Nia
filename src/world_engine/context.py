"""NPC context assembly — the engine's structural control over what an NPC may say.

`assemble_npc_context` gathers everything an NPC is allowed to use to speak, in
clearly separated sections, while structurally protecting its secrets. It reads
ONLY the NPC's own rows: never another entity's secrets, never the
interlocutor's knowledge or secrets (the NPC cannot read minds).

The output is a French text block (the world and the local dialogue model both
work in French) ready to drop into a model prompt. It is intentionally not JSON:
it is a briefing addressed to the NPC.

Design rules enforced here:
- Section "freely" = this NPC's knowledge rows with is_secret = FALSE.
- Section "conceal" = this NPC's knowledge rows with is_secret = TRUE, marked
  unmistakably and paired with an explicit non-revelation instruction.
- Perception = relations where THIS NPC is the perceiver (entity_a + a_to_b,
  entity_b + b_to_a, or mutual) toward the interlocutor or other people present.
- The location's hidden/secret subculture fields are never rendered.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import Character, Entity, Knowledge, Location, Relation

# Section headers (kept stable so a harness can split the output reliably).
H_IDENTITY = "QUI TU ES"
H_SETTING = "OÙ TU TE TROUVES"
H_FREE = "CE QUE TU SAIS ET PEUX DIRE LIBREMENT"
H_CONCEAL = "CE QUE TU SAIS MAIS DOIS CACHER — NE JAMAIS RÉVÉLER"
H_PERCEPTION = "COMMENT TU VOIS CEUX QUI T'ENTOURENT"
H_BOUNDARIES = "LIMITES STRICTES"

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

    Reads only the NPC's own identity, knowledge, and outgoing perceptions, plus
    public identity/atmosphere of the interlocutor and location. Never injects
    another entity's secrets nor the interlocutor's knowledge.
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

    # ----- 3 & 4. Knowledge, split by concealment ---------------------------
    knowledge = session.exec(
        select(Knowledge)
        .where(Knowledge.entity_id == npc_id)
        .order_by(Knowledge.id)
    ).all()
    shareable = [k for k in knowledge if not k.is_secret]
    secret = [k for k in knowledge if k.is_secret]

    if shareable:
        free_body = "Tu peux parler librement de ce qui suit, si la conversation s'y prête :\n"
        free_body += "\n".join(_knowledge_line(k) for k in shareable)
    else:
        free_body = "Tu n'as rien de particulier à partager spontanément."

    conceal_intro = (
        "⚠️ SECRET — Ce qui suit ne doit JAMAIS sortir de ta bouche.\n"
        "Tu ne dois jamais le révéler, le confirmer, ni le laisser deviner.\n"
        "Si l'on te presse, esquive, change de sujet, ou nie — mais ne confirme JAMAIS."
    )
    if secret:
        conceal_body = conceal_intro + "\n\n" + "\n".join(
            _knowledge_line(k) for k in secret
        )
    else:
        conceal_body = "Tu ne caches rien de particulier."

    # ----- 5. Perception of those present -----------------------------------
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

    present = session.exec(
        select(Character).where(Character.current_location_id == location_id)
    ).all()
    present_ids = [c.id for c in present]

    perception_lines = [f"Face à toi : {inter_name}."]
    if interlocutor_id in perceived:
        perception_lines.append("  " + _render_perception(inter_name, perceived[interlocutor_id]))
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

    # ----- 6. Hard boundaries ----------------------------------------------
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
        + _section(H_FREE, free_body)
        + "\n"
        + _section(H_CONCEAL, conceal_body)
        + "\n"
        + _section(H_PERCEPTION, perception)
        + "\n"
        + _section(H_BOUNDARIES, boundaries)
    )
