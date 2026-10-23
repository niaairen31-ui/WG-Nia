<script>
  /* TICKET-0125 (BRIEF-0125-G, K1). Choose or create a player profile; the
     server's 422/409 messages are shown as returned. */
  import { joueurState, chooseProfile, createProfile } from './joueur.svelte.js';

  let name = $state('');
</script>

<section class="profile-picker">
  <h1>Qui joue ?</h1>
  {#if joueurState.profiles.length > 0}
    <div class="profile-list">
      {#each joueurState.profiles as profile (profile.id)}
        <button onclick={() => chooseProfile(profile)}>{profile.name}</button>
      {/each}
    </div>
  {/if}
  <div class="profile-create">
    <input bind:value={name} placeholder="Nom du joueur" maxlength="80" />
    <button disabled={!name.trim()} onclick={() => createProfile(name)}>Créer</button>
  </div>
  {#if joueurState.error}
    <div class="r-err">{joueurState.error}</div>
  {/if}
</section>

<style>
  .profile-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .profile-create { display: flex; gap: 6px; }
  .r-err { color: var(--red); margin-top: 6px; }
</style>
