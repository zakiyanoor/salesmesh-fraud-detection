import { createContext, useContext } from "react";

export const AuthContext = createContext(null);

/** { status: "loading" | "anonymous" | "authenticated", user: { username, role } | null, notice, login, logout } */
export function useAuth() {
  return useContext(AuthContext);
}

export const SESSION_ENDED = "Your session has ended. Please sign in again.";

/** The message the sign-in page shows after a 401. */
export function noticeFor(error) {
  if (error?.status === 401) return error.message === "Account is deactivated" ? error.message : SESSION_ENDED;
  return error?.message || null;
}
