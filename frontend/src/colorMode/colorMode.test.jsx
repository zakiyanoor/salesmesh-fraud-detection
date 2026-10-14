import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useTheme } from "@mui/material";
import ColorModeProvider from "./ColorModeProvider";
import ColorModeToggle from "../components/ColorModeToggle";
import { STORAGE_KEY } from "./colorModeContext";

function Mode() {
  return <span data-testid="mode">{useTheme().palette.mode}</span>;
}

const renderApp = () => render(<ColorModeProvider><Mode /><ColorModeToggle /></ColorModeProvider>);

afterEach(() => vi.restoreAllMocks());

describe("colour mode", () => {
  it("is light by default and the toggle switches and remembers dark", async () => {
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    await userEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
  });

  it("starts in the saved mode", () => {
    window.localStorage.setItem(STORAGE_KEY, "dark");
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
  });

  it("still works when storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    await userEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
  });
});
