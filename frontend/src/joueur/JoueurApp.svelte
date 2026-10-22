<script>
  /* TICKET-0125 (BRIEF-0125-G, P1). The player shell's root: no profile ->
     ProfilePicker; no world -> WorldList; else WorldPage. */
  import ProfilePicker from './ProfilePicker.svelte';
  import WorldList from './WorldList.svelte';
  import WorldPage from './WorldPage.svelte';
  import { joueurState, chooseProfile, restoreProfile } from './joueur.svelte.js';

  restoreProfile();
</script>

<main class="joueur">
  {#if joueurState.profile}
    <header class="joueur-head">
      <span>Joueur : {joueurState.profile.name}</span>
      <button onclick={() => chooseProfile(null)}>Changer de joueur</button>
    </header>
    {#if joueurState.world}
      <WorldPage />
    {:else}
      <WorldList />
    {/if}
  {:else}
    <ProfilePicker />
  {/if}
</main>

<style>
  .joueur { max-width: 760px; margin: 0 auto; padding: 16px; }
  .joueur-head { display: flex; justify-content: space-between; align-items: center; gap: 8px;
    border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }
</style>
