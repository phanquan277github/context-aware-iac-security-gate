from pathlib import Path
import pandas as pd
import subprocess
import tempfile
import shutil


INV = Path(
    "results/source_corpus/"
    "geniac_aws_terraform_inventory.csv"
)

OUT = Path(
    "results/source_corpus/"
    "geniac_validation/"
    "hcl_parse_summary.csv"
)


def decode(data):
    if data is None:
        return ""

    if isinstance(data, str):
        return data

    return data.decode(
        "utf-8",
        errors="replace",
    )


df = pd.read_csv(INV)

records = []


for i, row in df.iterrows():

    source = Path(
        row["artifact_path"]
    )

    print(
        f"[{i + 1}/{len(df)}] "
        f"{row['complexity']} | "
        f"{row['model']} | "
        f"{row['scenario_id']}"
    )

    with tempfile.TemporaryDirectory() as td:

        td = Path(td)

        target = td / "main.tf"

        shutil.copy2(
            source,
            target,
        )

        try:

            result = subprocess.run(
                [
                    "terraform",
                    "fmt",
                    "-check",
                    "-no-color",
                    "main.tf",
                ],
                cwd=td,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                timeout=30,
            )

            rc = result.returncode

            output = decode(
                result.stdout
            )

            parse_ok = (
                rc in [0, 3]
            )

        except subprocess.TimeoutExpired as e:

            rc = 124
            output = (
                decode(e.stdout)
                + "\nTIMEOUT"
            )
            parse_ok = False

        except Exception as e:

            rc = 125
            output = repr(e)
            parse_ok = False

    records.append({
        "scenario_id": row["scenario_id"],
        "complexity": row["complexity"],
        "model": row["model"],
        "artifact_path": row["artifact_path"],
        "terraform_like": row["terraform_like"],
        "fmt_exit_code": rc,
        "hcl_parse_ok": parse_ok,
        "fmt_output": output[:2000],
    })


out = pd.DataFrame(records)

out.to_csv(
    OUT,
    index=False,
)


print()
print("==============================")
print("HCL PARSE CHECK")
print("==============================")

print("Rows =", len(out))

print()

print(
    out["hcl_parse_ok"]
    .value_counts(dropna=False)
    .to_string()
)

print()
print("=== heuristic x HCL ===")

print(
    pd.crosstab(
        out["terraform_like"],
        out["hcl_parse_ok"],
    ).to_string()
)

print()
print("Output =", OUT)
