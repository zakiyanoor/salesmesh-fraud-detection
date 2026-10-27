import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime, formatPercentile } from "./format";

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

describe("shared date format", () => {
  it("shows day, short month, year and 24 hour time in Nairobi time", () => {
    // System times arrive without a zone and are UTC: 14:26 UTC is 17:26 in Nairobi.
    expect(formatDateTime("2026-10-13T14:26:00")).toBe("13 Oct 2026, 17:26");
    expect(formatDateTime("2026-10-13T21:05:00Z")).toBe("14 Oct 2026, 00:05");
    expect(formatDate("2026-10-13T14:26:00")).toBe("13 Oct 2026");
  });

  it("shows recorded activation times as recorded, without shifting them", () => {
    expect(formatDateTime("2026-08-30T23:58:43", { recorded: true })).toBe("30 Aug 2026, 23:58");
    expect(formatDate("2025-11-02T08:00:00", { recorded: true })).toBe("2 Nov 2025");
  });

  it("never shows a month first date, and shows a dash for no value", () => {
    expect(formatDateTime("2026-01-02T09:00:00")).not.toMatch(/^\d{1,2}\/\d{1,2}\//);
    for (const empty of [null, undefined, "", "not a date"]) expect(formatDateTime(empty)).toBe("—");
  });
});
