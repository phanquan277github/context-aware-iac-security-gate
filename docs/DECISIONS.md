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

---

## D-009 — Finding-Level Context Feature Evidence Contract

Status: Accepted

Decision:

Every contextual feature value used by the research dataset must be
supported by deterministic, auditable static evidence.

The approved evidence representation uses:

- one shared provenance object for the finding/source context; and
- one decision-basis object for each applicable contextual feature.

This avoids duplicating common provenance while preserving
feature-level traceability.

## Evidence States

A determined feature value requires evidence that identifies:

- the relevant object and analysis scope;
- source references or deterministic derived references;
- the extraction/inference method and version;
- observed facts;
- the conclusion derived from those facts.

Absence of positive evidence must NOT be treated as evidence for a
negative state.

Negative states such as `no` or `internal` require evidence that the
relevant analysis scope was examined sufficiently to support the
negative conclusion.

## Unknown

`unknown` represents research-relevant static uncertainty.

It may be used when:

- the feature is applicable;
- extraction/selection was successfully attempted;
- available static evidence is insufficient to determine the value;
- the reason for uncertainty is recorded.

Examples include:

- unresolved Terraform references;
- partially resolved expressions;
- incomplete static relationship/path resolution;
- supported constructs whose value cannot be determined statically.

Operational failures must NOT be converted into `unknown`.

Examples of operational failures include:

- missing required source artifact;
- parser failure on a construct that should be supported;
- extractor exception;
- corrupted evidence input.

Such cases are extraction/validation failures and must not be
accepted as valid contextual observations.

## Not Applicable

`not_applicable` is determined only by the approved applicability
contract.

It does not require fabricated Terraform/source evidence.

Evidence for `not_applicable` must identify at minimum:

- rule/check identifier;
- feature identifier;
- applicability-matrix provenance/version.

## Scanner Evidence

A Checkov `FAILED` result establishes the scanner finding and its
rule context.

A scanner failure alone is not sufficient evidence for a contextual
feature value when that feature claims a property of the Terraform
configuration or infrastructure context.

Scanner evidence must be combined with deterministic source/config
evidence appropriate to the feature.

## Source Scope

Evidence may use:

- explicit Terraform configuration;
- deterministic references between resources within the candidate
  artifact;
- Checkov finding metadata and evaluated keys;
- approved versioned taxonomies or deterministic mappings.

Evidence v1 must not silently materialize provider/runtime defaults
as if they were explicit Terraform literals.

If a provider default is later used as research evidence, that
behavior requires explicit versioned documentation.

## Network Evidence

Network-related conclusions must preserve direction and the
deterministic relationship/path used to support the value.

For positive exposure/reachability conclusions, evidence must record
the explicit configuration and relevant path elements.

For negative/internal conclusions, the relevant static scope must be
sufficiently resolved to support the absence of the exposure/path.

If required network relationships cannot be resolved statically,
the applicable feature must be `unknown`.

Literal network facts that do not appear in explicit or otherwise
approved evidence must not be fabricated.

## IAM Evidence

IAM evidence must conform to D-007 and D-008.

For statement-dependent IAM features, evidence must preserve as
applicable:

- statement-selection provenance;
- evaluated-keys relationship;
- selected statement index;
- source location;
- Effect;
- raw and resolved Actions;
- unresolved Action expressions;
- raw and resolved Resources;
- unresolved Resource expressions;
- wildcard match evidence;
- IAM Action capability taxonomy version;
- Action-to-capability classification;
- Condition when present.

For `privilege_impact`, evidence must make the D-008 classification
reproducible.

## Resource Role

`resource_role` must be derived through an explicit,
version-controlled `resource_type -> resource_role` taxonomy.

A recognized resource type not assigned to a specialized role may
use the approved `other` category.

A missing or unreadable resource type is not equivalent to `other`;
it is an extraction/data-quality failure.

The exact resource-role taxonomy must be audited and versioned
before final feature-dataset acceptance.

## Encryption and Logging

For scanner-aligned control features such as
`encryption_missing` and `logging_missing`, evidence must preserve:

- scanner rule/check provenance; and
- deterministic source/config evidence supporting whether the
  specific control required by that rule is present or absent.

For controls represented by relationships or separate Terraform
resources, the relevant candidate scope must be checked rather than
using absence from a short source snippet as proof.

## Evidence Versioning

Evidence must carry a versioned evidence contract or equivalent
stable identifier.

Versioned supporting artifacts such as:

- applicability matrix;
- IAM Action taxonomy;
- resource-role taxonomy;

must be identifiable through version or reproducible content hash.

## Research Integrity

Evidence must not be derived from:

- human priority labels;
- target values;
- model predictions;
- desired experiment results.

Evidence validation and feature extraction must remain independent
of downstream ranking performance.

---

## D-010 — Versioned Resource Role Taxonomy

Status: Accepted

Decision:

`resource_role` represents the functional security domain of the
Terraform object type.

It is a type-level contextual feature.

It does NOT attempt to infer:

- the actual business purpose of an individual resource;
- data sensitivity;
- workload criticality;
- resource importance;
- runtime usage from resource names or naming conventions.

The approved roles are:

### `identity`

Terraform objects whose primary security function concerns identity,
authorization, trust, IAM policy, role, or permission semantics.

### `primary_data`

Persistent data/storage resources and Terraform objects that directly
configure storage, access, ownership, or lifecycle controls for those
data resources.

The label does not assert that the resource contains the most
important business data.

### `logging`

Terraform objects whose primary function is audit, log, or telemetry
collection/storage.

General security detection services are not automatically classified
as logging.

### `network`

Terraform objects whose primary function concerns connectivity,
routing, addressing, ingress/egress, edge exposure, traffic
distribution, filtering, or network security controls.

### `compute`

Terraform objects whose primary function concerns workload execution,
compute capacity, compute deployment configuration, or workload
orchestration.

### `other`

A recognized Terraform object type that has been explicitly reviewed
and does not belong to the five specialized roles above.

`other` is an explicit taxonomy decision, not a fallback.

## Mapping Rules

The taxonomy must use explicit, version-controlled
`resource_type -> resource_role` entries.

Prefix inference such as:

`aws_iam_* -> identity`

is not sufficient for the accepted taxonomy.

Configuration or attachment objects may be assigned to the security
domain they directly govern, but each such mapping must be explicit
in the taxonomy.

Dynamic role inheritance from another Terraform resource is not part
of taxonomy v1.

## Missing and Unmapped Types

An empty, missing, or unreadable `resource_type` must not be mapped
to `other`.

A non-empty resource type absent from the approved taxonomy must also
not silently fall back to `other`.

For an in-scope research finding, either case is a data-quality /
extraction failure requiring review.

Research-scope filtering occurs before contextual-feature extraction.
A finding outside the approved research rule scope does not require
a `resource_role` observation merely because it exists in the raw
scanner corpus.

## Approved v1 Mappings

### identity

- aws_iam_policy
- aws_iam_role_policy
- aws_iam_role_policy_attachment
- aws_iam_policy_document

### primary_data

- aws_s3_bucket
- aws_db_instance
- aws_rds_cluster
- aws_rds_cluster_instance
- aws_rds_global_cluster
- aws_dynamodb_table
- aws_elasticache_replication_group
- aws_secretsmanager_secret
- aws_ssm_parameter
- aws_s3_bucket_lifecycle_configuration
- aws_s3_bucket_ownership_controls
- aws_s3_bucket_policy
- aws_s3_bucket_public_access_block

### logging

- aws_cloudwatch_log_group
- aws_cloudtrail
- aws_flow_log

### network

- aws_vpc
- aws_subnet
- aws_security_group
- aws_security_group_rule
- aws_vpc_security_group_ingress_rule
- aws_vpc_security_group_egress_rule
- aws_lb
- aws_lb_listener
- aws_lb_target_group
- aws_network_acl
- aws_network_acl_rule
- aws_networkfirewall_firewall
- aws_networkfirewall_firewall_policy
- aws_networkfirewall_rule_group
- aws_eip
- aws_route53_zone
- aws_cloudfront_distribution
- aws_wafv2_web_acl
- aws_api_gateway_method
- aws_api_gateway_method_settings
- aws_api_gateway_rest_api
- aws_api_gateway_stage
- aws_apigatewayv2_route
- aws_apigatewayv2_stage

### compute

- aws_instance
- aws_lambda_function
- aws_eks_cluster
- aws_autoscaling_group
- aws_launch_configuration
- aws_launch_template
- aws_glue_crawler
- aws_glue_job
- aws_sfn_state_machine

### other

- aws_dlm_lifecycle_policy
- aws_guardduty_detector
- aws_kinesis_firehose_delivery_stream
- aws_kms_key
- aws_sns_topic

## Versioning

The operational taxonomy must be stored in a version-controlled
artifact with a stable version identifier.

Evidence for `resource_role` must preserve at minimum:

- input `resource_type`;
- resulting `resource_role`;
- taxonomy version or reproducible content hash;
- mapping entry used.

The taxonomy must be frozen before the final contextual-feature
dataset is frozen.

---

## D-011 — Network Context Semantics and Unknown Reason Codes

Status: Accepted

Decision:

Network contextual features represent deterministic static properties
of the Terraform/network object directly associated with the finding.

They do not require proof that a production workload is currently
using the configured network path unless the feature itself requires
such an attachment to establish its value.

## Reachability

`reachability` represents the statically configured network
reachability scope of the relevant resource or network control.

`reachability=internet` may be concluded when explicit Terraform
configuration establishes an Internet-directed path or destination
for the relevant network object.

Examples include:

- a subnet deterministically associated with a route table containing
  a default route to an Internet Gateway;
- an applicable egress security-group rule whose destination is an
  Internet-wide CIDR such as `0.0.0.0/0`.

For a security-group rule, this classification describes the
configured reachability scope of the rule. It does not assert that a
specific runtime workload is currently attached to that security
group.

`reachability=internal` requires static evidence that the relevant
network scope is limited to internal/private destinations.

If the route, destination, association, or other relationship
required to determine the configured scope cannot be resolved
statically, the value is `unknown`.

## Internet Exposure

`internet_exposure` represents direct inbound exposure from the
Internet.

An Internet route, public subnet, public-IP assignment capability,
or outbound rule alone does not prove `internet_exposure=yes`.

A positive value requires deterministic evidence of the inbound
exposure semantics relevant to the affected resource, such as:

- an Internet-facing endpoint; or
- an inbound network control/path explicitly permitting Internet
  origin traffic.

If the static evidence establishes Internet routing capability but
does not establish the required inbound relationship,
`internet_exposure` remains `unknown` when applicable.

## Public Access

`public_access` represents whether the affected resource is
statically demonstrated to be publicly accessible.

Missing a preventive security control alone is not evidence that a
resource is public.

For S3-related public-access findings, a missing Public Access Block
does not by itself establish public access.

The analysis must record candidate-specific evidence concerning the
relevant explicit controls available in the Terraform candidate,
including as applicable:

- Public Access Block;
- bucket policy;
- ACL or equivalent explicit access configuration.

Provider/runtime defaults must not be silently materialized as
Terraform evidence.

If the explicit static configuration does not establish either
public or non-public access, the value is `unknown`.

## CKV_AWS_130 Subnet Semantics

For a subnet finding:

- deterministic route-table association plus a default route to an
  Internet Gateway is sufficient evidence for
  `reachability=internet`;

- `map_public_ip_on_launch=true` records public-IP assignment
  capability but does not alone establish
  `internet_exposure=yes` or `public_access=yes`;

- without sufficient endpoint/workload/inbound-access evidence,
  applicable `internet_exposure` and `public_access` remain
  `unknown`.

Therefore subnet reachability and workload/public exposure must not
be collapsed into the same concept.

## CKV_AWS_382 Egress Semantics

For an applicable egress-rule finding, an explicit egress
destination of `0.0.0.0/0` or equivalent Internet-wide destination
is sufficient to establish configured
`reachability=internet`.

This does not assert runtime workload attachment and does not imply
inbound Internet exposure.

## Approved Unknown Reason Codes

Evidence v1 must use a deterministic reason code when an applicable
feature is `unknown`.

Approved D-009 v1 reason codes are:

- `unresolved_reference`
- `partially_resolved_expression`
- `insufficient_static_relationship`
- `insufficient_static_path`
- `insufficient_access_control_evidence`
- `unresolved_statement`
- `unresolved_effect`
- `unresolved_action`
- `unresolved_resource`
- `unclassified_action`
- `unsupported_static_construct`

A human-readable reason detail may accompany the code.

These reason codes describe research-relevant static uncertainty.

Operational failures such as missing required source files, parser
defects on supported syntax, extractor exceptions, corrupted inputs,
or invalid taxonomy/configuration must not be represented using these
codes and must not be converted into research `unknown`.

## Evidence Requirements

Evidence for network features must distinguish:

- facts that were successfully resolved;
- relationships or path elements that remain unresolved;
- the final feature conclusion.

An `unknown` explanation must not claim that a path element is
missing when that element was actually found and resolved.

This decision does not change the applicability matrix.
