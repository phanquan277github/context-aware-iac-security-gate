# Current Project State

Last updated: 2026-09-30

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
- unit tests: 23 PASS
- validation errors: 0
- validation warnings: 0
- pilot replay mismatches: 0

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

1. IAM statement fallback behavior.
2. Unresolved IAM resource references.
3. Wildcard-resource inference for unresolved values.
4. Exact privilege-level semantics.
5. Semantic correctness of evidence content.
6. Minimum evidence requirements per contextual feature.
7. Final main-pipeline applicability coverage.
8. Final feature-dataset acceptance criteria.

These issues must not be silently resolved by implementation code.

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

Establish a reproducible Git repository baseline by classifying
currently untracked artifacts into:

- source/configuration that must be tracked;
- reproducibility artifacts that should be tracked;
- generated outputs;
- external/large datasets;
- local/runtime artifacts.

Do NOT use `git add .` until this classification is complete.

---

## Next Research Implementation Task

After the repository baseline is established, continue resolving
context-feature semantic/implementation issues one at a time.

The next candidate issue is:

**unresolved IAM resource references must not become false negative
observations such as `wildcard_resource=no` when the actual value
cannot be determined.**

This must be checked against the approved `unknown` semantics before
implementation.

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
