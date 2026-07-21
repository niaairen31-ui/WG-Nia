"""G1 gate: UI-visible data is never stored in JSON (TICKET-0025).

Motivated by the TICKET-0024 duplication bug — RECON failed to detect a UI
field backed by an `entity.metadata` JSON key, producing a parallel role
structure. This check makes "no JSON storage for UI-visible data" a
structural, fail-closed property of the codebase instead of a CLAUDE.md
note. Three volets, all must pass:

  a. CRUD registry volet — no `"kind": "json"` field spec survives in
     `ENTITY_BASE_FIELDS` or `ENTITY_TYPE_REGISTRY` (cockpit/crud.py).
     Allow-list: EMPTY.
  b. Source-access volet — no `metadata_` attribute access and no
     `Column("metadata"` declaration anywhere in `src/`, outside comments.
     Allow-list: EMPTY. Regression guard: the column died in BRIEF-0025-a;
     this keeps it dead.
  c. JSON-column volet — every `Column(JSON` occurrence in `models.py`
     must be a named, justified entry in `JSON_COLUMN_ALLOWLIST` below.
     Any JSON column absent from the allow-list fails; any allow-list
     entry whose column no longer exists fails (stale exceptions rot).

Per run.py doctrine, a volet that parses to zero findings is a FAIL, not a
pass — a parse that finds nothing is a broken parse, not a clean repo.

No DB, plain text/regex scan of `crud.py` and `models.py` plus a `src/`
tree walk.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
CRUD_PY = SRC / "world_engine" / "cockpit" / "crud" / "entities.py"
# Retargeted (TICKET-0028, BRIEF-0028-c): models.py split into a models/
# package by schema stratum — volet c now walks every file in the package
# instead of one flat module (relocation-not-broadening precedent,
# BRIEF-0027-c/-d).
MODELS_DIR = SRC / "world_engine" / "models"

# Volet c — every `Column(JSON` occurrence in models.py must appear here,
# one line each with justification. Adding a JSON column requires editing
# this allow-list — a visible, reviewable diff, never a convention.
JSON_COLUMN_ALLOWLIST = {
    # Polymorphic model-proposal envelope; rendered readonly in the
    # review queue; shape is the mutation type's contract, not a UI
    # field. First structured UI consumer must relationalize.
    "ProposedMutation.payload",
    # Append-only audit snapshots — never rendered in any UI surface.
    "Relation.change_history",
    "Knowledge.change_history",
    "NpcGoal.change_history",
    "Skill.change_history",
    "Agenda.change_history",
    "AgendaStep.change_history",
    # Internal engine snapshots — never rendered in any UI surface.
    "PassPlay.injected_context",
    "PassPlay.history",
    "Conversation.injected_context",
    "Conversation.scene_state",
    "Visit.present_npc_ids",
    # No UI consumer today. The FIRST UI consumer of any of these
    # MUST migrate it to relational storage in the same brief.
    "Event.consequences",
    "Artifact.known_properties",
    "Artifact.actual_behavior",
    # NPC link agent staging (TICKET-0036, BRIEF-0036-a) — ephemeral
    # stratum, same non-canon status as scene_state/injected_context above.
    # Individual fields are edited in the batch review UI (0036-d), but
    # ONLY via PATCH /api/link-batches/{id}/rows/{row_id}, which re-validates
    # each field through the same vocab/clamp gate as the coherence patch
    # pipeline (_coerce_patch_value) — never a raw JSON blob edit. This
    # staging row mirrors the write_relation/write_knowledge kwargs it
    # becomes on commit; it is not a durable UI-query surface. The FIRST
    # consumer that needs to QUERY into these fields (list/filter/report)
    # must relationalize.
    "LinkBatch.scope",
    "LinkBatch.coherence_findings",
    "LinkBatchRow.payload",
    # NPC group agent staging (TICKET-0037, BRIEF-0037-a) — ephemeral
    # stratum, same non-canon status as the link-agent staging fields
    # above. No frontend surface exists yet this step (that is
    # BRIEF-0037-c); once it lands, any per-field edit route must
    # re-validate through a vocab/clamp gate rather than a raw JSON blob
    # edit, same posture as LinkBatchRow.payload. This staging row mirrors
    # the per-NPC `_create_entity_core`/`write_npc_goal` kwargs it becomes
    # on commit; it is not a durable UI-query surface. The FIRST consumer
    # that needs to QUERY into these fields (list/filter/report) must
    # relationalize.
    "NpcBatch.scope",
    "NpcBatchRow.payload",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def _extract_between(src: str, start_marker: str, end_marker: str) -> str:
    start = src.find(start_marker)
    if start == -1:
        return ""
    end = src.find(end_marker, start + len(start_marker))
    return src[start:end] if end != -1 else src[start:]


def _check_crud_registry_volet(src: str) -> None:
    base_fields_block = _extract_between(
        src, "ENTITY_BASE_FIELDS:", "# ── Type"
    )
    registry_block = _extract_between(
        src, "ENTITY_TYPE_REGISTRY:", "# ── Relation / knowledge field specs"
    )
    if not base_fields_block or not registry_block:
        fail("volet a: could not locate ENTITY_BASE_FIELDS / ENTITY_TYPE_REGISTRY in crud.py")

    field_count = len(re.findall(r'"name":\s*"', base_fields_block)) + \
        len(re.findall(r'"name":\s*"', registry_block))
    if field_count == 0:
        fail("volet a: zero field specs found — parse is broken, not the repo clean")

    json_kinds = re.findall(r'"kind":\s*"json"', base_fields_block) + \
        re.findall(r'"kind":\s*"json"', registry_block)
    if json_kinds:
        fail(f"volet a: {len(json_kinds)} \"kind\": \"json\" field spec(s) found in the CRUD registry")


def _check_source_access_volet() -> None:
    py_files = sorted(SRC.rglob("*.py"))
    if not py_files:
        fail("volet b: zero .py files found under src/ — parse is broken")

    hits: list[str] = []
    for path in py_files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_part = line.split("#", 1)[0]
            if re.search(r"\bmetadata_\b", code_part) or 'Column("metadata"' in code_part:
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{lineno}")

    if hits:
        fail(f"volet b: metadata_/Column(\"metadata\" reference(s) found outside comments: {', '.join(hits)}")


def _scan_json_columns_one(rel: str, src: str) -> dict[str, int]:
    """Per-file scan — `current_class`/`current_field` state never crosses a
    file boundary, so each models/*.py file is scanned independently."""
    lines = src.splitlines()
    current_class: str | None = None
    current_field: str | None = None
    found: dict[str, int] = {}

    for lineno, line in enumerate(lines, 1):
        class_match = re.match(r"class (\w+)\(SQLModel", line)
        if class_match:
            current_class = class_match.group(1)
            current_field = None
            continue
        field_match = re.match(r"    (\w+)\s*:\s*", line)
        if field_match:
            current_field = field_match.group(1)
        if "Column(JSON" in line:
            if current_class is None or current_field is None:
                fail(f"volet c: Column(JSON at {rel}:{lineno} could not be attributed to a class.field")
            found[f"{current_class}.{current_field}"] = lineno

    return found


def _check_json_column_volet(models_dir: pathlib.Path) -> None:
    found: dict[str, int] = {}
    for path in sorted(models_dir.glob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        found.update(_scan_json_columns_one(rel, path.read_text(encoding="utf-8")))

    if not found:
        fail("volet c: zero Column(JSON occurrences found — parse is broken, not the repo clean")

    unlisted = sorted(set(found) - JSON_COLUMN_ALLOWLIST)
    if unlisted:
        fail(f"volet c: JSON column(s) not in JSON_COLUMN_ALLOWLIST: {', '.join(unlisted)}")

    stale = sorted(JSON_COLUMN_ALLOWLIST - set(found))
    if stale:
        fail(f"volet c: JSON_COLUMN_ALLOWLIST entry(ies) whose column no longer exists: {', '.join(stale)}")


def main() -> None:
    if not CRUD_PY.exists():
        fail(f"{CRUD_PY} not found")
    if not MODELS_DIR.is_dir():
        fail(f"{MODELS_DIR} not found")

    crud_src = CRUD_PY.read_text(encoding="utf-8")

    _check_crud_registry_volet(crud_src)
    _check_source_access_volet()
    _check_json_column_volet(MODELS_DIR)

    print(
        "PASS: json_ui_boundary — zero \"kind\": \"json\" CRUD fields, zero "
        "metadata_/Column(\"metadata\" references outside comments, every "
        "Column(JSON in models/*.py is a named allow-list entry"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
