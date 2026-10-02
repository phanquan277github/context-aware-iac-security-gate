"""Regression checks for the approved D-010 type-level role taxonomy."""

import csv
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import extract_finding_context_features as extractor


ROOT = Path(__file__).resolve().parents[1]
MAIN_FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
PILOT_FINDINGS = ROOT / "results/context_feature_pilot/pilot_findings.csv"
APPLICABILITY = ROOT / "dataset/main/context/rule_context_applicability.csv"


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class ResourceRoleTaxonomyTests(unittest.TestCase):
    def test_version_and_entry_count(self):
        self.assertEqual("d010-v1", extractor.RESOURCE_ROLE_TAXONOMY_VERSION)
        self.assertEqual(58, len(extractor.RESOURCE_ROLE_MAP))

    def test_approved_specialized_mappings(self):
        examples = {
            "aws_iam_policy": "identity",
            "aws_s3_bucket": "primary_data",
            "aws_eks_cluster": "compute",
            "aws_iam_policy_document": "identity",
            "aws_api_gateway_rest_api": "network",
            "aws_network_acl": "network",
            "aws_elasticache_replication_group": "primary_data",
            "aws_secretsmanager_secret": "primary_data",
            "aws_glue_job": "compute",
        }
        for resource_type, role in examples.items():
            with self.subTest(resource_type=resource_type):
                self.assertEqual(role, extractor.infer_resource_role(resource_type))

    def test_explicit_other_mappings(self):
        for resource_type in ("aws_kms_key", "aws_sns_topic"):
            with self.subTest(resource_type=resource_type):
                self.assertEqual("other", extractor.infer_resource_role(resource_type))

    def test_empty_or_unreadable_type_fails(self):
        for resource_type in ("", "  ", None, float("nan")):
            with self.subTest(resource_type=resource_type):
                with self.assertRaisesRegex(ValueError, "Missing or unreadable resource_type"):
                    extractor.infer_resource_role(resource_type)

    def test_unmapped_nonempty_type_has_no_other_fallback(self):
        with self.assertRaisesRegex(ValueError, "Unmapped resource_type"):
            extractor.infer_resource_role("aws_future_service")

    def test_iam_prefix_has_no_implicit_identity_fallback(self):
        with self.assertRaisesRegex(ValueError, "Unmapped resource_type"):
            extractor.infer_resource_role("aws_iam_future_policy")

    def test_resource_role_evidence_identifies_mapping_and_version(self):
        applicability = {feature: False for feature in extractor.FEATURES}
        applicability["resource_role"] = True
        row = {
            "check_id": "CKV_AWS_117",
            "resource": "aws_lambda_function.demo",
            "resource_type": "aws_lambda_function",
        }
        features, evidence = extractor.extract_features(row, applicability, "")
        self.assertEqual("compute", features["resource_role"])
        self.assertEqual(
            {
                "resource_type": "aws_lambda_function",
                "resource_role": "compute",
                "taxonomy_version": "d010-v1",
                "mapping_entry": {
                    "resource_type": "aws_lambda_function", "role": "compute"
                },
            },
            evidence["resource_role"],
        )

    def test_non_applicable_role_does_not_require_type(self):
        applicability = {feature: False for feature in extractor.FEATURES}
        features = extractor.initialize_features(applicability, "")
        self.assertEqual("not_applicable", features["resource_role"])

    def test_current_main_nonempty_types_have_explicit_entries(self):
        rows = csv_rows(MAIN_FINDINGS)
        observed = {row["resource_type"] for row in rows if row["resource_type"].strip()}
        self.assertEqual(1706, len(rows))
        self.assertEqual(56, len(observed))
        self.assertFalse(observed - extractor.RESOURCE_ROLE_MAP.keys())

    def test_current_scope_excludes_nine_empty_ckv_tf_1_findings(self):
        main = csv_rows(MAIN_FINDINGS)
        rules = {row["check_id"] for row in csv_rows(APPLICABILITY)}
        empty = [row for row in main if not row["resource_type"].strip()]
        scoped = [row for row in main if row["check_id"] in rules]
        self.assertEqual(9, len(empty))
        self.assertEqual({"CKV_TF_1"}, {row["check_id"] for row in empty})
        self.assertNotIn("CKV_TF_1", rules)
        self.assertEqual(369, len(scoped))
        self.assertTrue(all(row["resource_type"] in extractor.RESOURCE_ROLE_MAP
                            for row in scoped))

    def test_pilot_types_are_mapped(self):
        rows = csv_rows(PILOT_FINDINGS)
        self.assertEqual(20, len(rows))
        self.assertTrue(all(row["resource_type"] in extractor.RESOURCE_ROLE_MAP
                            for row in rows))

    def test_extractor_rejects_out_of_scope_rule_before_output(self):
        raw = next(row for row in csv_rows(MAIN_FINDINGS)
                   if row["check_id"] == "CKV_TF_1")
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "out_of_scope.csv"
            output = folder / "should_not_exist.csv"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(raw))
                writer.writeheader()
                writer.writerow(raw)
            args = ["extract_finding_context_features.py",
                    "--input", str(source), "--output", str(output)]
            with patch.object(sys, "argv", args):
                with self.assertRaisesRegex(ValueError, "Missing applicability row for CKV_TF_1"):
                    extractor.main()
            self.assertFalse(output.exists())

    def test_extractor_rejects_empty_type_for_in_scope_finding(self):
        raw = dict(csv_rows(PILOT_FINDINGS)[0])
        raw["resource_type"] = ""
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "empty_type.csv"
            output = folder / "should_not_exist.csv"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(raw))
                writer.writeheader()
                writer.writerow(raw)
            args = ["extract_finding_context_features.py",
                    "--input", str(source), "--output", str(output)]
            with patch.object(sys, "argv", args):
                with self.assertRaisesRegex(ValueError, "Missing or unreadable resource_type"):
                    extractor.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
