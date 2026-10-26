<script>
  /* TICKET-0129 (BRIEF-0129-F, C-08, C-15). The creator's review of one
     submitted character draft, below the player's version in
     PcDraftPanel.svelte: the starting place, each person (create, attach,
     drop) and the relation he has for the character, each membership, one
     NPC batch per group of people to create and its rows, the check of the
     final version, then the return with a note or the approval. Every call
     goes through pcReview.svelte.js; errors show in place. */
  import {
    abandonLot, afterApproval, afterReturn, approveDraft, loadLot, loadReview, prepareLot,
    returnDraft, runLot, saveReview, setLotRow,
  } from './pcReview.svelte.js';

  let { draftId } = $props();

  const KINDS = { family: 'Famille', master: 'Maître', faction: 'Faction', other: 'Autre' };

  let body = $state(null);
  let edit = $state(null);
  let lotRows = $state({});
  let note = $state('');
  let busy = $state(false);
  let error = $state('');
  let loadSeq = 0;

  function copyOf(review) {
    return {
      review_location_id: review.review_location ? review.review_location.entity_id : '',
      sketches: review.sketches.map((s) => ({
        id: s.id, action: s.action, entity_id: s.entity ? s.entity.entity_id : '',
        relation_type: s.relation_type, intensity: s.intensity,
      })),
      memberships: review.memberships.map((m) => ({ id: m.id, dropped: m.dropped })),
    };
  }

  function complete(group) {
    return group.lot && group.lot.npcs_done >= group.lot.npcs_total;
  }

  async function rowsOf(groups) {
    const rows = {};
    for (const group of groups) {
      if (complete(group)) rows[group.lot.batch_id] = (await loadLot(group.lot.batch_id)).rows;
    }
    return rows;
  }

  async function show(next) {
    const rows = await rowsOf(next.groups);
    body = next;
    edit = copyOf(next.review);
    lotRows = rows;
  }

  $effect(() => {
    const id = draftId;
    const seq = ++loadSeq;
    if (!id) return;
    body = null;
    error = '';
    note = '';
    loadReview(id).then(
      (next) => { if (seq === loadSeq) show(next).catch((err) => { error = err.message; }); },
      (err) => { if (seq === loadSeq) error = err.message; },
    );
  });

  async function act(call) {
    busy = true;
    error = '';
    try {
      await call();
    } catch (err) {
      error = err.message;
    } finally {
      busy = false;
    }
  }

  async function reload() {
    await show(await loadReview(draftId));
  }

  function sketchEdit(id) {
    return edit.sketches.find((s) => s.id === id);
  }

  function attachChoices(sketch) {
    if (sketch.kind === 'master') {
      return (body.choices.masters[sketch.skill_key] ?? []).map((m) => ({ entity_id: m.id, name: m.name }));
    }
    return body.choices.characters;
  }

  function sketchName(id) {
    return body.draft.sketches.find((s) => s.id === id)?.name ?? '?';
  }

  function factionName(id) {
    return body.draft.memberships.find((m) => m.id === id)?.faction_name ?? '?';
  }

  function payloadName(row) {
    return row.payload?.draft?.public?.name ?? '';
  }

  function payloadDescription(row) {
    return row.payload?.draft?.facets?.description ?? '';
  }

  function kept(row) {
    return row.row_status === 'proposed' || row.row_status === 'edited';
  }

  const save = () => act(async () => {
    const sent = {
      review_location_id: edit.review_location_id || null,
      sketches: edit.sketches.map((s) => ({
        id: s.id, action: s.action, entity_id: s.action === 'attach' ? (s.entity_id || null) : null,
        relation_type: s.relation_type, intensity: Number(s.intensity),
      })),
      memberships: edit.memberships,
    };
    await show(await saveReview(draftId, sent));
  });

  const prepare = (label) => act(async () => { await prepareLot(draftId, label); await reload(); });

  const generate = (lot) => act(async () => {
    await runLot(lot.batch_id, (step) => { lot.npcs_done = step.npcs_done; });
    await reload();
  });

  const rename = (lot, row, name) => act(async () => {
    await setLotRow(lot.batch_id, row.id, { payload_patch: { name } });
    await reload();
  });

  const retain = (lot, row, yes) => act(async () => {
    await setLotRow(lot.batch_id, row.id, { row_status: yes ? 'proposed' : 'rejected' });
    await reload();
  });

  const abandon = (lot) => act(async () => { await abandonLot(lot.batch_id); await reload(); });

  const sendBack = () => act(async () => { await returnDraft(draftId, note); afterReturn(); });

  const approve = () => act(async () => { await approveDraft(draftId); afterApproval(); });
</script>

<section class="pc-review">
  <h4>Revue de la créatrice</h4>
  {#if error}<div class="r-err">{error}</div>{/if}
  {#if body && edit}
    {@const draft = body.draft}
    {@const ready = body.verdict.violations.length === 0 && body.blockers.length === 0}

    <div class="block">
      <label>
        Lieu de départ
        <select bind:value={edit.review_location_id}>
          <option value="">{draft.start_location ? `${draft.start_location.name} (choix du joueur)` : '—'}</option>
          {#each body.choices.places as p (p.entity_id)}
            <option value={p.entity_id}>
              {p.name}{draft.start_location && draft.start_location.entity_id === p.entity_id ? ' (choix du joueur)' : ''}
            </option>
          {/each}
        </select>
      </label>
    </div>

    <div class="block">
      <h5>Personnes</h5>
      {#each draft.sketches as sketch (sketch.id)}
        {@const s = sketchEdit(sketch.id)}
        {#if s}
          <div class="person">
            <div>
              <strong>{sketch.name}</strong> · {KINDS[sketch.kind] ?? sketch.kind}{#if sketch.role} — {sketch.role}{/if}
            </div>
            <div class="row">
              <label><input type="radio" name={`act-${s.id}`} value="create" bind:group={s.action} /> Créer</label>
              <label><input type="radio" name={`act-${s.id}`} value="attach" bind:group={s.action} /> Rattacher</label>
              <label><input type="radio" name={`act-${s.id}`} value="drop" bind:group={s.action} /> Écarter</label>
            </div>
            {#if s.action === 'attach'}
              <select bind:value={s.entity_id}>
                <option value="">—</option>
                {#each attachChoices(sketch) as c (c.entity_id)}
                  <option value={c.entity_id}>
                    {c.name}{sketch.existing_entity && sketch.existing_entity.entity_id === c.entity_id ? ' (proposé par le joueur)' : ''}
                  </option>
                {/each}
              </select>
            {/if}
            {#if s.action === 'create' || s.action === 'attach'}
              <div class="row">
                <label>
                  Lien
                  <select bind:value={s.relation_type}>
                    {#each body.choices.relation_types as t (t)}
                      <option value={t}>{t}</option>
                    {/each}
                  </select>
                </label>
                <label>Intensité <input type="number" min="1" max="100" bind:value={s.intensity} /></label>
              </div>
            {/if}
          </div>
        {/if}
      {/each}
    </div>

    <div class="block">
      <h5>Appartenances</h5>
      {#if edit.memberships.length === 0}
        <div class="muted">Aucune.</div>
      {/if}
      {#each edit.memberships as m (m.id)}
        <label class="row">
          <input type="checkbox" checked={!m.dropped} onchange={(e) => { m.dropped = !e.currentTarget.checked; }} />
          Garder · {factionName(m.id)}
        </label>
      {/each}
    </div>

    <button class="btn" disabled={busy} onclick={save}>Enregistrer la revue</button>

    <div class="block">
      <h5>Lots</h5>
      {#if body.groups.length === 0}
        <div class="muted">Personne à créer.</div>
      {/if}
      {#each body.groups as group (group.label)}
        <div class="lot">
          <div><strong>{group.label || 'sans groupe'}</strong> · {group.sketch_ids.map(sketchName).join(', ')}</div>
          {#if !group.lot}
            <button class="btn" disabled={busy} onclick={() => prepare(group.label)}>Préparer le lot</button>
          {:else if !complete(group)}
            <div class="row">
              <button class="btn" disabled={busy} onclick={() => generate(group.lot)}>Générer</button>
              <span class="muted">{group.lot.npcs_done} / {group.lot.npcs_total}</span>
            </div>
          {:else}
            {#each lotRows[group.lot.batch_id] ?? [] as row (row.id)}
              {#if row.kind === 'draft'}
                <div class="lot-row">
                  <input type="text" value={payloadName(row)} disabled={busy}
                         onchange={(e) => rename(group.lot, row, e.currentTarget.value)} />
                  <label>
                    <input type="checkbox" checked={kept(row)} disabled={busy}
                           onchange={(e) => retain(group.lot, row, e.currentTarget.checked)} />
                    Retenir
                  </label>
                  {#if payloadDescription(row)}<div class="muted">{payloadDescription(row)}</div>{/if}
                </div>
              {/if}
            {/each}
          {/if}
          {#if group.lot}
            <button class="btn-ghost" disabled={busy} onclick={() => abandon(group.lot)}>Abandonner le lot</button>
          {/if}
        </div>
      {/each}
    </div>

    <div class="block">
      <h5>Vérification</h5>
      {#if ready}
        <div>Prêt à approuver.</div>
      {:else}
        <ul class="r-err">
          {#each body.verdict.violations as v, i (i)}<li>{v.message}</li>{/each}
          {#each body.blockers as b, i (i)}<li>{b.message}</li>{/each}
        </ul>
      {/if}
    </div>

    <div class="block">
      <label>
        Note pour le joueur
        <textarea rows="3" bind:value={note}></textarea>
      </label>
      <div class="row">
        <button class="btn" disabled={busy} onclick={sendBack}>Renvoyer au joueur</button>
        <button class="btn" disabled={busy || !ready} onclick={approve}>Approuver</button>
      </div>
    </div>
  {:else if !error}
    <div class="muted"><span class="spin">⟳</span></div>
  {/if}
</section>
