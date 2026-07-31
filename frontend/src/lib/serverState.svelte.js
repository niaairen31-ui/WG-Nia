/* TICKET-0056 (C3). The SERVER is the authority on the active world; this
   store is a MIRROR, never a second source of truth. Deliberate contrast
   with the legacy loadBootstrap() (index.html), which swallows every error
   in `catch (_) {}` and leaves WORLD_ID null with no visible symptom: a
   failed read here sets `error` and the shell renders a refusal banner.
   Fail-closed over advisory. */
export const serverState = $state({
  worldId: null,
  playerId: null,
  worlds: [],
  error: null,
});

export async function refreshServerState() {
  try {
    const bootstrapRes = await fetch('/api/bootstrap');
    if (!bootstrapRes.ok) {
      throw new Error(`GET /api/bootstrap -> ${bootstrapRes.status}`);
    }
    const bootstrap = await bootstrapRes.json();

    const worldsRes = await fetch('/api/worlds');
    if (!worldsRes.ok) {
      throw new Error(`GET /api/worlds -> ${worldsRes.status}`);
    }
    const worldsData = await worldsRes.json();

    serverState.worldId = bootstrap.world_id;
    serverState.playerId = bootstrap.player_id;
    serverState.worlds = worldsData;
    serverState.error = null;
  } catch (err) {
    serverState.error = err.message;
  }
}
