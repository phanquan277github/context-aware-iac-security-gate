from pathlib import Path
import hashlib
import json
import re

import pandas as pd


RAW = Path(
    "results/security_scans/checkov/"
    "geniac_tier_a/findings_raw.csv"
)

SUMMARY = Path(
    "results/security_scans/checkov/"
    "geniac_tier_a/scan_summary.csv"
)

MANIFEST = Path(
    "dataset/main/manifests/"
    "geniac_corpus_manifest.csv"
)

OUT = Path(
    "dataset/main/findings/"
    "geniac_tier_a_checkov.csv"
)


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def stable_hash(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def parse_line_range(value):
    try:
        x = json.loads(
            clean(value)
        )

        if isinstance(x, list) and len(x) >= 2:
            return int(x[0]), int(x[1])

    except Exception:
        pass

    return None, None


def extract_resource_type(resource):
    """
    Extract Terraform AWS resource type from strings such as:
      aws_s3_bucket.logs
      module.foo.aws_security_group.bar
    """

    resource = clean(resource)

    match = re.search(
        r"(aws_[A-Za-z0-9_]+)",
        resource,
    )

    if match:
        return match.group(1)

    if resource.startswith("module."):
        return "module"

    if resource.startswith("data."):
        return "data"

    return ""


def extract_resource_name(resource):
    resource = clean(resource)

    if not resource:
        return ""

    parts = resource.split(".")

    if len(parts) >= 2:
        return parts[-1]

    return resource


raw = pd.read_csv(
    RAW
).fillna("")

summary = pd.read_csv(
    SUMMARY
).fillna("")

manifest = pd.read_csv(
    MANIFEST
).fillna("")


manifest = manifest[
    manifest[
        "include_main_evaluation"
    ].astype(str).str.lower().eq("true")
].copy()


# ---------------------------------------------------------
# ATTACH ARTIFACT METADATA
# ---------------------------------------------------------

artifact_meta = summary[
    [
        "candidate_id",
        "resource_count",
        "passed_checks",
        "failed_checks",
        "parsing_errors",
        "scan_status",
    ]
].copy()


df = raw.merge(
    artifact_meta,
    on="candidate_id",
    how="left",
)


manifest_cols = [
    "candidate_id",
    "corpus_tier",
    "file_size_bytes",
    "resource_blocks",
    "module_blocks",
    "data_blocks",
]

available = [
    c for c in manifest_cols
    if c in manifest.columns
]


df = df.merge(
    manifest[available],
    on="candidate_id",
    how="left",
)


# ---------------------------------------------------------
# NORMALIZE RESOURCE
# ---------------------------------------------------------

df["resource_type"] = (
    df["resource"]
    .apply(extract_resource_type)
)

df["resource_name"] = (
    df["resource"]
    .apply(extract_resource_name)
)


# ---------------------------------------------------------
# NORMALIZE LINES
# ---------------------------------------------------------

ranges = df[
    "file_line_range"
].apply(parse_line_range)

df["line_start"] = [
    x[0] for x in ranges
]

df["line_end"] = [
    x[1] for x in ranges
]


# ---------------------------------------------------------
# POLICY FAMILY
# ---------------------------------------------------------

def policy_namespace(check_id):
    check_id = clean(check_id)

    if check_id.startswith("CKV2_"):
        return "CKV2"

    if check_id.startswith("CKV_"):
        return "CKV"

    return "OTHER"


df["check_namespace"] = (
    df["check_id"]
    .apply(policy_namespace)
)


# ---------------------------------------------------------
# STABLE IDENTITIES
# ---------------------------------------------------------

df["artifact_resource_id"] = (
    df.apply(
        lambda r: stable_hash(
            "|".join([
                clean(r["candidate_id"]),
                clean(r["resource"]),
            ])
        ),
        axis=1,
    )
)


df["finding_id"] = (
    df.apply(
        lambda r: stable_hash(
            "|".join([
                clean(r["candidate_id"]),
                clean(r["check_id"]),
                clean(r["resource"]),
                clean(r["file_path"]),
                clean(r["file_line_range"]),
            ])
        ),
        axis=1,
    )
)


# ---------------------------------------------------------
# IMPORTANT:
# scanner severity remains provenance only.
# Do NOT manufacture missing severity.
# ---------------------------------------------------------

df["scanner_severity"] = (
    df["severity"]
)

df["scanner_severity_available"] = (
    df["scanner_severity"]
    .astype(str)
    .str.strip()
    .ne("")
)


# ---------------------------------------------------------
# PLACEHOLDERS FOR FUTURE STAGES
# ---------------------------------------------------------

df["context_variant_id"] = ""
df["risk_label"] = ""
df["risk_score"] = ""


# ---------------------------------------------------------
# COLUMN ORDER
# ---------------------------------------------------------

preferred = [
    "finding_id",
    "artifact_resource_id",

    "candidate_id",
    "scenario_id",
    "complexity",
    "model",
    "artifact_sha256",

    "check_id",
    "check_namespace",
    "check_name",

    "resource",
    "resource_type",
    "resource_name",

    "file_path",
    "line_start",
    "line_end",

    "check_result",

    "scanner",
    "scanner_version",

    "scanner_severity",
    "scanner_severity_available",

    "resource_count",
    "failed_checks",
    "passed_checks",
    "parsing_errors",
    "scan_status",

    "corpus_tier",

    "guideline",
    "evaluated_keys",

    "context_variant_id",
    "risk_label",
    "risk_score",
]


columns = [
    c for c in preferred
    if c in df.columns
]

remaining = [
    c for c in df.columns
    if c not in columns
]

df = df[
    columns + remaining
]


# ---------------------------------------------------------
# ASSERTIONS
# ---------------------------------------------------------

assert len(df) == len(raw)

assert df["finding_id"].nunique() == len(df)

assert (
    df["candidate_id"]
    .astype(str)
    .str.strip()
    .ne("")
    .all()
)

assert (
    df["check_id"]
    .astype(str)
    .str.strip()
    .ne("")
    .all()
)

assert (
    df["resource"]
    .astype(str)
    .str.strip()
    .ne("")
    .all()
)

assert (
    df["scan_status"]
    .eq("SCAN_OK")
    .all()
)


OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUT,
    index=False,
)


print("==============================")
print("NORMALIZED CHECKOV FINDINGS")
print("==============================")

print("Rows =", len(df))
print(
    "Unique finding IDs =",
    df["finding_id"].nunique(),
)

print(
    "Artifacts =",
    df["candidate_id"].nunique(),
)

print(
    "Artifact resources with findings =",
    df["artifact_resource_id"].nunique(),
)

print(
    "Check IDs =",
    df["check_id"].nunique(),
)

print(
    "Resource types =",
    df[
        df["resource_type"] != ""
    ]["resource_type"].nunique(),
)

print(
    "Severity available =",
    int(
        df[
            "scanner_severity_available"
        ].sum()
    ),
)

print()
print("Output =", OUT)
