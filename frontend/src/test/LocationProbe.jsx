import { useLocation } from "react-router-dom";

/** Renders the router address so tests can read it (see currentLocation in server.jsx). */
export default function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location" hidden>{`${location.pathname}${location.search}`}</output>;
}
