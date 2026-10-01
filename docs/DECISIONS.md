# Research and Implementation Decisions

This file records accepted decisions that affect implementation.

This file does not replace the full research specification in
`docs/THESIS_CONTEXT.md`.

---

## D-001 — Authoritative Research Specification

Status: Accepted

Decision:

`docs/THESIS_CONTEXT.md` is the primary source of truth for the
current research design and methodology.

Older research protocol documents remain historical/supporting
references.

If they conflict with THESIS_CONTEXT.md, the latter takes
precedence.

---

## D-002 — Research Design vs Existing Code

Status: Accepted

Decision:

Existing implementation does not automatically define the research
methodology.

If implementation conflicts with the approved research design,
the conflict must be reported.

The methodology must not be silently changed simply to preserve
existing code behavior.

---

## D-003 — Applicability Is Not Unknown

Status: Accepted

Decision:

A contextual feature that is not applicable to a finding/rule is
semantically different from an unknown feature value.

Non-applicable:
the feature does not belong to the semantics of that rule/finding.

Unknown:
the feature is applicable, but its value cannot be reliably
determined from available evidence.

These states must not be collapsed.

---

## D-004 — Context Evidence

Status: Accepted

Decision:

Contextual feature extraction should retain sufficient evidence to
trace important extracted values back to the Terraform source.

No fabricated evidence or silent default evidence is permitted.

---

## D-005 — Research Integrity

Status: Accepted

Implementation must not introduce undocumented heuristics simply
to improve downstream metrics.

In particular, avoid:

- target leakage
- data leakage
- silent fallback labels
- fabricated context
- evaluation contamination
- methodology changes made only to make tests pass

---

## D-006 — Current Phase Boundary

Status: Accepted

Do not advance to final ML training/evaluation until the
finding-level contextual feature dataset and semantic validation
are considered stable.

---

## D-007 — IAM Statement-Level Context Scope

Status: Accepted

Decision:

IAM contextual features defined at statement level must be derived
from the Checkov-relevant IAM policy statement, not from an
aggregation of unrelated statements in the surrounding policy.

A statement may be used when it can be identified deterministically
from approved evidence, such as a valid Checkov `evaluated_keys`
statement index combined with a successfully parsed corresponding
statement block.

If the Checkov-relevant statement cannot be identified reliably:

- do not aggregate all `Action` or `Resource` values from the policy
  as a substitute;
- do not infer a negative or positive value from unrelated
  statements;
- applicable statement-dependent contextual features must use
  `unknown`;
- non-applicable features remain `not_applicable` according to the
  applicability matrix.

This applies at minimum to statement-dependent IAM features such as:

- `wildcard_action`
- `wildcard_resource`
- `privilege_impact`

A parser failure caused only by supported Terraform/HCL syntax is an
implementation defect and should be fixed rather than treated as
research uncertainty.

This decision does NOT yet define or modify the exact mapping of
`privilege_impact` values `0`–`3`. That mapping remains a separate
research-semantic issue.

---

## D-008 — Privilege Impact Measures Potential IAM Capability

Status: Accepted

Decision:

`privilege_impact` is an ordinal contextual feature describing the
potential authorization capability granted by the Checkov-relevant
IAM policy statement.

It does NOT represent:

- final security risk;
- scanner severity;
- effective runtime authorization;
- human priority;
- resource exposure or resource breadth.

Resource breadth is represented separately by contextual features
such as `wildcard_resource`.

The approved values are:

### `0` — No granted privilege capability

Use `0` only when available evidence establishes that the relevant
statement does not grant an authorization capability.

A deterministically identified `Effect = "Deny"` statement is the
primary supported case.

### `1` — Read / observation capability

Use `1` for resolved actions whose capability is limited to reading,
listing, describing, querying, or otherwise observing resources
without modifying their state or authorization configuration.

### `2` — Operational mutation / resource-control capability

Use `2` for resolved non-privilege-administration actions capable of
creating, modifying, deleting, starting, stopping, updating, or
otherwise changing resource or service state.

Resource wildcard/scoping does not independently change this level.

### `3` — Privilege administration / delegation / unrestricted control

Use `3` when resolved actions establish direct capability to manage,
delegate, assume, alter, or escalate identity, role, policy,
permission, or equivalent authorization control.

Explicit unrestricted actions such as:

- `Action = "*"`
- `iam:*`

also belong to level `3`.

A non-IAM service wildcard such as `s3:*` is not automatically
level `3` solely because it contains `*`; it must be classified
according to the capability taxonomy unless the action represents
unrestricted cross-service or privilege-administration capability.

### `unknown`

Use `unknown` when `privilege_impact` is applicable but the available
static evidence is insufficient to determine the level reliably.

This includes, as applicable:

- unresolved statement selection;
- unresolved `Effect`;
- unresolved `Action`;
- partially resolved Action expressions where the unresolved portion
  could change the resulting level;
- actions not covered by the approved capability taxonomy.

Unknown or unresolved `Resource` scope does not by itself make
`privilege_impact` unknown because resource breadth is modeled
separately.

### `not_applicable`

Use `not_applicable` only when the applicability matrix establishes
that `privilege_impact` is not meaningful for the finding/rule.

## Multiple Actions

For a statement containing multiple fully resolved Actions:

- classify each Action independently;
- use the maximum resulting privilege level.

If one or more Actions are unresolved and could increase or otherwise
change the resulting level, return `unknown`.

If an already resolved Action establishes level `3`, additional
unresolved Actions cannot increase the ordinal level and do not
invalidate that level solely for this reason.

## Effect

`Effect = "Deny"` produces level `0` because the statement does not
grant the represented capability.

If `Effect` cannot be determined reliably, use `unknown`.

## Condition

`privilege_impact` measures potential capability rather than fully
evaluated effective authorization.

Therefore the presence of `Condition` does not automatically reduce
the privilege level.

The Condition must remain traceable in evidence when available.

This decision does not claim that the capability is exercisable in
every runtime context.

## Resource Scope

`privilege_impact` must not encode resource breadth.

The following must therefore not independently raise or lower the
privilege level:

- wildcard Resource;
- explicitly scoped Resource;
- unresolved Resource expression.

Resource breadth is represented by the appropriate resource-scope
context feature such as `wildcard_resource`.

## Research Integrity

The mapping must be derived only from objective IAM statement
evidence.

It must not be inferred from:

- human priority labels;
- final risk scores;
- model predictions;
- desired experimental results.

The Action capability taxonomy used to operationalize levels `1`,
`2`, and `3` must be explicit, deterministic, version-controlled,
and auditable.

Unknown Actions must not silently default to level `1`.
