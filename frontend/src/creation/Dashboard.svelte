<script>
  /* TICKET-0115 (BRIEF-0115-E; H1, E2, F2, I1, J1 and M1 of the
     conditions series' dashboard). The « Suivi » island: the creator's
     dashboard -- each metric a question, its numbers and the decision codes
     it watches, no threshold (E2) -- the deferrals she watches with their
     reactivation condition, and the export of the same scope for a deeper
     analysis. One world or all (J1), two real-world days. Reads only; its
     CREATION_ISLANDS entry declares origin 'new'. State and requests live
     in dashboard.svelte.js. */
  import { untrack } from 'svelte';
  import { dashboardState, loadDashboard, exportDashboard, share } from './dashboard.svelte.js';

  // Loaded once when the island mounts; the selectors reload on change.
  $effect(() => {
    untrack(() => loadDashboard());
  });

  const STATUS_FR = { open: 'en attente', reached: 'atteinte' };
  let metricTitles = $derived(Object.fromEntries(dashboardState.metrics.map((m) => [m.key, m.title])));

  function metricLabel(key) {
    if (!key) return 'à surveiller toi-même';
    if (key === 'export') return "mesurable dans l'export";
    return 'suivie par « ' + (metricTitles[key] || key) + ' »';
  }
</script>

<div class="dashboard">
  <div class="queue-panel">
    <div class="queue-body">
      <div class="inline">
        <label>Monde
          <select bind:value={dashboardState.world} onchange={loadDashboard}>
            <option value="all">Tous les mondes</option>
            {#each dashboardState.worlds as w (w.id)}<option value={w.id}>{w.name}</option>{/each}
          </select>
        </label>
        <label>du <input type="date" bind:value={dashboardState.since} onchange={loadDashboard} /></label>
        <label>au <input type="date" bind:value={dashboardState.until} onchange={loadDashboard} /></label>
        <button class="btn-icon" onclick={loadDashboard} title="Rafraîchir">↻</button>
        <button class="btn-send" disabled={dashboardState.exporting} onclick={exportDashboard}>
          {dashboardState.exporting ? 'Export…' : 'Exporter (JSON)'}
        </button>
      </div>
      <div class="muted">
        L'export contient tout ce que voit Création, secrets et notes compris : il ne quitte ta machine que si
        tu l'envoies.
      </div>
      {#if dashboardState.exportError}<div class="r-err">Export : {dashboardState.exportError}</div>{/if}
      {#if dashboardState.loadError}
        <div class="r-err">Erreur : {dashboardState.loadError}</div>
      {:else}
        <div class="cards">
          {#each dashboardState.metrics as metric (metric.key)}
            <div class="row-card metric">
              <div class="head">
                <strong>{metric.title}</strong>
                {#each metric.watches as code (code)}<span class="badge b-other">{code}</span>{/each}
                {#if !metric.dated}<span class="badge b-other">état actuel</span>{/if}
              </div>
              <div class="question">{metric.question}</div>
              {#if metric.rows.length === 0}
                <div class="muted">Aucune donnée pour cette période.</div>
              {:else}
                <table>
                  <tbody>
                    {#each metric.rows as row, i (i)}
                      <tr><td class="muted">{row.group}</td><td>{row.label}</td><td class="num">{share(row)}</td></tr>
                    {/each}
                  </tbody>
                </table>
              {/if}
              <div class="muted">{metric.note}</div>
            </div>
          {/each}
        </div>
        <h4>Reports surveillés</h4>
        {#each dashboardState.deferrals as d (d.code + d.ticket)}
          <div class="row-card" class:reached={d.status === 'reached'}>
            <div class="head">
              <strong>{d.code}</strong> <span class="muted">{d.ticket}</span>
              <span class="badge b-other">{STATUS_FR[d.status] || d.status}</span>
              {#if d.follow_up}<span class="badge b-other">{d.follow_up}</span>{/if}
            </div>
            <div>{d.deferred}</div>
            <div class="muted">Revient si : {d.condition} — {metricLabel(d.metric)}</div>
          </div>
        {/each}
      {/if}
    </div>
  </div>
</div>

<style>
  .dashboard { display: flex; flex-direction: column; gap: 12px; }
  .head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .inline { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 6px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; margin-top: 10px; }
  .metric table { width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 13px; }
  .metric td { padding: 2px 4px; vertical-align: top; }
  .metric td.num { text-align: right; white-space: nowrap; }
  .question { margin: 4px 0; font-style: italic; }
  .row-card.reached { border-left: 3px solid var(--red); }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  h4 { margin: 16px 0 4px; font-size: 13px; color: var(--muted); }
</style>
