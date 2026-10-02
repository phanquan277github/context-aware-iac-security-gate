# Current Project State

Last updated: 2026-10-03

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

The project is validating finding-level contextual features before
main-dataset experiments. The 20-finding context-feature pilot and its
Evidence v1 output are research-accepted for the pilot scope.
The main contextual-feature dataset has not been accepted.

---

## Current Pipeline and Artifacts

Current flow: approved research-scope finding and Terraform source
→ rule applicability → contextual-feature extraction → evidence
construction → structural and semantic validation.

Core specification and implementation:

- dataset/main/context/context_schema.yaml
- dataset/main/context/feature_definitions.yaml
- dataset/main/context/rule_context_applicability.csv
- dataset/main/context/feature_evidence_contract.yaml
- dataset/main/context/iam_action_capability_taxonomy.yaml
- dataset/main/context/resource_role_taxonomy.yaml
- scripts/extract_finding_context_features.py
- scripts/validate_finding_context_features.py
- scripts/validate_context_evidence.py
- scripts/validate_context_schema.py
- scripts/validate_context_pilot_semantics.py

The saved output is
results/context_feature_pilot/finding_context_features_pilot.csv,
from results/context_feature_pilot/pilot_findings.csv. Its
feature_evidence is Evidence v1 (d009-v1), not legacy evidence.

---

## Accepted Pilot Checkpoint

- Findings: 20
- Contextual features: 9
- Feature cells: 180
- Applicable cells: 56
- not_applicable cells: 124
- unknown cells: 6
- AUTOMATED_VERIFIED: 23
- MANUAL_VERIFIED: 33
- INSUFFICIENT_EVIDENCE: 0
- SEMANTIC_CONFLICT: 0
- EXTRACTION_FAILURE: 0

The general context-feature validator, Evidence v1 validator, context
schema validator, and pilot semantic validator all PASS. The full
regression suite passes 95/95 tests.

Saved pilot SHA-256:
7c88f02ad28648e8ff434ebc5cfe59f35be67781cbca8d53225076e332278cc8

The pilot context-feature phase is research-accepted for its pilot
scope. Pilot acceptance does not imply FINAL_MAIN_DATASET_ACCEPTED.
Do not revise the saved pilot unless main expansion reveals a real
semantic or implementation defect.

---

## Research Semantics and Scope

Approved applicability keeps unknown distinct from not_applicable.
IAM statement selection follows D-007; potential IAM capability
follows D-008; Evidence v1 follows D-009; resource roles use the
explicit D-010 d010-v1 taxonomy; network conclusions and unknown
reason codes follow D-011. The authoritative definitions remain in
docs/THESIS_CONTEXT.md and accepted decisions in docs/DECISIONS.md.

The current contextual-feature pipeline is limited to approved
research-scope rules. The nine raw CKV_TF_1 findings with empty
resource_type remain in the raw corpus but are outside that scope.
Pilot results must not be treated as main-dataset coverage or
acceptance evidence.

---

## Next Research Implementation Task

Extend the accepted pipeline to the approved research-scope main
finding set. Then perform coverage validation, semantic-evidence
validation, and explicit main-dataset acceptance.

Do not train or evaluate ML until the main contextual-feature dataset
is accepted. The external archive location of historical raw Checkov
JSON and independent upstream license verification remain documented
provenance limitations; they do not change the pilot acceptance above.
