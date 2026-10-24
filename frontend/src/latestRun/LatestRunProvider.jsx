import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api";
import { LatestRunContext } from "./latestRunContext";

/**
 * Fetches GET /api/detection-runs/latest once per page and shares it, so the Overview card and the
 * footer make one request between them (issue #28). It refreshes on each navigation and keeps the
 * previous answer on screen until the new one arrives.
 */
export default function LatestRunProvider({ children }) {
  const { pathname } = useLocation();
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    api.getLatestDetectionRun().then(
      (data) => active && setState({ loading: false, data, error: null }),
      (error) => active && setState({ loading: false, data: null, error }),
    );
    return () => {
      active = false;
    };
  }, [pathname]);

  return <LatestRunContext.Provider value={state}>{children}</LatestRunContext.Provider>;
}
