import { useState } from "react";
import {
  Accordion, AccordionDetails, AccordionSummary, Box, Button, Paper, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMoreOutlined";
import PageHeader from "../components/PageHeader";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { useLatestRun } from "../latestRun/latestRunContext";
import { formatDateTime } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const WIDTH = 960;
const card = { p: 2.5, borderRadius: "8px", boxShadow: "none" };
const tabular = { fontVariantNumeric: "tabular-nums" };

const STEPS = [
  ["Collect activations", "Every activation an agent submitted in the analysis period."],
  ["Compare with other agents", "Four signals per agent, measured against all the others."],
  ["Score", "One number for how unusual the agent is; a typical agent scores about 1."],
  ["Flag at the cutoff", "Agents at or above the cutoff are flagged for review."],
  ["A person reviews", "An analyst proposes an outcome and a compliance officer agrees or overrules it."],
];

// What the model looks at, keyed by the names the model uses.
const SIGNALS = [
  ["Busiest 24 hours", "The most activations the agent submitted in any 24 hours.", "Unusual when the agent submits far more in a day than agents usually manage."],
  ["Spread of working hours", "How evenly the agent's activations spread over the hours of the day.", "Unusual when work is packed into a few odd hours, or spread over every hour."],
  ["Look-alike customer IDs", "How alike the customer IDs the agent enters are.", "Unusual when many IDs are near identical, such as numbers in a sequence."],
  ["Customers shared with other agents", "The share of the agent's customers that other agents also activated.", "Unusual when many customers are shared; honest agents rarely share them."],
];

const FLAG_SOURCES = [
  ["Model", "The model flagged the agent.", "High"],
  ["Rule only", "Only the duplicate activation rule flagged the agent.", "Review"],
  ["Model and rule", "Both flagged the agent.", "High"],
  ["Not flagged", "Neither flagged the agent.", "Review when the score is close to the cutoff, otherwise Low"],
];

const SYSTEMS = [["model", "Model"], ["rule", "Duplicate activation rule"], ["model_or_rule", "Model or rule"]];

const GLOSSARY = [
  ["Precision", "Of the agents that were flagged, the share that were really fraud."],
  ["Recall", "Of the agents that were really fraud, the share that were flagged."],
  ["PR AUC", "How well the scores put fraud agents ahead of honest ones, judged mostly among the highest scores; 1 is perfect."],
  ["ROC AUC", "How often a fraud agent scores higher than an honest one, across all agents; 0.5 is no better than chance and 1 is perfect."],
];

const two = (value) => Number(value).toFixed(2);
const interval = ([low, high]) => `${two(low)} to ${two(high)}`;

function every(minutes) {
  if (minutes % 1440 === 0) return minutes === 1440 ? "once a day" : `every ${minutes / 1440} days`;
  if (minutes % 60 === 0) return minutes === 60 ? "every hour" : `every ${minutes / 60} hours`;
  return `every ${minutes} minutes`;
}

function Section({ title, children }) {
  return (
    <Box component="section" aria-label={title} sx={{ mb: 5 }}>
      <Typography component="h2" sx={{ fontSize: 20, fontWeight: 600, mb: 2 }}>{title}</Typography>
      {children}
    </Box>
  );
}

function Steps({ info }) {
  return (
    <>
      <Box component="ol" sx={{
        listStyle: "none", m: 0, p: 0, display: "grid", gap: 2,
        gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))", md: "repeat(5, minmax(0, 1fr))" },
      }}>
        {STEPS.map(([name, line], i) => (
          <Paper component="li" key={name} sx={card}>
            <Typography sx={{ ...mono, fontSize: 13, color: "text.secondary", mb: 0.5 }}>{i + 1}</Typography>
            <Typography sx={{ fontSize: 15, fontWeight: 600, mb: 0.5 }}>{name}</Typography>
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{line}</Typography>
          </Paper>
        ))}
      </Box>
      {info && (
        <Typography sx={{ fontSize: 14, mt: 2 }}>
          {`Detection runs ${every(info.detection_interval_minutes)}. Every page shows the latest run.`}
        </Typography>
      )}
    </>
  );
}

function Signals() {
  return (
    <>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))" } }}>
        {SIGNALS.map(([name, sentence, unusual]) => (
          <Paper key={name} component="article" aria-label={name} sx={card}>
            <Typography component="h3" sx={{ fontSize: 15, fontWeight: 600, mb: 0.5 }}>{name}</Typography>
            <Typography sx={{ fontSize: 14, mb: 1 }}>{sentence}</Typography>
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{unusual}</Typography>
          </Paper>
        ))}
      </Box>
      <Paper component="article" aria-label="The duplicate activation rule" sx={{ ...card, mt: 2 }}>
        <Typography component="h3" sx={{ fontSize: 15, fontWeight: 600, mb: 0.5 }}>The duplicate activation rule</Typography>
        <Typography sx={{ fontSize: 14 }}>
          Beside the model, a simple rule flags an agent when the same customer and client pair appears twice where it
          should not: used by another agent too, or repeated by the same agent after it was already completed.
        </Typography>
      </Paper>
    </>
  );
}

function FlagSources() {
  const head = { fontSize: 13, fontWeight: 500, color: "text.secondary" };
  return (
    <TableContainer component={Paper} sx={{ ...card, p: 0 }}>
      <Table size="small" aria-label="Flag sources and risk bands">
        <TableHead>
          <TableRow>
            <TableCell sx={head}>Flagged by</TableCell>
            <TableCell sx={head}>Meaning</TableCell>
            <TableCell sx={head}>Risk band</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {FLAG_SOURCES.map(([source, meaning, band]) => (
            <TableRow key={source}>
              <TableCell sx={{ fontWeight: 500, whiteSpace: "nowrap" }}>{source}</TableCell>
              <TableCell>{meaning}</TableCell>
              <TableCell>{band}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/** A scale with the typical agent's score and the cutoff marked; the cutoff comes from /api/model-info. */
function ScoreScale({ cutoff }) {
  // The scale runs from 0 to twice the cutoff, so the cutoff sits in the middle.
  const at = (value) => `${Math.min(value / (2 * cutoff), 1) * 100}%`;
  const mark = (value, label) => (
    <Box sx={{ position: "absolute", left: at(value), top: 0, transform: "translateX(-50%)", textAlign: "center" }}>
      <Box sx={{ width: 2, height: 18, bgcolor: "text.primary", mx: "auto" }} />
      <Typography sx={{ fontSize: 13, mt: 0.75, whiteSpace: "nowrap", ...tabular }}>{label}</Typography>
    </Box>
  );
  return (
    <Box role="img" aria-label={`Score scale with a typical agent at about 1 and the cutoff at ${cutoff.toFixed(3)}`}
      sx={{ position: "relative", height: 56, mx: { xs: 6, sm: 8 }, mt: 1 }}>
      <Box sx={{ position: "absolute", left: 0, right: 0, top: 8, height: 2, bgcolor: "divider" }} />
      {mark(1, "Typical agent, about 1")}
      {mark(cutoff, `Cutoff, ${cutoff.toFixed(3)}`)}
    </Box>
  );
}

function Summary({ info }) {
  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(3, minmax(0, 1fr))" } }}>
      {SYSTEMS.map(([key, label]) => {
        const r = info.results[key];
        return (
          <Paper key={key} component="article" aria-label={label} sx={card}>
            <Typography component="h3" sx={{ fontSize: 15, fontWeight: 600, mb: 1.5 }}>{label}</Typography>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
              {[["Precision", r.precision, `${r.tp} of ${r.flagged}`], ["Recall", r.recall, `${r.tp} of ${r.tp + r.fn}`]].map(([name, value, counts]) => (
                <Box key={name}>
                  <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{name}</Typography>
                  <Typography sx={{ fontFamily: (th) => th.typography.h1.fontFamily, fontSize: 30, fontWeight: 500, lineHeight: 1.2, ...tabular }}>{two(value)}</Typography>
                  <Typography sx={{ fontSize: 13, color: "text.secondary", ...tabular }}>{counts}</Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        );
      })}
    </Box>
  );
}

function FullResults({ info }) {
  const head = { fontSize: 13, fontWeight: 500, color: "text.secondary" };
  return (
    <>
      <TableContainer component={Paper} sx={{ ...card, p: 0, mt: 2 }}>
        <Table size="small" aria-label="Test results">
          <TableHead>
            <TableRow>
              <TableCell sx={head}>What flags agents</TableCell>
              <TableCell align="right" sx={head}>Flagged</TableCell>
              <TableCell sx={head}>Precision</TableCell>
              <TableCell sx={head}>Recall</TableCell>
              <TableCell sx={head}>PR AUC</TableCell>
              <TableCell sx={head}>ROC AUC</TableCell>
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
      <Typography sx={{ fontSize: 14, mt: 1.5 }}>
        {"The model flags an agent whose score is at or above the cutoff of "}
        <Box component="span" sx={mono}>{info.cutoff.toFixed(3)}</Box>
        {`. It was chosen on separate ${info.cutoff_chosen_on} agents, before the test, to balance missed fraud against false alarms (rule: "${info.cutoff_rule}", the cost of a missed fraud agent against a false alarm).`}
      </Typography>
    </>
  );
}

function TestResults({ info }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Summary info={info} />
      <Box sx={{ mt: 2, display: "grid", gap: 0.5 }}>
        <Typography sx={{ fontSize: 14 }}>{`Measured once on ${info.test_agents} held out test agents, ${info.test_fraud_agents} of them fraud.`}</Typography>
        <Typography sx={{ fontSize: 14 }}>Not a promise for other data.</Typography>
        <Typography sx={{ fontSize: 14 }}>The rule never wrongly flagged an honest test agent; that comes from how the test data was made.</Typography>
      </Box>
      <Button size="small" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="full-results" sx={{ mt: 1.5, px: 0 }}>
        {open ? "Hide full results" : "Show full results"}
      </Button>
      {open && <Box id="full-results"><FullResults info={info} /></Box>}
    </>
  );
}

function Glossary() {
  return (
    <Box>
      {GLOSSARY.map(([term, meaning]) => (
        <Accordion key={term} disableGutters elevation={0} square
          sx={{ border: 1, borderColor: "divider", "&:not(:last-of-type)": { borderBottom: 0 }, "&::before": { display: "none" }, bgcolor: "background.paper" }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
            <Typography sx={{ fontSize: 15, fontWeight: 500 }}>{term}</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 2, pt: 0 }}>
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{meaning}</Typography>
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}

/** The detection guide (issue #28), for every role. Every figure comes from /api/model-info, read from the frozen results. */
export default function DetectionGuide() {
  const result = useApi(api.getModelInfo);
  const run = useLatestRun();
  const info = result.data;
  const lastRun = run.data?.run;

  return (
    <Box sx={{ maxWidth: WIDTH }}>
      <PageHeader title="Detection guide" subtitle="How agents are flagged, and how to read the numbers." />
      <Section title="How a flag is made"><Steps info={info} /></Section>
      <Section title="What the model looks at"><Signals /></Section>
      <Section title="Flag sources and risk bands"><FlagSources /></Section>
      <Section title="Reading a score">
        {info ? <ScoreScale cutoff={info.cutoff} /> : <LoadStatus result={result} />}
        <Typography sx={{ fontSize: 14, mt: 2 }}>
          Scores and ranks are not probabilities. A flag asks a person to look; it is not a finding of fraud.
        </Typography>
      </Section>
      <Section title="How well it did on test agents">
        {info ? <TestResults info={info} /> : <LoadStatus result={result} />}
      </Section>
      <Section title="Glossary"><Glossary /></Section>
      {info && (
        <Typography data-testid="guide-footer" sx={{ fontSize: 13, color: "text.secondary", borderTop: 1, borderColor: "divider", pt: 2 }}>
          {`Model ${info.model_version}. Last detection run ${lastRun ? formatDateTime(lastRun.finished_at || lastRun.started_at) : "not yet"}`}
        </Typography>
      )}
    </Box>
  );
}
