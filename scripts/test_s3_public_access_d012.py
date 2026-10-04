"""D-012 regression cases for affected-bucket static public-access proof."""

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

from context_evidence import s3_public_access_decision, source_inventory
import extract_finding_context_features as extractor
from extract_finding_context_features import FEATURES, enforce_applicability
import validate_context_evidence as evidence_validator


BUCKET = 'resource "aws_s3_bucket" "target" {\n  bucket = "target-bucket"\n%s\n}\n'
ACL = ('resource "aws_s3_bucket_acl" "target" {\n'
       '  bucket = aws_s3_bucket.target.id\n  acl = "public-read"\n}\n')
PAB_FALSE = ('resource "aws_s3_bucket_public_access_block" "target" {\n'
             '  bucket = aws_s3_bucket.target.id\n'
             '  block_public_acls = false\n  ignore_public_acls = false\n'
             '  block_public_policy = false\n  restrict_public_buckets = false\n}\n')
PAB_TRUE = PAB_FALSE.replace("= false", "= true")
POLICY = ('resource "aws_s3_bucket_policy" "target" {\n'
          '  bucket = aws_s3_bucket.target.id\n'
          '  policy = jsonencode({ Statement = [{ Effect = "Allow", '
          'Principal = "*", Action = "s3:GetObject", '
          'Resource = "${aws_s3_bucket.target.arn}/*"%s }] })\n}\n')
DATA_POLICY = ('data "aws_iam_policy_document" "public" {\n'
               '  statement {\n    effect = "Allow"\n'
               '    principals { type = "*" identifiers = ["*"] }\n'
               '    actions = ["s3:GetObject"]\n'
               '    resources = ["${aws_s3_bucket.target.arn}/*"]\n%s'
               '  }\n}\n'
               'resource "aws_s3_bucket_policy" "target" {\n'
               '  bucket = aws_s3_bucket.target.id\n'
               '  policy = data.aws_iam_policy_document.public.json\n}\n')


class S3PublicAccessD012Tests(unittest.TestCase):
    def decide(self, source):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text(source, encoding="utf-8")
            return s3_public_access_decision(source_inventory(path), "target")

    def test_public_acl_and_unblocked_acl_flags_is_yes(self):
        value, facts, refs = self.decide(BUCKET % "" + ACL + PAB_FALSE)
        self.assertEqual("yes", value)
        self.assertEqual("public_acl_with_unblocked_pab", facts["selected_mechanism"])
        self.assertTrue(any(ref.get("literal") == 'acl = "public-read"' for ref in refs))

    def test_public_read_write_inline_acl_is_yes(self):
        value, facts, _ = self.decide(
            BUCKET % '  acl = "public-read-write"' + PAB_FALSE)
        self.assertEqual("yes", value)
        self.assertEqual("aws_s3_bucket.target", facts["selected_resource"])

    def test_public_policy_and_unblocked_policy_flags_is_yes(self):
        value, facts, refs = self.decide(BUCKET % "" + POLICY % "" + PAB_FALSE)
        self.assertEqual("yes", value)
        self.assertEqual("public_policy_with_unblocked_pab", facts["selected_mechanism"])
        self.assertTrue(any("Principal = \"*\"" in ref.get("literal", "") for ref in refs))

    def test_resolved_data_policy_document_is_yes(self):
        value, facts, refs = self.decide(BUCKET % "" + DATA_POLICY % "" + PAB_FALSE)
        self.assertEqual("yes", value)
        self.assertEqual("public_policy_with_unblocked_pab", facts["selected_mechanism"])
        self.assertTrue(any('data "aws_iam_policy_document" "public"' ==
                            ref.get("literal") for ref in refs))

    def test_data_policy_document_condition_is_unknown(self):
        condition = ('    condition { test = "IpAddress" variable = "aws:SourceIp" '
                     'values = ["10.0.0.0/8"] }\n')
        value, facts, _ = self.decide(BUCKET % "" + DATA_POLICY % condition + PAB_FALSE)
        self.assertEqual("unknown", value)
        self.assertIn("Condition", facts["policy_paths"][0]["statements"][0]["reason"])

    def test_all_four_pab_flags_true_is_no(self):
        value, facts, _ = self.decide(BUCKET % "" + PAB_TRUE)
        self.assertEqual("no", value)
        self.assertEqual("all_four_bucket_pab_flags_true", facts["selected_mechanism"])
        self.assertEqual({True}, set(facts["pab_flags"].values()))

    def test_missing_pab_with_public_acl_is_unknown(self):
        value, facts, _ = self.decide(BUCKET % "" + ACL)
        self.assertEqual("unknown", value)
        self.assertIsNone(facts["pab_flags"])

    def test_missing_pab_with_public_policy_is_unknown(self):
        value, facts, _ = self.decide(BUCKET % "" + POLICY % "")
        self.assertEqual("unknown", value)
        self.assertTrue(facts["policy_paths"][0]["public"])

    def test_unsupported_policy_condition_is_unknown(self):
        condition = ', Condition = { IpAddress = { "aws:SourceIp" = "10.0.0.0/8" } }'
        value, facts, _ = self.decide(BUCKET % "" + POLICY % condition + PAB_FALSE)
        self.assertEqual("unknown", value)
        self.assertIn("Condition", facts["policy_paths"][0]["statements"][0]["reason"])

    def test_partial_pab_is_unknown(self):
        partial = PAB_FALSE.replace("  ignore_public_acls = false\n", "")
        value, facts, _ = self.decide(BUCKET % "" + ACL + partial)
        self.assertEqual("unknown", value)
        self.assertIsNone(facts["pab_flags"]["ignore_public_acls"])

    def test_dynamic_acl_and_policy_are_unknown(self):
        dynamic_acl = BUCKET % "  acl = var.acl" + PAB_FALSE
        self.assertEqual("unknown", self.decide(dynamic_acl)[0])
        dynamic_policy = ('resource "aws_s3_bucket_policy" "target" {\n'
                          '  bucket = aws_s3_bucket.target.id\n'
                          '  policy = var.policy_json\n}\n')
        value, facts, _ = self.decide(BUCKET % "" + dynamic_policy + PAB_FALSE)
        self.assertEqual("unknown", value)
        self.assertFalse(facts["policy_paths"][0]["resolved_document"])

    def test_wrong_bucket_controls_do_not_affect_target(self):
        other = (BUCKET.replace('"target"', '"other"') %
                 '  acl = "public-read"')
        other_pab = PAB_FALSE.replace('aws_s3_bucket.target.id', 'aws_s3_bucket.other.id')
        value, facts, _ = self.decide(BUCKET % "" + other + other_pab)
        self.assertEqual("unknown", value)
        self.assertEqual([], facts["acl_paths"])
        self.assertIsNone(facts["pab_flags"])

    def test_wrong_bucket_policy_resource_is_unknown(self):
        wrong = (POLICY % "").replace(
            "aws_s3_bucket.target.arn", "aws_s3_bucket.other.arn")
        value, _, _ = self.decide(BUCKET % "" + wrong + PAB_FALSE)
        self.assertEqual("unknown", value)

    def test_non_applicable_guard_is_unchanged(self):
        features = {feature: "unknown" for feature in FEATURES}
        features["public_access"] = "yes"
        applicability = {feature: False for feature in FEATURES}
        self.assertEqual("not_applicable",
                         enforce_applicability(features, applicability)["public_access"])

    def test_missing_candidate_source_is_extraction_failure(self):
        applicability = {feature: feature in {"resource_role", "public_access"}
                         for feature in FEATURES}
        with self.assertRaisesRegex(ValueError, "candidate source path required"):
            extractor.extract_features({"check_id": "CKV2_AWS_6",
                                        "resource": "aws_s3_bucket.target",
                                        "resource_type": "aws_s3_bucket"},
                                       applicability, 'resource "aws_s3_bucket" "target" {}')

    def test_extractor_and_evidence_validator_agree_on_yes_and_no(self):
        for expected, controls in (("yes", ACL + PAB_FALSE), ("no", PAB_TRUE)):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source = root / "synthetic_s3" / "main.tf"
                source.parent.mkdir()
                bucket = BUCKET % ""
                source.write_text(bucket + controls, encoding="utf-8")
                finding = {"finding_id": f"d012-{expected}", "candidate_id": "synthetic_s3",
                           "scenario_id": "synthetic", "check_id": "CKV2_AWS_6",
                           "check_name": "S3 Public Access Block", "resource": "aws_s3_bucket.target",
                           "resource_type": "aws_s3_bucket", "line_start": "1",
                           "line_end": str(len(bucket.splitlines())), "evaluated_keys": "[]",
                           "scanner": "checkov", "scanner_version": "3.3.17",
                           "check_result": "FAILED"}
                input_path, output_path = root / "findings.csv", root / "features.csv"
                with input_path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=finding)
                    writer.writeheader()
                    writer.writerow(finding)
                argv = ["extract_finding_context_features.py", "--input", str(input_path),
                        "--output", str(output_path)]
                with patch.object(extractor, "CORPUS_ROOT", root), patch.object(sys, "argv", argv):
                    with redirect_stdout(io.StringIO()):
                        extractor.main()
                with output_path.open(newline="", encoding="utf-8") as stream:
                    result = next(csv.DictReader(stream))
                self.assertEqual(expected, result["public_access"])
                self.assertEqual([], evidence_validator.validate_file(output_path).errors)
                basis = json.loads(result["feature_evidence"])["features"]["public_access"]
                self.assertEqual("d012-v1", basis["method_version"])
                self.assertEqual(expected, basis["facts"]["static_public_access_relation"])
                if expected == "no":
                    self.assertTrue(basis["scope_examined"])
                altered = json.loads(result["feature_evidence"])
                altered["features"]["public_access"]["facts"]["d012_decision"][
                    "selected_mechanism"] = "fabricated"
                result["feature_evidence"] = json.dumps(altered)
                with output_path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=result)
                    writer.writeheader()
                    writer.writerow(result)
                report = evidence_validator.validate_file(output_path)
                self.assertIn("decision_basis", {group for group, _ in report.errors})


if __name__ == "__main__":
    unittest.main()
