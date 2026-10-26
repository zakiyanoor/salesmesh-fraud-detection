import { describe, expect, it } from "vitest";
import { layout, placeLabels } from "./ringLayout";

const ids = (n) => Array.from({ length: n }, (_, i) => `A${10000 + i}`);
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

describe("ring graph layout (issue #28)", () => {
  it("is deterministic and puts the first agent at the top", () => {
    expect(layout(ids(6))).toEqual(layout(ids(6)));
    const { size, positions } = layout(ids(6));
    expect(positions.A10000.x).toBeCloseTo(size / 2);
    expect(Math.min(...Object.values(positions).map((p) => p.y))).toBe(positions.A10000.y);
  });

  it.each([2, 6, 12])("keeps %i agents inside the drawing and far enough apart for their labels", (n) => {
    const { size, positions } = layout(ids(n));
    const points = Object.values(positions);
    for (const p of points) {
      expect(p.x).toBeGreaterThanOrEqual(40);
      expect(p.x).toBeLessThanOrEqual(size - 40);
      expect(p.y).toBeGreaterThanOrEqual(40);
      expect(p.y).toBeLessThanOrEqual(size - 40);
    }
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) expect(distance(points[i], points[j])).toBeGreaterThan(60);
    }
  });
});

describe("edge labels (issue #28)", () => {
  it("are placed the same way every time, apart from each other and from the agents", () => {
    const agents = ids(6);
    const { radius, positions } = layout(agents);
    const edges = [];
    agents.forEach((a, i) => agents.slice(i + 1).forEach((b) => edges.push({ source: a, target: b })));
    const labels = placeLabels(edges, positions, radius);
    expect(placeLabels(edges, positions, radius)).toEqual(labels);
    const spots = Object.values(labels);
    expect(spots).toHaveLength(15);
    let crowded = 0;
    for (let i = 0; i < spots.length; i += 1) {
      for (let j = i + 1; j < spots.length; j += 1) if (distance(spots[i], spots[j]) < 20) crowded += 1;
    }
    expect(crowded).toBe(0);
    for (const spot of spots) for (const p of Object.values(positions)) expect(distance(spot, p)).toBeGreaterThanOrEqual(30);
    // ...and never on the agent ID and county written under a node.
    for (const spot of spots) {
      for (const p of Object.values(positions)) expect(Math.abs(spot.x - p.x) < 44 && spot.y - p.y > 16 && spot.y - p.y < 58).toBe(false);
    }
  });
});
