# BRIEF-0050-c — Step "conversation_summary prompt usage (creator-editable model)"

## Context

Brief (d) will summarize the older, dropped turns and feed the result into the empty summary slot
from brief (b). That summary is an LLM call and, per the standing pattern, it must route through a
seeded `prompt_template` with a `PROMPT_REGISTRY` entry so its text AND its model are creator-
editable exactly like every other prompt (decision C1-configurable / N2). This brief ships the
prompt plumbing only — no call site yet. Default model is the authoring model (`llama3.1:8b`),
overridable per world from the prompts tab.

Mini-RECON (confirmed this session): `upsert_prompt_template(session, id, *, world_id, name, usage,
system_prompt, user_template, variables, destination)` is the seed shape
(`scripts/seed_pilot.py:1662-1671`, npc_dialogue block). `PROMPT_REGISTRY` entries are
`PromptSpec(surface, world_scoped, dry_run_capable, call_sites, default_model)`
(`prompt_registry.py`), with `_author_model` -> `llama3.1:8b` (`prompt_registry.py:_author_model`,
`entity_author.py:39`). The creator model override write path already exists:
`PATCH /api/prompts/{id}/model` (CLAUDE.md:302, `cockpit/crud/prompts.py:327`), validated
fail-closed against the live registry.

## Scope IN

1. **`PROMPT_REGISTRY` entry** in `src/world_engine/prompt_registry.py`, key
   `"conversation_summary"`:
   ```
   "conversation_summary": PromptSpec(
       surface="play",
       world_scoped=True,
       dry_run_capable=False,
       call_sites=("src/world_engine/conversation_window.py:_load_summary_template",),
       default_model=_author_model,
   ),
   ```
   (The `call_sites` anchor is the loader added in brief (d); naming it now keeps the registry the
   single source of "what runs where".)

2. **Seed block** in `scripts/seed_pilot.py`, alongside the other `upsert_prompt_template(...)`
   calls, id `"pt-conversation-summary"`, `world_id=None` (applies to every world; per-world
   override remains possible), `usage="conversation_summary"`, `destination="local"`. The
   `system_prompt` is a compression instruction (French, the game surface language) whose exact
   text is below — the executor copies it verbatim, does not paraphrase. The `user_template` is
   `"{transcript}"` with `variables=["transcript"]`.

   `system_prompt` (verbatim):
   ```
   Tu es un outil de compression de conversation, pas un personnage.
   On te donne la partie ANCIENNE d'un dialogue entre un joueur et un ou plusieurs PNJ.
   Produis un resume factuel et compact de ce qui s'est passe, en francais, a la troisieme
   personne.

   Regles strictes :
   - Ne conserve que ce qui a un effet durable sur la scene : faits etablis, decisions prises,
     informations revelees, changements d'attitude, objets ou promesses echanges.
   - Enumere les points sans les redire mot pour mot : c'est un aide-memoire, pas une transcription.
   - N'invente rien. Ne complete pas. Ne devine pas la suite.
   - Ne joue aucun personnage, n'ecris aucune replique, ne t'adresse a personne.
   - Omet les salutations, les hesitations et les repetitions.
   - Maximum une douzaine de lignes, en puces courtes.

   Ne renvoie que le resume, sans preambule ni conclusion.
   ```

3. **No call site.** This brief does NOT invoke the template. Brief (d) adds the loader
   `_load_summary_template` and the `ollama_client.chat(...)` call.

4. **Verify check** `tooling/verify/checks/conversation_summary_usage.py` (standard idiom,
   vacuous-proof): assert `"conversation_summary"` is a key in `PROMPT_REGISTRY` with
   `default_model is _author_model` and `world_scoped is True`; and assert a `prompt_template` row
   with `usage="conversation_summary"` exists after seeding. If either is absent -> FAIL.

## Scope OUT

- No summarization call, no word-budget trigger, no message-list wiring — brief (d). If the
  executor is tempted to "just hook it up", STOP: (d) owns the call and its F1 per-turn cadence.
- No new model-override route — the existing `PATCH /api/prompts/{id}/model` already covers the new
  usage. Do NOT add a bespoke route.
- No UI change — the prompts tab already lists every seeded usage; the new row appears there for
  free. The extra config fields (budget/K/enabled) beside it are brief (e).
- Do NOT set a non-NULL `model` in the seed. NULL means "code default" (`_author_model`); a
  hardcoded seed model would shadow the creator override semantics.
- Do NOT translate the prompt to English — the play surface runs in French; the summary is consumed
  by the French-speaking game model.

## Invariants to defend

- **model choice is a creator override, resolved at read time** (`effective_model`,
  `prompt_registry.py:42`): seed `model` NULL, default via `_author_model`.
- **every seeded usage has a registry entry** — this brief adds both halves together.
- **the summary prompt never authors canon**: it is a compression tool; it emits prose for the
  prompt only, never a `proposed_mutation` (enforced structurally in brief d — flagged here for
  continuity).

## Done means

- [ ] After `python scripts/seed_pilot.py`, a `prompt_template` row with
      `usage='conversation_summary'`, `world_id IS NULL`, `model IS NULL` exists with the verbatim
      system prompt above.
- [ ] The prompts tab in the cockpit lists "conversation_summary" and shows its model as the
      resolved default (`llama3.1:8b`) with an editable override control.
- [ ] `PATCH /api/prompts/{id}/model` on that row to a non-NULL value persists, and the prompts
      list then shows the override.
- [ ] `python tooling/verify/checks/conversation_summary_usage.py` PASSES; removing the registry
      entry makes it FAIL (vacuous-proof).
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: add `conversation_summary` to the prompt-usage inventory with
  `default_model = author`, and note it is a compression artifact (C1), never a canon-write path.
- This step is otherwise its own doc.
