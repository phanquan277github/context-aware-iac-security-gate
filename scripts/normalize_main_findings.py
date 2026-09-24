from pathlib import Path
import hashlib
import json
import re

import pandas as pd
import yaml


# ======================================================================
# Paths
# ======================================================================

RAW_CSV = Path(
    "results/main_checkov/raw_finding_inventory.csv"
)

RAW_JSON = Path(
    "results/main_checkov/checkov-main.json/results_json.json"
)

SCOPE_CSV = Path(
    "results/main_normalization/main_scope_mapping.csv"
)

SEVERITY_CSV = Path(
    "results/main_normalization/main_severity_mapping.csv"
)

CONTEXT_ROOT = Path(
    "dataset/main/contrastive"
)

OUT_DIR = Path(
    "results/main_normalization"
)

OUT_ALL = (
    OUT_DIR / "normalized_findings_all.csv"
)

OUT_SCOPE = (
    OUT_DIR / "normalized_findings_in_scope.csv"
)

OUT_SUMMARY = (
    OUT_DIR / "normalization_summary.csv"
)


# ======================================================================
# Helpers
# ======================================================================

def normalize_resource_address(value: str) -> str:
    """
    Checkov currently returns resource_address=null for the observed
    main-dataset findings.

    Therefore, the Checkov 'resource' field is used as the logical
    Terraform resource identity.

    Examples:
        aws_s3_bucket.example
        aws_iam_policy.target
        aws_db_instance.target
        module.web.aws_instance.server
    """
    value = str(value or "").strip()

    # Remove whitespace that should not affect resource identity.
    value = re.sub(r"\s+", "", value)

    return value


def resource_type_from_address(address: str) -> str:
    """
    Extract Terraform resource type from a logical resource address.

    Examples:
        aws_s3_bucket.example
            -> aws_s3_bucket

        aws_iam_policy.target
            -> aws_iam_policy

        module.web.aws_instance.server
            -> aws_instance

        data.aws_ami.example
            -> aws_ami
    """
    address = str(address or "").strip()

    if not address:
        return ""

    parts = [p for p in address.split(".") if p]

    if len(parts) < 2:
        return ""

    # Handle indexed/count addresses conservatively.
    candidate = parts[-2]

    candidate = re.sub(
        r"\[.*\]$",
        "",
        candidate,
    )

    return candidate


def normalize_repo_path(path: str) -> str:
    """
    Normalize absolute or repository-relative paths.

    Example:

      /home/.../dataset/main/contrastive/CTX-03/context_a/main.tf

    becomes:

      dataset/main/contrastive/CTX-03/context_a/main.tf
    """
    path = str(path or "").replace("\\", "/").strip()

    marker = "/dataset/main/contrastive/"

    if marker in path:
        return (
            "dataset/main/contrastive/"
            + path.split(marker, 1)[1]
        )

    if path.startswith(
        "dataset/main/contrastive/"
    ):
        return path

    return path.lstrip("/")


def extract_scenario_from_path(path: str):
    """
    Extract:

        family_id
        context_variant
        scenario_id

    from a repository path such as:

        dataset/main/contrastive/CTX-03/context_a/main.tf
    """
    path = normalize_repo_path(path)

    pattern = (
        r"dataset/main/contrastive/"
        r"(CTX-\d+)/(context_a|context_b)/"
    )

    match = re.search(pattern, path)

    if not match:
        return "", "", ""

    family_id = match.group(1)
    context_variant = match.group(2)

    scenario_id = (
        f"{family_id}-A"
        if context_variant == "context_a"
        else f"{family_id}-B"
    )

    return (
        family_id,
        context_variant,
        scenario_id,
    )


def finding_key(
    scenario_id: str,
    check_id: str,
    resource: str,
):
    """
    Logical identity for a raw Checkov finding.

    IMPORTANT:
    file_path is intentionally NOT included.

    The research protocol defines a matched finding using:
        same check_id
        +
        same logical Terraform resource address

    In the observed Checkov output, resource_address is null and
    resource contains the usable logical resource identity.
    """
    return (
        str(scenario_id or ""),
        str(check_id or ""),
        str(resource or ""),
    )


def first_nonempty(*values):
    """
    Return the first non-empty value.
    """
    for value in values:
        if value is None:
            continue

        value = str(value)

        if value.strip():
            return value

    return ""


# ======================================================================
# 1. Validate input files
# ======================================================================

required_files = [
    RAW_CSV,
    RAW_JSON,
    SCOPE_CSV,
    SEVERITY_CSV,
]

for path in required_files:
    if not path.is_file():
        raise SystemExit(
            f"Missing input file: {path}"
        )


# ======================================================================
# 2. Load raw finding inventory
# ======================================================================

raw = pd.read_csv(
    RAW_CSV,
    dtype=str,
).fillna("")

if raw.empty:
    raise SystemExit(
        "ERROR: raw finding inventory is empty."
    )

required_raw_columns = {
    "raw_finding_id",
    "scenario_id",
    "family_id",
    "context_variant",
    "check_id",
    "resource",
    "file_path",
    "severity_raw",
    "check_name",
}

missing_raw = (
    required_raw_columns
    - set(raw.columns)
)

if missing_raw:
    raise SystemExit(
        "Raw inventory missing columns: "
        + ", ".join(sorted(missing_raw))
    )

print(
    "Raw inventory rows =",
    len(raw),
)


# ======================================================================
# 3. Load scope mapping
# ======================================================================

scope = pd.read_csv(
    SCOPE_CSV,
    dtype=str,
).fillna("")

required_scope_columns = {
    "check_id",
    "check_name",
    "scope_status",
    "scope_category",
    "notes",
}

missing_scope_columns = (
    required_scope_columns
    - set(scope.columns)
)

if missing_scope_columns:
    raise SystemExit(
        "Scope mapping missing columns: "
        + ", ".join(
            sorted(missing_scope_columns)
        )
    )

if scope["check_id"].duplicated().any():
    duplicate_ids = sorted(
        scope.loc[
            scope["check_id"].duplicated(
                keep=False
            ),
            "check_id",
        ].unique()
    )

    raise SystemExit(
        "Duplicate check_id in scope mapping: "
        + ", ".join(duplicate_ids)
    )

scope_map = {
    row["check_id"]: row.to_dict()
    for _, row in scope.iterrows()
}


# ======================================================================
# 4. Load main severity mapping
# ======================================================================

severity = pd.read_csv(
    SEVERITY_CSV,
    dtype=str,
).fillna("")

required_severity_columns = {
    "check_id",
    "severity_class",
    "severity_numeric",
    "policy_basis",
}

missing_severity_columns = (
    required_severity_columns
    - set(severity.columns)
)

if missing_severity_columns:
    raise SystemExit(
        "Severity mapping missing columns: "
        + ", ".join(
            sorted(missing_severity_columns)
        )
    )

if severity["check_id"].duplicated().any():
    duplicate_ids = sorted(
        severity.loc[
            severity["check_id"].duplicated(
                keep=False
            ),
            "check_id",
        ].unique()
    )

    raise SystemExit(
        "Duplicate check_id in severity mapping: "
        + ", ".join(duplicate_ids)
    )

severity_map = {
    row["check_id"]: row.to_dict()
    for _, row in severity.iterrows()
}


# ======================================================================
# 5. Load explicit scenario contexts
# ======================================================================

contexts = {}

context_files = sorted(
    CONTEXT_ROOT.glob(
        "CTX-*/context_*/context.yaml"
    )
)

required_context_fields = {
    "family_id",
    "scenario_id",
    "base_seed_id",
    "context_variant",
    "environment",
    "asset_criticality",
    "data_sensitivity",
}

for path in context_files:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        ctx = yaml.safe_load(f) or {}

    missing_context = (
        required_context_fields
        - set(ctx.keys())
    )

    if missing_context:
        raise SystemExit(
            f"{path}: missing context fields: "
            + ", ".join(
                sorted(missing_context)
            )
        )

    scenario_id = str(
        ctx["scenario_id"]
    )

    if scenario_id in contexts:
        raise SystemExit(
            "Duplicate scenario context: "
            + scenario_id
        )

    contexts[scenario_id] = ctx

print(
    "Context files =",
    len(contexts),
)

if len(contexts) != 20:
    raise SystemExit(
        "Expected 20 scenario contexts, "
        f"found {len(contexts)}."
    )


# ======================================================================
# 6. Load raw Checkov JSON
# ======================================================================

with RAW_JSON.open(
    "r",
    encoding="utf-8",
) as f:
    checkov = json.load(f)

results = checkov.get(
    "results",
    {},
)

json_failed = results.get(
    "failed_checks",
    [],
)

if len(json_failed) != len(raw):
    raise SystemExit(
        "Raw CSV / Checkov JSON count mismatch: "
        f"{len(raw)} vs {len(json_failed)}"
    )

print(
    "Checkov JSON failed checks =",
    len(json_failed),
)


# ======================================================================
# 7. Build Checkov lookup
# ======================================================================
#
# IMPORTANT:
# We use:
#
#     scenario_id + check_id + resource
#
# and NOT file_path.
#
# This is necessary because Checkov may expose:
#
#     file_path = /main.tf
#
# while:
#
#     repo_file_path =
#       /dataset/main/contrastive/CTX-03/context_a/main.tf
#
# ======================================================================

json_lookup = {}

for item in json_failed:

    path_for_identity = first_nonempty(
        item.get("repo_file_path"),
        item.get("file_abs_path"),
        item.get("file_path"),
    )

    normalized_path = normalize_repo_path(
        path_for_identity
    )

    (
        family_id,
        context_variant,
        scenario_id,
    ) = extract_scenario_from_path(
        normalized_path
    )

    if not scenario_id:
        raise SystemExit(
            "Unable to extract scenario identity "
            f"from Checkov path: {path_for_identity}"
        )

    check_id = str(
        item.get("check_id", "")
    )

    resource = str(
        item.get("resource", "")
    )

    if not check_id:
        raise SystemExit(
            "Checkov finding missing check_id."
        )

    if not resource:
        raise SystemExit(
            "Checkov finding missing resource."
        )

    key = finding_key(
        scenario_id,
        check_id,
        resource,
    )

    if key in json_lookup:
        raise SystemExit(
            "Duplicate Checkov logical finding key: "
            + repr(key)
        )

    json_lookup[key] = item


print(
    "Checkov logical findings indexed =",
    len(json_lookup),
)


# ======================================================================
# 8. Verify scope coverage
# ======================================================================

main_check_ids = sorted(
    raw["check_id"].unique()
)

missing_scope = [
    check_id
    for check_id in main_check_ids
    if check_id not in scope_map
]

if missing_scope:
    print(
        "Missing scope mappings:"
    )

    for check_id in missing_scope:
        print(
            " -",
            check_id,
        )

    raise SystemExit(
        "STOP: main Checkov checks are not "
        "fully covered by main_scope_mapping.csv."
    )


# ======================================================================
# 9. Verify severity coverage for IN_SCOPE checks
# ======================================================================

in_scope_check_ids = [
    check_id
    for check_id in main_check_ids
    if scope_map[check_id]["scope_status"]
    == "IN_SCOPE"
]

missing_severity = [
    check_id
    for check_id in in_scope_check_ids
    if check_id not in severity_map
]

if missing_severity:
    print(
        "Missing severity mappings for IN_SCOPE checks:"
    )

    for check_id in missing_severity:
        print(
            " -",
            check_id,
        )

    raise SystemExit(
        "STOP: main severity mapping does not "
        "cover all IN_SCOPE Checkov checks."
    )


# ======================================================================
# 10. Normalize findings
# ======================================================================

rows = []

for _, raw_row in raw.iterrows():

    scenario_id = raw_row[
        "scenario_id"
    ]

    family_id = raw_row[
        "family_id"
    ]

    context_variant = raw_row[
        "context_variant"
    ]

    check_id = raw_row[
        "check_id"
    ]

    resource_raw = raw_row[
        "resource"
    ]

    file_path_raw = raw_row[
        "file_path"
    ]

    resource_address_norm = (
        normalize_resource_address(
            resource_raw
        )
    )

    repo_path = normalize_repo_path(
        file_path_raw
    )

    # --------------------------------------------------------------
    # Verify raw finding against Checkov JSON
    # --------------------------------------------------------------

    key = finding_key(
        scenario_id,
        check_id,
        resource_raw,
    )

    item = json_lookup.get(key)

    if item is None:
        raise SystemExit(
            "Missing matching raw Checkov JSON finding: "
            + repr(key)
        )

    # --------------------------------------------------------------
    # Verify scenario identity from the authoritative path
    # --------------------------------------------------------------

    path_for_verification = first_nonempty(
        item.get("repo_file_path"),
        item.get("file_abs_path"),
        item.get("file_path"),
    )

    normalized_verification_path = (
        normalize_repo_path(
            path_for_verification
        )
    )

    (
        json_family,
        json_variant,
        json_scenario,
    ) = extract_scenario_from_path(
        normalized_verification_path
    )

    if json_scenario != scenario_id:
        raise SystemExit(
            "Scenario mismatch between raw inventory "
            "and Checkov JSON path: "
            f"{scenario_id} vs {json_scenario}"
        )

    if json_family != family_id:
        raise SystemExit(
            "Family mismatch: "
            f"{family_id} vs {json_family}"
        )

    if json_variant != context_variant:
        raise SystemExit(
            "Context variant mismatch: "
            f"{context_variant} vs {json_variant}"
        )

    # --------------------------------------------------------------
    # Context
    # --------------------------------------------------------------

    if scenario_id not in contexts:
        raise SystemExit(
            f"Missing context metadata: {scenario_id}"
        )

    ctx = contexts[
        scenario_id
    ]

    # --------------------------------------------------------------
    # Scope
    # --------------------------------------------------------------

    scope_row = scope_map[
        check_id
    ]

    scope_status = scope_row[
        "scope_status"
    ]

    scope_category = scope_row[
        "scope_category"
    ]

    scope_notes = scope_row[
        "notes"
    ]

    # --------------------------------------------------------------
    # Severity
    # --------------------------------------------------------------

    if scope_status == "IN_SCOPE":

        sev_row = severity_map[
            check_id
        ]

        severity_class = sev_row[
            "severity_class"
        ]

        severity_numeric = sev_row[
            "severity_numeric"
        ]

        severity_policy_basis = sev_row[
            "policy_basis"
        ]

    else:

        severity_class = ""
        severity_numeric = ""
        severity_policy_basis = ""

    # --------------------------------------------------------------
    # Checkov line range
    # --------------------------------------------------------------

    line_range = (
        item.get("file_line_range")
        or []
    )

    if (
        isinstance(line_range, list)
        and len(line_range) >= 2
    ):
        line_start = line_range[0]
        line_end = line_range[1]
    else:
        line_start = ""
        line_end = ""

    # --------------------------------------------------------------
    # Stable normalized finding ID
    # --------------------------------------------------------------

    normalized_identity = "|".join(
        [
            scenario_id,
            check_id,
            resource_address_norm,
            repo_path,
            str(line_start),
            str(line_end),
        ]
    )

    normalized_finding_id = (
        hashlib.sha256(
            normalized_identity.encode(
                "utf-8"
            )
        ).hexdigest()[:16]
    )

    rows.append(
        {
            "normalized_finding_id":
                normalized_finding_id,

            "raw_finding_id":
                raw_row["raw_finding_id"],

            "scenario_id":
                scenario_id,

            "family_id":
                family_id,

            "context_variant":
                context_variant,

            "base_seed_id":
                ctx["base_seed_id"],

            "check_id":
                check_id,

            "check_name":
                raw_row["check_name"],

            "resource_raw":
                resource_raw,

            "resource_address_norm":
                resource_address_norm,

            "resource_type":
                resource_type_from_address(
                    resource_address_norm
                ),

            "file_path_raw":
                file_path_raw,

            "file_path_repo":
                repo_path,

            "line_start":
                line_start,

            "line_end":
                line_end,

            "severity_raw":
                raw_row["severity_raw"],

            "severity_class":
                severity_class,

            "severity_numeric":
                severity_numeric,

            "scope_status":
                scope_status,

            "scope_category":
                scope_category,

            "scope_notes":
                scope_notes,

            "severity_policy_basis":
                severity_policy_basis,

            "environment":
                ctx["environment"],

            "asset_criticality":
                ctx["asset_criticality"],

            "data_sensitivity":
                ctx["data_sensitivity"],
        }
    )


# ======================================================================
# 11. Create DataFrame
# ======================================================================

normalized = pd.DataFrame(
    rows
)

if normalized.empty:
    raise SystemExit(
        "ERROR: normalized dataset is empty."
    )


# ======================================================================
# 12. Integrity checks
# ======================================================================

# Raw count must be preserved.
if len(normalized) != len(raw):
    raise SystemExit(
        "Row count changed during normalization: "
        f"{len(raw)} -> {len(normalized)}"
    )


# Raw IDs must remain unique.
raw_duplicate_count = (
    normalized["raw_finding_id"]
    .duplicated()
    .sum()
)

if raw_duplicate_count:
    raise SystemExit(
        "Duplicate raw_finding_id detected: "
        f"{raw_duplicate_count}"
    )


# Normalized IDs must be unique.
normalized_duplicate_count = (
    normalized["normalized_finding_id"]
    .duplicated()
    .sum()
)

if normalized_duplicate_count:
    raise SystemExit(
        "Duplicate normalized_finding_id detected: "
        f"{normalized_duplicate_count}"
    )


# Required columns.
required_normalized_columns = [
    "normalized_finding_id",
    "raw_finding_id",
    "scenario_id",
    "family_id",
    "context_variant",
    "base_seed_id",
    "check_id",
    "check_name",
    "resource_raw",
    "resource_address_norm",
    "resource_type",
    "file_path_raw",
    "file_path_repo",
    "line_start",
    "line_end",
    "severity_raw",
    "severity_class",
    "severity_numeric",
    "scope_status",
    "scope_category",
    "scope_notes",
    "severity_policy_basis",
    "environment",
    "asset_criticality",
    "data_sensitivity",
]

for column in required_normalized_columns:
    if column not in normalized.columns:
        raise SystemExit(
            "Missing normalized column: "
            + column
        )


# Required non-null identity/context fields.
required_nonnull = [
    "scenario_id",
    "family_id",
    "context_variant",
    "check_id",
    "resource_address_norm",
    "scope_status",
    "environment",
    "asset_criticality",
    "data_sensitivity",
]

for column in required_nonnull:

    missing_count = (
        normalized[column]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if missing_count:
        raise SystemExit(
            f"Missing values in required field "
            f"{column}: {missing_count}"
        )


# Scenario count.
if normalized[
    "scenario_id"
].nunique() != 20:

    raise SystemExit(
        "Expected 20 scenarios after normalization."
    )


# Family count.
if normalized[
    "family_id"
].nunique() != 10:

    raise SystemExit(
        "Expected 10 families after normalization."
    )


# Context variants.
context_a_count = (
    normalized[
        "context_variant"
    ] == "context_a"
).sum()

context_b_count = (
    normalized[
        "context_variant"
    ] == "context_b"
).sum()

if context_a_count != 74:
    raise SystemExit(
        f"Unexpected context_a count: "
        f"{context_a_count}"
    )

if context_b_count != 74:
    raise SystemExit(
        f"Unexpected context_b count: "
        f"{context_b_count}"
    )


# ======================================================================
# 13. Create IN_SCOPE subset
# ======================================================================

normalized_in_scope = normalized[
    normalized["scope_status"] == "IN_SCOPE"
].copy()


# All IN_SCOPE records must have severity.
if normalized_in_scope.empty:

    raise SystemExit(
        "ERROR: No IN_SCOPE findings after normalization."
    )

if (
    normalized_in_scope[
        "severity_class"
    ]
    .astype(str)
    .str.strip()
    .eq("")
    .any()
):
    raise SystemExit(
        "IN_SCOPE finding missing severity_class."
    )

if (
    normalized_in_scope[
        "severity_numeric"
    ]
    .astype(str)
    .str.strip()
    .eq("")
    .any()
):
    raise SystemExit(
        "IN_SCOPE finding missing severity_numeric."
    )


# ======================================================================
# 14. Write output files
# ======================================================================

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

normalized.to_csv(
    OUT_ALL,
    index=False,
    encoding="utf-8",
)

normalized_in_scope.to_csv(
    OUT_SCOPE,
    index=False,
    encoding="utf-8",
)


# ======================================================================
# 15. Write summary
# ======================================================================

summary = {
    "raw_findings":
        len(raw),

    "normalized_findings_all":
        len(normalized),

    "normalized_findings_in_scope":
        len(normalized_in_scope),

    "unique_families":
        normalized[
            "family_id"
        ].nunique(),

    "unique_scenarios":
        normalized[
            "scenario_id"
        ].nunique(),

    "unique_check_ids":
        normalized[
            "check_id"
        ].nunique(),

    "context_a_findings":
        int(context_a_count),

    "context_b_findings":
        int(context_b_count),

    "in_scope_findings":
        int(
            (
                normalized[
                    "scope_status"
                ]
                == "IN_SCOPE"
            ).sum()
        ),

    "out_of_scope_findings":
        int(
            (
                normalized[
                    "scope_status"
                ]
                == "OUT_OF_SCOPE"
            ).sum()
        ),

    "missing_scope_mappings":
        0,

    "missing_severity_mappings":
        0,

    "missing_context":
        0,

    "duplicate_raw_ids":
        int(raw_duplicate_count),

    "duplicate_normalized_ids":
        int(normalized_duplicate_count),

    "status":
        "PASS",
}

pd.DataFrame(
    [summary]
).to_csv(
    OUT_SUMMARY,
    index=False,
    encoding="utf-8",
)


# ======================================================================
# 16. Final console output
# ======================================================================

print()
print(
    "=================================================="
)
print(
    "STEP 13 NORMALIZATION"
)
print(
    "=================================================="
)

print(
    "Normalization status = PASS"
)

print(
    "Raw findings =",
    len(raw),
)

print(
    "Normalized findings =",
    len(normalized),
)

print(
    "In-scope findings =",
    len(normalized_in_scope),
)

print(
    "Out-of-scope findings =",
    len(normalized)
    - len(normalized_in_scope),
)

print(
    "Families =",
    normalized[
        "family_id"
    ].nunique(),
)

print(
    "Scenarios =",
    normalized[
        "scenario_id"
    ].nunique(),
)

print(
    "Check IDs =",
    normalized[
        "check_id"
    ].nunique(),
)

print(
    "Context A =",
    context_a_count,
)

print(
    "Context B =",
    context_b_count,
)

print()
print(
    "Severity classes in IN_SCOPE:"
)

for severity_class, count in (
    normalized_in_scope[
        "severity_class"
    ]
    .value_counts()
    .sort_index()
    .items()
):
    print(
        f"  {severity_class}: {count}"
    )

print()
print(
    "Output files:"
)

print(
    " -",
    OUT_ALL,
)

print(
    " -",
    OUT_SCOPE,
)

print(
    " -",
    OUT_SUMMARY,
)

print(
    "=================================================="
)
