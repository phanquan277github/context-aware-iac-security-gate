"""Regression tests for the D-014 scope builder and read-only validator."""

import csv
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

import build_phase4_tier3_scope as builder
import validate_phase4_tier3_scope as validator


class Phase4Tier3ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest = Path(self.temp.name) / "scope.csv"
        self.features = builder.read_frozen_features()
        self.rows = builder.build_rows(self.features)
        self.manifest.write_bytes(builder.manifest_bytes(self.rows))

    def rewrite(self, rows=None, fields=builder.FIELDS):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(self.rows if rows is None else rows)
        self.manifest.write_text(stream.getvalue(), encoding="utf-8")

    def validate(self):
        return validator.validate_manifest(self.manifest, builder.FEATURES)

    def test_current_manifest_reconstructs_exact_selected_finding_set(self):
        report = self.validate()
        self.assertEqual([], report.errors)
        self.assertEqual(81, report.counts["manifest_rows"])
        self.assertEqual(40, report.counts["selected_artifacts"])
        self.assertEqual(300, report.counts["selected_findings"])
        self.assertEqual(10, report.counts["selected_families"])
        self.assertEqual(20, report.counts["ndcg_at_5_size_eligible"])
        selected = {r["artifact_id"] for r in self.rows if r["selected"] == "True"}
        selected_findings = {r["finding_id"] for r in self.features if r["candidate_id"] in selected}
        self.assertEqual(300, len(selected_findings))
        self.assertEqual(selected, {r["candidate_id"] for r in self.features
                                    if sum(f["candidate_id"] == r["candidate_id"]
                                           for f in self.features) >= 3})

    def test_builder_is_deterministic_under_finding_row_order(self):
        reversed_rows = builder.build_rows(list(reversed(self.features)))
        self.assertEqual(builder.manifest_bytes(self.rows),
                         builder.manifest_bytes(reversed_rows))

    def test_numeric_suffix_does_not_merge_simple_and_complex_tasks(self):
        simple = next(r for r in self.rows if r["source_task_id"] == "aws-tf-001")
        complex_task = next(r for r in self.rows if r["source_task_id"] == "complex-aws-tf-001")
        self.assertEqual("aws-tf-001", simple["family_id"])
        self.assertEqual("complex-aws-tf-001", complex_task["family_id"])

    def test_rejects_wrong_family_and_task(self):
        self.rows[0]["family_id"] = "wrong-task"
        self.rows[0]["source_task_id"] = "wrong-task"
        self.rewrite()
        errors = self.validate().errors
        self.assertTrue(any("family_id" in error for error in errors))
        self.assertTrue(any("source_task_id" in error for error in errors))

    def test_rejects_selected_low_density_artifact(self):
        row = next(r for r in self.rows if r["selected"] == "False")
        row["selected"] = "True"
        self.rewrite()
        self.assertTrue(any("selected" in error for error in self.validate().errors))

    def test_rejects_excluded_eligible_artifact(self):
        row = next(r for r in self.rows if r["selected"] == "True")
        row["selected"] = "False"
        self.rewrite()
        self.assertTrue(any("selected" in error for error in self.validate().errors))

    def test_rejects_missing_and_duplicate_artifact(self):
        self.rewrite(self.rows[1:])
        self.assertTrue(any("coverage mismatch" in error for error in self.validate().errors))
        self.rewrite(self.rows + [self.rows[0]])
        self.assertTrue(any("Duplicate manifest" in error for error in self.validate().errors))

    def test_rejects_fabricated_finding_membership_digest(self):
        self.rows[0]["finding_ids_sha256"] = "0" * 64
        self.rewrite()
        self.assertTrue(any("finding_ids_sha256" in error for error in self.validate().errors))

    def test_rejects_wrong_count_rule_or_feature_version(self):
        self.rows[0]["finding_count"] = "999"
        self.rows[0]["selection_rule"] = "finding_count >= 5"
        self.rows[0]["feature_spec_version"] = "v2.0"
        self.rewrite()
        errors = self.validate().errors
        for field in ("finding_count", "selection_rule", "feature_spec_version"):
            self.assertTrue(any(field in error for error in errors))

    def test_rejects_fabricated_feature_hash_and_extra_label_column(self):
        self.rows[0]["features_v1_sha256"] = "0" * 64
        self.rewrite()
        self.assertTrue(any("features_v1_sha256" in error for error in self.validate().errors))
        for row in self.rows:
            row["human_rank"] = ""
        self.rewrite(fields=(*builder.FIELDS, "human_rank"))
        self.assertTrue(any("columns/order" in error for error in self.validate().errors))

    def test_rejects_drifted_feature_artifact(self):
        copy = Path(self.temp.name) / "drifted_features.csv"
        data = builder.FEATURES.read_bytes()
        first_id = self.features[0]["finding_id"].encode("ascii")
        copy.write_bytes(data.replace(first_id, b"0" * len(first_id), 1))
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            builder.read_frozen_features(copy)
        self.assertTrue(any("SHA-256 mismatch" in error for error in
                            validator.validate_manifest(self.manifest, copy).errors))

    def test_validator_does_not_modify_inputs(self):
        paths = (self.manifest, builder.FEATURES)
        before = {path: (hashlib.sha256(path.read_bytes()).hexdigest(),
                         path.stat().st_mtime_ns) for path in paths}
        self.assertEqual([], self.validate().errors)
        after = {path: (hashlib.sha256(path.read_bytes()).hexdigest(),
                        path.stat().st_mtime_ns) for path in paths}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
