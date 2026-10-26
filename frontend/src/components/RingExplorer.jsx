import { useCallback, useState } from "react";
import {
  Box, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import AgentId from "./AgentId";
import RingGraph from "./RingGraph";
import SectionCard from "./SectionCard";
import { SimpleBarChart } from "./charts";
import { FlagSourceChip } from "./chips";
import { ringTimelineTable } from "../chartTables";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

function RingDetail({ candidateId }) {
  const load = useCallback(() => api.getRingGraph(candidateId), [candidateId]);
  const result = useApi(load);

  return (
    <>
      <SectionCard title={`Ring graph: ${candidateId}`} subtitle="Agents and how many customers each pair shares. No customer is named." result={result} sx={{ mt: 3 }}>
        {(g) => (
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 3, alignItems: "start" }}>
            <RingGraph graph={g} />
            <Box sx={{ minWidth: 0 }}>
              <TableContainer sx={{ mb: 2 }}>
                <Table size="small" aria-label={`Pairs in ${g.candidate_id} that share customers`}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Agent</TableCell>
                      <TableCell>Agent</TableCell>
                      <TableCell align="right">Shared customers</TableCell>
                      <TableCell>Reaches the rule (3 or more)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {g.edges.map((e) => (
                      <TableRow key={`${e.source}-${e.target}`}>
                        <TableCell><AgentId id={e.source} /></TableCell>
                        <TableCell><AgentId id={e.target} /></TableCell>
                        <TableCell align="right" sx={mono}>{e.shared_customers}</TableCell>
                        <TableCell>{e.meets_rule ? "Yes" : "No"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TableContainer>
                <Table size="small" aria-label={`Members of ${g.candidate_id}`}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Agent</TableCell>
                      <TableCell>County</TableCell>
                      <TableCell>Flagged by</TableCell>
                      <TableCell align="right">Activations</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {g.nodes.map((n) => (
                      <TableRow key={n.agent_id}>
                        <TableCell><AgentId id={n.agent_id} /></TableCell>
                        <TableCell>{n.county || "—"}</TableCell>
                        <TableCell><FlagSourceChip source={n.flag_source} /></TableCell>
                        <TableCell align="right" sx={mono}>{n.activations}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <Typography variant="body2" sx={{ mt: 1.5 }}>
                {`${g.county_count} ${g.county_count === 1 ? "county" : "counties"}: ${g.counties.join(", ")}.`}
              </Typography>
              <Typography variant="caption" color="text.secondary" component="p">{g.county_note}</Typography>
            </Box>
          </Box>
        )}
      </SectionCard>
      <SectionCard
        title={`Group activity: ${candidateId}`}
        subtitle="Activations per day by all members of the ring. Days are as recorded in the data."
        result={result}
        table={ringTimelineTable}
        sx={{ mt: 3 }}
      >
        {(g) => <SimpleBarChart data={g.days.map((d) => ({ name: d.date.slice(5), value: d.activations }))} name="Activations" />}
      </SectionCard>
    </>
  );
}

/**
 * The ring candidates (issue #18) with a graph of the selected one (issue #28). The first candidate is shown
 * until another is chosen.
 */
export default function RingExplorer({ data }) {
  const [chosen, setChosen] = useState(null);
  const selected = chosen || data.candidates[0]?.candidate_id;

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {data.candidates_total} {data.candidates_total === 1 ? "group" : "groups"} among the {data.flagged_agents} agents
        the model flagged.
      </Typography>
      <TableContainer>
        <Table size="small" aria-label="Ring candidate groups">
          <TableHead>
            <TableRow>
              <TableCell>Candidate</TableCell>
              <TableCell>Agents</TableCell>
              <TableCell>Size</TableCell>
              <TableCell>Shared customers</TableCell>
              <TableCell>Clients</TableCell>
              <TableCell align="right">Graph</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.candidates.map((c) => (
              <TableRow key={c.candidate_id} selected={c.candidate_id === selected}>
                <TableCell sx={mono}>{c.candidate_id}</TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", flexWrap: "wrap", columnGap: 1.5, rowGap: 0.5 }}>
                    {c.agent_ids.map((id) => <AgentId key={id} id={id} />)}
                  </Box>
                </TableCell>
                <TableCell sx={mono}>{c.size}</TableCell>
                <TableCell sx={mono}>{c.shared_customers}</TableCell>
                <TableCell sx={mono}>{(c.client_ids || []).join(", ")}</TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    onClick={() => setChosen(c.candidate_id)}
                    aria-pressed={c.candidate_id === selected}
                    aria-label={`Show the graph of ${c.candidate_id}`}
                  >
                    {c.candidate_id === selected ? "Shown" : "Show"}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1.5 }}>
        A candidate is a lead for review, not a confirmed ring. No labels are used.
      </Typography>
      {selected && <RingDetail key={selected} candidateId={selected} />}
    </>
  );
}
