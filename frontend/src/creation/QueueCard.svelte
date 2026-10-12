<script>
  /* TICKET-0059 (BRIEF-0059-k commit 2). Faithful port of renderCard +
     _renderResourceChangeLegs + _renderAgendaProvenanceSummary +
     doApprove/doReject/showResult/lockCard/unlockCard/markCardDone
     (index.html, now deleted) -- one card per mutation, split out of
     Queue.svelte the same way RoleRow.svelte carries its own local edit
     buffer instead of scattering per-row state through one big component.

     payloadText/notesText seed ONCE from the mutation prop (no resync
     effect): a card goes read-only the moment its status leaves
     'proposed' and never becomes editable again, so there is nothing to
     resync -- the same one-shot-seed reasoning RoleRow.svelte's own
     header describes, just without that component's resync effect
     because this card never needs one. */
  import { mutationEntityName, mutationAgendaName, mutationDayInfo, shortId, approveMutation, rejectMutation, toggleSelected, queueState } from './queue.svelte.js';
  import { draftFromPayload, payloadFromDraft } from './eventDraft.svelte.js';
  import { vocabState, loadVocabulary } from './eventVocab.svelte.js';
  import { creationState } from './state.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';
  import EventEditor from './EventEditor.svelte';

  let { mutation, selected } = $props();

  // Captured once, deliberately not re-derived from `mutation` -- the Svelte
  // compiler warns that this only captures the initial value; that's the
  // intent, not a bug. markMutationDone (queue.svelte.js) replaces this
  // card's mutation object on approve/reject to flip `status`, but never
  // touches payload/creator_notes; resyncing these from the prop (an
  // $effect or $derived) would stomp whatever the creator just typed and
  // submitted back to the pre-edit original the instant it succeeds.
  let payloadText = $state(JSON.stringify(mutation.payload, null, 2));
  let notesText = $state(mutation.creator_notes || '');
  let locked = $state(false);
  let resultCls = $state('');
  let resultMsg = $state('');

  let editable = $derived(mutation.status === 'proposed');

  /* TICKET-0119 (BRIEF-0119-D, Y2): a typed event proposal still in review is
     edited in the shared EventEditor -- its type, text, participants and
     their secret, quantity, scopes, and what it changes in the world -- and
     approved as edited (`payloadFromDraft`). Seeded once, like payloadText:
     the card never resyncs from the prop. An untyped proposal keeps its
     payload. */
  const typedEvent = mutation.mutation_type === 'event_creation' && mutation.status === 'proposed'
    && !!(mutation.payload && mutation.payload.type_name);
  let eventDraft = $state(typedEvent ? draftFromPayload(mutation.payload, mutationEntityName) : null);
  let showJson = $state(!typedEvent);

  $effect(() => {
    if (typedEvent) loadVocabulary(serverState.worldId);
  });

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  }

  let targetTxt = $derived(
    [mutation.target_table, mutation.target_id ? shortId(mutation.target_id) : null].filter(Boolean).join(' · ')
  );
  let sourceRef = $derived(
    mutation.conversation_id
      ? `conv:${shortId(mutation.conversation_id)}`
      : mutation.pass_play_id
        ? `pass-play:${shortId(mutation.pass_play_id)}`
        : ''
  );

  /* BRIEF-0075-e (D2): the day this pass_play-sourced proposal came from,
     so the queue entry links back to it in context -- day number and the
     declaration's first line, same idiom as mutationEntityName/
     mutationAgendaName's lazy id->label caches. */
  let dayInfo = $derived(
    mutation.source_type === 'pass_play' ? mutationDayInfo(mutation.pass_play_id) : null
  );

  /** Human-readable money + optional knowledge leg for a resource_change
   *  card (BRIEF-19) -- the creator sees what is being granted before
   *  approving. null for every other mutation_type. */
  function resourceChangeLegs(m) {
    if (m.mutation_type !== 'resource_change') return null;
    const p = m.payload || {};
    const amount = Number(p.amount);
    const amountTxt = isNaN(amount) ? String(p.amount) : (amount >= 0 ? '+' : '') + amount;
    const amountColor = amount < 0 ? 'var(--danger, #c44)' : 'var(--accent)';
    const k = p.knowledge && typeof p.knowledge === 'object' ? p.knowledge : null;
    return {
      entityName: mutationEntityName(p.entity_id),
      amountTxt,
      amountColor,
      counterpartyName: p.counterparty_id ? mutationEntityName(p.counterparty_id) : '',
      reason: p.reason || '',
      knowledge: k
        ? {
            entityName: mutationEntityName(k.entity_id),
            level: k.level || '',
            content: k.content || '',
          }
        : null,
    };
  }

  /** Human-readable summary for agenda_delegation (ids resolved to names)
   *  and agenda_creation (owner name resolved), TICKET-0020/BRIEF-0020-c.
   *  null for every other mutation_type. */
  function agendaProvenanceSummary(m) {
    const p = m.payload || {};
    if (m.mutation_type === 'agenda_delegation') {
      return {
        kind: 'delegation',
        npcName: mutationEntityName(p.npc_id),
        horizon: p.horizon || '',
        goal: p.goal || '',
        agendaName: mutationAgendaName(p.agenda_id),
      };
    }
    if (m.mutation_type === 'agenda_creation') {
      return { kind: 'creation', ownerName: mutationEntityName(p.owner_entity_id), title: p.title || '' };
    }
    return null;
  }

  /** TICKET-0114 (BRIEF-0114-H, I2): a typed event_creation read for the
   *  creator -- its type (a proposed one with its roles, approved with the
   *  event), each participant by role, its quantity. null otherwise (an
   *  untyped proposal shows its payload only). */
  function eventSummary(m) {
    if (m.mutation_type !== 'event_creation') return null;
    const p = m.payload || {};
    if (!p.type_name) return null;
    return {
      typeName: p.type_name,
      newType: p.new_type && typeof p.new_type === 'object' ? p.new_type : null,
      participants: (p.participants || []).map((x) => ({
        role: x.role || '',
        name: x.entity_id ? mutationEntityName(x.entity_id) : (x.sorte_name || ''),
        newSorte: !x.entity_id && !x.sorte_id && !!x.sorte_name,
      })),
      quantity: p.quantity || null,
      place: p.location_id ? mutationEntityName(p.location_id) : '',
    };
  }

  let resourceLegs = $derived(resourceChangeLegs(mutation));
  let eventLegs = $derived(eventSummary(mutation));
  let agendaSummary = $derived(agendaProvenanceSummary(mutation));

  function onCheckToggle(ev) {
    toggleSelected(mutation.id, ev.currentTarget.checked);
  }

  async function onApprove() {
    if (eventDraft) payloadText = JSON.stringify(payloadFromDraft(eventDraft, mutation.payload, vocabState.types), null, 2);
    // Validate JSON before sending -- saves a round trip.
    try {
      JSON.parse(payloadText);
    } catch (e) {
      resultCls = 'err';
      resultMsg = 'Invalid JSON in payload: ' + e.message;
      return;
    }
    locked = true;
    resultCls = '';
    resultMsg = '⟳ Applying to canon…';
    try {
      const r = await approveMutation(mutation.id, payloadText, notesText);
      resultCls = r.cls;
      resultMsg = r.msg;
    } catch (e) {
      resultCls = 'err';
      resultMsg = '✗ ' + e.message;
      locked = false;
    }
  }

  async function onReject() {
    locked = true;
    resultCls = '';
    resultMsg = '⟳ Rejecting…';
    try {
      const r = await rejectMutation(mutation.id, notesText);
      resultCls = r.cls;
      resultMsg = r.msg;
    } catch (e) {
      resultCls = 'err';
      resultMsg = '✗ ' + e.message;
      locked = false;
    }
  }
</script>

<div class="card s-{mutation.status}">
  <div class="card-head">
    {#if editable}
      <input type="checkbox" class="row-select" checked={selected} onchange={onCheckToggle}>
    {/if}
    <span class="badge b-{mutation.mutation_type}">{mutation.mutation_type}</span>
    {#if targetTxt}<span class="target-ref">{targetTxt}</span>{/if}
    <span class="badge b-{mutation.status}">{mutation.status}</span>
    {#if mutation.source_type === 'world_tick' && mutation.tick_id}
      <span class="badge b-tick" title="tick {mutation.tick_id}">TICK ·{mutation.tick_id.slice(0, 4)}</span>
    {/if}
    {#if mutation.source_type === 'pass_play'}
      <span class="badge b-pass-play" title="pass_play {mutation.pass_play_id}">JOURNÉE{dayInfo ? ` · Jour ${dayInfo.dayNumber}` : ''}</span>
    {/if}
    {#if mutation.payload && mutation.payload.secret_derived === true}
      <span class="badge b-secret-derived">dérivé d'un secret</span>
    {/if}
    {#if sourceRef}<span class="target-ref">{sourceRef}</span>{/if}
    {#if dayInfo?.firstLine}<span class="target-ref">« {dayInfo.firstLine} »</span>{/if}
    <span class="ts">{fmtDate(mutation.proposed_at)}</span>
  </div>

  {#if mutation.status === 'approved' && mutation.creator_notes}
    <div class="card-apply-error"><strong>⚠ Could not apply to canon — needs attention:</strong>{mutation.creator_notes}</div>
  {/if}
  {#if mutation.applied_duplicate}
    <div class="card-dup-warn"><strong>⚠ Duplicate risk — approving will be blocked:</strong>{mutation.applied_duplicate}</div>
  {/if}

  <div class="card-rationale">{mutation.rationale || '(no rationale provided)'}</div>

  {#if resourceLegs}
    <div class="card-fields" style="margin-bottom:8px;">
      <div class="field-label">Money leg</div>
      <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
        <span style="font-weight:600;">{resourceLegs.entityName}</span>
        <span style="font-weight:700; color:{resourceLegs.amountColor};">{resourceLegs.amountTxt}</span>
        {#if resourceLegs.counterpartyName}<span style="color:var(--muted); font-size:12px;">↔ {resourceLegs.counterpartyName}</span>{/if}
        {#if resourceLegs.reason}<span style="font-size:12px;">{resourceLegs.reason}</span>{/if}
      </div>
      {#if resourceLegs.knowledge}
        <div class="field-label" style="margin-top:6px;">Knowledge leg</div>
        <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
          <span class="badge b-new_knowledge">knowledge</span>
          <span style="font-weight:600;">{resourceLegs.knowledge.entityName}</span>
          <span style="color:var(--muted); font-size:12px;">{resourceLegs.knowledge.level}</span>
          {#if resourceLegs.knowledge.content}<span style="font-size:12px;">{resourceLegs.knowledge.content}</span>{/if}
        </div>
      {/if}
    </div>
  {/if}

  {#if eventDraft && editable}
    <div class="card-fields" style="margin-bottom:8px;">
      <EventEditor draft={eventDraft} entities={queueState.entities} playerCharIds={creationState.playerCharIds}
                   withText={true} />
    </div>
  {:else if eventLegs}
    <div class="card-fields" style="margin-bottom:8px;">
      <div class="field-label">Événement</div>
      <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
        <span style="font-weight:600;">{eventLegs.typeName}</span>
        {#if eventLegs.newType}<span class="badge b-other">nouveau type — validé avec l'événement</span>{/if}
        {#if eventLegs.quantity}<span>× {eventLegs.quantity}</span>{/if}
        {#if eventLegs.place}<span style="font-size:12px; color:var(--muted);">à {eventLegs.place}</span>{/if}
      </div>
      {#if eventLegs.newType}
        <div style="font-size:12px; color:var(--muted);">
          Rôles : {eventLegs.newType.roles.map((r) => r.name + (r.accepts_sorte ? ' (ou une sorte)' : '')).join(', ')}
        </div>
      {/if}
      {#each eventLegs.participants as x, i (i)}
        <div style="font-size:12px;">{x.role} : <strong>{x.name}</strong>{#if x.newSorte} <span class="badge b-other">sorte à créer</span>{/if}</div>
      {/each}
    </div>
  {/if}

  {#if agendaSummary?.kind === 'delegation'}
    <div class="card-fields" style="margin-bottom:8px;">
      <div class="field-label">Délégation</div>
      <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
        <span style="font-weight:600;">{agendaSummary.npcName}</span>
        <span style="font-size:12px; color:var(--muted);">{agendaSummary.horizon}</span>
        <span>{agendaSummary.goal}</span>
        <span style="font-size:12px; color:var(--muted);">sert : « {agendaSummary.agendaName} »</span>
      </div>
    </div>
  {:else if agendaSummary?.kind === 'creation'}
    <div class="card-fields" style="margin-bottom:8px;">
      <div class="field-label">Propriétaire</div>
      <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
        <span style="font-weight:600;">{agendaSummary.ownerName}</span>
        <span>{agendaSummary.title}</span>
      </div>
    </div>
  {/if}

  <div class="card-fields">
    {#if showJson}
      <div>
        <div class="field-label">Payload</div>
        <textarea class="payload" rows="5" spellcheck="false" readonly={!editable || !!eventDraft} bind:value={payloadText}></textarea>
      </div>
    {:else}
      <button class="btn-icon" style="font-size:12px" onclick={() => (showJson = true)}>Voir le JSON</button>
    {/if}
    <div>
      <div class="field-label">Creator notes</div>
      <input class="notes" type="text" placeholder={editable ? 'optional note…' : ''} readonly={!editable} bind:value={notesText}>
    </div>
  </div>

  {#if editable}
    <div class="card-actions">
      <button class="btn-approve" disabled={locked} onclick={onApprove}>✓ Approve</button>
      <button class="btn-reject" disabled={locked} onclick={onReject}>✗ Reject</button>
    </div>
  {/if}

  <div class="card-result {resultMsg ? 'show' : ''} {resultCls ? 'r-' + resultCls : ''}">{resultMsg}</div>
</div>
