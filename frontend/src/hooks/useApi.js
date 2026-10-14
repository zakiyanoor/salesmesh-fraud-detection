import { useCallback, useEffect, useState } from "react";

/**
 * Runs load() (a stable function: module level or useCallback) and returns
 * { loading, data, error, retry }. A 401 is handled by the auth provider.
 */
export function useApi(load) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState({ load: null, attempt: -1, data: null, error: null });

  useEffect(() => {
    let active = true;
    load().then(
      (data) => active && setResult({ load, attempt, data, error: null }),
      (error) => active && setResult({ load, attempt, data: null, error }),
    );
    return () => {
      active = false;
    };
  }, [load, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const current = result.load === load && result.attempt === attempt;
  return { loading: !current, data: current ? result.data : null, error: current ? result.error : null, retry };
}
