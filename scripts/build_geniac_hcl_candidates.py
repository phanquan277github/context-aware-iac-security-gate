from pathlib import Path
import pandas as pd
import shutil


PARSE = Path(
    "results/source_corpus/"
    "geniac_validation/"
    "hcl_parse_summary.csv"
)

OUT = Path(
    "dataset/main/candidates/geniac_hcl"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


df = pd.read_csv(PARSE)

selected = df[
    df["hcl_parse_ok"] == True
].copy()


count = 0


for _, row in selected.iterrows():

    source = Path(
        row["artifact_path"]
    )

    candidate_id = (
        f'{row["complexity"]}'
        f'__{row["model"]}'
        f'__{row["scenario_id"]}'
    )

    dest = OUT / candidate_id

    dest.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        dest / "main.tf",
    )

    count += 1


print(
    "Copied HCL-parseable candidates =",
    count,
)

print(
    "Destination =",
    OUT,
)
