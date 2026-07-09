# BRIEF — Step "AI agenda-draft assistant (generate_agenda_draft)"

## Context

BRIEF-0021-a moved Intrigues onto the entity-sheet shell and shipped an
empty `#agenda-gen-panel` placeholder in the create panel. This brief fills
it: the creator selects an owner, types a one-sentence intent, and the
assistant pre-fills the shell — title + 2-to-5 steps — in the existing
form. The generator is a standalone sibling of `generate_npc_goals`
(entity_author.py:736): agendas are not `entity` rows, so it is NOT a
`_TYPE_FIELDS` entry. It writes no canon; the only write is the creator's
accept through the existing `POST /api/agendas`. Locked: B1, C1 (C2
deferred), D1.

## Scope IN

1. **Prompt constants in `scripts/seed_pilot.py`** — add, verbatim:

   ```python
   AGENDA_DRAFT_SYSTEM_PROMPT = """\
   Tu es un assistant d'écriture pour un jeu de rôle. On te donne l'identité \
   d'un propriétaire (une faction ou un personnage) et une intention en une \
   phrase. Tu produis la coquille d'une intrigue : un titre et de 2 à 5 étapes.

   Règles :
   - Le titre est court et évocateur (moins de 10 mots), sans ponctuation \
   finale.
   - Chaque étape est un objectif concret tenant en UNE seule phrase, \
   commençant par un verbe à l'infinitif.
   - Les étapes forment une progression : chacune rapproche le propriétaire \
   de l'aboutissement de l'intention, et la dernière l'accomplit ou l'expose \
   à l'échec.
   - N'invente aucun nom propre absent des informations fournies.
   - Reste cohérent avec le caractère du propriétaire : une faction agit \
   selon sa philosophie, un personnage selon son passé.

   Tu réponds UNIQUEMENT avec un objet JSON, sans texte autour :
   {"title": "…", "steps": ["…", "…"]}\
   """

   AGENDA_DRAFT_USER_TEMPLATE = """\
   Propriétaire ({owner_kind}) : {owner_name}
   Ce qu'on sait de lui : {owner_context}
   Intention du créateur : {brief}\
   """
   ```

2. **Template seed** — in the seed's prompt-template block, add an
   `upsert_prompt_template` call (S2 discipline: text written only on a
   virgin head; non-text head fields converge on re-seed):
   - id `pt-agenda-draft`, world_id `None`,
   - name `"Assistant de création d'intrigue — titre + étapes (JSON)"`,
   - usage `"agenda_generation"` (new usage value),
   - variables `["owner_kind", "owner_name", "owner_context", "brief"]`,
   - destination `"local"`,
   - the two constants above.
   Comment mirrors the pt-npc-goals block: standalone sibling, NOT a
   `_TYPE_FIELDS` entry, pure generate-and-return, C2 (goal-link
   suggestions) explicitly deferred.

3. **`entity_author.generate_agenda_draft`** — new function, signature:
   ```python
   def generate_agenda_draft(
       owner_kind: str,        # "faction" | "personnage" (French, injected verbatim)
       owner_name: str,
       owner_context: str,     # pre-assembled public context, see item 4
       brief: str,
       db: Session,
   ) -> dict:
   ```
   Behaviour cloned from `generate_npc_goals` (entity_author.py:736-790):
   loads `pt-agenda-draft` via the same template-loading idiom,
   `current_prompt`, `.replace()` substitution of the four variables,
   `chat(..., model=effective_model(template, AUTHOR_MODEL), format="json")`.
   Never raises into the caller — every failure (missing template,
   OllamaError, non-JSON, empty/malformed dict) returns
   `{"ok": False, "error": "<reason>"}`.
   On success returns `{"ok": True, "title": str, "steps": [str, ...],
   "notes": [str, ...]}` where:
   - `title` is the trimmed string, `""` when absent/malformed (note
     appended: `"Titre absent du brouillon — à saisir manuellement."`);
   - `steps` keeps trimmed non-empty strings only, truncated to 5 (note on
     truncation); fewer than 2 is a PARTIAL accept (note:
     `"Moins de 2 étapes générées — compléter manuellement."`), never an
     error — the creator finishes the shell by hand;
   - the function contains no `writes.`, no `session.add`/`db.add`, no
     commit: generate-and-return only (machine-checked).

4. **Endpoint `POST /api/agendas/generate`** — in cockpit (app.py, beside
   the other `/generate` routes, app.py:166-467 family). Body:
   `{owner_entity_id: str, brief: str}`. Server-side D1 resolution:
   - 404/422 if the entity is missing, inactive, or not of type
     `faction`/`character` (mirror `write_agenda`'s owner rule so the
     assistant can never draft for an owner the create would reject);
   - `owner_kind` = `"faction"` or `"personnage"`;
   - `owner_context` assembled from PUBLIC fields only:
     - faction: `entity.description` + `Faction.philosophy`
       (models.py:174), joined as
       `"{description}\nPhilosophie : {philosophy}"`, each part dropped
       when empty;
     - character: `entity.description` + `Character` backstory, joined as
       `"{description}\nPassé : {backstory}"`, each part dropped when
       empty;
     - both empty -> `"(aucune description)"` (the `(aucune faction)`
       precedent).
   - delegates to `generate_agenda_draft`; thin route, no logic beyond
     resolution (the app.py:135-146 "ONE seam" comment style applies:
     never raises, returns the generator's dict verbatim).
   Secrets stay structurally excluded: the resolver reads no `knowledge`
   rows, no `character.secrets`, no `internal_tensions`.

5. **Cockpit panel** — fill `#agenda-gen-panel` (shipped empty in -a) with
   the `authorRenderGeneratePanel` idiom (index.html:5463+):
   - title « Générer avec l'IA », textarea
     `#agenda-gen-brief` (rows=2, placeholder:
     `Intention en une phrase, ex. : « La Guilde du Sel veut prendre le
     contrôle du port sans que le Magistrat ne s'en aperçoive »`),
     button « Générer » -> `intriguesGenerateDraft()`, status span
     `#agenda-gen-status`, notes div `#agenda-gen-notes`;
   - `intriguesGenerateDraft()`: reads the owner select — empty ->
     status « Propriétaire requis. », return, form untouched; empty brief
     -> « Intention requise. »; on success fills the title input and the
     five step inputs positionally (steps beyond the draft cleared),
     renders notes, status « Brouillon généré — relisez et éditez avant
     d'accepter. »; on `ok:false` shows the error, form untouched;
   - one-shot (F2 precedent): a second « Générer » overwrites title and
     all five step fields with the new draft.

6. **Verify check `verify/checks/agenda_assist.py`** — asserts:
   `generate_agenda_draft` exists in entity_author.py and its body contains
   none of `writes.`, `session.add`, `db.add`, `.commit(`; the
   `pt-agenda-draft` upsert exists in seed_pilot.py with the exact usage
   and variables; the `/api/agendas/generate` route is registered.

## Scope OUT

- **C2 (deferred explicitly)** — no suggested `goal_agenda_link`s, no NPC
  goal names in the draft, no `linked_goals` key in the JSON contract.
  Revisit when goal-name resolution has a concrete design.
- **D2** — the model never proposes or names the owner; owner is a
  creator-side select, resolved server-side.
- **Conversational refine** — one-shot only, the BRIEF-24 F2 precedent.
- **`visibility_trace` generation** — the model does not author traces.
- **No per-world template**, no new `_TYPE_FIELDS` entry, no
  `generate_entity_draft` routing.
- **No apply-script** — `pt-agenda-draft` is a virgin head; seed_pilot
  alone creates head + v1. An apply_ticket_0021 script exists only if a
  later brief revises the text.

## Invariants to defend

- **Model proposes, code judges / single canon-write paths**: the
  generator and its route write NOTHING; the only write is the existing
  create endpoint the creator triggers.
- **Secrets excluded structurally**: owner_context is built from public
  columns by query construction; the resolver never touches `knowledge`,
  `character.secrets`, or `internal_tensions`.
- **History is sacred**: untouched — no canon write here; the prompt
  template head/version goes through the seed's upsert + versioned store
  as always.

## Done means

- [ ] Live sequence: `python scripts/backup.py` then
      `python scripts/seed_pilot.py` — output shows `pt-agenda-draft`
      created (head + v1); re-run reports convergence, no duplicate version
- [ ] `pt-agenda-draft` appears in the Prompts tab, editable/versionable
      like `pt-npc-goals`
- [ ] In the Intrigues create panel: owner selected + intent typed +
      « Générer » -> title and steps pre-filled; editing then
      « + Créer l'intrigue » creates the agenda through the normal path,
      step 1 active
- [ ] « Générer » with no owner -> « Propriétaire requis. », form untouched;
      with Ollama stopped -> error shown, form untouched
- [ ] A draft for a faction owner reflects its philosophy; for a character
      owner, its backstory (spot-check one of each)
- [ ] `python tooling/verify/run.py` passes including
      `verify/checks/agenda_assist.py`
- [ ] /review-step and /close-step run (engine + cockpit code touched)

## Docs to update

- ARCHITECTURE_DECISIONS.md: append "AI agenda-draft assistant
  (TICKET-0021, B1/C1/D1)" — sibling-generator rationale, C2 deferred, D2
  rejected, owner-context public-fields-only rule.
- No schema change; no changelog entry. Prompt-template addition is data,
  not schema.
