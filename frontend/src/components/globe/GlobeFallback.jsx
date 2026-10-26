import { useTheme } from "@mui/material/styles";
import { KENYA_COUNTIES } from "./kenyaCounties";
import { KENYA_OUTLINE } from "./kenyaOutline";
import { kenyaGrid } from "./kenyaShape";
import { project } from "./globeMath";

const SIZE = 200;
// Kenya fills about 70% of the drawing, as on the zoomed globe.
const FILL = 0.7;

/**
 * Kenya for browsers without WebGL (issue #28): the outline filled with the same dot grid as the globe and
 * the 47 county dots, drawn still in SVG with the same projection centred on Kenya. Decorative.
 */
export default function GlobeFallback() {
  const theme = useTheme();
  const outline = KENYA_OUTLINE.map(([lng, lat]) => project(lat, lng));
  const span = Math.max(...outline.map(([x, y]) => Math.max(Math.abs(x), Math.abs(y))));
  const k = (SIZE * FILL) / 2 / span;
  const at = ([x, y]) => [x * k, -y * k];
  const path = `M${outline.map((p) => at(p).map((v) => v.toFixed(1)).join(" ")).join("L")}Z`;
  const grid = kenyaGrid().map(([lat, lng]) => at(project(lat, lng)));
  const counties = KENYA_COUNTIES.map(([county, , lat, lng]) => [county, ...at(project(lat, lng))]);

  return (
    <svg viewBox={`${-SIZE / 2} ${-SIZE / 2} ${SIZE} ${SIZE}`} width="100%" height="100%" data-testid="globe-fallback" focusable="false">
      <path d={path} fill="none" stroke={theme.palette.divider} strokeWidth={0.6} data-testid="kenya-outline" />
      {grid.map(([x, y]) => <circle key={`${x.toFixed(2)}-${y.toFixed(2)}`} cx={x} cy={y} r={0.55} fill={theme.palette.text.secondary} opacity={0.55} />)}
      {counties.map(([county, x, y]) => <circle key={county} cx={x} cy={y} r={1.3} fill={theme.palette.primary.main} />)}
    </svg>
  );
}
