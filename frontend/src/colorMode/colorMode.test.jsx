import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useTheme } from "@mui/material";
import ColorModeProvider from "./ColorModeProvider";
import ThemeMenu from "../components/ThemeMenu";
import { STORAGE_KEY } from "./colorModeContext";

function Mode() {
  const theme = useTheme();
  return <span data-testid="mode">{`${theme.palette.mode} ${theme.palette.background.default}`}</span>;
}

/** The device prefers dark (or not); other media queries keep the setup's behaviour (none match). */
function device(prefersDark) {
  vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
    matches: prefersDark && query.includes("prefers-color-scheme: dark"),
    media: query, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {},
    dispatchEvent: () => false,
  }));
}

const renderApp = () => render(<ColorModeProvider><Mode /><ThemeMenu /></ColorModeProvider>);

async function choose(label) {
  await userEvent.click(screen.getByRole("button", { name: /^Theme: / }));
  await userEvent.click(screen.getByRole("menuitemradio", { name: label }));
}

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-color-scheme");
});

describe("colour scheme (issue #28)", () => {
  it.each([true, false])("starts light on a first visit, whatever the device prefers (prefers dark: %s)", (prefersDark) => {
    device(prefersDark);
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("light #F5F7FA");
    expect(screen.getByRole("button", { name: "Theme: Light" })).toBeInTheDocument();
    expect(document.documentElement.getAttribute("data-color-scheme")).toBe("light");
  });

  it("offers only Light and Dark, marks the choice and remembers it", async () => {
    device(false);
    renderApp();
    await userEvent.click(screen.getByRole("button", { name: /^Theme: / }));
    expect(screen.getAllByRole("menuitemradio").map((item) => item.textContent)).toEqual(["Light", "Dark"]);
    expect(screen.queryByRole("menuitemradio", { name: "System" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Dark" }));
    expect(screen.getByTestId("mode")).toHaveTextContent("dark #0F141A");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.getAttribute("data-color-scheme")).toBe("dark");
    await userEvent.click(screen.getByRole("button", { name: "Theme: Dark" }));
    expect(screen.getByRole("menuitemradio", { name: "Dark" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("menuitemradio", { name: "Light" })).toHaveAttribute("aria-checked", "false");
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Light" }));
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("light");
  });

  it("starts in the remembered choice", () => {
    device(false);
    window.localStorage.setItem(STORAGE_KEY, "dark");
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
    expect(screen.getByRole("button", { name: "Theme: Dark" })).toBeInTheDocument();
  });

  it.each(["system", "sepia"])("treats a stored %s as light, even on a dark device", (stored) => {
    device(true);
    window.localStorage.setItem(STORAGE_KEY, stored);
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    expect(screen.getByRole("button", { name: "Theme: Light" })).toBeInTheDocument();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("light");
  });

  it("still works when storage is blocked", async () => {
    device(true);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    await choose("Dark");
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
  });
});
