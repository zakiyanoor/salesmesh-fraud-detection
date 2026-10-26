import { Fragment, useCallback, useState } from "react";
import {
  Box, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import AgentId from "./AgentId";
import RingGraph from "./RingGraph";
import SectionCard from "./SectionCard";
import { SimpleBarChart } from "./charts";
import { FlagSourceChip } from "./chips";
import { LoadStatus } from "./states";
import { ringTimelineTable } from "../chartTables";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

const FLAGGED = "flagged";
const CONNECTED = "connected";
const cell = { fontSize: 14, py: 1.25, borderColor: "divider", fontVariantNumeric: "tabular-nums" };
const head = { fontSize: 13, fontWeight: 500, color: "text.secondary", py: 1, borderColor: "divider" };
const card = { p: 2.5, mt: 3 };

function RingDetail({ candidateId }) {
  const load = useCallback(() => api.getRingGraph(candidateId), [candidateId]);
  const result = useApi(load);

  return (
    <>
      <SectionCard panel title={`Ring graph: ${candidateId}`} subtitle="Agents and how many customers each pair shares. No customer is named." result={result} sx={card}>
        {(g) => (
          <>
            <RingGraph graph={g} />
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "repeat(2, minmax(0, 1fr))" }, gap: 3, mt: 3, alignItems: "start" }}>
              <TableContainer>
                <Table size="small" aria-label={`Pairs in ${g.candidate_id} that share customers`}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={head}>Agent</TableCell>
                      <TableCell sx={head}>Agent</TableCell>
                      <TableCell align="right" sx={head}>Shared customers</TableCell>
                      <TableCell sx={head}>Reaches the rule (3 or more)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {g.edges.map((e) => (
                      <TableRow key={`${e.source}-${e.target}`} hover>
                        <TableCell sx={cell}><AgentId id={e.source} /></TableCell>
                        <TableCell sx={cell}><AgentId id={e.target} /></TableCell>
                        <TableCell align="right" sx={{ ...cell, ...mono }}>{e.shared_customers}</TableCell>
                        <TableCell sx={cell}>{e.meets_rule ? "Yes" : "No"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <Box sx={{ minWidth: 0 }}>
                <TableContainer>
                  <Table size="small" aria-label={`Members of ${g.candidate_id}`}>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={head}>Agent</TableCell>
                        <TableCell sx={head}>County</TableCell>
                        <TableCell sx={head}>Flagged by</TableCell>
                        <TableCell align="right" sx={head}>Activations</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {g.nodes.map((n) => (
                        <TableRow key={n.agent_id} hover>
                          <TableCell sx={cell}><AgentId id={n.agent_id} /></TableCell>
                          <TableCell sx={cell}>{n.county || "—"}</TableCell>
                          <TableCell sx={cell}><FlagSourceChip source={n.flag_source} /></TableCell>
                          <TableCell align="right" sx={{ ...cell, ...mono }}>{n.activations}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <Typography sx={{ fontSize: 14, mt: 1.5 }}>
                  {`${g.county_count} ${g.county_count === 1 ? "county" : "counties"}: ${g.counties.join(", ")}.`}
                </Typography>
                <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{g.county_note}</Typography>
              </Box>
            </Box>
          </>
        )}
      </SectionCard>
      <SectionCard
        panel
        title={`Group activity: ${candidateId}`}
        subtitle="Activations per day by all members of the ring. Days are as recorded in the data."
        result={result}
        table={ringTimelineTable}
        sx={card}
      >
        {(g) => <SimpleBarChart data={g.days.map((d) => ({ name: d.date.slice(5), value: d.activations }))} name="Activations" />}
      </SectionCard>
    </>
  );
}

/** "4: A1, A2, A3, A4": the count first, then the agent IDs (linked for roles that may open agent detail). */
function Agents({ ids }) {
  return (
    <Box component="span" sx={{ display: "inline-flex", flexWrap: "wrap", columnGap: 1, rowGap: 0.5, alignItems: "baseline" }}>
      <Box component="span" sx={{ ...mono, fontWeight: 600 }}>{`${ids.length}:`}</Box>
      {ids.map((id, i) => (
        <Fragment key={id}>
          <Box component="span" sx={{ whiteSpace: "nowrap" }}><AgentId id={id} />{i < ids.length - 1 ? "," : ""}</Box>
        </Fragment>
      ))}
    </Box>
  );
}

function GroupTable({ label, rows, selected, onShow }) {
  return (
    <TableContainer>
      <Table size="small" aria-label={label} sx={{ "& tbody tr:last-of-type td": { borderBottom: 0 } }}>
        <TableHead>
          <TableRow>
            <TableCell sx={head}>Group</TableCell>
            <TableCell sx={head}>Agents</TableCell>
            <TableCell align="right" sx={head}>Shared customers</TableCell>
            <TableCell sx={head}>Clients</TableCell>
            <TableCell align="right" sx={head}>Graph</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.key} hover selected={Boolean(r.candidateId) && r.candidateId === selected}>
              <TableCell sx={{ ...cell, ...mono, whiteSpace: "nowrap" }}>{r.group}</TableCell>
              <TableCell sx={cell}><Agents ids={r.ids} /></TableCell>
              <TableCell align="right" sx={{ ...cell, ...mono }}>{r.shared}</TableCell>
              <TableCell sx={{ ...cell, ...mono }}>{r.clients.join(", ")}</TableCell>
              <TableCell align="right" sx={cell}>
                {r.candidateId ? (
                  <Button
                    size="small"
                    onClick={() => onShow(r.candidateId)}
                    aria-pressed={r.candidateId === selected}
                    aria-label={`Show the graph of ${r.candidateId}`}
                  >
                    {r.candidateId === selected ? "Shown" : "Show"}
                  </Button>
                ) : (
                  <Box component="span" sx={{ color: "text.secondary" }}>—</Box>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/**
 * Who works together (issue #28): one table with a scope switch. "Flagged by the model" lists the ring
 * candidates (flagged agents sharing at least 3 customers, each with a graph); "All connected agents" lists every
 * group of agents linked by customers they share for the same client. The first candidate's graph is shown
 * until another is chosen.
 */
export default function RingExplorer({ data, sharing }) {
  const [scope, setScope] = useState(FLAGGED);
  const [chosen, setChosen] = useState(null);
  const selected = chosen || data.candidates[0]?.candidate_id;
  const candidateRows = data.candidates.map((c) => ({
    key: c.candidate_id, group: c.candidate_id, candidateId: c.candidate_id, ids: c.agent_ids, shared: c.shared_customers, clients: c.client_ids || [],
  }));
  const clusters = sharing?.data?.clusters || [];
  const connectedRows = clusters.map((c, i) => ({
    key: c.agent_ids.join("-"), group: `Group ${i + 1}`, ids: c.agent_ids, shared: c.customer_count, clients: c.client_ids || [],
  }));

  return (
    <>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={scope}
        onChange={(_, next) => next && setScope(next)}
        aria-label="Which groups to list"
        sx={{ mb: 1.5, "& .MuiToggleButton-root": { textTransform: "none", fontSize: 14, px: 1.5 } }}
      >
        <ToggleButton value={FLAGGED}>Flagged by the model</ToggleButton>
        <ToggleButton value={CONNECTED}>All connected agents</ToggleButton>
      </ToggleButtonGroup>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
        Flagged by the model joins agents the model flagged that share at least 3 customers; all connected agents shows
        every group of agents, flagged or not, linked by customers they share for the same client.
      </Typography>

      {scope === FLAGGED ? (
        <>
          <Typography sx={{ fontSize: 14, mb: 1, fontVariantNumeric: "tabular-nums" }}>
            {`${data.candidates_total} ${data.candidates_total === 1 ? "group" : "groups"} among the ${data.flagged_agents} agents the model flagged.`}
          </Typography>
          <GroupTable label="Ring candidate groups" rows={candidateRows} selected={selected} onShow={setChosen} />
        </>
      ) : !sharing?.data ? (
        <LoadStatus result={sharing || { loading: true }} />
      ) : connectedRows.length === 0 ? (
        <Typography sx={{ fontSize: 14, color: "text.secondary" }}>No agents share customers.</Typography>
      ) : (
        <>
          <Typography sx={{ fontSize: 14, mb: 1, fontVariantNumeric: "tabular-nums" }}>
            {`${sharing.data.shared_customers} customers were activated by more than one agent for the same client, linking agents into ${sharing.data.clusters_total} groups.`}
            {sharing.data.clusters_total > clusters.length ? ` The ${clusters.length} largest are shown.` : ""}
          </Typography>
          <GroupTable label="Connected agent groups" rows={connectedRows} selected={selected} onShow={setChosen} />
        </>
      )}

      <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 1.5 }}>
        A candidate is a lead for review, not a confirmed ring. No labels are used.
      </Typography>
      {selected && <RingDetail key={selected} candidateId={selected} />}
    </>
  );
}
