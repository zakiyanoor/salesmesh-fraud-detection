import { useMemo, useState } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { createAppTheme } from "../theme";
import { ColorModeContext, readStoredMode, storeMode } from "./colorModeContext";

export default function ColorModeProvider({ children }) {
  const [mode, setMode] = useState(readStoredMode);
  const value = useMemo(
    () => ({
      mode,
      toggle: () =>
        setMode((current) => {
          const next = current === "dark" ? "light" : "dark";
          storeMode(next);
          return next;
        }),
    }),
    [mode],
  );
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
