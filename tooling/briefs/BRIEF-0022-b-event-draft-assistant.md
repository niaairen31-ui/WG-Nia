# BRIEF — Step "AI event-draft assistant (generate_event_draft)"

## Context

BRIEF-0022-a shipped the Événements tab on the entity page contract, with an
empty `#event-gen-panel` placeholder in the create panel. This brief fills it:
the creator types a one-sentence intent, optionally pre-selects a location,
and the assistant pre-fills the shell — title, description, type, location and
involved-entity chips.

The generator is a standalone sibling of `generate_agenda_draft`
(entity_author.py:825) and `generate_npc_goals` (entity_author.py:736):
`event` is not an `entity` row, so it is NOT a `_TYPE_FIELDS` entry. It writes
no canon. The only write is the creator's accept through the EXISTING
`POST /api/events` from BRIEF-0022-a.

Two pieces of the design already exist and must be reused rather than
reinvented: `tick.py:889-897` performs exactly the name→id resolution I2 asks
for (resolved ids kept, unresolved names dropped into `notes`, never
invented), and `tick.py:929`'s `_build_roster` establishes the roster idiom
(`name.casefold() -> id`, ambiguous names removed so resolution fails cleanly
rather than guessing).

Locked: B2 (assistant), I2, J3.

## Scope IN

1. **Prompt constants in `scripts/seed_pilot.py`** — add, verbatim:

   ```python
   EVENT_DRAFT_SYSTEM_PROMPT = """\
   Tu es un assistant d'écriture pour un jeu de rôle. On te donne une \
   intention en une phrase, éventuellement un lieu, et la liste des noms \
   connus du monde. Tu produis la coquille d'un événement du monde.

   Règles :
   - Le titre est court et factuel (moins de 10 mots), sans ponctuation \
   finale.
   - La description tient en deux ou trois phrases : ce qui s'est produit, \
   pas ce que les personnages en pensent.
   - Le type est EXACTEMENT l'une de ces valeurs : political, military, \
   criminal, social, mystery, magical, other.
   - Le lieu et les entités impliquées sont choisis UNIQUEMENT parmi les \
   noms fournis. N'invente aucun nom propre absent de ces listes. Si aucun \
   ne convient, laisse la liste vide.
   - Tu ne décides pas de ce que le monde sait de cet événement.

   Tu réponds UNIQUEMENT avec un objet JSON, sans texte autour :
   {"title": "…", "description": "…", "type": "…", "location": "…", \
   "involved_entities": ["…", "…"]}\
   """

   EVENT_DRAFT_USER_TEMPLATE = """\
   Intention du créateur : {brief}
   Lieu pressenti : {location_hint}
   Lieu — contexte public : {location_context}
   Noms connus du monde : {roster_names}\
   """
   ```

   The system prompt names the seven `_EVENT_TYPES` values verbatim, in
   English, because that is the column's vocabulary (BRIEF-0022-a item 2).
   It carries **no `knowledge_status` key** — the model must never propose
   what the world knows (I2).

2. **Template seed** — in the seed's prompt-template block, an
   `upsert_prompt_template` call (S2 discipline: text written only on a virgin
   head; non-text head fields converge on re-seed):
   - id `pt-event-draft`, world_id `None`
   - name `"Assistant de création d'événement — coquille (JSON)"`
   - usage `"event_generation"` (new usage value)
   - variables `["brief", "location_hint", "location_context", "roster_names"]`
   - destination `"local"`
   - the two constants above

   Comment mirrors the `pt-agenda-draft` block: standalone sibling, not a
   `_TYPE_FIELDS` entry, pure generate-and-return, `knowledge_status`
   deliberately absent from the contract.

3. **`PROMPT_REGISTRY` entry** in `prompt_registry.py`:

   ```python
   "event_generation": PromptSpec(
       surface="authoring",
       world_scoped=False,
       dry_run_capable=False,
       call_sites=("src/world_engine/entity_author.py:_load_event_draft_template",),
       default_model=_author_model,
   ),
   ```

4. **`entity_author._load_event_draft_template(db)`** — clone of
   `_load_agenda_draft_template` (entity_author.py:141), keyed on
   `pt-event-draft`.

5. **`entity_author.generate_event_draft`** — new function:

   ```python
   def generate_event_draft(
       brief: str,
       location_hint: str,          # location name, or "" when none pre-selected
       location_context: str,       # pre-assembled public context, see item 6
       roster: dict[str, str],      # name.casefold() -> entity_id, see item 6
       db: Session,
   ) -> dict:
   ```

   Behaviour cloned from `generate_agenda_draft` (entity_author.py:825-900):
   loads the template, `current_prompt`, `.replace()` substitution of the four
   variables (`roster_names` = the roster's display names, comma-joined,
   sorted), `chat(..., model=effective_model(template, AUTHOR_MODEL),
   format="json")`.

   **Never raises into the caller.** Every failure mode — missing template,
   `OllamaError`, non-JSON, empty/malformed dict — returns
   `{"ok": False, "error": "<reason>"}`.

   On success returns:
   `{"ok": True, "title": str, "description": str, "type": str,
     "location_id": str | None, "involved_entities": [str, …],
     "notes": [str, …]}`

   Parsing rules, each producing a `notes` entry when it fires:
   - `title` — trimmed; `""` when absent/malformed (noted). Empty title +
     empty description = `{"ok": False, "error": "..."}`.
   - `description` — trimmed; `""` when absent.
   - `type` — `casefold()`ed, then `raw if raw in _EVENT_TYPES else "other"`.
     **Import `_EVENT_TYPES` from `tick.py`**; do not re-type the seven.
     Coercion is noted, mirroring `tick.py:877`.
   - `location` — resolved against the location names in `roster`, casefolded.
     Unresolved → `location_id = None` + note. **Never invented.** When
     `location_hint` was supplied by the creator, it wins outright and the
     model's `location` key is ignored (noted if they disagree).
   - `involved_entities` — the `tick.py:889-897` loop, verbatim in shape:
     each name casefolded and looked up in `roster`; resolved ids appended;
     unresolved names appended to `notes` as
     `« nom non résolu, ignoré : … »` and dropped. Never an invented id.
     Duplicates collapsed, order preserved.

   **`knowledge_status` must not appear anywhere in the returned dict**, nor
   be read from `parsed`. If the model volunteers one, it is silently
   discarded (not even noted — noting it would invite the creator to honour
   it).

   The function body contains no `writes.`, no `db.add`, no `session.add`.

6. **`POST /api/events/generate` in `cockpit/app.py`** — mirrors
   `generate_agenda` (app.py:440-477), which is the precedent for server-side
   context assembly:

   ```python
   class EventGenerateBody(BaseModel):
       brief: str
       location_id: Optional[str] = None
   ```

   - `brief` empty/whitespace → `422 « Intention requise. »`
   - `location_id`, when supplied, must resolve to an **active `location`
     entity in the active world** (the `app.py:1575-1583` predicate). 422
     otherwise.
   - `location_context` = the location entity's `name` and `description`
     only. Public fields only. Never `internal_name`, never `metadata`.
   - **The J3 roster** is built here, server-side, by a new module-level
     helper in `entity_author.py`:

     ```python
     def build_world_roster(db: Session, world_id: str) -> dict[str, str]:
     ```

     `select(Entity.id, Entity.name, Entity.type).where(Entity.world_id == world_id,
     Entity.status == "active", Entity.is_public.is_(True))`.

     **`is_public` MUST be in the `where` clause, not post-filtered in
     Python.** `context.py:615` post-filters it after the query — that is the
     pattern NOT to copy. Secrets are excluded by query construction at every
     assembler; this is an assembler.

     `internal_name` is never selected (`context.py:530`). Only `name` and
     `type` leave the function.

     Ambiguity discipline from `_build_roster` (tick.py:929-940): when two
     active public entities share a casefolded name, **both are removed** from
     the roster so resolution fails cleanly instead of guessing. Removed names
     are returned alongside so the route can note them.

   - Returns `generate_event_draft(...)`'s dict unchanged. The route writes no
     canon.

7. **Create-panel UI in `index.html`** — fill `#event-gen-panel`, styled and
   structured exactly like `#agenda-gen-panel` (index.html:3994-4005):

   - a `<textarea id="event-gen-brief">` with a placeholder such as
     « Une phrase, ex. : « Une crue emporte le pont du quartier bas pendant
     la nuit » »
   - a « Générer » button calling `evenementsGenerateDraft()`
   - a `<span id="event-gen-status">` and a `<div id="event-gen-notes">`

   `evenementsGenerateDraft()`:
   - reads the brief and the currently selected `location_id` from the form
     (the creator may have chosen one already — it is then authoritative)
   - empty brief → « Intention requise. », form untouched
   - `POST /api/events/generate`; on `{ok: false}` shows the error, **form
     untouched** (never partially filled from a failed draft)
   - on `{ok: true}` fills title, description, `type` (the `datalist` input),
     `location_id` (the location select), and pushes each resolved
     `involved_entities` id into `evenementsInvolvedDraft` as a chip,
     resolving names from the cached `authorAllEntities`
   - **never touches the `knowledge_status` select**, which stays at its
     `secret` default (BRIEF-0022-a item 9)
   - renders `notes` as muted lines in `#event-gen-notes` — this is where
     unresolved names surface. Unresolved names must NOT become chips.

## Scope OUT

- Everything in BRIEF-0022-a's Scope OUT, unchanged.
- **`knowledge_status` in the JSON contract**, in any form — no key, no
  suggestion, no note (I2). The creator promotes `secret → public` by an
  informed click, and under C3 that same field is the sole retraction lever.
- **`occurred_at`** — the assistant proposes no date, in-fiction or otherwise.
- **`has_magic_impact` / `consequences`** — no reader; not proposed.
- **Editing an existing event with the assistant.** Generation lives in the
  create panel only. Regenerating over a saved event is not built.
- **Any change to `tick._EVENT_TYPES`, to `tick.py`'s own draft parsing, or to
  the tick prompt.** `_EVENT_TYPES` is imported and read; `tick.py:889-897` is
  the *model* for the new loop, not a function to extract and share. Extracting
  a shared helper is a second concrete case away — do not generalize here.
- **`dry_run_capable`** — the registry entry says `False`, like every other
  authoring prompt.
- **Any migration.** A prompt template is data, not schema.

## Invariants to defend

- **Model proposes, code judges.** `generate_event_draft` writes no canon.
  Every id it returns was resolved from the roster by code; the model returns
  names only, and an unresolvable name is dropped with a note, never coerced
  into a plausible id.
- **Secrets excluded structurally, by query construction.** `build_world_roster`
  filters `is_public` in SQL. A verify check asserts `is_public` appears in the
  `where` clause and that `internal_name` is never selected.
- **The model never sets visibility.** No `knowledge_status` in the prompt, in
  the parse, or in the returned dict. Events created through the assistant are
  born `secret` like any other creator-authored event.
- **Single canon-write paths.** Unchanged. The accept goes through the
  BRIEF-0022-a `POST /api/events`, which calls `write_event`.
- **Failure is total, never partial.** A failed generation leaves the form
  exactly as the creator left it.

## Done means

- [ ] Live sequence: `python scripts/backup.py`, then
      `python scripts/seed_pilot.py` — output shows `pt-event-draft` created
      (head + v1); re-run reports convergence, no duplicate version
- [ ] `pt-event-draft` appears in the Prompts tab, editable and versionable
      like `pt-agenda-draft`
- [ ] In the Événements create panel: an intent typed + « Générer » pre-fills
      title, description, type, location and involved-entity chips
- [ ] `knowledge_status` still reads `secret` after a successful generation;
      creating the event yields a `secret` event
- [ ] A brief naming an entity that does not exist produces a note
      « nom non résolu, ignoré : … » and **no chip** for that name
- [ ] A brief naming a `is_public = FALSE` entity resolves nothing — the
      entity is absent from the roster (spot-check with one)
- [ ] « Générer » with an empty brief → « Intention requise. », form untouched;
      with Ollama stopped → error shown, form untouched, no partial fill
- [ ] A pre-selected location is honoured even when the model proposes another
- [ ] `python tooling/verify/run.py` passes, including the new
      `verify/checks/event_assist.py`
- [ ] /review-step and /close-step run (engine + cockpit code touched)

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append **"AI event-draft assistant
  (TICKET-0022, I2/J3)"**. Record: sibling-generator rationale (third
  instance — `generate_npc_goals`, `generate_agenda_draft`,
  `generate_event_draft`; a shared abstraction is now *one* case away and is
  deliberately NOT built); **`knowledge_status` structurally absent from the
  model contract, and why**; `build_world_roster`'s query-construction
  `is_public` filter, contrasted with `context.py:615`'s post-filter, which is
  logged as a divergence to correct opportunistically; name→id resolution
  discipline reused from `tick.py:889-897` without extraction.
- No schema change, no changelog entry. The prompt template is data.

---

## Drafting decisions flagged for Nia

1. **Le brouillon ne propose pas de statut.** Verrouillé par I2, mais je le
   remonte parce que c'est le point le plus contre-intuitif du brief : le
   modèle peut inventer un événement entier, et pas décider si le monde le
   sait. C'est délibéré, et c'est aussi ce qui rend C3 (aucune suppression)
   vivable — `knowledge_status` est ta seule marche arrière.
2. **Le lieu présélectionné écrase la proposition du modèle** (item 5). Je
   note le désaccord dans `notes` plutôt que de le taire. L'alternative —
   laisser le modèle proposer un autre lieu et te faire choisir — ajoute une
   décision à chaque génération. Refusé, réversible.
3. **Je n'extrais PAS de helper partagé** pour la résolution nom→id, malgré
   trois usages proches (`tick.py:889`, `tick.py:1114`, le nouveau). Les trois
   ont des rosters de portée différente (lieu, faction, monde). Minimal first :
   on généralisera quand une quatrième portée le forcera.
4. **`build_world_roster` vit dans `entity_author.py`**, pas dans `context.py`.
   Motif : c'est un assembleur d'autorat, pas de jeu. Si tu préfères
   `context.py` pour regrouper tous les assembleurs, c'est un déplacement de
   fonction, sans conséquence.
5. **`context.py:615` post-filtre `is_public` en Python.** Je ne le corrige pas
   dans ce ticket (hors scope, chemin de jeu), mais je le consigne dans
   `ARCHITECTURE_DECISIONS.md` comme divergence à reprendre. Dis-moi si tu
   veux que ça devienne un TICKET-0023 à part.
