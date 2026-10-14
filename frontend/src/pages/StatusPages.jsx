import { Button } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { AccessDeniedState, EmptyState } from "../components/states";

export function AccessDenied() {
  return (
    <>
      <PageHeader title="Access denied" />
      <AccessDeniedState />
    </>
  );
}

export function NotFound() {
  return (
    <>
      <PageHeader title="Page not found" />
      <EmptyState title="There is no page at this address">
        Check the address, or go back to the overview.
      </EmptyState>
      <Button component={RouterLink} to="/" variant="contained" sx={{ display: "flex", mx: "auto", mt: 3, width: "fit-content" }}>
        Go to overview
      </Button>
    </>
  );
}
