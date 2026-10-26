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
  it.each([[true, "dark", "#0F141A"], [false, "light", "#F5F7FA"]])(
    "follows the device by default (prefers dark: %s)", (prefersDark, mode, background) => {
      device(prefersDark);
      renderApp();
      expect(screen.getByTestId("mode")).toHaveTextContent(`${mode} ${background}`);
      expect(screen.getByRole("button", { name: `Theme: System, now ${mode}` })).toBeInTheDocument();
      expect(document.documentElement.getAttribute("data-color-scheme")).toBe(mode);
    },
  );

  it("lets the user choose dark, light or system, marks the choice and remembers it", async () => {
    device(false);
    renderApp();
    await choose("Dark");
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.getAttribute("data-color-scheme")).toBe("dark");
    await userEvent.click(screen.getByRole("button", { name: "Theme: Dark" }));
    expect(screen.getByRole("menuitemradio", { name: "Dark" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("menuitemradio", { name: "System" })).toHaveAttribute("aria-checked", "false");
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Light" }));
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    await choose("System");
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("system");
  });

  it("starts in the remembered choice, even against the device", () => {
    device(true);
    window.localStorage.setItem(STORAGE_KEY, "light");
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
    expect(screen.getByRole("button", { name: "Theme: Light" })).toBeInTheDocument();
  });

  it("still works when storage is blocked", async () => {
    device(true);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    renderApp();
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
    await choose("Light");
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
  });
});
