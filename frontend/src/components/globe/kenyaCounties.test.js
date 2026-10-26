import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cwd } from "node:process";
import { COUNTY_DOT, COUNTY_MARKERS, KENYA_COUNTIES } from "./kenyaCounties";

// The county names the data generator uses (ml/data_generation.py, COUNTY_POPULATION_THOUSANDS).
function generatorCounties() {
  const source = readFileSync(resolve(cwd(), "..", "ml", "data_generation.py"), "utf-8");
  const block = source.slice(source.indexOf("COUNTY_POPULATION_THOUSANDS = {"), source.indexOf("}", source.indexOf("COUNTY_POPULATION_THOUSANDS = {")));
  return [...block.matchAll(/"([^"]+)":\s*\d+/g)].map((m) => m[1]);
}

describe("Kenya county headquarters (issue #28)", () => {
  it("has all 47 counties of the data generator, once each", () => {
    const names = KENYA_COUNTIES.map(([county]) => county);
    expect(names).toHaveLength(47);
    expect(new Set(names).size).toBe(47);
    expect([...names].sort()).toEqual([...generatorCounties()].sort());
  });

  it("puts every headquarters inside Kenya's bounding box, with no two in the same place", () => {
    for (const [county, , lat, lng] of KENYA_COUNTIES) {
      expect(lat, county).toBeGreaterThanOrEqual(-4.8);
      expect(lat, county).toBeLessThanOrEqual(5.1);
      expect(lng, county).toBeGreaterThanOrEqual(33.9);
      expect(lng, county).toBeLessThanOrEqual(41.9);
    }
    expect(new Set(KENYA_COUNTIES.map(([, , lat, lng]) => `${lat},${lng}`)).size).toBe(47);
  });

  it("gives cobe one small marker per county", () => {
    expect(COUNTY_MARKERS).toHaveLength(47);
    expect(COUNTY_MARKERS[0]).toEqual({ location: [KENYA_COUNTIES[0][2], KENYA_COUNTIES[0][3]], size: COUNTY_DOT });
  });
});
