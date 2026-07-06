"""G1 check for TICKET-0012 (BRIEF-0012-a) — prompt lean rewrite gate.
Exit 0 on pass, 1 on failure; prints one line per failure.

Static assertions only (source text / AST, no DB):
1. NPC_DIALOGUE_SYSTEM_PROMPT carries none of the removed blocks.
2. No seed prompt constant (*_SYSTEM_PROMPT, *_USER_TEMPLATE) contains any
   pilot identifier, case-insensitively.
3. context.py: no "magiquement"; _SAFE_SUBCULTURE_KEYS == ("values",);
   _affinity_tier is defined and referenced inside assemble_npc_context.
4. "RÈGLES DE TARIFICATION" appears exactly once in context.py, zero times
   in seed_pilot.py.
5. CONVERSATION_ANALYSIS_SYSTEM_PROMPT: exactly 4 "=== EXEMPLE" markers,
   zero "=== EXAMPLE" markers, all three rubric headers present.
6. REGION_MANIFEST_SYSTEM_PROMPT: no "synchronis", no "BRIEF-", "au moins 4"
   appears twice.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "scripts" / "seed_pilot.py"
CONTEXT = ROOT / "src" / "world_engine" / "context.py"

PILOT_TERMS = ("maelis", "reike", "senna", "korin", "bryn", "dernier verre", "verkhaal")


def _seed_string_constants() -> dict[str, str]:
    """Module-level `*_SYSTEM_PROMPT` / `*_USER_TEMPLATE` string assignments."""
    tree = ast.parse(SEED.read_text(encoding="utf-8"), filename=str(SEED))
    out: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        if not (name.endswith("_SYSTEM_PROMPT") or name.endswith("_USER_TEMPLATE")):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            out[name] = node.value.value
    return out


def main() -> int:
    failures: list[str] = []

    seed_text = SEED.read_text(encoding="utf-8")
    context_text = CONTEXT.read_text(encoding="utf-8")
    constants = _seed_string_constants()

    # 1. Removed blocks gone from NPC_DIALOGUE_SYSTEM_PROMPT.
    npc_dialogue = constants.get("NPC_DIALOGUE_SYSTEM_PROMPT", "")
    if not npc_dialogue:
        failures.append("NPC_DIALOGUE_SYSTEM_PROMPT not found as a module-level string constant")
    for banned in ("ATTITUDE SELON LA RELATION", "RÈGLES DE TARIFICATION", "QUESTIONS SUR TES ALLÉGEANCES"):
        if banned in npc_dialogue:
            failures.append(f"NPC_DIALOGUE_SYSTEM_PROMPT still contains {banned!r}")

    # 2. No pilot identifiers in any seed prompt constant.
    for name, value in constants.items():
        lower = value.lower()
        hits = [t for t in PILOT_TERMS if t in lower]
        if hits:
            failures.append(f"{name} contains pilot identifier(s): {hits}")

    # 3. context.py structural checks.
    if "magiquement" in context_text:
        failures.append("context.py still contains 'magiquement'")
    if '_SAFE_SUBCULTURE_KEYS = ("values",)' not in context_text:
        failures.append('context.py: _SAFE_SUBCULTURE_KEYS is not exactly ("values",)')
    if "def _affinity_tier(" not in context_text:
        failures.append("context.py: _affinity_tier is not defined")
    else:
        assemble_start = context_text.find("def assemble_npc_context(")
        assemble_end = context_text.find("\ndef ", assemble_start + 1)
        if assemble_end == -1:
            assemble_end = len(context_text)
        assemble_body = context_text[assemble_start:assemble_end]
        if "_affinity_tier(" not in assemble_body:
            failures.append("context.py: _affinity_tier is not referenced inside assemble_npc_context")

    # 4. Pricing rules text lives in exactly one place.
    if context_text.count("RÈGLES DE TARIFICATION") != 1:
        failures.append(
            f"context.py: 'RÈGLES DE TARIFICATION' appears "
            f"{context_text.count('RÈGLES DE TARIFICATION')} times, expected 1"
        )
    if "RÈGLES DE TARIFICATION" in seed_text:
        failures.append("seed_pilot.py still contains 'RÈGLES DE TARIFICATION'")

    # 5. Conversation-analysis examples.
    conv = constants.get("CONVERSATION_ANALYSIS_SYSTEM_PROMPT", "")
    if not conv:
        failures.append("CONVERSATION_ANALYSIS_SYSTEM_PROMPT not found as a module-level string constant")
    exemple_count = conv.count("=== EXEMPLE")
    if exemple_count != 4:
        failures.append(f"CONVERSATION_ANALYSIS_SYSTEM_PROMPT has {exemple_count} '=== EXEMPLE' markers, expected 4")
    if "=== EXAMPLE" in conv:
        failures.append("CONVERSATION_ANALYSIS_SYSTEM_PROMPT still contains an '=== EXAMPLE' marker")
    for rubric in ("SIGN RUBRIC", "ANTI-INFLATION RUBRIC", "RESOURCE_CHANGE RUBRIC"):
        if rubric not in conv:
            failures.append(f"CONVERSATION_ANALYSIS_SYSTEM_PROMPT missing rubric header {rubric!r}")

    # 6. Region manifest sync note relocated.
    region = constants.get("REGION_MANIFEST_SYSTEM_PROMPT", "")
    if not region:
        failures.append("REGION_MANIFEST_SYSTEM_PROMPT not found as a module-level string constant")
    if "synchronis" in region:
        failures.append("REGION_MANIFEST_SYSTEM_PROMPT still contains 'synchronis'")
    if "BRIEF-" in region:
        failures.append("REGION_MANIFEST_SYSTEM_PROMPT still contains 'BRIEF-'")
    floor_count = region.count("au moins 4")
    if floor_count != 2:
        failures.append(f"REGION_MANIFEST_SYSTEM_PROMPT has 'au moins 4' {floor_count} times, expected 2")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print("PASS: prompt_lean — pilot purge, affinity tier resolver, pricing relocation, example trims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
