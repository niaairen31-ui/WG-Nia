# BRIEF — Step "Deterministic targeted join: `target_gathering_id` on scene/join"

Ticket: TICKET-0032 · Brief: BRIEF-0032-a · v1.00
Execution order: first (BRIEF-0032-c depends on this endpoint contract;
BRIEF-0032-b is independent and may run in parallel).

## Context

TICKET-0032 wires a "Parler" affordance from the spatial canvas onto NPC
circles. The client always knows the exact target `gathering_id` (from the
scene roster), yet the only join path today routes free text through
`_interpret_mode` — an LLM call to resolve something code already resolved.
The 0031 handoff contract pointed "Parler" at `POST /api/conversations/start`,
but that endpoint creates conversations with no `gathering_id`
(`routes/play.py:131-146`), invisible to `_active_conv_for_gathering`. Decision
G2-b amends the contract: "Parler" joins deterministically through
`scene/join`.

## Scope IN

1. **`src/world_engine/cockpit/routes/play.py` — extend `SceneJoinBody`
   (currently line 391)**: add field
   `target_gathering_id: Optional[str] = None` with comment:
   `# G2-b (TICKET-0032): deterministic targeted join — when present, the`
   `# interpretation step is skipped entirely; code resolves what code knows.`
   `player_text` becomes `Optional[str] = None`; exactly one of the two must
   be provided — both present or both absent -> 422.

2. **`scene_join` handler (currently line 534)**: after the existing
   `already_joined` short-circuit and the `no open gatherings` guard, branch:
   if `body.target_gathering_id` is set, validate that the gathering (a) exists,
   (b) `status == "open"`, (c) `location_id` == player's current location,
   (d) `session_id` == the open session — else 404 ("Gathering not found or
   not open") / 400 ("Gathering does not match this location/session"),
   mirroring the wording of `join_gathering` (`routes/play.py:239-246`). On
   success, enter the existing creation path with the resolved id.

3. **Refactor `_scene_join_resolve_and_create` (currently line 461)**: split
   the conversation-creation tail (from `behaviour = _load_npc_dialogue_template...`
   to the return) into a new function
   `_scene_join_create_for_gathering(resolved_id, player_id, location_id, world_id, sess, db) -> dict`
   in the same module. The free-text path calls interpretation then this
   function; the targeted path calls this function directly. Behavior of the
   free-text path must be byte-identical (same LLM calls, same rows, same
   response shape).

4. **Docstring of `scene_join`**: add one paragraph documenting the targeted
   mode and that it performs zero model calls.

5. **Unit tests** (same test module/style as existing play route tests):
   - targeted join creates conversation + `gathering_member`, conversation
     `gathering_id` set, interpreter mock NOT called;
   - closed gathering -> 404, wrong location -> 400, zero rows written;
   - both/neither of `player_text` / `target_gathering_id` -> 422;
   - free-text path regression: interpreter mock IS called, response shape
     unchanged.

6. **`ARCHITECTURE_DECISIONS.md`** (append-only): new entry under the spatial
   workstream section:
   `G2-b (TICKET-0032) — "Parler" handoff AMENDED: the 0031 client contract`
   `(routes/spatial.py header) pointed the talk affordance at`
   `POST /api/conversations/start, which creates gathering-less conversations`
   `invisible to _active_conv_for_gathering. The affordance now performs a`
   `deterministic targeted join via scene/join.target_gathering_id (no LLM`
   `call — code resolves what code knows). conversations/start remains for`
   `1:1 pilot flows.`

7. **`routes/spatial.py` header comment (lines 13-18)**: update the client
   handoff contract paragraph to point at the targeted join, referencing
   G2-b.

## Scope OUT

- No change to `POST /api/conversations/start` (stays as-is for pilot 1:1).
- No change to `/api/conversations/{conv_id}/join` (post-conversation C2
  picker path stays).
- No client code (BRIEF-0032-c).
- No canvas, no spatial rendering (BRIEF-0032-b).
- No player migration primitive between gatherings (I1 is composed
  client-side from leave + join; do NOT add a server-side migrate endpoint).
- No change to the C2 picker's name-based flow in `index.html` (it may adopt
  `target_gathering_id` in a later cleanup; not now).
- NPC migration between gatherings (pending Tier 3 C2) untouched.

## Invariants to defend

- **Single canon-write paths**: joining is a state transition, not a canon
  mutation — no `proposed_mutation` row; `single_canon_write.py` must stay
  green.
- **History is sacred**: append-only edit to `ARCHITECTURE_DECISIONS.md`.
- **Prompts propres**: the targeted path must contain zero model calls — that
  is the point of this brief; a "small helper" that still calls
  `_interpret_mode` is a failure.

## Done means

- [ ] All five unit-test groups of Scope IN §5 pass.
- [ ] `tooling/verify` suite green (including `single_canon_write.py`).
- [ ] Live: `curl POST /api/scene/join` with a valid `target_gathering_id`
      returns `{conversation_id, gathering}`; server log shows no Ollama
      call for that request.
- [ ] Live: free-text join from the existing scene view still works
      unchanged.
- [ ] `ARCHITECTURE_DECISIONS.md` entry present; `routes/spatial.py` header
      updated.
- [ ] /review-step and /close-step run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md` (Scope IN §6). No schema change — no changelog
  entry, `schema_version_touched: none`.
