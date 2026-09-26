from pathlib import Path
import pandas as pd


CATALOG = Path(
    "dataset/main/findings/"
    "geniac_checkov_rule_catalog.csv"
)

OUT = Path(
    "dataset/main/research_scope/"
    "research_scope_rules.csv"
)


SCOPE = {
    "CKV_AWS_130": {
        "security_domain": "Network Exposure",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Public IP assignment risk depends on "
            "subnet role, workload exposure and environment."
        ),
    },

    "CKV_AWS_382": {
        "security_domain": "Network Exposure",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Unrestricted egress risk depends on workload "
            "role, destination constraints and controls."
        ),
    },

    "CKV_AWS_260": {
        "security_domain": "Network Exposure",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Public HTTP ingress may be intended for a "
            "frontend but inappropriate for internal services."
        ),
    },

    "CKV_AWS_38": {
        "security_domain": "Network Exposure",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "EKS public endpoint exposure depends on "
            "environment, access restrictions and controls."
        ),
    },

    "CKV2_AWS_6": {
        "security_domain": "Data Protection",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "S3 public-access controls depend strongly on "
            "bucket purpose and data sensitivity."
        ),
    },

    "CKV_AWS_145": {
        "security_domain": "Data Protection",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "KMS encryption importance changes with "
            "data sensitivity and compliance context."
        ),
    },

    "CKV_AWS_355": {
        "security_domain": "IAM / Authorization",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Wildcard resource risk depends on permission "
            "scope, account boundary and asset criticality."
        ),
    },

    "CKV_AWS_290": {
        "security_domain": "IAM / Authorization",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Unconstrained write access risk changes with "
            "resource criticality and trust boundary."
        ),
    },

    "CKV_AWS_117": {
        "security_domain": "Workload Isolation",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Lambda outside a VPC is not universally unsafe; "
            "risk depends on workload and connectivity needs."
        ),
    },

    "CKV2_AWS_11": {
        "security_domain": "Detection / Observability",
        "context_sensitive": True,
        "include_research_scope": True,
        "priority": "primary",
        "reason": (
            "Flow logging importance depends on environment, "
            "monitoring controls and compliance requirements."
        ),
    },
}


df = pd.read_csv(CATALOG).fillna("")


selected = df[
    df["check_id"].isin(
        SCOPE.keys()
    )
].copy()


selected["security_domain"] = (
    selected["check_id"].map(
        lambda x: SCOPE[x][
            "security_domain"
        ]
    )
)

selected["context_sensitive"] = (
    selected["check_id"].map(
        lambda x: SCOPE[x][
            "context_sensitive"
        ]
    )
)

selected["include_research_scope"] = (
    selected["check_id"].map(
        lambda x: SCOPE[x][
            "include_research_scope"
        ]
    )
)

selected["research_priority"] = (
    selected["check_id"].map(
        lambda x: SCOPE[x][
            "priority"
        ]
    )
)

selected["selection_reason"] = (
    selected["check_id"].map(
        lambda x: SCOPE[x][
            "reason"
        ]
    )
)


selected = selected.sort_values(
    [
        "security_domain",
        "check_id",
    ]
)


OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

selected.to_csv(
    OUT,
    index=False,
)


print("==============================")
print("RESEARCH SCOPE RULES")
print("==============================")

print(
    "Rules =",
    len(selected),
)

print(
    "Findings =",
    selected[
        "finding_count"
    ].sum(),
)

print(
    "Artifacts represented =",
    selected[
        "artifact_count"
    ].max(),
    "(not unique-union count)",
)

print()

print(
    selected[
        [
            "check_id",
            "security_domain",
            "finding_count",
            "artifact_count",
            "scenario_count",
        ]
    ].to_string(
        index=False
    )
)

print()
print("Output =", OUT)
