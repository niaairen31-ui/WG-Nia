import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [svelte()],
  base: '/static/',
  build: {
    outDir: '../src/world_engine/cockpit/static',
    emptyOutDir: true,
    rollupOptions: {
      // TICKET-0125 (P1): the player shell is a second page with its own
      // bundle, never the creator shell.
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        jouer: fileURLToPath(new URL('./jouer.html', import.meta.url)),
      },
      // TICKET-0055 D3: cytoscape stays vendored and is served by the
      // pre-existing GET /vendor/{filename} route. The bundler must never
      // own it. Which engine sits under the graph primitive is TICKET-0057.
      external: ['cytoscape'],
    },
  },
});
