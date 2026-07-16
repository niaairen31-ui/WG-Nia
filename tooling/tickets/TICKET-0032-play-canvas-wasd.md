---
id: TICKET-0032
title: Play-mode canvas + WASD input (client spatial surface)
type: feature
status: brief
created: 2026-07-16
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]      # scene/join creates conversation + gathering_member rows (existing paths only)
blast_radius: medium
brief_ids: [BRIEF-0032-a, BRIEF-0032-b, BRIEF-0032-c]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Ticket 0032 — Play-mode canvas + WASD input (client)
>
> Purpose
> A minimal real-time spatial surface grafted onto the Play cockpit: player circle
> moves via WASD, NPC circles are drawn, walls are drawn, movement is validated by
> the server.
>
> Locked context
> - New front surface: `<canvas>` + requestAnimationFrame loop, OUTSIDE HTMX.
>   Standalone JS grafted onto existing Play cockpit.
> - Movement is visually transient (Q1): the canvas moves the player circle;
>   nothing is written to canon.
> - The canvas emits movement segments to the collision endpoint (brief 2) and
>   calls the proximity endpoint (brief 3, E2) when relevant.
> - Renders: player circle, NPC circles (positions from brief 3), walls
>   (obstacle geometry from brief 1).
>
> To resolve in discussion
> - Input model: WASD -> velocity -> segment emission cadence.
> - How the server's corrected stop point reconciles with the client's drawn
>   position.
> - When the client decides to call the proximity endpoint (E2 "when to ask").
> - Building entry/exit (D1) is explicitly OUT of this ticket, its own chantier.

## Clarifications resolved (intake)

- **A1 — Input model: server-lockstep at fixed cadence.** Client accumulates
  WASD into an intended displacement; every tick it sends
  `last confirmed position -> intended destination` to `/api/spatial/move-check`
  and draws ONLY server-confirmed positions (linear interpolation toward the
  confirmed point between ticks). No optimistic drawing, no client-side
  collision prediction (C3 remains rejected). Reconciliation question is moot
  by construction.
- **B1 — Cadence: 100 ms (10 Hz)** while movement input is active; zero
  requests when idle.
- **D1 — Proximity timing: on-stop with debounce.** One call on scene entry,
  then one call when movement ceases (all movement keys released AND last
  confirmed position stable, ~200 ms debounce). No proximity calls while
  moving.
- **E (transitional) — Spawn: fixed center of bounds.** Documented as
  temporary; the upcoming door chantier will replace spawn with
  spawn-at-door. No probing, no server spawn endpoint.
- **F2 — New cockpit tab "Play (spatiale)".** On activation, one
  `GET /api/entities/{location_id}`; if `geometry.bounds_width/height` is
  null, the tab shows an explicit "lieu non spatial" error message instead of
  the canvas.
- **G2 + G2-b — "Parler" goes through the gathering-anchored join flow,
  deterministically.** `SceneJoinBody` gains optional `target_gathering_id`;
  when present the server SKIPS `_interpret_mode` (no LLM call), validates
  the gathering is open at the player's location, and enters the existing
  creation path. This AMENDS the 0031 client-handoff contract
  (`routes/spatial.py:13-18`, which pointed at `POST /api/conversations/start`);
  rationale: `conversations/start` creates conversations with no
  `gathering_id`, invisible to `_active_conv_for_gathering` and to
  "Reprendre la conversation". Amendment must be logged in
  ARCHITECTURE_DECISIONS.md.
- **I1 — "Parler" while already grouped:** same-gathering NPC -> resume /
  continue (existing flow); other-gathering NPC -> `POST /api/scene/leave`
  then targeted join (existing endpoints, correct close-and-analyze
  semantics).
- **H1 — Keyboard capture:** WASD handled only when no input/textarea has
  focus (`document.activeElement` guard); canvas click focuses it, Esc
  releases.
- **Rendering scale:** default 24 px/m; mouse-wheel zoom centered on cursor,
  clamped 8–64 px/m.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `scene/join` with `target_gathering_id` performs zero LLM calls and
      anchors the created conversation to that gathering
      -> verify/checks/scene_join_target.py
- [ ] `scene/join` with `target_gathering_id` for a closed / wrong-location
      gathering is rejected (404/400), no rows written
      -> verify/checks/scene_join_target.py
- [ ] Existing free-text `scene/join` behavior unchanged (regression:
      interpretation path still runs when `target_gathering_id` absent)
      -> verify/checks/scene_join_target.py
- [ ] No new write path: the client surface performs zero writes outside
      existing endpoints (`scene/join`, `scene/leave`)
      -> verify/checks/single_canon_write.py
- [ ] routes/play.py and routes/scene.py stay within the module-budget cap
      -> verify/checks/module_budget.py

### Live  ->  human gate (Nia)
- [ ] "Play (spatiale)" tab: spatial location renders bounds, walls, NPC
      circles, player circle at center spawn
- [ ] Non-spatial location shows the explicit error message, no canvas
- [ ] WASD moves the player; walls stop movement with no visual
      pass-through; typing in chat inputs never moves the player
- [ ] Wheel zoom in/out around cursor, clamped
- [ ] Stopping within 2.0 m of an NPC surfaces "Parler"; clicking it opens a
      gathering-anchored conversation; "Reprendre la conversation" sees it
      after leaving/reloading
- [ ] "Parler" on an NPC of another gathering while grouped leaves the
      current group (conversation closed + analyzed) then joins the target
