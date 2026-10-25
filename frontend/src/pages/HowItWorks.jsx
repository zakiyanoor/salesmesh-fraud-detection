import { Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import PageHeader from "../components/PageHeader";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

// Plain-language meaning of each model input, keyed by the names the model uses.
const SIGNALS = {
  submission_frequency: ["Busiest 24 hours", "The most activations the agent submitted in any 24 hours. A burst far above what agents usually manage is unusual."],
  time_of_day_entropy: ["Spread of working hours", "How evenly the agent's activations spread over the hours of the day. Working only at a few odd hours, or at every hour, is unusual."],
  customer_similarity: ["Look-alike customer IDs", "How alike the customer IDs the agent enters are. Many near-identical IDs, such as numbers in a sequence, suggest made-up customers."],
  collusion_score: ["Customers shared with other agents", "The share of the agent's customers that other agents also used. Honest agents rarely share many customers."],
};

const SYSTEMS = [["model", "Model"], ["rule", "Duplicate activation rule"], ["model_or_rule", "Model or rule (the system)"]];

const GLOSSARY = [
  ["Precision", "Of the agents that were flagged, the share that were really fraud."],
  ["Recall", "Of the agents that were really fraud, the share that were flagged."],
  ["PR AUC", "How well the scores put fraud agents ahead of honest ones, judged mostly among the highest scores; 1 is perfect."],
  ["ROC AUC", "How often a fraud agent scores higher than an honest one, across all agents; 0.5 is no better than chance and 1 is perfect."],
];

const two = (value) => Number(value).toFixed(2);
const interval = ([low, high]) => `${two(low)} to ${two(high)}`;

function Section({ title, children }) {
  return (
    <Paper component="section" aria-label={title} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" component="h2" sx={{ mb: 1.5 }}>{title}</Typography>
      {children}
    </Paper>
  );
}

function P({ children }) {
  return <Typography variant="body1" sx={{ mb: 1.5, maxWidth: 760 }}>{children}</Typography>;
}

function every(minutes) {
  if (minutes % 1440 === 0) return minutes === 1440 ? "once a day" : `every ${minutes / 1440} days`;
  if (minutes % 60 === 0) return minutes === 60 ? "every hour" : `every ${minutes / 60} hours`;
  return `every ${minutes} minutes`;
}

function Results({ info }) {
  return (
    <>
      <TableContainer>
        <Table size="small" aria-label="Test results">
          <TableHead>
            <TableRow>
              <TableCell>What flags agents</TableCell>
              <TableCell align="right">Flagged</TableCell>
              <TableCell>Precision</TableCell>
              <TableCell>Recall</TableCell>
              <TableCell>PR AUC</TableCell>
              <TableCell>ROC AUC</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {SYSTEMS.map(([key, label]) => {
              const r = info.results[key];
              const ranked = key !== "model_or_rule";
              return (
                <TableRow key={key}>
                  <TableCell>{label}</TableCell>
                  <TableCell align="right" sx={mono}>{r.flagged}</TableCell>
                  <TableCell sx={mono}>{`${two(r.precision)} (${r.tp} of ${r.flagged})`}</TableCell>
                  <TableCell sx={mono}>{`${two(r.recall)} (${r.tp} of ${r.tp + r.fn})`}</TableCell>
                  <TableCell sx={mono}>{ranked ? `${two(r.pr_auc)} (${interval(r.pr_auc_ci)})` : "not comparable"}</TableCell>
                  <TableCell sx={mono}>{ranked ? `${two(r.roc_auc)} (${interval(r.roc_auc_ci)})` : "not comparable"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, maxWidth: 760 }}>
        {`Measured on ${info.measured_on}. ${info.test_fraud_agents} of the ${info.test_agents} test agents were fraud. `}
        In brackets: the counts behind precision and recall, and the range the PR AUC and ROC AUC would likely fall in on
        another sample of the same size (95% interval). The system flags an agent when the model or the rule flags it, so
        its ranking measures are not comparable with the others. The rule never wrongly flagged an honest test agent; that
        comes from how the test data was made and should not be expected elsewhere.
      </Typography>
    </>
  );
}

/** How the model works (issue #28): plain words for every role, with the figures read from the frozen results. */
export default function HowItWorks() {
  const result = useApi(api.getModelInfo);
  const info = result.data;

  return (
    <Box sx={{ maxWidth: 1000 }}>
      <PageHeader title="How the model works" subtitle="What the system does, what it looks at, and what its numbers mean." />

      <Section title="What the system does">
        <P>
          The system looks at how sales agents onboard customers and highlights agents whose activity is unusual, so that
          people can review them. A flag is a request for a person to look, not a finding of fraud.
        </P>
        <P>
          People decide. A fraud analyst proposes an outcome for a flagged agent, and a compliance officer agrees or
          overrules it. Nothing is decided automatically, and a decision never changes the model.
        </P>
        <P>
          {`Detection runs on a schedule, not live${info ? `: ${every(info.detection_interval_minutes)} by default` : ""}. New activity appears after the next run, and every page shows the results of the latest run.`}
        </P>
      </Section>

      <Section title="The four signals">
        <P>The model compares each agent with the others on four signals, all worked out from the agent's own activations.</P>
        <Box component="dl" sx={{ m: 0 }}>
          {Object.entries(SIGNALS).map(([key, [name, meaning]]) => (
            <Box key={key} sx={{ mb: 1.5 }}>
              <Typography component="dt" variant="body1" sx={{ fontWeight: 500 }}>{name}</Typography>
              <Typography component="dd" variant="body2" color="text.secondary" sx={{ m: 0, maxWidth: 760 }}>{meaning}</Typography>
            </Box>
          ))}
        </Box>
      </Section>

      <Section title="The duplicate activation rule">
        <P>
          Beside the model, a simple rule flags an agent when the same customer and client pair appears twice where it
          should not: used by another agent too, or repeated by the same agent after it was already completed. The agent
          page lists the records behind it.
        </P>
      </Section>

      <Section title="Flag sources and risk bands">
        <P>Each agent shows who flagged it: Model, Rule only, Both (model and rule), or Not flagged.</P>
        <P>
          The risk band sorts agents for review. High: the model flagged the agent. Review: only the rule flagged it, or its
          score is close to the cutoff. Low: everyone else.
        </P>
      </Section>

      <Section title="Scores and the cutoff">
        <P>
          The model gives every agent a score for how unusual it is. A typical agent scores about 1, and higher means
          more unusual. Pages also show a rank, such as Top 2%, meaning the agent scored higher than 98% of agents in the
          latest run.
        </P>
        <P>Scores and ranks are not probabilities. A score does not say how likely an agent is to be committing fraud.</P>
        {info && (
          <P>
            {"The model flags an agent whose score is at or above the cutoff of "}
            <Box component="span" sx={mono}>{info.cutoff.toFixed(3)}</Box>
            {`. It was chosen on separate ${info.cutoff_chosen_on} agents, before the test, to balance missed fraud against false alarms (rule: "${info.cutoff_rule}", the cost of a missed fraud agent against a false alarm).`}
          </P>
        )}
      </Section>

      <Section title="How well it did on test agents">
        {info ? <Results info={info} /> : <LoadStatus result={result} />}
      </Section>

      <Section title="Glossary">
        <Box component="dl" sx={{ m: 0 }}>
          {GLOSSARY.map(([term, meaning]) => (
            <Box key={term} sx={{ mb: 1.5 }}>
              <Typography component="dt" variant="body1" sx={{ fontWeight: 500 }}>{term}</Typography>
              <Typography component="dd" variant="body2" color="text.secondary" sx={{ m: 0 }}>{meaning}</Typography>
            </Box>
          ))}
        </Box>
      </Section>
    </Box>
  );
}
