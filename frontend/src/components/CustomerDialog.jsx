import { useCallback } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Link, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Typography,
} from "@mui/material";
import { FlagSourceChip } from "./chips";
import { LoadStatus } from "./states";
import { useApi } from "../hooks/useApi";
import { formatDateTime } from "../format";

// Activation times are shown as recorded, in Nairobi time.
const RECORDED = { recorded: true };
import { mono } from "../theme";
import { api } from "../api";

/**
 * One customer from an agent's duplicate evidence (issue #28): the agents who used it, the clients and the
 * dates. It is fetched on every open, and the server records every open in the audit log. The customer ID
 * is shown as the evidence table shows it; the request uses customerRef, so the ID is never in a URL.
 */
export default function CustomerDialog({ customerRef, customerId, fromAgent, onClose }) {
  const load = useCallback(() => api.getCustomer({ customerRef, fromAgent }), [customerRef, fromAgent]);
  const result = useApi(load);
  const data = result.data;

  return (
    <Dialog open onClose={onClose} aria-labelledby="customer-title" fullWidth maxWidth="md">
      <DialogTitle id="customer-title">
        Customer <Box component="span" sx={mono}>{customerId}</Box>
      </DialogTitle>
      <DialogContent>
        {!data ? <LoadStatus result={result} /> : (
          <>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              {`Used by ${data.agent_count} ${data.agent_count === 1 ? "agent" : "agents"} across ${data.client_count} ${data.client_count === 1 ? "client" : "clients"}`}
              {data.client_ids.length > 0 && <Box component="span" sx={mono}>{` (${data.client_ids.join(", ")})`}</Box>}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {`First seen ${formatDateTime(data.first_seen, RECORDED)} · Last seen ${formatDateTime(data.last_seen, RECORDED)}`}
            </Typography>

            <TableContainer sx={{ mb: 3 }}>
              <Table size="small" aria-label="Agents who used this customer">
                <TableHead>
                  <TableRow>
                    <TableCell>Agent</TableCell>
                    <TableCell>Flagged by</TableCell>
                    <TableCell align="right">Activations</TableCell>
                    <TableCell>Clients</TableCell>
                    <TableCell>First seen</TableCell>
                    <TableCell>Last seen</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.agents.map((a) => (
                    <TableRow key={a.agent_id}>
                      <TableCell sx={mono}>
                        <Link component={RouterLink} to={`/agents/${a.agent_id}`} onClick={onClose} color="primary.dark">{a.agent_id}</Link>
                      </TableCell>
                      <TableCell><FlagSourceChip source={a.flag_source} /></TableCell>
                      <TableCell align="right" sx={mono}>{a.activations}</TableCell>
                      <TableCell sx={mono}>{a.client_ids.join(", ")}</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDateTime(a.first_seen, RECORDED)}</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDateTime(a.last_seen, RECORDED)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Typography variant="overline" color="text.secondary" component="h3">Activations, newest first</Typography>
            {data.activations_total > data.activations.length && (
              <Typography variant="body2" color="text.secondary">
                {`Showing the latest ${data.activations.length} of ${data.activations_total} activations.`}
              </Typography>
            )}
            <TableContainer>
              <Table size="small" aria-label="Activations">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Agent</TableCell>
                    <TableCell>Client</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.activations.map((r, i) => (
                    <TableRow key={`${r.timestamp}-${r.agent_id}-${i}`}>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDateTime(r.timestamp, RECORDED)}</TableCell>
                      <TableCell sx={mono}>{r.agent_id}</TableCell>
                      <TableCell sx={mono}>{r.client_id}</TableCell>
                      <TableCell>{r.status}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
          Opening this view is recorded in the audit log.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
