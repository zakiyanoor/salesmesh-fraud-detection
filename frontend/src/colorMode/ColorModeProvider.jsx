import { useEffect, useLayoutEffect } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { useColorScheme } from "@mui/material/styles";
import { createAppTheme } from "../theme";
import { DEFAULT_MODE, MODES, SCHEME_STORAGE_KEY, STORAGE_KEY } from "./colorModeContext";

const theme = createAppTheme();

/**
 * Keeps the html element's scheme (used by index.html's first-paint styles) in step with the app, and turns a
 * stored mode that is not light or dark (an old "system") into light before the first paint.
 */
function SyncDocumentScheme() {
  const { mode, setMode, colorScheme } = useColorScheme();
  useLayoutEffect(() => {
    if (mode && !MODES.includes(mode)) setMode(DEFAULT_MODE);
  }, [mode, setMode]);
  useEffect(() => {
    if (!colorScheme) return;
    document.documentElement.setAttribute("data-color-scheme", colorScheme);
    document.documentElement.style.colorScheme = colorScheme;
  }, [colorScheme]);
  return null;
}

/** Light and dark colour schemes, light by default (issue #28). */
export default function ColorModeProvider({ children }) {
  return (
    <ThemeProvider
      theme={theme}
      defaultMode={DEFAULT_MODE}
      modeStorageKey={STORAGE_KEY}
      colorSchemeStorageKey={SCHEME_STORAGE_KEY}
      noSsr
      disableTransitionOnChange
    >
      <CssBaseline />
      <SyncDocumentScheme />
      {children}
    </ThemeProvider>
  );
}
