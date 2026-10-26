import { useId } from "react";
import { Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { FLAG_STEPS, STEPS } from "./flowDiagramContent";

const SIGNALS = ["Busiest 24 hours", "Time of day", "Customer ID patterns", "Shared customers"];

/** Two fixed layouts: wide (side by side) and tall (stacked for narrow screens). Nothing is random. */
const LAYOUTS = {
  wide: {
    width: 780, height: 372,
    signals: SIGNALS.map((label, i) => ({ label, x: 10, y: 14 + i * 44, w: 190, h: 34 })),
    records: { x: 10, y: 214, w: 190, h: 40, lines: ["Activation records"] },
    model: { x: 240, y: 60, w: 130, h: 72, lines: ["Model", "scores each agent"] },
    rule: { x: 240, y: 196, w: 130, h: 76, lines: ["Duplicate", "activation rule"] },
    flag: { x: 412, y: 86, w: 140, h: 162, title: "Flag" },
    analyst: { x: 594, y: 40, w: 176, h: 76, lines: ["Fraud analyst", "proposes an outcome", "with a note"] },
    officer: { x: 594, y: 168, w: 176, h: 76, lines: ["Compliance officer", "agrees or overrules"] },
    audit: { x: 10, y: 314, w: 760, h: 44, lines: ["Audit log: every step is written here and never changed"] },
    pillsVertical: true,
  },
  tall: {
    width: 340, height: 732,
    // On narrow screens the four signals share one box, so one arrow clearly carries all four to the model.
    signalGroup: { x: 10, y: 10, w: 154, h: 150, title: "Four signals" },
    signals: [],
    records: { x: 172, y: 65, w: 154, h: 40, lines: ["Activation records"] },
    model: { x: 10, y: 196, w: 154, h: 64, lines: ["Model", "scores each agent"] },
    rule: { x: 172, y: 196, w: 154, h: 64, lines: ["Duplicate", "activation rule"] },
    flag: { x: 10, y: 304, w: 316, h: 92, title: "Flag" },
    analyst: { x: 10, y: 440, w: 316, h: 64, lines: ["Fraud analyst", "proposes an outcome with a note"] },
    officer: { x: 10, y: 548, w: 316, h: 64, lines: ["Compliance officer", "agrees or overrules"] },
    audit: { x: 10, y: 656, w: 316, h: 64, lines: ["Audit log: every step is", "written here and never changed"] },
    pillsVertical: false,
  },
};

function Node({ box, lines, stroke, fill, text, bold = true }) {
  const lineHeight = 17;
  const top = box.y + box.h / 2 - ((lines.length - 1) * lineHeight) / 2;
  return (
    <g>
      <rect x={box.x} y={box.y} width={box.w} height={box.h} rx={6} fill={fill} stroke={stroke} strokeWidth={1.5} />
      {lines.map((line, i) => (
        <text key={line} x={box.x + box.w / 2} y={top + i * lineHeight} textAnchor="middle" dominantBaseline="central"
          fontSize={14} fontWeight={i === 0 && bold ? 600 : 400} fill={text}>
          {line}
        </text>
      ))}
    </g>
  );
}

/**
 * How a flag is made (issue #28), as one inline SVG in the theme's colours. It has a title and description,
 * and the same steps as an ordered list for screen readers. Deterministic: two fixed layouts, chosen by
 * the `tall` prop (stacked for narrow screens).
 */
export default function FlowDiagram({ tall = false }) {
  const theme = useTheme();
  const id = useId();
  const L = LAYOUTS[tall ? "tall" : "wide"];
  const c = {
    line: theme.palette.text.secondary,
    border: theme.palette.divider,
    card: theme.palette.background.paper,
    text: theme.palette.text.primary,
    muted: theme.palette.text.secondary,
  };
  const marker = `${id}-arrow`.replace(/:/g, "");
  const arrow = (x1, y1, x2, y2, dashed = false) => (
    <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={c.line} strokeWidth={1.5} strokeDasharray={dashed ? "4 4" : undefined}
      markerEnd={dashed ? undefined : `url(#${marker})`} />
  );
  const mid = (b) => ({ x: b.x + b.w / 2, y: b.y + b.h / 2, r: b.x + b.w, b: b.y + b.h });
  const { model, rule, flag, analyst, officer, audit, records } = L;
  const pill = { w: L.pillsVertical ? 112 : 92, h: 30 };

  return (
    <Box>
      <Box
        component="svg"
        viewBox={`0 0 ${L.width} ${L.height}`}
        role="img"
        aria-labelledby={`${id}-title ${id}-desc`}
        sx={{ width: "100%", height: "auto", display: "block", mx: "auto", maxWidth: tall ? 420 : "100%" }}
      >
        <title id={`${id}-title`}>How a flag is made</title>
        <desc id={`${id}-desc`}>{STEPS.join(" ")}</desc>
        <defs>
          <marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={c.line} />
          </marker>
        </defs>

        {L.signals.map((s) => (
          <Node key={s.label} box={s} lines={[s.label]} stroke={c.border} fill={c.card} text={c.text} bold={false} />
        ))}
        {L.signalGroup && (
          <g>
            <rect x={L.signalGroup.x} y={L.signalGroup.y} width={L.signalGroup.w} height={L.signalGroup.h} rx={6}
              fill={c.card} stroke={c.border} strokeWidth={1.5} />
            <text x={L.signalGroup.x + 12} y={L.signalGroup.y + 22} fontSize={14} fontWeight={600} fill={c.text}>{L.signalGroup.title}</text>
            {SIGNALS.map((label, i) => (
              <text key={label} x={L.signalGroup.x + 12} y={L.signalGroup.y + 50 + i * 26} fontSize={13} fill={c.text}>{label}</text>
            ))}
          </g>
        )}
        <Node box={records} lines={records.lines} stroke={c.border} fill={c.card} text={c.text} bold={false} />
        <Node box={model} lines={model.lines} stroke={c.line} fill={c.card} text={c.text} />
        <Node box={rule} lines={rule.lines} stroke={c.line} fill={c.card} text={c.text} />

        {tall ? (
          <>
            {arrow(87, L.signalGroup.y + L.signalGroup.h, 87, model.y - 2)}
            {arrow(mid(records).x, mid(records).b, mid(rule).x, rule.y - 2)}
            {arrow(mid(model).x, mid(model).b, mid(model).x, flag.y - 2)}
            {arrow(mid(rule).x, mid(rule).b, mid(rule).x, flag.y - 2)}
            {arrow(mid(flag).x, mid(flag).b, mid(flag).x, analyst.y - 2)}
            {arrow(mid(analyst).x, mid(analyst).b, mid(analyst).x, officer.y - 2)}
            {arrow(mid(officer).x, mid(officer).b, mid(officer).x, audit.y - 2, true)}
          </>
        ) : (
          <>
            {L.signals.map((s) => <g key={s.label}>{arrow(s.x + s.w, s.y + s.h / 2, model.x - 2, mid(model).y)}</g>)}
            {arrow(records.x + records.w, mid(records).y, rule.x - 2, mid(rule).y)}
            {arrow(model.x + model.w, mid(model).y, flag.x - 2, flag.y + 40)}
            {arrow(rule.x + rule.w, mid(rule).y, flag.x - 2, mid(flag).b - 40)}
            {arrow(flag.x + flag.w, flag.y + 40, analyst.x - 2, mid(analyst).y)}
            {arrow(mid(analyst).x, mid(analyst).b, mid(analyst).x, officer.y - 2)}
            {arrow(mid(rule).x, mid(rule).b, mid(rule).x, audit.y, true)}
            {arrow(mid(flag).x, mid(flag).b, mid(flag).x, audit.y, true)}
            {arrow(mid(officer).x, mid(officer).b, mid(officer).x, audit.y, true)}
          </>
        )}

        <rect x={flag.x} y={flag.y} width={flag.w} height={flag.h} rx={6} fill={c.card} stroke={c.line} strokeWidth={1.5} />
        <text x={flag.x + 12} y={flag.y + 22} fontSize={14} fontWeight={600} fill={c.text}>{flag.title}</text>
        {FLAG_STEPS.map((f, i) => {
          const x = L.pillsVertical ? flag.x + (flag.w - pill.w) / 2 : flag.x + 12 + i * (pill.w + 9);
          const y = L.pillsVertical ? flag.y + 38 + i * 40 : flag.y + 44;
          const colour = theme.palette.risk[f.band];
          return (
            <g key={f.key}>
              <rect x={x} y={y} width={pill.w} height={pill.h} rx={6} fill={c.card} stroke={colour} strokeWidth={2} />
              <circle cx={x + 14} cy={y + pill.h / 2} r={5} fill={colour} />
              <text x={x + 26} y={y + pill.h / 2} dominantBaseline="central" fontSize={13} fill={c.text}>{f.label}</text>
            </g>
          );
        })}

        <Node box={analyst} lines={analyst.lines} stroke={c.line} fill={c.card} text={c.text} />
        <Node box={officer} lines={officer.lines} stroke={c.line} fill={c.card} text={c.text} />
        <rect x={audit.x} y={audit.y} width={audit.w} height={audit.h} rx={6} fill="none" stroke={c.line} strokeWidth={1.5} strokeDasharray="6 4" />
        {audit.lines.map((line, i) => (
          <text key={line} x={audit.x + audit.w / 2} y={audit.y + audit.h / 2 + (i - (audit.lines.length - 1) / 2) * 17}
            textAnchor="middle" dominantBaseline="central" fontSize={14} fill={c.muted}>
            {line}
          </text>
        ))}
      </Box>
      <Box component="ol" sx={{ position: "absolute", width: "1px", height: "1px", p: 0, m: "-1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0 }}>
        {STEPS.map((step) => <li key={step}>{step}</li>)}
      </Box>
    </Box>
  );
}
