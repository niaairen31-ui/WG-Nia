<script>
  /* TICKET-0058 (BRIEF-0058-d). Pilot island: a faithful port of the legacy
     constructeurRender/OnNameInput/OnSlugInput/Submit/ResetForm cluster
     (index.html, now deleted). No shared state with the sheet engine --
     this component fetches its own copy of GET /api/entity-types rather
     than reading the legacy `authorRegistry` global, exactly like the
     relations graph consumer does for its own needs (TICKET-0058,
     BRIEF-0058-c).

     `primaryAction` is exported so frontend/src/creation/mount.js can
     invoke it when the legacy shell's standard action band forwards a
     click via the generic `island:action` seam -- the container this
     component mounts into (#creation-constructeur) has never held its own
     submit control; the trigger has always lived in the shared shell,
     outside the mount target, so it stays there.

     No scoped <style> block: like Graph.svelte, this renders inside the
     legacy iframe document, where Svelte's shell-injected scoped CSS never
     reaches. Markup reuses the legacy document's own classes/CSS vars. */
  import { serverState } from '../lib/serverState.svelte.js';

  let { legacyDoc } = $props();

  let name = $state('');
  let slug = $state('');
  let slugTouched = $state(false);
  let traits = $state([]);
  let checkedTraits = $state(new Set());
  let status = $state({ kind: null, text: '' });

  function slugify(value) {
    return value
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  function onNameInput() {
    if (!slugTouched) slug = slugify(name);
  }

  function onSlugInput() {
    slugTouched = true;
  }

  function toggleTrait(key, checked) {
    const next = new Set(checkedTraits);
    if (checked) next.add(key); else next.delete(key);
    checkedTraits = next;
  }

  async function api(path, options) {
    const res = await fetch(path, options);
    if (!res.ok) {
      let msg = `${path} -> ${res.status}`;
      try {
        const body = await res.json();
        if (body && typeof body.detail === 'string') msg = body.detail;
      } catch (_err) {
        // response body wasn't JSON -- keep the status-based message
      }
      throw new Error(msg);
    }
    return res.json();
  }

  async function loadTraits() {
    try {
      const registry = await api('/api/entity-types');
      traits = registry.checkable_traits || [];
    } catch (err) {
      status = { kind: 'error', text: err.message };
    }
  }

  // The active world is server-authoritative (serverState mirrors it,
  // TICKET-0056 C3); this island resets its own form when it changes
  // rather than being told to by a legacy onWorldSwitch callback
  // (RECON-0058-a M5 -- the legacy reset path is exactly what destroyed a
  // mounted island on every world switch).
  $effect(() => {
    void serverState.worldId;
    name = '';
    slug = '';
    slugTouched = false;
    checkedTraits = new Set();
    status = { kind: null, text: '' };
    loadTraits();
  });

  export async function primaryAction() {
    const trimmedName = name.trim();
    const trimmedSlug = slug.trim();
    if (!trimmedName || !trimmedSlug) {
      status = { kind: 'error', text: 'Nom et slug requis.' };
      return;
    }
    status = { kind: 'spin', text: '' };
    try {
      const result = await api('/api/entity-types', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmedName, slug: trimmedSlug, trait_keys: Array.from(checkedTraits) }),
      });
      status = { kind: 'success', text: `Type « ${result.slug} » créé (${result.physical_table}).` };
      // Reverse direction: the legacy tab bar is still legacy-owned under
      // A1 (TICKET-0058), so this island signals it rather than reaching
      // in directly -- the one CustomEvent the legacy document listens for
      // (index.html, BRIEF-0058-d). legacyDoc, not the bare `document`
      // global: this component's script runs in the shell's realm, not
      // the legacy iframe's (mirrors Graph.svelte's ownerDocument note).
      legacyDoc.dispatchEvent(new CustomEvent('creation:refresh-tabs'));
    } catch (err) {
      status = { kind: 'error', text: err.message };
    }
  }
</script>

<div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px; max-width:480px;">
  <div class="field-section-title">Nouveau type</div>
  <div class="field-row">
    <label for="constructeur-name">Nom</label>
    <input type="text" id="constructeur-name" bind:value={name} oninput={onNameInput}>
  </div>
  <div class="field-row">
    <label for="constructeur-slug">Slug</label>
    <input type="text" id="constructeur-slug" bind:value={slug} oninput={onSlugInput}>
  </div>
  <div class="field-section-title" style="margin-top:10px">Traits</div>
  {#if traits.length === 0}
    <div class="empty">Aucun trait cochable.</div>
  {:else}
    {#each traits as t (t.key)}
      <label style="display:flex; align-items:center; gap:6px; font-size:13px; margin:4px 0">
        <input
          type="checkbox"
          checked={checkedTraits.has(t.key)}
          onchange={(e) => toggleTrait(t.key, e.currentTarget.checked)}
        > {t.label}
      </label>
    {/each}
  {/if}
  <div id="constructeur-status" class="author-status" style="margin-top:8px">
    {#if status.kind === 'spin'}<span class="spin">⟳</span>{/if}
    {#if status.kind === 'success'}<span style="color:var(--green)">{status.text}</span>{/if}
    {#if status.kind === 'error'}<span style="color:var(--red)">{status.text}</span>{/if}
  </div>
</div>
