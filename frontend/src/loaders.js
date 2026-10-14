import { api } from "./api";

// Stable loaders for useApi when a page needs more than one endpoint.
export const loadAgentsAndDecisions = () => Promise.all([api.getAllAgents(), api.getReviewDecisions()]);
