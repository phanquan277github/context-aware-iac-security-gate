"""Build the D-014 artifact-level Tier-3 scope from frozen Feature Spec v1.0."""

import argparse
from collections import defaultdict
import csv
import hashlib
import io
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "results/main_context_features/features_v1.csv"
MANIFEST = ROOT / "dataset/main/manifests/phase4_tier3_scope_v1.csv"
FROZEN_SHA256 = "67295a1742a01a77dd35a3a817e591a6206356a963f5fe46edae6481b6ac9164"
SELECTION_RULE = "artifact_finding_count >= 3"
FIELDS = (
    "source_id", "source_task_id", "family_id", "artifact_id",
    "candidate_id", "finding_count", "selected", "selection_rule",
    "feature_spec_version", "features_v1_sha256", "finding_ids_sha256",
)
REQUIRED_FEATURE_FIELDS = (
    "finding_id", "candidate_id", "scenario_id", "check_id",
    "resource_type", "feature_extraction_status",
)


def read_frozen_features(path=FEATURES):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != FROZEN_SHA256:
        raise ValueError(f"Frozen features SHA-256 mismatch: {digest}")
    with io.StringIO(data.decode("utf-8-sig"), newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)) or not set(REQUIRED_FEATURE_FIELDS) <= set(header):
            raise ValueError("Frozen features have missing or duplicate required columns")
        rows = []
        for number, cells in enumerate(reader, start=2):
            if len(cells) != len(header):
                raise ValueError(f"Frozen features row {number}: malformed column count")
            rows.append(dict(zip(header, cells)))
    if len(rows) != 369 or len({row["finding_id"] for row in rows}) != 369:
        raise ValueError("Frozen population must contain 369 unique findings")
    if any(not all(row[name] for name in REQUIRED_FEATURE_FIELDS) or
           row["feature_extraction_status"] != "EXTRACTED" for row in rows):
        raise ValueError("Frozen features contain missing identity or extraction failure")
    return rows


def finding_ids_sha256(rows):
    ids = sorted(row["finding_id"] for row in rows)
    return hashlib.sha256(("\n".join(ids) + "\n").encode("utf-8")).hexdigest()


def build_rows(features):
    grouped = defaultdict(list)
    for row in features:
        grouped[row["candidate_id"]].append(row)
    if len(grouped) != 81:
        raise ValueError(f"Expected 81 frozen artifacts, found {len(grouped)}")
    manifest_rows = []
    selected_findings = []
    for artifact_id, group in sorted(grouped.items()):
        tasks = {row["scenario_id"] for row in group}
        if len(tasks) != 1 or not next(iter(tasks)):
            raise ValueError(f"Ambiguous upstream source_task_id: {artifact_id}")
        source_task_id = next(iter(tasks))
        selected = len(group) >= 3
        if selected:
            selected_findings.extend(group)
        manifest_rows.append({
            "source_id": "geniac-secbench",
            "source_task_id": source_task_id,
            "family_id": source_task_id,
            "artifact_id": artifact_id,
            "candidate_id": artifact_id,
            "finding_count": str(len(group)),
            "selected": "True" if selected else "False",
            "selection_rule": SELECTION_RULE,
            "feature_spec_version": "v1.0",
            "features_v1_sha256": FROZEN_SHA256,
            "finding_ids_sha256": finding_ids_sha256(group),
        })
    selected_rows = [row for row in manifest_rows if row["selected"] == "True"]
    if (len(selected_rows) != 40 or len(selected_findings) != 300 or
            len({row["family_id"] for row in selected_rows}) != 10 or
            len({row["check_id"] for row in selected_findings}) != 10 or
            len({row["resource_type"] for row in selected_findings}) != 9 or
            sum(int(row["finding_count"]) >= 5 for row in selected_rows) != 20):
        raise ValueError("D-014 selected-scope counts differ from accepted checkpoint")
    return manifest_rows


def manifest_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURES)
    parser.add_argument("--output", type=Path, default=MANIFEST)
    args = parser.parse_args()
    try:
        rows = build_rows(read_frozen_features(args.features))
        data = manifest_bytes(rows)
        if args.output.exists():
            if args.output.read_bytes() != data:
                raise ValueError(f"Existing manifest differs; refusing to overwrite: {args.output}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(data)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Manifest = {args.output}")
    print(f"Manifest SHA-256 = {hashlib.sha256(data).hexdigest()}")
    print("Artifacts = 81; selected = 40; selected findings = 300")
    print("Selected families = 10; rules = 10; resource types = 9; >=5 artifacts = 20")


if __name__ == "__main__":
    main()
