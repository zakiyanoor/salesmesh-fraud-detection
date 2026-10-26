// Globe maths for the landing page (issue #28): where to look, how far to sway, and colours from the theme.

// Roughly the middle of Kenya; the globe faces this point.
export const KENYA = { lat: 0.2, lng: 37.9 };
// A slow sway of a few degrees either side of Kenya, so Kenya stays in view (not a spin).
// Zoomed in, a few degrees is a large move, so the sway is small enough to keep Kenya near the centre.
export const SWAY_DEGREES = 2;
export const SWAY_SECONDS = 18;
export const MAX_PIXEL_RATIO = 2;
// How far the globe is zoomed in (cobe's scale), so Kenya is large while the sphere still reads as a globe.
export const ZOOM = 5.5;
// cobe loads its map image asynchronously and does not redraw when it arrives, so a still globe is repainted,
// always at the same angle, for this long after it starts or resizes.
export const STILL_REPAINT_MS = 1200;

const toRadians = (degrees) => (degrees * Math.PI) / 180;

/** cobe's phi and theta that turn a latitude and longitude to face the viewer. */
export function facing({ lat, lng }) {
  return { phi: Math.PI - (toRadians(lng) - Math.PI / 2), theta: toRadians(lat) };
}

/** phi at time t (milliseconds): Kenya plus or minus SWAY_DEGREES. */
export function swayPhi(t, centre = facing(KENYA).phi) {
  return centre + toRadians(SWAY_DEGREES) * Math.sin((2 * Math.PI * t) / (SWAY_SECONDS * 1000));
}

/** "#1976D2" -> [0.098, 0.463, 0.824] for cobe. */
export function hexToRgb(hex) {
  const value = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255);
}

/** Orthographic projection centred on Kenya: [x, y] in -1..1 (y up), or null on the far side. */
export function project(lat, lng, centre = KENYA) {
  const [phi, lambda, phi0, lambda0] = [lat, lng, centre.lat, centre.lng].map(toRadians);
  const cosC = Math.sin(phi0) * Math.sin(phi) + Math.cos(phi0) * Math.cos(phi) * Math.cos(lambda - lambda0);
  if (cosC < 0) return null;
  return [Math.cos(phi) * Math.sin(lambda - lambda0),
    Math.cos(phi0) * Math.sin(phi) - Math.sin(phi0) * Math.cos(phi) * Math.cos(lambda - lambda0)];
}

/** Whether this browser can draw WebGL. */
export function hasWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(window.WebGLRenderingContext && (canvas.getContext("webgl2") || canvas.getContext("webgl")));
  } catch {
    return false;
  }
}
