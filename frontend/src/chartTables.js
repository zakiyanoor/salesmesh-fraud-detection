// The numbers behind each chart, for SectionCard's "Show as table" view (text alternative to the chart).
import { FLAG_SOURCE_LABELS, MODEL_FEATURE_LABELS, formatPercent } from "./format";

const SOURCES = ["ML", "Both", "Rule", "None"];

export const flagSourceTable = (summary) => ({
  columns: [{ key: "source", label: "Flagged by" }, { key: "agents", label: "Agents" }],
  rows: SOURCES.map((s) => ({ source: FLAG_SOURCE_LABELS[s], agents: summary.flag_sources?.[s] ?? 0 })),
});

export const riskBandTable = (summary) => ({
  columns: [{ key: "band", label: "Risk band" }, { key: "agents", label: "Agents" }],
  rows: [["High risk", "high"], ["Review", "review"], ["Low risk", "low"]].map(([band, key]) => ({ band, agents: summary.risk_bands?.[key] ?? 0 })),
});

export const timelineTable = (timeline) => ({
  columns: [{ key: "date", label: "Date" }, { key: "flagged", label: "Flagged agents" }, { key: "other", label: "Other agents" }],
  rows: timeline.days.map((d) => ({ date: d.date, flagged: d.flagged_agents, other: d.other_agents })),
});

export const regionRateTable = (regions) => ({
  columns: [{ key: "region", label: "Region" }, { key: "rate", label: "Flagged rate" }, { key: "flagged", label: "Flagged" }, { key: "agents", label: "Agents" }],
  rows: regions.top_by_flagged_rate.map((r) => ({ region: r.region, rate: formatPercent(r.flagged_rate), flagged: r.flagged, agents: r.agents })),
});

export const scoreDistributionTable = (analytics) => ({
  columns: [{ key: "bucket", label: "Score range" }, { key: "count", label: "Agents" }],
  rows: analytics.score_distribution,
});

export const regionBreakdownTable = (analytics) => ({
  columns: [{ key: "region", label: "Region" }, { key: "flagged", label: "Flagged" }, { key: "total", label: "Total" }],
  rows: analytics.region_breakdown,
});

export const hourTable = (activity) => ({
  columns: [{ key: "hour", label: "Hour of day" }, { key: "activations", label: "Activations" }],
  rows: activity.hours.map((h) => ({ hour: h.hour, activations: h.activations })),
});

export const topFeatureTable = (summary) => ({
  columns: [{ key: "feature", label: "Strongest feature" }, { key: "agents", label: "Flagged agents" }],
  rows: summary.top_features.as_top_feature.map((f) => ({ feature: MODEL_FEATURE_LABELS[f.feature] || f.feature, agents: f.agents })),
});
