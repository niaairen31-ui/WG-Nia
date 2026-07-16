"""Region orchestrator — BRIEF-34, chantier 1; split into two phases by
BRIEF-38.

Turns a creator region brief into a **region draft**: a tree of per-entity
drafts plus draft-local references, produced by composing the atomic entity
generators (`entity_author.generate_entity_draft`). Writes NO canon — mirrors
`entity_author.py`'s posture exactly: the draft is returned to the caller,
ephemeral, never persisted here. `generate_entity_draft` itself is never
modified or monkeypatched — this module composes it as-is.

Two phases, split by a creator checkpoint (BRIEF-38, C1 — one-liner text
editing only): `generate_region_manifest(brief, db)` runs Stage 0 (the
model call producing the manifest) and returns it for the creator to edit;
`generate_region_draft(manifest, db)` takes that manifest (advisory —
re-normalized server-side first) and runs Stages 1-3 (Factions ->
Locations (root first) -> NPCs).

Locked design (see ARCHITECTURE_DECISIONS.md, "REGION GENERATION —
orchestrator (chantier 1)"): A3 (structural skeleton only, link suggestions
are confirm-by-creator), B1 (order Factions -> Locations -> NPCs), C1
(bounded forward context), F1 (sequential, peers as context), K1 (the
manifest IS the density control and the source of compact peer summaries),
I1 (factions flat in v1), J1 (stage-0 failure aborts; per-entity failure
drops and continues).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Optional

from sqlmodel import Session, select

from . import llm_parse
from .entity_author import AUTHOR_MODEL, generate_entity_draft, generate_npc_goals
from .models import PromptTemplate, World, WorldLaw
from .ollama_client import OllamaError, chat
from .prompt_registry import effective_model
from .prompt_store import current_prompt

# BRIEF-40: code-side targeted re-prompt clamp (A1). Must equal the prose
# floor stated in REGION_MANIFEST_SYSTEM_PROMPT (seed_pilot.py) — keep in sync.
MIN_NPCS_PER_FACTION = 4
MIN_FACTIONLESS = 4


def _active_world(db: Session) -> World | None:
    """BRIEF-44: the active world, for the manifest's premise reader."""
    return db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712


def _load_manifest_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "region_manifest")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def _load_manifest_topup_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "region_manifest_topup")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


# ── Stage 0 — manifest parsing (code judges, mirroring the atomic parsers) ──


def _name_key(name: str) -> str:
    """Normalize a name for dedup comparison only — apostrophe/whitespace/
    accent-composition variants of the same name fold to one key. The
    surviving row keeps its original, unnormalized name (RECON H1 fix)."""
    s = unicodedata.normalize("NFC", name)
    s = s.replace("’", "'").replace("ʼ", "'").replace("`", "'")
    s = " ".join(s.split())
    return s.lower()


def _dedupe_by_name(raw: Any, label: str, notes: list[str]) -> list[dict]:
    """Drop later case-insensitive duplicate names within one manifest list."""
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        key = _name_key(name)
        if key in seen:
            notes.append(f"{label} dupliqué ignoré : '{name}'")
            continue
        seen.add(key)
        rows.append(item)
    return rows


def _normalize_concept(parsed: dict) -> str:
    """The small local model sometimes emits a list of sentences instead of
    one string — coerce rather than drop (see CLAUDE.md "Local model notes":
    format compliance is best-effort, not guaranteed)."""
    concept_raw = parsed.get("concept")
    if isinstance(concept_raw, str):
        return concept_raw
    if isinstance(concept_raw, list):
        return " ".join(str(part) for part in concept_raw if isinstance(part, str))
    return ""


def _normalize_root_location(locations: list[dict], notes: list[str]) -> Optional[str]:
    """Exactly one root location. Mutates `locations` in place; returns the
    resolved root's name (None if `locations` is empty)."""
    root_indices = [i for i, l in enumerate(locations) if l.get("is_root") is True]
    if not root_indices:
        if locations:
            locations[0]["is_root"] = True
            notes.append(
                f"Aucun lieu racine désigné — '{locations[0]['name']}' promu racine"
            )
    elif len(root_indices) > 1:
        for i in root_indices[1:]:
            locations[i]["is_root"] = False
        notes.append(
            f"Plusieurs lieux racine désignés — seul '{locations[root_indices[0]]['name']}' "
            "reste racine"
        )

    for l in locations:
        if l.get("is_root") is True:
            return l["name"]
    return None


def _normalize_location_parents(
    locations: list[dict], location_names: set[str], root_name: Optional[str], notes: list[str],
) -> None:
    """parent_name validation for non-root locations. Mutates `locations` in place."""
    for l in locations:
        if l.get("is_root") is True:
            l["parent_name"] = None
            continue
        parent_name = l.get("parent_name")
        valid = (
            isinstance(parent_name, str)
            and parent_name.strip().lower() in location_names
            and parent_name.strip().lower() != l["name"].strip().lower()
        )
        if not valid:
            l["parent_name"] = root_name
            notes.append(
                f"Lieu '{l['name']}' — parent invalide ou absent, rattaché à la racine"
            )


def _normalize_npc_placement(
    npcs: list[dict], location_names: set[str], faction_names: set[str],
    skipped: list[dict], notes: list[str],
) -> list[dict]:
    """npc.location_name must resolve; on a miss, drop the NPC (appended to
    `skipped`). An unresolved faction_name is nulled, not dropped."""
    placed_npcs: list[dict] = []
    for n in npcs:
        location_name = n.get("location_name")
        if not isinstance(location_name, str) or location_name.strip().lower() not in location_names:
            skipped.append(
                {
                    "stage": "npc",
                    "name": n.get("name"),
                    "reason": f"location_name '{location_name}' introuvable dans le manifeste",
                }
            )
            continue
        faction_name = n.get("faction_name")
        if faction_name:
            if not isinstance(faction_name, str) or faction_name.strip().lower() not in faction_names:
                notes.append(
                    f"PNJ '{n.get('name')}' — faction_name '{faction_name}' introuvable, "
                    "mise à null"
                )
                n["faction_name"] = None
        placed_npcs.append(n)
    return placed_npcs


def _normalize_manifest(parsed: dict, notes: list[str]) -> tuple[dict, list[dict]]:
    """Structural normalization of a parsed manifest. Returns (manifest, skipped)."""
    skipped: list[dict] = []

    concept = _normalize_concept(parsed)
    factions = _dedupe_by_name(parsed.get("factions"), "Faction", notes)
    locations = _dedupe_by_name(parsed.get("locations"), "Lieu", notes)
    npcs = _dedupe_by_name(parsed.get("npcs"), "PNJ", notes)

    faction_names = {f["name"].strip().lower() for f in factions}
    location_names = {l["name"].strip().lower() for l in locations}

    root_name = _normalize_root_location(locations, notes)
    _normalize_location_parents(locations, location_names, root_name, notes)
    placed_npcs = _normalize_npc_placement(npcs, location_names, faction_names, skipped, notes)

    manifest = {
        "concept": concept,
        "factions": factions,
        "locations": locations,
        "npcs": placed_npcs,
    }
    return manifest, skipped


def _parse_manifest_response(raw: str) -> dict:
    """Returns {"ok": True, "manifest": ..., "notes": [...], "skipped": [...]}
    or {"ok": False, "error": ...}. Never raises."""
    try:
        parsed = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError:
        return {"ok": False, "error": "Model returned non-JSON manifest"}
    if not parsed:
        return {"ok": False, "error": "Model returned an empty or malformed manifest"}

    notes: list[str] = []
    manifest, skipped = _normalize_manifest(parsed, notes)
    return {"ok": True, "manifest": manifest, "notes": notes, "skipped": skipped}


# ── Stage 2b — compact peer context, manifest-sourced only ──────────────────


def _compose_faction_brief(concept: str, factions: list[dict], this_faction: dict) -> str:
    peers = [
        f"- {f['name']} : {f.get('one_liner', '')}"
        for f in factions
        if f["name"] != this_faction["name"]
    ]
    peer_block = "\n".join(peers) if peers else "(aucune autre faction)"
    return (
        f"{concept}\n\n"
        f"--- Autres factions de la région ---\n{peer_block}\n\n"
        f"--- Cette faction ---\n{this_faction['name']} : {this_faction.get('one_liner', '')}"
    )


def _compose_location_brief(concept: str, locations: list[dict], this_location: dict) -> str:
    lines = []
    for l in locations:
        parent = l.get("parent_name")
        suffix = f" (sous {parent})" if parent else " (racine)"
        lines.append(f"- {l['name']}{suffix} : {l.get('one_liner', '')}")
    loc_block = "\n".join(lines) if lines else "(aucun autre lieu)"
    return (
        f"{concept}\n\n"
        f"--- Lieux de la région ---\n{loc_block}\n\n"
        f"--- Ce lieu ---\n{this_location['name']} : {this_location.get('one_liner', '')}"
    )


def _compose_npc_brief(
    concept: str,
    npc: dict,
    location: dict | None,
    faction: dict | None,
    co_located: list[dict],
) -> str:
    parts = [concept, "", f"--- Ce PNJ ---\n{npc['name']} : {npc.get('one_liner', '')}"]
    if location is not None:
        parts.append(f"--- Son lieu ---\n{location['name']} : {location.get('one_liner', '')}")
    if faction is not None:
        parts.append(f"--- Sa faction ---\n{faction['name']} : {faction.get('one_liner', '')}")
    peers = [
        f"- {p['name']} : {p.get('one_liner', '')}"
        for p in co_located
        if p["name"] != npc["name"]
    ]
    if peers:
        parts.append("--- Autres PNJ du même lieu ---\n" + "\n".join(peers))
    return "\n\n".join(parts)


# ── BRIEF-40 — NPC top-up clamp (A1: one targeted re-prompt, code-judged) ───


def _npc_deficits(manifest: dict) -> dict[str | None, int]:
    """Map faction name (or None for factionless) -> shortfall against the
    floor. Only positive deficits are included."""
    npcs = manifest["npcs"]
    deficits: dict[str | None, int] = {}
    for faction in manifest["factions"]:
        name = faction["name"]
        count = sum(1 for n in npcs if n.get("faction_name") == name)
        deficit = max(0, MIN_NPCS_PER_FACTION - count)
        if deficit:
            deficits[name] = deficit
    factionless_count = sum(1 for n in npcs if n.get("faction_name") is None)
    factionless_deficit = max(0, MIN_FACTIONLESS - factionless_count)
    if factionless_deficit:
        deficits[None] = factionless_deficit
    return deficits


def _topup_blocks(manifest: dict, deficits: dict[str | None, int]) -> tuple[str, str, str, str]:
    factions_block = "\n".join(
        f"- {f['name']} : {f.get('one_liner', '')}" for f in manifest["factions"]
    ) or "(aucune)"
    locations_block = "\n".join(f"- {l['name']}" for l in manifest["locations"]) or "(aucun)"
    existing_npcs_block = "\n".join(f"- {n['name']}" for n in manifest["npcs"]) or "(aucun)"
    request_lines = []
    for faction_name, count in deficits.items():
        if faction_name is None:
            request_lines.append(f"Sans faction : {count} PNJ manquants")
        else:
            request_lines.append(f"Faction « {faction_name} » : {count} PNJ manquants")
    requests_block = "\n".join(request_lines)
    return factions_block, locations_block, existing_npcs_block, requests_block


def _run_npc_topup(result: dict, db: Session) -> dict:
    """Mutates and returns `result` in place: tops up under-floor NPCs via a
    single targeted re-prompt to AUTHOR_MODEL. Never raises; on any failure,
    appends a shortfall note and returns the original `result` unchanged."""
    manifest = result["manifest"]
    deficits = _npc_deficits(manifest)
    if not deficits:
        return result

    template = _load_manifest_topup_template(db)
    if template is None:
        result["notes"].append(
            "Plancher PNJ non atteint : modèle de complément introuvable, pas de complément tenté"
        )
        return result

    factions_block, locations_block, existing_npcs_block, requests_block = _topup_blocks(
        manifest, deficits
    )
    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{concept}", manifest["concept"])
        .replace("{factions_block}", factions_block)
        .replace("{locations_block}", locations_block)
        .replace("{existing_npcs_block}", existing_npcs_block)
        .replace("{requests_block}", requests_block)
    )

    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw_topup = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
        data = llm_parse.extract_object(raw_topup)
    except (OllamaError, llm_parse.LlmParseError) as exc:
        result["notes"].append(f"Plancher PNJ non atteint : complément échoué ({exc})")
        return result

    new_npcs = data.get("npcs")
    if not isinstance(new_npcs, list) or not new_npcs:
        result["notes"].append("Plancher PNJ non atteint : le complément n'a renvoyé aucun PNJ")
        return result

    merged = {**manifest, "npcs": manifest["npcs"] + new_npcs}
    normalized_manifest, new_skipped = _normalize_manifest(merged, result["notes"])
    result["manifest"] = normalized_manifest
    result["skipped"].extend(new_skipped)

    residual = _npc_deficits(normalized_manifest)
    if residual:
        result["notes"].append(
            "Plancher PNJ non atteint après complément : "
            + "; ".join(
                ("sans faction" if k is None else f"faction « {k} »") + f" manque {v}"
                for k, v in residual.items()
            )
        )
    return result


# ── Entry point ───────────────────────────────────────────────────────────


def generate_region_manifest(brief: str, db: Session) -> dict:
    """Phase A — produce the Stage-0 region manifest from a creator brief.

    Writes no canon. Never raises into the caller: every failure path
    returns {"ok": False, "error": ...} verbatim (empty brief, missing
    template, template format error, Ollama error, malformed/non-JSON
    manifest).

    After a successful parse, a code-side clamp (BRIEF-40, A1) checks the
    manifest against the NPC density floor and, if short, issues one
    targeted re-prompt to AUTHOR_MODEL for exactly the missing NPCs. The
    clamp only ever adds NPCs — it never caps, drops, or overrides the
    model's counts above the floor (K1, amended, bounded).
    """
    if not brief or not brief.strip():
        return {"ok": False, "error": "brief must not be empty"}

    template = _load_manifest_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-region-manifest template found"}

    world = _active_world(db)
    description = (world.description if world else None) or ""
    laws = db.exec(
        select(WorldLaw).where(WorldLaw.world_id == world.id).order_by(WorldLaw.position)
    ).all() if world else []
    fundamental_laws = "\n".join(law.text_ for law in laws)
    world_description = f"Contexte du monde : {description}\n\n" if description else ""
    world_fundamental_laws = (
        f"Lois fondamentales du monde (contraintes absolues) : {fundamental_laws}\n\n"
        if fundamental_laws else ""
    )

    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{brief}", brief)
        .replace("{world_description}", world_description)
        .replace("{world_fundamental_laws}", world_fundamental_laws)
    )

    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
    except OllamaError as exc:
        return {"ok": False, "error": str(exc)}

    result = _parse_manifest_response(raw)
    if not result["ok"]:
        return result

    return _run_npc_topup(result, db)


def _draft_factions(
    concept: str, factions_in: list[dict], skipped: list[dict], db: Session,
) -> tuple[dict[str, str], list[dict]]:
    """Stage 1 — factions. Returns (faction_local_id, factions_out)."""
    faction_local_id: dict[str, str] = {}
    factions_out: list[dict] = []
    for i, fac in enumerate(factions_in):
        local_id = f"fac-{i}"
        composite_brief = _compose_faction_brief(concept, factions_in, fac)
        result = generate_entity_draft("faction", composite_brief, db)
        if not result.get("ok"):
            skipped.append(
                {"stage": "faction", "name": fac["name"], "reason": result.get("error")}
            )
            continue
        faction_local_id[fac["name"].strip().lower()] = local_id
        factions_out.append({"local_id": local_id, "manifest": fac, "result": result})
    return faction_local_id, factions_out


def _draft_locations(
    concept: str, locations_in: list[dict], skipped: list[dict], notes: list[str], db: Session,
) -> tuple[dict[str, str], list[dict]]:
    """Stage 2 — locations, root first then the rest in manifest order.
    Returns (location_local_id, locations_out)."""
    root_first = sorted(
        enumerate(locations_in), key=lambda pair: 0 if pair[1].get("is_root") else 1
    )
    location_local_id: dict[str, str] = {}
    locations_out: list[dict] = []
    for i, loc in root_first:
        local_id = f"loc-{i}"
        composite_brief = _compose_location_brief(concept, locations_in, loc)
        result = generate_entity_draft("location", composite_brief, db)
        if not result.get("ok"):
            skipped.append(
                {"stage": "location", "name": loc["name"], "reason": result.get("error")}
            )
            continue
        parent_name = loc.get("parent_name")
        parent_local_id = None
        if parent_name:
            parent_local_id = location_local_id.get(parent_name.strip().lower())
            if parent_local_id is None and not loc.get("is_root"):
                notes.append(
                    f"Lieu '{loc['name']}' — parent '{parent_name}' indisponible (généré en échec)"
                )
        location_local_id[loc["name"].strip().lower()] = local_id
        locations_out.append(
            {
                "local_id": local_id,
                "parent_local_id": parent_local_id,
                "manifest": loc,
                "result": result,
            }
        )
    return location_local_id, locations_out


def _draft_one_npc(
    i: int, npc: dict, concept: str, npcs_in: list[dict],
    location_local_id: dict[str, str], faction_local_id: dict[str, str],
    locations_by_name: dict[str, dict], factions_by_name: dict[str, dict],
    faction_goals_by_local: dict[str, Any], skipped: list[dict], notes: list[str], db: Session,
) -> Optional[dict]:
    """One Stage-3 NPC: composite brief -> draft -> (on success) goals.
    Returns None (appended to `skipped`) when the host location is
    unavailable or the character draft itself fails."""
    location_name = npc["location_name"].strip().lower()
    loc_local = location_local_id.get(location_name)
    if loc_local is None:
        skipped.append(
            {
                "stage": "npc",
                "name": npc.get("name"),
                "reason": f"lieu '{npc['location_name']}' indisponible (généré en échec)",
            }
        )
        return None

    faction_name = npc.get("faction_name")
    fac_local = None
    if faction_name:
        fac_local = faction_local_id.get(faction_name.strip().lower())
        if fac_local is None:
            notes.append(
                f"PNJ '{npc['name']}' — faction '{faction_name}' indisponible (généré en échec), "
                "affiliation mise à null"
            )

    co_located = [
        other for other in npcs_in if other["location_name"].strip().lower() == location_name
    ]
    location_obj = locations_by_name.get(location_name)
    faction_obj = factions_by_name.get(faction_name.strip().lower()) if faction_name else None

    composite_brief = _compose_npc_brief(concept, npc, location_obj, faction_obj, co_located)
    result = generate_entity_draft("character", composite_brief, db)
    if not result.get("ok"):
        skipped.append(
            {"stage": "npc", "name": npc.get("name"), "reason": result.get("error")}
        )
        return None

    # BRIEF-0013-b (G1): goals generated after the character draft succeeds,
    # attached read-only to the draft for the region review UI. A goal-
    # generation failure never drops the NPC — it ships without goals, noted.
    pub = result["draft"]["public"]
    goals_result = generate_npc_goals(
        pub.get("name", ""),
        pub.get("description", ""),
        pub.get("backstory", ""),
        faction_goals_by_local.get(fac_local) if fac_local else None,
        db,
    )
    if goals_result.get("ok"):
        pub["goals"] = {"long": goals_result.get("long", ""), "shorts": goals_result.get("shorts", [])}
    else:
        notes.append(
            f"PNJ '{npc['name']}' — génération des objectifs échouée : {goals_result.get('error')}"
        )

    return {
        "local_id": f"npc-{i}",
        "location_local_id": loc_local,
        "faction_local_id": fac_local,
        "manifest": npc,
        "result": result,
    }


def _draft_npcs(
    concept: str, npcs_in: list[dict], locations_in: list[dict], factions_in: list[dict],
    location_local_id: dict[str, str], faction_local_id: dict[str, str],
    factions_out: list[dict], skipped: list[dict], notes: list[str], db: Session,
) -> list[dict]:
    """Stage 3 — NPCs."""
    locations_by_name = {l["name"].strip().lower(): l for l in locations_in}
    factions_by_name = {f["name"].strip().lower(): f for f in factions_in}

    # BRIEF-0013-b (G1): faction.goals per local_id, for generate_npc_goals'
    # faction_goals input only — None when a faction draft's secret.goals is
    # empty. `faction.goals` gains its first reader here, as generator INPUT
    # only; prompt injection of faction posture remains a separate chantier.
    faction_goals_by_local = {
        f["local_id"]: (f["result"]["draft"]["secret"].get("goals") or None)
        for f in factions_out
    }

    npcs_out: list[dict] = []
    for i, npc in enumerate(npcs_in):
        drafted = _draft_one_npc(
            i, npc, concept, npcs_in, location_local_id, faction_local_id,
            locations_by_name, factions_by_name, faction_goals_by_local,
            skipped, notes, db,
        )
        if drafted is not None:
            npcs_out.append(drafted)
    return npcs_out


def generate_region_draft(manifest: dict, db: Session) -> dict:
    """Phase B — generate a region draft (factions/locations/NPCs) from an
    already-produced manifest dict (Phase A's output, possibly creator-edited).

    The incoming manifest is advisory; this function re-runs
    `_normalize_manifest` on it first and uses the result as authoritative,
    guaranteeing invariants on untrusted re-submitted input. Writes no canon
    anywhere in this function or its call path. Never raises into the
    caller: a per-entity Stage 1-3 failure drops that entity (recorded in
    `region.skipped`) and the run continues. See `_draft_factions` /
    `_draft_locations` / `_draft_npcs` for the per-stage logic.
    """
    notes: list[str] = []
    manifest, skipped = _normalize_manifest(dict(manifest), notes)

    concept = manifest["concept"]
    factions_in = manifest["factions"]
    locations_in = manifest["locations"]
    npcs_in = manifest["npcs"]

    faction_local_id, factions_out = _draft_factions(concept, factions_in, skipped, db)
    location_local_id, locations_out = _draft_locations(concept, locations_in, skipped, notes, db)
    npcs_out = _draft_npcs(
        concept, npcs_in, locations_in, factions_in, location_local_id, faction_local_id,
        factions_out, skipped, notes, db,
    )

    region = {
        "concept": concept,
        "factions": factions_out,
        "locations": locations_out,
        "npcs": npcs_out,
        "skipped": skipped,
        "notes": notes,
    }
    return {"ok": True, "region": region}
