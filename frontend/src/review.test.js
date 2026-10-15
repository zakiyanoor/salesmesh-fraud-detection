import { describe, expect, it } from "vitest";
import { NOTES_MAX, PROPOSED_MESSAGE, confirmedMessage, notesError } from "./review";

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

  it("only a confirmation is called final", () => {
    expect(confirmedMessage("A35485")).toBe("Decision for A35485 confirmed. It is now final.");
  });
});
