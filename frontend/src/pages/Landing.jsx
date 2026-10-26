import { Suspense, lazy, useEffect, useId, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, IconButton, Link, Menu, MenuItem, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/MenuOutlined";
import ThemeMenu from "../components/ThemeMenu";
import { useAuth } from "../auth/authContext";
import { SHARED_PAGES, signInHref } from "../auth/redirect";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { CARDS, COPYRIGHT, HEADLINE, LOCATION, SECURITY_POINTS, SIGN_IN_PATH, SUBLINE, TAGLINE } from "./landingContent";

// The globe and cobe load in their own chunk, after the first paint.
const KenyaGlobe = lazy(() => import("../components/globe/KenyaGlobe"));

const RADIUS = "6px";
const HEADER_HEIGHT = 64;
const GRID = 56;
const PAGE = { maxWidth: 1180, mx: "auto", px: { xs: 2, sm: 4 }, boxSizing: "border-box", width: "100%" };

/** Page tokens from the theme: one accent, thin rules, and a light scheme that stays crisp. */
function useTokens() {
  const { palette } = useTheme();
  const dark = palette.mode === "dark";
  return {
    rule: alpha(palette.text.primary, dark ? 0.12 : 0.14),
    grid: alpha(palette.text.primary, dark ? 0.035 : 0.04),
    band: alpha(palette.primary.main, dark ? 0.06 : 0.05),
    // Light: the deeper blue (primary.dark) behind white text, for contrast on a pale page.
    accent: dark ? palette.primary.main : palette.primary.dark,
    accentText: palette.primary.contrastText,
    link: palette.primary.dark,
  };
}

/** Where a page link goes: straight there when signed in, otherwise to sign in, remembering the page. */
function useHref() {
  const { status } = useAuth();
  return (path) => (status === "authenticated" ? path : signInHref(path));
}

/** The pages every role may open; a menu button with a list on narrow screens. */
function Navigation() {
  const t = useTokens();
  const href = useHref();
  const [anchor, setAnchor] = useState(null);
  const menuId = useId();
  const linkSx = {
    fontSize: 15, color: "text.primary", textDecoration: "none", borderRadius: RADIUS, px: 1, py: 0.5,
    "&:hover": { color: t.link, textDecoration: "underline", textUnderlineOffset: "4px" },
  };
  return (
    <>
      <Box component="nav" aria-label="Main" sx={{ display: { xs: "none", md: "block" } }}>
        <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, display: "flex", gap: 1 }}>
          {SHARED_PAGES.map((page) => (
            <li key={page.key}><Link component={RouterLink} to={href(page.path)} sx={linkSx}>{page.label}</Link></li>
          ))}
        </Box>
      </Box>
      <Box sx={{ display: { xs: "block", md: "none" } }}>
        <IconButton
          aria-label="Open navigation"
          aria-haspopup="true"
          aria-controls={anchor ? menuId : undefined}
          aria-expanded={anchor ? "true" : "false"}
          onClick={(e) => setAnchor(e.currentTarget)}
          size="small"
        >
          <MenuIcon fontSize="small" />
        </IconButton>
        <Menu id={menuId} anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)} slotProps={{ list: { "aria-label": "Main" } }}>
          {SHARED_PAGES.map((page) => (
            <MenuItem key={page.key} component={RouterLink} to={href(page.path)} onClick={() => setAnchor(null)}>{page.label}</MenuItem>
          ))}
        </Menu>
      </Box>
    </>
  );
}

/** The space the globe will take, kept from the first paint so nothing moves when it arrives. */
function GlobeSpace({ children }) {
  return (
    <Box data-testid="globe-space" sx={{ position: "relative", width: "100%", maxWidth: { xs: 320, sm: 420, md: 520 }, mx: "auto", aspectRatio: "1 / 1" }}>
      {children}
    </Box>
  );
}

function FooterGroup({ title, children }) {
  return (
    <Box>
      <Typography component="h2" sx={{ fontSize: 14, fontWeight: 600, mb: 1.5 }}>{title}</Typography>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, display: "grid", gap: 1 }}>{children}</Box>
    </Box>
  );
}

/** The first page at the site root before sign in (issue #28). No requests of its own; the globe is decorative. */
export default function Landing() {
  useDocumentTitle(null);
  const t = useTokens();
  const href = useHref();
  // Mount the globe after the first paint, so the headline and Sign in appear at once.
  const [globe, setGlobe] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setGlobe(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const signIn = {
    component: RouterLink, to: SIGN_IN_PATH, variant: "contained", disableElevation: true,
    sx: { borderRadius: RADIUS, bgcolor: t.accent, color: t.accentText, "&:hover": { bgcolor: t.link } },
  };
  const footerLink = { fontSize: 14, color: t.link, borderRadius: RADIUS, textUnderlineOffset: "3px" };

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column", bgcolor: "background.default", color: "text.primary", overflowX: "clip" }}>
      <Box component="header" sx={{ borderBottom: `1px solid ${t.rule}`, bgcolor: "background.default" }}>
        <Box sx={{ ...PAGE, height: HEADER_HEIGHT, display: "flex", alignItems: "center", gap: { xs: 1, md: 3 } }}>
          <Typography component="p" sx={{ fontSize: 19, fontWeight: 600, fontFamily: (th) => th.typography.h1.fontFamily, mr: { md: 2 } }}>SalesMesh</Typography>
          <Box sx={{ flexGrow: 1, display: "flex", justifyContent: { xs: "flex-end", md: "flex-start" } }}>
            <Navigation />
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Button {...signIn}>Sign in</Button>
            <ThemeMenu />
          </Box>
        </Box>
      </Box>

      <Box component="main" id="main-content" sx={{ flexGrow: 1 }}>
        {/* A lightly tinted band with a faint grid behind the hero. */}
        <Box sx={{
          borderBottom: `1px solid ${t.rule}`, bgcolor: t.band,
          backgroundImage: `linear-gradient(${t.grid} 1px, transparent 1px), linear-gradient(90deg, ${t.grid} 1px, transparent 1px)`,
          backgroundSize: `${GRID}px ${GRID}px`,
        }}>
          <Box sx={{
            ...PAGE, display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) minmax(0, 1fr)" },
            alignItems: "center", columnGap: 6, rowGap: { xs: 5, md: 0 }, pt: { xs: 6, md: 10 }, pb: { xs: 6, md: 10 },
          }}>
            <Box>
              <Typography variant="h1" sx={{ fontSize: { xs: 40, sm: 52, md: 64 }, lineHeight: 1.05, letterSpacing: "-0.02em", maxWidth: "13ch", mb: 3, color: "text.primary" }}>
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
        </Box>

        <Box component="section" aria-labelledby="platform-title" sx={{ ...PAGE, py: { xs: 6, md: 9 } }}>
          <Typography id="platform-title" component="h2" sx={{ fontSize: { xs: 22, md: 26 }, fontWeight: 600, fontFamily: (th) => th.typography.h2.fontFamily, mb: 3 }}>
            What the platform does
          </Typography>
          {/* A ruled grid: the cards share their borders, with no shadows. */}
          <Box component="ul" sx={{
            listStyle: "none", m: 0, p: 0, display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
            gap: "1px", bgcolor: t.rule, border: `1px solid ${t.rule}`, borderRadius: RADIUS, overflow: "hidden",
          }}>
            {CARDS.map(([title, text], i) => (
              <Box component="li" key={title} sx={{ bgcolor: "background.paper", p: { xs: 2.5, md: 3 } }}>
                <Typography aria-hidden="true" sx={{ fontFamily: (th) => th.typography.fontFamilyMono, fontSize: 13, color: "text.secondary", mb: 1.5 }}>
                  {String(i + 1).padStart(2, "0")}
                </Typography>
                <Typography component="h3" sx={{ fontSize: 18, fontWeight: 600, fontFamily: (th) => th.typography.h3.fontFamily, mb: 1 }}>{title}</Typography>
                <Typography sx={{ fontSize: 15, lineHeight: 1.6, color: "text.secondary" }}>{text}</Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </Box>

      <Box component="footer" sx={{ borderTop: `1px solid ${t.rule}` }}>
        <Box sx={{
          ...PAGE, pt: { xs: 5, md: 6 }, pb: 4, display: "grid", gap: { xs: 4, md: 6 },
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "1.4fr 1fr 1fr 1fr" },
        }}>
          <Box>
            <Typography component="p" sx={{ fontSize: 17, fontWeight: 600, fontFamily: (th) => th.typography.h1.fontFamily }}>SalesMesh</Typography>
            <Typography sx={{ fontSize: 14, color: "text.secondary", mt: 0.75, maxWidth: "32ch" }}>{TAGLINE}</Typography>
          </Box>
          <nav aria-label="Platform">
            <FooterGroup title="Platform">
              {SHARED_PAGES.map((page) => (
                <li key={page.key}><Link component={RouterLink} to={href(page.path)} sx={footerLink}>{page.label}</Link></li>
              ))}
            </FooterGroup>
          </nav>
          <nav aria-label="Access">
            <FooterGroup title="Access">
              <li><Link component={RouterLink} to={SIGN_IN_PATH} sx={footerLink}>Sign in</Link></li>
              <li><Link component={RouterLink} to={href("/how-it-works")} sx={footerLink}>How the model works</Link></li>
            </FooterGroup>
          </nav>
          <FooterGroup title="Security">
            {SECURITY_POINTS.map((point) => (
              <Typography component="li" key={point} sx={{ fontSize: 14, color: "text.secondary" }}>{point}</Typography>
            ))}
          </FooterGroup>
        </Box>
        <Box sx={{ borderTop: `1px solid ${t.rule}` }}>
          <Box sx={{ ...PAGE, py: 2.5, display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{COPYRIGHT}</Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{LOCATION}</Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
