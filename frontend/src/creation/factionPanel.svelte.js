/* TICKET-0058 (BRIEF-0058-g, family b). Shared state + mutation functions
   for the faction roles editor and roster panel -- RolesEditor.svelte and
   FactionRoster.svelte both read/write this one store rather than each
   re-fetching, mirroring the legacy globals (authorFactionRolesDraft/
   authorFactionRolesLive/authorFactionRolesUndeclared/authorFactionRosterRows/
   authorFactionRosterEditingId, index.html, now deleted) they replace.

   loadFactionMembersPanel is the sequencing wrapper TICKET-0054/BRIEF-0054-c
   introduced (authorLoadFactionMembersPanel, also deleted): the roster's
   grouped render needs the declared-role list in memory BEFORE it runs, so
   Sheet.svelte's own async tail calls this instead of a two-step legacyCall
   pair -- roles load first, same as before, just as a plain import instead
   of a cross-realm bridge call. */
export const factionPanelState = $state({
  // isNew-mode draft rows (name/description/limit), read directly by
  // Sheet.svelte's submitEntity at faction-creation time -- replaces
  // _authorFactionRolesDraftForCreate's legacyCall round-trip.
  draftRoles: [],
  rolesLive: [],
  rolesUndeclared: [],
  rosterRows: [],
  rosterEditingId: null,
});

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

export function resetDraftRoles() {
  factionPanelState.draftRoles = [];
}

export function draftRolesForCreate() {
  return factionPanelState.draftRoles
    .map((r) => ({ name: (r.name || '').trim(), description: r.description || null, max_holders: r.limit ?? null }))
    .filter((r) => r.name);
}

export async function loadFactionRoles(factionId) {
  const data = await api(`/api/factions/${encodeURIComponent(factionId)}/roles`);
  factionPanelState.rolesLive = data.roles || [];
  factionPanelState.rolesUndeclared = data.undeclared_active_roles || [];
}

export async function loadFactionRoster(factionId) {
  const rows = await api(`/api/entities/${encodeURIComponent(factionId)}/faction-roster`);
  factionPanelState.rosterRows = rows || [];
  factionPanelState.rosterEditingId = null;
}

export async function loadFactionMembersPanel(factionId) {
  await loadFactionRoles(factionId);
  await loadFactionRoster(factionId);
}

export async function createFactionRole(factionId, { name, description, max_holders }) {
  await api(`/api/factions/${encodeURIComponent(factionId)}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, max_holders }),
  });
  await loadFactionRoles(factionId);
}

export async function updateFactionRole(factionId, roleId, { description, max_holders }) {
  await api(`/api/factions/${encodeURIComponent(factionId)}/roles/${encodeURIComponent(roleId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description, max_holders }),
  });
  await loadFactionRoles(factionId);
}

export async function renameFactionRole(factionId, roleId, { name, description, max_holders }) {
  await api(`/api/factions/${encodeURIComponent(factionId)}/roles/${encodeURIComponent(roleId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, max_holders }),
  });
  await loadFactionRoles(factionId);
}

export async function moveFactionRole(factionId, i, dir) {
  const j = i + dir;
  if (j < 0 || j >= factionPanelState.rolesLive.length) return;
  const ids = factionPanelState.rolesLive.map((r) => r.id);
  [ids[i], ids[j]] = [ids[j], ids[i]];
  await api(`/api/factions/${encodeURIComponent(factionId)}/roles/reorder`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role_ids: ids }),
  });
  await loadFactionRoles(factionId);
}

export async function deleteFactionRole(factionId, roleId) {
  await api(`/api/factions/${encodeURIComponent(factionId)}/roles/${encodeURIComponent(roleId)}`, { method: 'DELETE' });
  await loadFactionRoles(factionId);
}

export async function declareFactionRole(factionId, name) {
  await api(`/api/factions/${encodeURIComponent(factionId)}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: null, max_holders: null }),
  });
  await loadFactionRoles(factionId);
}

export async function addFactionMember(factionId, entityId, { role, cover_role, is_primary, is_secret }) {
  await api(`/api/entities/${encodeURIComponent(entityId)}/memberships`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ faction_id: factionId, role, cover_role, is_primary, is_secret }),
  });
  await loadFactionMembersPanel(factionId);
}

export async function memberRoleEditSubmit(factionId, membershipId, role) {
  await api(`/api/memberships/${encodeURIComponent(membershipId)}/role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
  await loadFactionMembersPanel(factionId);
}
