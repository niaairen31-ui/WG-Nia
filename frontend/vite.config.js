import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  base: '/static/',
  build: {
    outDir: '../src/world_engine/cockpit/static',
    emptyOutDir: true,
    rollupOptions: {
      // TICKET-0055 D3: cytoscape stays vendored and is served by the
      // pre-existing GET /vendor/{filename} route. The bundler must never
      // own it. Which engine sits under the graph primitive is TICKET-0057.
      external: ['cytoscape'],
    },
  },
});
