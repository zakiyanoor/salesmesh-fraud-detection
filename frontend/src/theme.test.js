import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { cwd } from "node:process";
import { resolve } from "node:path";
import { PALETTES, createAppTheme } from "./theme";
import { STORAGE_KEY } from "./colorMode/colorModeContext";

function luminance(hex) {
  const [r, g, b] = hex.replace("#", "").match(/../g).map((h) => {
    const v = parseInt(h, 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// rgba(r, g, b, a) laid over an opaque hex colour.
function over(rgba, hex) {
  const [r, g, b, a] = rgba.match(/[\d.]+/g).map(Number);
  const base = hex.replace("#", "").match(/../g).map((h) => parseInt(h, 16));
  return "#" + [r, g, b].map((c, i) => Math.round(c * a + base[i] * (1 - a)).toString(16).padStart(2, "0")).join("");
}

describe.each(["light", "dark"])("%s palette", (mode) => {
  const p = PALETTES[mode];
  const surfaces = { page: p.background.default, card: p.background.paper };
  const text = {
    "text.primary": p.text.primary,
    "text.secondary": p.text.secondary,
    "primary.dark": p.primary.dark,
    "error.main": p.error.main,
    "warning.main": p.warning.main,
    "success.main": p.success.main,
  };

  it.each(Object.entries(text))("%s meets AA (4.5:1) on page and card", (_, colour) => {
    for (const surface of Object.values(surfaces)) expect(contrast(colour, surface)).toBeGreaterThanOrEqual(4.5);
  });

  it("primary.main meets AA on cards, and its button text meets AA", () => {
    expect(contrast(p.primary.main, p.background.paper)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(p.primary.contrastText, p.primary.main)).toBeGreaterThanOrEqual(4.5);
  });

  it("the active menu item text meets AA on its tinted background", () => {
    expect(contrast(p.primary.dark, over(p.selected, p.background.paper))).toBeGreaterThanOrEqual(4.5);
  });

  it("the keyboard focus ring (primary.main) meets 3:1 on page and card", () => {
    for (const surface of Object.values(surfaces)) expect(contrast(p.primary.main, surface)).toBeGreaterThanOrEqual(3);
  });

  it("the neutral chart bar meets 3:1 against cards", () => {
    expect(contrast(p.chartNeutral, p.background.paper)).toBeGreaterThanOrEqual(3);
  });

  it("risk tokens reuse the status colours", () => {
    const { risk } = createAppTheme().colorSchemes[mode].palette;
    expect(risk).toMatchObject({ high: p.error.main, review: p.warning.main, low: p.success.main });
  });
});

it("has a light and a dark scheme built from PALETTES (issue #28)", () => {
  const { colorSchemes } = createAppTheme();
  for (const mode of ["light", "dark"]) {
    const palette = colorSchemes[mode].palette;
    expect(palette.mode).toBe(mode);
    expect(palette.background).toMatchObject(PALETTES[mode].background);
    expect([palette.primary.main, palette.error.main, palette.text.primary]).toEqual(
      [PALETTES[mode].primary.main, PALETTES[mode].error.main, PALETTES[mode].text.primary]);
  }
});

it("index.html paints the first frame with the palette backgrounds and the stored choice", () => {
  // Vitest runs from frontend/.
  const html = readFileSync(resolve(cwd(), "index.html"), "utf-8");
  expect(html).toContain(`html { background: ${PALETTES.light.background.default}; color-scheme: light; }`);
  expect(html).toContain(`html[data-color-scheme="dark"] { background: ${PALETTES.dark.background.default}; color-scheme: dark; }`);
  expect(html).toContain(`window.localStorage.getItem("${STORAGE_KEY}")`);
  expect(html).toContain("try {");
  // Light unless dark was chosen: the device setting is no longer followed.
  expect(html).toContain(`getItem("${STORAGE_KEY}") === "dark"`);
  expect(html).not.toContain("prefers-color-scheme");
});

it("light mode keeps the original look", () => {
  const { typography, shape, colorSchemes } = createAppTheme();
  const palette = colorSchemes.light.palette;
  expect(palette.mode).toBe("light");
  expect(palette.background).toMatchObject({ default: "#F5F7FA", paper: "#FFFFFF" });
  expect(palette.primary.main).toBe("#1976D2");
  expect([palette.error.main, palette.warning.main, palette.success.main]).toEqual(["#D32F2F", "#B45309", "#2E7D4F"]);
  expect(palette.chart.region).toEqual(["#1976D2", "#00897B", "#F59E0B", "#8E24AA", "#546E7A"]);
  expect(shape.borderRadius).toBe(4);
  expect(typography.fontFamily.startsWith('"IBM Plex Sans"')).toBe(true);
  expect(typography.h4.fontFamily.startsWith('"Space Grotesk"')).toBe(true);
  expect(typography.fontFamilyMono.startsWith('"IBM Plex Mono"')).toBe(true);
});

it("hides the chart text measurement span, so no stray 0 joins the page text", () => {
  const theme = createAppTheme();
  const rules = theme.components.MuiCssBaseline.styleOverrides(theme);
  expect(rules["#recharts_measurement_span"]).toEqual({ visibility: "hidden" });
});
