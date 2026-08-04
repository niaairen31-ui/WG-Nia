<script>
  /* TICKET-0059 (BRIEF-0059-h commit 2). Faithful port of
     loadCreationArtefacts + CREATION_ARTEFACTS_NOTICE (index.html, now
     deleted) -- read-only list, GET /api/entities?type=artifact. Preserves
     the three-state behaviour exactly: rows present -> notice + row-table;
     empty response -> notice + "Aucun artefact dans la base."; fetch
     failure -> notice + "Aucun artefact disponible." (the failure branch
     swallows the error deliberately, same as the legacy `catch (_)` --
     not "improved" into a surfaced error).

     No refresh control existed on this tab before (unlike competences/
     registre's icon button) and none is added here -- the island resets
     itself off serverState.worldId (the -d rule every migrated island
     follows), the same idiom as Constructeur.svelte's own effect.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { serverState } from '../lib/serverState.svelte.js';

  const NOTICE = "La création et l'édition d'artefacts arriveront dans une étape ultérieure (support backend requis).";

  let rows = $state(null); // null = loading, [] = empty, [...] = loaded
  let failed = $state(false);

  async function load() {
    rows = null;
    failed = false;
    try {
      const res = await fetch('/api/entities?type=artifact');
      if (!res.ok) throw new Error(res.statusText);
      rows = await res.json();
    } catch (_err) {
      failed = true;
      rows = [];
    }
  }

  $effect(() => {
    void serverState.worldId;
    load();
  });
</script>

{#if rows === null}
  <div class="empty"><span class="spin">⟳</span></div>
{:else}
  <p style="font-style:italic; color:var(--muted); margin-bottom:16px">{NOTICE}</p>
  {#if failed}
    <div class="empty">Aucun artefact disponible.</div>
  {:else if rows.length === 0}
    <div class="empty">Aucun artefact dans la base.</div>
  {:else}
    <div class="row-table">
      {#each rows as a (a.id)}
        <div class="row-card">
          <div style="font-weight:600">{a.name}</div>
          {#if a.description}
            <div style="font-size:12px; color:var(--muted); white-space:pre-wrap">{a.description}</div>
          {/if}
          <div style="font-size:11px; color:var(--muted)">{a.status || ''}</div>
        </div>
      {/each}
    </div>
  {/if}
{/if}
