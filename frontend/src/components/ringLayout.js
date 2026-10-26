// Ring graph layout (issue #28), kept apart from the component so it can be tested on its own.

/** Deterministic circle layout: members in agent ID order, the first at the top, then clockwise. */
export function layout(agentIds) {
  const n = agentIds.length;
  const radius = Math.max(110, 22 * n);
  const centre = radius + 70;
  const positions = {};
  agentIds.forEach((id, i) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    positions[id] = { x: centre + radius * Math.cos(angle), y: centre + radius * Math.sin(angle) };
  });
  return { size: centre * 2, radius, positions };
}

// Edge labels: tried along each edge in this order; the first spot far enough from the labels already
// placed and from every agent wins. Short edges (neighbours on the circle) start in the middle.
const LONG_EDGE_STOPS = [0.35, 0.5, 0.65, 0.25, 0.75, 0.42, 0.58];
const SHORT_EDGE_STOPS = [0.5, 0.35, 0.65];
const SHORT_EDGE = 1.2;
const LABEL_GAP = 20;
const NODE_CLEARANCE = 30;
// The agent ID and county are written under each node, in about this box (from the node's centre).
const NAME_BOX = { halfWidth: 44, top: 16, bottom: 58 };
const onName = (p, n) => Math.abs(p.x - n.x) < NAME_BOX.halfWidth && p.y - n.y > NAME_BOX.top && p.y - n.y < NAME_BOX.bottom;

/** {"source-target": {x, y}} for every edge, deterministic for the same edges in the same order. */
export function placeLabels(edges, positions, radius) {
  const placed = [];
  const nodes = Object.values(positions);
  const result = {};
  for (const e of edges) {
    const a = positions[e.source];
    const b = positions[e.target];
    const stops = Math.hypot(b.x - a.x, b.y - a.y) < SHORT_EDGE * radius ? SHORT_EDGE_STOPS : LONG_EDGE_STOPS;
    const spots = stops.map((t) => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }));
    const clear = (p) => placed.every((q) => Math.hypot(p.x - q.x, p.y - q.y) >= LABEL_GAP)
      && nodes.every((n) => Math.hypot(p.x - n.x, p.y - n.y) >= NODE_CLEARANCE && !onName(p, n));
    const spot = spots.find(clear) || spots[0];
    placed.push(spot);
    result[`${e.source}-${e.target}`] = spot;
  }
  return result;
}
