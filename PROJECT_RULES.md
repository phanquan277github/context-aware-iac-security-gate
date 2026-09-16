# Project Rules

## Thesis Scope

- Domain: AWS Cloud Security
- IaC: Terraform
- Primary scanner: Checkov
- Primary ML model: Random Forest Regressor
- Comparative ML model: XGBoost Regressor
- CI/CD: GitHub Actions
- Runtime LLM: NOT allowed

## Research Scope

- Finding is the ML observation unit.
- Scenario is the experimental grouping unit.
- Train/test split must be scenario-level.
- Ground truth must be frozen before main experiments.
- Primary metrics:
  - NDCG@3
  - NDCG@5
- Secondary metrics:
  - Spearman correlation
  - Recall@3
- Statistical comparison:
  - Wilcoxon signed-rank
  - Bootstrap confidence interval

## Explicitly Out of Scope

- Kubernetes
- Multi-cloud
- RAG
- MCP
- Multi-agent systems
- Runtime GPT/Gemini/Claude API
- Fine-tuning LLM
- Autonomous remediation
- SIEM integration
- Attack graph
- Complex web dashboard

## Engineering Rules

- Prefer simple implementations.
- Do not add dependencies without justification.
- Do not change the research protocol because of model results.
- Do not modify ground truth after seeing model results.
- Do not use naming conventions as business-context ground truth.
- All experiments must be reproducible.
- Every experiment must save raw results.
