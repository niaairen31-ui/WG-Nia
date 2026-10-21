"""`prompt_version` read accessor (G1) — TICKET-0011.

The ONLY read path for `prompt_version`. Every prompt-text consumer (loaders,
assemblers, previews, reader API) fetches the head (`PromptTemplate`, via its
existing loader) and then calls `current_prompt(db, template)` once, next to
that load, to get the text — mirroring the `effective_model` pattern.

Pure reads only: this module never writes. The sole write path is
`writes.write_prompt_version`. `premised_prompt` (TICKET-0124) returns the
same text with `{world_premise}` filled, as plain values -- never the row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .models import PromptTemplate, PromptVersion


@dataclass(frozen=True)
class PremisedPrompt:
    """The current version's text with the world premise filled -- plain
    values, never the append-only row (INV-48)."""
    id: str
    version_number: int
    system_prompt: str
    user_template: str


def current_prompt(db: Session, template: PromptTemplate) -> PromptVersion:
    """Return the highest-`version_number` row for `template`.

    Raises RuntimeError on a versionless head — structurally impossible
    post-migration (migration post-check + S2 + append-only): a head with
    zero versions must fail loud, never fall back to blank text.
    """
    version = db.exec(
        select(PromptVersion)
        .where(PromptVersion.prompt_template_id == template.id)
        .order_by(PromptVersion.version_number.desc())
    ).first()
    if version is None:
        raise RuntimeError(
            f"prompt_template {template.id!r} ({template.usage!r}) has no "
            "prompt_version rows — run the vX.YY migration."
        )
    return version


def premised_prompt(
    db: Session, template: PromptTemplate, *, entity_type: Optional[str] = None,
) -> PremisedPrompt:
    """`current_prompt`'s text with `{world_premise}` filled in the regime of
    `template.usage` (`world_premise.fill`). Same RuntimeError on a versionless head."""
    # lazy: `world_premise` imports `attributes` and the registry;
    # `prompt_store` is imported by both sides
    from .world_premise import fill

    version = current_prompt(db, template)
    return PremisedPrompt(
        id=version.id,
        version_number=version.version_number,
        system_prompt=fill(version.system_prompt, db, template.usage, entity_type=entity_type),
        user_template=fill(version.user_template, db, template.usage, entity_type=entity_type),
    )


def get_version(db: Session, template_id: str, version_number: int) -> PromptVersion | None:
    """Return one specific version row, or None if it doesn't exist."""
    return db.exec(
        select(PromptVersion).where(
            PromptVersion.prompt_template_id == template_id,
            PromptVersion.version_number == version_number,
        )
    ).first()


def list_versions(db: Session, template_id: str) -> list[PromptVersion]:
    """Every version row for `template_id`, newest first."""
    return list(
        db.exec(
            select(PromptVersion)
            .where(PromptVersion.prompt_template_id == template_id)
            .order_by(PromptVersion.version_number.desc())
        ).all()
    )


__all__ = ["PremisedPrompt", "current_prompt", "get_version", "list_versions", "premised_prompt"]
