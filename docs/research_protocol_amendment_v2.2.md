# Research Protocol Amendment v2.2

## 1. Primary Ranking

The primary ranking unit is the security finding within a scenario.

All in-scope findings within each scenario are reviewed and ranked
from 1 to N.

Relevance mapping:

- Rank 1 -> 3
- Rank 2 -> 2
- Rank 3 -> 1
- Rank 4+ -> 0

Pair-pool ranking is not used for the primary task.

## 2. Experiment B1

The main scenario-level evaluation compares:

1. Severity-only baseline
2. Deterministic contextual scoring
3. Random Forest Regressor
4. XGBoost Regressor (optional)

Primary metrics:

- NDCG@3
- NDCG@5

Secondary metric:

- Spearman correlation

Supplementary regression metrics:

- MAE
- RMSE

## 3. Context Representation

Scenario-level:

- environment
- asset_criticality
- data_sensitivity

Finding/resource-level:

- internet_exposure
- privilege_impact
- reachability
- relevant infrastructure facts

## 4. Experiment B2

B2 is a secondary contrastive context-sensitivity analysis supporting RQ2.

A matched finding is defined by:

- same check_id
- same normalized logical Terraform resource address

For a matched finding:

    delta_score = score(B) - score(A)

When B represents the higher-risk business context,
the expected direction is:

    delta_score > 0

Contrastive Direction Accuracy (CDA):

    matched findings with delta_score > 0
    -------------------------------------
    total matched findings

CDA is descriptive.

Matched findings within the same contrastive family
are not treated as independent statistical observations.

Inferential analysis uses family-level summaries.

## 5. Annotation

Annotators must explicitly consider business context.

A context change does not automatically require a ranking change.

When matched findings retain the same relative priority,
the annotator provides a brief rationale.

Annotators remain blind to model outputs,
baseline outputs, and predicted scores.

## 6. Dataset Split

Dataset splitting is performed by scenario or scenario family.

Contrastive variants from the same family remain in the same split.

Finding-level random splitting is not used.

## 7. Scope

Mandatory scope:

- AWS
- Terraform
- Checkov
- Static analysis
- Context-aware prioritization
- Random Forest
- Security Gate prototype

Out of scope:

- Runtime LLM
- RAG
- MCP
- Multi-agent systems
- Kubernetes
- Multi-cloud
- Attack graphs
- SIEM
- Autonomous remediation
- LLM fine-tuning
- XGBRanker
- Large dashboard

terraform plan is not mandatory unless explicitly required
by a selected feature.

## 8. Freeze

This amendment freezes the methodology for the Main Dataset
and Main Experiments.

The Research Questions remain unchanged.

Further methodological changes require an explicit
documented decision.
