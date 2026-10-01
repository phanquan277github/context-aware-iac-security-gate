# Current Project State

Last updated: 2026-10-01

## Purpose

This document is a concise snapshot of the CURRENT implementation
state of the research project.

It is NOT:

- the full research methodology;
- a chronological implementation log;
- a replacement for Git history.

For authoritative research design and methodology, use:

`docs/THESIS_CONTEXT.md`

For accepted research and implementation decisions, use:

`docs/DECISIONS.md`

---

## Current Research Phase

The project is currently in the:

**finding-level contextual feature extraction and semantic
validation phase**

before downstream Machine Learning experiments.

Final ML training/evaluation must NOT start until this phase is
considered stable and research-accepted.

---

## Current Research Pipeline Position

Current conceptual flow:

Terraform / finding
→ determine rule applicability
→ load relevant source context
→ extract applicable contextual features
→ enforce applicability semantics
→ validate feature values
→ validate evidence/consistency
→ emit finding-level contextual feature record

Current work is focused on the context-feature extraction and
validation stages.

---

## Current Core Artifacts

### Context specification

- `dataset/main/context/context_schema.yaml`
- `dataset/main/context/feature_definitions.yaml`
- `dataset/main/context/rule_context_applicability.csv`

### Extractor

- `scripts/extract_finding_context_features.py`

### Validators

- `scripts/validate_finding_context_features.py`
- `scripts/validate_context_schema.py`
- `scripts/validate_context_pilot_semantics.py`

### Tests

- `scripts/test_validate_finding_context_features.py`
- `scripts/test_extract_finding_context_features_bool.py`

### Current pilot outputs

- `results/context_feature_pilot/finding_context_features_pilot.csv`
- `results/context_feature_pilot/pilot_findings.csv`
- `results/context_feature_pilot/manual_review.csv`
- `results/context_feature_pilot/pilot_evidence_review.txt`

---

## Current Stable Validation Baseline

The current pilot contains:

- 20 finding records
- 9 contextual features
- 180 feature cells
- 10 applicability rules
- 90 applicability Boolean cells

Current validated feature-state distribution:

- applicable feature cells: 56
- `not_applicable`: 124
- `unknown`: 8

Current validation status:

- general context-feature validator: PASS
- context schema validator: PASS
- pilot semantic validator: PASS
- unit tests: 58 PASS
- validation errors: 0
- validation warnings: 0
- pilot replay feature-value mismatches: 0

The D-008 replay changes only `feature_evidence` in the four IAM
pilot records by adding Effect, Action taxonomy, and Condition
traceability. The saved pilot output has not been regenerated.

The latest Boolean applicability parsing fix did NOT change any
stored pilot feature values or applicability results.

---

## Accepted Semantics Already Enforced

The implementation currently preserves:

- rule-specific applicability;
- `unknown` and `not_applicable` as distinct states;
- rejection of invalid Boolean applicability values;
- allowed feature-value validation;
- unknown-counter consistency;
- parseable evidence JSON;
- finding/source reference consistency;
- deterministic pilot replay.

Invalid applicability tokens must not be silently converted to
False / non-applicable.

---

## Known Unresolved Semantic Issues

The following issues remain unresolved and must be handled
separately:

1. Semantic correctness of evidence content.
2. Minimum evidence requirements per contextual feature.
3. Final main-pipeline applicability coverage.
4. Final feature-dataset acceptance criteria.

The `privilege_impact` contract is now accepted in D-008 and the
normative thesis clarification. The extractor uses the versioned
`d008-v1` exact-action taxonomy; unclassified Actions remain
`unknown` unless another resolved Action already establishes level 3.

IAM statement-level context now follows D-007:

- features are derived from the Checkov-relevant IAM statement;
- supported HCL statement syntax is parsed deterministically;
- whole-policy aggregation is not used as a fallback;
- unresolved applicable statement-level features use `unknown`;
- non-applicable features remain `not_applicable`.

The current IAM corpus audit resolves all 39 CKV_AWS_290/355
findings to a deterministic statement block.

These remaining issues must not be silently resolved by
implementation code.
---

## Current Limitations

The current passing validators establish structural and consistency
guarantees.

They do NOT yet prove that every contextual feature is semantically
correct from a security/research perspective.

In particular, a successfully parsed evidence JSON object does not
prove that the evidence correctly establishes:

- exposure;
- reachability;
- network direction;
- IAM privilege;
- wildcard scope;
- business/security meaning.

Therefore:

**the contextual-feature phase is NOT yet research-accepted.**

---

## Immediate Operational Task

The repository reproducibility/provenance baseline for the current
context-feature phase has been established.

The repository now preserves:

- authoritative research/context configuration;
- current extractor, validators, and tests;
- pilot inputs and reproducibility fixtures;
- GenIaC source URL and exact source revision;
- SHA-256 source-artifact verification;
- candidate-specific Terraform provider provenance;
- candidate Terraform lockfiles required for provider reproducibility;
- Checkov version, scan command, normalized outputs, and raw-output
  checksums.

Known provenance limitations remain documented:

- the immutable external archive location of historical raw Checkov
  JSON is unresolved;
- independent upstream license verification for every original seed
  remains unresolved.

These limitations do not currently change research semantics or
block contextual-feature semantic validation.
---

## D-008 Output Checkpoint

The saved pilot feature values remain unchanged; its IAM evidence
still reflects the pre-D-008 extractor until an explicitly approved
regeneration. An in-memory audit of 39 CKV_AWS_290/355 findings
found two `1` to `2` changes for `rds:PromoteReadReplica` and two
`2` to `unknown` changes involving unclassified `ec2:TagResource`.

No corpus feature output or annotation was regenerated in this task.
---

## Phase Exit Criteria

This phase can progress toward main-pipeline/ML work only when:

- context schema is stable;
- feature definitions are stable;
- applicability semantics are stable;
- pilot structural validation passes;
- pilot semantic validation passes;
- evidence behavior is sufficiently defined;
- known silent fallback behaviors are resolved;
- required main-scope rules have defined applicability;
- feature outputs are reproducible;
- the feature dataset is explicitly accepted as stable.

Until then:

**Do NOT proceed to final ML training/evaluation.**
