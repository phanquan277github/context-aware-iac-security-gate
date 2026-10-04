"""Read-only validation of the D-014 Phase-4 Tier-3 artifact scope manifest."""

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass, field
import hashlib
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
FEATURE_FIELDS = (
    "finding_id", "candidate_id", "scenario_id", "check_id",
    "resource_type", "feature_extraction_status",
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    manifest_sha256: str = ""


def read_csv(path):
    data = Path(path).read_bytes()
    text = data.decode("utf-8-sig")
    from io import StringIO
    with StringIO(text, newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if not header or len(header) != len(set(header)):
            raise ValueError(f"{path}: missing or duplicate CSV header")
        rows = []
        for number, cells in enumerate(reader, start=2):
            if len(cells) != len(header):
                raise ValueError(f"{path}: row {number} has {len(cells)} cells, expected {len(header)}")
            rows.append(dict(zip(header, cells)))
    return data, header, rows


def digest_ids(group):
    values = sorted(row["finding_id"] for row in group)
    return hashlib.sha256(("\n".join(values) + "\n").encode("utf-8")).hexdigest()


def validate_manifest(manifest_path=MANIFEST, features_path=FEATURES):
    report = Report()
    try:
        feature_data, feature_header, features = read_csv(features_path)
        manifest_data, manifest_header, manifest = read_csv(manifest_path)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        report.errors.append(str(exc))
        return report
    report.manifest_sha256 = hashlib.sha256(manifest_data).hexdigest()
    feature_sha = hashlib.sha256(feature_data).hexdigest()
    if feature_sha != FROZEN_SHA256:
        report.errors.append(f"Frozen features SHA-256 mismatch: {feature_sha}")
    if not set(FEATURE_FIELDS) <= set(feature_header):
        report.errors.append("Frozen features missing required identity columns")
        return report
    if manifest_header != list(FIELDS):
        report.errors.append("Manifest columns/order differ from D-014 schema")
        return report
    if len(features) != 369 or len({r["finding_id"] for r in features}) != 369:
        report.errors.append("Frozen population must contain 369 unique findings")
    if any(not all(row[name] for name in FEATURE_FIELDS) or
           row["feature_extraction_status"] != "EXTRACTED" for row in features):
        report.errors.append("Frozen features contain missing identity or extraction failure")
    grouped = defaultdict(list)
    for row in features:
        grouped[row["candidate_id"]].append(row)
    report.counts.update(frozen_findings=len(features), frozen_artifacts=len(grouped),
                         manifest_rows=len(manifest))
    if len(grouped) != 81:
        report.errors.append(f"Expected 81 frozen artifacts; found {len(grouped)}")
    ids = [row["artifact_id"] for row in manifest]
    if ids != sorted(ids):
        report.errors.append("Manifest artifact rows are not sorted deterministically")
    if len(ids) != len(set(ids)):
        report.errors.append("Duplicate manifest artifact_id")
    missing = sorted(set(grouped) - set(ids))
    extra = sorted(set(ids) - set(grouped))
    if missing or extra:
        report.errors.append(f"Manifest artifact coverage mismatch: missing={missing}, extra={extra}")
    selected_ids = set()
    for row in manifest:
        artifact = row["artifact_id"]
        group = grouped.get(artifact)
        if not group:
            continue
        tasks = {item["scenario_id"] for item in group}
        if len(tasks) != 1:
            report.errors.append(f"{artifact}: ambiguous upstream source_task_id")
            continue
        task = next(iter(tasks))
        expected = {
            "source_id": "geniac-secbench",
            "source_task_id": task,
            "family_id": task,
            "candidate_id": artifact,
            "finding_count": str(len(group)),
            "selected": "True" if len(group) >= 3 else "False",
            "selection_rule": SELECTION_RULE,
            "feature_spec_version": "v1.0",
            "features_v1_sha256": FROZEN_SHA256,
            "finding_ids_sha256": digest_ids(group),
        }
        for field_name, value in expected.items():
            if row[field_name] != value:
                report.errors.append(
                    f"{artifact}: {field_name}={row[field_name]!r}; expected {value!r}"
                )
        if row["selected"] == "True":
            selected_ids.add(artifact)
    expected_ids = {artifact for artifact, group in grouped.items() if len(group) >= 3}
    if selected_ids != expected_ids:
        report.errors.append("Selected artifact set differs from finding_count >= 3")
    selected_findings = [row for row in features if row["candidate_id"] in selected_ids]
    report.counts.update(
        selected_artifacts=len(selected_ids),
        selected_findings=len(selected_findings),
        selected_families=len({row["scenario_id"] for row in selected_findings}),
        selected_rules=len({row["check_id"] for row in selected_findings}),
        selected_resource_types=len({row["resource_type"] for row in selected_findings}),
        ndcg_at_3_size_eligible=sum(len(group) >= 3 for artifact, group in grouped.items()
                                    if artifact in selected_ids),
        ndcg_at_5_size_eligible=sum(len(group) >= 5 for artifact, group in grouped.items()
                                    if artifact in selected_ids),
    )
    expected_counts = {
        "frozen_findings": 369, "frozen_artifacts": 81, "manifest_rows": 81,
        "selected_artifacts": 40, "selected_findings": 300,
        "selected_families": 10, "selected_rules": 10,
        "selected_resource_types": 9, "ndcg_at_3_size_eligible": 40,
        "ndcg_at_5_size_eligible": 20,
    }
    for name, expected in expected_counts.items():
        if report.counts[name] != expected:
            report.errors.append(f"{name}={report.counts[name]}; expected {expected}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--features", type=Path, default=FEATURES)
    args = parser.parse_args()
    report = validate_manifest(args.manifest, args.features)
    print("D-014 TIER-3 SCOPE VALIDATION")
    print(f"manifest_sha256 = {report.manifest_sha256}")
    for name, count in sorted(report.counts.items()):
        print(f"{name} = {count}")
    print(f"errors = {len(report.errors)}; warnings = 0")
    for error in report.errors:
        print(f"ERROR: {error}")
    print("STATUS = FAIL" if report.errors else "STATUS = PASS")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
