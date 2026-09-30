from pathlib import Path
import pandas as pd


OUT = Path(
    "dataset/main/context/"
    "rule_context_applicability.csv"
)


rows = [

    # ==========================================================
    # NETWORK EXPOSURE
    # ==========================================================

    {
        "check_id": "CKV_AWS_130",
        "internet_exposure": True,
        "reachability": True,
        "privilege_impact": False,
        "resource_role": True,
        "public_access": True,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": False,
    },

    {
        "check_id": "CKV_AWS_382",
        "internet_exposure": False,
        "reachability": True,
        "privilege_impact": False,
        "resource_role": True,
        "public_access": False,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": False,
    },

    {
        "check_id": "CKV_AWS_260",
        "internet_exposure": True,
        "reachability": True,
        "privilege_impact": False,
        "resource_role": True,
        "public_access": True,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": False,
    },

    {
        "check_id": "CKV_AWS_38",
        "internet_exposure": True,
        "reachability": True,
        "privilege_impact": False,
        "resource_role": True,
        "public_access": True,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": False,
    },

    # ==========================================================
    # DATA PROTECTION
    # ==========================================================

    {
        "check_id": "CKV2_AWS_6",

        # Missing Public Access Block does NOT prove that the
        # bucket is directly Internet-exposed or reachable.
        "internet_exposure": False,
        "reachability": False,

        "privilege_impact": False,
        "resource_role": True,

        # Public-access state is still relevant and should be
        # evaluated from actual Terraform evidence.
        "public_access": True,

        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": False,
    },

    {
        "check_id": "CKV_AWS_145",
        "internet_exposure": False,
        "reachability": False,
        "privilege_impact": False,
        "resource_role": True,
        "public_access": False,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": True,
        "logging_missing": False,
    },

    # ==========================================================
    # IAM / AUTHORIZATION
    # ==========================================================

    {
        "check_id": "CKV_AWS_355",
        "internet_exposure": False,
        "reachability": False,
        "privilege_impact": True,
        "resource_role": True,
        "public_access": False,
        "wildcard_action": False,
        "wildcard_resource": True,
        "encryption_missing": False,
        "logging_missing": False,
    },

    {
        "check_id": "CKV_AWS_290",
        "internet_exposure": False,
        "reachability": False,
        "privilege_impact": True,
        "resource_role": True,
        "public_access": False,
        "wildcard_action": True,
        "wildcard_resource": True,
        "encryption_missing": False,
        "logging_missing": False,
    },

    # ==========================================================
    # WORKLOAD ISOLATION
    # ==========================================================

    {
        "check_id": "CKV_AWS_117",

        # Lambda not being inside a VPC does not itself prove
        # Internet exposure or direct Internet reachability.
        "internet_exposure": False,
        "reachability": False,

        "privilege_impact": False,
        "resource_role": True,
        "public_access": False,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": False,
    },

    # ==========================================================
    # DETECTION / OBSERVABILITY
    # ==========================================================

    {
        "check_id": "CKV2_AWS_11",
        "internet_exposure": False,
        "reachability": False,
        "privilege_impact": False,
        "resource_role": True,
        "public_access": False,
        "wildcard_action": False,
        "wildcard_resource": False,
        "encryption_missing": False,
        "logging_missing": True,
    },
]


df = pd.DataFrame(rows)


# ----------------------------------------------------------
# SAFETY CHECKS
# ----------------------------------------------------------

if df["check_id"].duplicated().any():

    duplicated = (
        df[
            df["check_id"].duplicated(
                keep=False
            )
        ]["check_id"]
        .tolist()
    )

    raise ValueError(
        f"Duplicate check_id values: {duplicated}"
    )


expected_features = [
    "internet_exposure",
    "reachability",
    "privilege_impact",
    "resource_role",
    "public_access",
    "wildcard_action",
    "wildcard_resource",
    "encryption_missing",
    "logging_missing",
]


missing = [
    feature
    for feature in expected_features
    if feature not in df.columns
]

if missing:
    raise ValueError(
        "Missing applicability features: "
        + ", ".join(missing)
    )


OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


df.to_csv(
    OUT,
    index=False,
)


print("Rules =", len(df))
print("Output =", OUT)

print()

print(
    df.to_string(
        index=False
    )
)
