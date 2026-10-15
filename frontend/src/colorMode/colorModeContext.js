import { createContext, useContext } from "react";

export const STORAGE_KEY = "salesmesh.colorMode";

export const ColorModeContext = createContext({ mode: "light", toggle: () => {} });

export function useColorMode() {
  return useContext(ColorModeContext);
}

/** The saved preference, or "light". Storage can be missing or blocked, so every access is guarded. */
export function readStoredMode() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function storeMode(mode) {
  try {
    window.localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // Not saved; the choice still applies until the page is reloaded.
  }
}
