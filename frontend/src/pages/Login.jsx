import { useState } from "react";
import { Box, Paper, TextField, Button, Typography, Alert } from "@mui/material";
import { useAuth } from "../auth/authContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import ThemeMenu from "../components/ThemeMenu";

export default function Login() {
  const { login, notice } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  useDocumentTitle("Sign in");

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
        bgcolor: "background.default",
        p: 2,
      }}
    >
      <Box sx={{ position: "fixed", top: 12, right: 12 }}>
        <ThemeMenu />
      </Box>
      <Paper sx={{ p: { xs: 3, sm: 5 }, width: "100%", maxWidth: 380, boxSizing: "border-box" }}>
        <Typography variant="h5" component="h1" gutterBottom>
          SalesMesh
        </Typography>

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
          <Button type="submit" variant="contained" fullWidth disabled={submitting} sx={{ mt: 3, py: 1.2 }}>
            Sign in
          </Button>
        </form>
      </Paper>
    </Box>
  );
}
