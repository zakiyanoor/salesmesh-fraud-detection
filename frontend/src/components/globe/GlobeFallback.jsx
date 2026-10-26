import { useTheme } from "@mui/material/styles";
import { KENYA_COUNTIES } from "./kenyaCounties";
import { project } from "./globeMath";

const R = 100;
const STEP = 7;
// Kenya spans only a few degrees, so the county dots are spread out from the centre to be visible.
const COUNTY_SPREAD = 4;

/** A still dotted disc with the county dots, for browsers without WebGL (issue #28). Decorative. */
export default function GlobeFallback() {
  const theme = useTheme();
  const dots = [];
  for (let y = -R + STEP / 2; y < R; y += STEP) {
    for (let x = -R + STEP / 2; x < R; x += STEP) {
      if (x * x + y * y < (R - 3) * (R - 3)) dots.push([x, y]);
    }
  }
  const counties = KENYA_COUNTIES.map(([county, , lat, lng]) => [county, project(lat, lng)])
    .filter(([, p]) => p)
    .map(([county, [x, y]]) => [county, x * R * COUNTY_SPREAD, -y * R * COUNTY_SPREAD]);

  return (
    <svg viewBox={`${-R - 4} ${-R - 4} ${2 * R + 8} ${2 * R + 8}`} width="100%" height="100%" data-testid="globe-fallback" focusable="false">
      <circle r={R} fill="none" stroke={theme.palette.divider} strokeWidth={1} />
      {dots.map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r={1} fill={theme.palette.text.secondary} opacity={0.35} />)}
      {counties.map(([county, x, y]) => <circle key={county} cx={x} cy={y} r={2} fill={theme.palette.primary.main} />)}
    </svg>
  );
}
