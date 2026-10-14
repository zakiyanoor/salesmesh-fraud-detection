import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Page state kept in the URL query string, so a refresh or Back restores it.
 * defaults must be a stable object (module level). Values equal to their default are left out of the URL.
 */
export function useQueryParams(defaults) {
  const [params, setParams] = useSearchParams();

  const values = useMemo(
    () => Object.fromEntries(Object.entries(defaults).map(([key, fallback]) => [key, params.get(key) ?? fallback])),
    [params, defaults],
  );

  const update = useCallback(
    (changes) =>
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const [key, value] of Object.entries(changes)) {
            if (value === null || value === undefined || value === "" || String(value) === String(defaults[key])) {
              next.delete(key);
            } else {
              next.set(key, String(value));
            }
          }
          return next;
        },
        { replace: true },
      ),
    [setParams, defaults],
  );

  return [values, update];
}
