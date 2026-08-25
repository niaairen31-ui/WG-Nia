<script>
  /* TICKET-0075 (BRIEF-0075-a). Journée's own shell-native surface -- a
     sibling of Play/Création/Observation, mounted the same way as
     Observation.svelte (M10 precedent): always mounted from App.svelte,
     `active` only toggles this root's own visibility, no legacy bridge
     call.

     Once submitted, a declaration is never editable here: no edit control,
     no delete control, and `declared_action` has no update path anywhere
     in the backend (writes/pipeline.py). No agenda data is fetched,
     rendered or referenced anywhere in this surface (Scope OUT). */
  import { serverState } from '../lib/serverState.svelte.js';
  import { navigate } from '../lib/router.js';
  import {
    journeeState, selectedDay, loadDays, selectDay, submitDeclaration, reloadForWorld,
    planDay, resolveDay,
  } from './journee.svelte.js';

  let { active = false } = $props();

  function goToPlay() {
    navigate('play');
  }

  // Mirrors writes/pipeline.py's MAX_DECLARATION_CHARS -- no shared source
  // across the network boundary, so the two are kept in step by hand.
  const MAX_DECLARATION_CHARS = 4000;

  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });
</script>

<div class="app-view" id="journee-view" style:display={active ? '' : 'none'}>

  <div class="queue-panel" id="journee-declare-panel">
    <div class="panel-head">
      <h2>Journée — déclarer une action</h2>
    </div>
    <div class="queue-body">
      <textarea
        bind:value={journeeState.declaration}
        maxlength={MAX_DECLARATION_CHARS}
        rows="6"
        placeholder="Que fait votre personnage aujourd'hui ?"
        disabled={journeeState.submitting}
      ></textarea>
      <div class="char-count">{journeeState.declaration.length} / {MAX_DECLARATION_CHARS}</div>
      {#if journeeState.submitError}
        <div class="r-err">{journeeState.submitError}</div>
      {/if}
      <div style="margin-top:8px">
        <button disabled={journeeState.submitting || !journeeState.declaration.trim()} onclick={() => submitDeclaration()}>
          Déclarer
        </button>
      </div>
    </div>
  </div>

  <div class="queue-panel" id="journee-list-panel">
    <div class="panel-head">
      <h2>Jours précédents</h2>
      <button class="btn-icon" onclick={() => loadDays()} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      {#if journeeState.daysLoading}
        <div class="empty"><span class="spin">⟳</span></div>
      {:else if journeeState.days.length === 0}
        <div class="empty">Aucun jour déclaré.</div>
      {:else}
        {#each journeeState.days as d (d.id)}
          <div class="day-row" class:selected={journeeState.selectedId === d.id} onclick={() => selectDay(d.id)}>
            <span class="badge b-other">Jour {d.day_number}</span>
            <span class="target-ref">{d.status}</span>
          </div>
        {/each}
      {/if}

      {#if selectedDay()}
        {@const day = selectedDay()}
        <div class="day-detail">
          <h3>Jour {day.day_number} — {day.status}</h3>
          <p>{day.declared_action}</p>

          {#if day.status === 'submitted'}
            <button disabled={journeeState.planning} onclick={() => planDay(day.id)}>
              {journeeState.planning ? '⟳ Émission du plan…' : 'Émettre le plan'}
            </button>
          {:else if day.status === 'resolving'}
            <button disabled={journeeState.resolving} onclick={() => resolveDay(day.id)}>
              {journeeState.resolving ? '⟳ Résolution…' : 'Résoudre la journée'}
            </button>
          {/if}
          {#if journeeState.planError}<div class="r-err">{journeeState.planError}</div>{/if}
          {#if journeeState.resolveError}<div class="r-err">{journeeState.resolveError}</div>{/if}

          {#if journeeState.detail?.feasibility}
            {@const feas = journeeState.detail.feasibility}
            <p class="muted feasibility-note">
              Faisabilité : {feas.veto_retained}/{feas.python_retained} étape(s) retenue(s) —
              {feas.reason}
              {#if feas.outcome === 'unavailable'}(jugement indisponible, plan inchangé){/if}
            </p>
          {/if}

          {#if journeeState.detailLoading}
            <div class="empty"><span class="spin">⟳</span></div>
          {:else if journeeState.detailError}
            <div class="r-err">{journeeState.detailError}</div>
          {:else if journeeState.detail?.account}
            {@const account = journeeState.detail.account}
            <div class="day-account">
              {#if account.is_replay}<div class="badge b-other">journée rejouée — dernière résolution</div>{/if}

              <h4>Récit</h4>
              <p class="account-prose">{account.prose}</p>

              <h4>Personnages rencontrés</h4>
              {#if account.npcs.length === 0}
                <p class="muted">Aucun.</p>
              {:else}
                <ul>{#each account.npcs as n}<li>{n.name}</li>{/each}</ul>
              {/if}

              <h4>Lieux visités</h4>
              {#if account.locations.length === 0}
                <p class="muted">Aucun.</p>
              {:else}
                <ul>{#each account.locations as l}<li>{l.name}</li>{/each}</ul>
              {/if}
              {#if account.role_hints.length > 0}
                <p class="muted">Évoqués sans identité résolue : {account.role_hints.join(', ')}</p>
              {/if}

              <h4>Gains</h4>
              <ul class="gains-list">
                {#each account.gains.resource as g}
                  <li><span class="badge b-other">ressource</span> {g.status} — {JSON.stringify(g.detail)}</li>
                {/each}
                {#each account.gains.knowledge as g}
                  <li><span class="badge b-other">connaissance</span> {g.subject} → {g.to_level} ({g.status})</li>
                {/each}
                {#each account.gains.relation as g}
                  <li><span class="badge b-other">relation</span> {g.status} — {JSON.stringify(g.detail)}</li>
                {/each}
                {#if account.gains.resource.length === 0 && account.gains.knowledge.length === 0 && account.gains.relation.length === 0}
                  <li class="muted">Rien pour l'instant.</li>
                {/if}
              </ul>
              <p class="muted">{account.gains.skill.note}</p>

              {#if account.germs.length > 0}
                <h4>Nouveaux contacts entrevus</h4>
                <ul>{#each account.germs as g}<li>{g.name} ({g.role_hint || '—'}) — {g.status}</li>{/each}</ul>
              {/if}

              {#if account.pending_review.length > 0}
                <h4>En attente de revue</h4>
                <ul>{#each account.pending_review as p}<li>{p.mutation_type} — {p.rationale}</li>{/each}</ul>
              {/if}

              {#if account.rendezvous}
                <h4>Rendez-vous</h4>
                <p>
                  {account.rendezvous.objective}
                  {#if account.rendezvous.npc_name}(avec {account.rendezvous.npc_name}){/if}
                </p>
                <button onclick={goToPlay}>Parler</button>
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>

</div><!-- #journee-view -->

<style>
  .r-err { color: var(--red); }
  .char-count { font-size: 12px; color: var(--muted); margin-top: 4px; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .day-row {
    display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer;
  }
  .day-row.selected { background: rgba(106, 176, 255, 0.15); }
  .day-detail {
    margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px;
    white-space: pre-wrap;
  }
  .day-account { margin-top: 12px; }
  .day-account h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
  .account-prose { white-space: pre-wrap; }
  .muted { color: var(--muted); font-size: 12px; }
  .gains-list { list-style: none; padding: 0; margin: 0; }
  .gains-list li { padding: 2px 0; }
</style>
