import { useEffect, useRef, useState } from "react";
import createGlobe from "cobe";
import { Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import GlobeFallback from "./GlobeFallback";
import { COUNTY_MARKERS } from "./kenyaCounties";
import { KENYA, MAX_PIXEL_RATIO, STILL_REPAINT_MS, facing, hasWebGL, hexToRgb, swayPhi } from "./globeMath";

const reducedMotion = () => Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

/** cobe colours for the active scheme; the markers are the app's accent. */
function look(palette) {
  const dark = palette.mode === "dark";
  return {
    dark: dark ? 1 : 0,
    diffuse: dark ? 1.2 : 1.5,
    mapBrightness: dark ? 3 : 1.5,
    mapSamples: dark ? 18000 : 22000,
    baseColor: dark ? [0.34, 0.37, 0.42] : [0.93, 0.95, 0.98],
    glowColor: dark ? [0.14, 0.22, 0.38] : [0.86, 0.91, 0.98],
    markerColor: hexToRgb(palette.primary.main),
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
  const colours = look(theme.palette);
  const key = JSON.stringify(colours);

  useEffect(() => {
    if (fallback || !canvas.current || !wrapper.current) return undefined;
    const dpr = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
    const size = () => Math.max(1, Math.round(wrapper.current.clientWidth * dpr));
    const { phi, theta } = facing(KENYA);
    let globe;
    try {
      globe = createGlobe(canvas.current, {
        devicePixelRatio: dpr, width: size(), height: size(), phi, theta,
        markers: COUNTY_MARKERS, opacity: 1, ...JSON.parse(key),
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
        <Box component="canvas" ref={canvas} sx={{ width: "100%", height: "100%", display: "block", contain: "layout paint size" }} />
      )}
    </Box>
  );
}
