import { Link as RouterLink } from "react-router-dom";
import { Box, Button, Container, Paper, Typography } from "@mui/material";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export const SIGN_IN_PATH = "/sign-in";

// Each point is backed by the code named in docs/FRONTEND.md ("Landing page").
const SECURITY = [
  ["Role based access", "Each person has one role: fraud analyst, compliance officer or administrator. The server checks the role on every request, so a page or action outside your role is refused, whatever the screen shows."],
  ["Two person review of every decision", "A fraud analyst proposes an outcome and a different person, a compliance officer, agrees or overrules it. Nobody can decide on their own proposal, and a decision is never edited afterwards; a correction is added beside it."],
  ["An append only audit log", "Sign-ins, refused requests, review actions, account changes and detection runs are written to an audit log that the database refuses to change or delete."],
  ["Secure sessions", "Signing in starts a session held in a cookie that page scripts cannot read, sent only over secure connections in production, and ended after a period of time. The account is checked again on every request, so a deactivated account loses access at once."],
];

/** The first page at the site root before sign in (issue #28). It makes no API calls. */
export default function Landing() {
  useDocumentTitle(null);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Box component="header" sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "background.paper" }}>
        <Container maxWidth="lg" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, py: 1.5 }}>
          <Typography variant="h6" component="p" sx={{ fontWeight: 600 }}>SalesMesh</Typography>
          <Button component={RouterLink} to={SIGN_IN_PATH} variant="contained">Sign in</Button>
        </Container>
      </Box>

      <Container component="main" id="main-content" maxWidth="lg" sx={{ py: { xs: 4, md: 8 } }}>
        <Box sx={{ maxWidth: 760, mb: { xs: 5, md: 7 } }}>
          <Typography variant="h3" component="h1" sx={{ fontSize: { xs: "2rem", md: "3rem" }, mb: 2 }}>SalesMesh Fraud Detection</Typography>
          <Typography variant="h6" component="p" color="text.secondary" sx={{ fontWeight: 400, mb: 3 }}>
            Highlights unusual activity by sales agents so that people can review it.
          </Typography>
          <Button component={RouterLink} to={SIGN_IN_PATH} variant="outlined" size="large">Sign in to review agents</Button>
        </Box>

        <Box component="section" aria-labelledby="how-title" sx={{ mb: { xs: 5, md: 7 } }}>
          <Typography id="how-title" variant="h5" component="h2" sx={{ mb: 2 }}>How it works</Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: 3 }}>
            {[
              ["Agents are flagged", "A model looks for unusual activity, and a duplicate activation rule looks for customers activated twice where they should not be. Either one can flag an agent."],
              ["People decide", "A flag is a request for a person to look, not a finding. A fraud analyst reviews the evidence and proposes an outcome, and a compliance officer agrees or overrules it."],
              ["Detection runs on a schedule", "Activity is checked at set times, not live, and each review page shows the results of the latest run."],
            ].map(([title, text]) => (
              <Paper key={title} component="article" sx={{ p: 3 }}>
                <Typography variant="h6" component="h3" sx={{ mb: 1 }}>{title}</Typography>
                <Typography variant="body2" color="text.secondary">{text}</Typography>
              </Paper>
            ))}
          </Box>
        </Box>

        <Box component="section" aria-labelledby="security-title">
          <Typography id="security-title" variant="h5" component="h2" sx={{ mb: 2 }}>Security design</Typography>
          <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
            {SECURITY.map(([title, text]) => (
              <Paper key={title} component="li" sx={{ p: 3 }}>
                <Typography variant="h6" component="h3" sx={{ mb: 1 }}>{title}</Typography>
                <Typography variant="body2" color="text.secondary">{text}</Typography>
              </Paper>
            ))}
          </Box>
        </Box>
      </Container>
    </Box>
  );
}
