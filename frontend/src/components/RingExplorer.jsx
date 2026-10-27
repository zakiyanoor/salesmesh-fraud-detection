import { useCallback, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Chip, Paper, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel, Tabs,
  ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import AgentId from "./AgentId";
import RingGraph from "./RingGraph";
import SectionCard from "./SectionCard";
import { SimpleBarChart } from "./charts";
import { FlagSourceChip } from "./chips";
import { LoadStatus } from "./states";
import { ringTimelineTable } from "../chartTables";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/authContext";
import { canAccess } from "../auth/roles";
import { mono } from "../theme";
import { api } from "../api";

const FLAGGED = "flagged";
const CONNECTED = "connected";
const SHOWN_IDS = 3;
const COUNTY_NOTE = "County is the agent's region in the loaded data, shown for information only. The model never uses it.";
const cell = { fontSize: 14, py: 1.25, borderColor: "divider", fontVariantNumeric: "tabular-nums" };
const head = { fontSize: 13, fontWeight: 500, color: "text.secondary", py: 1, borderColor: "divider" };
// On phones the client count is left out so the table fits; the Members tab lists the clients.
const narrowHidden = { display: { xs: "none", sm: "table-cell" } };
const TABS = [["graph", "Graph"], ["members", "Members"], ["pairs", "Pairs"], ["activity", "Activity"]];

const SCOPE_LINES = {
  [FLAGGED]: "Agents the model flagged that share at least 3 customers.",
  [CONNECTED]: "Every group of agents, flagged or not, linked by customers they share for the same client.",
};

function TabPanel({ value, current, children }) {
  return (
    <Box role="tabpanel" id={`ring-panel-${value}`} aria-labelledby={`ring-tab-${value}`} hidden={value !== current} sx={{ pt: 2.5 }}>
      {value === current && children}
    </Box>
  );
}

function Members({ graph, clients }) {
  return (
    <>
      <TableContainer>
        <Table size="small" aria-label={`Members of ${graph.candidate_id}`}>
          <TableHead>
            <TableRow>
              <TableCell sx={head}>Agent</TableCell>
              <TableCell sx={head}>County</TableCell>
              <TableCell sx={head}>Flagged by</TableCell>
              <TableCell align="right" sx={head}>Activations</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {graph.nodes.map((n) => (
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
      <Typography sx={{ fontSize: 14, mt: 2 }}>
        {`${graph.county_count} ${graph.county_count === 1 ? "county" : "counties"}: ${graph.counties.join(", ")}.`}
      </Typography>
      {clients.length > 0 && (
        <Typography sx={{ fontSize: 14, mt: 0.5 }}>
          {`${clients.length} ${clients.length === 1 ? "client" : "clients"}: `}
          <Box component="span" sx={mono}>{clients.join(", ")}</Box>
        </Typography>
      )}
    </>
  );
}

function Pairs({ graph }) {
  return (
    <TableContainer>
      <Table size="small" aria-label={`Pairs in ${graph.candidate_id} that share customers`}>
        <TableHead>
          <TableRow>
            <TableCell sx={head}>Agent</TableCell>
            <TableCell sx={head}>Agent</TableCell>
            <TableCell align="right" sx={head}>Shared customers</TableCell>
            <TableCell sx={head}>Reaches the rule (3 or more)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {graph.edges.map((e) => (
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
  );
}

/** The selected group: its graph, members, pairs and activity in tabs, with the county note once. */
function GroupPanel({ candidateId, clients }) {
  const load = useCallback(() => api.getRingGraph(candidateId), [candidateId]);
  const result = useApi(load);
  const [tab, setTab] = useState("graph");
  return (
    <Paper component="section" aria-label={`Group ${candidateId}`} sx={{ p: 2.5, mt: 3, borderRadius: "8px", boxShadow: "none" }}>
      <Typography component="h3" sx={{ ...mono, fontSize: 16, fontWeight: 600 }}>{candidateId}</Typography>
      <Tabs
        value={tab}
        onChange={(_, next) => setTab(next)}
        aria-label={`Views of ${candidateId}`}
        variant="scrollable"
        sx={{ borderBottom: 1, borderColor: "divider", minHeight: 40, "& .MuiTab-root": { textTransform: "none", minHeight: 40, fontSize: 14, px: 1.5, minWidth: 0 } }}
      >
        {TABS.map(([value, label]) => <Tab key={value} value={value} label={label} id={`ring-tab-${value}`} aria-controls={`ring-panel-${value}`} />)}
      </Tabs>
      {!result.data ? (
        <Box sx={{ pt: 2.5 }}><LoadStatus result={result} /></Box>
      ) : (
        <>
          <TabPanel value="graph" current={tab}><RingGraph graph={result.data} /></TabPanel>
          <TabPanel value="members" current={tab}><Members graph={result.data} clients={clients} /></TabPanel>
          <TabPanel value="pairs" current={tab}><Pairs graph={result.data} /></TabPanel>
          <TabPanel value="activity" current={tab}>
            <SectionCard
              panel
              title={`Group activity: ${candidateId}`}
              subtitle="Activations per day by all members of the ring. Days are as recorded in the data."
              result={result}
              table={ringTimelineTable}
              sx={{ p: 0, border: 0 }}
            >
              {(g) => <SimpleBarChart data={g.days.map((d) => ({ name: d.date.slice(5), value: d.activations }))} name="Activations" />}
            </SectionCard>
          </TabPanel>
          <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 2.5, pt: 1.5, borderTop: 1, borderColor: "divider" }}>{COUNTY_NOTE}</Typography>
        </>
      )}
    </Paper>
  );
}

/** The agent count, then the first three IDs as small chips (links where the role may open agent detail), then "+N". */
function Agents({ ids }) {
  const { user } = useAuth();
  const openable = canAccess(user?.role, "agentDetail");
  const chip = { size: "small", variant: "outlined", sx: { ...mono, fontSize: 12, height: 22 } };
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
      <Box component="span" sx={{ fontWeight: 600, minWidth: 16, fontVariantNumeric: "tabular-nums" }}>{ids.length}</Box>
      {ids.slice(0, SHOWN_IDS).map((id) => (openable
        ? <Chip key={id} {...chip} label={id} component={RouterLink} to={`/agents/${id}`} clickable />
        : <Chip key={id} {...chip} label={id} />))}
      {ids.length > SHOWN_IDS && (
        <Box component="span" sx={{ fontSize: 13, color: "text.secondary" }} title={ids.slice(SHOWN_IDS).join(", ")}>
          {`+${ids.length - SHOWN_IDS}`}
        </Box>
      )}
    </Box>
  );
}

const SORTS = {
  group: (r) => r.group,
  agents: (r) => r.ids.length,
  shared: (r) => r.shared,
  clients: (r) => r.clients.length,
};

function GroupTable({ label, rows, selected, onView }) {
  const [sort, setSort] = useState({ key: "shared", dir: "desc" });
  const sorted = useMemo(() => {
    const value = SORTS[sort.key];
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = value(a);
      const y = value(b);
      return dir * (typeof x === "string" ? x.localeCompare(y) : x - y);
    });
  }, [rows, sort]);
  const header = (key, text, align, extra) => (
    <TableCell sx={{ ...head, ...extra }} align={align} sortDirection={sort.key === key ? sort.dir : false}>
      <TableSortLabel
        active={sort.key === key}
        direction={sort.key === key ? sort.dir : "desc"}
        onClick={() => setSort((s) => (s.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: key === "group" ? "asc" : "desc" }))}
      >
        {text}
      </TableSortLabel>
    </TableCell>
  );
  return (
    <TableContainer>
      <Table size="small" aria-label={label} sx={{ "& tbody tr:last-of-type td": { borderBottom: 0 } }}>
        <TableHead>
          <TableRow>
            {header("group", "Group")}
            {header("agents", "Agents")}
            {header("shared", "Shared customers", "right")}
            {header("clients", "Clients", "right", narrowHidden)}
            <TableCell sx={{ ...head, position: "relative" }} align="right"><Box component="span" sx={{ position: "absolute", width: "1px", height: "1px", p: 0, m: "-1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0 }}>Action</Box></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sorted.map((r) => {
            const isSelected = Boolean(r.candidateId) && r.candidateId === selected;
            return (
              <TableRow key={r.key} hover selected={isSelected} aria-selected={isSelected || undefined}>
                <TableCell sx={{ ...cell, ...mono, whiteSpace: "nowrap" }}>{r.group}</TableCell>
                <TableCell sx={cell}><Agents ids={r.ids} /></TableCell>
                <TableCell align="right" sx={{ ...cell, ...mono }}>{r.shared}</TableCell>
                <TableCell align="right" sx={{ ...cell, ...narrowHidden, whiteSpace: "nowrap" }}>{`${r.clients.length} ${r.clients.length === 1 ? "client" : "clients"}`}</TableCell>
                <TableCell align="right" sx={cell}>
                  {r.candidateId ? (
                    <Button size="small" onClick={() => onView(r.candidateId)} aria-pressed={isSelected} aria-label={`View ${r.candidateId}`}>
                      View
                    </Button>
                  ) : (
                    <Box component="span" sx={{ color: "text.secondary" }}>—</Box>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/**
 * Who works together (issue #28): one table with a scope switch. "Flagged by the model" lists the ring
 * candidates (each can be viewed as a group); "All connected agents" lists every group linked by customers they
 * share for the same client. The group with the most shared customers is shown until another is viewed.
 */
export default function RingExplorer({ data, sharing }) {
  const [scope, setScope] = useState(FLAGGED);
  const [chosen, setChosen] = useState(null);
  const candidateRows = data.candidates.map((c) => ({
    key: c.candidate_id, group: c.candidate_id, candidateId: c.candidate_id, ids: c.agent_ids, shared: c.shared_customers, clients: c.client_ids || [],
  }));
  const first = [...candidateRows].sort((a, b) => b.shared - a.shared)[0];
  const selected = chosen || first?.candidateId;
  const selectedRow = candidateRows.find((r) => r.candidateId === selected);
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
        sx={{ mb: 1, "& .MuiToggleButton-root": { textTransform: "none", fontSize: 14, px: 1.5 } }}
      >
        <ToggleButton value={FLAGGED}>Flagged by the model</ToggleButton>
        <ToggleButton value={CONNECTED}>All connected agents</ToggleButton>
      </ToggleButtonGroup>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>{SCOPE_LINES[scope]}</Typography>

      {scope === FLAGGED ? (
        <GroupTable label="Ring candidate groups" rows={candidateRows} selected={selected} onView={setChosen} />
      ) : !sharing?.data ? (
        <LoadStatus result={sharing || { loading: true }} />
      ) : connectedRows.length === 0 ? (
        <Typography sx={{ fontSize: 14, color: "text.secondary" }}>No agents share customers.</Typography>
      ) : (
        <GroupTable label="Connected agent groups" rows={connectedRows} selected={selected} onView={setChosen} />
      )}

      <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 1.5 }}>A candidate is a lead for review, not a confirmed ring.</Typography>
      {selected && <GroupPanel key={selected} candidateId={selected} clients={selectedRow?.clients || []} />}
    </>
  );
}
