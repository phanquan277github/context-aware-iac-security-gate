# Current Project State

Last updated: 2026-09-26

## Purpose

This document records the current implementation checkpoint of the
research project.

It is NOT the research methodology.

For methodology and research design, use:

`docs/THESIS_CONTEXT.md`

---

## Current Research Phase

Current work is focused on the dataset/context-feature preparation
stage before downstream machine-learning experiments.

The immediate implementation focus is finding-level contextual
feature extraction and semantic validation.

---

## Repository State Already Implemented

### Dataset preparation

The repository already contains:

- GenIaC-SecBench source data
- AI-generated candidate corpus
- GenIaC HCL candidates
- Tier-A corpus
- research-scope findings
- research-scope rules
- contrastive scenarios
- external candidates

### Context specification

Current context specification files:

- `dataset/main/context/context_schema.yaml`
- `dataset/main/context/feature_definitions.yaml`
- `dataset/main/context/rule_context_applicability.csv`

### Existing context-feature pilot

Existing pilot outputs:

- `results/context_feature_pilot/finding_context_features_pilot.csv`
- `results/context_feature_pilot/manual_review.csv`
- `results/context_feature_pilot/pilot_evidence_review.txt`
- `results/context_feature_pilot/pilot_findings.csv`

---

## Current Implementation Focus

Primary script:

`scripts/extract_finding_context_features.py`

Related validation scripts:

- `scripts/validate_context_schema.py`
- `scripts/validate_context_pilot_semantics.py`

Current concern:

Rule-specific applicability semantics must be enforced before
generic feature-value validation.

A feature that is not applicable to a finding/rule must not be
validated as if it were an applicable contextual observation.

---

## Current Processing Direction

Expected conceptual flow:

finding
→ determine rule applicability
→ load relevant Terraform source context
→ extract applicable contextual features
→ enforce applicability semantics
→ validate allowed feature values
→ validate supporting evidence
→ emit finding-level contextual feature record

---

## Current Boundary

Do NOT proceed to final ML model training yet.

The contextual feature dataset and its semantic validation must
first reach an accepted/stable state.

---

## Next Immediate Goal

Complete and verify the finding-context feature extraction pipeline.

Validation should establish at minimum:

- schema conformity
- allowed feature values
- correct applicability handling
- distinction between unknown and non-applicable
- evidence consistency
- absence of silent fallback values
- reproducible output

---

## Completed Checkpoint — General Context Feature Validator

Date: 2026-09-30

A general read-only validator has been implemented:

`scripts/validate_finding_context_features.py`

Regression/unit tests:

`scripts/test_validate_finding_context_features.py`

Validation result on the current context-feature pilot:

- records: 20
- unique finding IDs: 20
- finding features: 9
- feature cells: 180
- applicability rules: 10
- applicability Boolean cells: 90
- validation errors: 0
- validation warnings: 0
- evidence JSON parse failures: 0
- source reference failures: 0
- unit tests: 16 passed

The following validators currently pass:

- `scripts/validate_finding_context_features.py`
- `scripts/validate_context_schema.py`
- `scripts/validate_context_pilot_semantics.py`

The general validator establishes structural and consistency
guarantees only.

It does NOT yet establish semantic correctness of:

- exposure/reachability evidence
- network direction
- IAM statement selection/fallback
- wildcard-resource inference
- privilege-level inference
- per-feature minimum evidence requirements

Therefore the contextual-feature phase is NOT yet considered
research-accepted.

## Next Immediate Implementation Focus

Resolve implementation defects that do not require changing
research semantics, one at a time, while preserving the currently
passing validation baseline.

The next approved implementation issue is the inconsistent Boolean
parsing behavior identified in the contextual feature extractor.

Do NOT proceed to final ML training/evaluation.

