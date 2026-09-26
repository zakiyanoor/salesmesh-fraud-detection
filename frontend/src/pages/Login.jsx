import { useState } from "react";
import { Box, Paper, TextField, Button, Typography, Alert } from "@mui/material";
import { api } from "../api";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const data = await api.login(username, password);
      onLogin(data.username);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Paper sx={{ p: 5, width: 380 }}>
        <Typography variant="h5" gutterBottom>
          SalesMesh
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Fraud detection administrator sign-in
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            label="Username"
            fullWidth
            margin="normal"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" variant="contained" fullWidth sx={{ mt: 3, py: 1.2 }}>
            Sign in
          </Button>
        </form>
      </Paper>
    </Box>
  );
}