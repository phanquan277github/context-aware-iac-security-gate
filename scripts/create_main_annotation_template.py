from pathlib import Path
import random

import pandas as pd


INPUT = Path(
    "results/main_normalization/normalized_findings_in_scope.csv"
)

OUTPUT = Path(
    "results/main_annotation/main_annotation_template.csv"
)

SEED = 42


required_columns = [
    "normalized_finding_id",
    "scenario_id",
    "family_id",
    "context_variant",
    "base_seed_id",
    "check_id",
    "check_name",
    "resource_address_norm",
    "resource_type",
    "scope_category",
    "severity_class",
    "severity_numeric",
    "file_path_repo",
    "line_start",
    "line_end",
    "environment",
    "asset_criticality",
    "data_sensitivity",
]


# ------------------------------------------------------------
# Load
# ------------------------------------------------------------

if not INPUT.is_file():
    raise SystemExit(
        f"Missing input: {INPUT}"
    )

df = pd.read_csv(
    INPUT,
    dtype=str,
).fillna("")


missing = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing:
    raise SystemExit(
        "Missing input columns: "
        + ", ".join(missing)
    )


# ------------------------------------------------------------
# Basic checks
# ------------------------------------------------------------

if len(df) != 44:
    raise SystemExit(
        f"Expected 44 IN_SCOPE findings, found {len(df)}"
    )

if df["normalized_finding_id"].duplicated().any():
    raise SystemExit(
        "Duplicate normalized_finding_id detected."
    )


# ------------------------------------------------------------
# Deterministic shuffle within each scenario
# ------------------------------------------------------------

rng = random.Random(SEED)

parts = []

for scenario_id, group in df.groupby(
    "scenario_id",
    sort=True
):
    rows = group.to_dict("records")

    rng.shuffle(rows)

    for display_order, row in enumerate(
        rows,
        start=1
    ):
        row["display_order"] = display_order
        row["annotator_id"] = "A1"
        row["annotation_round"] = "1"
        row["rank"] = ""
        row["relevance"] = ""
        row["reason"] = ""
        row["annotation_status"] = "PENDING"

        parts.append(row)


template = pd.DataFrame(parts)


# ------------------------------------------------------------
# Output columns
# ------------------------------------------------------------

columns = [
    "annotator_id",
    "annotation_round",
    "scenario_id",
    "family_id",
    "context_variant",
    "base_seed_id",
    "display_order",

    "normalized_finding_id",

    "check_id",
    "check_name",

    "resource_address_norm",
    "resource_type",

    "scope_category",

    "severity_class",
    "severity_numeric",

    "environment",
    "asset_criticality",
    "data_sensitivity",

    "file_path_repo",
    "line_start",
    "line_end",

    "rank",
    "relevance",
    "reason",
    "annotation_status",
]


template = template[columns]


OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

template.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8",
)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print(
    "Annotation template created."
)

print(
    "Rows =",
    len(template)
)

print(
    "Scenarios =",
    template["scenario_id"].nunique()
)

print(
    "Output =",
    OUTPUT
)

print()
print("Rows per scenario:")

for scenario_id, count in (
    template
    .groupby("scenario_id")
    .size()
    .items()
):
    print(
        f"  {scenario_id}: {count}"
    )
