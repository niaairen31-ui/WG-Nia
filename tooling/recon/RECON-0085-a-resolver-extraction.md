<!-- slug: resolver-extraction -->
# RECON-0085-a — Named-rung extraction for a creator-scoped resolver

Report-only. Measured against `main` at schema **v1.97**, fetched fresh.
No finding in this document authorizes a change; BRIEF-0085-a does.

## F1 — The named rungs depend on the concordance context only through `world_id`

`_rung_named_exact` (day_concordance.py:172) and `_rung_named_token`
(day_concordance.py:188) each read exactly one field of `_ConcordContext`:
`ctx.world_id`. Neither touches `place_candidate_ids` nor
`reachable_location_ids`. `_rung_named_alias` (day_concordance.py:211) is a
declared permanent no-op — its body is `del mention, ctx, db; return None`.

**Consequence:** extraction to a module parameterized on `world_id` is
mechanical. None of the casting machinery (`_cast_one`, `CAST_PRECEDENCE`,
`_concord_reachable_ids`, `who_is_at`) travels with it, and the extracted
module needs no `Character`.

## F2 — `_normalize_surface` is the shared dependency and is pure

`_normalize_surface` (day_concordance.py:147) takes text and returns text: no
`ctx`, no `Session`. Both named rungs apply it to both sides of every
comparison. It carries the accent-stripping, the bounded three-iteration
leading-article strip, and the apostrophe-aware token split that makes French
elision work.

**Consequence:** it moves with the rungs, and `day_concordance` imports it back.
Duplicating it would be two functions that mean the same thing — and would drift
the day path and the lore path apart on the first French edge case.

## F3 — `Mention` is a `day_extract` type, and importing it would couple the
chantiers

`Mention` (day_extract.py:42) carries `category`, `surface_form`, `kind`, and
`role_hint`. The named rungs use `category` and `surface_form`, and guard on
`kind != "named"`. `role_hint` is only meaningful for the inferred rungs.

**Consequence, and the one real design call in this brief:** a lore module
importing `day_extract` would inherit the whole player-declaration extraction
chain for the sake of a two-field dataclass. The extracted function should take
`(surface_form: str, category: str, world_id: str, db: Session)` and assume the
mention is named; `day_concordance` keeps its own `kind != "named"` guard at the
call site, exactly where it already is.

## F4 — `_RUNG_LOOKUPS` bijection is asserted by an existing G1 check

`tooling/verify/checks/day_concordance.py` R6 asserts `MATCHING_RUNGS` and
`_RUNG_LOOKUPS` are in bijection, and the dispatch signature is
`Callable[[Mention, _ConcordContext, Session], Optional[list[str]]]`.

**Consequence:** the `_RUNG_LOOKUPS` entries must keep that exact signature.
After extraction they become thin adapters that unpack the mention and call the
shared function. R6 keeps passing without being touched.

## F5 — `AmbiguousMention` exists but carries bare ids

`AmbiguousMention` (day_concordance.py:119) is `(mention, candidate_ids)`.
Nothing in it lets a reader tell two same-named entities apart.

**Consequence:** the ambiguity round-trip the ticket requires needs candidates
with distinguishing detail (name, type, description). That is a presentation
lookup, not a resolver concern — the extracted resolver stays id-only, and the
enrichment belongs to BRIEF-0085-c.

## F6 — The existing purity check is scoped to two named files

`verify/checks/day_concordance.py` R1 asserts `day_concordance.py` contains no
`db.add(`, no `.commit(`, no `chat(`; R4 names `day_extract.py`,
`day_concordance.py`, `day_plan.py`.

**Consequence:** widening those file lists would put this ticket's contract
inside TICKET-0075/0081's check. This chantier gets its own check file.

## F7 — Both named rungs fetch the world's entities of a type and filter in
Python

Each rung issues `select(Entity).where(world_id, type, status == "active")` and
compares normalized names in Python. There is no index-backed name lookup.

**Consequence:** cost is linear in the world's entity count of that type, per
mention. Same cost the day chain already pays per declaration. Acceptable for an
interactive question; **report only**, no optimization in this ticket.

## F8 — Function-length headroom is fine

`concord` is 55 lines against `MAX_LINES = 80`
(`verify/checks/function_length.py`). Extraction shortens it.

## F9 — No naming collision

`resolution.py` is physical-action dice resolution, unrelated. No `lore_*` module
exists. The `day_*` / `observation_*` prefix idiom extends cleanly to `lore_*`.

## F10 — Structural facts the later briefs depend on

- `knowledge` has **no** `world_id` (canon.py:442). World scoping goes through
  `entity_id -> entity.world_id`, at query construction.
- `knowledge.subject` is free text, indexed (`idx_knowledge_subject`). No FK. The
  reverse question ("who knows about X") is therefore not answerable structurally
  and is correctly excluded from this ticket's selector set.
- `relation` carries `world_id` directly, plus `direction`, `intensity`,
  `visible_to_b`, `notes`.
- `faction` extends `entity` by primary key; several of its columns are marked
  DORMANT in the model (`parent_faction_id`, `scope`) — a dossier must not
  present dormant columns as canon.
- `prompt_registry.PromptSpec.default_model` is a zero-argument callable;
  `_author_model` is the authoring-side symbol. A new usage costs one entry.
- `llm_parse.extract_object` is the single sanctioned JSON extraction path and
  raises `LlmParseError`.
- `ollama_client.chat` raises `OllamaError` on unreachable host or HTTP error —
  the exception the deterministic fallback catches.
- Routes are `APIRouter` modules under `cockpit/routes/`, included in
  `cockpit/app.py` (currently 13 `include_router` lines).
- Frontend surfaces are Svelte directories under `frontend/src/` with a
  `<Name>.svelte` plus a `<name>.svelte.js` store, as `observation/`.

## Open question raised by the RECON, for Nia

None blocking. F3 is a design call; BRIEF-0085-a takes it explicitly and names it
in Scope IN so it can be reversed there rather than discovered in the diff.
