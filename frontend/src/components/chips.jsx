import { Chip, Tooltip } from "@mui/material";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import HourglassEmptyOutlined from "@mui/icons-material/HourglassEmptyOutlined";
import TaskAltOutlined from "@mui/icons-material/TaskAltOutlined";
import RemoveCircleOutlineOutlined from "@mui/icons-material/RemoveCircleOutlineOutlined";
import GavelOutlined from "@mui/icons-material/GavelOutlined";
import BlockOutlined from "@mui/icons-material/BlockOutlined";
import ErrorOutlineOutlined from "@mui/icons-material/ErrorOutlineOutlined";
import UndoOutlined from "@mui/icons-material/UndoOutlined";
import SwapHorizOutlined from "@mui/icons-material/SwapHorizOutlined";
import ScheduleOutlined from "@mui/icons-material/ScheduleOutlined";
import EditNoteOutlined from "@mui/icons-material/EditNoteOutlined";
import FlagOutlined from "@mui/icons-material/OutlinedFlag";
import { FLAG_SOURCE_LABELS, OUTCOME_LABELS, REVIEW_STATUS_LABELS, STATUS_LABELS, WAITING_TEXT } from "../format";
import { auditResult } from "../audit";

const chip = { size: "small", variant: "outlined" };

/** Decision status: Proposed (waiting for compliance) or Confirmed. Label and icon, never colour alone. */
export function DecisionStatusChip({ status }) {
  const icons = {
    pending_confirmation: [<HourglassEmptyOutlined fontSize="small" key="i" />, "warning"],
    agreed: [<TaskAltOutlined fontSize="small" key="i" />, "success"],
    overruled: [<SwapHorizOutlined fontSize="small" key="i" />, "info"],
    withdrawn: [<UndoOutlined fontSize="small" key="i" />, "default"],
  };
  if (!icons[status]) {
    return <Chip {...chip} icon={<RemoveCircleOutlineOutlined fontSize="small" />} label={REVIEW_STATUS_LABELS.none} />;
  }
  const [icon, color] = icons[status];
  const shown = <Chip {...chip} color={color} icon={icon} label={STATUS_LABELS[status]} />;
  if (status !== "pending_confirmation") return shown;
  // Proposed: say what it is waiting for, in the decision history's words.
  return (
    <Tooltip title={WAITING_TEXT} describeChild>
      <Chip {...chip} color={color} icon={icon} label={STATUS_LABELS[status]} tabIndex={0} />
    </Tooltip>
  );
}

/** An open proposal waiting longer than the server's limit (3 days). Nothing decides it automatically. */
export function OverdueChip() {
  return <Chip {...chip} color="error" icon={<ScheduleOutlined fontSize="small" />} label="Overdue" />;
}

/** A final decision that a compliance officer corrected since; the history shows each step. */
export function CorrectedChip() {
  return <Chip {...chip} icon={<EditNoteOutlined fontSize="small" />} label="Corrected" />;
}

/** The agent was flagged when the proposal was made but not in the latest detection run. */
export function NoLongerFlaggedChip() {
  return <Chip {...chip} icon={<FlagOutlined fontSize="small" />} label="No longer flagged in the latest run" />;
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

/** Audit event result: Completed, Refused (access denied) or Failed. */
export function AuditResultChip({ entry }) {
  const result = auditResult(entry);
  if (result === "refused") return <Chip {...chip} color="error" icon={<BlockOutlined fontSize="small" />} label="Refused" />;
  if (result === "failed") return <Chip {...chip} color="error" icon={<ErrorOutlineOutlined fontSize="small" />} label="Failed" />;
  return <Chip {...chip} icon={<CheckCircleOutlined fontSize="small" />} label="Completed" />;
}
