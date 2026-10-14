import { Component } from "react";
import { Box, Button, Paper, Typography } from "@mui/material";

/** Catches a rendering error so one broken page does not blank the whole app. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    console.error("Page failed to render", error, info?.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <Box sx={{ p: { xs: 2, md: 5 } }}>
        <Paper role="alert" sx={{ p: { xs: 3, md: 5 }, textAlign: "center", maxWidth: 560, mx: "auto" }}>
          <Typography variant="h6" component="h2" gutterBottom>This page could not be shown</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Something went wrong while drawing it. Reloading usually fixes this.
          </Typography>
          <Button variant="contained" onClick={() => window.location.reload()}>Reload</Button>
        </Paper>
      </Box>
    );
  }
}
