import { Box, Paper, Skeleton, Typography } from "@mui/material";
import PageHeader from "../components/PageHeader";
import SectionCard from "../components/SectionCard";
import RingExplorer from "../components/RingExplorer";
import { regionRateTable } from "../chartTables";
import { CountyChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { formatPercent } from "../format";
import { api } from "../api";

const card = { p: 2.5, mb: 3 };

function Stat({ label, value, note }) {
  return (
    <Paper component="article" aria-label={label} sx={{ p: 2.5, borderRadius: "8px", boxShadow: "none", minWidth: 0 }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 28, fontWeight: 500, lineHeight: 1.25, fontVariantNumeric: "tabular-nums", mt: 0.5 }}>{value}</Typography>
      {note && <Typography sx={{ fontSize: 13, color: "text.secondary", fontVariantNumeric: "tabular-nums" }}>{note}</Typography>}
    </Paper>
  );
}

/** Three stat tiles from the summary and the ring candidates: flagged agents, their commission share, groups. */
function Stats({ summary, rings }) {
  const s = summary.data;
  if (summary.loading) return <Skeleton variant="rounded" height={104} sx={{ mb: 3 }} />;
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
    <Box component="section" aria-label="Summary" sx={{ display: "grid", gap: 2, mb: 3, gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(3, minmax(0, 1fr))" } }}>
      <Stat label="Flagged by the model" value={`${s.flagged} of ${s.agents_scored}`} note={formatPercent(s.flagged_rate)} />
      <Stat label="Commission carried by flagged agents" value={share != null ? formatPercent(share) : "—"} note="of commission paid" />
      <Stat label="Ring candidates" value={rings.data ? rings.data.candidates_total : "—"} note="groups sharing 3 or more customers" />
    </Box>
  );
}

/**
 * Threat intelligence for every role, from the latest successful detection run (issue #28). It answers who is
 * working together (ring candidates and connected agents) and where (counties).
 */
export default function ThreatIntelligence() {
  const summary = useApi(api.getThreatSummary);
  const regions = useApi(api.getThreatByRegion);
  const sharing = useApi(api.getCustomerSharing);
  const rings = useApi(api.getRingCandidates);

  return (
    <>
      <PageHeader title="Threat intelligence" subtitle="Where flagged activity concentrates, from the latest successful detection run" />
      <Stats summary={summary} rings={rings} />

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
