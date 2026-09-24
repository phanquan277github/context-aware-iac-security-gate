from pathlib import Path
import csv
import shutil
import yaml

PROJECT = Path(".")
POOL_PATH = PROJECT / "results" / "seed_pool_inventory.csv"
SELECT_PATH = PROJECT / "results" / "contrastive_seed_selection.csv"
AI_ROOT = PROJECT / "dataset" / "main" / "candidates" / "ai_generated"
ROOT = PROJECT / "dataset" / "main" / "contrastive"

with POOL_PATH.open(newline="", encoding="utf-8-sig") as f:
    pool = {
        r["seed_id"]: r
        for r in csv.DictReader(f)
    }

with SELECT_PATH.open(newline="", encoding="utf-8") as f:
    selection = list(csv.DictReader(f))

ROOT.mkdir(parents=True, exist_ok=True)

CONTEXT_A = {
    "context_variant": "A",
    "environment": "dev",
    "asset_criticality": "low",
    "data_sensitivity": "low",
}

CONTEXT_B = {
    "context_variant": "B",
    "environment": "prod",
    "asset_criticality": "high",
    "data_sensitivity": "high",
}

for row in selection:
    family_id = row["family_id"]
    seed_id = row["base_seed_id"]

    if seed_id not in pool:
        raise RuntimeError(
            f"{seed_id}: not found in seed pool"
        )

    seed = pool[seed_id]
    artifact_rel = Path(seed["artifact_path"])

    # AI candidates use paths relative to
    # dataset/main/candidates/ai_generated/
    if seed["source_id"] == "SRC-04":
        artifact = AI_ROOT / artifact_rel

    # External candidates already use project-relative paths.
    else:
        artifact = artifact_rel

    if not artifact.exists():
        raise RuntimeError(
            f"{seed_id}: artifact does not exist:\n{artifact}"
        )

    family_root = ROOT / family_id
    a_dir = family_root / "context_a"
    b_dir = family_root / "context_b"

    if family_root.exists():
        shutil.rmtree(family_root)

    a_dir.mkdir(parents=True)
    b_dir.mkdir(parents=True)

    # Copy Terraform source only.
    if artifact.is_file():
        if artifact.suffix != ".tf":
            raise RuntimeError(
                f"{seed_id}: expected .tf file, got {artifact}"
            )

        shutil.copy2(
            artifact,
            a_dir / artifact.name
        )

        shutil.copy2(
            artifact,
            b_dir / artifact.name
        )

    elif artifact.is_dir():
        tf_files = sorted(
            artifact.glob("*.tf")
        )

        if not tf_files:
            raise RuntimeError(
                f"{seed_id}: no root-level Terraform files in {artifact}"
            )

        for tf in tf_files:
            shutil.copy2(
                tf,
                a_dir / tf.name
            )

            shutil.copy2(
                tf,
                b_dir / tf.name
            )

    else:
        raise RuntimeError(
            f"{seed_id}: unsupported artifact type: {artifact}"
        )

    context_a = {
        "family_id": family_id,
        "scenario_id": f"{family_id}-A",
        "base_seed_id": seed_id,
        **CONTEXT_A,
    }

    context_b = {
        "family_id": family_id,
        "scenario_id": f"{family_id}-B",
        "base_seed_id": seed_id,
        **CONTEXT_B,
    }

    with (
        a_dir / "context.yaml"
    ).open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            context_a,
            f,
            sort_keys=False,
            allow_unicode=True,
        )

    with (
        b_dir / "context.yaml"
    ).open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            context_b,
            f,
            sort_keys=False,
            allow_unicode=True,
        )

    print(
        family_id,
        "| seed=", seed_id,
        "| source=", seed["source_id"],
    )

print(f"\nFamilies created: {len(selection)}")
