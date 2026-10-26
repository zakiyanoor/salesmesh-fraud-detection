import { useState } from "react";
import { Box, Paper, TextField, Button, Typography, Alert } from "@mui/material";
import { useAuth } from "../auth/authContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import ThemeMenu from "../components/ThemeMenu";
import { RADIUS, TEXTURE_STEP, accentButtonSx, useSurface } from "./surfaces";
import { TAGLINE } from "./landingContent";

export default function Login() {
  const { login, notice } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  useDocumentTitle("Sign in");
  const t = useSurface();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  const message = error || notice;

  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        // The landing page's hero surface: a lightly tinted band with a fine dot texture.
        bgcolor: "background.default",
        backgroundImage: `linear-gradient(${t.band}, ${t.band}), ${t.texture}`,
        backgroundSize: `auto, ${TEXTURE_STEP}px ${TEXTURE_STEP}px`,
        p: 2,
      }}
    >
      <Box sx={{ position: "fixed", top: 12, right: 12 }}>
        <ThemeMenu />
      </Box>
      <Paper elevation={0} sx={{ p: { xs: 3, sm: 5 }, width: "100%", maxWidth: 400, boxSizing: "border-box", borderRadius: RADIUS, borderColor: t.ruleStrong, bgcolor: "background.paper" }}>
        <Typography variant="h5" component="h1" sx={{ letterSpacing: "-0.01em" }}>
          SalesMesh
        </Typography>
        <Typography sx={{ fontSize: 15, color: "text.secondary", mt: 0.5, mb: 2 }}>{TAGLINE}</Typography>

        {message && (
          <Alert severity={error ? "error" : "warning"} sx={{ mb: 2 }}>
            {message}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            label="Username"
            fullWidth
            margin="normal"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            margin="normal"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" variant="contained" disableElevation fullWidth disabled={submitting} sx={{ ...accentButtonSx(t), mt: 3, py: 1.2 }}>
            Sign in
          </Button>
        </form>
      </Paper>
    </Box>
  );
}
