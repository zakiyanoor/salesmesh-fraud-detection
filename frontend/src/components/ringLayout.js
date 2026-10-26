// Ring graph layout (issue #28): a force layout from d3-force, run to the end at once from a fixed start, so
// the same group always gives the same picture, then fitted to the container's width. No animation.
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX } from "d3-force";

export const DOT = { min: 10, max: 22 };
export const LINE = { min: 1.5, max: 6 };
// Room around each dot for its agent ID and county under it, so neither dots nor labels overlap.
const LABEL_HALF_WIDTH = 46;
const LABEL_BELOW = 34;
const LABEL_BELOW_COMPACT = 20;
const PADDING = 16;
const TICKS = 300;

/** Dot radius from the agent's activations, between DOT.min and DOT.max for the group. */
export function dotRadius(activations, low, high) {
  if (!(high > low)) return (DOT.min + DOT.max) / 2;
  return DOT.min + ((activations - low) / (high - low)) * (DOT.max - DOT.min);
}

/** Line width from the pair's shared customers, between LINE.min and LINE.max for the group. */
export function lineWidth(shared, low, high) {
  if (!(high > low)) return (LINE.min + LINE.max) / 2;
  return LINE.min + ((shared - low) / (high - low)) * (LINE.max - LINE.min);
}

/**
 * Positions for a ring graph: { width, height, compact, nodes: { id: { x, y, r } } }, inside width x height.
 * Agents start on a circle in agent ID order (no randomness); links pull pairs closer the more customers they
 * share, many-body repulsion spreads the group, collision keeps dots and their labels apart, and the centre
 * force holds it together. When the group is wider than the container it is scaled to fit, and `compact`
 * asks the drawing to drop the county line so the shorter labels still fit.
 */
export function forceLayout(nodes, edges, width) {
  const ids = nodes.map((n) => n.agent_id).sort();
  const activity = nodes.map((n) => n.activations ?? 0);
  const low = Math.min(...activity);
  const high = Math.max(...activity);
  const shared = edges.map((e) => e.shared_customers);
  const most = Math.max(1, ...shared);

  const start = 120 + 18 * ids.length;
  const points = ids.map((id, i) => {
    const node = nodes.find((n) => n.agent_id === id);
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / ids.length;
    return {
      id, r: dotRadius(node.activations ?? 0, low, high),
      x: start * Math.cos(angle), y: start * Math.sin(angle),
    };
  });
  // Links in a fixed order too: each pair as (lower ID, higher ID), sorted.
  const links = edges
    .map((e) => {
      const [source, target] = [e.source, e.target].sort();
      return { source, target, shared: e.shared_customers };
    })
    .sort((a, b) => (a.source === b.source ? a.target.localeCompare(b.target) : a.source.localeCompare(b.source)));

  const simulation = forceSimulation(points)
    .force("link", forceLink(links).id((d) => d.id).distance((l) => 210 - 90 * (l.shared / most)).strength(0.6))
    .force("charge", forceManyBody().strength(-500))
    .force("collide", forceCollide((d) => Math.max(d.r, LABEL_HALF_WIDTH) + 8).iterations(4))
    .force("center", forceCenter(0, 0))
    .stop();
  // In a narrow container, pull the group towards a tall shape so it needs less scaling to fit.
  if (width < 520) simulation.force("narrow", forceX(0).strength(0.35));
  simulation.tick(TICKS);

  // The drawing's extent, labels included.
  const left = Math.min(...points.map((p) => p.x - Math.max(p.r, LABEL_HALF_WIDTH)));
  const right = Math.max(...points.map((p) => p.x + Math.max(p.r, LABEL_HALF_WIDTH)));
  const top = Math.min(...points.map((p) => p.y - p.r));
  const available = Math.max(120, width - 2 * PADDING);
  const scale = Math.min(1, available / (right - left));
  const offsetX = (width - (right - left) * scale) / 2;

  const placed = {};
  for (const p of points) {
    placed[p.id] = {
      x: Math.round((offsetX + (p.x - left) * scale) * 10) / 10,
      y: Math.round((PADDING + (p.y - top) * scale) * 10) / 10,
      // Dots shrink a little with the drawing, never below 60% of their size.
      r: Math.round(p.r * Math.max(scale, 0.6) * 10) / 10,
    };
  }
  // Labels keep their size when the drawing is scaled, so the height is measured from the placed dots.
  const compact = scale < 0.8;
  const below = compact ? LABEL_BELOW_COMPACT : LABEL_BELOW;
  const height = Math.ceil(Math.max(...Object.values(placed).map((p) => p.y + p.r + below)) + PADDING);
  return { width, height, compact, nodes: placed, order: ids };
}
