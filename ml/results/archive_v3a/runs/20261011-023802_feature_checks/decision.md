# Decision for volume_vs_peers

Training agents: 700 (91 fraud).

- Single-feature AUC (all fraud vs legitimate): 0.780 (rule: > 0.55)
- Max |Spearman| with a base feature: 0.807 (rule: <= 0.85)

**Decision: KEEP volume_vs_peers.**
