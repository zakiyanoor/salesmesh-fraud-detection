import { Chip } from "@mui/material";
import ReportOutlined from "@mui/icons-material/ReportOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import HelpOutlineOutlined from "@mui/icons-material/HelpOutlineOutlined";

const RISK_LABELS = { high: "High risk", review: "Review", low: "Low risk", none: "Not scored" };
const ICONS = { high: ReportOutlined, review: WarningAmberOutlined, low: CheckCircleOutlined, none: HelpOutlineOutlined };

/** risk_band from the API (high, review, low or null): always a label and an icon, never colour alone. */
export default function RiskBadge({ band }) {
  const key = band in ICONS ? band : "none";
  const Icon = ICONS[key];
  return (
    <Chip
      size="small"
      variant="outlined"
      icon={<Icon fontSize="small" />}
      label={RISK_LABELS[key]}
      sx={{
        color: `risk.${key}`,
        borderColor: (theme) => theme.palette.risk[key],
        "& .MuiChip-icon": { color: "inherit" },
      }}
    />
  );
}
