from pathlib import Path
import pandas as pd
import hcl2


PARSE_CSV = Path(
    "results/source_corpus/"
    "geniac_validation/"
    "hcl_parse_summary.csv"
)

VALIDATION_CSV = Path(
    "results/source_corpus/"
    "geniac_hcl_validation/"
    "validation_summary.csv"
)

OUT = Path(
    "results/source_corpus/"
    "geniac_hcl_validation/"
    "structure_summary.csv"
)


parse_df = pd.read_csv(PARSE_CSV)

parse_df = parse_df[
    parse_df["hcl_parse_ok"] == True
].copy()


validation = pd.read_csv(
    VALIDATION_CSV
)


records = []


for _, row in parse_df.iterrows():

    path = Path(
        row["artifact_path"]
    )

    candidate_id = (
        f'{row["complexity"]}'
        f'__{row["model"]}'
        f'__{row["scenario_id"]}'
    )

    raw = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    file_size = len(
        raw.encode(
            "utf-8",
            errors="replace",
        )
    )

    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as f:
            obj = hcl2.load(f)

        parser_ok = True

    except Exception as e:
        obj = {}
        parser_ok = False

    def count_blocks(name):
        value = obj.get(
            name,
            []
        )

        if isinstance(value, list):
            return len(value)

        if isinstance(value, dict):
            return len(value)

        return 0

    resource_blocks = count_blocks(
        "resource"
    )

    module_blocks = count_blocks(
        "module"
    )

    data_blocks = count_blocks(
        "data"
    )

    provider_blocks = count_blocks(
        "provider"
    )

    terraform_blocks = count_blocks(
        "terraform"
    )

    variable_blocks = count_blocks(
        "variable"
    )

    output_blocks = count_blocks(
        "output"
    )

    local_blocks = count_blocks(
        "locals"
    )

    deployable_surface = (
        resource_blocks > 0
        or module_blocks > 0
    )

    meaningful_hcl = (
        file_size > 0
        and (
            resource_blocks > 0
            or module_blocks > 0
            or data_blocks > 0
            or provider_blocks > 0
            or terraform_blocks > 0
            or variable_blocks > 0
            or output_blocks > 0
            or local_blocks > 0
        )
    )

    records.append({
        "candidate_id": candidate_id,
        "scenario_id": row["scenario_id"],
        "complexity": row["complexity"],
        "model": row["model"],
        "artifact_path": str(path),

        "file_size_bytes": file_size,

        "python_hcl2_parse_ok": (
            parser_ok
        ),

        "resource_blocks": (
            resource_blocks
        ),

        "module_blocks": (
            module_blocks
        ),

        "data_blocks": (
            data_blocks
        ),

        "provider_blocks": (
            provider_blocks
        ),

        "terraform_blocks": (
            terraform_blocks
        ),

        "variable_blocks": (
            variable_blocks
        ),

        "output_blocks": (
            output_blocks
        ),

        "local_blocks": (
            local_blocks
        ),

        "meaningful_hcl": (
            meaningful_hcl
        ),

        "deployable_surface": (
            deployable_surface
        ),
    })


structure = pd.DataFrame(
    records
)


merged = structure.merge(
    validation[
        [
            "candidate_id",
            "status",
            "init_exit_code",
            "validate_exit_code",
        ]
    ],
    on="candidate_id",
    how="left",
)


merged.to_csv(
    OUT,
    index=False,
)


print("==============================")
print("GENIAC STRUCTURE AUDIT")
print("==============================")

print(
    "Rows =",
    len(merged),
)

print()

print("=== FILE SIZE ===")

print(
    "Empty files =",
    (merged["file_size_bytes"] == 0).sum()
)

print()

print("=== MEANINGFUL HCL ===")

print(
    merged[
        "meaningful_hcl"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)

print()

print("=== DEPLOYABLE SURFACE ===")

print(
    merged[
        "deployable_surface"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)

print()

print(
    "=== VALIDATION x DEPLOYABLE SURFACE ==="
)

print(
    pd.crosstab(
        merged["status"],
        merged["deployable_surface"],
    ).to_string()
)

print()

print("=== EMPTY / NO SURFACE ===")

x = merged[
    (merged["file_size_bytes"] == 0)
    | (~merged["deployable_surface"])
]

print(
    x[
        [
            "candidate_id",
            "file_size_bytes",
            "resource_blocks",
            "module_blocks",
            "data_blocks",
            "status",
        ]
    ].to_string(
        index=False
    )
)

print()
print("Output =", OUT)
