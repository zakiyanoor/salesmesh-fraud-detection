import { Box, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { RADIUS, useSurface } from "./surfaces";

// The drawings are 160 by 64; each is a small, thin-stroked picture of what its card says (issue #28).
const W = 160;
const H = 64;
const STROKE = 1.25;

function Drawing({ name, children }) {
  return (
    <Box component="svg" viewBox={`0 0 ${W} ${H}`} aria-hidden="true" focusable="false" data-testid={`drawing-${name}`}
      sx={{ display: "block", width: "100%", maxWidth: W, height: H, mb: 2.5, overflow: "visible" }}>
      {children}
    </Box>
  );
}

/** Detection: a row of agents, one raised above a dotted threshold. */
function DetectionDrawing({ t }) {
  const xs = [14, 36, 58, 80, 102, 124, 146];
  return (
    <Drawing name="detection">
      <line x1={4} x2={156} y1={28} y2={28} stroke={t.accentSoft} strokeWidth={STROKE} strokeDasharray="1.5 4" strokeLinecap="round" />
      <line x1={4} x2={156} y1={52} y2={52} stroke={t.rule} strokeWidth={1} />
      {xs.map((x, i) => (i === 4 ? null : <circle key={x} cx={x} cy={46} r={3} fill="none" stroke={t.accentSoft} strokeWidth={STROKE} />))}
      <line x1={102} x2={102} y1={46} y2={18} stroke={t.accentSoft} strokeWidth={1} strokeDasharray="1 3" />
      <g className="pc-lift">
        <circle cx={102} cy={14} r={8} fill="none" stroke={alpha(t.accent, 0.35)} strokeWidth={1} />
        <circle cx={102} cy={14} r={4} fill={t.accent} />
      </g>
    </Drawing>
  );
}

/** Review: two people joined by a line, the second agreeing. */
function ReviewDrawing({ t }) {
  return (
    <Drawing name="review">
      <line className="pc-draw" pathLength={1} x1={38} x2={114} y1={30} y2={30} stroke={t.accent} strokeWidth={STROKE} />
      <circle cx={30} cy={30} r={8} fill="none" stroke={t.accent} strokeWidth={STROKE} />
      <circle cx={30} cy={30} r={2.5} fill={t.accent} />
      <circle cx={122} cy={30} r={8} fill="none" stroke={t.accent} strokeWidth={STROKE} />
      <circle cx={122} cy={30} r={2.5} fill={t.accent} />
      <polyline className="pc-draw pc-late" pathLength={1} points="114,52 120,58 134,44" fill="none" stroke={t.accent}
        strokeWidth={STROKE + 0.25} strokeLinecap="round" strokeLinejoin="round" />
    </Drawing>
  );
}

/** Investigation: a small ring of connected agents, one highlighted. */
function InvestigationDrawing({ t }) {
  const nodes = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI * 2 * i) / 6 - Math.PI / 2;
    return [80 + 34 * Math.cos(a), 32 + 24 * Math.sin(a)];
  });
  const ring = nodes.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [hx, hy] = nodes[1];
  return (
    <Drawing name="investigation">
      <polygon className="pc-draw" pathLength={1} points={ring} fill="none" stroke={t.accentSoft} strokeWidth={STROKE} strokeLinejoin="round" />
      <line x1={nodes[0][0]} y1={nodes[0][1]} x2={nodes[3][0]} y2={nodes[3][1]} stroke={t.accentSoft} strokeWidth={1} strokeDasharray="1.5 3" />
      {nodes.map(([x, y], i) => (i === 1 ? null : (
        <circle key={i} cx={x} cy={y} r={3.5} fill={t.surface} stroke={t.accent} strokeWidth={STROKE} />
      )))}
      <g className="pc-pulse" style={{ transformOrigin: `${hx}px ${hy}px` }}>
        <circle cx={hx} cy={hy} r={9} fill="none" stroke={alpha(t.accent, 0.35)} strokeWidth={1} />
        <circle cx={hx} cy={hy} r={4.5} fill={t.accent} />
      </g>
    </Drawing>
  );
}

/** Accountability: log entries, the newest slightly brighter. */
function AccountabilityDrawing({ t }) {
  const rows = [[0, 92], [1, 70], [2, 104], [3, 58], [4, 84]];
  return (
    <Drawing name="accountability">
      {rows.map(([i, width]) => {
        const last = i === rows.length - 1;
        const y = 8 + i * 12;
        return (
          <g key={i} className="pc-row" style={{ animationDelay: `${i * 90}ms` }}>
            <circle cx={30} cy={y} r={1.6} fill={last ? t.accent : t.accentSoft} />
            <line x1={40} x2={40 + width} y1={y} y2={y} stroke={last ? t.accent : t.accentSoft}
              strokeWidth={last ? STROKE + 0.5 : STROKE} strokeLinecap="round" />
          </g>
        );
      })}
    </Drawing>
  );
}

const DRAWINGS = [DetectionDrawing, ReviewDrawing, InvestigationDrawing, AccountabilityDrawing];

// Each animation runs once when a card is hovered or focused; reduced motion skips them.
const ANIMATED = "&:hover, &:focus-visible";
const motion = {
  "@keyframes pcLift": { from: { transform: "translateY(32px)", opacity: 0.4 }, to: { transform: "none", opacity: 1 } },
  "@keyframes pcDraw": { from: { strokeDashoffset: 1 }, to: { strokeDashoffset: 0 } },
  "@keyframes pcPulse": { "0%": { transform: "scale(1)" }, "45%": { transform: "scale(1.35)" }, "100%": { transform: "scale(1)" } },
  "@keyframes pcAppear": { from: { opacity: 0, transform: "translateX(-6px)" }, to: { opacity: 1, transform: "none" } },
  "& .pc-draw": { strokeDasharray: 1 },
  [ANIMATED]: {
    "& .pc-lift": { animation: "pcLift 520ms cubic-bezier(.2,.7,.2,1) both" },
    "& .pc-draw": { animation: "pcDraw 560ms ease-out both" },
    "& .pc-draw.pc-late": { animationDelay: "380ms" },
    "& .pc-pulse": { animation: "pcPulse 600ms ease-out 300ms both" },
    "& .pc-row": { animationName: "pcAppear", animationDuration: "260ms", animationTimingFunction: "ease-out", animationFillMode: "both" },
  },
  "@media (prefers-reduced-motion: reduce)": { [ANIMATED]: { "& *": { animation: "none !important" } } },
};

/**
 * The four platform cards in one ruled grid (issue #28): a drawing, a mono numeral, a heading and the text.
 * Each card takes keyboard focus so its hover state (accent border, soft glow, drawing) is reachable by keyboard.
 */
export default function PlatformCards({ cards }) {
  const t = useSurface();
  return (
    <Box component="ul" sx={{
      listStyle: "none", m: 0, p: 0, display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
      gap: "1px", bgcolor: t.ruleStrong, border: `1px solid ${t.ruleStrong}`, borderRadius: RADIUS, overflow: "hidden",
    }}>
      {cards.map(([title, text], i) => {
        const Picture = DRAWINGS[i];
        const id = `platform-card-${i + 1}`;
        return (
          <Box component="li" key={title} sx={{ display: "flex" }}>
            <Box component="article" tabIndex={0} aria-labelledby={id} sx={{
              position: "relative", flex: 1, bgcolor: "background.paper", p: { xs: 2.5, md: 3 }, pt: { xs: 3.5, md: 4 },
              backgroundImage: t.cardTexture, backgroundSize: "12px 12px", backgroundPosition: "6px 6px",
              transition: "box-shadow 160ms ease",
              // A corner tick at the top left.
              "&::before": {
                content: '""', position: "absolute", top: 10, left: 10, width: 10, height: 10,
                borderTop: `1px solid ${t.accent}`, borderLeft: `1px solid ${t.accent}`,
              },
              "&:hover": { boxShadow: `inset 0 0 0 1px ${t.accent}, inset 0 0 8px ${alpha(t.accent, 0.28)}` },
              "&:focus-visible": { outline: "none", boxShadow: `inset 0 0 0 2px ${t.accent}, inset 0 0 8px ${alpha(t.accent, 0.32)}` },
              ...motion,
            }}>
              <Picture t={t} />
              <Typography aria-hidden="true" sx={{ fontFamily: (th) => th.typography.fontFamilyMono, fontSize: 13, color: t.accent, mb: 1, letterSpacing: "0.04em" }}>
                {String(i + 1).padStart(2, "0")}
              </Typography>
              <Typography id={id} component="h3" sx={{ fontSize: 18, fontWeight: 600, fontFamily: (th) => th.typography.h3.fontFamily, mb: 1, color: "text.primary" }}>
                {title}
              </Typography>
              <Typography sx={{ fontSize: 15, lineHeight: 1.6, color: "text.secondary" }}>{text}</Typography>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
