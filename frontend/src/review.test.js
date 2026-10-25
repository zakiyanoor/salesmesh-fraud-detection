import { describe, expect, it } from "vitest";
import { NOTES_MAX, PROPOSED_MESSAGE, closedMessage, correctedMessage, notesError, otherOutcome } from "./review";

describe("notes validation (same rules as the server)", () => {
  it.each([
    ["", "Notes are required."],
    ["   \n\t ", "Notes are required."],
    ["a".repeat(1001), "Notes must be at most 1000 characters (now 1001)."],
  ])("refuses %j", (notes, message) => {
    expect(notesError(notes)).toBe(message);
  });

  it.each(["x", "a".repeat(NOTES_MAX), `  ${"a".repeat(NOTES_MAX)}  `])("accepts a value of %#", (notes) => {
    expect(notesError(notes)).toBeNull();
  });
});

describe("proposed versus confirmed wording", () => {
  it("a proposal is never called saved, recorded or final", () => {
    expect(PROPOSED_MESSAGE).toMatch(/^Decision proposed\./);
    expect(PROPOSED_MESSAGE).toMatch(/waiting for a compliance officer to confirm/);
    expect(PROPOSED_MESSAGE).not.toMatch(/saved|recorded|final/i);
  });

  it("an agreement or an overrule gives the final outcome (issue #28)", () => {
    expect(closedMessage("A35485", "agreed", "Confirmed fraud")).toBe("Proposal for A35485 agreed. The final outcome is Confirmed fraud.");
    expect(closedMessage("A35485", "overruled", "Legitimate")).toBe("Proposal for A35485 overruled. The final outcome is Legitimate.");
  });

  it("a correction says the original decision stays in the history", () => {
    expect(correctedMessage("A35485", "Legitimate")).toMatch(/now Legitimate; the history keeps the original decision/);
    expect(otherOutcome("confirmed_fraud")).toBe("legitimate");
    expect(otherOutcome("legitimate")).toBe("confirmed_fraud");
  });
});
