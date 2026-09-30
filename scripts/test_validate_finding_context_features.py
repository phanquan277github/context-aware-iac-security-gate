"""Regression tests for the general validator using isolated synthetic inputs."""

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

import yaml

import validate_finding_context_features as validator


class FindingContextValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "features.csv"
        self.schema = self.root / "schema.yaml"
        self.definitions = self.root / "definitions.yaml"
        self.matrix = self.root / "matrix.csv"
        self.findings = self.root / "findings.csv"
        self.source = self.root / "main.tf"
        self.source.write_text("resource line\nsecond line\n", encoding="utf-8")
        self.schema.write_text(yaml.safe_dump({"finding_context": {
            "technical_fact": {"values": ["yes", "no", "unknown", "not_applicable"]},
            # Applicability is enforced before generic value checks.
            "role_fact": {"values": ["network"]},
        }}), encoding="utf-8")
        self.definitions.write_text(yaml.safe_dump({
            "technical_fact": {"human_label_derived": False},
            "role_fact": {"human_label_derived": False},
        }), encoding="utf-8")
        self.matrix_rows = [
            {"check_id": "RULE_A", "technical_fact": "True", "role_fact": "False"},
            {"check_id": "RULE_B", "technical_fact": "False", "role_fact": "True"},
        ]
        self.rows = [
            {
                "finding_id": "finding-1", "check_id": "RULE_A",
                "technical_fact": "unknown", "role_fact": "not_applicable",
                "applicable_unknown_count": "1",
                "applicable_unknown_features": "technical_fact",
                "feature_evidence": json.dumps({"check_id": "RULE_A", "resource": "resource.one"}),
                "resource": "resource.one", "source_path": "main.tf",
                "line_start": "1", "line_end": "2",
            },
            {
                "finding_id": "finding-2", "check_id": "RULE_B",
                "technical_fact": "not_applicable", "role_fact": "network",
                "applicable_unknown_count": "0", "applicable_unknown_features": "",
                "feature_evidence": json.dumps({"check_id": "RULE_B"}),
                "resource": "resource.two", "source_path": "main.tf",
                "line_start": "1", "line_end": "1",
            },
        ]

    def write_csv(self, path, rows):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def prepare(self, rows=None):
        self.write_csv(self.input, self.rows if rows is None else rows)
        self.write_csv(self.matrix, self.matrix_rows)
        self.write_csv(self.findings, self.rows)

    def validate(self, rows=None):
        self.prepare(rows)
        return validator.validate_file(
            self.input, self.schema, self.definitions, self.matrix,
            self.findings, self.root,
        )

    def assert_group(self, report, group):
        self.assertIn(group, [name for name, _ in report.errors])

    def test_general_schema_and_record_count_are_not_pilot_specific(self):
        report = self.validate()
        self.assertEqual([], report.errors)
        self.assertEqual([], report.warnings)
        self.assertEqual(2, report.counts["records_checked"])
        self.assertEqual(2, report.counts["features"])
        self.assertEqual(2, report.counts["not_applicable_cells"])

    def test_deterministic_and_read_only(self):
        self.prepare()
        files = [self.input, self.schema, self.definitions, self.matrix, self.findings, self.source]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
        entries = sorted(p.name for p in self.root.iterdir())
        first = validator.validate_file(self.input, self.schema, self.definitions, self.matrix, self.findings, self.root)
        second = validator.validate_file(self.input, self.schema, self.definitions, self.matrix, self.findings, self.root)
        self.assertEqual(first, second)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files})
        self.assertEqual(entries, sorted(p.name for p in self.root.iterdir()))

    def test_required_column_missing(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            del row["technical_fact"]
        self.assert_group(self.validate(rows), "input_schema")

    def test_duplicate_headers_and_malformed_rows(self):
        self.prepare()
        for text in ("finding_id,finding_id\none,two\n", "finding_id,check_id\none,RULE_A,extra\n"):
            with self.subTest(text=text):
                self.input.write_text(text, encoding="utf-8")
                report = validator.validate_file(self.input, self.schema, self.definitions, self.matrix, self.findings, self.root)
                self.assert_group(report, "input_schema")

    def test_blank_and_duplicate_finding_identifiers(self):
        for value in ("", "finding-1"):
            with self.subTest(value=value):
                rows = copy.deepcopy(self.rows)
                rows[1]["finding_id"] = value
                self.assert_group(self.validate(rows), "identifiers")

    def test_invalid_boolean_does_not_become_non_applicable(self):
        for value in ("", "yes", "1", "invalid"):
            with self.subTest(value=value):
                self.matrix_rows[0]["technical_fact"] = value
                report = self.validate()
                self.assert_group(report, "configuration")
                self.assertEqual(0, report.counts["records_checked"])

    def test_duplicate_matrix_rule_and_missing_feature(self):
        self.matrix_rows[1]["check_id"] = "RULE_A"
        self.assert_group(self.validate(), "configuration")
        for row in self.matrix_rows:
            del row["role_fact"]
        self.assert_group(self.validate(), "configuration")

    def test_missing_rule_is_an_error(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["check_id"] = "UNCONFIGURED"
        self.assert_group(self.validate(rows), "applicability")

    def test_applicability_both_directions_and_blank_state(self):
        for index, field, value, group in (
            (0, "technical_fact", "not_applicable", "applicability"),
            (0, "role_fact", "unknown", "applicability"),
            (0, "technical_fact", "", "feature_values"),
            (1, "technical_fact", "yes", "applicability"),
            (1, "role_fact", "unsupported", "feature_values"),
        ):
            with self.subTest(index=index, field=field, value=value):
                rows = copy.deepcopy(self.rows)
                rows[index][field] = value
                self.assert_group(self.validate(rows), group)

    def test_unknown_count_and_list_consistency(self):
        for field, value in (
            ("applicable_unknown_count", "0"),
            ("applicable_unknown_count", "-1"),
            ("applicable_unknown_count", "1.0"),
            ("applicable_unknown_features", ""),
            ("applicable_unknown_features", "technical_fact|technical_fact"),
            ("applicable_unknown_features", "role_fact"),
        ):
            with self.subTest(field=field, value=value):
                rows = copy.deepcopy(self.rows)
                rows[0][field] = value
                self.assert_group(self.validate(rows), "unknown_counters")

    def test_invalid_and_non_standard_json(self):
        for value in ("", "{invalid", '{"x": NaN}', '{"x": Infinity}'):
            with self.subTest(value=value):
                rows = copy.deepcopy(self.rows)
                rows[0]["feature_evidence"] = value
                self.assert_group(self.validate(rows), "evidence_json")

    def test_json_shape_does_not_introduce_an_evidence_contract(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["feature_evidence"] = "[]"
        report = self.validate(rows)
        self.assertEqual([], report.errors)
        self.assertIn("references", [group for group, _ in report.warnings])

    def test_evidence_and_input_references(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["feature_evidence"] = '{"check_id": "OTHER_RULE"}'
        self.assert_group(self.validate(rows), "references")
        rows[0]["finding_id"] = "not-in-input"
        self.assert_group(self.validate(rows), "references")
        rows = copy.deepcopy(self.rows)
        rows[0]["resource"] = "different-resource"
        self.assert_group(self.validate(rows), "references")

    def test_source_bounds_and_missing_source(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["line_end"] = "3"
        self.assert_group(self.validate(rows), "source")
        rows[0]["line_end"] = "2"
        rows[0]["source_path"] = "missing.tf"
        report = self.validate(rows)
        self.assertNotIn("source", [group for group, _ in report.errors])
        self.assertIn("source", [group for group, _ in report.warnings])

    def test_missing_input_returns_report(self):
        report = validator.validate_file(self.root / "missing.csv")
        self.assert_group(report, "input_schema")

    def test_cli_failure_exit_and_summary(self):
        self.prepare()
        args = [
            "--input", str(self.input), "--schema", str(self.schema),
            "--definitions", str(self.definitions), "--applicability", str(self.matrix),
            "--findings", str(self.findings), "--source-root", str(self.root),
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, validator.main(args))
        self.assertIn("STATUS = PASS", output.getvalue())
        self.rows[0]["feature_evidence"] = "{invalid"
        self.prepare()
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(1, validator.main(args))
        self.assertIn("ERROR [evidence_json]", output.getvalue())
        self.assertIn("STATUS = FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()