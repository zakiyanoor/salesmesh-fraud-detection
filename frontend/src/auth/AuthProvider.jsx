import { useCallback, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler } from "../api";
import { AuthContext, noticeFor } from "./authContext";

const SIGNED_OUT = { status: "anonymous", user: null, notice: null };

// Only the username and role are kept, in memory. The session itself is the server's HTTP-only cookie.
export default function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "loading", user: null, notice: null });

  useEffect(() => {
    let active = true;
    api
      .me()
      .then(({ username, role }) => active && setState({ status: "authenticated", user: { username, role }, notice: null }))
      .catch((error) => {
        if (!active) return;
        // No session is the normal signed-out state; anything else gets a message.
        const quiet = error.status === 401 && error.message === "Authentication required";
        setState({ ...SIGNED_OUT, notice: quiet ? null : noticeFor(error) });
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => setUnauthorizedHandler((error) => setState({ ...SIGNED_OUT, notice: noticeFor(error) })), []);

  const login = useCallback(async (username, password) => {
    const { username: name, role } = await api.login(username, password);
    setState({ status: "authenticated", user: { username: name, role }, notice: null });
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // The client signs out whatever the server answered.
    } finally {
      setState(SIGNED_OUT);
    }
  }, []);

  const value = useMemo(() => ({ ...state, login, logout }), [state, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
