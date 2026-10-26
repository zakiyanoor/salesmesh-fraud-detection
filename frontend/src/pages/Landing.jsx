import { Suspense, lazy, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, Link, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import ThemeMenu from "../components/ThemeMenu";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { HEADLINE, SECURITY_POINTS, SIGN_IN_PATH, SUBLINE } from "./landingContent";

// The globe and cobe load in their own chunk, after the first paint.
const KenyaGlobe = lazy(() => import("../components/globe/KenyaGlobe"));

const RADIUS = "6px";
const HEADER_HEIGHT = 64;
const GRID = 56;
const visuallyHidden = { position: "absolute", width: "1px", height: "1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" };

/** The space the globe will take, kept from the first paint so nothing moves when it arrives. */
function GlobeSpace({ children }) {
  const theme = useTheme();
  const dark = theme.palette.mode === "dark";
  return (
    <Box data-testid="globe-space" sx={{ position: "relative", width: "100%", maxWidth: { xs: 320, sm: 420, md: 560 }, mx: "auto", aspectRatio: "1 / 1" }}>
      {/* A soft atmosphere behind the globe only. */}
      <Box aria-hidden="true" sx={{
        position: "absolute", inset: { xs: "-6%", md: "-12%" }, borderRadius: "50%", pointerEvents: "none",
        background: `radial-gradient(circle, ${alpha(theme.palette.primary.main, dark ? 0.22 : 0.12)} 0%, ${alpha(theme.palette.primary.main, 0)} 62%)`,
      }} />
      <Box sx={{ position: "relative" }}>{children}</Box>
    </Box>
  );
}

/** The first page at the site root before sign in (issue #28). No requests of its own; the globe is decorative. */
export default function Landing() {
  useDocumentTitle(null);
  const theme = useTheme();
  const dark = theme.palette.mode === "dark";
  // Mount the globe after the first paint, so the headline and Sign in appear at once.
  const [globe, setGlobe] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setGlobe(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const line = alpha(theme.palette.text.primary, dark ? 0.1 : 0.12);
  const grid = alpha(theme.palette.text.primary, dark ? 0.035 : 0.03);
  const page = { maxWidth: 1180, mx: "auto", px: { xs: 2, sm: 4 } };
  const signIn = { component: RouterLink, to: SIGN_IN_PATH, variant: "contained", disableElevation: true, sx: { borderRadius: RADIUS } };

  return (
    <Box sx={{
      minHeight: "100vh", display: "flex", flexDirection: "column", color: "text.primary", overflowX: "clip",
      bgcolor: "background.default",
      // A faint fine grid, and in the dark scheme a navy tint toward the globe.
      backgroundImage: [
        `linear-gradient(${grid} 1px, transparent 1px)`,
        `linear-gradient(90deg, ${grid} 1px, transparent 1px)`,
        dark ? `radial-gradient(ellipse 80% 70% at 75% 40%, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.primary.main, 0)} 70%)` : "none",
      ].join(", "),
      backgroundSize: `${GRID}px ${GRID}px, ${GRID}px ${GRID}px, 100% 100%`,
    }}>
      <Box component="header" sx={{ borderBottom: `1px solid ${line}` }}>
        <Box sx={{ ...page, height: HEADER_HEIGHT, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography component="p" sx={{ fontSize: 19, fontWeight: 600, fontFamily: (t) => t.typography.h1.fontFamily }}>SalesMesh</Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Button {...signIn}>Sign in</Button>
            <ThemeMenu />
          </Box>
        </Box>
      </Box>

      <Box component="main" id="main-content" sx={{ ...page, flexGrow: 1, width: "100%", boxSizing: "border-box" }}>
        <Box sx={{
          display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) minmax(0, 1fr)" }, alignItems: "center",
          columnGap: 6, rowGap: { xs: 5, md: 0 }, pt: { xs: 7, md: 12 }, pb: { xs: 6, md: 10 },
        }}>
          <Box>
            <Typography variant="h1" sx={{ fontSize: { xs: 40, sm: 52, md: 64 }, lineHeight: 1.05, letterSpacing: "-0.02em", maxWidth: "13ch", mb: 3 }}>
              {HEADLINE}
            </Typography>
            <Typography sx={{ fontSize: { xs: 18, md: 20 }, lineHeight: 1.5, color: "text.secondary", maxWidth: "34ch", mb: 5 }}>
              {SUBLINE}
            </Typography>
            <Button {...signIn} size="large" sx={{ ...signIn.sx, px: 3.5, py: 1.25 }}>Sign in</Button>
          </Box>
          <GlobeSpace>
            {globe && (
              <Suspense fallback={null}>
                <KenyaGlobe />
              </Suspense>
            )}
          </GlobeSpace>
        </Box>

        <Box component="section" aria-labelledby="security-design" sx={{ borderTop: `1px solid ${line}`, py: { xs: 4, md: 5 } }}>
          <Typography id="security-design" component="h2" sx={visuallyHidden}>Security design</Typography>
          <Box component="ul" sx={{
            listStyle: "none", m: 0, p: 0, display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, auto)" }, justifyContent: { lg: "space-between" },
            gap: { xs: 1.5, md: 2 },
          }}>
            {SECURITY_POINTS.map((point) => (
              <Typography component="li" key={point} sx={{ fontSize: 15, color: "text.secondary" }}>{point}</Typography>
            ))}
          </Box>
        </Box>
      </Box>

      <Box component="footer" sx={{ borderTop: `1px solid ${line}` }}>
        <Box sx={{ ...page, py: 3, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography sx={{ fontSize: 15, color: "text.secondary" }}>SalesMesh Fraud Detection</Typography>
          <Link component={RouterLink} to={SIGN_IN_PATH} sx={{ fontSize: 15, color: "primary.dark", borderRadius: RADIUS }}>Sign in</Link>
        </Box>
      </Box>
    </Box>
  );
}
