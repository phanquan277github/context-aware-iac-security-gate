"""Regression checks for strict, shared applicability Boolean parsing."""

import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import extract_finding_context_features as extractor


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "dataset/main/context/rule_context_applicability.csv"
PILOT_INPUT = ROOT / "results/context_feature_pilot/pilot_findings.csv"
PILOT_OUTPUT = ROOT / "results/context_feature_pilot/finding_context_features_pilot.csv"


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class ApplicabilityBooleanTests(unittest.TestCase):
    def test_python_boolean_and_string_representations(self):
        cases = (
            (True, True),
            (False, False),
            ("True", True),
            ("False", False),
            (" true ", True),
            (" FALSE ", False),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertIs(extractor.as_bool(value), expected)

    def test_actual_pandas_csv_boolean_scalars(self):
        matrix = pd.read_csv(MATRIX)
        for feature in extractor.FEATURES:
            self.assertTrue(pd.api.types.is_bool_dtype(matrix[feature].dtype))
            for value in matrix[feature]:
                self.assertIs(extractor.as_bool(value), bool(value))

    def test_invalid_tokens_are_rejected(self):
        for value in ("yes", "1", "no", "0", "invalid", "", None, 1, 0, float("nan")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Invalid applicability Boolean"):
                    extractor.as_bool(value)

    def test_initialization_and_final_guard_share_parser(self):
        false_features = {feature: False for feature in extractor.FEATURES}
        initialized = extractor.initialize_features(false_features, "aws_vpc")
        self.assertTrue(all(value == "not_applicable" for value in initialized.values()))

        true_features = {feature: True for feature in extractor.FEATURES}
        initialized = extractor.initialize_features(true_features, "aws_vpc")
        self.assertEqual("unknown", initialized["internet_exposure"])
        self.assertEqual("network", initialized["resource_role"])

        values = {feature: "yes" for feature in extractor.FEATURES}
        guard = {feature: "false" for feature in extractor.FEATURES}
        guard["internet_exposure"] = "true"
        result = extractor.enforce_applicability(values, guard)
        self.assertEqual("yes", result["internet_exposure"])
        self.assertTrue(all(
            result[feature] == "not_applicable"
            for feature in extractor.FEATURES if feature != "internet_exposure"
        ))

    def test_invalid_token_never_becomes_non_applicable(self):
        values = {feature: "unknown" for feature in extractor.FEATURES}
        matrix_row = {feature: True for feature in extractor.FEATURES}
        matrix_row["internet_exposure"] = "yes"
        with self.assertRaisesRegex(ValueError, "Invalid applicability Boolean"):
            extractor.enforce_applicability(values, matrix_row)
        self.assertEqual("unknown", values["internet_exposure"])

    def test_main_rejects_bad_matrix_cell_before_writing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            rows = csv_rows(MATRIX)
            rows[-2]["internet_exposure"] = "1"
            altered_matrix = folder / "applicability.csv"
            with altered_matrix.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            input_rows = csv_rows(PILOT_INPUT)
            single_input = folder / "one_finding.csv"
            with single_input.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(input_rows[0]))
                writer.writeheader()
                writer.writerow(input_rows[0])
            output = folder / "should_not_exist.csv"
            args = [
                "extract_finding_context_features.py",
                "--input", str(single_input),
                "--output", str(output),
            ]
            with patch.object(extractor, "APPLICABILITY", altered_matrix), patch.object(sys, "argv", args):
                with self.assertRaisesRegex(ValueError, "check_id=CKV_AWS_117, feature=internet_exposure"):
                    extractor.main()
            self.assertFalse(output.exists())

    def test_pilot_replay_preserves_values_and_emits_versioned_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "replayed.csv"
            args = [
                "extract_finding_context_features.py",
                "--input", str(PILOT_INPUT),
                "--output", str(output),
            ]
            with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
                extractor.main()
            actual, expected = csv_rows(output), csv_rows(PILOT_OUTPUT)
            self.assertEqual(20, len(actual))
            self.assertEqual([row["finding_id"] for row in expected],
                             [row["finding_id"] for row in actual])
            for actual_row, expected_row in zip(actual, expected):
                # D-011 resolves the two subnet routes; saved output remains untouched.
                expected_values = dict(expected_row)
                if expected_row["check_id"] == "CKV_AWS_130":
                    expected_values.update(reachability="internet", applicable_unknown_count="2",
                                           applicable_unknown_features="internet_exposure|public_access")
                self.assertEqual(
                    {k: v for k, v in expected_values.items() if k != "feature_evidence"},
                    {k: v for k, v in actual_row.items() if k != "feature_evidence"},
                )
                new_evidence = json.loads(actual_row["feature_evidence"])
                self.assertEqual("d009-v1", new_evidence["contract_version"])
                self.assertEqual(actual_row["finding_id"],
                                 new_evidence["provenance"]["finding_id"])
                self.assertEqual(set(extractor.FEATURES),
                                 set(new_evidence["features"]) |
                                 set(new_evidence["not_applicable"]))
                for feature in extractor.FEATURES:
                    self.assertEqual(expected_values[feature], actual_row[feature])
                self.assertEqual(expected_values["applicable_unknown_count"],
                                 actual_row["applicable_unknown_count"])
                self.assertEqual(expected_values["applicable_unknown_features"],
                                 actual_row["applicable_unknown_features"])


if __name__ == "__main__":
    unittest.main()
