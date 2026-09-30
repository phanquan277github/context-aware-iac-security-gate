from pathlib import Path

import pandas as pd
import yaml


SCHEMA = Path(
    "dataset/main/context/context_schema.yaml"
)

DEFINITIONS = Path(
    "dataset/main/context/feature_definitions.yaml"
)

APPLICABILITY = Path(
    "dataset/main/context/rule_context_applicability.csv"
)

SCOPE = Path(
    "dataset/main/research_scope/research_scope_rules.csv"
)


with SCHEMA.open(
    "r",
    encoding="utf-8",
) as f:
    schema = yaml.safe_load(f)


with DEFINITIONS.open(
    "r",
    encoding="utf-8",
) as f:
    definitions = yaml.safe_load(f)


app = pd.read_csv(
    APPLICABILITY
)

scope = pd.read_csv(
    SCOPE
)


errors = []


# --------------------------------------------------
# 1. Schema sections
# --------------------------------------------------

if "scenario_context" not in schema:
    errors.append(
        "Missing scenario_context in context_schema.yaml"
    )

if "finding_context" not in schema:
    errors.append(
        "Missing finding_context in context_schema.yaml"
    )


finding_schema = set(
    schema.get(
        "finding_context",
        {}
    ).keys()
)

definition_features = set(
    definitions.keys()
)

app_features = set(
    app.columns
) - {"check_id"}


# --------------------------------------------------
# 2. Applicability fields must exist in schema
# --------------------------------------------------

missing_schema = (
    app_features
    - finding_schema
)

if missing_schema:
    errors.append(
        "Applicability fields missing from schema: "
        + ", ".join(
            sorted(missing_schema)
        )
    )


# --------------------------------------------------
# 3. Schema features need definitions
# --------------------------------------------------

missing_definitions = (
    finding_schema
    - definition_features
)

if missing_definitions:
    errors.append(
        "Schema fields missing feature definitions: "
        + ", ".join(
            sorted(missing_definitions)
        )
    )


# --------------------------------------------------
# 4. Definitions not declared in schema
# --------------------------------------------------

orphan_definitions = (
    definition_features
    - finding_schema
)

if orphan_definitions:
    errors.append(
        "Feature definitions absent from schema: "
        + ", ".join(
            sorted(orphan_definitions)
        )
    )


# --------------------------------------------------
# 5. Human-label leakage check
# --------------------------------------------------

for name, cfg in definitions.items():

    if cfg.get(
        "human_label_derived"
    ) is not False:

        errors.append(
            f"{name}: human_label_derived "
            "must explicitly be false"
        )


# --------------------------------------------------
# 6. Rule scope consistency
# --------------------------------------------------

scope_rules = set(
    scope["check_id"]
    .astype(str)
)

app_rules = set(
    app["check_id"]
    .astype(str)
)


missing_rules = (
    scope_rules
    - app_rules
)

extra_rules = (
    app_rules
    - scope_rules
)


if missing_rules:
    errors.append(
        "Research-scope rules missing applicability: "
        + ", ".join(
            sorted(missing_rules)
        )
    )

if extra_rules:
    errors.append(
        "Applicability contains non-scope rules: "
        + ", ".join(
            sorted(extra_rules)
        )
    )


# --------------------------------------------------
# 7. Duplicate rule check
# --------------------------------------------------

duplicates = (
    app[
        app["check_id"]
        .duplicated(
            keep=False
        )
    ]["check_id"]
    .tolist()
)

if duplicates:
    errors.append(
        "Duplicate applicability rules: "
        + ", ".join(
            sorted(
                set(duplicates)
            )
        )
    )


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print(
    "=============================="
)

print(
    "CONTEXT SCHEMA VALIDATION"
)

print(
    "=============================="
)

print(
    "Scenario context fields =",
    len(
        schema.get(
            "scenario_context",
            {}
        )
    ),
)

print(
    "Finding context fields =",
    len(finding_schema),
)

print(
    "Feature definitions =",
    len(definition_features),
)

print(
    "Applicability features =",
    len(app_features),
)

print(
    "Research-scope rules =",
    len(scope_rules),
)

print(
    "Applicability rules =",
    len(app_rules),
)


if errors:

    print()
    print("STATUS = FAIL")

    for error in errors:
        print(
            "-",
            error,
        )

    raise SystemExit(1)


print()
print("STATUS = PASS")
