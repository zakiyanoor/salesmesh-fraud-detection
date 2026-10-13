"""
Admin report downloads (issue #18): two CSV files and a one-page PDF.

- Names, phone numbers and national IDs are masked in every report.
- CSV cells that a spreadsheet would read as a formula (starting with =, +, -,
  @, tab or carriage return) get a leading apostrophe (formula injection).
- The PDF is built with reportlab, uncompressed so its text can be checked.
"""

import csv
import hashlib
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src import audit, threat_intel
from src.db import Agent, AgentIdentity, AgentScore, DataLoad
from src.risk import risk_band

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
AUDIT_CSV_CAP = 50000
FLAGGED_COLUMNS = ["agent_id", "region", "account_status", "anomaly_score", "threshold", "flag_source", "risk_band",
                   "reasons", "duplicate_pairs", "masked_name", "masked_phone", "masked_national_id"]
AUDIT_COLUMNS = ["timestamp", "actor", "actor_type", "category", "action", "target_agent_id", "request_ip", "details"]


def csv_safe(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def to_csv(columns, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([csv_safe("" if row.get(c) is None else row.get(c)) for c in columns])
    return buffer.getvalue().encode("utf-8")


def mask_tail(value, visible=3):
    text_value = str(value)
    return "*" * max(len(text_value) - visible, 0) + text_value[-visible:]


def mask_name(full_name):
    """First letter of each name, the rest as '*': "Agnes Omondi" -> "A**** O*****"."""
    if not full_name:
        return None
    return " ".join(part[0] + "*" * (len(part) - 1) for part in full_name.split())


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def flagged_agents_csv(db_session, run):
    """Agents flagged by the model or the rule in the run, highest score first."""
    rows = (db_session.query(AgentScore, Agent, AgentIdentity)
            .join(Agent, Agent.agent_id == AgentScore.agent_id)
            .outerjoin(AgentIdentity, AgentIdentity.agent_id == AgentScore.agent_id)
            .filter(AgentScore.run_id == run.run_id, AgentScore.flag_source != "None")
            .order_by(AgentScore.anomaly_score.desc(), AgentScore.agent_id).all())
    records = [{
        "agent_id": score.agent_id, "region": agent.region, "account_status": agent.account_status,
        "anomaly_score": round(score.anomaly_score, 6), "threshold": round(score.threshold, 6),
        "flag_source": score.flag_source, "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold),
        "reasons": score.reasons, "duplicate_pairs": score.duplicate_pairs,
        "masked_name": mask_name(identity.full_name) if identity else None,
        "masked_phone": mask_tail(identity.phone_number) if identity else None,
        "masked_national_id": mask_tail(identity.national_id_number) if identity else None,
    } for score, agent, identity in rows]
    return to_csv(FLAGGED_COLUMNS, records), len(records)


def audit_log_csv(db_session, args):
    """Audit entries matching the audit-log filters, newest first, at most AUDIT_CSV_CAP rows."""
    entries = audit.filtered_query(db_session, args).limit(AUDIT_CSV_CAP).all()
    records = [{"timestamp": e.timestamp.isoformat(), "actor": e.admin_id, "actor_type": e.actor_type,
                "category": e.category, "action": e.action, "target_agent_id": e.target_agent_id,
                "request_ip": e.request_ip, "details": e.details} for e in entries]
    return to_csv(AUDIT_COLUMNS, records), len(records)


def data_fingerprint(db_session):
    """(load_id, sha256 over the loaded files' hashes) of the latest data load."""
    load = db_session.query(DataLoad).order_by(DataLoad.loaded_at.desc()).first()
    if load is None:
        return None, None
    combined = "\n".join(f"{name}:{digest}" for name, digest in sorted(load.file_hashes.items()))
    return load.load_id, sha256(combined.encode())


def detection_summary_pdf(db_session, run, actor):
    """One-page PDF: run status, counts by flag_source and risk_band, top 10 regions; footer with time, actor, data hash."""
    summary = threat_intel.summary(db_session, run)
    regions = threat_intel.by_region(db_session, run)["top_by_flagged_rate"]
    load_id, data_hash = data_fingerprint(db_session)
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    styles = getSampleStyleSheet()
    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                       ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e3df")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)])

    def table(rows, widths):
        t = Table(rows, colWidths=widths, hAlign="LEFT")
        t.setStyle(grid)
        return t

    styles["Title"].fontSize, styles["Title"].spaceAfter = 15, 4
    styles["Heading2"].fontSize, styles["Heading2"].spaceBefore, styles["Heading2"].spaceAfter = 11, 2, 3
    story = [
        Paragraph("SalesMesh fraud detection: detection summary", styles["Title"]),
        Paragraph("Run status", styles["Heading2"]),
        table([["Field", "Value"], ["Run id", run.run_id], ["Status", run.status], ["Trigger", run.trigger],
               ["Started (UTC)", run.started_at.isoformat(timespec="seconds")],
               ["Finished (UTC)", run.finished_at.isoformat(timespec="seconds")],
               ["Model version", run.model_version], ["Cutoff", f"{run.threshold:.6f}"],
               ["Agents scored", str(summary["agents_scored"])],
               ["Flagged by the model", f"{summary['flagged']} ({summary['flagged_rate']:.1%})"],
               ["Flagged by the duplicate rule", str(summary["rule_flagged"])]], [55 * mm, 110 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("Agents by flag_source and risk_band", styles["Heading2"]),
        table([["flag_source", "Agents"]] + [[k, str(v)] for k, v in summary["flag_sources"].items()], [55 * mm, 30 * mm]),
        Spacer(1, 2 * mm),
        table([["risk_band", "Agents"]] + [[k, str(v)] for k, v in summary["risk_bands"].items()], [55 * mm, 30 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("Top 10 regions by flagged rate (at least 5 agents)", styles["Heading2"]),
        table([["Region", "Agents", "Flagged", "Rule flagged", "Flagged rate"]] +
              [[r["region"], str(r["agents"]), str(r["flagged"]), str(r["rule_flagged"]), f"{r['flagged_rate']:.1%}"]
               for r in regions], [45 * mm, 22 * mm, 22 * mm, 28 * mm, 28 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("Scores are anomaly scores, not probabilities. A flag is a request for human review. "
                  "Synthetic data only.", styles["Italic"]),
    ]
    footer = [f"Generated {generated} by {actor}. Data load {load_id}.", f"Data hash (sha256): {data_hash}"]

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(15 * mm, 12 * mm, footer[0])
        canvas.drawString(15 * mm, 8.5 * mm, footer[1])
        canvas.drawRightString(195 * mm, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                                 bottomMargin=20 * mm, title="Detection summary", author=actor, pageCompression=0)
    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue(), summary["agents_scored"], {"load_id": load_id, "data_hash": data_hash}
