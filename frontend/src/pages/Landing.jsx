import { Suspense, lazy, useEffect, useId, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, IconButton, Link, Menu, MenuItem, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/MenuOutlined";
import ThemeMenu from "../components/ThemeMenu";
import { useAuth } from "../auth/authContext";
import { SHARED_PAGES, signInHref } from "../auth/redirect";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import PlatformCards from "./PlatformCards";
import { GRID_STEP, RADIUS, TEXTURE_STEP, accentButtonSx, linkSx, useSurface } from "./surfaces";
import { CARDS, COPYRIGHT, HEADLINE, LOCATION, SECURITY_POINTS, SIGN_IN_PATH, SUBLINE, TAGLINE } from "./landingContent";

// The globe and cobe load in their own chunk, after the first paint.
const KenyaGlobe = lazy(() => import("../components/globe/KenyaGlobe"));

const HEADER_HEIGHT = 64;
const PAGE = { maxWidth: 1180, mx: "auto", px: { xs: 2, sm: 4 }, boxSizing: "border-box", width: "100%" };

/** Where a page link goes: straight there when signed in, otherwise to sign in, remembering the page. */
function useHref() {
  const { status } = useAuth();
  return (path) => (status === "authenticated" ? path : signInHref(path));
}

/** The pages every role may open; a menu button with a list on narrow screens. */
function Navigation() {
  const t = useSurface();
  const href = useHref();
  const [anchor, setAnchor] = useState(null);
  const menuId = useId();
  const navLink = { ...linkSx(t, { color: "text.primary" }), fontSize: 15, fontWeight: 500, px: 1, py: 0.5, display: "inline-block" };
  return (
    <>
      <Box component="nav" aria-label="Main" sx={{ display: { xs: "none", md: "block" } }}>
        <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, display: "flex", gap: 1.5 }}>
          {SHARED_PAGES.map((page) => (
            <li key={page.key}><Link component={RouterLink} to={href(page.path)} sx={navLink}>{page.label}</Link></li>
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
          sx={{ color: "text.primary", "&:hover": { bgcolor: alpha(t.accent, 0.08) } }}
        >
          <MenuIcon fontSize="small" />
        </IconButton>
        <Menu id={menuId} anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}
          slotProps={{ list: { "aria-label": "Main" }, paper: { sx: { borderRadius: RADIUS, border: `1px solid ${t.ruleStrong}`, boxShadow: "none", mt: 0.5 } } }}>
          {SHARED_PAGES.map((page) => (
            <MenuItem key={page.key} component={RouterLink} to={href(page.path)} onClick={() => setAnchor(null)}
              sx={{ "&:hover, &.Mui-focusVisible": { bgcolor: alpha(t.accent, 0.08), color: t.link } }}>
              {page.label}
            </MenuItem>
          ))}
        </Menu>
      </Box>
    </>
  );
}

/** The space the globe will take, kept from the first paint so nothing moves when it arrives. */
function GlobeSpace({ children }) {
  const t = useSurface();
  return (
    <Box data-testid="globe-space" sx={{ position: "relative", width: "100%", maxWidth: { xs: 320, sm: 420, md: 520 }, mx: "auto", aspectRatio: "1 / 1" }}>
      {/* A soft contact shadow, so the dark sphere sits on the page. */}
      <Box aria-hidden="true" sx={{
        position: "absolute", left: "18%", right: "18%", bottom: "-5%", height: "9%", borderRadius: "50%",
        bgcolor: t.dark ? alpha("#000000", 0.55) : alpha("#0B1A33", 0.22), filter: "blur(12px)",
      }} />
      {children}
    </Box>
  );
}

function FooterGroup({ title, children }) {
  return (
    <Box>
      <Typography component="h2" sx={{ fontSize: 13, fontWeight: 600, mb: 1.75, color: "text.primary" }}>{title}</Typography>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, display: "grid", gap: 1.25 }}>{children}</Box>
    </Box>
  );
}

/** The first page at the site root before sign in (issue #28). No requests of its own; the globe is decorative. */
export default function Landing() {
  useDocumentTitle(null);
  const t = useSurface();
  const href = useHref();
  // Mount the globe after the first paint, so the headline and Sign in appear at once.
  const [globe, setGlobe] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setGlobe(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const signIn = { component: RouterLink, to: SIGN_IN_PATH, variant: "contained", disableElevation: true, sx: accentButtonSx(t) };

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column", bgcolor: "background.default", color: "text.primary", overflowX: "clip" }}>
      <Box component="header" sx={{ borderBottom: `1px solid ${t.rule}`, bgcolor: "background.default" }}>
        <Box sx={{ ...PAGE, height: HEADER_HEIGHT, display: "flex", alignItems: "center", gap: { xs: 1, md: 3 } }}>
          <Typography component="p" sx={{ fontSize: 19, fontWeight: 600, letterSpacing: "-0.01em", fontFamily: (th) => th.typography.h1.fontFamily, mr: { md: 2 } }}>SalesMesh</Typography>
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
        {/* The hero: a lightly tinted band with a fine dot texture and a rule under it. */}
        <Box sx={{
          borderBottom: `1px solid ${t.rule}`, bgcolor: t.band,
          backgroundImage: t.texture, backgroundSize: `${TEXTURE_STEP}px ${TEXTURE_STEP}px`,
        }}>
          <Box sx={{
            ...PAGE, display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) minmax(0, 1fr)" },
            alignItems: "center", columnGap: 6, rowGap: { xs: 6, md: 0 }, pt: { xs: 6, md: 10 }, pb: { xs: 8, md: 11 },
          }}>
            <Box>
              <Typography variant="h1" sx={{ fontSize: { xs: 40, sm: 52, md: 64 }, lineHeight: 1.04, letterSpacing: "-0.025em", maxWidth: "13ch", mb: 3, color: "text.primary" }}>
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

        <Box component="section" aria-labelledby="platform-title" sx={{
          bgcolor: t.section, borderBottom: `1px solid ${t.rule}`,
          // A very faint fine grid on the section only, behind the cards.
          backgroundImage: t.grid, backgroundSize: `${GRID_STEP}px ${GRID_STEP}px`,
        }}>
          <Box sx={{ ...PAGE, py: { xs: 6, md: 9 } }}>
            <Typography id="platform-title" component="h2" sx={{ fontSize: { xs: 22, md: 26 }, fontWeight: 600, letterSpacing: "-0.01em", fontFamily: (th) => th.typography.h2.fontFamily, mb: 3 }}>
              What the platform does
            </Typography>
            <PlatformCards cards={CARDS} href={href} />
          </Box>
        </Box>
      </Box>

      <Box component="footer" sx={{ bgcolor: t.footer }}>
        <Box sx={{
          ...PAGE, pt: { xs: 5, md: 7 }, pb: { xs: 4, md: 6 }, display: "grid", columnGap: 6, rowGap: 4,
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr)" },
        }}>
          <Box sx={{ gridColumn: { sm: "1 / -1", md: "auto" } }}>
            <Typography component="p" sx={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em", fontFamily: (th) => th.typography.h1.fontFamily }}>SalesMesh</Typography>
            <Typography sx={{ fontSize: 15, color: "text.secondary", mt: 0.75, maxWidth: "34ch" }}>{TAGLINE}</Typography>
          </Box>
          <nav aria-label="Platform">
            <FooterGroup title="Platform">
              {SHARED_PAGES.map((page) => (
                <li key={page.key}><Link component={RouterLink} to={href(page.path)} sx={{ ...linkSx(t), fontSize: 14 }}>{page.label}</Link></li>
              ))}
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
