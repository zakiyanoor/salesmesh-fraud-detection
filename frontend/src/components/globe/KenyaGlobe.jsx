import { useEffect, useRef, useState } from "react";
import createGlobe from "cobe";
import { Box } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { SPHERE } from "./sphereColours";
import GlobeFallback from "./GlobeFallback";
import { COUNTY_MARKERS, GRID_DOT } from "./kenyaCounties";
import { graticuleArcs, kenyaGrid } from "./kenyaShape";
import { KENYA, MAX_PIXEL_RATIO, STILL_REPAINT_MS, ZOOM, facing, hasWebGL, hexToRgb, swayPhi } from "./globeMath";

// Kenya's dot grid and the latitude and longitude lines, worked out once when the chunk loads.
const GRID = kenyaGrid();
const ARCS = graticuleArcs();

const reducedMotion = () => Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

/**
 * cobe settings. Only Kenya is drawn: cobe's world land dots are switched off, and Kenya is a grid of small
 * neutral markers with the county dots in the accent on top.
 */
function look() {
  const neutral = [0.42, 0.47, 0.55];
  return {
    dark: 1,
    diffuse: 1.2,
    // cobe reads 0 as "not set" (mapBrightness || 1), so a vanishing value turns the world map off.
    mapBrightness: 0.0001,
    mapBaseBrightness: 0,
    mapSamples: 1000,
    baseColor: [0.34, 0.37, 0.42],
    glowColor: [0.14, 0.22, 0.38],
    markerColor: hexToRgb(SPHERE.primary.main),
    markerElevation: 0,
    scale: ZOOM,
    // Very faint latitude and longitude lines, lying on the sphere.
    arcColor: [0.11, 0.13, 0.17],
    // Thin at this zoom: cobe draws arc width in globe units, so it grows with the scale.
    arcWidth: 0.04,
    arcHeight: 0,
    neutral,
  };
}

/**
 * A globe centred on Kenya with a dot for each county (issue #28). Decorative: the page's text carries the
 * meaning. It sways a few degrees either side of Kenya, pauses when the tab is hidden or the globe is off
 * screen, draws one still frame when reduced motion is preferred, and falls back to an SVG drawing without
 * WebGL. Everything it starts is released on unmount.
 */
export default function KenyaGlobe() {
  const theme = useTheme();
  const wrapper = useRef(null);
  const canvas = useRef(null);
  const [fallback, setFallback] = useState(() => !hasWebGL());
  const colours = look();
  const key = JSON.stringify(colours);

  useEffect(() => {
    if (fallback || !canvas.current || !wrapper.current) return undefined;
    const dpr = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
    const size = () => Math.max(1, Math.round(wrapper.current.clientWidth * dpr));
    const { phi, theta } = facing(KENYA);
    const { neutral, ...settings } = JSON.parse(key);
    // Kenya's grid first, then the county dots on top.
    const markers = [...GRID.map(([lat, lng]) => ({ location: [lat, lng], size: GRID_DOT, color: neutral })), ...COUNTY_MARKERS];
    let globe;
    try {
      globe = createGlobe(canvas.current, {
        devicePixelRatio: dpr, width: size(), height: size(), phi, theta,
        markers, arcs: ARCS, opacity: 1, ...settings,
      });
    } catch {
      // WebGL was reported but cannot be used (for example a lost context): show the drawing instead.
      queueMicrotask(() => setFallback(true));
      return undefined;
    }

    const still = reducedMotion();
    let frame = 0;
    let visible = !document.hidden;
    let onScreen = true;
    const start = performance.now();
    let stillUntil = performance.now() + STILL_REPAINT_MS;
    const tick = (now) => {
      if (still) {
        // The same frame, facing Kenya, until the map has loaded; then nothing more is drawn.
        globe.update({ phi });
        frame = now < stillUntil ? requestAnimationFrame(tick) : 0;
        return;
      }
      globe.update({ phi: swayPhi(now - start, phi) });
      frame = requestAnimationFrame(tick);
    };
    const run = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      if (visible && onScreen && (!still || performance.now() < stillUntil)) frame = requestAnimationFrame(tick);
    };
    // With reduced motion one still image, facing Kenya; otherwise the sway, while it can be seen.
    globe.update({ phi });
    run();

    const onVisibility = () => {
      visible = !document.hidden;
      run();
    };
    document.addEventListener("visibilitychange", onVisibility);
    const intersection = typeof IntersectionObserver === "function"
      ? new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; run(); })
      : null;
    intersection?.observe(wrapper.current);
    const resize = typeof ResizeObserver === "function"
      ? new ResizeObserver(() => {
        globe.update({ width: size(), height: size(), phi });
        if (still) {
          stillUntil = performance.now() + STILL_REPAINT_MS;
          run();
        }
      })
      : null;
    resize?.observe(wrapper.current);

    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("visibilitychange", onVisibility);
      intersection?.disconnect();
      resize?.disconnect();
      globe.destroy();
    };
  }, [fallback, key]);

  return (
    <Box ref={wrapper} aria-hidden="true" data-testid="kenya-globe" sx={{ width: "100%", aspectRatio: "1 / 1", position: "relative" }}>
      {fallback ? (
        <GlobeFallback />
      ) : (
        <>
          {/* Zoomed in, the sphere is larger than the canvas; the circle keeps it reading as a globe. */}
          <Box component="canvas" ref={canvas} sx={{
            width: "100%", height: "100%", display: "block", contain: "layout paint size", borderRadius: "50%",
            // A clear edge, so the dark sphere stands apart on both page backgrounds.
            boxShadow: `0 0 0 1px ${alpha(SPHERE.primary.main, theme.palette.mode === "dark" ? 0.4 : 0.55)}`,
          }} />
          {/* A soft glow over Kenya (cobe has no glow for markers). */}
          <Box sx={{
            position: "absolute", left: "50%", top: "50%", width: "78%", height: "78%", transform: "translate(-50%, -50%)",
            borderRadius: "50%", pointerEvents: "none", mixBlendMode: "screen",
            background: `radial-gradient(circle, ${alpha(SPHERE.primary.main, 0.14)} 0%, ${alpha(SPHERE.primary.main, 0)} 70%)`,
          }} />
        </>
      )}
    </Box>
  );
}
