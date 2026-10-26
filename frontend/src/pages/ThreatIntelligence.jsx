import { Skeleton, Typography } from "@mui/material";
import PageHeader from "../components/PageHeader";
import SectionCard from "../components/SectionCard";
import RingExplorer from "../components/RingExplorer";
import { regionRateTable, timelineTable } from "../chartTables";
import { ActivationTimelineChart, CountyChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { formatPercent } from "../format";
import { api } from "../api";

const card = { p: 2.5, mb: 3 };

/** "145 of 1000 agents (14.5%) flagged by the model. Their records carry X% of commission paid." */
function SummaryLine({ summary }) {
  const s = summary.data;
  if (summary.loading) return <Skeleton variant="text" width={420} sx={{ mb: 3 }} />;
  if (!s) {
    return (
      <Typography role="alert" sx={{ fontSize: 14, color: "text.secondary", mb: 3 }}>
        {summary.error?.status === 403 ? "Your role does not have access to this." : `Summary figures could not be loaded: ${summary.error?.message || "the request failed."}`}
      </Typography>
    );
  }
  if (!s.agents_scored) return <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 3 }}>No successful detection run yet.</Typography>;
  const share = s.commission_kes?.flagged_share;
  return (
    <Typography data-testid="threat-summary" sx={{ fontSize: 15, mb: 3, fontVariantNumeric: "tabular-nums" }}>
      {`${s.flagged} of ${s.agents_scored} agents (${formatPercent(s.flagged_rate)}) flagged by the model.`}
      {share != null ? ` Their records carry ${formatPercent(share)} of commission paid.` : ""}
    </Typography>
  );
}

/**
 * Threat intelligence for every role, from the latest successful detection run (issue #28). It answers who is
 * working together (ring candidates and connected agents), when (the activation timeline) and where (counties).
 */
export default function ThreatIntelligence() {
  const summary = useApi(api.getThreatSummary);
  const timeline = useApi(api.getThreatTimeline);
  const regions = useApi(api.getThreatByRegion);
  const sharing = useApi(api.getCustomerSharing);
  const rings = useApi(api.getRingCandidates);

  return (
    <>
      <PageHeader title="Threat intelligence" subtitle="Where flagged activity concentrates, from the latest successful detection run" />
      <SummaryLine summary={summary} />

      <SectionCard
        panel
        title="Ring candidates"
        subtitle="Who is working together: agents linked by the customers they share"
        result={rings}
        isEmpty={(d) => !d?.candidates?.length}
        emptyText="No flagged agents share 3 or more customers."
        sx={card}
      >
        {(d) => <RingExplorer data={d} sharing={sharing} />}
      </SectionCard>

      <SectionCard
        panel
        title="Activation timeline"
        table={timelineTable}
        subtitle="Activations per day by agents the model flagged and by all other agents"
        result={timeline}
        isEmpty={(d) => !d?.days?.length}
        emptyText="No activation records are loaded yet."
        sx={card}
      >
        {(d) => <ActivationTimelineChart days={d.days} />}
      </SectionCard>

      <SectionCard
        panel
        title="Flagged agents by county"
        table={regionRateTable}
        subtitle="Flagged and all agents in the 10 counties with the highest flagged rate, among counties with at least 5 agents"
        result={regions}
        isEmpty={(d) => !d?.top_by_flagged_rate?.length}
        emptyText="No county has enough agents yet."
        sx={{ p: 2.5 }}
      >
        {(d) => <CountyChart counties={d.top_by_flagged_rate} />}
      </SectionCard>
    </>
  );
}
