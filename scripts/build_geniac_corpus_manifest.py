from pathlib import Path
import hashlib
import shutil
import pandas as pd


INVENTORY = Path(
    "results/source_corpus/"
    "geniac_aws_candidate_inventory.csv"
)

HCL_PARSE = Path(
    "results/source_corpus/"
    "geniac_validation/"
    "hcl_parse_summary.csv"
)

STRUCTURE = Path(
    "results/source_corpus/"
    "geniac_hcl_validation/"
    "structure_summary.csv"
)

VALIDATION = Path(
    "results/source_corpus/"
    "geniac_hcl_validation/"
    "validation_summary.csv"
)

OUT_MANIFEST = Path(
    "dataset/main/manifests/"
    "geniac_corpus_manifest.csv"
)

TIER_A_DIR = Path(
    "dataset/main/corpus/"
    "geniac_tier_a"
)

EXTENDED_DIR = Path(
    "dataset/main/corpus/"
    "geniac_extended"
)


def bool_value(x):
    if pd.isna(x):
        return False

    if isinstance(x, bool):
        return x

    return str(x).strip().lower() == "true"


def sha256_file(path):
    path = Path(path)

    if not path.exists():
        return ""

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def make_candidate_id(row):
    return (
        f'{row["complexity"]}'
        f'__{row["model"]}'
        f'__{row["scenario_id"]}'
    )


inventory = pd.read_csv(
    INVENTORY
).fillna("")

inventory["candidate_id"] = inventory.apply(
    make_candidate_id,
    axis=1,
)


hcl = pd.read_csv(
    HCL_PARSE
).fillna("")

hcl["candidate_id"] = hcl.apply(
    make_candidate_id,
    axis=1,
)


structure = pd.read_csv(
    STRUCTURE
).fillna("")


validation = pd.read_csv(
    VALIDATION
).fillna("")


# ----------------------------------------------------------
# MERGE
# ----------------------------------------------------------

df = inventory.merge(
    hcl[
        [
            "candidate_id",
            "hcl_parse_ok",
            "fmt_exit_code",
        ]
    ],
    on="candidate_id",
    how="left",
)

df = df.merge(
    structure[
        [
            "candidate_id",
            "file_size_bytes",
            "python_hcl2_parse_ok",
            "resource_blocks",
            "module_blocks",
            "data_blocks",
            "provider_blocks",
            "terraform_blocks",
            "variable_blocks",
            "output_blocks",
            "local_blocks",
            "meaningful_hcl",
            "deployable_surface",
        ]
    ],
    on="candidate_id",
    how="left",
)

df = df.merge(
    validation[
        [
            "candidate_id",
            "init_exit_code",
            "validate_exit_code",
            "status",
        ]
    ],
    on="candidate_id",
    how="left",
)


# ----------------------------------------------------------
# CLASSIFY
# ----------------------------------------------------------

tiers = []
reasons = []
include_eval = []
include_extended = []


for _, row in df.iterrows():

    detected_format = str(
        row.get(
            "detected_format",
            "",
        )
    ).lower()

    hcl_ok = bool_value(
        row.get(
            "hcl_parse_ok",
            False,
        )
    )

    surface = bool_value(
        row.get(
            "deployable_surface",
            False,
        )
    )

    status = str(
        row.get(
            "status",
            "",
        )
    )

    if detected_format != "terraform":

        tier = "WRONG_FORMAT"

        reason = (
            "Upstream labelled as Terraform, "
            f"but detected format is "
            f"{detected_format or 'unknown'}."
        )

        eval_ok = False
        ext_ok = False

    elif not hcl_ok:

        tier = "MALFORMED_HCL"

        reason = (
            "Artifact is .tf but Terraform "
            "HCL parsing did not succeed."
        )

        eval_ok = False
        ext_ok = False

    elif not surface:

        tier = "NON_ACTIONABLE_HCL"

        reason = (
            "HCL is parseable but contains "
            "no resource or module surface "
            "for security analysis."
        )

        eval_ok = False
        ext_ok = False

    elif status == "PASS":

        tier = "TIER_A_CLEAN"

        reason = (
            "HCL parse passed, resource/module "
            "surface exists, terraform init "
            "passed, and terraform validate passed."
        )

        eval_ok = True
        ext_ok = True

    elif status in {
        "INIT_FAILED",
        "VALIDATE_FAILED",
    }:

        tier = (
            "TIER_B_ANALYZABLE_WITH_ERRORS"
        )

        reason = (
            "HCL is parseable and contains "
            "resource/module surface, but "
            f"validation status is {status}."
        )

        eval_ok = False
        ext_ok = True

    else:

        tier = "REVIEW_REQUIRED"

        reason = (
            "Artifact did not match a known "
            "corpus classification rule."
        )

        eval_ok = False
        ext_ok = False

    tiers.append(tier)
    reasons.append(reason)
    include_eval.append(eval_ok)
    include_extended.append(ext_ok)


df["corpus_tier"] = tiers
df["exclusion_or_tier_reason"] = reasons

df["include_main_evaluation"] = (
    include_eval
)

df["include_extended_corpus"] = (
    include_extended
)


# ----------------------------------------------------------
# HASH SOURCE ARTIFACT
# ----------------------------------------------------------

df["sha256"] = df[
    "artifact_path"
].apply(
    lambda x: sha256_file(x)
    if x
    else ""
)


# ----------------------------------------------------------
# COPY FROZEN CORPORA
# ----------------------------------------------------------

for directory in [
    TIER_A_DIR,
    EXTENDED_DIR,
]:
    if directory.exists():
        shutil.rmtree(directory)

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


tier_a_count = 0
extended_count = 0


for _, row in df.iterrows():

    source = Path(
        row["artifact_path"]
    )

    if not source.exists():
        continue

    candidate_id = (
        row["candidate_id"]
    )

    if bool_value(
        row["include_main_evaluation"]
    ):

        dest = (
            TIER_A_DIR
            / candidate_id
        )

        dest.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            dest / "main.tf",
        )

        tier_a_count += 1

    if bool_value(
        row["include_extended_corpus"]
    ):

        dest = (
            EXTENDED_DIR
            / candidate_id
        )

        dest.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            dest / "main.tf",
        )

        extended_count += 1


# ----------------------------------------------------------
# WRITE MANIFEST
# ----------------------------------------------------------

preferred_columns = [
    "candidate_id",
    "scenario_id",
    "complexity",
    "model",
    "model_mode",

    "artifact_path",

    "source_iac_format",
    "detected_format",
    "format_match",

    "terraform_like",
    "hcl_parse_ok",
    "fmt_exit_code",

    "file_size_bytes",
    "python_hcl2_parse_ok",

    "resource_blocks",
    "module_blocks",
    "data_blocks",
    "provider_blocks",
    "terraform_blocks",
    "variable_blocks",
    "output_blocks",
    "local_blocks",

    "meaningful_hcl",
    "deployable_surface",

    "init_exit_code",
    "validate_exit_code",
    "status",

    "corpus_tier",

    "include_main_evaluation",
    "include_extended_corpus",

    "exclusion_or_tier_reason",

    "sha256",
]


columns = [
    c
    for c in preferred_columns
    if c in df.columns
]

remaining = [
    c
    for c in df.columns
    if c not in columns
]

df = df[
    columns + remaining
]


OUT_MANIFEST.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUT_MANIFEST,
    index=False,
)


# ----------------------------------------------------------
# ASSERT EXPECTED COUNTS
# ----------------------------------------------------------

counts = (
    df["corpus_tier"]
    .value_counts()
)


print()
print("==============================")
print("GENIAC CORPUS MANIFEST")
print("==============================")

print(
    "Total upstream records =",
    len(df),
)

print()

print("=== CORPUS TIERS ===")
print(
    counts.to_string()
)

print()

print(
    "Main evaluation corpus =",
    int(
        df[
            "include_main_evaluation"
        ].sum()
    ),
)

print(
    "Extended corpus =",
    int(
        df[
            "include_extended_corpus"
        ].sum()
    ),
)

print()

print(
    "Copied Tier A =",
    tier_a_count,
)

print(
    "Copied Extended =",
    extended_count,
)

print()

print(
    "Manifest =",
    OUT_MANIFEST,
)


# Expected from current audit
expected = {
    "TIER_A_CLEAN": 109,
    "TIER_B_ANALYZABLE_WITH_ERRORS": 60,
    "NON_ACTIONABLE_HCL": 2,
    "MALFORMED_HCL": 33,
    "WRONG_FORMAT": 36,
}

print()
print("=== EXPECTED COUNT CHECK ===")

all_ok = True

for tier, expected_count in expected.items():

    actual = int(
        counts.get(
            tier,
            0,
        )
    )

    ok = actual == expected_count

    print(
        tier,
        "| expected =",
        expected_count,
        "| actual =",
        actual,
        "|",
        "OK" if ok else "MISMATCH",
    )

    if not ok:
        all_ok = False


review_count = int(
    counts.get(
        "REVIEW_REQUIRED",
        0,
    )
)

print(
    "REVIEW_REQUIRED =",
    review_count,
)


if not all_ok or review_count != 0:
    raise SystemExit(
        "Manifest count validation failed."
    )


print()
print(
    "Corpus manifest validation: PASS"
)
