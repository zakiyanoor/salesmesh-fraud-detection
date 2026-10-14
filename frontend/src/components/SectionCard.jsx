import { Box, Button, Paper, Skeleton, Typography } from "@mui/material";

/**
 * A card with its own loading, error and empty state, so one failing request does not blank a page.
 * children is a function of the loaded data. isEmpty(data) decides the empty state.
 */
export default function SectionCard({ title, subtitle, result, isEmpty, emptyText = "Nothing to show yet.", sx, children }) {
  let body;
  if (result.loading || result.error?.status === 401) {
    body = <Skeleton variant="rounded" height={160} aria-label={`Loading ${title}`} />;
  } else if (result.error) {
    body = (
      <Box role="alert">
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {result.error.status === 403 ? "Your role does not have access to this." : result.error.message}
        </Typography>
        {result.error.status !== 403 && (
          <Button size="small" variant="outlined" onClick={result.retry}>Try again</Button>
        )}
      </Box>
    );
  } else if (isEmpty?.(result.data)) {
    body = <Typography variant="body2" color="text.secondary">{emptyText}</Typography>;
  } else {
    body = children(result.data);
  }

  return (
    <Paper component="section" aria-label={title} sx={{ p: 3, minWidth: 0, ...sx }}>
      <Typography variant="overline" color="text.secondary" component="h2">{title}</Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{subtitle}</Typography>
      )}
      <Box sx={{ mt: 2 }}>{body}</Box>
    </Paper>
  );
}
