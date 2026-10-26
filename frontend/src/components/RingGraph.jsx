import { useState } from "react";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { layout } from "./ringLayout";

const NODE_RADIUS = 18;
// Labels sit part of the way along each edge, from its first agent, so the labels of edges that cross in
// the middle of the circle (for example the diagonals of a ring of 6) do not land on top of each other.
const LABEL_AT = 0.35;

/**
 * A ring candidate as a graph in plain SVG (issue #28). Agents are nodes; an edge means the two agents share
 * customers and shows only how many. Each node is a button: Tab moves between agents, Enter or Space
 * highlights the agent's edges, and Escape clears it. The same relationships are in the table beside it.
 */
export default function RingGraph({ graph }) {
  const theme = useTheme();
  const [selected, setSelected] = useState(null);
  const ids = graph.nodes.map((n) => n.agent_id);
  const { size, positions } = layout(ids);
  const touches = (e) => selected && (e.source === selected || e.target === selected);
  const maxShared = Math.max(1, ...graph.edges.map((e) => e.shared_customers));
  const linked = selected ? graph.edges.filter(touches) : [];

  const toggle = (id) => setSelected((current) => (current === id ? null : id));

  return (
    <Box>
      <Box
        component="svg"
        viewBox={`0 0 ${size} ${size}`}
        role="group"
        aria-label={`Graph of ring candidate ${graph.candidate_id}: ${graph.nodes.length} agents and ${graph.edges.length} pairs that share customers. The table beside it lists the same pairs.`}
        // Visible keyboard focus on the SVG nodes, which the theme's focus styles do not reach.
        sx={{
          width: "100%", maxWidth: 480, height: "auto", display: "block", mx: "auto",
          "& .ring-node:focus-visible circle": { stroke: theme.palette.text.primary, strokeWidth: 4 },
        }}
        onKeyDown={(e) => e.key === "Escape" && setSelected(null)}
      >
        {graph.edges.map((e) => {
          const a = positions[e.source];
          const b = positions[e.target];
          const dim = selected && !touches(e);
          const x = a.x + (b.x - a.x) * LABEL_AT;
          const y = a.y + (b.y - a.y) * LABEL_AT;
          return (
            <g key={`${e.source}-${e.target}`} opacity={dim ? 0.15 : 1} aria-hidden="true">
              <line
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={e.meets_rule ? theme.palette.error.main : theme.palette.chart.neutral}
                strokeDasharray={e.meets_rule ? undefined : "4 3"}
                strokeWidth={1 + (4 * e.shared_customers) / maxShared}
              />
              <text
                x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize={12}
                fill={theme.palette.text.primary} stroke={theme.palette.background.paper} strokeWidth={4} paintOrder="stroke"
              >
                {e.shared_customers}
              </text>
            </g>
          );
        })}
        {graph.nodes.map((n) => {
          const p = positions[n.agent_id];
          const active = selected === n.agent_id;
          return (
            <g
              key={n.agent_id}
              role="button"
              tabIndex={0}
              aria-pressed={active}
              aria-label={`Agent ${n.agent_id}, county ${n.county || "unknown"}, shares customers with ${n.linked_members} of the other members`}
              onClick={() => toggle(n.agent_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  toggle(n.agent_id);
                }
              }}
              style={{ cursor: "pointer", outline: "none" }}
              className="ring-node"
            >
              <circle
                cx={p.x} cy={p.y} r={NODE_RADIUS}
                fill={active ? theme.palette.primary.main : theme.palette.background.paper}
                stroke={theme.palette.primary.main} strokeWidth={active ? 3 : 2}
              />
              <text x={p.x} y={p.y + NODE_RADIUS + 14} textAnchor="middle" fontSize={12} fill={theme.palette.text.primary}>{n.agent_id}</text>
              <text x={p.x} y={p.y + NODE_RADIUS + 28} textAnchor="middle" fontSize={11} fill={theme.palette.text.secondary}>{n.county}</text>
            </g>
          );
        })}
      </Box>
      <Typography variant="body2" color="text.secondary" aria-live="polite" sx={{ mt: 1, minHeight: 20 }}>
        {selected
          ? `${selected} shares customers with ${linked.map((e) => `${e.source === selected ? e.target : e.source} (${e.shared_customers})`).join(", ") || "no other member"}.`
          : "Select an agent (Tab, then Enter) to highlight the pairs it belongs to. Solid red lines reach the 3 shared customers of the rule."}
      </Typography>
    </Box>
  );
}
