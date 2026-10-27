import { useEffect, useMemo, useRef, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, Link, Typography } from "@mui/material";
import { darken, useTheme } from "@mui/material/styles";
import { useAuth } from "../auth/authContext";
import { canAccess } from "../auth/roles";
import { FLAG_SOURCE_LABELS } from "../format";
import { forceLayout, lineWidth } from "./ringLayout";

const FADED = 0.2;
const COUNTY_CHARS = 14;
const DRAG_THRESHOLD = 3;
const shorten = (text, max) => (text && text.length > max ? `${text.slice(0, max - 1)}…` : text || "");

/** The container's width, followed as it resizes (640 until it can be measured). */
function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(([entry]) => {
      const next = Math.round(entry.contentRect.width / 8) * 8;
      if (next > 0) setWidth(next);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

/**
 * How a dot is painted for its flag source, in the colours the app's chips use: the accent for the model, a
 * darker accent for model and rule, an accent outline for the rule only, and the Not flagged chip's green outline.
 */
function dotPaint(theme, source) {
  const accent = theme.palette.primary.main;
  if (source === "ML") return { fill: accent, stroke: accent };
  if (source === "Both") return { fill: darken(accent, 0.4), stroke: darken(accent, 0.4) };
  if (source === "Rule") return { fill: theme.palette.background.paper, stroke: accent };
  return { fill: theme.palette.background.paper, stroke: theme.palette.success.main };
}

function Legend({ theme, sources }) {
  const swatch = (source) => {
    const paint = dotPaint(theme, source);
    return (
      <Box component="svg" width={14} height={14} aria-hidden="true" sx={{ flexShrink: 0 }}>
        <circle cx={7} cy={7} r={5.5} fill={paint.fill} stroke={paint.stroke} strokeWidth={1.5} />
      </Box>
    );
  };
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", columnGap: 2, rowGap: 0.5, fontSize: 13, color: "text.secondary" }}>
      {sources.map((s) => (
        <Box key={s} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>{swatch(s)}{FLAG_SOURCE_LABELS[s]}</Box>
      ))}
      <Box component="span">Dot size is the agent&apos;s activations. Line thickness is the shared customers.</Box>
    </Box>
  );
}

/**
 * A ring candidate as a graph in plain SVG (issue #28), laid out by a deterministic force layout (ringLayout.js)
 * that settles at once, with no animation. Agents can be dragged; Reset layout puts them back. Hovering or
 * focusing an agent highlights it and its neighbours and fades the rest. Each agent is a button: Tab moves
 * between agents in agent ID order, Enter or Space (or a click) selects one and lists its pairs beside the graph,
 * Escape clears. The Members and Pairs tabs carry the same data as tables.
 */
export default function RingGraph({ graph }) {
  const theme = useTheme();
  const { user } = useAuth();
  const [ref, width] = useWidth();
  const svgRef = useRef(null);
  const dragRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const [pointed, setPointed] = useState(null);
  const layout = useMemo(() => forceLayout(graph.nodes, graph.edges, width), [graph, width]);
  // Dragged positions belong to one layout: a new group or width starts from the computed layout again.
  const [drags, setDrags] = useState({ layout: null, positions: {} });
  const moved = drags.layout === layout ? drags.positions : {};
  const setMoved = (update) => setDrags((current) => {
    const base = current.layout === layout ? current.positions : {};
    return { layout, positions: typeof update === "function" ? update(base) : update };
  });
  const at = (id) => ({ ...layout.nodes[id], ...moved[id] });
  const byId = Object.fromEntries(graph.nodes.map((n) => [n.agent_id, n]));
  const shared = graph.edges.map((e) => e.shared_customers);
  const [low, high] = [Math.min(...shared), Math.max(...shared)];
  const touches = (e, id) => e.source === id || e.target === id;
  const other = (e, id) => (e.source === id ? e.target : e.source);
  // Hover or focus wins over the selection for the highlight; the selection keeps the panel.
  const focus = pointed || selected;
  const neighbours = focus ? new Set([focus, ...graph.edges.filter((e) => touches(e, focus)).map((e) => other(e, focus))]) : null;
  const pairs = selected
    ? graph.edges.filter((e) => touches(e, selected)).sort((a, b) => b.shared_customers - a.shared_customers)
    : [];
  const toggle = (id) => setSelected((current) => (current === id ? null : id));
  const halo = { stroke: theme.palette.background.paper, strokeWidth: 4, paintOrder: "stroke", strokeLinejoin: "round" };
  const surface = theme.palette.mode === "dark" ? theme.palette.background.default : theme.palette.background.paper;
  const sources = ["ML", "Both", "Rule", "None"].filter((s) => graph.nodes.some((n) => (n.flag_source || "None") === s));
  const openable = canAccess(user?.role, "agentDetail");

  // Dragging: pointer coordinates turned into the SVG's own, kept inside the drawing.
  const toSvg = (event) => {
    const svg = svgRef.current;
    const matrix = svg?.getScreenCTM?.();
    if (!matrix) return null;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    return { x: Math.min(Math.max(point.x, 12), layout.width - 12), y: Math.min(Math.max(point.y, 12), layout.height - 12) };
  };
  const startDrag = (id) => (event) => {
    if (event.button !== 0) return;
    dragRef.current = { id, x: event.clientX, y: event.clientY, moved: false };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };
  const drag = (event) => {
    const d = dragRef.current;
    if (!d) return;
    if (!d.moved && Math.hypot(event.clientX - d.x, event.clientY - d.y) < DRAG_THRESHOLD) return;
    d.moved = true;
    const point = toSvg(event);
    if (point) setMoved((current) => ({ ...current, [d.id]: point }));
  };
  const endDrag = () => {
    const d = dragRef.current;
    dragRef.current = null;
    return d?.moved;
  };

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1fr) 240px" }, gap: 2, alignItems: "start" }}>
      <Box sx={{ border: 1, borderColor: "divider", borderRadius: "8px", bgcolor: surface, overflow: "hidden", minWidth: 0 }}>
        <Box ref={ref} sx={{ width: "100%" }}>
          <Box
            component="svg"
            ref={svgRef}
            width={layout.width}
            height={layout.height}
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            role="group"
            aria-label={`Graph of ring candidate ${graph.candidate_id}: ${graph.nodes.length} agents and ${graph.edges.length} pairs that share customers. The Members and Pairs tabs list the same data.`}
            sx={{ display: "block", maxWidth: "100%", height: "auto", touchAction: "none", "& .ring-node:focus-visible .ring-focus": { opacity: 1 } }}
            onKeyDown={(e) => e.key === "Escape" && setSelected(null)}
          >
            {graph.edges.map((e) => {
              const a = at(e.source);
              const b = at(e.target);
              if (!layout.nodes[e.source] || !layout.nodes[e.target]) return null;
              const lit = !neighbours || touches(e, focus);
              const strength = high > low ? (e.shared_customers - low) / (high - low) : 0.5;
              return (
                <g key={`${e.source}-${e.target}`} opacity={lit ? 1 : FADED} aria-hidden="true">
                  <line
                    x1={a.x} y1={a.y} x2={b.x} y2={b.y} strokeLinecap="round"
                    stroke={e.meets_rule ? theme.palette.primary.main : theme.palette.chart.neutral}
                    strokeOpacity={0.35 + 0.55 * strength}
                    strokeWidth={lineWidth(e.shared_customers, low, high)}
                  />
                  {focus && touches(e, focus) && (
                    <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2} textAnchor="middle" dominantBaseline="central" fontSize={12}
                      fontWeight={600} fill={theme.palette.text.primary} {...halo}>
                      {e.shared_customers}
                    </text>
                  )}
                </g>
              );
            })}
            {layout.order.map((id) => {
              const n = byId[id];
              const p = at(id);
              const paint = dotPaint(theme, n.flag_source);
              const active = selected === id;
              const lit = !neighbours || neighbours.has(id);
              return (
                <g
                  key={id}
                  className="ring-node"
                  role="button"
                  tabIndex={0}
                  aria-pressed={active}
                  aria-label={`Agent ${id}, ${n.county || "county unknown"}, ${FLAG_SOURCE_LABELS[n.flag_source] || "not flagged"}, ${n.activations ?? 0} activations, shares customers with ${n.linked_members} of the other members`}
                  opacity={lit ? 1 : FADED}
                  style={{ cursor: "grab", outline: "none" }}
                  onPointerDown={startDrag(id)}
                  onPointerMove={drag}
                  onPointerUp={() => { if (!endDrag()) toggle(id); }}
                  onPointerCancel={endDrag}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggle(id);
                    }
                  }}
                  onMouseEnter={() => setPointed(id)}
                  onMouseLeave={() => setPointed((current) => (current === id ? null : current))}
                  onFocus={() => setPointed(id)}
                  onBlur={() => setPointed((current) => (current === id ? null : current))}
                >
                  <circle className="ring-focus" cx={p.x} cy={p.y} r={p.r + 5} fill="none" stroke={theme.palette.text.primary} strokeWidth={2} opacity={0} />
                  <circle cx={p.x} cy={p.y} r={p.r} fill={paint.fill} stroke={paint.stroke} strokeWidth={active ? 3.5 : 2} />
                  <text x={p.x} y={p.y + p.r + 15} textAnchor="middle" fontSize={layout.compact ? 11 : 12}
                    fontFamily={theme.typography.fontFamilyMono} fill={theme.palette.text.primary} {...halo}>
                    {id}
                  </text>
                  {!layout.compact && (
                    <text x={p.x} y={p.y + p.r + 29} textAnchor="middle" fontSize={11} fill={theme.palette.text.secondary} {...halo}>
                      {shorten(n.county, COUNTY_CHARS)}
                    </text>
                  )}
                </g>
              );
            })}
          </Box>
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 1, px: 2, py: 1.25, borderTop: 1, borderColor: "divider" }}>
          <Legend theme={theme} sources={sources} />
          <Button size="small" onClick={() => setMoved({})} disabled={Object.keys(moved).length === 0}>Reset layout</Button>
        </Box>
      </Box>

      <Box aria-live="polite" sx={{ border: 1, borderColor: "divider", borderRadius: "8px", p: 2, minWidth: 0 }}>
        {selected ? (
          <>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 1, mb: 0.5 }}>
              <Typography sx={{ fontFamily: theme.typography.fontFamilyMono, fontSize: 15, fontWeight: 600 }}>{selected}</Typography>
              {openable && (
                <Link component={RouterLink} to={`/agents/${selected}`} color="primary.dark" sx={{ fontSize: 14 }}>Open agent</Link>
              )}
            </Box>
            <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 1.5 }}>{byId[selected]?.county || "County unknown"}</Typography>
            {pairs.length === 0 ? (
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Shares no customers with another member.</Typography>
            ) : (
              <Box component="ul" aria-label={`Pairs of ${selected}`} sx={{ listStyle: "none", m: 0, p: 0 }}>
                {pairs.map((e) => (
                  <Box component="li" key={other(e, selected)} sx={{ display: "flex", justifyContent: "space-between", gap: 1, py: 0.75, borderTop: 1, borderColor: "divider", fontSize: 14 }}>
                    <Box component="span" sx={{ fontFamily: theme.typography.fontFamilyMono }}>{other(e, selected)}</Box>
                    <Box component="span" sx={{ fontVariantNumeric: "tabular-nums", color: "text.secondary" }}>
                      {`${e.shared_customers} shared ${e.shared_customers === 1 ? "customer" : "customers"}`}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </>
        ) : (
          <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
            Select an agent to list the agents it shares customers with: click it, or move to it with Tab and press Enter or Space. Escape clears the selection. Drag an agent to move it.
          </Typography>
        )}
      </Box>
    </Box>
  );
}
