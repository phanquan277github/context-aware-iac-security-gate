# Pilot GO / REFINE / STOP Decision

## Decision

GO

## Rationale

The Pilot successfully demonstrated the technical and methodological
feasibility of the proposed experimental design.

### Terraform feasibility

- 10/10 scenarios passed Terraform initialization.
- 10/10 scenarios passed Terraform validation.

### Security scanning feasibility

- 10/10 scenarios produced valid Checkov JSON outputs.
- 10/10 scenarios had zero parsing errors.
- 118 raw failed Checkov findings were observed across the Pilot.

### Metric feasibility

- 10/10 scenarios are eligible for NDCG@3.
- 8/10 scenarios are eligible for NDCG@5.
- SCN-007 and SCN-008 contain only 3 findings each and are therefore
  eligible for NDCG@3 but not NDCG@5.

### Security category coverage

All 8 predefined security categories have at least one observed
Terraform + Checkov evidence in the Pilot.

- Covered: 8
- Weak: 0
- Missing: 0

### Contrastive design

All 5 contrastive pairs satisfy:

- equivalent Terraform infrastructure
- different business context
- same objective infrastructure facts
- equivalent observed Checkov findings

### Annotation feasibility

All preliminary annotation feasibility checks passed.

The preliminary ranking was single-annotator only and is not treated
as final frozen ground truth or independent annotation.

## Important Pilot Observation

The Pilot demonstrates that contextual variation can be introduced
while holding Terraform infrastructure and observed scanner findings
constant across contrastive pairs.

The preliminary ranking subset does not by itself demonstrate that
business context changes the relative priority of findings.

This question remains an empirical question for the main experiment.

## Decision Interpretation

GO means that the Pilot provides sufficient evidence to proceed to
construction of the main experimental dataset and experimental
pipeline.

GO does not mean that the proposed ML models have demonstrated
superior prioritization performance.

## Next Stage

Proceed to:

1. Full dataset construction
2. Final annotation protocol
3. Context feature extraction
4. Deterministic contextual baseline
5. Random Forest model
6. Optional XGBoost comparison
7. Experimental evaluation
