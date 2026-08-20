"""G1 check: the cockpit stylesheet partition (TICKET-0063, BRIEF-0063-a).

Creation's entire visual layer -- buttons, cards, badges, the `:root`
design tokens -- used to live in one ~1050-line <style> block inside
cockpit/index.html, shared by Play/Observation/Creation alike. Once
Creation mounts outside the legacy iframe (BRIEF-0059-l), nothing in that
inline block reaches it. R1 partitions the sheet three ways -- shared.css
(both surviving documents), creation.css (Creation-only, linked by both
while the iframe mount persists) and cockpit/index.html's own remaining
inline <style> (Play + legacy-document-only chrome) -- and makes cascade
order moot rather than reasoned about: if no selector appears in more than
one destination, load order cannot decide a conflict.

Seven rules, each named in its own failure message:

  rule1 (scan is real)         -- vacuous-proof: both sheets exist and are
                                   non-empty, the inline <style> block
                                   parses and is non-empty.
  rule2 (no duplicate selectors) -- every top-level selector across the
                                   three sources is unique; a duplicate
                                   means load order would decide a
                                   conflict, exactly what this partition
                                   exists to make impossible.
  rule3 (tokens moved, not copied) -- no `:root { ... }` block survives in
                                   cockpit/index.html; the design tokens
                                   exist exactly once, in shared.css.
  rule4 (both documents link shared) -- frontend/index.html and
                                   cockpit/index.html each carry the exact
                                   shared.css <link>.
  rule5 (creation link tracks the mount) -- cockpit/index.html links
                                   creation.css IFF LEGACY_MOUNTS declares
                                   `creation`; both directions FAIL. This
                                   is what makes BRIEF-0059-l's single
                                   deleted <link> structurally required,
                                   not remembered.
  rule6 (built copies are fresh) -- static/shared.css and static/creation.css
                                   exist and byte-match their
                                   frontend/public/ sources. No line-ending
                                   normalisation: a byte comparison that
                                   normalises is fail-open, and
                                   .gitattributes already governs EOLs
                                   here.
  rule7 (coverage)               -- disjointness (rule2) proves the three
                                   sheets never overlap; it never proves
                                   Creation actually RECEIVES its visual
                                   layer (TICKET-0064). rule7 closes that
                                   gap. Per applying file F:

                                       STRANDED(F) = APPLIED(F) ∩ INLINE
                                                      − REACHABLE − SCOPED(F)
                                       REACHABLE = base rules in shared.css
                                                   ∪ creation.css ∪ the
                                                   built CSS bundle
                                       SCOPED(F) = base rules in F's own
                                                   <style> block

                                   APPLIED(F) is literal class="..."/
                                   id="..." markup in one frontend/src
                                   file; INLINE is loose (any class/id
                                   name appearing anywhere in an inline
                                   selector, descendant position
                                   included). REACHABLE and SCOPED are
                                   STRICT: a selector counts only when its
                                   whole text is `.N` with optional
                                   pseudo-classes, pseudo-elements or
                                   self-compounds (`.N`, `.N:hover`,
                                   `.N.active`, `.N::before`) -- a
                                   descendant/compound selector like
                                   `.parent .N` is a contextual override
                                   and proves nothing about N's base
                                   styling. SCOPED is per-file and never
                                   unioned across components: Svelte scopes
                                   component <style> blocks, so one
                                   component's own rule for `.N` does not
                                   cover a same-named `.N` applied by a
                                   different component. Loose reachability
                                   was tried and rejected: it let
                                   `.lieux-graph-head .btn-send` in
                                   creation.css mask a genuine, 24-file
                                   stranding of `.btn-send`'s base rule --
                                   the exact fail-open this ticket exists
                                   to close, reproduced inside the fix.
                                   Class names and id names are two
                                   disjoint namespaces throughout -- never
                                   unioned, so a class and an id sharing a
                                   literal name can never cross-trigger.
                                   This is computed, not enumerated: no
                                   baseline, no allow-list, no annotation.
                                   rule7 is directional -- it covers
                                   frontend/src/** against the
                                   Svelte-reachable sheets only. The mirror
                                   direction (the legacy document's own
                                   markup against shared.css plus its
                                   inline block) is unguarded until
                                   TICKET-0060 migrates Observation out of
                                   the legacy document.

No DB, stdlib only, same FAILURES/_report_and_exit/ROOT idiom as
legacy_call.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_PUBLIC = ROOT / "frontend" / "public"
SHARED_SRC = FRONTEND_PUBLIC / "shared.css"
CREATION_SRC = FRONTEND_PUBLIC / "creation.css"
FRONTEND_INDEX = ROOT / "frontend" / "index.html"
COCKPIT_INDEX = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
STATIC_DIR = ROOT / "src" / "world_engine" / "cockpit" / "static"
SHARED_STATIC = STATIC_DIR / "shared.css"
CREATION_STATIC = STATIC_DIR / "creation.css"
REGISTRY_FILE = ROOT / "frontend" / "src" / "legacy" / "registry.js"
FRONTEND_SRC = ROOT / "frontend" / "src"

SHARED_LINK = '<link rel="stylesheet" href="/static/shared.css">'
CREATION_LINK = '<link rel="stylesheet" href="/static/creation.css">'
STYLE_BLOCK_RE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
MOUNTS_CREATION_RE = re.compile(r"^\s*creation:\s*Object\.freeze\(", re.MULTILINE)

# rule7 (coverage) -- see module docstring.
APPLIED_ATTR_RE = re.compile(r'(?<![\w-])(class|id)="([^"]*)"')
EXPR_RE = re.compile(r"\{[^{}]*\}")
TOKEN_RE = re.compile(r"^[A-Za-z_][\w-]*$")
SELECTOR_TOKEN_RE = re.compile(r"[.#][A-Za-z_][\w-]*")
# A strict base rule: `.N`/`#N` plus only pseudo-classes, pseudo-elements
# or self-compound classes -- no combinator, no descendant, no tag prefix.
# TICKET-0060 (BRIEF-0060-e, J1). The self-compound branch used to accept
# a Svelte scope hash: `.spacer.svelte-13t3afu` matched and yielded
# `spacer`, so every component-scoped rule leaked into the GLOBAL
# reachable set that _reachable_names() builds. That function's docstring
# already asserted the opposite -- the code contradicted its own
# documentation, and the direction of the error was fail-open: names were
# granted reachability they never had. Measured on main before this fix,
# the built bundle contributed 11 class names to REACHABLE, all 11 via a
# hashed selector and none legitimately, so the bundle term supplied
# nothing but over-grants. The lookahead is deliberately narrow: it
# refuses Svelte's scope suffix and nothing else. Whether a genuine
# compound like `.a.b` should grant a base rule for `a` at all is a
# separate question with unmeasured blast radius -- not reopened here.
# Defect originates in TICKET-0064's rule7; repaired here because
# BRIEF-0060-c cannot land while it stands.
BASE_RULE_RE = re.compile(
    r"^([.#])([A-Za-z_][\w-]*)"
    r"(?:(?::[\w-]+(?:\([^)]*\))?)|(?:::[\w-]+)|(?:\.(?!svelte-)[\w-]+))*$"
)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: stylesheet_partition — {counts['selectors']} top-level selector(s) "
        f"across shared.css/creation.css/inline, zero duplicates; rule7 scanned "
        f"{counts['files']} frontend/src file(s), {counts['applied_classes']} applied "
        f"class name(s), {counts['applied_ids']} applied id name(s), "
        f"{counts['inline_selectors']} inline selector name(s), zero stranded"
    )
    sys.exit(0)


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _split_top_level(prelude: str, sep: str) -> list[str]:
    """Split on sep at paren/bracket depth 0 only."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in prelude:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _top_level_selectors(css_text: str) -> list[str]:
    """Top-level selectors/at-rule preludes of a stylesheet. Does not
    descend into an at-rule's body (e.g. @keyframes spin { to {...} } is
    one atomic entry, 'to' is never extracted as its own selector) --
    only the selectors this partition actually governs are meaningful
    duplication candidates."""
    text = _strip_comments(css_text)
    selectors: list[str] = []
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        start = i
        while i < n and text[i] != "{":
            i += 1
        if i >= n:
            break
        prelude = text[start:i].strip()
        depth = 0
        j = i
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        i = j + 1
        if not prelude:
            continue
        if prelude.startswith("@"):
            selectors.append(" ".join(prelude.split()))
        else:
            for sel in _split_top_level(prelude, ","):
                sel = " ".join(sel.split())
                if sel:
                    selectors.append(sel)
    return selectors


def _extract_inline_style(html_text: str, source_label: str) -> str | None:
    m = STYLE_BLOCK_RE.search(html_text)
    if not m:
        fail(f"rule1: vacuous scan -- no <style>...</style> block found in {source_label}")
        return None
    body = m.group(1)
    if not body.strip():
        fail(f"rule1: vacuous scan -- <style> block in {source_label} is empty")
        return None
    return body


def _check_rule1_and_collect() -> dict[str, list[str]] | None:
    """rule1 + selector collection for rule2/rule3. Returns
    {source_name: [selectors]} or None if any input is vacuous."""
    sources: dict[str, list[str]] = {}

    if not SHARED_SRC.is_file():
        fail(f"rule1: vacuous scan -- {SHARED_SRC} does not exist")
    else:
        text = SHARED_SRC.read_text(encoding="utf-8")
        if not text.strip():
            fail(f"rule1: vacuous scan -- {SHARED_SRC} is empty")
        else:
            sources["shared.css"] = _top_level_selectors(text)

    if not CREATION_SRC.is_file():
        fail(f"rule1: vacuous scan -- {CREATION_SRC} does not exist")
    else:
        text = CREATION_SRC.read_text(encoding="utf-8")
        if not text.strip():
            fail(f"rule1: vacuous scan -- {CREATION_SRC} is empty")
        else:
            sources["creation.css"] = _top_level_selectors(text)

    if not COCKPIT_INDEX.is_file():
        fail(f"rule1: vacuous scan -- {COCKPIT_INDEX} does not exist")
    else:
        html_text = COCKPIT_INDEX.read_text(encoding="utf-8")
        inline_body = _extract_inline_style(html_text, str(COCKPIT_INDEX))
        if inline_body is not None:
            sources["cockpit/index.html (inline)"] = _top_level_selectors(inline_body)

    if len(sources) != 3:
        return None
    return sources


def _check_rule2(sources: dict[str, list[str]]) -> int:
    """No selector appears in more than one source. Returns total selector count."""
    owner: dict[str, str] = {}
    total = 0
    for source_name, selectors in sources.items():
        for sel in selectors:
            total += 1
            if sel in owner and owner[sel] != source_name:
                fail(
                    f"rule2: selector {sel!r} appears in both {owner[sel]} and "
                    f"{source_name} -- exactly one destination is allowed"
                )
            else:
                owner[sel] = source_name
    return total


def _check_rule3(sources: dict[str, list[str]]) -> None:
    inline = sources.get("cockpit/index.html (inline)")
    if inline is None:
        return
    if ":root" in inline:
        fail(
            "rule3: cockpit/index.html's inline <style> still declares a :root block -- "
            "design tokens must exist exactly once, in shared.css"
        )


def _check_rule4() -> None:
    for path, label in ((FRONTEND_INDEX, "frontend/index.html"), (COCKPIT_INDEX, "cockpit/index.html")):
        if not path.is_file():
            fail(f"rule4: {path} does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        if SHARED_LINK not in text:
            fail(f"rule4: {label} is missing the exact shared.css <link> ({SHARED_LINK!r})")


def _check_rule5() -> None:
    if not REGISTRY_FILE.is_file():
        fail(f"rule5: {REGISTRY_FILE} does not exist")
        return
    registry_text = REGISTRY_FILE.read_text(encoding="utf-8")
    mount_declared = bool(MOUNTS_CREATION_RE.search(registry_text))

    if not COCKPIT_INDEX.is_file():
        fail(f"rule5: {COCKPIT_INDEX} does not exist")
        return
    cockpit_text = COCKPIT_INDEX.read_text(encoding="utf-8")
    link_present = CREATION_LINK in cockpit_text

    if link_present and not mount_declared:
        fail(
            "rule5: cockpit/index.html links creation.css but LEGACY_MOUNTS no longer "
            "declares 'creation' -- the link outlived the mount it was tied to"
        )
    elif mount_declared and not link_present:
        fail(
            "rule5: LEGACY_MOUNTS still declares 'creation' but cockpit/index.html is "
            "missing the creation.css <link> -- Creation would lose its styling while "
            "still rendering inside the legacy iframe"
        )


def _check_rule6() -> None:
    for src, built, label in (
        (SHARED_SRC, SHARED_STATIC, "shared.css"),
        (CREATION_SRC, CREATION_STATIC, "creation.css"),
    ):
        if not src.is_file():
            continue  # already FAILed by rule1
        if not built.is_file():
            fail(f"rule6: {built} does not exist -- run \"npm run build\" in frontend/")
            continue
        if src.read_bytes() != built.read_bytes():
            fail(
                f"rule6: {built} does not byte-match {src} -- run \"npm run build\" in "
                "frontend/ and commit the output"
            )


def _tokenize_attr_value(value: str) -> list[str]:
    """Applies BRIEF-0064-a Sec2.2's adjacency rule to a literal
    class="..."/id="..." attribute value: expressions {...} are removed,
    the surviving literal runs are split on whitespace, and a token fused
    (no intervening whitespace) to a removed expression is discarded."""
    expr_spans = [(m.start(), m.end()) for m in EXPR_RE.finditer(value)]
    runs: list[str] = []
    cursor = 0
    for start, end in expr_spans:
        runs.append(value[cursor:start])
        cursor = end
    runs.append(value[cursor:])

    tokens: list[str] = []
    n_runs = len(runs)
    for i, run in enumerate(runs):
        toks = run.split()
        if not toks:
            continue
        is_first_run = i == 0
        is_last_run = i == n_runs - 1
        if not is_first_run and not run[0].isspace():
            toks = toks[1:]
        if toks and not is_last_run and not run[-1].isspace():
            toks = toks[:-1]
        tokens.extend(toks)
    return [t for t in tokens if TOKEN_RE.match(t)]


def _scan_frontend_src() -> tuple[dict[str, list[str]], dict[str, list[str]], int]:
    """Applied class/id names under frontend/src/** (BRIEF-0064-a Sec2.2).
    Returns (applied_classes, applied_ids, files_scanned), each dict
    mapping a name to the repo-relative files that apply it."""
    applied_classes: dict[str, list[str]] = {}
    applied_ids: dict[str, list[str]] = {}
    if not FRONTEND_SRC.is_dir():
        return applied_classes, applied_ids, 0
    files = sorted(
        p for p in FRONTEND_SRC.rglob("*")
        if p.is_file() and p.suffix in (".svelte", ".js")
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        for attr_name, value in APPLIED_ATTR_RE.findall(text):
            target = applied_classes if attr_name == "class" else applied_ids
            for name in _tokenize_attr_value(value):
                files_for_name = target.setdefault(name, [])
                if rel not in files_for_name:  # dedupe: distinct files, not occurrences
                    files_for_name.append(rel)
    return applied_classes, applied_ids, len(files)


def _inline_class_and_id_names(sources: dict[str, list[str]]) -> tuple[set[str], set[str]]:
    """Every class/id name appearing anywhere in a selector of
    cockpit/index.html's inline <style> block (BRIEF-0064-a Sec2.3),
    including in descendant and compound selectors. Loose by design --
    this is the "reachable only through the inline block" candidate set,
    narrowed to genuine strandings by REACHABLE/SCOPED below."""
    classes: set[str] = set()
    ids: set[str] = set()
    for sel in sources.get("cockpit/index.html (inline)", []):
        for m in SELECTOR_TOKEN_RE.finditer(sel):
            (classes if m.group(0)[0] == "." else ids).add(m.group(0)[1:])
    return classes, ids


def _base_rule_names(selectors: list[str]) -> tuple[set[str], set[str]]:
    """Strict base-rule names (Nia's Decision 1 correction, D-0064-2): a
    selector counts only when its whole text is `.N`/`#N` with optional
    trailing pseudo-classes, pseudo-elements or self-compound classes --
    `.N`, `.N:hover`, `.N.active`, `.N::before`. A descendant/compound
    selector like `.parent .N` is a contextual override, not a base rule,
    and contributes nothing."""
    classes: set[str] = set()
    ids: set[str] = set()
    for sel in selectors:
        m = BASE_RULE_RE.match(sel.strip())
        if not m:
            continue
        (classes if m.group(1) == "." else ids).add(m.group(2))
    return classes, ids


def _reachable_names() -> tuple[set[str], set[str]]:
    """REACHABLE: strict base rules in shared.css ∪ creation.css ∪ the
    built CSS bundle (global, unioned -- these are genuinely reachable
    from anywhere). A Svelte-scoped compiled rule always carries its
    per-component hash suffix (e.g. `.mode-tab.svelte-13t3afu`), which
    fails the strict base-rule match, so scoped component output never
    leaks into this global set -- only true `:global(...)` rules can."""
    classes: set[str] = set()
    ids: set[str] = set()
    paths = [SHARED_SRC, CREATION_SRC]
    if STATIC_DIR.is_dir():
        paths.extend(sorted((STATIC_DIR / "assets").glob("*.css")))
    for path in paths:
        if not path.is_file():
            continue
        c, i = _base_rule_names(_top_level_selectors(path.read_text(encoding="utf-8")))
        classes |= c
        ids |= i
    return classes, ids


def _scoped_names_for_file(path: Path) -> tuple[set[str], set[str]]:
    """SCOPED(F): strict base rules in F's own <style> block. Per-file,
    never unioned -- Svelte scopes component styles, so one component's
    rule for `.N` does not cover a same-named `.N` applied elsewhere."""
    if path.suffix != ".svelte" or not path.is_file():
        return set(), set()
    m = STYLE_BLOCK_RE.search(path.read_text(encoding="utf-8"))
    if not m:
        return set(), set()
    return _base_rule_names(_top_level_selectors(m.group(1)))


def _stranded_names_by_kind(
    applied: dict[str, list[str]], inline: set[str], reachable: set[str], kind: str
) -> dict[str, list[str]]:
    """Per BRIEF-0064-a's corrected rule7: for each candidate name (applied
    under frontend/src, present in the inline block, not globally
    REACHABLE), keep only the applying files not covered by their own
    SCOPED(F) -- STRANDED(F) = APPLIED(F) ∩ INLINE − REACHABLE − SCOPED(F).
    `kind` selects the class or id half of SCOPED(F)'s namespace pair."""
    scoped_index = 0 if kind == "class" else 1
    stranded: dict[str, list[str]] = {}
    for name in sorted((set(applied) & inline) - reachable):
        files = [
            f for f in applied[name]
            if name not in _scoped_names_for_file(ROOT / f)[scoped_index]
        ]
        if files:
            stranded[name] = files
    return stranded


def _check_rule7(sources: dict[str, list[str]]) -> dict[str, int] | None:
    """Coverage (corrected per Nia's Decision 1, D-0064-2): STRANDED(F) =
    APPLIED(F) ∩ INLINE − REACHABLE − SCOPED(F), computed separately for
    the class namespace and the id namespace (F2 -- never unioned). Five
    independent vacuity guards -- none may inherit its liveness from
    rule1's ordering."""
    if not FRONTEND_SRC.is_dir():
        fail(f"rule7: vacuous scan -- {FRONTEND_SRC} is not a directory")
        return None
    applied_classes, applied_ids, n_files = _scan_frontend_src()
    if n_files == 0:
        fail(f"rule7: vacuous scan -- zero .svelte/.js files found under {FRONTEND_SRC}")
        return None
    if not applied_classes:
        fail("rule7: vacuous scan -- zero applied class names extracted from frontend/src")
        return None
    if not applied_ids:
        fail("rule7: vacuous scan -- zero applied id names extracted from frontend/src")
        return None

    inline_classes, inline_ids = _inline_class_and_id_names(sources)
    if not inline_classes and not inline_ids:
        fail(
            "rule7: vacuous scan -- zero selectors parsed from cockpit/index.html's "
            "inline <style> block"
        )
        return None

    reachable_classes, reachable_ids = _reachable_names()
    stranded_classes = _stranded_names_by_kind(applied_classes, inline_classes, reachable_classes, kind="class")
    stranded_ids = _stranded_names_by_kind(applied_ids, inline_ids, reachable_ids, kind="id")

    for name, files in stranded_classes.items():
        cited = ", ".join(files[:3])
        fail(
            f"rule7: class {name!r} is stranded -- applied under frontend/src ({cited}) "
            "but reachable only via cockpit/index.html's inline <style>"
        )
    for name, files in stranded_ids.items():
        cited = ", ".join(files[:3])
        fail(
            f"rule7: id {name!r} is stranded -- applied under frontend/src ({cited}) "
            "but reachable only via cockpit/index.html's inline <style>"
        )

    return {
        "files": n_files,
        "applied_classes": len(applied_classes),
        "applied_ids": len(applied_ids),
        "inline_selectors": len(inline_classes) + len(inline_ids),
    }


def main() -> None:
    sources = _check_rule1_and_collect()
    if sources is None:
        _report_and_exit()
        return

    total = _check_rule2(sources)
    _check_rule3(sources)
    _check_rule4()
    _check_rule5()
    _check_rule6()
    rule7_counts = _check_rule7(sources)

    counts = {"selectors": total}
    if rule7_counts:
        counts.update(rule7_counts)
    _report_and_exit(counts)


if __name__ == "__main__":
    main()
