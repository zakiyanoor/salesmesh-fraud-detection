// Ring graph layout (issue #28), kept apart from the component so it can be tested on its own.

/** Deterministic circle layout: members in agent ID order, the first at the top, then clockwise. */
export function layout(agentIds) {
  const n = agentIds.length;
  const radius = Math.max(110, 22 * n);
  const centre = radius + 70;
  const positions = {};
  agentIds.forEach((id, i) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    positions[id] = { x: centre + radius * Math.cos(angle), y: centre + radius * Math.sin(angle) };
  });
  return { size: centre * 2, positions };
}
