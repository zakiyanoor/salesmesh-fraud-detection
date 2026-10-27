import { Box, Tooltip } from "@mui/material";
import { formatNumber, formatPercentile } from "../format";
import { mono } from "../theme";

/**
 * The raw model score, then its rank in the latest run ("Top X%", muted). The exact percentile is in the
 * aria-label and the tooltip. Scores and ranks are not probabilities.
 */
export default function ScoreWithRank({ score, percentile, digits = 3 }) {
  const text = formatNumber(score, digits);
  if (percentile == null) return <Box component="span" sx={mono}>{text}</Box>;
  const exact = Number(percentile).toFixed(1);
  return (
    <Box component="span" role="group" aria-label={`Score ${text}, percentile ${exact}`} sx={{ whiteSpace: "nowrap" }}>
      <Box component="span" sx={mono}>{text}</Box>{" "}
      <Tooltip
        describeChild
        title={`Percentile ${exact}: higher than ${exact}% of agents scored in the latest run. A rank, not a probability.`}
      >
        <Box component="span" tabIndex={0} sx={{ color: "text.secondary", fontSize: "max(12px, 0.85em)" }}>
          {formatPercentile(percentile)}
        </Box>
      </Tooltip>
    </Box>
  );
}
