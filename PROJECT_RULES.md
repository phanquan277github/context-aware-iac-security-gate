# Project Rules

## Thesis Scope

- Domain: AWS Cloud Security
- IaC: Terraform
- Primary scanner: Checkov
- Primary ML model: Random Forest Regressor

- Required prioritization baselines:
  - Severity-only prioritization
  - Deterministic context-aware prioritization

- Optional comparative/extension model:
  - XGBoost Regressor
  - XGBoost is NOT required for successful completion of the thesis.
  - It should only be implemented if the primary Random Forest
    pipeline and core experiments are already stable.

- Optional integration/demo:
  - GitHub Actions Security Gate
  - GitHub Actions integration is not a scientific contribution
    and should only be implemented after the core research pipeline
    and evaluation are complete.

- Runtime LLM: NOT allowed

---

## Research Scope

- Finding is the ML observation unit.

- Scenario is the experimental grouping and evaluation unit.

- Train/test separation must be performed at scenario level or at
  the scenario-family level defined by the authoritative research
  methodology.

- Findings originating from the same scenario must not be allowed
  to leak across evaluation boundaries.

- Ground truth must be frozen before final/main experiments.

- Research methodology, feature semantics, labels, baselines, or
  evaluation metrics must not be modified after observing final
  model results merely to improve reported performance.

---

## Core Methods

The required prioritization methods are:

1. Severity-only prioritization

2. Deterministic context-aware prioritization

3. Random Forest-based prioritization

The core scientific comparison is therefore:

Severity-only
vs
Deterministic Context-Aware Baseline
vs
Random Forest

XGBoost is an optional extension and is not part of the minimum
required scientific comparison.

---

## Evaluation

Primary ranking metrics:

- NDCG@3
- NDCG@5

Secondary metrics:

- Spearman correlation

Statistical comparison may include:

- Wilcoxon signed-rank test
- Bootstrap confidence intervals

Evaluation must follow the detailed protocol defined in:

`docs/THESIS_CONTEXT.md`

Do not independently alter metric definitions, eligibility rules,
aggregation units, or statistical procedures.

---

## Ground Truth

- Ground truth must be established independently from final model
  performance.

- Ground truth must be frozen before the main/final experiments.

- Do not modify annotations after seeing Random Forest, baseline,
  or optional XGBoost results merely to improve agreement.

- Annotation decisions must follow the approved rubric and research
  methodology.

- Existing implementation behavior does not automatically define
  ground-truth semantics.

---

## Context Features

Contextual features must follow the approved research definitions.

Relevant authoritative implementation artifacts currently include:

- `dataset/main/context/context_schema.yaml`
- `dataset/main/context/feature_definitions.yaml`
- `dataset/main/context/rule_context_applicability.csv`

Important semantic rule:

Non-applicable and unknown are different states.

- Non-applicable:
  the contextual feature does not belong to the semantics of the
  specific rule/finding.

- Unknown:
  the contextual feature is applicable, but its value cannot be
  determined reliably from available evidence.

These states must not be silently collapsed.

Contextual values requiring evidence must remain traceable to
Terraform source or another approved evidence source.

Do not fabricate context or evidence.

---

## Dataset Integrity

- Preserve provenance of dataset artifacts.

- Do not silently delete or exclude difficult samples merely
  because they produce inconvenient results.

- Dataset inclusion/exclusion must follow the approved research
  methodology.

- Do not use naming conventions as business-context ground truth.

- Do not infer business context solely from resource names,
  filenames, scenario identifiers, directory names, model names,
  or other naming conventions unless explicitly permitted by the
  research specification.

- Avoid duplicate samples crossing evaluation boundaries.

- Avoid target leakage and feature leakage.

- Generated, pilot, historical, and main-research artifacts must
  not be silently mixed when their roles differ.

---

## Reproducibility

- All experiments must be reproducible.

- Every experiment must preserve enough information to reproduce
  the result.

- Preserve raw results where required by the research methodology.

- Record relevant parameters, inputs, outputs, versions, and
  random seeds when applicable.

- Prefer deterministic processing when randomness is unnecessary.

- Do not claim an experiment is valid only because a script exits
  successfully.

Outputs should also be checked for:

- expected schema
- expected row counts where relevant
- null values
- unknown values
- non-applicable values
- duplicate records
- validation errors
- evidence consistency
- unexpected distribution changes

---

## Explicitly Out of Scope

Unless the authoritative research specification is explicitly
updated, the following are out of scope:

- Kubernetes
- Multi-cloud
- RAG
- MCP
- Multi-agent systems
- Runtime GPT/Gemini/Claude API
- Fine-tuning LLMs
- Autonomous remediation
- SIEM integration
- Attack graphs
- Complex web dashboards
- Production-grade cloud deployment platform

Generative AI is treated primarily as a source of Terraform
artifacts for the research dataset, not as a runtime component of
the proposed prioritization pipeline.

---

## Engineering Rules

- Prefer simple and reproducible implementations.

- Do not introduce unnecessary architectural complexity.

- Do not add new dependencies without justification.

- Do not perform unrelated refactoring while implementing a
  research task.

- Keep implementation changes scoped to the requested objective.

- Do not rewrite functioning research code only for stylistic
  preferences.

- Do not change the research protocol because model results are
  inconvenient.

- Do not modify ground truth after seeing model results.

- Do not introduce undocumented heuristics.

- Do not introduce hidden assumptions.

- Do not create silent fallback labels or silent fallback feature
  values.

- Do not fabricate missing evidence.

- Do not optimize implementation merely to make evaluation metrics
  appear better.

---

## Current Phase Boundary

The project is currently working on finding-level contextual
feature extraction and semantic validation.

Do not prematurely proceed to final ML training/evaluation until
the contextual feature dataset and its validation gates are
considered stable according to:

`docs/CURRENT_STATE.md`

The current implementation focus must be interpreted using:

- `docs/CURRENT_STATE.md`
- `docs/DECISIONS.md`
- the relevant finalized sections of `docs/THESIS_CONTEXT.md`

---

## Research Governance

The authoritative research specification is:

`docs/THESIS_CONTEXT.md`

Accepted research and implementation decisions are recorded in:

`docs/DECISIONS.md`

The current implementation checkpoint is recorded in:

`docs/CURRENT_STATE.md`

Repository-level agent behavior is governed by:

`AGENTS.md`

Use the following authority order:

1. `docs/THESIS_CONTEXT.md`
2. `docs/DECISIONS.md`
3. `docs/CURRENT_STATE.md`
4. `PROJECT_RULES.md`
5. Existing source code, outputs, comments, and historical documents

This file defines stable project constraints and engineering rules,
but it must not override approved methodology in
`docs/THESIS_CONTEXT.md`.

Existing code does not automatically define research methodology.

If this file, existing implementation, an older protocol,
experimental output, or historical documentation appears to
conflict with the authoritative research specification:

- do not silently choose an interpretation;
- do not change research semantics;
- report the conflict;
- wait for an explicit research decision when necessary.
