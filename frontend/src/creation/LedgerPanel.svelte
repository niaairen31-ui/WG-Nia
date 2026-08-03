<script>
  /* TICKET-0058 (BRIEF-0058-g, family d). Faithful port of the read-only
     "Solde" block on a character/faction sheet (schema v1.31, BRIEF-18) --
     authorLoadLedger/authorRenderLedger (index.html, now deleted). Write
     path stays the global Registre tab (POST /api/ledger, still legacy,
     out of scope -- one of the ticket's five residual legacy tabs); this
     panel only reads GET /api/entities/{id}/ledger.

     authorAddLedgerEntry (index.html:~4820) is NOT part of this port
     despite appearing in the brief's family list: it belongs to the
     Registre tab's own add-form (registre-f-entity/-amount/... ids), a
     completely different legacy surface untouched by this ticket
     (RECON-SUPPLEMENT-0058's ticket-level correction: registre is one of
     the five expected residual legacy tabs) -- moving it would strand the
     Registre tab's own "Ajouter" button. Reported as a RECON M7
     approximation, not acted on. */
  let { entityId } = $props();

  let balance = $state(0);
  let entries = $state([]);
  let loadError = $state('');

  async function load() {
    try {
      const data = await fetch(`/api/entities/${encodeURIComponent(entityId)}/ledger`).then((r) => r.json());
      balance = data.balance;
      entries = data.entries || [];
      loadError = '';
    } catch (e) {
      loadError = e.message;
    }
  }

  $effect(() => { load(); });

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  }
</script>

{#if loadError}
  <div class="empty">{loadError}</div>
{:else}
  <div style="font-size:20px; font-weight:700; color:{balance >= 0 ? 'var(--accent)' : 'var(--danger, #c44)'}; margin-bottom:8px;">{balance}</div>
  {#if entries.length === 0}
    <div class="empty">Aucune ligne pour cette entité.</div>
  {:else}
    <div class="row-table">
      {#each entries as e}
        <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
          <span style="color:var(--muted); font-size:12px;">{fmtDate(e.created_at)}</span>
          <span style="font-weight:700; color:{e.amount >= 0 ? 'var(--accent)' : 'var(--danger, #c44)'};">{e.amount >= 0 ? '+' : ''}{e.amount}</span>
          <span style="font-size:12px; flex:1; min-width:120px;">{e.reason || ''}</span>
          <span class="badge b-other">{e.source_type || ''}</span>
        </div>
      {/each}
    </div>
  {/if}
{/if}
