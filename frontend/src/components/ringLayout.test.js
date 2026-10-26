import { describe, expect, it } from "vitest";
import { layout } from "./ringLayout";

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
