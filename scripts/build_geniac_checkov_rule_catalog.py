from pathlib import Path
import pandas as pd


INPUT = Path(
    "dataset/main/findings/"
    "geniac_tier_a_checkov.csv"
)

OUTPUT = Path(
    "dataset/main/findings/"
    "geniac_checkov_rule_catalog.csv"
)


df = pd.read_csv(INPUT).fillna("")


# ----------------------------------------------------------
# RESOURCE TYPE
# ----------------------------------------------------------

if "resource_type" not in df.columns:

    df["resource_type"] = (
        df["resource"]
        .astype(str)
        .str.split(".")
        .str[0]
    )


# ----------------------------------------------------------
# RULE NAMESPACE
# ----------------------------------------------------------

def get_namespace(check_id):
    check_id = str(check_id)

    if check_id.startswith("CKV2_AWS_"):
        return "CKV2_AWS"

    if check_id.startswith("CKV_AWS_"):
        return "CKV_AWS"

    return "OTHER"


df["check_namespace"] = (
    df["check_id"]
    .apply(get_namespace)
)


# ----------------------------------------------------------
# AGGREGATE RULE CATALOG
# ----------------------------------------------------------

records = []


for check_id, group in df.groupby(
    "check_id",
    sort=False,
):

    names = sorted(
        x
        for x in group[
            "check_name"
        ].astype(str).unique()
        if x
    )

    resource_types = sorted(
        x
        for x in group[
            "resource_type"
        ].astype(str).unique()
        if x
    )

    scenarios = sorted(
        x
        for x in group[
            "scenario_id"
        ].astype(str).unique()
        if x
    )

    complexities = sorted(
        x
        for x in group[
            "complexity"
        ].astype(str).unique()
        if x
    )

    models = sorted(
        x
        for x in group[
            "model"
        ].astype(str).unique()
        if x
    )

    records.append({
        "check_id": check_id,

        "check_namespace": (
            get_namespace(
                check_id
            )
        ),

        "check_name": (
            names[0]
            if names
            else ""
        ),

        "finding_count": (
            len(group)
        ),

        "artifact_count": (
            group[
                "candidate_id"
            ].nunique()
        ),

        "scenario_count": (
            group[
                "scenario_id"
            ].nunique()
        ),

        "resource_type_count": (
            group[
                "resource_type"
            ].nunique()
        ),

        "resource_types": (
            "|".join(
                resource_types
            )
        ),

        "complexities": (
            "|".join(
                complexities
            )
        ),

        "model_count": (
            group[
                "model"
            ].nunique()
        ),

        "models": (
            "|".join(
                models
            )
        ),

        "example_resource": (
            group[
                "resource"
            ].iloc[0]
        ),

        # Deliberately blank.
        # To be assigned during research-scope review,
        # not inferred automatically.
        "security_domain": "",

        "context_sensitive": "",

        "include_research_scope": "",

        "review_note": "",
    })


catalog = pd.DataFrame(
    records
)


catalog = catalog.sort_values(
    [
        "artifact_count",
        "finding_count",
        "check_id",
    ],
    ascending=[
        False,
        False,
        True,
    ],
)


catalog.to_csv(
    OUTPUT,
    index=False,
)


print("==============================")
print("CHECKOV RULE CATALOG")
print("==============================")

print(
    "Rules =",
    len(catalog),
)

print(
    "Findings represented =",
    catalog[
        "finding_count"
    ].sum(),
)

print()

print("=== TOP 40 RULES ===")

print(
    catalog[
        [
            "check_id",
            "check_name",
            "finding_count",
            "artifact_count",
            "scenario_count",
            "resource_types",
        ]
    ]
    .head(40)
    .to_string(
        index=False
    )
)

print()

print(
    "Output =",
    OUTPUT,
)
