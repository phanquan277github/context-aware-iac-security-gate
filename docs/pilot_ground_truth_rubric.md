# Pilot Preliminary Ground-Truth Ranking Rubric

## Purpose

This rubric is used only for preliminary ranking during the Pilot.
It is intended to test whether security findings can be ranked
consistently before the final annotation protocol is applied to the
main dataset.

This preliminary ranking is not the final frozen ground truth.

## Ranking unit

The ranking unit is an individual normalized security finding within
a scenario. In this preliminary stage, raw Checkov findings are used
as the candidate observations.

The scenario is the grouping unit.

## Independence requirements

The preliminary ranking must not use:

- Checkov finding order
- ML predictions
- deterministic contextual-score output
- model feature importance

The ranking is based on security reasoning about the observed
Terraform configuration and the defined business context.

## Ranking considerations

The annotator considers:

1. Direct security impact
2. Exposure or attack-surface implications
3. Privilege or data-access impact
4. Business context:
   - environment
   - asset criticality
   - data sensitivity

## Preliminary priority interpretation

Rank 1 represents the finding judged highest priority within the
scenario.

Lower ranks represent progressively lower priority.

Findings that are primarily hardening or governance observations,
without a direct security exposure in the evaluated configuration,
are expected to receive lower priority.

## Relevance mapping for NDCG

For the preliminary ranking:

- Rank 1 -> relevance 3
- Rank 2 -> relevance 2
- Rank 3 -> relevance 1
- Rank 4 and below -> relevance 0

This mapping will be frozen and applied consistently after the final
ground-truth annotation protocol is established.

## Annotator status

The Pilot preliminary ranking is single-annotator only.

It must not be described as independent annotation or inter-annotator
agreement.

The final dataset should use the previously defined independent
annotation protocol where feasible.
