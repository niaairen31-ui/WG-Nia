"""G1 check for TICKET-0125 -- the Lore perspective tab and the player shell are wired and confined.

PSH1 -- static (BRIEF-0125-F): `frontend/src/lore/Lore.svelte` holds
   `loreTab === 'perspective'`, the tab button's `(loreTab = 'perspective')`
   and `<PerspectivePanel`;
   `frontend/src/lore/perspective.svelte.js` posts to
   `/api/lore/perspective/ask` and `/api/lore/perspective/resolve` and sends
   `attempt_id`; `frontend/src/lore/PerspectivePanel.svelte` holds the five
   French reason labels (`réservé à la créatrice`, `pas public`, `entité non
   publique`, `appartenance secrète`, `faction non publique`) and `Rien n'a
   été retenu.`, and none of `alert(`, `confirm(`, `prompt(`.
PSH2 -- (BRIEF-0125-G) every `fetch(` / `call(` URL literal under
   `frontend/src/joueur/` starts with `/api/joueur/`; at least one found.
PSH3 -- no `import` under `frontend/src/joueur/` resolves outside that
   folder: a specifier is `svelte` (or `svelte/...`) or a relative `./`
   path, never `..` nor an absolute path; at least one import found.
PSH4 -- `frontend/vite.config.js` names `jouer.html` as an input;
   `frontend/jouer.html` loads `/src/joueur/main.js`;
   `src/world_engine/cockpit/app.py` holds the `/jouer` decorator route
   reading `jouer.html`; `/jouer` is not in `_SHELL_ROUTES`.

A missing file, or a rule that collected nothing, is a FAILURE.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
LORE = ROOT / "frontend" / "src" / "lore"
JOUEUR = ROOT / "frontend" / "src" / "joueur"
VITE_CONFIG = ROOT / "frontend" / "vite.config.js"
JOUER_HTML = ROOT / "frontend" / "jouer.html"
APP_PY = ROOT / "src" / "world_engine" / "cockpit" / "app.py"

# A fetch( or call( whose first argument is a string literal (quote or backtick).
URL_CALL_RE = re.compile(r"\b(?:fetch|call)\(\s*(['\"`])([^'\"`]*)\1")
# `import x from '...'`, a bare `import '...'`, or a dynamic `import('...')`.
IMPORT_RE = re.compile(
    r"\bimport\b[^'\"`;]*?\bfrom\s*['\"]([^'\"]+)['\"]"
    r"|\bimport\s*['\"]([^'\"]+)['\"]"
    r"|\bimport\(\s*['\"]([^'\"]+)['\"]"
)

REASON_LABELS = ("réservé à la créatrice", "pas public", "entité non publique",
                 "appartenance secrète", "faction non publique")
DIALOGS = ("alert(", "confirm(", "prompt(")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: pathlib.Path) -> str | None:
    if not path.exists():
        fail(f"{path.relative_to(ROOT)} missing")
        return None
    return path.read_text(encoding="utf-8")


def rule_psh1() -> None:
    lore = _read(LORE / "Lore.svelte")
    if lore is not None:
        for needle in ("loreTab === 'perspective'", "(loreTab = 'perspective')", "<PerspectivePanel"):
            if needle not in lore:
                fail(f"PSH1: Lore.svelte lacks {needle}")
    state = _read(LORE / "perspective.svelte.js")
    if state is not None:
        for needle in ("'/api/lore/perspective/ask'", "'/api/lore/perspective/resolve'", "attempt_id"):
            if needle not in state:
                fail(f"PSH1: perspective.svelte.js lacks {needle}")
    panel = _read(LORE / "PerspectivePanel.svelte")
    if panel is not None:
        for needle in (*REASON_LABELS, "Rien n'a été retenu."):
            if needle not in panel:
                fail(f"PSH1: PerspectivePanel.svelte lacks {needle!r}")
        for needle in DIALOGS:
            if needle in panel:
                fail(f"PSH1: PerspectivePanel.svelte calls {needle}")


def _joueur_sources() -> list[pathlib.Path]:
    if not JOUEUR.is_dir():
        fail(f"{JOUEUR.relative_to(ROOT)} missing")
        return []
    files = sorted(p for p in JOUEUR.rglob("*") if p.suffix in (".js", ".svelte") and p.is_file())
    if not files:
        fail("frontend/src/joueur/ holds no .js or .svelte file")
    return files


def rule_psh2() -> None:
    found = 0
    for path in _joueur_sources():
        text = path.read_text(encoding="utf-8")
        literal_calls = URL_CALL_RE.findall(text)
        for _, url in literal_calls:
            found += 1
            if not url.startswith("/api/joueur/"):
                fail(f"PSH2: {path.name} calls {url!r}, outside /api/joueur/")
    if not found:
        fail("PSH2: no fetch( / call( URL literal found under frontend/src/joueur/")


def _allowed_import(spec: str) -> bool:
    return spec == "svelte" or spec.startswith("svelte/") or (spec.startswith("./") and ".." not in spec)


def rule_psh3() -> None:
    found = 0
    for path in _joueur_sources():
        for groups in IMPORT_RE.findall(path.read_text(encoding="utf-8")):
            spec = next(g for g in groups if g)
            found += 1
            if not _allowed_import(spec):
                fail(f"PSH3: {path.name} imports {spec!r}, outside frontend/src/joueur/")
    if not found:
        fail("PSH3: no import found under frontend/src/joueur/")


def _shell_routes(tree: ast.Module) -> tuple | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_SHELL_ROUTES"
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def rule_psh4() -> None:
    vite = _read(VITE_CONFIG)
    if vite is not None and not re.search(r"input\s*:\s*\{[^}]*jouer\.html", vite, re.S):
        fail("PSH4: vite.config.js does not name jouer.html as an input")
    page = _read(JOUER_HTML)
    if page is not None and 'src="/src/joueur/main.js"' not in page:
        fail("PSH4: frontend/jouer.html does not load /src/joueur/main.js")
    app = _read(APP_PY)
    if app is None:
        return
    tree = ast.parse(app)
    routed = False
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and deco.func.attr == "get" \
                    and deco.args and isinstance(deco.args[0], ast.Constant) and deco.args[0].value == "/jouer":
                if '"jouer.html"' in ast.unparse(node).replace("'", '"'):
                    routed = True
    if not routed:
        fail("PSH4: app.py holds no GET /jouer decorator route reading jouer.html")
    routes = _shell_routes(tree)
    if routes is None:
        fail("PSH4: _SHELL_ROUTES not found in app.py")
    elif "/jouer" in routes:
        fail("PSH4: /jouer is a _SHELL_ROUTES surface")


def main() -> int:
    for rule in (rule_psh1, rule_psh2, rule_psh3, rule_psh4):
        try:
            rule()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule.__name__} raised {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_shell -- the Lore perspective tab is wired; "
          "the player shell calls only /api/joueur and imports nothing of the creator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
