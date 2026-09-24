"""Token posing on new canon prose (TICKET-0091, BRIEF-0091-J, contract
C-14, decision F1).

`tokenize` turns every name the server can resolve, in a text about to be
written as `fact`/`knowledge` content, into an identity token
(`prose_render.entity_token`). The index is `name_index.surfaces` under the
caller's scope: every active entity `name` of the world plus every
`appellation` fact content (rendered) that has a scope and is not
creator-only (TICKET-0092, N17a) — or names alone, for an appellation's own
text (N15b). Each surface is normalized with
`lore_resolve.normalize_surface` — both sides of every comparison, never
one. Longest match first, whole words only; text already inside a token is
skipped (a token is a barrier: no match spans it).

A surface naming exactly one entity becomes a token; two or more stay plain
and are reported `ambigu` — this module never picks. A generator `mentions`
entry the index did not already cover, and whose surface occurs in the text,
is resolved with `lore_resolve.resolve_named`: one candidate -> its first
occurrence is tokenized; zero -> `inconnu`; two or more -> `ambigu`. A
mention that does not occur in the text is not about it and is ignored.

No model call, no write: the caller records `unresolved` through
`writes/mentions.py::record_unresolved`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from .lore_resolve import normalize_surface, resolve_named
from .models import Entity
from .name_index import PROSE, NameScope, surfaces
from .prose_render import TOKEN_RE, entity_token

_WORD_RE = re.compile(r"[^\W_]+(?:-[^\W_]+)*")
_GAP_RE = re.compile(r"[\s'’]*")
# Mirror of `lore_resolve._CATEGORY_ENTITY_TYPE`, keyed by entity type.
_CATEGORY_OF_TYPE = {"location": "place", "character": "person", "faction": "faction"}


@dataclass(frozen=True)
class Unresolved:
    surface: str
    reason: str            # "ambigu" | "inconnu"
    category: Optional[str]   # "place"|"person"|"faction" when known


@dataclass(frozen=True)
class Tokenized:
    text: str
    unresolved: tuple[Unresolved, ...]


@dataclass
class _Entry:
    ids: set
    full: set             # folded word tuples of the unstripped surfaces


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    key: tuple
    entity_id: Optional[str]


def _fold(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _key_words(surface: str) -> tuple:
    return tuple(w for part in normalize_surface(surface).split() for w in _WORD_RE.findall(part))


def _full_words(surface: str) -> tuple:
    return tuple(_fold(w) for w in _WORD_RE.findall(surface))


def _build_index(db: Session, world_id: str, scope: NameScope) -> tuple[dict, dict]:
    """(index key -> _Entry, entity id -> (name, type)) for the world, from
    the name surfaces `scope` admits (`name_index.surfaces`)."""
    found = surfaces(db, world_id, scope)
    info = {s.entity_id: (s.entity_name, s.entity_type) for s in found if s.source == "name"}
    index: dict = {}
    for s in found:
        key = _key_words(s.text)
        if not key:
            continue
        entry = index.setdefault(key, _Entry(set(), set()))
        entry.ids.add(s.entity_id)
        entry.full.add(_full_words(s.text))
    return index, info


def _words(text: str) -> list[list[tuple]]:
    """Word runs of `text` outside tokens: [(start, end, folded)] per run."""
    runs, cursor = [], 0
    bounds = [m.span() for m in TOKEN_RE.finditer(text)] + [(len(text), len(text))]
    for token_start, token_end in bounds:
        segment = text[cursor:token_start]
        runs.append([(cursor + m.start(), cursor + m.end(), _fold(m.group()))
                     for m in _WORD_RE.finditer(segment)])
        cursor = token_end
    return runs


def _joined(text: str, run: list, i: int, length: int) -> Optional[tuple]:
    """The folded words `run[i:i+length]` if only spaces/apostrophes separate them."""
    for j in range(i, i + length - 1):
        if not _GAP_RE.fullmatch(text[run[j][1]:run[j + 1][0]]):
            return None
    return tuple(w for _, _, w in run[i:i + length])


def _index_spans(text: str, runs: list, index: dict) -> list[_Span]:
    longest = max((len(key) for key in index), default=0)
    spans: list[_Span] = []
    for run in runs:
        i = 0
        while i < len(run):
            span = None
            for length in range(min(longest, len(run) - i), 0, -1):
                key = _joined(text, run, i, length)
                if key in index:
                    entry = index[key]
                    start = _article_start(text, run, i, length, entry, spans)
                    only = next(iter(entry.ids)) if len(entry.ids) == 1 else None
                    span = _Span(start, run[i + length - 1][1], key, only)
                    break
            if span is None:
                i += 1
                continue
            spans.append(span)
            i += length
    return spans


def _article_start(text: str, run: list, i: int, length: int, entry: _Entry, spans: list) -> int:
    """Extend a match back over the leading article the name itself carries
    ("Le Dernier Verre"), never over a previous match."""
    floor = spans[-1].end if spans else -1
    for full in entry.full:
        extra = len(full) - length
        if extra > 0 and i - extra >= 0 and run[i - extra][0] >= floor:
            if _joined(text, run, i - extra, len(full)) == full:
                return run[i - extra][0]
    return run[i][0]


def _find(text: str, runs: list, key: tuple, taken: list[_Span]) -> Optional[tuple[int, int]]:
    for run in runs:
        for i in range(len(run) - len(key) + 1):
            if _joined(text, run, i, len(key)) != key:
                continue
            start, end = run[i][0], run[i + len(key) - 1][1]
            if all(end <= s.start or start >= s.end for s in taken):
                return start, end
    return None


def _category(ids, info: dict) -> Optional[str]:
    categories = {_CATEGORY_OF_TYPE.get(info[i][1]) for i in ids if i in info}
    return categories.pop() if len(categories) == 1 else None


def _mention_spans(db, world_id, text, runs, mentions, spans, info) -> list[Unresolved]:
    unresolved = []
    for mention in mentions or []:
        name = mention.get("name") if isinstance(mention, dict) else None
        category = mention.get("category") if isinstance(mention, dict) else None
        key = _key_words(name) if isinstance(name, str) else ()
        if not key or category not in _CATEGORY_OF_TYPE.values() or any(s.key == key for s in spans):
            continue
        found = _find(text, runs, key, spans)
        if found is None:
            continue
        surface = text[found[0]:found[1]]
        resolution = resolve_named(name, category, world_id, db)
        if resolution.verdict == "matched":
            spans.append(_Span(found[0], found[1], key, resolution.entity_id))
            info.setdefault(resolution.entity_id, (db.get(Entity, resolution.entity_id).name, None))
        else:
            reason = "ambigu" if resolution.verdict == "ambiguous" else "inconnu"
            unresolved.append(Unresolved(surface, reason, category))
    return unresolved


def tokenize(
    db: Session, *, world_id: str, text: str, mentions: Optional[list] = None,
    scope: NameScope = PROSE,
) -> Tokenized:
    """Pose identity tokens on `text` (see module docstring). `scope` is
    `prose` (the default) or `names_only` (an appellation's own text, its
    owner excluded — N15b); any other regime raises `ValueError`."""
    if scope.regime not in ("prose", "names_only"):
        raise ValueError(f"tokenize takes the prose or names_only regime, not {scope.regime!r}")
    if not text:
        return Tokenized(text, ())
    index, info = _build_index(db, world_id, scope)
    runs = _words(text)
    spans = _index_spans(text, runs, index)
    unresolved = [
        Unresolved(text[s.start:s.end], "ambigu", _category(index[s.key].ids, info))
        for s in spans if s.entity_id is None
    ]
    unresolved += _mention_spans(db, world_id, text, runs, mentions, spans, info)
    out = text
    for span in sorted((s for s in spans if s.entity_id), key=lambda s: s.start, reverse=True):
        out = out[:span.start] + entity_token(span.entity_id, info[span.entity_id][0]) + out[span.end:]
    seen, unique = set(), []
    for item in unresolved:
        mark = (_fold(item.surface), item.reason, item.category)
        if mark not in seen:
            seen.add(mark)
            unique.append(item)
    return Tokenized(out, tuple(unique))
