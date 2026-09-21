# Severity Mapping

## Purpose

This document defines the severity policy used by the
Severity-only baseline.

The assigned severity represents the intrinsic security
severity of the finding and does not depend on deployment context.

## Severity Scale

| Severity | Numeric |
|---|---:|
| LOW | 1 |
| MEDIUM | 2 |
| HIGH | 3 |
| CRITICAL | 4 |

## Severity Principles

### CRITICAL

A finding is classified as CRITICAL when its check semantics
directly indicate severe privilege-escalation risk,
full administrative IAM privileges, full IAM privileges,
or unrestricted administrative remote access.

### HIGH

A finding is classified as HIGH when its check semantics
indicate direct public exposure or broad IAM permission scope.

### MEDIUM

A finding is classified as MEDIUM when the violated control
represents an important defense-in-depth security control,
such as encryption or logging.

### LOW

No currently in-scope Pilot finding is assigned LOW.

## Context Independence

Severity assignment must not use:

- environment
- asset_criticality
- data_sensitivity
- internet_exposure
- reachability
- model predictions
- ground-truth ranking

Context-aware prioritization is evaluated separately.

## Scope Rule

Only Checkov findings belonging to the eight predefined
security categories are included in the Severity-only baseline.

Other raw Checkov findings remain in the raw dataset but are
excluded from the main prioritization experiment.

## Pilot Check Mapping

| Check ID | Category | Severity | Numeric | Basis |
|---|---|---|---:|---|
| CKV_AWS_24 | CAT-06; CAT-07 | CRITICAL | 4 | Unrestricted administrative remote access through SSH ingress |
| CKV_AWS_286 | CAT-03 | CRITICAL | 4 | Direct privilege-escalation risk |
| CKV2_AWS_40 | CAT-03 | CRITICAL | 4 | Full IAM privileges |
| CKV_AWS_62 | CAT-03 | CRITICAL | 4 | Full administrative IAM privileges |
| CKV_AWS_20 | CAT-04 | HIGH | 3 | Direct public S3 exposure |
| CKV_AWS_17 | CAT-05 | HIGH | 3 | Direct public RDS exposure |
| CKV_AWS_63 | CAT-01 | HIGH | 3 | IAM wildcard action scope |
| CKV_AWS_355 | CAT-02 | HIGH | 3 | IAM wildcard resource scope |
| CKV_AWS_289 | CAT-03 | HIGH | 3 | Permissions-management/resource-exposure without constraints |
| CKV_AWS_16 | CAT-08 | MEDIUM | 2 | Missing RDS encryption control |
| CKV_AWS_18 | CAT-08 | MEDIUM | 2 | Missing S3 access logging control |
| CKV_AWS_129 | CAT-08 | MEDIUM | 2 | Missing RDS logging control |
| CKV_AWS_145 | CAT-08 | MEDIUM | 2 | Missing S3 KMS encryption control |

## Baseline Use

The Severity-only baseline uses only:

- severity_numeric

It does not use business context,
ground-truth ranking, or model predictions.

## Freeze Rule

This mapping is frozen before Main Experiment evaluation.

Any newly encountered in-scope Checkov ID must be assigned
according to the frozen severity principles before being used
in the baseline.

The assignment must be documented explicitly and must not
depend on observed model performance.
