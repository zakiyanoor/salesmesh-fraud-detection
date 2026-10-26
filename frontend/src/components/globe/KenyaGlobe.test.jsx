import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import createGlobe from "cobe";
import KenyaGlobe from "./KenyaGlobe";
import { KENYA, MAX_PIXEL_RATIO, STILL_REPAINT_MS, SWAY_DEGREES, facing } from "./globeMath";
import { createAppTheme } from "../../theme";

const globe = { update: vi.fn(), destroy: vi.fn() };
vi.mock("cobe", () => ({ default: vi.fn(() => globe) }));

// A controllable animation frame queue.
let frames = [];
function flush(count, at) {
  for (let i = 0; i < count && frames.length; i += 1) {
    const [, callback] = frames.shift();
    callback(at(i));
  }
}

function webgl(available) {
  if (available) {
    vi.stubGlobal("WebGLRenderingContext", function WebGLRenderingContext() {});
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => ({}));
  }
}

function reducedMotion(reduce) {
  vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
    matches: reduce && query.includes("prefers-reduced-motion"), media: query,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
  }));
}

const show = () => render(<ThemeProvider theme={createAppTheme()}><KenyaGlobe /></ThemeProvider>);
const phis = () => globe.update.mock.calls.map(([state]) => state.phi).filter((phi) => phi !== undefined);
const kenya = facing(KENYA).phi;

beforeEach(() => {
  frames = [];
  let id = 0;
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => { id += 1; frames.push([id, callback]); return id; });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation((cancelled) => { frames = frames.filter(([id]) => id !== cancelled); });
});

afterEach(() => {
  globe.update.mockClear();
  globe.destroy.mockClear();
  createGlobe.mockClear();
  window.devicePixelRatio = 1;
});

describe("Kenya globe (issue #28)", () => {
  it("draws a decorative globe facing Kenya with the 47 county markers and a capped pixel ratio", () => {
    webgl(true);
    reducedMotion(false);
    window.devicePixelRatio = 3;
    show();
    const wrapper = screen.getByTestId("kenya-globe");
    expect(wrapper).toHaveAttribute("aria-hidden", "true");
    expect(wrapper.querySelector("canvas")).not.toBeNull();
    expect(createGlobe).toHaveBeenCalledTimes(1);
    const options = createGlobe.mock.calls[0][1];
    expect(options.markers).toHaveLength(47);
    expect(options.phi).toBeCloseTo(kenya);
    expect(options.devicePixelRatio).toBe(MAX_PIXEL_RATIO);
  });

  it("sways only a few degrees either side of Kenya", () => {
    webgl(true);
    reducedMotion(false);
    show();
    flush(400, (i) => i * 100);
    const swing = Math.max(...phis().map((phi) => Math.abs(phi - kenya)));
    expect(swing).toBeGreaterThan(0);
    expect(swing).toBeLessThanOrEqual((SWAY_DEGREES * Math.PI) / 180 + 1e-9);
  });

  it("draws one still image facing Kenya when reduced motion is preferred, then stops", () => {
    webgl(true);
    reducedMotion(true);
    show();
    const start = performance.now();
    flush(20, (i) => start + i * 50);
    flush(5, () => start + STILL_REPAINT_MS + 100);
    expect(new Set(phis())).toEqual(new Set([kenya]));
    expect(frames).toHaveLength(0);
  });

  it("pauses while the tab is hidden", () => {
    webgl(true);
    reducedMotion(false);
    show();
    expect(frames).toHaveLength(1);
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(frames).toHaveLength(0);
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(frames).toHaveLength(1);
  });

  it("shows a still SVG drawing when WebGL is not available", () => {
    webgl(false);
    show();
    expect(screen.getByTestId("globe-fallback")).toBeInTheDocument();
    expect(createGlobe).not.toHaveBeenCalled();
    expect(screen.getByTestId("kenya-globe")).toHaveAttribute("aria-hidden", "true");
  });

  it("falls back to the drawing if the globe cannot start", async () => {
    webgl(true);
    reducedMotion(false);
    createGlobe.mockImplementationOnce(() => { throw new Error("context lost"); });
    show();
    expect(await screen.findByTestId("globe-fallback")).toBeInTheDocument();
  });

  it("releases everything on unmount", () => {
    webgl(true);
    reducedMotion(false);
    const removed = vi.spyOn(document, "removeEventListener");
    const { unmount } = show();
    unmount();
    expect(globe.destroy).toHaveBeenCalledTimes(1);
    expect(frames).toHaveLength(0);
    expect(removed).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
  });
});
