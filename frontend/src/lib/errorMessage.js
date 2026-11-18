/* The one reader of a failed request's body for the creator's shell.
   FastAPI answers `detail` as a string, as an object (`{message, ...}`,
   `{failures: [...]}`) or, for a validation error, as a list of
   `{loc, msg}`. Each becomes readable text; anything else becomes
   `fallback`. Never "[object Object]". */

function validationLine(item) {
  if (!item || typeof item.msg !== 'string') return null;
  const where = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : '';
  return where ? `${where} : ${item.msg}` : item.msg;
}

export function errorMessage(body, fallback) {
  const detail = body && typeof body === 'object' ? body.detail : undefined;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const lines = detail.map(validationLine).filter(Boolean);
    if (lines.length) return lines.join(' ; ');
  } else if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message) return detail.message;
    if (Array.isArray(detail.failures)) {
      const failures = detail.failures.filter((f) => typeof f === 'string' && f);
      if (failures.length) return failures.join(' ; ');
    }
  }
  return String(fallback);
}
