import { Box, Button, Paper, Skeleton, Typography } from "@mui/material";
import LockOutlined from "@mui/icons-material/LockOutlined";
import ErrorOutlineOutlined from "@mui/icons-material/ErrorOutlineOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import { Link as RouterLink } from "react-router-dom";

/** Skeleton shaped like a page body (the PageHeader renders above it): optional cards, then rows. */
export function PageSkeleton({ cards = 0, rows = 6 }) {
  return (
    <Box aria-busy="true" aria-label="Loading">
      {cards > 0 && (
        <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
          {Array.from({ length: cards }, (_, i) => (
            <Skeleton key={i} variant="rounded" height={180} sx={{ flex: "1 1 280px" }} />
          ))}
        </Box>
      )}
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} variant="text" height={36} />
      ))}
    </Box>
  );
}

function StateCard({ icon, title, children, action }) {
  return (
    <Paper sx={{ p: { xs: 3, md: 5 }, textAlign: "center", maxWidth: 560, mx: "auto", mt: 2 }}>
      <Box sx={{ color: "text.secondary", mb: 1 }}>{icon}</Box>
      <Typography variant="h6" component="h2" gutterBottom>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: action ? 3 : 0 }}>{children}</Typography>
      {action}
    </Paper>
  );
}

export function EmptyState({ title = "Nothing here yet", children }) {
  return <StateCard icon={<InboxOutlined fontSize="large" />} title={title}>{children}</StateCard>;
}

export function ErrorState({ error, onRetry }) {
  return (
    <StateCard
      icon={<ErrorOutlineOutlined fontSize="large" />}
      title={error?.status === 404 ? "Not found" : "Something went wrong"}
      action={onRetry && <Button variant="contained" onClick={onRetry}>Try again</Button>}
    >
      {error?.message || "The request failed."}
    </StateCard>
  );
}

export function AccessDeniedState() {
  return (
    <StateCard
      icon={<LockOutlined fontSize="large" />}
      title="Access denied"
      action={<Button component={RouterLink} to="/" variant="contained">Go to overview</Button>}
    >
      Your role does not have access to this page. Ask an admin if you think it should.
    </StateCard>
  );
}

/** What a page shows while its data is not ready: skeleton, access denied or error with retry. */
export function LoadStatus({ result, skeleton }) {
  if (result.loading) return skeleton || <PageSkeleton />;
  if (result.error?.status === 401) return skeleton || <PageSkeleton />;
  if (result.error?.status === 403) return <AccessDeniedState />;
  return <ErrorState error={result.error} onRetry={result.retry} />;
}
