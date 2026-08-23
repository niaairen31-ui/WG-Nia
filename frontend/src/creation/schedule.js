/* TICKET-0074 (BRIEF-0074-b). Frontend mirror of `models/schedule.py`'s
   SCHEDULE_PHASES -- no read endpoint returns the bare four-value list on
   its own (every response already carries phase-keyed rows or groups), so
   this is the ONE named source a phase <select> loops over.
   verify/checks/npc_schedule.py's R11 asserts every phase <select> under
   frontend/src/ traces back to this constant. */
export const SCHEDULE_PHASES = ['matin', 'apres-midi', 'soir', 'nuit'];

export const PHASE_LABELS = {
  matin: 'Matin',
  'apres-midi': 'Après-midi',
  soir: 'Soir',
  nuit: 'Nuit',
};
