/* TICKET-0129 (BRIEF-0129-G, C-17, K1-b). The profile a player character
   belongs to: a player profile, or the creator. Every call goes through
   `api` (sheetRequest.svelte.js). */

import { api } from './sheetRequest.svelte.js';

export function loadProfiles(characterId) {
  return api(`/api/pc-profiles?character_id=${encodeURIComponent(characterId)}`);
}

export function setProfile(characterId, profileId) {
  return api(`/api/pc-profiles/${encodeURIComponent(characterId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId }),
  });
}
