import { describe, expect, it } from "vitest";
import { formatPercentile } from "./format";

describe("formatPercentile", () => {
  it.each([
    [99.9, "Top 1%"],
    [99.0, "Top 1%"],
    [98.9, "Top 2%"],
    [92.0, "Top 8%"],
    [51.5, "Top 49%"],
    [0, "Top 100%"],
    [100, "Top 1%"],
  ])("%s -> %s", (percentile, expected) => {
    expect(formatPercentile(percentile)).toBe(expected);
  });

  it("shows a dash when there is no percentile", () => {
    expect(formatPercentile(null)).toBe("—");
    expect(formatPercentile(undefined)).toBe("—");
    expect(formatPercentile(Number.NaN)).toBe("—");
  });
});
