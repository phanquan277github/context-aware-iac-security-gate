# Checkov JSON Schema — Pilot Freeze

## 1. Tool Information

- Tool: Checkov
- Version: 3.3.17
- IaC type: Terraform
- Output format: JSON
- Primary scan source: `results.failed_checks`

## 2. Observed Top-Level Structure

Observed from:

`dataset/pilot/checkov/SCN-001.json`

Top-level keys:

- `check_type`
- `results`
- `summary`
- `url`

Expected value types:

- `check_type`: string
- `results`: object
- `summary`: object
- `url`: string or null

## 3. Observed Results Structure

`results` contains:

- `passed_checks`
- `failed_checks`
- `skipped_checks`
- `parsing_errors`

For SCN-001:

- `failed_checks`: 20
- `passed_checks`: 9
- `skipped_checks`: 0
- `parsing_errors`: 0

## 4. Primary Finding Record

Each element of `results.failed_checks` is an object.

Observed fields include:

- `check_id`
- `bc_check_id`
- `check_name`
- `check_result`
- `code_block`
- `file_path`
- `file_abs_path`
- `repo_file_path`
- `file_line_range`
- `resource`
- `evaluations`
- `check_class`
- `fixed_definition`
- `entity_tags`
- `caller_file_path`
- `caller_file_line_range`
- `resource_address`
- `severity`
- `bc_category`
- `benchmarks`
- `description`
- `short_description`
- `vulnerability_details`
- `connected_node`
- `guideline`
- `details`
- `check_len`
- `definition_context_file_path`

## 5. Fields Selected for Normalization

The normalization layer will initially preserve:

- `check_id`
- `bc_check_id`
- `check_name`
- `resource`
- `repo_file_path`
- `file_line_range`
- `severity`
- `guideline`
- `check_result.result`
- `check_result.evaluated_keys`

These are treated as scanner-originated attributes.

## 6. Severity Handling

The Checkov JSON observed in the pilot contains:

`severity = null`

for the observed failed checks.

Therefore, the raw Checkov `severity` field is NOT assumed to provide the
severity-only baseline for the thesis.

A separate deterministic severity mapping must be defined and documented
before the main experiment.

The mapping must not be inferred from machine-learning model output.

## 7. Finding Scope

The raw Checkov result is retained without modification.

The research dataset will later distinguish:

1. Raw Checkov findings
2. Findings selected as in-scope for the thesis
3. Normalized findings used by feature extraction and prioritization

The eight target security categories are:

1. IAM wildcard action
2. IAM wildcard resource
3. Excessive privilege
4. Public S3
5. Public RDS
6. Security Group 0.0.0.0/0
7. Open administrative port
8. Missing encryption/logging

Additional Checkov findings may be retained as raw scanner output but excluded
from the main experimental finding set when they are outside the defined scope.

## 8. Finding Identity

For the pilot, one ML observation corresponds to one failed Checkov check
associated with one Terraform resource.

A finding is therefore identified using at least:

- `check_id`
- `resource`
- `repo_file_path`
- `file_line_range`

The pilot will assess whether multiple Checkov checks referring to the same
underlying misconfiguration create problematic duplication for manual ranking.

## 9. Research Reproducibility

The parser must consume the observed Checkov JSON structure rather than
depending on terminal formatting or human-readable CLI output.

The raw JSON files are retained unchanged as experimental evidence.

The schema may only be revised if a later pilot scenario demonstrates a
previously unobserved structural variation. Any revision must be documented
with the affected scenario and reason.
