from pathlib import Path
import pandas as pd
import re


SUMMARY = Path(
    "results/source_corpus/"
    "geniac_validation/"
    "validation_summary.csv"
)

LOG_DIR = Path(
    "results/source_corpus/"
    "geniac_validation"
)

OUT = Path(
    "results/source_corpus/"
    "geniac_validation/"
    "failure_classification.csv"
)


df = pd.read_csv(SUMMARY)


PATTERNS = [
    (
        "PROVIDER_RESOLUTION",
        [
            r"failed to query available provider packages",
            r"could not retrieve the list of available versions",
            r"no available releases match",
            r"failed to install provider",
            r"provider registry",
        ],
    ),

    (
        "MODULE_RESOLUTION",
        [
            r"module not installed",
            r"failed to download module",
            r"failed to retrieve module",
            r"unreadable module directory",
        ],
    ),

    (
        "SYNTAX_PARSE",
        [
            r"argument or block definition required",
            r"invalid expression",
            r"invalid character",
            r"missing newline after argument",
            r"unclosed configuration block",
            r"unterminated",
            r"unexpected token",
            r"invalid block definition",
        ],
    ),

    (
        "UNDECLARED_REFERENCE",
        [
            r"reference to undeclared",
            r"undeclared input variable",
            r"undeclared resource",
            r"undeclared local value",
            r"undeclared module",
        ],
    ),

    (
        "UNSUPPORTED_ARGUMENT",
        [
            r"unsupported argument",
        ],
    ),

    (
        "UNSUPPORTED_BLOCK",
        [
            r"unsupported block type",
            r"blocks of type .* are not expected here",
        ],
    ),

    (
        "MISSING_REQUIRED_ARGUMENT",
        [
            r"missing required argument",
            r"required attribute",
        ],
    ),

    (
        "DUPLICATE_DECLARATION",
        [
            r"duplicate resource",
            r"duplicate variable",
            r"duplicate output",
            r"duplicate local",
            r"duplicate provider",
        ],
    ),

    (
        "TYPE_OR_VALUE_ERROR",
        [
            r"incorrect attribute value type",
            r"invalid value for",
            r"invalid function argument",
            r"unsuitable value",
            r"attribute .* must",
        ],
    ),

    (
        "PROVIDER_SCHEMA",
        [
            r"invalid resource type",
            r"provider .* does not support resource type",
            r"failed to load plugin schemas",
        ],
    ),
]


def classify(text):
    low = text.lower()

    matches = []

    for category, patterns in PATTERNS:
        if any(
            re.search(p, low, re.I)
            for p in patterns
        ):
            matches.append(category)

    if not matches:
        return "OTHER"

    return "|".join(matches)


def first_error(text):
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if line.strip().startswith("Error:"):
            block = lines[i:i + 8]
            return "\n".join(block)

    return "\n".join(lines[:8])


records = []


for _, row in df.iterrows():

    if row["status"] == "PASS":
        continue

    cid = row["candidate_id"]

    if row["status"] == "INIT_FAILED":
        log_path = (
            LOG_DIR /
            f"{cid}_init.log"
        )
    else:
        log_path = (
            LOG_DIR /
            f"{cid}_validate.log"
        )

    if log_path.exists():
        text = log_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    else:
        text = ""

    records.append({
        "candidate_id": cid,
        "status": row["status"],
        "failure_class": classify(text),
        "first_error": first_error(text),
        "log_path": str(log_path),
    })


out = pd.DataFrame(records)

out.to_csv(
    OUT,
    index=False,
)


print("==============================")
print("FAILURE CLASSIFICATION")
print("==============================")

print()
print("Total failures =", len(out))

print()
print("=== STATUS ===")
print(
    out["status"]
    .value_counts()
    .to_string()
)

print()
print("=== FAILURE CLASS ===")
print(
    out["failure_class"]
    .value_counts()
    .to_string()
)

print()
print("=== STATUS x CLASS ===")
print(
    pd.crosstab(
        out["status"],
        out["failure_class"],
    ).to_string()
)

print()
print("Output =", OUT)
