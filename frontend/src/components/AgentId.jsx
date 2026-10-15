import { Box, Link } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useAuth } from "../auth/authContext";
import { canAccess } from "../auth/roles";
import { mono } from "../theme";

/** An agent id in full: a link to agent detail for roles that may open it, plain text otherwise (admin). */
export default function AgentId({ id }) {
  const { user } = useAuth();
  if (!id) return <Box component="span" sx={{ color: "text.secondary" }}>—</Box>;
  if (!canAccess(user?.role, "agentDetail")) return <Box component="span" sx={mono}>{id}</Box>;
  return <Link component={RouterLink} to={`/agents/${id}`} color="primary.dark" sx={mono}>{id}</Link>;
}
