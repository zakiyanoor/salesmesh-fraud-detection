import { describe, expect, it } from "vitest";
import { DOT, LINE, dotRadius, forceLayout, lineWidth } from "./ringLayout";

// A group of n agents; every pair shares customers, more for neighbours in ID order.
function group(n) {
  const nodes = Array.from({ length: n }, (_, i) => ({ agent_id: `A${10000 + i * 7}`, activations: 40 + i * 25, county: "Nairobi" }));
  const edges = [];
  nodes.forEach((a, i) => nodes.slice(i + 1).forEach((b, j) => edges.push({ source: a.agent_id, target: b.agent_id, shared_customers: j === 0 ? 9 : 3 + ((i + j) % 4) })));
  return { nodes, edges };
}

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
// The agent ID (monospace, about 7.2px a character) and, unless compact, the county line under each dot.
const labelBox = (p, compact) => ({ left: p.x - 24, right: p.x + 24, top: p.y + p.r + 2, bottom: p.y + p.r + (compact ? 18 : 32) });
const overlaps = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

describe("ring graph force layout (issue #28)", () => {
  it("gives the same coordinates for the same group, whatever the input order", () => {
    const { nodes, edges } = group(6);
    const first = forceLayout(nodes, edges, 640);
    expect(forceLayout(nodes, edges, 640)).toEqual(first);
    expect(forceLayout([...nodes].reverse(), [...edges].reverse(), 640)).toEqual(first);
  });

  // 2 is the smallest ring candidate in the data and 6 the largest; 12 checks a larger group still works.
  it.each([
    [2, 640], [6, 640], [12, 640], [2, 260], [6, 260], [12, 260],
  ])("keeps %i agents inside a %ipx container, with no dots or labels overlapping", (n, width) => {
    const { nodes, edges } = group(n);
    const layout = forceLayout(nodes, edges, width);
    const points = Object.values(layout.nodes);
    expect(points).toHaveLength(n);
    for (const p of points) {
      expect(p.x - p.r).toBeGreaterThanOrEqual(0);
      expect(p.x + p.r).toBeLessThanOrEqual(width);
      expect(p.y - p.r).toBeGreaterThanOrEqual(0);
      expect(p.y + p.r).toBeLessThanOrEqual(layout.height);
      expect(p.r).toBeGreaterThanOrEqual(DOT.min * 0.6);
    }
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        expect(distance(points[i], points[j])).toBeGreaterThan(points[i].r + points[j].r);
        expect(overlaps(labelBox(points[i], layout.compact), labelBox(points[j], layout.compact))).toBe(false);
      }
    }
  });

  it("pulls pairs that share more customers closer together", () => {
    const nodes = ["A1", "A2", "A3"].map((agent_id) => ({ agent_id, activations: 50 }));
    const edges = [{ source: "A1", target: "A2", shared_customers: 20 }, { source: "A2", target: "A3", shared_customers: 3 }];
    const { nodes: at } = forceLayout(nodes, edges, 800);
    expect(distance(at.A1, at.A2)).toBeLessThan(distance(at.A2, at.A3));
  });

  it("sizes dots by activations and lines by shared customers, within their ranges", () => {
    expect(dotRadius(10, 10, 90)).toBe(DOT.min);
    expect(dotRadius(90, 10, 90)).toBe(DOT.max);
    expect(lineWidth(3, 3, 12)).toBe(LINE.min);
    expect(lineWidth(12, 3, 12)).toBe(LINE.max);
    expect(lineWidth(5, 5, 5)).toBeGreaterThan(LINE.min);
  });
});
