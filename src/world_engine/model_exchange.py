"""One model exchange, captured as it happened (TICKET-0103, BRIEF-0103-B,
decisions B1 + C1, C-03).

A neutral module, like `prompt_load.py`: the consultation pipeline
(`lore_plan.py`, `lore_render.py`) and the writing panel
(`lore_write_draft.py`) both import it, and it imports neither -- nor any
`Session`, model, writer or client. It holds plain strings only, so the
Session-free renderer can fill one (`lore_isolation.py` R10).

A call site that talks to the model appends one `ModelExchange` per `chat`
call to the list its caller handed in: `begin` before the call records the
prompt version, the model and the rendered messages; the raw reply is
assigned as soon as `chat` returns, before any parsing, so a reply that
fails to parse is still kept; `fail` records the error of whoever caught it.
`to_record` is the journal's model-call shape (`writes/lore_usage.py`
`MODEL_CALL_KEYS`, kept equal by `lore_usage.py` U5).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class ModelExchange:
    usage: str
    prompt_version_id: Optional[str] = None
    prompt_version_number: Optional[int] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    user_message: Optional[str] = None
    raw_output: Optional[str] = None
    error: Optional[str] = None

    def to_record(self) -> dict:
        return asdict(self)


def begin(
    exchanges: Optional[list[ModelExchange]], usage: str, spec, system_prompt: str, user_message: str,
) -> Optional[ModelExchange]:
    """Append and return a new exchange carrying `spec`'s prompt version and
    model and the rendered messages; `None` when the caller keeps no list.
    `spec` is a `prompt_load.RenderSpec` (duck-typed: this module imports
    nothing)."""
    if exchanges is None:
        return None
    exchange = ModelExchange(
        usage=usage, prompt_version_id=spec.version_id,
        prompt_version_number=spec.version_number, model=spec.model,
        system_prompt=system_prompt, user_message=user_message,
    )
    exchanges.append(exchange)
    return exchange


def fail(exchanges: Optional[list[ModelExchange]], exc: BaseException) -> None:
    """Record `exc` on the last exchange of `exchanges` that has no error
    yet -- the one the exception interrupted. No-op on an empty list."""
    for exchange in reversed(exchanges or []):
        if exchange.error is None:
            exchange.error = f"{type(exc).__name__}: {exc}"
            return
