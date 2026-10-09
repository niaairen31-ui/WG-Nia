"""One templated JSON call to the model, shared by the creator's authoring
tools (TICKET-0112, BRIEF-0112-A -- extracted verbatim from
`lore_write_draft._call`, which now delegates here).

`call_json` loads a usage's prompt through `prompt_load.load`, fills the
user template's `{name}` variables, records the exchange when the caller
keeps a list (`model_exchange.begin`; the raw reply is kept before parsing,
so a reply that does not parse is still recorded), calls the model and
parses one JSON object (`llm_parse.extract_object`).

The model client is a parameter: each caller passes the `chat` it imported,
so a check that replaces `<caller module>.chat` still reaches the call
(`lore_write.py` D1, `lore_usage.py` U6, `condition_interpreter.py`). This
module imports no client, writes nothing and commits nothing.
`OllamaError` and `LlmParseError` propagate.
"""

from __future__ import annotations

from typing import Callable, Optional

from sqlmodel import Session

from . import llm_parse, model_exchange, prompt_load


def call_json(
    db: Session, usage: str, values: dict[str, str],
    exchanges: Optional[list[model_exchange.ModelExchange]], chat: Callable[..., str],
) -> dict:
    """One model call for `usage`, its template filled with `values`."""
    spec = prompt_load.load(db, usage)
    user_message = spec.user_template
    for key, value in values.items():
        user_message = user_message.replace("{" + key + "}", value)
    exchange = model_exchange.begin(exchanges, usage, spec, spec.system_prompt, user_message)
    raw = chat(
        [{"role": "system", "content": spec.system_prompt},
         {"role": "user", "content": user_message}],
        model=spec.model, format="json",
    )
    if exchange is not None:
        exchange.raw_output = raw
    return llm_parse.extract_object(raw)
