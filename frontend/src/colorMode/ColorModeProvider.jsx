import { useEffect } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { useColorScheme } from "@mui/material/styles";
import { createAppTheme } from "../theme";
import { SCHEME_STORAGE_KEY, STORAGE_KEY } from "./colorModeContext";

const theme = createAppTheme();

/** Keeps the html element's scheme (used by index.html's first-paint styles) in step with the app. */
function SyncDocumentScheme() {
  const { colorScheme } = useColorScheme();
  useEffect(() => {
    if (!colorScheme) return;
    document.documentElement.setAttribute("data-color-scheme", colorScheme);
    document.documentElement.style.colorScheme = colorScheme;
  }, [colorScheme]);
  return null;
}

/** Light and dark colour schemes; the default follows the device setting (issue #28). */
export default function ColorModeProvider({ children }) {
  return (
    <ThemeProvider
      theme={theme}
      defaultMode="system"
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
