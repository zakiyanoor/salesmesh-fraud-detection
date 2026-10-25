import { createContext, useContext } from "react";

export const LatestRunContext = createContext({ loading: true, data: null, error: null });

/** The latest detection run, fetched once per page by LatestRunProvider: { loading, data, error }. */
export function useLatestRun() {
  return useContext(LatestRunContext);
}
