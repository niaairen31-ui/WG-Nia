"""Day-chain prompt coverage guard (TICKET-0076, BRIEF-0076-a).

`DAY_CHAIN_USAGES` is derived from `PROMPT_REGISTRY`, never restated as a
literal list: it is every usage whose `PromptSpec.call_sites` names a
`src/world_engine/day_*.py` module, minus the one usage this chain lets
degrade rather than refuse.

That one exception is `day_feasibility`: its missing-template branch
(`day_feasibility.py:188`) returns `_unavailable(...)` instead of raising —
BRIEF-0075-g's designed degradation (decision Y1), the veto is optional and
its absence is tolerated. Every other day-chain usage's missing-template
branch raises, so requiring `day_feasibility` here would turn a tolerated
absence into a hard refusal it was never meant to have.

Coverage means an active `prompt_template` AND at least one `prompt_version`
row for it: `prompt_store.current_prompt` raises `RuntimeError` on a
versionless head, outside the `/api/day/{batch}/plan` route's 502 wrapper —
an active head with zero versions is not actually usable. Version depth is
checked THROUGH `prompt_store.current_prompt` (the sole `prompt_version`
read accessor, TICKET-0011) rather than by querying `PromptVersion`
directly — `tooling/verify/checks/prompt_version.py` allowlists that class
to a fixed set of files this module is not on, and `current_prompt` already
does exactly the check this module needs (a template has at least one
version, or it raises).
"""

from __future__ import annotations

import re
from typing import Sequence

from sqlmodel import Session, select

from .models import PromptTemplate
from .prompt_registry import PROMPT_REGISTRY
from .prompt_store import current_prompt

_DAY_MODULE = re.compile(r"^src/world_engine/day_[a-z_]+\.py$")

# day_feasibility.py:188 returns _unavailable(...) rather than raising.
DEGRADING_USAGES: frozenset[str] = frozenset({"day_feasibility"})

DAY_CHAIN_USAGES: tuple[str, ...] = tuple(
    sorted(
        usage
        for usage, spec in PROMPT_REGISTRY.items()
        if any(_DAY_MODULE.match(site.split(":", 1)[0]) for site in spec.call_sites)
        and usage not in DEGRADING_USAGES
    )
)


def missing_usages(usages: Sequence[str], db: Session) -> list[str]:
    """Usages lacking an active `prompt_template` with >= 1 `prompt_version` row.

    One query (active templates) plus one `current_prompt` call per active
    template, joined in Python. A usage absent from the DB entirely comes
    back as missing — never assumed present.
    """
    active_templates = db.exec(
        select(PromptTemplate).where(PromptTemplate.is_active == True)  # noqa: E712
    ).all()
    covered_usages: set[str] = set()
    for template in active_templates:
        try:
            current_prompt(db, template)
        except RuntimeError:
            continue
        covered_usages.add(template.usage)
    return [usage for usage in usages if usage not in covered_usages]
