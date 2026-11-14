"""G1 check for TICKET-0130 -- the home page at /, the browser opener, the preview's database.

HP1 -- static, AST of `src/world_engine/cockpit/app.py`: a module-level
   function decorated `@app.get("/", response_class=HTMLResponse)` whose
   source holds `"accueil.html"`; `"/"` is not in `_SHELL_ROUTES`; `"/play"`
   is (A2-a).
HP2 -- static, frontend: `frontend/vite.config.js` names `accueil.html`
   inside `input`; `frontend/accueil.html` holds `href="/play"`,
   `href="/jouer"`, `Créatrice`, `Joueur`, `/static/shared.css`, and none of
   `<script`, `fetch(` (H1); the built
   `src/world_engine/cockpit/static/accueil.html` exists and holds both
   hrefs; no file under `frontend/src/joueur/` holds `href="/"`,
   `href="/play"` or `"/play"` (B1), at least one file scanned.
HP3 -- live: through `TestClient(app, base_url="http://127.0.0.1")` on a
   fresh temp-file database, `GET /` is 200, holds `href="/jouer"` and
   `href="/play"`, and its `cache-control` contains `no-cache`; `GET /play`
   is 200, holds `<div id="app">` and not `href="/jouer"`; `GET /jouer` is
   200 and holds `World Engine — Joueur`.
HP4 -- live, `world_engine.cockpit.browser_open` imported alone (O1): with
   a socket listening on 127.0.0.1, `open_when_ready` returns True and a
   recording opener got exactly `[url]`; with a port bound then closed
   (nothing listening) and `timeout=1.0`, it returns False and the opener
   got nothing. AST of `scripts/cockpit.py`: an `add_argument("--ouvrir",
   ...)` call exists; every call to `start_opener` sits inside an `if` whose
   test names `ouvrir`; at least one such call.
HP5 -- static: `.claude/launch.json` parses as JSON; the `cockpit`
   configuration's `-c` program holds `os.environ['WORLD_ENGINE_ENV'] =
   'test'` at an index before `from world_engine.cockpit.app import app`,
   and does not hold `prod` (P1).

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A missing file, or a rule that
collected nothing, is a FAILURE.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import socket
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_PY = ROOT / "src" / "world_engine" / "cockpit" / "app.py"
VITE_CONFIG = ROOT / "frontend" / "vite.config.js"
ACCUEIL_SRC = ROOT / "frontend" / "accueil.html"
ACCUEIL_BUILT = ROOT / "src" / "world_engine" / "cockpit" / "static" / "accueil.html"
JOUEUR = ROOT / "frontend" / "src" / "joueur"
COCKPIT_PY = ROOT / "scripts" / "cockpit.py"
LAUNCH_JSON = ROOT / ".claude" / "launch.json"

HOME_TEXTS = ('href="/play"', 'href="/jouer"', "Créatrice", "Joueur", "/static/shared.css")
HOME_FORBIDDEN = ("<script", "fetch(")
JOUEUR_FORBIDDEN = ('href="/"', 'href="/play"', '"/play"')
ENV_TEST = "os.environ['WORLD_ENGINE_ENV'] = 'test'"
APP_IMPORT = "from world_engine.cockpit.app import app"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: pathlib.Path, rule: str) -> str | None:
    if not path.is_file():
        fail(f"{rule}: missing file {path.relative_to(ROOT)}")
        return None
    return path.read_text(encoding="utf-8")


def _is_home_decorator(dec: ast.expr) -> bool:
    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
        return False
    if not (isinstance(dec.func.value, ast.Name) and dec.func.value.id == "app"
            and dec.func.attr == "get"):
        return False
    if not (dec.args and isinstance(dec.args[0], ast.Constant) and dec.args[0].value == "/"):
        return False
    return any(kw.arg == "response_class" and isinstance(kw.value, ast.Name)
               and kw.value.id == "HTMLResponse" for kw in dec.keywords)


def rule_hp1() -> None:
    src = _read(APP_PY, "HP1")
    if src is None:
        return
    tree = ast.parse(src)
    homes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and any(_is_home_decorator(d) for d in n.decorator_list)]
    if not homes:
        fail('HP1: no module-level @app.get("/", response_class=HTMLResponse) function')
    elif not any('"accueil.html"' in (ast.get_source_segment(src, n) or "") for n in homes):
        fail('HP1: the "/" route does not read "accueil.html"')
    routes = None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "_SHELL_ROUTES"):
            routes = ast.literal_eval(node.value)
    if routes is None:
        fail("HP1: _SHELL_ROUTES not found")
        return
    if "/" in routes:
        fail('HP1: "/" is still in _SHELL_ROUTES')
    if "/play" not in routes:
        fail('HP1: "/play" is not in _SHELL_ROUTES')


def rule_hp2() -> None:
    vite = _read(VITE_CONFIG, "HP2")
    if vite is not None:
        start = vite.find("input:")
        end = vite.find("}", start) if start >= 0 else -1
        if start < 0 or end < 0 or "accueil.html" not in vite[start:end]:
            fail("HP2: vite.config.js does not name accueil.html inside input")
    home = _read(ACCUEIL_SRC, "HP2")
    if home is not None:
        for text in HOME_TEXTS:
            if text not in home:
                fail(f"HP2: frontend/accueil.html lacks {text!r}")
        for text in HOME_FORBIDDEN:
            if text in home:
                fail(f"HP2: frontend/accueil.html holds {text!r}")
    built = _read(ACCUEIL_BUILT, "HP2")
    if built is not None:
        for text in ('href="/play"', 'href="/jouer"'):
            if text not in built:
                fail(f"HP2: built static/accueil.html lacks {text!r}")
    files = [p for p in JOUEUR.rglob("*") if p.is_file()] if JOUEUR.is_dir() else []
    if not files:
        fail("HP2: no file scanned under frontend/src/joueur")
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in JOUEUR_FORBIDDEN:
            if needle in text:
                fail(f"HP2: {path.relative_to(ROOT)} holds {needle!r} (B1)")


def rule_hp3() -> None:
    from fastapi.testclient import TestClient
    from world_engine.cockpit.app import app

    client = TestClient(app, base_url="http://127.0.0.1")
    home = client.get("/")
    if home.status_code != 200:
        fail(f"HP3: GET / answered {home.status_code}")
    else:
        for text in ('href="/jouer"', 'href="/play"'):
            if text not in home.text:
                fail(f"HP3: GET / lacks {text!r}")
        if "no-cache" not in home.headers.get("cache-control", ""):
            fail("HP3: GET / has no `no-cache` cache-control")
    shell = client.get("/play")
    if shell.status_code != 200:
        fail(f"HP3: GET /play answered {shell.status_code}")
    else:
        if '<div id="app">' not in shell.text:
            fail('HP3: GET /play lacks <div id="app">')
        if 'href="/jouer"' in shell.text:
            fail('HP3: GET /play holds href="/jouer"')
    player = client.get("/jouer")
    if player.status_code != 200:
        fail(f"HP3: GET /jouer answered {player.status_code}")
    elif "World Engine — Joueur" not in player.text:
        fail("HP3: GET /jouer lacks « World Engine — Joueur »")


def _names_ouvrir(test: ast.expr) -> bool:
    return any((isinstance(n, ast.Name) and n.id == "ouvrir")
               or (isinstance(n, ast.Attribute) and n.attr == "ouvrir")
               for n in ast.walk(test))


def rule_hp4() -> None:
    from world_engine.cockpit import browser_open

    url = "http://127.0.0.1/"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    got: list[str] = []
    try:
        ok = browser_open.open_when_ready(url, "127.0.0.1", port, timeout=5.0, opener=got.append)
    finally:
        listener.close()
    if ok is not True or got != [url]:
        fail(f"HP4: listening port -> returned {ok!r}, opener got {got!r} (want True, [url])")

    closed = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    closed.bind(("127.0.0.1", 0))
    dead_port = closed.getsockname()[1]
    closed.close()
    got = []
    ok = browser_open.open_when_ready(url, "127.0.0.1", dead_port, timeout=1.0, opener=got.append)
    if ok is not False or got:
        fail(f"HP4: dead port -> returned {ok!r}, opener got {got!r} (want False, [])")

    src = _read(COCKPIT_PY, "HP4")
    if src is None:
        return
    tree = ast.parse(src)
    has_flag = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_argument" and n.args
        and isinstance(n.args[0], ast.Constant) and n.args[0].value == "--ouvrir"
        for n in ast.walk(tree)
    )
    if not has_flag:
        fail('HP4: scripts/cockpit.py has no add_argument("--ouvrir", ...)')
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _names_ouvrir(node.test):
            for stmt in node.body:
                guarded.update(id(n) for n in ast.walk(stmt))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and ((isinstance(n.func, ast.Name) and n.func.id == "start_opener")
                  or (isinstance(n.func, ast.Attribute) and n.func.attr == "start_opener"))]
    if not calls:
        fail("HP4: scripts/cockpit.py never calls start_opener")
    for call in calls:
        if id(call) not in guarded:
            fail(f"HP4: start_opener call at line {call.lineno} is not under an `ouvrir` test")


def rule_hp5() -> None:
    raw = _read(LAUNCH_JSON, "HP5")
    if raw is None:
        return
    config = json.loads(raw)
    cockpit = [c for c in config.get("configurations", []) if c.get("name") == "cockpit"]
    if len(cockpit) != 1:
        fail(f"HP5: {len(cockpit)} `cockpit` configuration(s), want 1")
        return
    args = cockpit[0].get("runtimeArgs", [])
    if "-c" not in args or args.index("-c") + 1 >= len(args):
        fail("HP5: the cockpit configuration has no `-c` program")
        return
    program = args[args.index("-c") + 1]
    env_at, import_at = program.find(ENV_TEST), program.find(APP_IMPORT)
    if env_at < 0:
        fail(f"HP5: the -c program lacks {ENV_TEST!r}")
    if import_at < 0:
        fail(f"HP5: the -c program lacks {APP_IMPORT!r}")
    if env_at >= 0 and import_at >= 0 and env_at > import_at:
        fail("HP5: WORLD_ENGINE_ENV is set after the app import")
    if "prod" in program:
        fail("HP5: the -c program names `prod`")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="home_page_")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{tmp}/x.db"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    for rule in (rule_hp1, rule_hp2, rule_hp3, rule_hp4, rule_hp5):
        try:
            rule()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule.__name__} raised {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: home_page -- / serves the home page with two doors and no script; "
          "the shell stays at /play; --ouvrir opens once the port answers; "
          "the preview pins the test database")
    return 0


if __name__ == "__main__":
    sys.exit(main())
