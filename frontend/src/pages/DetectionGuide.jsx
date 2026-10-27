import { useEffect, useRef, useState } from "react";
import {
  Accordion, AccordionDetails, AccordionSummary, Box, Button, Chip, Link, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMoreOutlined";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import RiskBadge from "../components/RiskBadge";
import { FlagSourceChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { FEATURE_NAMES } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const MAX_WIDTH = 1200;
const CONTENT = 880;
const card = { p: 2.5, borderRadius: "8px", boxShadow: "none" };
const tabular = { fontVariantNumeric: "tabular-nums" };
// Every agent's score in the latest run (the endpoint's maximum page; the data has 1000 agents).
const loadScores = () => api.getAgentScores({ limit: 1000 });
const BIN = 0.1;
const CLIP = 4;

const SECTIONS = [
  ["how-a-flag-is-made", "How a flag is made"],
  ["what-the-model-looks-at", "What the model looks at"],
  ["flag-sources-and-risk-bands", "Flag sources and risk bands"],
  ["reading-a-score", "Reading a score"],
  ["how-well-it-did", "How well it did on test agents"],
  ["glossary", "Glossary"],
];

const STEPS = [
  ["Collect activations", "Every activation an agent submitted in the analysis period."],
  ["Compare with other agents", "Four signals per agent, measured against all the others."],
  ["Score", "One number for how unusual the agent is; a typical agent scores about 1."],
  ["Flag at the cutoff", "Agents at or above the cutoff are flagged for review."],
  ["A person reviews", "An analyst proposes an outcome and a compliance officer agrees or overrules it."],
];

const SIGNALS = [
  ["Timing", FEATURE_NAMES.submission_frequency, "The most activations the agent submitted in any 24 hours.", "Unusual when the agent submits far more in a day than agents usually manage."],
  ["Rhythm", FEATURE_NAMES.time_of_day_dist, "How evenly the agent's activations spread over the hours of the day.", "Unusual when work is packed into a few odd hours, or spread over every hour."],
  ["Identity", FEATURE_NAMES.customer_similarity, "How alike the customer IDs the agent enters are.", "Unusual when many IDs are near identical, such as numbers in a sequence."],
  ["Sharing", FEATURE_NAMES.collusion_score, "The share of the agent's customers that other agents also activated.", "Unusual when many customers are shared; honest agents rarely share them."],
];

// Flag source (as the API names it), what it means, and the risk bands it leads to (risk.py).
const FLAG_SOURCES = [
  ["ML", "The model flagged the agent.", ["high"]],
  ["Rule", "Only the duplicate activation rule flagged the agent.", ["review"]],
  ["Both", "Both flagged the agent.", ["high"]],
  ["None", "Neither flagged the agent. Review when the score is close to the cutoff, otherwise Low.", ["review", "low"]],
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

function prefersReducedMotion() {
  return typeof window !== "undefined" && Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
}

/** The accent for text on the page surface: the deeper blue in light, the lighter one in dark (AA either way). */
function useAccent() {
  const { palette } = useTheme();
  const dark = palette.mode === "dark";
  return { accent: dark ? palette.primary.main : palette.primary.dark, dark, palette };
}

/**
 * Soft flowing lines drifting slowly behind the hero, at about 8% in the accent. Canvas, no library. It pauses
 * while the tab is hidden and is drawn once, still, when reduced motion is preferred. Decorative.
 */
function FlowingLines() {
  const ref = useRef(null);
  const { accent } = useAccent();
  useEffect(() => {
    const canvas = ref.current;
    const context = canvas?.getContext?.("2d");
    if (!context) return undefined;
    const still = prefersReducedMotion();
    let frame = null;
    let width = 0;
    let height = 0;
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };
    const draw = (t) => {
      context.clearRect(0, 0, width, height);
      context.strokeStyle = accent;
      context.lineWidth = 1;
      for (let i = 0; i < 9; i += 1) {
        const base = height * (0.15 + i * 0.09);
        context.globalAlpha = 0.06 + (i % 3) * 0.01;
        context.beginPath();
        for (let x = 0; x <= width; x += 8) {
          const y = base + Math.sin(x / (170 + i * 23) + t / (9000 + i * 700) + i) * (14 + i * 2)
            + Math.sin(x / 61 + t / 5200 + i * 2) * 4;
          if (x === 0) context.moveTo(x, y); else context.lineTo(x, y);
        }
        context.stroke();
      }
      context.globalAlpha = 1;
    };
    const tick = (t) => {
      draw(t);
      frame = requestAnimationFrame(tick);
    };
    const start = () => { if (!still && frame === null && !document.hidden) frame = requestAnimationFrame(tick); };
    const stop = () => { if (frame !== null) cancelAnimationFrame(frame); frame = null; };
    const onVisibility = () => (document.hidden ? stop() : start());
    resize();
    draw(0);
    start();
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => { resize(); draw(performance.now()); }) : null;
    observer?.observe(canvas);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      observer?.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [accent]);
  return (
    <Box
      component="canvas"
      ref={ref}
      aria-hidden="true"
      data-testid="hero-lines"
      sx={{
        position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none",
        // Fades into the page surface towards the bottom and the right edge.
        maskImage: "linear-gradient(to bottom, black 35%, transparent), linear-gradient(to right, black 70%, transparent)",
        maskComposite: "intersect",
        WebkitMaskImage: "linear-gradient(to bottom, black 35%, transparent)",
      }}
    />
  );
}

/** A section that fades up 8px once as it enters the view (not at all with reduced motion). */
function Section({ id, title, children }) {
  const ref = useRef(null);
  const [shown, setShown] = useState(() => prefersReducedMotion() || typeof IntersectionObserver === "undefined");
  useEffect(() => {
    if (shown) return undefined;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setShown(true);
        observer.disconnect();
      }
    }, { threshold: 0.08 });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [shown]);
  return (
    <Box
      component="section"
      id={id}
      ref={ref}
      aria-labelledby={`${id}-title`}
      sx={{
        mb: 6, scrollMarginTop: 24,
        opacity: shown ? 1 : 0, transform: shown ? "none" : "translateY(8px)",
        transition: "opacity 320ms ease-out, transform 320ms ease-out",
        "@media (prefers-reduced-motion: reduce)": { opacity: 1, transform: "none", transition: "none" },
      }}
    >
      <Typography id={`${id}-title`} component="h2" sx={{ fontSize: 20, fontWeight: 600, mb: 2 }}>{title}</Typography>
      {children}
    </Box>
  );
}

/** The sticky "On this page" list (1200px and up), marking the section in view. */
function OnThisPage() {
  const { accent } = useAccent();
  const [active, setActive] = useState(SECTIONS[0][0]);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible[0]) setActive(visible[0].target.id);
    }, { rootMargin: "0px 0px -60% 0px" });
    for (const [id] of SECTIONS) {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);
  return (
    <Box component="nav" aria-label="On this page" sx={{ display: { xs: "none", lg: "block" }, position: "sticky", top: 24, alignSelf: "start" }}>
      <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 1.5 }}>On this page</Typography>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, borderLeft: 1, borderColor: "divider" }}>
        {SECTIONS.map(([id, title]) => (
          <li key={id}>
            <Link
              href={`#${id}`}
              underline="hover"
              aria-current={active === id ? "location" : undefined}
              sx={{
                display: "block", fontSize: 13, py: 0.75, pl: 1.5, ml: "-1px", borderLeft: 2,
                borderColor: active === id ? accent : "transparent",
                color: active === id ? accent : "text.secondary", fontWeight: active === id ? 500 : 400,
              }}
            >
              {title}
            </Link>
          </li>
        ))}
      </Box>
    </Box>
  );
}

function Badge({ children }) {
  const { accent, dark } = useAccent();
  return (
    <Box aria-hidden="true" sx={{
      width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
      bgcolor: (th) => alpha(th.palette.primary.main, dark ? 0.18 : 0.1), color: accent, fontSize: 13, fontWeight: 600,
      position: "relative", zIndex: 1, boxShadow: (th) => `0 0 0 4px ${th.palette.background.default}`, ...tabular,
    }}>
      {children}
    </Box>
  );
}

function Steps({ info }) {
  return (
    <>
      <Box component="ol" sx={{
        listStyle: "none", m: 0, p: 0, position: "relative", display: "grid", gap: { xs: 2.5, md: 2 },
        gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(5, minmax(0, 1fr))" },
        // The thin line joining the steps: across the badges on wide screens, down them on narrow ones.
        "&::before": {
          content: '""', position: "absolute", bgcolor: "divider",
          top: { xs: 14, md: 13 }, bottom: { xs: 14, md: "auto" }, left: { xs: 13, md: 14 }, right: { xs: "auto", md: 14 },
          width: { xs: "1px", md: "auto" }, height: { xs: "auto", md: "1px" },
        },
      }}>
        {STEPS.map(([name, line], i) => (
          <Box component="li" key={name} sx={{ display: "flex", flexDirection: { xs: "row", md: "column" }, gap: 1.5, minWidth: 0 }}>
            <Badge>{i + 1}</Badge>
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontSize: 15, fontWeight: 600, mb: 0.25 }}>{name}</Typography>
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{line}</Typography>
            </Box>
          </Box>
        ))}
      </Box>
      {info && (
        <Typography sx={{ fontSize: 14, mt: 3 }}>
          {`Detection runs on a schedule, ${every(info.detection_interval_minutes)} by default. Every page shows the results of the latest run.`}
        </Typography>
      )}
    </>
  );
}

function TintChip({ label }) {
  const { accent, dark } = useAccent();
  return (
    <Chip size="small" label={label} sx={{
      height: 22, fontSize: 12, fontWeight: 500, color: accent, borderRadius: "6px",
      bgcolor: (th) => alpha(th.palette.primary.main, dark ? 0.16 : 0.08),
    }} />
  );
}

function SignalCard({ chip, name, sentence, unusual, sx }) {
  const { accent, dark } = useAccent();
  return (
    <Paper component="article" aria-label={name} sx={{
      ...card, transition: "border-color 120ms ease", "&:hover": { borderColor: alpha(accent, 0.4) }, ...sx,
    }}>
      <TintChip label={chip} />
      <Typography component="h3" sx={{ fontSize: 16, fontWeight: 600, mt: 1.25, mb: 0.5 }}>{name}</Typography>
      <Typography sx={{ fontSize: 14, mb: unusual ? 1.5 : 0 }}>{sentence}</Typography>
      {unusual && (
        <Box sx={{
          px: 1.5, py: 1, borderLeft: 2, borderColor: accent, borderRadius: "0 6px 6px 0",
          bgcolor: (th) => alpha(th.palette.primary.main, dark ? 0.08 : 0.04),
        }}>
          <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{unusual}</Typography>
        </Box>
      )}
    </Paper>
  );
}

function Signals() {
  return (
    <>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))" } }}>
        {SIGNALS.map(([chip, name, sentence, unusual]) => (
          <SignalCard key={name} chip={chip} name={name} sentence={sentence} unusual={unusual} />
        ))}
      </Box>
      <SignalCard
        chip="Rule"
        name="The duplicate activation rule"
        sentence="Beside the model, a simple rule flags an agent when the same customer and client pair appears twice where it should not: used by another agent too, or repeated by the same agent after it was already completed."
        sx={{ mt: 2 }}
      />
    </>
  );
}

function FlagSources() {
  const head = { fontSize: 13, fontWeight: 500, color: "text.secondary" };
  return (
    <TableContainer component={Paper} sx={{ ...card, p: 0 }}>
      <Table size="small" aria-label="Flag sources and risk bands" sx={{ "& td": { borderColor: "divider", py: 1.25 }, "& tbody tr:last-of-type td": { borderBottom: 0 } }}>
        <TableHead>
          <TableRow>
            <TableCell sx={head}>Flagged by</TableCell>
            <TableCell sx={{ ...head, display: { xs: "none", sm: "table-cell" } }}>Meaning</TableCell>
            <TableCell sx={head}>Risk band</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {FLAG_SOURCES.map(([source, meaning, bands]) => (
            <TableRow key={source}>
              <TableCell>
                <FlagSourceChip source={source} />
                {/* On phones the meaning sits under the chip instead of in its own narrow column. */}
                <Typography sx={{ display: { xs: "block", sm: "none" }, fontSize: 13, color: "text.secondary", mt: 0.75 }}>{meaning}</Typography>
              </TableCell>
              <TableCell sx={{ fontSize: 14, display: { xs: "none", sm: "table-cell" } }}>{meaning}</TableCell>
              <TableCell>
                <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>{bands.map((b) => <RiskBadge key={b} band={b} />)}</Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/** Agents per 0.1 of score in the latest run, from 0 to CLIP; scores above CLIP are counted in the last bar. */
function scoreBins(scores) {
  const values = scores.map((s) => s.anomaly_score).filter((v) => Number.isFinite(v));
  const bins = Array.from({ length: Math.round(CLIP / BIN) }, (_, i) => ({ start: Math.round(i * BIN * 10) / 10, agents: 0 }));
  for (const v of values) {
    const i = Math.min(bins.length - 1, Math.max(0, Math.floor(v / BIN)));
    bins[i].agents += 1;
  }
  return { bins: bins.map((b) => ({ ...b, mid: Math.round((b.start + BIN / 2) * 100) / 100 })), total: values.length, above: values.filter((v) => v >= CLIP).length };
}

function ScoreChart({ scores, cutoff }) {
  const { accent, palette } = useAccent();
  const { bins, total, above } = scoreBins(scores);
  const axis = { fill: palette.text.secondary, fontSize: 12 };
  const label = (value, position) => ({ value, position, fill: palette.text.primary, fontSize: 12 });
  return (
    <Paper sx={{ ...card, pt: 3 }}>
      <Box role="img" aria-label={`Histogram of the scores of ${total} agents in the latest run, with a typical agent at about 1 and the cutoff at ${cutoff.toFixed(3)}.`}>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={bins} margin={{ top: 28, right: 12, bottom: 8, left: 0 }} barCategoryGap={1}>
            <CartesianGrid vertical={false} stroke={palette.divider} />
            <XAxis dataKey="mid" type="number" domain={[0, CLIP]} ticks={[0, 1, 2, 3, 4]} tickFormatter={(v) => (v === CLIP ? `${CLIP}+` : String(v))}
              tick={axis} axisLine={{ stroke: palette.divider }} tickLine={false} />
            <YAxis allowDecimals={false} tick={axis} axisLine={false} tickLine={false} width={40} />
            <Tooltip
              cursor={{ fill: palette.action.selected }}
              formatter={(value) => [value, "Agents"]}
              labelFormatter={(mid) => `Score ${(mid - BIN / 2).toFixed(1)} to ${(mid + BIN / 2).toFixed(1)}`}
              contentStyle={{ background: palette.background.paper, border: `1px solid ${palette.divider}`, color: palette.text.primary }}
            />
            <Bar dataKey="agents" fill={alpha(accent, 0.55)} isAnimationActive={false} />
            <ReferenceLine x={1} stroke={palette.text.secondary} strokeDasharray="3 3" label={label("Typical agent, about 1", "insideTopRight")} />
            <ReferenceLine x={cutoff} stroke={accent} strokeWidth={1.5} label={label(`Cutoff, ${cutoff.toFixed(3)}`, "insideTopLeft")} />
          </BarChart>
        </ResponsiveContainer>
      </Box>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 1 }}>
        {`Scores of the ${total} agents in the latest run, in steps of ${BIN}.${above ? ` The last bar also counts ${above} ${above === 1 ? "agent" : "agents"} scoring ${CLIP} or more.` : ""}`}
      </Typography>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 0.5 }}>
        This chart includes agents the model learned from, so use the test results below for accuracy.
      </Typography>
    </Paper>
  );
}

function Proportion({ part, whole }) {
  const { accent, palette } = useAccent();
  const share = whole > 0 ? part / whole : 0;
  return (
    <Box aria-hidden="true" sx={{ height: 4, borderRadius: 2, bgcolor: palette.divider, mt: 0.75, mb: 0.5, overflow: "hidden" }}>
      <Box sx={{ height: "100%", width: `${share * 100}%`, bgcolor: accent }} />
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
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2.5 }}>
              {[["Precision", r.precision, r.tp, r.flagged], ["Recall", r.recall, r.tp, r.tp + r.fn]].map(([name, value, part, whole]) => (
                <Box key={name}>
                  <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{name}</Typography>
                  <Typography sx={{ fontFamily: (th) => th.typography.h1.fontFamily, fontSize: 30, fontWeight: 500, lineHeight: 1.2, ...tabular }}>{two(value)}</Typography>
                  <Proportion part={part} whole={whole} />
                  <Typography sx={{ fontSize: 13, color: "text.secondary", ...tabular }}>{`${part} of ${whole}`}</Typography>
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
      <Typography sx={{ fontSize: 14, color: "text.secondary", mt: 1.5 }}>
        In brackets: the counts behind each figure, and the likely range (95% interval) for PR AUC and ROC AUC on another sample of the same size.
      </Typography>
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
      <Box sx={{ mt: 2.5, display: "grid", gap: 0.5 }}>
        <Typography sx={{ fontSize: 14 }}>{`Measured once on ${info.test_agents} held out test agents, ${info.test_fraud_agents} of them fraud.`}</Typography>
        <Typography sx={{ fontSize: 14 }}>{`Accuracy figures come only from these ${info.test_agents} test agents. Scores shown for other agents include agents the model learned from.`}</Typography>
        <Typography sx={{ fontSize: 14 }}>Not a promise for other data.</Typography>
        <Typography sx={{ fontSize: 14 }}>The rule never wrongly flagged an honest test agent; that comes from how the test data was made.</Typography>
      </Box>
      <Button variant="outlined" size="small" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="full-results" sx={{ mt: 2 }}>
        {open ? "Hide full results" : "Show full results"}
      </Button>
      {open && <Box id="full-results"><FullResults info={info} /></Box>}
    </>
  );
}

function Glossary() {
  const { accent } = useAccent();
  return (
    <Paper sx={{ ...card, p: 0, overflow: "hidden" }}>
      {GLOSSARY.map(([term, meaning]) => (
        <Accordion key={term} disableGutters elevation={0} square sx={{
          bgcolor: "transparent", "&::before": { display: "none" }, "&:not(:last-of-type)": { borderBottom: 1, borderColor: "divider" },
          "&.Mui-expanded .MuiAccordionSummary-expandIconWrapper": { color: accent },
        }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2.5 }}>
            <Typography sx={{ fontSize: 15, fontWeight: 500 }}>{term}</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 2.5, pt: 0 }}>
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{meaning}</Typography>
          </AccordionDetails>
        </Accordion>
      ))}
    </Paper>
  );
}

/**
 * The detection guide (issue #28), for every role. Figures come from /api/model-info (the frozen results) and
 * the score chart from /api/agent-scores (the latest run). The model version and last run are in the app footer.
 */
export default function DetectionGuide() {
  useDocumentTitle("Detection guide");
  const result = useApi(api.getModelInfo);
  const scores = useApi(loadScores);
  const info = result.data;

  return (
    <Box sx={{ maxWidth: MAX_WIDTH }}>
      {/* Hero band: title and subtitle over the faint flowing lines. */}
      <Box sx={{ position: "relative", overflow: "hidden", mx: { xs: -2, sm: -3 }, px: { xs: 2, sm: 3 }, pt: { xs: 3, md: 5 }, pb: { xs: 4, md: 6 }, mb: 4 }}>
        <FlowingLines />
        <Box sx={{ position: "relative" }}>
          <Typography component="h1" sx={{ fontFamily: (th) => th.typography.h1.fontFamily, fontSize: { xs: 34, md: 44 }, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1.1, mb: 1.5 }}>
            Detection guide
          </Typography>
          <Typography sx={{ fontSize: { xs: 16, md: 18 }, color: "text.secondary", maxWidth: 640 }}>
            How agents are flagged, and how to read the numbers.
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: `minmax(0, ${CONTENT}px) 200px` }, columnGap: 6 }}>
        <Box sx={{ minWidth: 0 }}>
          <Section id="how-a-flag-is-made" title="How a flag is made"><Steps info={info} /></Section>
          <Section id="what-the-model-looks-at" title="What the model looks at"><Signals /></Section>
          <Section id="flag-sources-and-risk-bands" title="Flag sources and risk bands"><FlagSources /></Section>
          <Section id="reading-a-score" title="Reading a score">
            {info && scores.data ? <ScoreChart scores={scores.data.scores || []} cutoff={info.cutoff} /> : <LoadStatus result={info ? scores : result} />}
            <Typography sx={{ fontSize: 14, mt: 2 }}>
              Scores and ranks are not probabilities. A flag asks a person to look; it is not a finding of fraud.
            </Typography>
          </Section>
          <Section id="how-well-it-did" title="How well it did on test agents">
            {info ? <TestResults info={info} /> : <LoadStatus result={result} />}
          </Section>
          <Section id="glossary" title="Glossary"><Glossary /></Section>
        </Box>
        <OnThisPage />
      </Box>
    </Box>
  );
}
