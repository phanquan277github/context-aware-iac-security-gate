from pathlib import Path
import csv
import re

ROOT = Path(
    "dataset/main/sources/geniac-secbench/generated"
)

OUT = Path(
    "results/source_corpus/geniac_aws_terraform_inventory.csv"
)

rows = []

for p in sorted(ROOT.rglob("main.tf")):
    path_str = p.as_posix()

    if (
        "/aws-tf-" not in path_str
        and "/complex-aws-tf-" not in path_str
    ):
        continue

    parts = p.parts

    try:
        idx = parts.index("generated")

        complexity = parts[idx + 1]
        model = parts[idx + 2]
        scenario_id = parts[idx + 3]

    except (ValueError, IndexError):
        continue

    text = p.read_text(
        encoding="utf-8",
        errors="replace",
    )

    has_terraform_block = bool(
        re.search(
            r"\bterraform\s*\{",
            text
        )
    )

    has_terraform_resource = bool(
        re.search(
            r'\bresource\s+"[^"]+"\s+"[^"]+"\s*\{',
            text
        )
    )

    has_aws_provider = bool(
        re.search(
            r'hashicorp/aws',
            text
        )
        or re.search(
            r'\bprovider\s+"aws"\s*\{',
            text
        )
        or re.search(
            r'\bresource\s+"aws_[^"]+"',
            text
        )
    )

    cloudformation_like = bool(
        re.search(
            r"AWSTemplateFormatVersion|"
            r"^\s*Resources\s*:",
            text,
            re.MULTILINE,
        )
    )

    terraform_like = (
        has_terraform_resource
        and has_aws_provider
        and not cloudformation_like
    )

    rows.append({
        "source_dataset": "GenIaC-SecBench",
        "complexity": complexity,
        "model": model,
        "scenario_id": scenario_id,
        "artifact_path": path_str,
        "has_terraform_block": has_terraform_block,
        "has_terraform_resource": has_terraform_resource,
        "has_aws_provider": has_aws_provider,
        "cloudformation_like": cloudformation_like,
        "terraform_like": terraform_like,
        "local_validation": "PENDING",
        "checkov_failed": "",
        "candidate_status": "UNSCREENED",
    })


OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

fieldnames = list(rows[0].keys())

with OUT.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(rows)


print("Total AWS-named main.tf =", len(rows))

print(
    "Terraform-like =",
    sum(
        r["terraform_like"]
        for r in rows
    ),
)

print(
    "CloudFormation-like mislabeled .tf =",
    sum(
        r["cloudformation_like"]
        for r in rows
    ),
)

print("Output =", OUT)
