import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Link, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import FlowDiagram from "../components/FlowDiagram";
import ThemeMenu from "../components/ThemeMenu";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { DUPLICATE_RULE, FOOTER, PERMISSIONS, ROLES, SECURITY, SIGNALS, SIGN_IN_PATH, STEPS } from "./landingContent";

// One corner radius and a fixed text measure for the whole page (issue #28).
const RADIUS = "6px";
const MEASURE = "68ch";
const HEADER_HEIGHT = 64;
// Footer links land below the sticky header.
const anchor = { scrollMarginTop: `${HEADER_HEIGHT + 16}px` };
// Heading and introduction on the left, the list on the right, from md up.
const split = { display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(220px, 300px) 1fr" }, columnGap: 8, alignItems: "start" };

function whoCan(allowed) {
  const names = ROLES.filter((_, i) => allowed[i]);
  if (names.length === ROLES.length) return "All three roles.";
  return `${names.map((name, i) => (i ? name.toLowerCase() : name)).join(" and ")} only.`;
}

function Heading({ id, children, sx }) {
  return (
    <Typography id={id} variant="h2" sx={{ fontSize: { xs: 22, md: 28 }, lineHeight: 1.25, mb: 2, ...anchor, ...sx }}>
      {children}
    </Typography>
  );
}

function Prose({ children, sx }) {
  return <Typography sx={{ fontSize: 17, lineHeight: 1.6, maxWidth: MEASURE, ...sx }}>{children}</Typography>;
}

function Definitions({ id, items, labelledBy }) {
  return (
    <Box component="dl" id={id} aria-labelledby={labelledBy} sx={{ m: 0, maxWidth: MEASURE, ...anchor }}>
      {items.map(([term, meaning, termId]) => (
        <Box key={term} sx={{ py: 1.75, borderTop: 1, borderColor: "divider" }}>
          <Typography component="dt" id={termId} sx={{ fontSize: 18, fontWeight: 600, fontFamily: (t) => t.typography.h3.fontFamily, ...(termId ? anchor : {}) }}>
            {term}
          </Typography>
          <Typography component="dd" sx={{ m: 0, mt: 0.5, fontSize: 17, lineHeight: 1.6, color: "text.secondary" }}>{meaning}</Typography>
        </Box>
      ))}
    </Box>
  );
}

/** The first page at the site root before sign in (issue #28). No API calls of its own, no motion. */
export default function Landing() {
  useDocumentTitle(null);
  const theme = useTheme();
  // Below md the diagram stacks; the side-by-side layout needs about 900px to keep its text readable.
  const narrow = !useMediaQuery(theme.breakpoints.up("md"), { noSsr: true });
  const phone = !useMediaQuery(theme.breakpoints.up("sm"), { noSsr: true });
  const signIn = { component: RouterLink, to: SIGN_IN_PATH, variant: "contained", sx: { borderRadius: RADIUS, boxShadow: "none" } };
  const page = { maxWidth: 1120, mx: "auto", px: { xs: 2, sm: 4 } };

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", color: "text.primary" }}>
      <Box component="header" sx={{ position: "sticky", top: 0, zIndex: 2, bgcolor: "background.default", borderBottom: 1, borderColor: "divider" }}>
        <Box sx={{ ...page, height: HEADER_HEIGHT, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography component="p" sx={{ fontSize: 19, fontWeight: 600, fontFamily: (t) => t.typography.h1.fontFamily }}>SalesMesh</Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Button {...signIn}>Sign in</Button>
            <ThemeMenu />
          </Box>
        </Box>
      </Box>

      <Box component="main" id="main-content" sx={page}>
        <Box component="section" aria-labelledby="hero-title" sx={{ pt: { xs: 5, md: 10 }, pb: { xs: 5, md: 7 } }}>
          <Typography id="hero-title" variant="h1" sx={{ fontSize: { xs: 30, md: 40 }, lineHeight: 1.15, maxWidth: "28ch", mb: 3 }}>
            Fraud detection for sales agent networks, with every decision reviewed by two people and recorded.
          </Typography>
          <Prose sx={{ mb: 4, color: "text.secondary" }}>
            SalesMesh compares each agent's activations with typical agent behaviour and applies a duplicate
            activation rule. Flagged agents are passed to a fraud analyst with the supporting evidence, and a compliance
            officer agrees or overrules the proposed outcome.
          </Prose>
          <Button {...signIn} size="large">Sign in</Button>
        </Box>

        <Box component="section" aria-labelledby="how-a-flag-is-made" sx={{ pb: { xs: 7, md: 10 } }}>
          <Heading id="how-a-flag-is-made" sx={{ fontSize: { xs: 18, md: 20 }, color: "text.secondary", fontWeight: 600 }}>How a flag is made</Heading>
          <Box sx={{ border: 1, borderColor: "divider", borderRadius: RADIUS, p: { xs: 1.5, sm: 3 } }}>
            <FlowDiagram tall={narrow} />
          </Box>
        </Box>

        <Box component="section" aria-labelledby="what-it-looks-at" sx={{ ...split, pb: { xs: 6, md: 8 } }}>
          <Box>
            <Heading id="what-it-looks-at">What it looks at</Heading>
            <Prose sx={{ mb: 2, color: "text.secondary" }}>Four signals from each agent's own activations go into the model, and one rule runs beside it.</Prose>
          </Box>
          <Box>
            <Definitions id="signals" items={SIGNALS} />
            <Typography component="h3" sx={{ fontSize: 15, fontWeight: 600, color: "text.secondary", mt: 4, mb: 1 }}>Beside the model</Typography>
            <Definitions id="duplicate-rule" items={[DUPLICATE_RULE]} />
          </Box>
        </Box>

        <Box component="section" aria-labelledby="flag-to-decision" sx={{ pb: { xs: 6, md: 8 } }}>
          <Heading id="flag-to-decision">From flag to decision</Heading>
          <Prose sx={{ mb: 3, fontWeight: 600 }}>A flag prompts a review. It is not a finding.</Prose>
          <Box component="ol" sx={{ m: 0, p: 0, listStyle: "none", maxWidth: MEASURE, counterReset: "step" }}>
            {STEPS.map(([title, text], i) => (
              <Box component="li" key={title} id={i === STEPS.length - 1 ? "corrections" : undefined}
                sx={{ display: "grid", gridTemplateColumns: "2.25rem 1fr", columnGap: 1.5, py: 1.5, borderTop: 1, borderColor: "divider", ...anchor }}>
                <Typography aria-hidden="true" sx={{ fontFamily: (t) => t.typography.fontFamilyMono, fontSize: 17, color: "text.secondary" }}>{i + 1}.</Typography>
                <Box>
                  <Typography component="h3" sx={{ fontSize: 18, fontWeight: 600, fontFamily: (t) => t.typography.h3.fontFamily }}>{title}</Typography>
                  <Typography sx={{ fontSize: 17, lineHeight: 1.6, color: "text.secondary", mt: 0.25 }}>{text}</Typography>
                </Box>
              </Box>
            ))}
          </Box>
          <Prose sx={{ mt: 3, color: "text.secondary" }}>
            Every step, from the detection run to each correction, is written to the audit log with who did it and when.
          </Prose>
        </Box>

        <Box component="section" aria-labelledby="who-can-do-what" sx={{ pb: { xs: 6, md: 9 } }}>
          <Heading id="who-can-do-what">Who can do what</Heading>
          {phone ? (
            // Three role columns do not fit a phone: each action, then the roles that can take it.
            <Definitions id="who-can-do-what-list" items={PERMISSIONS.map(([action, allowed]) => [action, whoCan(allowed)])} />
          ) : (
            <TableContainer sx={{ border: 1, borderColor: "divider", borderRadius: RADIUS, maxWidth: 820, "& .MuiTableCell-root": { fontSize: 15 } }}>
              <Table size="small" aria-labelledby="who-can-do-what">
                <TableHead>
                  <TableRow>
                    <TableCell>Action</TableCell>
                    {ROLES.map((r) => <TableCell key={r} align="center">{r}</TableCell>)}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {PERMISSIONS.map(([action, allowed]) => (
                    <TableRow key={action}>
                      <TableCell component="th" scope="row" sx={{ fontWeight: 400 }}>{action}</TableCell>
                      {allowed.map((yes, i) => (
                        <TableCell key={ROLES[i]} align="center" sx={{ color: yes ? "text.primary" : "text.secondary" }}>{yes ? "Yes" : "No"}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>

        <Box component="section" aria-labelledby="security-design" sx={{ ...split, pb: { xs: 8, md: 12 } }}>
          <Box>
            <Heading id="security-design">Security design</Heading>
            <Prose sx={{ mb: 2, color: "text.secondary" }}>How access and the record of decisions are protected.</Prose>
          </Box>
          <Definitions items={SECURITY.map(([id, term, meaning]) => [term, meaning, id])} />
        </Box>
      </Box>

      <Box component="footer" sx={{ borderTop: 1, borderColor: "divider" }}>
        <Box sx={{ ...page, pt: { xs: 5, md: 6 }, pb: 4 }}>
          <Box sx={{ mb: 4, maxWidth: MEASURE }}>
            <Typography component="p" sx={{ fontSize: 17, fontWeight: 600, fontFamily: (t) => t.typography.h1.fontFamily }}>SalesMesh Fraud Detection</Typography>
            <Typography sx={{ fontSize: 15, color: "text.secondary", mt: 0.5 }}>Fraud detection for sales agent networks in Kenya.</Typography>
          </Box>
          <Box component="nav" aria-label="Page sections" sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 4 }}>
            {FOOTER.map(([title, links]) => (
              <Box key={title}>
                <Typography component="h2" sx={{ fontSize: 15, fontWeight: 600, mb: 1 }}>{title}</Typography>
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                  {links.map(([label, target]) => (
                    <Box component="li" key={target} sx={{ py: 0.5 }}>
                      <Link href={`#${target}`} sx={{ fontSize: 15, color: "primary.dark", borderRadius: RADIUS }}>{label}</Link>
                    </Box>
                  ))}
                </Box>
              </Box>
            ))}
            <Box>
              <Typography component="h2" sx={{ fontSize: 15, fontWeight: 600, mb: 1 }}>Access</Typography>
              <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                <Box component="li" sx={{ py: 0.5 }}>
                  <Link component={RouterLink} to={SIGN_IN_PATH} sx={{ fontSize: 15, color: "primary.dark", borderRadius: RADIUS }}>Sign in</Link>
                </Box>
                <Box component="li" sx={{ py: 0.5 }}>
                  <Typography sx={{ fontSize: 15, color: "text.secondary" }}>Accounts are managed by an administrator.</Typography>
                </Box>
              </Box>
            </Box>
          </Box>
          <Typography sx={{ fontSize: 14, color: "text.secondary", mt: 5, pt: 3, borderTop: 1, borderColor: "divider" }}>
            SalesMesh Fraud Detection. ICS Project II, 2026.
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
