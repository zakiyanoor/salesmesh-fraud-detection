import { useMemo } from "react";
import AgentList from "../components/AgentList";
import PageHeader from "../components/PageHeader";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { loadAgentsAndDecisions } from "../loaders";

const FLAGGED_SOURCES = ["ML", "Both", "Rule"];

/** Agents flagged by the model, the rule or both in the latest run. */
export default function FlaggedAgents() {
  const result = useApi(loadAgentsAndDecisions);
  const [everyone, history] = result.data || [];
  const flagged = useMemo(
    () => (everyone?.agents || []).filter((a) => FLAGGED_SOURCES.includes(a.flag_source)),
    [everyone],
  );

  const header = (
    <PageHeader
      title="Flagged agents"
      subtitle="Agents the model or the duplicate rule flagged in the latest detection run"
    />
  );
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  return (
    <>
      {header}
      <AgentList
        label="Flagged agents"
        agents={flagged}
        decisions={history.decisions}
        sources={FLAGGED_SOURCES}
        emptyText="No agents are flagged in the latest run."
      />
    </>
  );
}
