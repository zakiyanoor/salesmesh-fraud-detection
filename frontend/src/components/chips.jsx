import { Chip } from "@mui/material";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import HourglassEmptyOutlined from "@mui/icons-material/HourglassEmptyOutlined";
import TaskAltOutlined from "@mui/icons-material/TaskAltOutlined";
import RemoveCircleOutlineOutlined from "@mui/icons-material/RemoveCircleOutlineOutlined";
import GavelOutlined from "@mui/icons-material/GavelOutlined";
import { FLAG_SOURCE_LABELS, OUTCOME_LABELS, REVIEW_STATUS_LABELS } from "../format";

const chip = { size: "small", variant: "outlined" };

/** Decision status: Proposed (waiting for compliance) or Confirmed. Label and icon, never colour alone. */
export function DecisionStatusChip({ status }) {
  if (status === "confirmed") {
    return <Chip {...chip} color="success" icon={<TaskAltOutlined fontSize="small" />} label="Confirmed" />;
  }
  if (status === "pending_confirmation") {
    return <Chip {...chip} color="warning" icon={<HourglassEmptyOutlined fontSize="small" />} label="Proposed" />;
  }
  return <Chip {...chip} icon={<RemoveCircleOutlineOutlined fontSize="small" />} label={REVIEW_STATUS_LABELS.none} />;
}

export function OutcomeChip({ outcome }) {
  return (
    <Chip
      {...chip}
      color={outcome === "confirmed_fraud" ? "error" : "success"}
      icon={outcome === "confirmed_fraud" ? <GavelOutlined fontSize="small" /> : <CheckCircleOutlined fontSize="small" />}
      label={OUTCOME_LABELS[outcome] || outcome}
    />
  );
}

/** Who flagged the agent; "Not flagged" is a clear, positive state. */
export function FlagSourceChip({ source }) {
  if (source === "None" || !source) {
    return <Chip {...chip} color="success" icon={<CheckCircleOutlined fontSize="small" />} label={FLAG_SOURCE_LABELS.None} />;
  }
  return <Chip {...chip} label={FLAG_SOURCE_LABELS[source] || source} />;
}
