// Kenya as dots for the landing globe (issue #28): which points lie inside the border, the dot grid, and a
// faint latitude and longitude grid so the sphere still reads as a globe.
import { KENYA_OUTLINE } from "./kenyaOutline";

// Spacing of the dot grid inside Kenya, in degrees.
export const GRID_STEP = 0.2;
// The latitude and longitude lines on the sphere, every this many degrees.
export const GRATICULE_STEP = 10;

/** Ray casting: whether [lng, lat] lies inside the polygon (a ring of [lng, lat] points). */
export function insidePolygon(lng, lat, ring = KENYA_OUTLINE) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[j];
    if ((y1 > lat) !== (y2 > lat) && lng < ((x2 - x1) * (lat - y1)) / (y2 - y1) + x1) inside = !inside;
  }
  return inside;
}

export function bounds(ring = KENYA_OUTLINE) {
  const lngs = ring.map(([lng]) => lng);
  const lats = ring.map(([, lat]) => lat);
  return { minLng: Math.min(...lngs), maxLng: Math.max(...lngs), minLat: Math.min(...lats), maxLat: Math.max(...lats) };
}

/** A regular grid of [lat, lng] points, step degrees apart, keeping those inside Kenya. */
export function kenyaGrid(step = GRID_STEP, ring = KENYA_OUTLINE) {
  const { minLng, maxLng, minLat, maxLat } = bounds(ring);
  const points = [];
  // Rows and columns are counted from the corner, so the grid is the same on every load.
  for (let r = 0; minLat + r * step <= maxLat; r += 1) {
    for (let c = 0; minLng + c * step <= maxLng; c += 1) {
      const lat = Number((minLat + r * step).toFixed(4));
      const lng = Number((minLng + c * step).toFixed(4));
      if (insidePolygon(lng, lat, ring)) points.push([lat, lng]);
    }
  }
  return points;
}

/**
 * Latitude and longitude lines as cobe arcs lying on the sphere (arcHeight 0): meridians every
 * GRATICULE_STEP degrees from 80 S to 80 N, and parallels from 70 S to 70 N in short segments, so each
 * segment stays close to its parallel.
 */
export function graticuleArcs(step = GRATICULE_STEP) {
  const arcs = [];
  for (let lng = -180; lng < 180; lng += step) arcs.push({ from: [-80, lng], to: [80, lng] });
  for (let lat = -70; lat <= 70; lat += step) {
    for (let lng = -180; lng < 180; lng += step) arcs.push({ from: [lat, lng], to: [lat, lng + step] });
  }
  return arcs;
}
