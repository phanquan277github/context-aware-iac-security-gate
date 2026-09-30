"""Read-only structural validation of finding-level contextual features.

This does not validate evidence security meaning or replace pilot regression QA.
Relative source paths are resolved against --source-root, not the CSV folder.
"""

import argparse
import csv
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "dataset/main/context"
GROUPS = (
    "input_schema", "configuration", "identifiers", "applicability",
    "feature_values", "unknown_counters", "evidence_json", "references", "source",
)
REQUIRED = (
    "finding_id", "check_id", "applicable_unknown_count",
    "applicable_unknown_features", "feature_evidence",
)
REFERENCE_FIELDS = (
    "candidate_id", "scenario_id", "check_id", "resource", "resource_type",
    "source_path", "line_start", "line_end",
)


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    def error(self, group, message):
        self.errors.append((group, message))

    def warn(self, group, message):
        self.warnings.append((group, message))


def read_csv(path, report, group):
    """Reject malformed rows and duplicate headers without changing values."""
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            if not header or any(not name.strip() for name in header):
                report.error(group, f"{path}: missing or blank column names")
                return [], []
            duplicates = sorted(name for name, count in Counter(header).items() if count > 1)
            if duplicates:
                report.error(group, f"{path}: duplicate columns: {', '.join(duplicates)}")
                return header, []
            rows = []
            for number, values in enumerate(reader, start=2):
                if len(values) != len(header):
                    report.error(group, f"{path}: record {number}: expected {len(header)} cells, found {len(values)}")
                    continue
                rows.append(dict(zip(header, values)))
            return header, rows
    except (OSError, UnicodeError, csv.Error) as exc:
        report.error(group, f"{path}: cannot read CSV: {exc}")
        return [], []


def read_yaml(path, report):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        if not isinstance(data, dict):
            raise ValueError("expected a YAML mapping")
        return data
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
        report.error("configuration", f"{path}: cannot load specification: {exc}")
        return {}


def load_contract(schema_path, definitions_path, applicability_path, report):
    schema = read_yaml(schema_path, report)
    definitions = read_yaml(definitions_path, report)
    features = schema.get("finding_context")
    if not isinstance(features, dict) or not features:
        report.error("configuration", "Schema requires a non-empty finding_context mapping")
        features = {}
    if any(not isinstance(name, str) or not name.strip() for name in features):
        report.error("configuration", "Finding feature names must be non-blank strings")
        features = {}
    if any(not isinstance(name, str) for name in definitions):
        report.error("configuration", "Definition feature names must be strings")
        definitions = {}
    allowed = {}
    for name, config in features.items():
        values = config.get("values") if isinstance(config, dict) else None
        if not isinstance(values, list) or not values or any(
            not isinstance(value, (str, int, float)) or isinstance(value, bool)
            for value in values
        ):
            report.error("configuration", f"{name}: missing or invalid allowed values")
            continue
        allowed[name] = {str(value) for value in values}
        definition = definitions.get(name)
        if not isinstance(definition, dict) or definition.get("human_label_derived") is not False:
            report.error("configuration", f"{name}: definition must explicitly declare human_label_derived=false")
    for name in sorted(set(definitions) - set(features)):
        report.error("configuration", f"Definition absent from finding schema: {name}")

    columns, rows = read_csv(applicability_path, report, "configuration")
    expected = {"check_id", *features}
    if set(columns) != expected:
        report.error("configuration", f"Applicability columns differ from schema: missing={sorted(expected - set(columns))}, extra={sorted(set(columns) - expected)}")
    matrix = {}
    for number, row in enumerate(rows, start=2):
        rule = row.get("check_id", "")
        if not rule.strip() or rule in matrix:
            report.error("configuration", f"Applicability record {number}: blank or duplicate check_id={rule!r}")
        parsed = {}
        for feature in features:
            value = row.get(feature, "")
            token = value.strip().lower()
            if token not in {"true", "false"}:
                report.error("configuration", f"Applicability record {number}, {rule}, {feature}: expected True/False, got {value!r}")
            else:
                parsed[feature] = token == "true"
        matrix[rule] = parsed
    report.counts.update(features=len(features), applicability_rules=len(rows), matrix_cells=sum(len(row) for row in matrix.values()))
    return allowed, matrix


def load_references(path, report):
    if path is None:
        report.warn("references", "No --findings supplied; finding provenance comparison skipped")
        return None
    columns, rows = read_csv(path, report, "references")
    if "finding_id" not in columns:
        report.error("references", f"{path}: required finding_id column missing")
    references = {}
    for number, row in enumerate(rows, start=2):
        finding = row.get("finding_id", "")
        if not finding.strip() or finding in references:
            report.error("references", f"{path}: record {number}: blank or duplicate finding_id={finding!r}")
        references[finding] = row
    return references


def reject_json_constant(value):
    raise ValueError(f"Non-standard JSON constant: {value}")


def validate_source(row, label, root, report, source_cache):
    raw_path = row.get("source_path", "")
    if not raw_path.strip():
        report.warn("source", f"{label}: source_path absent or blank; source verification skipped")
        return
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(root) / path
    report.counts["source_references"] += 1
    if path not in source_cache:
        try:
            source_cache[path] = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeError, ValueError) as exc:
            source_cache[path] = None
            report.warn("source", f"{label}: source unavailable: {raw_path!r}: {exc}; scanner evidence may still exist")
    line_count = source_cache[path]
    if line_count is None:
        return
    report.counts["source_references_verified"] += 1
    start, end = row.get("line_start", ""), row.get("line_end", "")
    if not start and not end:
        report.warn("source", f"{label}: no line range supplied; location verification skipped")
        return
    if not re.fullmatch(r"[0-9]+", start) or not re.fullmatch(r"[0-9]+", end):
        report.error("source", f"{label}: line range must contain positive integers, got {start!r}-{end!r}")
    elif not 1 <= int(start) <= int(end) <= line_count:
        report.error("source", f"{label}: line range {start}-{end} outside source bounds 1-{line_count}")
    else:
        report.counts["line_ranges_verified"] += 1


def validate_file(input_path, schema_path=CONTEXT / "context_schema.yaml",
                  definitions_path=CONTEXT / "feature_definitions.yaml",
                  applicability_path=CONTEXT / "rule_context_applicability.csv",
                  findings_path=None, source_root=ROOT):
    report = Report()
    columns, rows = read_csv(input_path, report, "input_schema")
    report.counts["records_loaded"] = len(rows)
    allowed, matrix = load_contract(schema_path, definitions_path, applicability_path, report)
    missing = sorted(set(REQUIRED).union(allowed) - set(columns))
    if missing:
        report.error("input_schema", f"{input_path}: missing required columns: {', '.join(missing)}")
    references = load_references(findings_path, report)
    if any(group in {"input_schema", "configuration"} for group, _ in report.errors):
        return report
    if not rows:
        report.warn("input_schema", "No finding records; no observations were validated")

    seen = set()
    source_cache = {}
    for number, row in enumerate(rows, start=2):
        report.counts["records_checked"] += 1
        finding, rule = row["finding_id"], row["check_id"]
        label = f"record {number}, finding_id={finding!r}"
        if not finding.strip() or finding in seen:
            report.error("identifiers", f"{label}: blank or duplicate finding_id")
        seen.add(finding)
        if not rule.strip():
            report.error("identifiers", f"{label}: blank check_id")
        applicability = matrix.get(rule)
        if applicability is None:
            report.error("applicability", f"{label}: missing applicability rule {rule!r}")

        unknowns = []
        for feature, values in allowed.items():
            value = row[feature]
            report.counts["feature_cells"] += 1
            if value == "unknown":
                report.counts["unknown_cells"] += 1
            elif value == "not_applicable":
                report.counts["not_applicable_cells"] += 1
            if not value.strip():
                report.error("feature_values", f"{label}, {feature}: blank value; an explicit state is required")
            if applicability is not None:
                if not applicability[feature]:
                    report.counts["non_applicable_cells_expected"] += 1
                    if value != "not_applicable":
                        report.error("applicability", f"{label}, {feature}: non-applicable feature must equal 'not_applicable', got {value!r}")
                    # Non-applicable observations are not generic feature values.
                    continue
                report.counts["applicable_cells_expected"] += 1
                if value == "not_applicable":
                    report.error("applicability", f"{label}, {feature}: applicable feature cannot equal 'not_applicable'")
                    continue
                if value == "unknown":
                    unknowns.append(feature)
            if value.strip() and value not in values:
                report.error("feature_values", f"{label}, {feature}: value {value!r} not allowed by schema")

        if applicability is not None:
            count = row["applicable_unknown_count"]
            if not re.fullmatch(r"[0-9]+", count) or int(count) != len(unknowns):
                report.error("unknown_counters", f"{label}: applicable_unknown_count={count!r}, expected {len(unknowns)}")
            names = row["applicable_unknown_features"].split("|") if row["applicable_unknown_features"] else []
            if len(names) != len(set(names)) or set(names) != set(unknowns):
                report.error("unknown_counters", f"{label}: applicable_unknown_features={names!r}, expected {sorted(unknowns)!r}")
            report.counts["unknown_counter_records_checked"] += 1

        try:
            evidence = json.loads(row["feature_evidence"], parse_constant=reject_json_constant)
            report.counts["evidence_json_parsed"] += 1
            if isinstance(evidence, dict):
                for name in ("finding_id", *REFERENCE_FIELDS):
                    if name in evidence and name in row and evidence[name] != row[name]:
                        report.error("references", f"{label}: evidence {name}={evidence[name]!r} differs from record {row[name]!r}")
            else:
                report.warn("references", f"{label}: evidence JSON is not an object; identifier comparison skipped (no evidence shape contract)")
        except (ValueError, RecursionError) as exc:
            report.error("evidence_json", f"{label}: invalid feature_evidence JSON: {exc}")

        if references is not None:
            original = references.get(finding)
            if original is None:
                report.error("references", f"{label}: finding_id absent from --findings")
            else:
                report.counts["finding_references_checked"] += 1
                for name in REFERENCE_FIELDS:
                    if name in row and name in original and row[name] != original[name]:
                        report.error("references", f"{label}: {name} differs from --findings: {row[name]!r} vs {original[name]!r}")
        validate_source(row, label, source_root, report, source_cache)
    report.counts["unique_finding_ids"] = sum(bool(value.strip()) for value in seen)
    report.counts["source_files_verified"] = sum(value is not None for value in source_cache.values())
    return report


def print_report(report):
    print("FINDING CONTEXT FEATURE VALIDATION")
    for name in sorted(report.counts):
        print(f"{name} = {report.counts[name]}")
    errors = Counter(group for group, _ in report.errors)
    warnings = Counter(group for group, _ in report.warnings)
    print("\nGROUP COUNTS")
    for group in GROUPS:
        print(f"{group}: errors={errors[group]}, warnings={warnings[group]}")
    for severity, issues in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for group, message in issues:
            print(f"{severity} [{group}] {message}")
    print(f"\nErrors = {len(report.errors)}; Warnings = {len(report.warnings)}")
    print("STATUS = " + ("FAIL" if report.errors else "PASS"))
    print("LIMITATION: Evidence security meaning, privilege levels, IAM statement resolution, and network direction are not validated.")
    print("LIMITATION: Missing source access is a warning; scanner or other approved evidence may exist. PASS is not research acceptance.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/context_feature_pilot/finding_context_features_pilot.csv")
    parser.add_argument("--schema", type=Path, default=CONTEXT / "context_schema.yaml")
    parser.add_argument("--definitions", type=Path, default=CONTEXT / "feature_definitions.yaml")
    parser.add_argument("--applicability", type=Path, default=CONTEXT / "rule_context_applicability.csv")
    parser.add_argument("--findings", type=Path, help="Optional original findings CSV using the same finding_id namespace")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    report = validate_file(args.input, args.schema, args.definitions, args.applicability, args.findings, args.source_root)
    print_report(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())