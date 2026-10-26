import { Box, Typography } from "@mui/material";
import { DecisionStatusChip, FlagSourceChip, OutcomeChip } from "../components/chips";
import RiskBadge from "../components/RiskBadge";
import { RADIUS, useSurface } from "./surfaces";
import { AUDIT_ROWS, FLAGGED_SUBTITLE, FLAGGED_TITLE, RANKED_AGENTS, REVIEW_STEPS, RING_COUNTIES, RING_PAIRS } from "./platformExcerpts";

const mono = { fontFamily: (th) => th.typography.fontFamilyMono };
const cell = { py: 1, px: { xs: 1, sm: 1.5 }, fontSize: 13, minWidth: 0, display: "flex", alignItems: "center" };
const head = { ...cell, py: 0.75, fontSize: 12, fontWeight: 500, color: "text.secondary" };

/**
 * A window into the product: the app's own chips and table styling on a slightly different surface. It is an
 * illustration (role img with a short description), so screen readers hear one sentence, not a fake table.
 */
function Excerpt({ label, children, sx }) {
  const t = useSurface();
  return (
    <Box role="img" aria-label={label} data-testid="excerpt" sx={{
      bgcolor: "background.default", border: `1px solid ${t.rule}`, borderRadius: "4px", overflow: "hidden", ...sx,
    }}>
      {children}
    </Box>
  );
}

const BREAKPOINTS = ["xs", "sm", "md"];

/**
 * Rows on one grid with the app's thin row rules. Each column is { label, width, from, align, render, sx };
 * a column with `from` shows from that breakpoint up, so narrow screens drop columns instead of clipping them.
 * With `fill`, the rows share the height the excerpt is given.
 */
function Rows({ columns, rows, fill = false }) {
  const t = useSurface();
  const shownAt = (c, bp) => BREAKPOINTS.indexOf(bp) >= BREAKPOINTS.indexOf(c.from || "xs");
  // A width is a length, or { xs, sm } for one that changes; every row uses the same lengths, so columns line up.
  const widthAt = (c, bp) => (typeof c.width === "string" ? c.width : c.width[bp] ?? c.width.sm ?? c.width.xs);
  const template = Object.fromEntries(BREAKPOINTS.map((bp) => [bp, columns.filter((c) => shownAt(c, bp)).map((c) => widthAt(c, bp)).join(" ")]));
  const display = (c) => (c.from ? { display: Object.fromEntries(BREAKPOINTS.map((bp) => [bp, shownAt(c, bp) ? "flex" : "none"])) } : {});
  const align = (c) => (c.align === "right" ? { justifyContent: "flex-end" } : {});
  const line = { display: "grid", gridTemplateColumns: template, borderBottom: `1px solid ${t.rule}`, "&:last-of-type": { borderBottom: 0 } };
  return (
    <Box sx={fill ? { flex: 1, display: "grid", gridTemplateRows: `auto repeat(${rows.length}, minmax(0, 1fr))` } : {}}>
      <Box sx={line}>{columns.map((c, j) => <Box key={j} sx={{ ...head, ...display(c), ...align(c) }}>{c.label}</Box>)}</Box>
      {rows.map((row, i) => (
        <Box key={i} sx={line}>
          {columns.map((c, j) => <Box key={j} sx={{ ...cell, ...display(c), ...align(c), ...c.sx }}>{c.render(row)}</Box>)}
        </Box>
      ))}
    </Box>
  );
}

function AgentCode({ id }) {
  const t = useSurface();
  return <Box component="span" sx={{ ...mono, color: t.link }}>{id}</Box>;
}

function DetectionExcerpt() {
  const t = useSurface();
  return (
    <Excerpt label="Example of the ranked list of flagged agents" sx={{ display: "flex", flexDirection: "column", flex: 1 }}>
      <Box sx={{ px: 1.5, py: 1.25, borderBottom: `1px solid ${t.rule}` }}>
        <Typography sx={{ fontSize: 14, fontWeight: 600, fontFamily: (th) => th.typography.h3.fontFamily }}>{FLAGGED_TITLE}</Typography>
        <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{FLAGGED_SUBTITLE}</Typography>
      </Box>
      <Rows
        fill
        rows={RANKED_AGENTS}
        columns={[
          { label: "Rank", width: "48px", render: (a) => a.rank, sx: { ...mono, color: "text.secondary" } },
          { label: "Agent ID", width: "minmax(0, 1fr)", render: (a) => <AgentCode id={a.agent_id} /> },
          { label: "Region", width: "minmax(0, 1fr)", from: "sm", render: (a) => a.region },
          { label: "Risk", width: "112px", from: "md", render: (a) => <RiskBadge band={a.risk_band} />, sx: { py: 0.5 } },
          { label: "Flagged by", width: "136px", render: (a) => <FlagSourceChip source={a.flag_source} />, sx: { py: 0.5 } },
          { label: "Review", width: "152px", from: "sm", render: (a) => <DecisionStatusChip status={a.review} />, sx: { py: 0.5 } },
        ]}
      />
    </Excerpt>
  );
}

function ReviewExcerpt() {
  const t = useSurface();
  const step = { position: "relative", pl: 2.5, "&::before": { content: '""', position: "absolute", left: 4, top: 7, width: 7, height: 7, borderRadius: "50%", border: `1.5px solid ${t.accent}`, bgcolor: "background.default" } };
  return (
    <Excerpt label="Example of a decision proposed by a fraud analyst and agreed by a compliance officer" sx={{ p: 1.75 }}>
      <Box sx={{ position: "relative", display: "grid", gap: 1.75, "&::before": { content: '""', position: "absolute", left: 7.5, top: 12, bottom: 12, borderLeft: `1px solid ${t.rule}` } }}>
        <Box sx={step}>
          <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.75 }}>{`Proposed by ${REVIEW_STEPS.proposedBy}`}</Typography>
          <OutcomeChip outcome={REVIEW_STEPS.outcome} />
        </Box>
        <Box sx={step}>
          <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.75 }}>{`Agreed by ${REVIEW_STEPS.agreedBy}`}</Typography>
          <DecisionStatusChip status="agreed" />
        </Box>
      </Box>
    </Excerpt>
  );
}

function InvestigationExcerpt() {
  const t = useSurface();
  return (
    <Excerpt label="Example of agents in a ring candidate that share customers, and their counties">
      <Rows
        rows={RING_PAIRS}
        columns={[
          { label: "Agent", width: "minmax(0, 1fr)", render: (p) => <AgentCode id={p.source} /> },
          { label: "Agent", width: "minmax(0, 1fr)", render: (p) => <AgentCode id={p.target} /> },
          { label: "Shared customers", width: "128px", align: "right", render: (p) => p.shared, sx: mono },
        ]}
      />
      <Typography sx={{ fontSize: 13, px: 1.5, py: 1, borderTop: `1px solid ${t.rule}` }}>
        {`${RING_COUNTIES.length} counties: ${RING_COUNTIES.join(", ")}.`}
      </Typography>
    </Excerpt>
  );
}

function AccountabilityExcerpt() {
  return (
    <Excerpt label="Example of audit log entries">
      <Rows
        rows={AUDIT_ROWS}
        columns={[
          { label: "Time", width: { xs: "56px", sm: "72px" }, render: (e) => e.time, sx: { ...mono, color: "text.secondary" } },
          // The action as the server records it, never broken mid-word; the role wraps instead.
          { label: "Action", width: { xs: "140px", sm: "200px" }, render: (e) => e.action, sx: { ...mono, whiteSpace: "nowrap" } },
          { label: "Role", width: "minmax(0, 1fr)", render: (e) => e.role },
        ]}
      />
    </Excerpt>
  );
}

const EXCERPTS = [DetectionExcerpt, ReviewExcerpt, InvestigationExcerpt, AccountabilityExcerpt];
// Uneven on purpose: Detection is the large card, Accountability a full-width strip underneath.
const AREAS = ["detection", "review", "investigation", "accountability"];

/** The four platform cards (issue #28): heading and text, then a short excerpt of the real interface. */
export default function PlatformCards({ cards }) {
  const t = useSurface();
  return (
    <Box component="ul" sx={{
      listStyle: "none", m: 0, p: 0, display: "grid", gap: 2,
      gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))", lg: "repeat(3, minmax(0, 1fr))" },
      gridTemplateAreas: {
        xs: '"detection" "review" "investigation" "accountability"',
        md: '"detection detection" "review investigation" "accountability accountability"',
        lg: '"detection detection review" "detection detection investigation" "accountability accountability accountability"',
      },
    }}>
      {cards.map(([title, text], i) => {
        const Shown = EXCERPTS[i];
        const wide = AREAS[i] === "accountability";
        const large = AREAS[i] === "detection";
        return (
          <Box component="li" key={title} data-testid={`card-${AREAS[i]}`} sx={{
            gridArea: AREAS[i], minWidth: 0, bgcolor: "background.paper", border: `1px solid ${t.ruleStrong}`, borderRadius: RADIUS,
            p: { xs: 2.5, md: large ? 4 : 3 }, transition: "border-color 120ms linear",
            "&:hover": { borderColor: t.accent },
            display: large ? "flex" : "grid", flexDirection: "column", gap: { xs: 2.5, md: 3 }, alignContent: "start",
            gridTemplateColumns: wide ? { xs: "minmax(0, 1fr)", md: "minmax(0, 1fr) minmax(0, 1.6fr)" } : "minmax(0, 1fr)",
            alignItems: wide ? "center" : "stretch",
          }}>
            <Box>
              <Typography component="h3" sx={{ fontSize: large ? { xs: 18, md: 22 } : 18, fontWeight: 600, fontFamily: (th) => th.typography.h3.fontFamily, mb: 1, color: "text.primary" }}>
                {title}
              </Typography>
              <Typography sx={{ fontSize: large ? { xs: 15, md: 16 } : 15, lineHeight: 1.6, color: "text.secondary", maxWidth: "52ch" }}>{text}</Typography>
            </Box>
            <Shown />
          </Box>
        );
      })}
    </Box>
  );
}
