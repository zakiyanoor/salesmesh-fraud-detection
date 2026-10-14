import { Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import DonutCard from "../components/DonutCard";
import PageHeader from "../components/PageHeader";
import { LoadStatus, PageSkeleton } from "../components/states";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

const loadOverview = () => Promise.all([api.getFlaggedAgents(), api.getAllAgents()]);

/** Overview: who is flagged, where, and how risky, from the latest detection run. */
export default function Dashboard() {
  const theme = useTheme();
  const result = useApi(loadOverview);
  const [flagged, everyone] = result.data || [];
  const analysisPeriod = flagged?.flagged_agents?.[0]?.analysis_period;
  const subtitle = `Agents surfaced by the most recent detection cycle${analysisPeriod ? ` · Analysis period ${analysisPeriod}` : ""}`;

  if (!result.data) {
    return (
      <>
        <PageHeader title="Overview" subtitle={subtitle} />
        <LoadStatus result={result} skeleton={<PageSkeleton cards={3} rows={0} />} />
      </>
    );
  }

  // The donuts count agents, so they read /all-agents (one row per agent, latest
  // period). /analytics and /flagged-agents aggregate per feature vector, which
  // double-counts any agent analysed in more than one period.
  const roster = everyone.agents || [];
  const flaggedTotal = roster.filter((a) => a.status === "flagged").length;

  const regionCounts = {};
  roster.forEach((a) => {
    const region = a.region ?? "Unknown";
    regionCounts[region] = (regionCounts[region] || 0) + 1;
  });
  const regionEntries = Object.entries(regionCounts).sort((a, b) => b[1] - a[1]);

  const statusSlices = [
    { name: "Flagged", value: flaggedTotal, fill: theme.palette.error.main },
    { name: "Clear", value: roster.length - flaggedTotal, fill: theme.palette.success.main },
  ];
  const regionSlices = regionEntries.slice(0, 5).map(([region, count], i) => ({
    name: region,
    value: count,
    fill: theme.palette.chart.region[i],
  }));
  const riskSlices = [
    { name: "High risk", band: "high" },
    { name: "Review", band: "review" },
    { name: "Low risk", band: "low" },
  ].map(({ name, band }) => ({
    name,
    value: roster.filter((a) => a.risk_band === band).length,
    fill: theme.palette.risk[band],
  }));

  return (
    <>
      <PageHeader title="Overview" subtitle={subtitle} />
      <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <DonutCard title="Agents by Status" subtitle="All registered agents" slices={statusSlices} />
        <DonutCard
          title="Top 5 Regions"
          subtitle={regionEntries.length > 5 ? `By agent count, 5 of ${regionEntries.length} regions` : "By agent count"}
          slices={regionSlices}
        />
        <DonutCard
          title="Risk Level Breakdown"
          subtitle="High: model flagged · Review: rule only or score 1.3 and above · Low: the rest"
          slices={riskSlices}
        />
      </Box>
    </>
  );
}
