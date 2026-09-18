# Pilot Observations

## SCN-001

### Terraform
- validation: PASS

### Infrastructure Facts
- internet_exposure: high
- privilege_impact: high
- reachability: internet

### Evidence
- S3 ACL allows public-read.
- Security group permits 0.0.0.0/0 to port 22.
- IAM policy allows Action = "*" and Resource = "*".

### Checkov
- finding_count:
- categories:
- severities:

## SCN-002

### Terraform
- validation: PASS

### Infrastructure Facts
- internet_exposure: high
- privilege_impact: high
- reachability: internet

### Evidence
- Same Terraform configuration as SCN-001.

### Checkov
- finding_count:
- categories:
- severities:

## SCN-003 / SCN-004 — RDS Context Pair

Terraform configuration:

- AWS RDS MySQL instance
- RDS is publicly accessible
- Security group allows TCP/3306 from `0.0.0.0/0`
- Storage encryption is disabled
- Both scenarios use equivalent Terraform infrastructure configuration
- Context metadata is the intended difference between the pair

### SCN-003

Business context:
- environment: prod
- asset_criticality: critical
- data_sensitivity: sensitive

Objective infrastructure facts:
- internet_exposure: high
- privilege_impact: low
- reachability: internet

Evidence:
- `publicly_accessible = true`
- security group ingress `0.0.0.0/0`
- TCP port `3306`

### SCN-004

Business context:
- environment: dev
- asset_criticality: low
- data_sensitivity: internal

Objective infrastructure facts:
- internet_exposure: high
- privilege_impact: low
- reachability: internet

Evidence:
- `publicly_accessible = true`
- security group ingress `0.0.0.0/0`
- TCP port `3306`

## Checkov Results — SCN-003 / SCN-004

SCN-003:
- failed_checks: 11
- passed_checks: 11
- skipped_checks: 0
- parsing_errors: 0

SCN-004:
- failed_checks: 11
- passed_checks: 11
- skipped_checks: 0
- parsing_errors: 0

The two scenarios produced the same set of Checkov check IDs.
This supports their use as a contrastive pair in which Terraform
infrastructure facts are held constant while business context differs.

Relevant target findings observed include:
- CKV_AWS_17 — public RDS
- CKV_AWS_16 — RDS encryption disabled

Additional RDS findings are retained in the raw scanner output and
normalized dataset. Their inclusion in the main experimental finding
set will be determined by the predefined scope/category mapping.

## SCN-005 / SCN-006 — IAM Privilege-Escalation Context Pair

Terraform configuration:

- An IAM user is defined as the target principal.
- An inline IAM user policy is attached directly to the user.
- The policy grants `iam:AttachUserPolicy`.
- The policy uses `Resource = "*"`.

### SCN-005

Business context:

- environment: dev
- asset_criticality: low
- data_sensitivity: internal

Objective infrastructure facts:

- internet_exposure: none
- privilege_impact: high
- reachability: internal

Observed Checkov findings:

- `CKV_AWS_273` — IAM user access / SSO control
- `CKV_AWS_40` — IAM policy attachment to user
- `CKV_AWS_355` — wildcard resource for restrictable actions
- `CKV_AWS_289` — permissions management / resource exposure without constraints
- `CKV_AWS_286` — privilege escalation

Primary pilot category:

- privilege escalation / excessive privilege

Primary evidence:

- `aws_iam_user_policy`
- `iam:AttachUserPolicy`
- `Resource = "*"`

### SCN-006

Business context:

- environment: prod
- asset_criticality: critical
- data_sensitivity: sensitive

Objective infrastructure facts:

- internet_exposure: none
- privilege_impact: high
- reachability: internal

Observed Checkov findings:

- `CKV_AWS_273` — IAM user access / SSO control
- `CKV_AWS_40` — IAM policy attachment to user
- `CKV_AWS_355` — wildcard resource for restrictable actions
- `CKV_AWS_289` — permissions management / resource exposure without constraints
- `CKV_AWS_286` — privilege escalation

Primary pilot category:

- privilege escalation / excessive privilege

Primary evidence:

- `aws_iam_user_policy`
- `iam:AttachUserPolicy`
- `Resource = "*"`

### Pilot observation

The IAM privilege-escalation pattern was not detected when tested using
standalone IAM policy resources or narrowly scoped policy resources.
An inline IAM user policy with `iam:AttachUserPolicy` and
`Resource = "*"` produced `CKV_AWS_286` in Checkov 3.3.17.

This demonstrates that observed scanner coverage depends on the
specific IAM resource representation and policy scope.

## SCN-007 / SCN-008 — Network Exposure Context Pair

Terraform configuration:

- An AWS security group is defined.
- TCP port 22 is exposed through an ingress rule.
- The ingress source is `0.0.0.0/0`.
- SCN-007 and SCN-008 use equivalent Terraform infrastructure.
- Business context differs between the two scenarios.

### SCN-007

Business context:

- environment: staging
- asset_criticality: medium
- data_sensitivity: internal

Objective infrastructure facts:

- internet_exposure: high
- privilege_impact: high
- reachability: internet

Evidence:

- `aws_security_group.admin_007`
- TCP port 22
- `cidr_blocks = ["0.0.0.0/0"]`

Observed Checkov findings:

- `CKV_AWS_23` — security group/rule description
- `CKV_AWS_24` — unrestricted ingress to port 22
- `CKV2_AWS_5` — security group is not attached to another resource

Primary pilot category:

- open administrative port / network exposure

Primary evidence:

- `CKV_AWS_24`
- TCP port 22
- `0.0.0.0/0`

### SCN-008

Business context:

- environment: prod
- asset_criticality: high
- data_sensitivity: sensitive

Objective infrastructure facts:

- internet_exposure: high
- privilege_impact: high
- reachability: internet

Evidence:

- `aws_security_group.admin_008`
- TCP port 22
- `cidr_blocks = ["0.0.0.0/0"]`

Observed Checkov findings:

- `CKV_AWS_23` — security group/rule description
- `CKV_AWS_24` — unrestricted ingress to port 22
- `CKV2_AWS_5` — security group is not attached to another resource

Primary pilot category:

- open administrative port / network exposure

Primary evidence:

- `CKV_AWS_24`
- TCP port 22
- `0.0.0.0/0`

### Pilot observation

Checkov 3.3.17 identified the unrestricted SSH ingress pattern
through `CKV_AWS_24` in both scenarios.

The same Terraform configuration generated the same set of
Checkov findings in SCN-007 and SCN-008, while the business
context metadata differed between the two scenarios.

## SCN-009 / SCN-010 — Mixed Security Context Pair

Terraform configuration:

- An S3 bucket is configured with public access controls disabled.
- An S3 bucket policy allows public `s3:GetObject` access.
- An IAM user is defined as the target principal.
- An inline IAM user policy grants `iam:AttachUserPolicy`.
- The IAM policy uses `Resource = "*"`.
- An AWS security group allows inbound TCP port 22 from `0.0.0.0/0`.
- SCN-009 and SCN-010 use equivalent Terraform infrastructure.
- Business context differs between the two scenarios.

### SCN-009

Business context:

- environment: dev
- asset_criticality: medium
- data_sensitivity: internal

Objective infrastructure facts:

- internet_exposure: high
- privilege_impact: high
- reachability: internet

Primary security patterns:

- public S3 access
- IAM privilege escalation
- open administrative port

Evidence:

- S3 bucket policy with `Principal = "*"`
- `s3:GetObject`
- `iam:AttachUserPolicy`
- IAM `Resource = "*"`
- TCP port 22
- `cidr_blocks = ["0.0.0.0/0"]`

### SCN-010

Business context:

- environment: prod
- asset_criticality: critical
- data_sensitivity: sensitive

Objective infrastructure facts:

- internet_exposure: high
- privilege_impact: high
- reachability: internet

Primary security patterns:

- public S3 access
- IAM privilege escalation
- open administrative port

Evidence:

- S3 bucket policy with `Principal = "*"`
- `s3:GetObject`
- `iam:AttachUserPolicy`
- IAM `Resource = "*"`
- TCP port 22
- `cidr_blocks = ["0.0.0.0/0"]`
