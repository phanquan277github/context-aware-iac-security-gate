# Pilot Protocol

## Purpose

Evaluate the feasibility of the dataset design, security scanning
workflow, contextual metadata, and ranking procedure before building
the full experimental dataset.

## Scope

- Cloud: AWS
- IaC: Terraform
- Scanner: Checkov
- Scenario type: controlled
- No AWS deployment
- No terraform plan
- No ML training

## Pilot Size

10 scenarios organized into 5 contrastive scenario families.

## Observation Unit

Individual security finding.

## Experimental Grouping Unit

Terraform scenario.

## Security Categories

1. IAM wildcard action
2. IAM wildcard resource
3. Excessive privilege
4. Public S3
5. Public RDS
6. Security Group 0.0.0.0/0
7. Open administrative port
8. Missing encryption/logging

## Primary Pilot Questions

1. Do Terraform scenarios validate successfully?
2. Does Checkov produce usable findings?
3. Are findings available in machine-readable JSON?
4. Can contextual information be assigned consistently?
5. Are there enough findings for ranking?
6. Are enough scenarios eligible for NDCG@3 and NDCG@5?
7. Do contrastive scenarios provide contextual variation?
8. Is the annotation procedure feasible?

## Ground Truth

Pilot ranking is preliminary.

Final ground truth will be created before the main experiments
and frozen before model evaluation.

## Leakage Prevention

- Scenario families remain intact during train/test splitting.
- Business metadata comes from explicit scenario metadata.
- Resource naming conventions do not define business context.
- Ground truth must not use model predictions.

## Exit Criteria

GO:
The pilot provides sufficient findings and contextual variation.

REFINE:
The pipeline works but scenario design requires modification.

STOP:
The proposed design cannot produce usable experimental data.
