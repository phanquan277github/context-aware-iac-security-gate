from pathlib import Path
import argparse
import json
import re

import pandas as pd
import yaml


# ==========================================================
# PATHS
# ==========================================================

DEFAULT_INPUT = Path(
    "results/context_feature_pilot/"
    "pilot_findings.csv"
)

DEFAULT_OUTPUT = Path(
    "results/context_feature_pilot/"
    "finding_context_features_pilot.csv"
)

CORPUS_ROOT = Path(
    "dataset/main/corpus/"
    "geniac_tier_a"
)

SCHEMA = Path(
    "dataset/main/context/"
    "context_schema.yaml"
)

APPLICABILITY = Path(
    "dataset/main/context/"
    "rule_context_applicability.csv"
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


# ==========================================================
# GENERIC HELPERS
# ==========================================================

def as_bool(value):
    if pd.api.types.is_bool_dtype(type(value)):
        return bool(value)

    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"true", "false"}:
            return token == "true"

    raise ValueError(
        f"Invalid applicability Boolean value: {value!r}; "
        "expected True or False"
    )


def parse_int(value, default=1):
    try:
        return int(float(value))
    except Exception:
        return default


def load_evaluated_keys(value):

    if isinstance(value, list):
        return value

    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    try:
        x = json.loads(text)

        if isinstance(x, list):
            return x

    except Exception:
        pass

    return [text]


def statement_index_from_evaluated_keys(
    value,
):

    keys = load_evaluated_keys(value)

    for key in keys:

        m = re.search(
            r"Statement/\[(\d+)\]",
            str(key),
        )

        if m:
            return int(
                m.group(1)
            )

    return None


def strip_quoted_strings(text):
    """
    Remove quoted contents before counting braces.

    This prevents ${...} inside Terraform strings from
    corrupting brace-depth tracking.
    """

    return re.sub(
        r'"(?:\\.|[^"\\])*"',
        '""',
        text,
    )


# ==========================================================
# SOURCE HANDLING
# ==========================================================

def get_source_path(candidate_id):

    return (
        CORPUS_ROOT
        / str(candidate_id)
        / "main.tf"
    )


def read_source(path):

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def source_region(
    full_text,
    line_start,
    line_end,
):
    lines = full_text.splitlines()

    start = max(
        1,
        parse_int(
            line_start,
            1,
        ),
    )

    end = parse_int(
        line_end,
        start,
    )

    end = max(
        start,
        min(
            end,
            len(lines),
        ),
    )

    return "\n".join(
        lines[
            start - 1:end
        ]
    )


# ==========================================================
# RESOURCE ROLE
# ==========================================================

def infer_resource_role(
    resource_type,
):

    rt = str(
        resource_type
    ).strip()

    if rt.startswith(
        "aws_iam_"
    ):
        return "identity"

    if rt in {
        "aws_s3_bucket",
        "aws_db_instance",
        "aws_rds_cluster",
        "aws_rds_cluster_instance",
        "aws_dynamodb_table",
    }:
        return "primary_data"

    if rt in {
        "aws_cloudwatch_log_group",
        "aws_cloudtrail",
        "aws_flow_log",
    }:
        return "logging"

    if rt in {
        "aws_vpc",
        "aws_subnet",
        "aws_security_group",
        "aws_security_group_rule",
        "aws_vpc_security_group_ingress_rule",
        "aws_vpc_security_group_egress_rule",
        "aws_lb",
        "aws_lb_listener",
        "aws_lb_target_group",
    }:
        return "network"

    if rt in {
        "aws_instance",
        "aws_lambda_function",
        "aws_eks_cluster",
    }:
        return "compute"

    return "other"


# ==========================================================
# IAM PARSING
# ==========================================================

def extract_statement_blocks(
    text,
):
    """
    Extract object blocks inside:

        Statement = [
          { ... },
          { ... }
        ]

    The parser is deliberately narrow and deterministic.
    It is not intended to be a full HCL parser.
    """

    lines = text.splitlines()

    found_statement = False

    blocks = []

    current = []
    depth = 0

    for line in lines:

        clean = strip_quoted_strings(
            line
        )

        if not found_statement:

            if re.search(
                r"\bStatement\s*=\s*\[",
                clean,
            ):
                found_statement = True

            continue

        if not current:

            if re.match(
                r"^\s*\]",
                clean,
            ):
                break

            if "{" in clean:

                current = [line]

                depth = (
                    clean.count("{")
                    - clean.count("}")
                )

                if depth == 0:

                    blocks.append(
                        "\n".join(
                            current
                        )
                    )

                    current = []

            continue

        current.append(
            line
        )

        depth += (
            clean.count("{")
            - clean.count("}")
        )

        if depth == 0:

            blocks.append(
                "\n".join(
                    current
                )
            )

            current = []

    return blocks


def extract_assignment(
    text,
    key,
):
    """
    Extract quoted string values assigned to an HCL key.

    Supports:

        Action = "x"

        Action = [
          "x",
          "y",
        ]

    Returns:
        present
        quoted_values
        raw_assignment
    """

    lines = text.splitlines()

    values = []
    raw_parts = []

    present = False

    i = 0

    pattern = re.compile(
        rf"^\s*{re.escape(key)}\s*=\s*(.*)$"
    )

    while i < len(lines):

        line = lines[i]

        m = pattern.match(
            line
        )

        if not m:
            i += 1
            continue

        present = True

        rhs = m.group(1)

        block = [
            rhs
        ]

        clean_rhs = strip_quoted_strings(
            rhs
        )

        bracket_depth = (
            clean_rhs.count("[")
            - clean_rhs.count("]")
        )

        while (
            bracket_depth > 0
            and i + 1 < len(lines)
        ):

            i += 1

            next_line = lines[i]

            block.append(
                next_line
            )

            clean_next = (
                strip_quoted_strings(
                    next_line
                )
            )

            bracket_depth += (
                clean_next.count("[")
                - clean_next.count("]")
            )

        raw = "\n".join(
            block
        )

        raw_parts.append(
            raw
        )

        values.extend(
            re.findall(
                r'"((?:\\.|[^"\\])*)"',
                raw,
            )
        )

        i += 1

    return (
        present,
        values,
        "\n".join(
            raw_parts
        ),
    )


def contains_wildcard(
    values,
):
    return any(
        "*" in str(value)
        for value in values
    )


def action_verb(action):

    text = str(
        action
    ).strip()

    if ":" not in text:
        return text.lower()

    return (
        text.split(
            ":",
            1,
        )[1]
        .lower()
    )


WRITE_PREFIXES = (
    "create",
    "delete",
    "put",
    "update",
    "set",
    "attach",
    "detach",
    "pass",
    "run",
    "start",
    "stop",
    "terminate",
    "modify",
    "change",
    "enable",
    "disable",
    "invoke",
    "publish",
    "send",
    "write",
    "execute",
    "register",
    "deregister",
    "associate",
    "disassociate",
    "authorize",
    "revoke",
    "batchstop",
    "batchwrite",
)


PRIVILEGE_CONTROL_ACTIONS = {
    "iam:passrole",
    "iam:attachrolepolicy",
    "iam:attachuserpolicy",
    "iam:attachgrouppolicy",
    "iam:putrolepolicy",
    "iam:putuserpolicy",
    "iam:putgrouppolicy",
    "iam:createpolicy",
    "iam:createpolicyversion",
    "iam:setdefaultpolicyversion",
    "iam:updateassumerolepolicy",
    "iam:createaccesskey",
    "sts:assumerole",
}


def is_write_action(
    action,
):

    verb = action_verb(
        action
    )

    return verb.startswith(
        WRITE_PREFIXES
    )


def is_privilege_control_action(
    action,
):

    return (
        str(action)
        .strip()
        .lower()
        in PRIVILEGE_CONTROL_ACTIONS
    )


def classify_privilege_impact(
    actions,
    wildcard_action,
    wildcard_resource,
):
    """
    Frozen deterministic rubric:

    0
      No meaningful privilege impact.

    1
      Read/list or narrowly scoped operational mutation.

    2
      Explicit write/mutation/resource-control over
      wildcard or broad resource scope.

    3
      Wildcard actions or explicit identity/policy/
      role-control capabilities.

    unknown
      Relevant actions cannot be resolved.
    """

    if not actions:
        return "unknown"

    if wildcard_action == "yes":
        return "3"

    if any(
        is_privilege_control_action(
            action
        )
        for action in actions
    ):
        return "3"

    has_write = any(
        is_write_action(
            action
        )
        for action in actions
    )

    if has_write:

        if wildcard_resource == "yes":
            return "2"

        return "1"

    # Read/list/describe/get-style permissions.
    return "1"


def analyze_iam_statement(
    source_text,
    evaluated_keys,
):

    statement_index = (
        statement_index_from_evaluated_keys(
            evaluated_keys
        )
    )

    blocks = extract_statement_blocks(
        source_text
    )

    selected = source_text

    statement_resolution = (
        "whole_policy_fallback"
    )

    if (
        statement_index is not None
        and statement_index
        < len(blocks)
    ):

        selected = blocks[
            statement_index
        ]

        statement_resolution = (
            f"statement_{statement_index}"
        )

    (
        action_present,
        actions,
        action_raw,
    ) = extract_assignment(
        selected,
        "Action",
    )

    (
        resource_present,
        resources,
        resource_raw,
    ) = extract_assignment(
        selected,
        "Resource",
    )

    if not action_present:
        wildcard_action = "unknown"

    elif not actions:
        wildcard_action = "unknown"

    else:
        wildcard_action = (
            "yes"
            if contains_wildcard(
                actions
            )
            else "no"
        )

    if not resource_present:
        wildcard_resource = "unknown"

    else:

        # Resource may be an HCL reference and therefore produce
        # zero quoted values. The assignment still exists and
        # contains no wildcard syntax.
        wildcard_resource = (
            "yes"
            if contains_wildcard(
                resources
            )
            else "no"
        )

    privilege_impact = (
        classify_privilege_impact(
            actions,
            wildcard_action,
            wildcard_resource,
        )
    )

    evidence = {
        "statement_index": (
            statement_index
        ),
        "statement_resolution": (
            statement_resolution
        ),
        "actions": actions,
        "resources": resources,
        "action_assignment_present": (
            action_present
        ),
        "resource_assignment_present": (
            resource_present
        ),
        "action_raw": action_raw,
        "resource_raw": resource_raw,
    }

    return {
        "wildcard_action": (
            wildcard_action
        ),
        "wildcard_resource": (
            wildcard_resource
        ),
        "privilege_impact": (
            privilege_impact
        ),
        "evidence": evidence,
    }


# ==========================================================
# FEATURE EXTRACTION
# ==========================================================

def initialize_features(
    applicability,
    resource_type,
):

    features = {}

    for feature in FEATURES:

        applicable = as_bool(
            applicability[
                feature
            ]
        )

        features[
            feature
        ] = (
            "unknown"
            if applicable
            else "not_applicable"
        )

    # Resource role is deterministic whenever applicable.
    if as_bool(
        applicability[
            "resource_role"
        ]
    ):
        features[
            "resource_role"
        ] = infer_resource_role(
            resource_type
        )

    return features


def extract_features(
    row,
    applicability,
    source_text,
):

    check_id = str(
        row["check_id"]
    )

    features = (
        initialize_features(
            applicability,
            row["resource_type"],
        )
    )

    evidence = {
        "check_id": check_id,
        "resource": str(
            row["resource"]
        ),
    }


    # ======================================================
    # DETECTION / OBSERVABILITY
    # ======================================================

    if check_id == "CKV2_AWS_11":

        features[
            "logging_missing"
        ] = "yes"

        evidence[
            "logging"
        ] = (
            "Checkov finding confirms "
            "VPC flow logging is missing."
        )


    # ======================================================
    # S3 PUBLIC ACCESS BLOCK
    # ======================================================

    elif check_id == "CKV2_AWS_6":

        # Missing Public Access Block is not equivalent
        # to confirmed public accessibility.
        features[
            "public_access"
        ] = "unknown"

        evidence[
            "public_access"
        ] = (
            "Missing S3 Public Access Block does "
            "not prove that the bucket is public."
        )


    # ======================================================
    # LAMBDA VPC
    # ======================================================

    elif check_id == "CKV_AWS_117":

        evidence[
            "workload_isolation"
        ] = (
            "Lambda is not configured inside a VPC. "
            "No direct Internet-exposure inference "
            "is made from this fact alone."
        )


    # ======================================================
    # SUBNET AUTO PUBLIC IP
    # ======================================================

    elif check_id == "CKV_AWS_130":

        features[
            "internet_exposure"
        ] = "unknown"

        features[
            "reachability"
        ] = "unknown"

        features[
            "public_access"
        ] = "unknown"

        evidence[
            "network"
        ] = (
            "Subnet assigns public IP by default, "
            "but direct Internet reachability also "
            "depends on routing/IGW evidence."
        )


    # ======================================================
    # S3 KMS
    # ======================================================

    elif check_id == "CKV_AWS_145":

        features[
            "encryption_missing"
        ] = "yes"

        evidence[
            "encryption"
        ] = (
            "Required KMS-based default encryption "
            "control is not satisfied."
        )


    # ======================================================
    # PUBLIC HTTP INGRESS
    # ======================================================

    elif check_id == "CKV_AWS_260":

        features[
            "internet_exposure"
        ] = "yes"

        features[
            "reachability"
        ] = "internet"

        features[
            "public_access"
        ] = "yes"

        evidence[
            "network"
        ] = {
            "direction": "ingress",
            "source": "0.0.0.0/0",
            "port": 80,
        }


    # ======================================================
    # EKS PUBLIC ENDPOINT
    # ======================================================

    elif check_id == "CKV_AWS_38":

        features[
            "internet_exposure"
        ] = "yes"

        features[
            "reachability"
        ] = "internet"

        features[
            "public_access"
        ] = "yes"

        evidence[
            "network"
        ] = {
            "direction": "ingress",
            "source": "0.0.0.0/0",
            "surface": (
                "EKS public endpoint"
            ),
        }


    # ======================================================
    # UNRESTRICTED EGRESS
    # ======================================================

    elif check_id == "CKV_AWS_382":

        # The finding proves an Internet-facing outbound
        # reachability relationship, not inbound exposure.
        features[
            "internet_exposure"
        ] = "unknown"

        features[
            "reachability"
        ] = "internet"

        evidence[
            "network"
        ] = {
            "direction": "egress",
            "destination": "0.0.0.0/0",
            "protocol_scope": "unrestricted",
            "note": (
                "Outbound Internet path does not "
                "prove inbound Internet exposure."
            ),
        }


    # ======================================================
    # IAM
    # ======================================================

    elif check_id in {
        "CKV_AWS_290",
        "CKV_AWS_355",
    }:

        iam = analyze_iam_statement(
            source_text,
            row.get(
                "evaluated_keys",
                "",
            ),
        )

        features[
            "privilege_impact"
        ] = iam[
            "privilege_impact"
        ]

        if as_bool(
            applicability[
                "wildcard_action"
            ]
        ):
            features[
                "wildcard_action"
            ] = iam[
                "wildcard_action"
            ]

        if as_bool(
            applicability[
                "wildcard_resource"
            ]
        ):
            features[
                "wildcard_resource"
            ] = iam[
                "wildcard_resource"
            ]

        evidence[
            "iam"
        ] = iam[
            "evidence"
        ]


    else:

        evidence[
            "note"
        ] = (
            "No rule-specific extraction "
            "logic configured."
        )


    return (
        features,
        evidence,
    )


# ==========================================================
# SCHEMA VALIDATION
# ==========================================================

def load_allowed_values():

    with SCHEMA.open(
        encoding="utf-8",
    ) as f:

        schema = yaml.safe_load(
            f
        )

    finding_context = (
        schema[
            "finding_context"
        ]
    )

    allowed = {}

    for feature in FEATURES:

        allowed[
            feature
        ] = {
            str(v)
            for v in (
                finding_context[
                    feature
                ]["values"]
            )
        }

    return allowed


def validate_feature_values(
    features,
    allowed,
):

    errors = []

    for feature in FEATURES:

        value = str(
            features[
                feature
            ]
        )

        if value not in (
            allowed[
                feature
            ]
        ):

            errors.append(
                f"{feature}={value}"
            )

    return errors


# ==========================================================
# MAIN
# ==========================================================


def enforce_applicability(
    features,
    applicability_row,
):
    """
    Final semantic guardrail.

    Any feature marked False in the rule-context applicability
    matrix MUST be represented as 'not_applicable'.

    This function is intentionally executed after rule-specific
    extraction logic so that a rule handler cannot accidentally
    overwrite a non-applicable feature with 'unknown', 'yes',
    'no', or another value.
    """

    feature_names = [
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

    for feature in feature_names:

        if feature not in applicability_row:
            raise KeyError(
                f"Applicability matrix missing feature: "
                f"{feature}"
            )

        if not as_bool(
            applicability_row[feature]
        ):
            features[feature] = (
                "not_applicable"
            )

    return features


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=str(
            DEFAULT_INPUT
        ),
    )

    parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    )

    output_path = Path(
        args.output
    )


    df = pd.read_csv(
        input_path
    ).fillna("")


    applicability_df = (
        pd.read_csv(
            APPLICABILITY
        )
        .fillna("")
    )


    applicability_map = {
        str(row["check_id"]): row
        for _, row
        in applicability_df.iterrows()
    }

    for check_id, applicability in applicability_map.items():
        for feature in FEATURES:
            try:
                applicability[feature] = as_bool(
                    applicability[feature]
                )
            except ValueError as exc:
                raise ValueError(
                    f"{APPLICABILITY}: check_id={check_id}, "
                    f"feature={feature}: {exc}"
                ) from exc

    allowed_values = (
        load_allowed_values()
    )


    rows = []


    for _, row in df.iterrows():

        check_id = str(
            row["check_id"]
        )

        candidate_id = str(
            row["candidate_id"]
        )

        source_path = (
            get_source_path(
                candidate_id
            )
        )


        if check_id not in (
            applicability_map
        ):

            raise ValueError(
                "Missing applicability row "
                f"for {check_id}"
            )


        applicability = (
            applicability_map[
                check_id
            ]
        )


        if not source_path.exists():

            full_source = ""

            source_text = ""

            source_status = (
                "SOURCE_MISSING"
            )

        else:

            full_source = (
                read_source(
                    source_path
                )
            )

            source_text = (
                source_region(
                    full_source,
                    row.get(
                        "line_start",
                        1,
                    ),
                    row.get(
                        "line_end",
                        1,
                    ),
                )
            )

            source_status = "OK"


        (
            features,
            evidence,
        ) = extract_features(
            row,
            applicability,
            source_text,
        )


        # ==================================================
        # FINAL APPLICABILITY ENFORCEMENT
        # ==================================================
        #
        # The applicability matrix is the final authority.
        # Any feature marked False must become
        # "not_applicable" before validation, unknown
        # counting, and output generation.
        #
        features = enforce_applicability(
            features,
            applicability,
        )


        validation_errors = (
            validate_feature_values(
                features,
                allowed_values,
            )
        )


        if validation_errors:

            extraction_status = (
                "SCHEMA_VALUE_ERROR"
            )

        elif source_status != "OK":

            extraction_status = (
                source_status
            )

        else:

            extraction_status = (
                "EXTRACTED"
            )


        applicable_unknowns = []

        for feature in FEATURES:

            if (
                as_bool(
                    applicability[
                        feature
                    ]
                )
                and str(
                    features[
                        feature
                    ]
                ) == "unknown"
            ):
                applicable_unknowns.append(
                    feature
                )


        out = {
            "finding_id": (
                row["finding_id"]
            ),
            "candidate_id": (
                candidate_id
            ),
            "scenario_id": (
                row["scenario_id"]
            ),
            "check_id": (
                check_id
            ),
            "check_name": (
                row.get(
                    "check_name",
                    "",
                )
            ),
            "resource": (
                row["resource"]
            ),
            "resource_type": (
                row["resource_type"]
            ),
            "source_path": str(
                source_path
            ),
            "line_start": (
                row.get(
                    "line_start",
                    "",
                )
            ),
            "line_end": (
                row.get(
                    "line_end",
                    "",
                )
            ),
            "evaluated_keys": (
                row.get(
                    "evaluated_keys",
                    "",
                )
            ),
        }


        out.update(
            features
        )


        out.update({
            "feature_extraction_status": (
                extraction_status
            ),
            "schema_validation_errors": (
                "|".join(
                    validation_errors
                )
            ),
            "applicable_unknown_count": (
                len(
                    applicable_unknowns
                )
            ),
            "applicable_unknown_features": (
                "|".join(
                    applicable_unknowns
                )
            ),
            "feature_evidence": (
                json.dumps(
                    evidence,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ),
        })


        rows.append(
            out
        )


    result = pd.DataFrame(
        rows
    )


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    result.to_csv(
        output_path,
        index=False,
    )


    print("==============================")
    print("PILOT CONTEXT FEATURE EXTRACTION")
    print("==============================")

    print(
        "Input rows =",
        len(df),
    )

    print(
        "Output rows =",
        len(result),
    )

    print(
        "Unique finding IDs =",
        result[
            "finding_id"
        ].nunique(),
    )

    print(
        "Rules =",
        result[
            "check_id"
        ].nunique(),
    )

    print()

    print("=== EXTRACTION STATUS ===")

    print(
        result[
            "feature_extraction_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()

    print("=== UNKNOWN COUNTS ===")

    print(
        result[
            "applicable_unknown_count"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()

    print("=== FEATURE DISTRIBUTIONS ===")

    for feature in FEATURES:

        print()
        print(
            f"[{feature}]"
        )

        print(
            result[
                feature
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    print()

    print(
        "Output =",
        output_path,
    )


if __name__ == "__main__":
    main()
