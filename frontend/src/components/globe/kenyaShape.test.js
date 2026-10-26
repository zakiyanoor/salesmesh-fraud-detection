import { describe, expect, it } from "vitest";
import { KENYA_OUTLINE } from "./kenyaOutline";
import { KENYA_COUNTIES } from "./kenyaCounties";
import { GRATICULE_STEP, GRID_STEP, graticuleArcs, insidePolygon, kenyaGrid } from "./kenyaShape";

// Kenya's bounding box. The top is 5.5, not 5.1, because Natural Earth's Kenya includes the Ilemi Triangle.
const BOX = { minLat: -4.75, maxLat: 5.5, minLng: 33.85, maxLng: 41.95 };

describe("Kenya outline and dot grid (issue #28)", () => {
  it("is a simplified outline of 150 to 300 points", () => {
    expect(KENYA_OUTLINE.length).toBeGreaterThanOrEqual(150);
    expect(KENYA_OUTLINE.length).toBeLessThanOrEqual(300);
  });

  it("tells inside from outside", () => {
    expect(insidePolygon(36.8219, -1.2921)).toBe(true); // Nairobi
    expect(insidePolygon(32.5825, 0.3476)).toBe(false); // Kampala
    expect(insidePolygon(38.7578, 9.0054)).toBe(false); // Addis Ababa
    expect(insidePolygon(41.5, -3.5)).toBe(false); // the Indian Ocean
  });

  it("keeps every grid point inside Kenya's bounding box and inside the outline", () => {
    const grid = kenyaGrid();
    expect(grid.length).toBeGreaterThan(900);
    expect(grid.length).toBeLessThan(1600);
    for (const [lat, lng] of grid) {
      expect(lat).toBeGreaterThanOrEqual(BOX.minLat);
      expect(lat).toBeLessThanOrEqual(BOX.maxLat);
      expect(lng).toBeGreaterThanOrEqual(BOX.minLng);
      expect(lng).toBeLessThanOrEqual(BOX.maxLng);
      expect(insidePolygon(lng, lat)).toBe(true);
    }
  });

  it("is a regular grid about 0.15 to 0.2 degrees apart, the same on every call", () => {
    expect(GRID_STEP).toBeGreaterThanOrEqual(0.15);
    expect(GRID_STEP).toBeLessThanOrEqual(0.2);
    const grid = kenyaGrid();
    expect(kenyaGrid()).toEqual(grid);
    const lats = [...new Set(grid.map(([lat]) => lat))].sort((a, b) => a - b);
    for (let i = 1; i < lats.length; i += 1) expect(lats[i] - lats[i - 1]).toBeCloseTo(GRID_STEP, 3);
  });

  it("has all 47 county headquarters inside the outline", () => {
    const outside = KENYA_COUNTIES.filter(([, , lat, lng]) => !insidePolygon(lng, lat)).map(([county]) => county);
    expect(outside).toEqual([]);
  });

  it("draws faint latitude and longitude lines every 10 degrees", () => {
    expect(GRATICULE_STEP).toBe(10);
    const arcs = graticuleArcs();
    const meridians = arcs.filter((a) => a.from[1] === a.to[1]);
    expect(meridians.map((a) => a.from[1])).toEqual(Array.from({ length: 36 }, (_, i) => -180 + i * 10));
    expect(arcs.length).toBe(36 + 15 * 36);
  });
});
