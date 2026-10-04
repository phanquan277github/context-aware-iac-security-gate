"""Regression tests for CKV_AWS_145 affected-bucket KMS-control evidence."""

import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_evidence import s3_kms_control_decision
import extract_finding_context_features as extractor
import validate_context_evidence as validator


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
CORPUS = ROOT / "dataset/main/corpus/geniac_tier_a"


def finding(prefix):
    with FINDINGS.open(encoding="utf-8", newline="") as stream:
        return next(row for row in csv.DictReader(stream) if row["finding_id"].startswith(prefix))


class S3KmsControlTests(unittest.TestCase):
    def decide(self, additional="", bucket='resource "aws_s3_bucket" "target" {\n  bucket = "target"\n}\n'):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text(bucket + additional, encoding="utf-8")
            return s3_kms_control_decision({"resource": "aws_s3_bucket.target"}, path)

    def config(self, name="control", link="aws_s3_bucket.target.id", algorithm='"AES256"'):
        return f'''resource "aws_s3_bucket_server_side_encryption_configuration" "{name}" {{
  bucket = {link}
  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = {algorithm}
    }}
  }}
}}
'''

    def test_linked_aes256_is_non_kms_not_unencrypted(self):
        row = finding("5c693b23d264")
        path = CORPUS / row["candidate_id"] / "main.tf"
        value, facts, _ = s3_kms_control_decision(row, path)
        self.assertEqual("yes", value)
        affected = [item for item in facts["standalone_configurations"]
                    if item["relationship"] == "affected_bucket"]
        self.assertEqual(1, len(affected))
        self.assertEqual("AES256", affected[0]["algorithm"])
        self.assertTrue(facts["explicit_sse_configuration_present"])
        self.assertFalse(facts["absence_of_required_control"])
        self.assertEqual("KMS-based S3 default encryption", facts["control"])

    def test_inline_aes256_is_non_kms(self):
        row = finding("380fea3085aa")
        path = CORPUS / row["candidate_id"] / "main.tf"
        value, facts, refs = s3_kms_control_decision(row, path)
        self.assertEqual("yes", value)
        self.assertEqual("AES256", facts["inline_configurations"][0]["algorithm"])
        self.assertTrue(facts["explicit_sse_configuration_present"])
        self.assertTrue(any("server_side_encryption_configuration {" in item.get("literal", "")
                            for item in refs))

    def test_other_bucket_configuration_does_not_satisfy_affected_bucket(self):
        row = finding("3797cf90e3b2")
        path = CORPUS / row["candidate_id"] / "main.tf"
        value, facts, _ = s3_kms_control_decision(row, path)
        self.assertEqual("yes", value)
        self.assertTrue(facts["absence_of_required_control"])
        self.assertFalse(facts["explicit_sse_configuration_present"])
        self.assertTrue(facts["standalone_configurations"])
        self.assertTrue(all(item["relationship"] == "other_bucket"
                            for item in facts["standalone_configurations"]))
        self.assertTrue(facts["candidate_scope_examined"])

    def test_explicit_equivalent_bucket_reference(self):
        value, facts, _ = self.decide(self.config(link="aws_s3_bucket.target.bucket"))
        self.assertEqual("yes", value)
        self.assertEqual("affected_bucket", facts["standalone_configurations"][0]["relationship"])

    def test_explicit_kms_in_failed_finding_raises_conflict(self):
        with self.assertRaisesRegex(ValueError, "Explicit aws:kms configuration"):
            self.decide(self.config(algorithm='"aws:kms"'))

    def test_unresolved_bucket_link_is_unknown(self):
        value, facts, _ = self.decide(self.config(link="var.bucket_id"))
        self.assertEqual("unknown", value)
        self.assertEqual("unresolved_reference", facts["unknown_reason_code"])
        self.assertEqual("var.bucket_id", facts["unresolved_bucket_links"][0]["bucket_expression"])

    def test_dynamic_algorithm_is_unknown(self):
        value, facts, _ = self.decide(self.config(algorithm="var.algorithm"))
        self.assertEqual("unknown", value)
        self.assertEqual("unresolved_reference", facts["unknown_reason_code"])

    def test_dynamic_inline_sse_block_is_unknown(self):
        bucket = '''resource "aws_s3_bucket" "target" {
  bucket = "target"
  dynamic "server_side_encryption_configuration" {
    for_each = var.encryption_rules
    content {
      rule {
        apply_server_side_encryption_by_default {
          sse_algorithm = server_side_encryption_configuration.value.algorithm
        }
      }
    }
  }
}
'''
        value, facts, _ = self.decide(bucket=bucket)
        self.assertEqual("unknown", value)
        self.assertEqual("unsupported_static_construct", facts["unknown_reason_code"])
        self.assertIn("aws_s3_bucket.target.dynamic_sse", facts["dynamic_control_constructs"])

    def test_multiple_affected_configurations_are_unknown(self):
        value, facts, _ = self.decide(self.config("first") + self.config("second"))
        self.assertEqual("unknown", value)
        self.assertEqual("insufficient_static_relationship", facts["unknown_reason_code"])

    def test_external_module_prevents_absence_proof(self):
        row = finding("2af107363de5")
        path = CORPUS / row["candidate_id"] / "main.tf"
        value, facts, _ = s3_kms_control_decision(row, path)
        self.assertEqual("unknown", value)
        self.assertEqual("unsupported_static_construct", facts["unknown_reason_code"])
        self.assertEqual({"vpc_primary", "vpc_dr"}, {item["name"] for item in facts["modules"]})

    def test_missing_source_and_parser_failure_are_not_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.tf"
            with self.assertRaisesRegex(ValueError, "source missing"):
                s3_kms_control_decision({"resource": "aws_s3_bucket.target"}, missing)
            malformed = Path(folder) / "main.tf"
            malformed.write_text('resource "aws_s3_bucket" "target" {\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot parse candidate Terraform source"):
                s3_kms_control_decision({"resource": "aws_s3_bucket.target"}, malformed)

    def test_not_applicable_uses_matrix_guard(self):
        values = {feature: "yes" for feature in extractor.FEATURES}
        guarded = extractor.enforce_applicability(
            values, {feature: False for feature in extractor.FEATURES})
        self.assertEqual("not_applicable", guarded["encryption_missing"])

    def test_validator_rejects_fabricated_absence_fact(self):
        row = finding("3797cf90e3b2")
        with tempfile.TemporaryDirectory() as folder:
            input_path = Path(folder) / "finding.csv"
            output_path = Path(folder) / "features.csv"
            with input_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=row.keys())
                writer.writeheader()
                writer.writerow(row)
            args = ["extract_finding_context_features.py", "--input", str(input_path),
                    "--output", str(output_path)]
            with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
                extractor.main()
            self.assertEqual([], validator.validate_file(output_path).errors)
            with output_path.open(encoding="utf-8", newline="") as stream:
                feature_row = next(csv.DictReader(stream))
            evidence = json.loads(feature_row["feature_evidence"])
            evidence["features"]["encryption_missing"]["facts"]["absence_of_required_control"] = False
            feature_row["feature_evidence"] = json.dumps(evidence)
            with output_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=feature_row.keys())
                writer.writeheader()
                writer.writerow(feature_row)
            report = validator.validate_file(output_path)
        self.assertTrue(any(group == "control" and "absence_of_required_control" in message
                            for group, message in report.errors))


if __name__ == "__main__":
    unittest.main()
