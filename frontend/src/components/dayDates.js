// Dates typed as day/month/year (issue #28): the audit log and report filters show and accept dd/mm/yyyy, and
// send the API its ISO format (YYYY-MM-DD).

const DAY_MONTH_YEAR = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;

/** "27/10/2026" -> "2026-10-27"; "" -> ""; anything that is not a real date -> null. */
export function toIsoDay(text) {
  const value = (text || "").trim();
  if (!value) return "";
  const match = DAY_MONTH_YEAR.exec(value);
  if (!match) return null;
  const [day, month, year] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** "2026-10-27" -> "27/10/2026"; anything else is returned as it is. */
export function fromIsoDay(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : iso || "";
}

/**
 * Checks a From and To pair typed as dd/mm/yyyy: { from, to } in ISO when both are valid, plus an error
 * message for each field that is not ({ fromError, toError }).
 */
export function checkDayRange(fromText, toText) {
  const from = toIsoDay(fromText);
  const to = toIsoDay(toText);
  const result = { from, to, fromError: null, toError: null };
  if (from === null) result.fromError = "Enter a real date as dd/mm/yyyy.";
  if (to === null) result.toError = "Enter a real date as dd/mm/yyyy.";
  if (from && to && from > to) result.toError = "The To date must be on or after the From date.";
  return result;
}
