import { describe, expect, it } from "vitest";
import { checkDayRange, fromIsoDay, toIsoDay } from "./dayDates";
import { categoryHasAgents } from "../audit";
import { roleLabel } from "../auth/roles";

describe("dates typed as day/month/year", () => {
  it("converts to and from the API format", () => {
    expect(toIsoDay("27/10/2026")).toBe("2026-10-27");
    expect(toIsoDay("1/2/2026")).toBe("2026-02-01");
    expect(toIsoDay("")).toBe("");
    expect(fromIsoDay("2026-10-27")).toBe("27/10/2026");
  });

  it("rejects text that is not a real date", () => {
    for (const bad of ["31/02/2026", "2026-10-27", "13/13/2026", "27/10/26", "abc"]) expect(toIsoDay(bad)).toBeNull();
  });

  it("checks the order of a range", () => {
    expect(checkDayRange("01/10/2026", "13/10/2026")).toMatchObject({ from: "2026-10-01", to: "2026-10-13", fromError: null, toError: null });
    expect(checkDayRange("14/10/2026", "13/10/2026").toError).toBe("The To date must be on or after the From date.");
    expect(checkDayRange("99/99/2026", "").fromError).toBe("Enter a real date as dd/mm/yyyy.");
  });
});

describe("shared labels", () => {
  it("shows administrator roles as Administrator", () => {
    expect(roleLabel("admin")).toBe("Administrator");
    expect(roleLabel("administrator")).toBe("Administrator");
    expect(roleLabel("fraud_analyst")).toBe("Fraud analyst");
    expect(roleLabel("compliance_officer")).toBe("Compliance officer");
  });

  it("shows the Agent column only for categories that can name an agent", () => {
    expect(["", "review", "ai_decision"].every(categoryHasAgents)).toBe(true);
    expect(["authentication", "report", "admin"].some(categoryHasAgents)).toBe(false);
  });
});
