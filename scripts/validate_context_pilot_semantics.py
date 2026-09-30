from pathlib import Path
import sys

import pandas as pd


INPUT = Path(
    "results/context_feature_pilot/"
    "finding_context_features_pilot.csv"
)


FEATURES = [
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


df = pd.read_csv(
    INPUT,
    dtype=str,
).fillna("")


errors = []


# ==========================================================
# BASIC STRUCTURE
# ==========================================================

if len(df) != 20:
    errors.append(
        f"Expected 20 rows, found {len(df)}"
    )

if df["finding_id"].nunique() != 20:
    errors.append(
        "finding_id values are not unique"
    )

if df["finding_id"].duplicated().any():
    errors.append(
        "Duplicate finding_id detected"
    )

if df["check_id"].nunique() != 10:
    errors.append(
        "Expected 10 unique rules"
    )


counts = (
    df["check_id"]
    .value_counts()
)

bad_counts = counts[
    counts != 2
]

if not bad_counts.empty:
    errors.append(
        "Each pilot rule must have exactly "
        "2 findings:\n"
        + bad_counts.to_string()
    )


# ==========================================================
# HELPER
# ==========================================================

def require(
    row,
    feature,
    expected,
):
    actual = str(
        row[feature]
    )

    if actual != expected:
        errors.append(
            f"{row['check_id']} | "
            f"{row['resource']} | "
            f"{feature}: "
            f"expected={expected}, "
            f"actual={actual}"
        )


# ==========================================================
# RULE-LEVEL SEMANTIC INVARIANTS
# ==========================================================

for _, row in df.iterrows():

    rule = row["check_id"]

    # ------------------------------------------------------
    # VPC FLOW LOGGING
    # ------------------------------------------------------

    if rule == "CKV2_AWS_11":

        require(
            row,
            "resource_role",
            "network",
        )

        require(
            row,
            "logging_missing",
            "yes",
        )

    # ------------------------------------------------------
    # S3 PUBLIC ACCESS BLOCK
    # ------------------------------------------------------

    elif rule == "CKV2_AWS_6":

        require(
            row,
            "resource_role",
            "primary_data",
        )

        # Missing Public Access Block does not prove
        # that the bucket is currently public.
        require(
            row,
            "public_access",
            "unknown",
        )

    # ------------------------------------------------------
    # LAMBDA VPC CONFIGURATION
    # ------------------------------------------------------

    elif rule == "CKV_AWS_117":

        require(
            row,
            "resource_role",
            "compute",
        )

        require(
            row,
            "internet_exposure",
            "not_applicable",
        )

        require(
            row,
            "reachability",
            "not_applicable",
        )

    # ------------------------------------------------------
    # SUBNET PUBLIC IP ASSIGNMENT
    # ------------------------------------------------------

    elif rule == "CKV_AWS_130":

        require(
            row,
            "resource_role",
            "network",
        )

        # Public-IP auto assignment alone does not prove
        # an Internet route or confirmed public exposure.
        require(
            row,
            "internet_exposure",
            "unknown",
        )

        require(
            row,
            "reachability",
            "unknown",
        )

        require(
            row,
            "public_access",
            "unknown",
        )

    # ------------------------------------------------------
    # S3 KMS ENCRYPTION
    # ------------------------------------------------------

    elif rule == "CKV_AWS_145":

        require(
            row,
            "resource_role",
            "primary_data",
        )

        require(
            row,
            "encryption_missing",
            "yes",
        )

    # ------------------------------------------------------
    # PUBLIC HTTP INGRESS
    # ------------------------------------------------------

    elif rule == "CKV_AWS_260":

        require(
            row,
            "resource_role",
            "network",
        )

        require(
            row,
            "internet_exposure",
            "yes",
        )

        require(
            row,
            "reachability",
            "internet",
        )

        require(
            row,
            "public_access",
            "yes",
        )

    # ------------------------------------------------------
    # IAM WRITE ACCESS WITHOUT CONSTRAINTS
    # ------------------------------------------------------

    elif rule == "CKV_AWS_290":

        require(
            row,
            "resource_role",
            "identity",
        )

        require(
            row,
            "wildcard_action",
            "no",
        )

        require(
            row,
            "wildcard_resource",
            "yes",
        )

        # Both selected pilot policies contain broad
        # write/resource-control capability but not
        # IAM administrative privilege escalation.
        require(
            row,
            "privilege_impact",
            "2",
        )

    # ------------------------------------------------------
    # IAM RESTRICTABLE ACTIONS + RESOURCE="*"
    # ------------------------------------------------------

    elif rule == "CKV_AWS_355":

        require(
            row,
            "resource_role",
            "identity",
        )

        require(
            row,
            "wildcard_action",
            "not_applicable",
        )

        require(
            row,
            "wildcard_resource",
            "yes",
        )

        privilege = str(
            row["privilege_impact"]
        )

        if privilege not in {
            "1",
            "2",
        }:
            errors.append(
                f"{rule} | "
                f"{row['resource']} | "
                "privilege_impact must be "
                "1 or 2, got "
                f"{privilege}"
            )

    # ------------------------------------------------------
    # EKS PUBLIC API ENDPOINT
    # ------------------------------------------------------

    elif rule == "CKV_AWS_38":

        require(
            row,
            "resource_role",
            "compute",
        )

        require(
            row,
            "internet_exposure",
            "yes",
        )

        require(
            row,
            "reachability",
            "internet",
        )

        require(
            row,
            "public_access",
            "yes",
        )

    # ------------------------------------------------------
    # UNRESTRICTED EGRESS
    # ------------------------------------------------------

    elif rule == "CKV_AWS_382":

        require(
            row,
            "resource_role",
            "network",
        )

        # This rule concerns outbound egress.
        # It must not be represented as confirmed
        # inbound Internet exposure.
        require(
            row,
            "internet_exposure",
            "not_applicable",
        )

        require(
            row,
            "reachability",
            "internet",
        )

    else:

        errors.append(
            f"Unexpected rule: {rule}"
        )


# ==========================================================
# UNKNOWN POLICY
# ==========================================================

allowed_unknowns = {
    "CKV2_AWS_6": {
        "public_access",
    },

    "CKV_AWS_130": {
        "internet_exposure",
        "reachability",
        "public_access",
    },
}


for _, row in df.iterrows():

    observed = {
        feature
        for feature in FEATURES
        if str(
            row[feature]
        ) == "unknown"
    }

    allowed = allowed_unknowns.get(
        row["check_id"],
        set(),
    )

    unexpected = (
        observed - allowed
    )

    if unexpected:
        errors.append(
            f"{row['check_id']} | "
            f"{row['resource']} | "
            "unexpected unknown features: "
            + ",".join(
                sorted(
                    unexpected
                )
            )
        )


# ==========================================================
# EXTRACTION STATUS
# ==========================================================

bad_status = df[
    df["feature_extraction_status"]
    != "EXTRACTED"
]

if not bad_status.empty:
    errors.append(
        "Some pilot rows are not EXTRACTED"
    )


# ==========================================================
# RESULT
# ==========================================================

print(
    "=============================="
)

print(
    "CONTEXT PILOT SEMANTIC QA"
)

print(
    "=============================="
)

print(
    "Rows =",
    len(df),
)

print(
    "Rules =",
    df["check_id"].nunique(),
)

print(
    "Unique finding IDs =",
    df["finding_id"].nunique(),
)

print(
    "Errors =",
    len(errors),
)

print()


if errors:

    print(
        "STATUS = FAIL"
    )

    print()

    for i, error in enumerate(
        errors,
        start=1,
    ):
        print(
            f"[{i}] {error}"
        )

    sys.exit(1)


print(
    "STATUS = PASS"
)

print()

print(
    "=== INTENTIONAL UNKNOWNS ==="
)

unknown_rows = df[
    df[FEATURES]
    .eq("unknown")
    .any(axis=1)
]

if unknown_rows.empty:

    print(
        "None"
    )

else:

    for _, row in unknown_rows.iterrows():

        unknown = [
            feature
            for feature in FEATURES
            if row[feature] == "unknown"
        ]

        print(
            row["check_id"],
            "|",
            row["resource"],
            "|",
            ",".join(unknown),
        )
