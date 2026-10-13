"""What the creator changed in a proposal before approving it: two payloads compared, value by value (TICKET-0115, BRIEF-0115-B; decision H1a of the conditions series' dashboard).

Pure: no database, no model. `diff_payloads(before, after)` walks the
payload stored before the review call and the one approved, and returns one
`PayloadChange` per value that differs -- the rows
`writes/mutation_reviews.py` records in `mutation_review_change`.

- A **path** names the value: keys joined by `.`, a list element in
  brackets -- `title`, `participants[Cible].entity_id`, `steps[2]`,
  `involved_entities["e-1"]`. Its **field** is the same path without what
  the brackets hold (`participants[].entity_id`): what the dashboard groups
  by.
- **Empty is absent**: `None`, `""`, `[]` and `{}` equal a missing key. The
  review card writes every key of its form (`description: null`, a
  participant's `secret: null`); none of that is a change.
- **Never compared**: `IGNORED_KEYS` -- `type_name` (the card's label for
  `type_id`, which is compared) and what an apply writes into a payload
  (`applied_changes`, `created_entity_id`).
- **A list pairs its elements** by `NATURAL_KEYS` (`participants` by role name -- the tick names a role, the card adds its id --,
  `state_changes` by entity and state, `scopes` by kind and target, a type's
  `roles` by name, completion `effects` by type); two elements sharing a key
  are told apart by their order (`[Chasseur#2]`). A list of plain values is a
  set (`involved_entities`, a role's `entity_types`) except `ORDERED_LISTS`
  (`steps`), paired by position from 1; a list of objects with no natural
  key is paired by position too (`[#1]`).
- **Kinds**: `added` (absent before), `removed` (absent after), `changed`.
  `before_value` / `after_value` hold a plain value as JSON text, and None
  for a whole object or list added, removed or replaced by another kind.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

IGNORED_KEYS: frozenset[str] = frozenset({"type_name", "applied_changes", "created_entity_id"})
NATURAL_KEYS: dict[str, tuple[tuple[str, ...], ...]] = {
    "participants": (("role", "role_id"),),
    "state_changes": (("entity_id",), ("attribute",)),
    "scopes": (("scope_type",), ("scope_id",)),
    "roles": (("name",),),
    "effects": (("type",),),
}
ORDERED_LISTS: frozenset[str] = frozenset({"steps"})
_BRACKETS = re.compile(r"\[[^\]]*\]")


@dataclass(frozen=True)
class PayloadChange:
    path: str
    field: str
    kind: str  # added | removed | changed
    before_value: Optional[str] = None
    after_value: Optional[str] = None


def field_of(path: str) -> str:
    """The path without what its brackets hold."""
    return _BRACKETS.sub("[]", path)


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _scalar(value: Any) -> bool:
    return not isinstance(value, (dict, list))


def _text(value: Any) -> Optional[str]:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if _scalar(value) else None


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def _label(value: Any) -> str:
    return str(value).replace("]", ")").replace("[", "(")


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _change(path: str, kind: str, before: Any = None, after: Any = None) -> PayloadChange:
    return PayloadChange(path=path, field=field_of(path), kind=kind,
                         before_value=None if kind == "added" else _text(before),
                         after_value=None if kind == "removed" else _text(after))


def _natural_key(item: dict, parts: tuple[tuple[str, ...], ...]) -> str:
    chosen = []
    for alternatives in parts:
        value = next((item.get(k) for k in alternatives if not _empty(item.get(k))), "")
        chosen.append(_label(value))
    return "|".join(chosen)


def _keyed(items: list, name: str) -> dict[str, Any]:
    """`name`'s elements by their label: a natural key, a position, or a
    plain value."""
    parts = NATURAL_KEYS.get(name)
    if name in ORDERED_LISTS:
        return {f"#{i}" if not _scalar(item) else str(i): item for i, item in enumerate(items, start=1)}
    if all(_scalar(item) for item in items):
        return {json.dumps(item, ensure_ascii=False, sort_keys=True): item for item in items}
    out: dict[str, Any] = {}
    seen: dict[str, int] = {}
    for position, item in enumerate(items, start=1):
        if parts is not None and isinstance(item, dict):
            base = _natural_key(item, parts)
            seen[base] = seen.get(base, 0) + 1
            label = base if seen[base] == 1 else f"{base}#{seen[base]}"
        else:
            label = f"#{position}"
        out[label] = item
    return out


def _walk_object(before: dict, after: dict, path: str, out: list[PayloadChange]) -> None:
    for key in sorted(set(before) | set(after)):
        if key not in IGNORED_KEYS:
            _walk(before.get(key), after.get(key), _join(path, key), key, out)


def _walk(before: Any, after: Any, path: str, name: str, out: list[PayloadChange]) -> None:
    if _empty(before) and _empty(after):
        return
    if _empty(before):
        out.append(_change(path, "added", after=after))
        return
    if _empty(after):
        out.append(_change(path, "removed", before=before))
        return
    if isinstance(before, dict) and isinstance(after, dict):
        _walk_object(before, after, path, out)
        return
    if isinstance(before, list) and isinstance(after, list):
        if all(_scalar(i) for i in before + after) and name not in ORDERED_LISTS:
            old, new = _keyed(before, name), _keyed(after, name)
            for label in sorted(set(old) | set(new)):
                if label not in new:
                    out.append(_change(f"{path}[{_label(label)}]", "removed", before=old[label]))
                elif label not in old:
                    out.append(_change(f"{path}[{_label(label)}]", "added", after=new[label]))
            return
        old, new = _keyed(before, name), _keyed(after, name)
        for label in sorted(set(old) | set(new), key=lambda k: (k not in old, k)):
            _walk(old.get(label), new.get(label), f"{path}[{label}]", name, out)
        return
    if _scalar(before) and _scalar(after):
        if not _same(before, after):
            out.append(_change(path, "changed", before, after))
        return
    out.append(_change(path, "changed", before, after))


def diff_payloads(before: Any, after: Any) -> list[PayloadChange]:
    """Every value that differs between `before` and `after`, in path order
    within each object. A payload that is not an object differs as a whole
    (path `$`)."""
    out: list[PayloadChange] = []
    if isinstance(before, dict) and isinstance(after, dict):
        _walk_object(before, after, "", out)
    elif not (_empty(before) and _empty(after)) and not _same(before, after):
        out.append(_change("$", "changed", before, after))
    return out
