/* TICKET-0115 (BRIEF-0115-E). State and requests of the « Suivi » island
   (Dashboard.svelte): the creator's dashboard -- every metric of
   `dashboard_metrics.METRICS` and the deferral registry, for one world or
   all of them, between two real-world days (GET /api/dashboard) -- and its
   export, the same scope as a JSON file to save
   (GET /api/dashboard/export). Reads only. */
import { api } from './sheetRequest.svelte.js';

export const dashboardState = $state({
  world: 'all',
  since: '',
  until: '',
  worlds: [],
  metrics: [],
  deferrals: [],
  loading: false,
  loadError: '',
  exporting: false,
  exportError: '',
});

function query() {
  const params = new URLSearchParams({ world: dashboardState.world });
  if (dashboardState.since) params.set('since', dashboardState.since);
  if (dashboardState.until) params.set('until', dashboardState.until);
  return params.toString();
}

export async function loadDashboard() {
  dashboardState.loading = true;
  dashboardState.loadError = '';
  try {
    const data = await api('/api/dashboard?' + query());
    dashboardState.worlds = data.worlds;
    dashboardState.metrics = data.metrics;
    dashboardState.deferrals = data.deferrals;
  } catch (e) {
    dashboardState.loadError = e.message;
  } finally {
    dashboardState.loading = false;
  }
}

/** Fetch the export and hand it to the browser as a file to save. */
export async function exportDashboard() {
  dashboardState.exporting = true;
  dashboardState.exportError = '';
  try {
    const res = await fetch('/api/dashboard/export?' + query());
    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(data.detail || res.statusText);
    }
    const disposition = res.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="([^"]+)"/);
    const url = URL.createObjectURL(await res.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = match ? match[1] : 'suivi.json';
    link.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    dashboardState.exportError = e.message;
  } finally {
    dashboardState.exporting = false;
  }
}

/** « 3 / 5 (60 %) », or the value alone. */
export function share(row) {
  if (row.of === null || row.of === undefined) return String(row.value);
  if (!row.of) return `${row.value} / 0`;
  return `${row.value} / ${row.of} (${Math.round((100 * row.value) / row.of)} %)`;
}
