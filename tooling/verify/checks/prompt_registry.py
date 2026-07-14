"""G1 check for TICKET-0008 (BRIEF-0008-a) — prompt registry structural gate.
Exit 0 on pass, 1 on failure; prints one line per failure.

Four assertions:
1. Bijection: usages seeded in scripts/seed_pilot.py == PROMPT_REGISTRY keys.
2. Every registry entry declares all five fields; call_sites non-empty; each
   "path:function" resolves to an existing file with that `def`.
3. Static wiring scan: every ollama_client.chat(/chat(/chat_stream( call
   carrying a `model=` argument uses `model=effective_model(` — except
   functions on the explicit exemption allowlist (the injected-context call
   path in the `say` play path — app.py plus its BRIEF-0027-b decomposition
   into cockpit/play*.py — deferred to the write-path chantier; see
   CLAUDE.md "Exemption, by construction").
4. effective_model's pure resolver behavior: NULL template.model -> default.
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
SEED = ROOT / "scripts" / "seed_pilot.py"

sys.path.insert(0, str(ROOT / "src"))

# Files carrying a templated chat()/chat_stream() call, per BRIEF-0008-a Scope IN 3.
WIRED_FILES = [
    SRC / "entity_author.py",
    SRC / "region_author.py",
    SRC / "analyzer.py",
    SRC / "gathering.py",
    SRC / "cockpit" / "play.py",
    SRC / "cockpit" / "play_physical.py",
    SRC / "cockpit" / "play_stream.py",
    SRC / "tick.py",
]

# Exemption allowlist (by enclosing function name): the call path whose
# model comes from `injected.get("model", DEFAULT_MODEL)` (originally
# `say`/`_stream` in app.py; decomposed by BRIEF-0027-b into cockpit/play*.py,
# then those helpers redistributed again by BRIEF-0027-d's router split —
# every one of these still consumes that single already-resolved value via
# its own `model` parameter rather than a PromptTemplate object). Wiring
# effective_model there would silently encode a template.model vs
# injected_context["model"] precedence — deferred to the write-path
# chantier (BRIEF-0008-a Scope OUT).
EXEMPT_FUNCTIONS = {
    SRC / "cockpit" / "play_physical.py": {
        "_interpret_mode",
        "_arbitrate",
        "_say_physical_npc_reaction",
    },
    SRC / "cockpit" / "play_stream.py": {
        "_npc_initiative_vote",
        "_select_group_speaker",
        "_say_stream_mj_narration",
        "_say_initiative_generate",
        "_say_initiative_narrate",
    },
    SRC / "cockpit" / "play.py": {
        "_say_npc_generation",
    },
}

USAGE_LINE = re.compile(r'usage\s*=\s*"([a-z_]+)"')


def _seeded_usages() -> set[str]:
    text = SEED.read_text(encoding="utf-8")
    return set(USAGE_LINE.findall(text))


class _ChatCallScan(ast.NodeVisitor):
    """Finds every chat(/chat_stream( call with a `model=` kwarg, tagging
    each with its innermost enclosing function name."""

    def __init__(self):
        self.func_stack: list[str] = []
        self.findings: list[tuple[int, str, bool]] = []  # (lineno, func, wired)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    def visit_Call(self, node: ast.Call):
        callee = node.func
        name = callee.id if isinstance(callee, ast.Name) else (
            callee.attr if isinstance(callee, ast.Attribute) else None
        )
        if name in ("chat", "chat_stream"):
            model_kw = next((kw for kw in node.keywords if kw.arg == "model"), None)
            if model_kw is not None:
                wired = (
                    isinstance(model_kw.value, ast.Call)
                    and isinstance(model_kw.value.func, ast.Name)
                    and model_kw.value.func.id == "effective_model"
                )
                enclosing = self.func_stack[-1] if self.func_stack else "<module>"
                self.findings.append((node.lineno, enclosing, wired))
        self.generic_visit(node)


def main() -> int:
    failures: list[str] = []

    # 1. Bijection.
    from world_engine import prompt_registry

    seeded = _seeded_usages()
    registry_keys = set(prompt_registry.PROMPT_REGISTRY.keys())
    missing_from_registry = seeded - registry_keys
    missing_from_seed = registry_keys - seeded
    for usage in sorted(missing_from_registry):
        failures.append(f"usage {usage!r} is seeded but has no PROMPT_REGISTRY entry")
    for usage in sorted(missing_from_seed):
        failures.append(f"PROMPT_REGISTRY entry {usage!r} has no seeded usage")

    # 2. Entry shape + call_sites resolve.
    required_fields = ("surface", "world_scoped", "dry_run_capable", "call_sites", "default_model")
    for usage, entry in prompt_registry.PROMPT_REGISTRY.items():
        for field in required_fields:
            if not hasattr(entry, field):
                failures.append(f"PROMPT_REGISTRY[{usage!r}] is missing field {field!r}")
        call_sites = getattr(entry, "call_sites", ())
        if not call_sites:
            failures.append(f"PROMPT_REGISTRY[{usage!r}].call_sites is empty")
        for site in call_sites:
            if ":" not in site:
                failures.append(f"PROMPT_REGISTRY[{usage!r}] call site {site!r} is not 'path:function'")
                continue
            rel_path, func_name = site.rsplit(":", 1)
            path = ROOT / rel_path
            if not path.exists():
                failures.append(f"PROMPT_REGISTRY[{usage!r}] call site path not found: {rel_path}")
                continue
            if not re.search(rf"^def {re.escape(func_name)}\(", path.read_text(encoding="utf-8"), re.MULTILINE):
                failures.append(
                    f"PROMPT_REGISTRY[{usage!r}] call site {site!r}: "
                    f"'def {func_name}(' not found in {rel_path}"
                )

    # 3. Static wiring scan.
    for path in WIRED_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        scanner = _ChatCallScan()
        scanner.visit(tree)
        exempt = EXEMPT_FUNCTIONS.get(path, set())
        for lineno, func, wired in scanner.findings:
            if wired or func in exempt:
                continue
            failures.append(
                f"{path.relative_to(ROOT)}:{lineno} in {func}() carries a bare "
                "model= argument, not model=effective_model( — and is not on "
                "the exemption allowlist"
            )

    # 4. Resolver default behavior (pure-function assertion, no DB).
    class _StubTemplate:
        model = None

    if prompt_registry.effective_model(None, "d") != "d":
        failures.append("effective_model(None, 'd') != 'd'")
    if prompt_registry.effective_model(_StubTemplate(), "d") != "d":
        failures.append("effective_model(<template with model=None>, 'd') != 'd'")

    class _OverrideTemplate:
        model = "custom-model"

    if prompt_registry.effective_model(_OverrideTemplate(), "d") != "custom-model":
        failures.append("effective_model(<template with model set>, 'd') did not return the override")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: prompt_registry — usage bijection, registry entry shape, "
        "static resolver wiring, effective_model pure-function behavior"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
