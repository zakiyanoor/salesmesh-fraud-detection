import { Box } from "@mui/material";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import AgentList from "../components/AgentList";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { loadAgentsAndDecisions } from "../loaders";

const ALL_SOURCES = ["ML", "Both", "Rule", "None"];

export default function AllAgents() {
  const result = useApi(loadAgentsAndDecisions);
  const header = <PageHeader title="All agents" subtitle="Every registered agent with their latest detection result" />;
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  const [everyone, history] = result.data;
  const agents = everyone.agents || [];
  const notFlagged = agents.filter((a) => a.flag_source === "None" || !a.flag_source).length;

  return (
    <>
      {header}
      <Box component="section" aria-label="Summary" sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <KpiCard icon={<GroupsOutlined fontSize="large" />} value={everyone.count ?? agents.length} label="Total agents" />
        <KpiCard icon={<WarningAmberOutlined fontSize="large" />} value={agents.length - notFlagged} label="Flagged by the model or rule" color="error.main" />
        <KpiCard icon={<CheckCircleOutlined fontSize="large" />} value={notFlagged} label="Not flagged" color="success.main" />
      </Box>
      <AgentList
        label="All agents"
        agents={agents}
        decisions={history.decisions}
        sources={ALL_SOURCES}
        emptyText="No agents are loaded yet."
      />
    </>
  );
}
