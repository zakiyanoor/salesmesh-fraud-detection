// How a flag is made (issue #28): the diagram's flag sources and its text alternative.

// The flag sources in the app's colours: Model and Both are the high risk band, Rule only the review band.
export const FLAG_STEPS = [
  { key: "model", label: "Model", band: "high" },
  { key: "rule", label: "Rule only", band: "review" },
  { key: "both", label: "Both", band: "high" },
];

export const STEPS = [
  "Four signals from each agent's activations feed the model: busiest 24 hours, time of day, customer ID patterns and shared customers.",
  "The duplicate activation rule runs beside the model on the same activation records.",
  "Either one raises a flag. The flag source is Model, Rule only or Both.",
  "A fraud analyst reviews the flag and proposes an outcome with a note.",
  "A compliance officer, a different person, agrees or overrules.",
  "Every step is written to the audit log.",
];
