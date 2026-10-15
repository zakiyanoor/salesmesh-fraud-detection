import { Box, Typography } from "@mui/material";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

/** Page title (also the document title) and subtitle, per docs/FRONTEND.md. */
export default function PageHeader({ title, subtitle, children }) {
  useDocumentTitle(title);
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ overflowWrap: "anywhere" }}>{title}</Typography>
      {subtitle && <Typography variant="body2" color="text.secondary">{subtitle}</Typography>}
      {children}
    </Box>
  );
}
