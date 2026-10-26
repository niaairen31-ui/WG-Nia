<script>
  /* TICKET-0129 (BRIEF-0129-G, C-17, K1-b). The « Joueur » field of a
     player character's skill pane: « Créatrice » or a player profile; a
     change saves at once, a refusal shows the server's message in place.
     No scoped <style> block: it renders inside the legacy document, as
     PjSkillFiche does. */
  import { loadProfiles, setProfile } from './pcProfiles.svelte.js';

  let { characterId } = $props();

  let profiles = $state([]);
  let current = $state('');
  let error = $state('');
  let busy = $state(false);

  function take(body) {
    profiles = body.profiles;
    current = body.current_profile_id ?? '';
  }

  $effect(() => {
    const id = characterId;
    error = '';
    loadProfiles(id).then(take).catch((e) => { error = e.message; });
  });

  async function onChange(event) {
    const value = event.currentTarget.value;
    busy = true;
    error = '';
    try {
      take(await setProfile(characterId, value || null));
    } catch (e) {
      error = e.message;
      event.currentTarget.value = current;
    } finally {
      busy = false;
    }
  }
</script>

<label class="field-row" style="margin:6px 0">
  <span style="font-size:12px">Joueur</span>
  <select value={current} onchange={onChange} disabled={busy}>
    <option value="">Créatrice</option>
    {#each profiles as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
  </select>
</label>
{#if error}<div class="empty">{error}</div>{/if}
