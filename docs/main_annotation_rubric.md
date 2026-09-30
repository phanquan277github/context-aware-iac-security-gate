# Main Dataset Annotation Rubric

## Purpose

This rubric defines the procedure for creating the ground-truth
security-finding prioritization used by the main research experiment.

The annotation task is to rank all in-scope security findings within
each scenario according to their relative priority.

The annotation must remain independent of model predictions and
evaluation results.

## Ranking unit

The ranking unit is an individual security finding within one scenario.

The scenario is the grouping unit.

For each scenario:

Rank 1, Rank 2, ..., Rank N

must be assigned to all in-scope findings.

Every finding must receive exactly one rank.

Every rank from 1 to N must occur exactly once.

## Priority considerations

The annotator considers:

1. Direct security impact
2. Exposure or attack-surface implications
3. Privilege or data-access impact
4. Business context:
   - environment
   - asset criticality
   - data sensitivity

The annotator should inspect the referenced Terraform configuration
when the Checkov finding summary alone is insufficient.

## Context treatment

Business context may change the relative priority of findings.

However, context is not required to change the ranking.

For a contrastive pair, if changed context does not alter relative
priority, the annotator should provide a brief reason explaining why
the relative order remains unchanged.

## Ranking independence

The annotator must not use:

- model predictions
- severity-only baseline output
- deterministic contextual-score output
- Random Forest predictions
- XGBoost predictions
- NDCG values
- feature importance
- evaluation results

The Checkov finding order must not determine the annotation order.

## Severity

Severity is an intrinsic finding attribute.

The annotator may consider the severity information as one part of
security reasoning, but must not treat severity as the only ranking
criterion.

## Tie handling

The final annotation requires a unique rank for every finding.

When two findings appear similarly important, the annotator should
resolve the ordering using the more direct security consequence,
exposure, privilege/data-access impact, and available business context.

A brief reason should document the decision.

## Relevance mapping

Relevance is generated automatically from the final human ranking:

Rank 1 -> relevance 3
Rank 2 -> relevance 2
Rank 3 -> relevance 1
Rank 4+ -> relevance 0

The annotator does not manually assign relevance.

## Required rationale

Every annotated finding must contain a non-empty reason.

The reason should explain the relative priority, not merely repeat the
Checkov check name.

## Annotator

Primary annotator:

A1

If a second independent annotator is available, the same annotation
input must be provided independently before comparing results.

If only one annotator is available, the final dataset must explicitly
record the single-annotator limitation.

## Ground-truth status

The resulting ranking is the human ground truth for evaluation.

No model output may be used to modify the ranking after annotation.
