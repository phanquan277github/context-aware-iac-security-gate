"""Evidence-detail regressions for unclassified IAM Actions and external modules."""

import copy
import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract_finding_context_features as extractor
import validate_context_evidence as validator
from context_evidence import s3_kms_control_decision


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
TAXONOMY = ROOT / "dataset/main/context/iam_action_capability_taxonomy.yaml"
TARGETS = {
    "db321cd08bc405689fb5fa0e24a61379c9abab5b1984dbdb2bf3e7b7c4f3abbd",
    "4193a42c8314e702a509abc844441d5756e2bb915bc614b6ba1b70761959ab37",
    "2af107363de5c8059c91a03ba03c6a0becf81b179d474410d8b3746485c7c4cc",
    "37467c4cf10ec069b193e97cd489e4a97541ad75f1128a4c7ba44b6d06d4f82e",
}


class UnknownDetailAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.input = Path(cls.folder.name) / "findings.csv"
        cls.output = Path(cls.folder.name) / "features.csv"
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            findings = [row for row in reader if row["finding_id"] in TARGETS]
        assert len(findings) == 4
        with cls.input.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            writer.writerows(findings)
        args = ["extract_finding_context_features.py", "--input", str(cls.input),
                "--output", str(cls.output)]
        with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
            extractor.main()
        with cls.output.open(encoding="utf-8", newline="") as stream:
            cls.rows = list(csv.DictReader(stream))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def basis(self, row):
        feature = "privilege_impact" if row["check_id"] in {"CKV_AWS_290", "CKV_AWS_355"} else "encryption_missing"
        return feature, json.loads(row["feature_evidence"])["features"][feature]

    def validate_mutation(self, row, mutate):
        changed = copy.deepcopy(row)
        evidence = json.loads(changed["feature_evidence"])
        feature = "privilege_impact" if changed["check_id"] in {"CKV_AWS_290", "CKV_AWS_355"} else "encryption_missing"
        mutate(evidence["features"][feature])
        changed["feature_evidence"] = json.dumps(evidence)
        path = Path(self.folder.name) / "mutation.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=changed.keys())
            writer.writeheader()
            writer.writerow(changed)
        return validator.validate_file(path)

    def test_four_unknown_values_have_source_specific_details(self):
        self.assertEqual(4, len(self.rows))
        self.assertEqual([], validator.validate_file(self.output).errors)
        for row in self.rows:
            feature, basis = self.basis(row)
            self.assertEqual("unknown", row[feature])
            if feature == "privilege_impact":
                self.assertEqual("unclassified_action", basis["unknown_reason_code"])
                self.assertIn("ec2:TagResource", basis["unknown_reason_detail"])
                self.assertIn("d008-v1", basis["unknown_reason_detail"])
                iam = basis["facts"]["iam"]
                self.assertIn("ec2:TagResource", iam["resolved_actions"])
                self.assertIn("unclassified", {entry["class"] for entry in iam["action_capabilities"]})
            else:
                self.assertEqual("unsupported_static_construct", basis["unknown_reason_code"])
                self.assertEqual({"vpc_primary", "vpc_dr"},
                                 {entry["name"] for entry in basis["facts"]["modules"]})
                self.assertIn('module "vpc_primary"', basis["unknown_reason_detail"])
                self.assertIn('module "vpc_dr"', basis["unknown_reason_detail"])

    def test_iam_detail_fabrication_and_reason_mutation_rejected(self):
        row = next(row for row in self.rows if row["check_id"] == "CKV_AWS_290")
        for mutate in (
            lambda basis: basis.update(unknown_reason_detail=basis["unknown_reason_detail"].replace(
                "ec2:TagResource", "ec2:FakeAction")),
            lambda basis: basis.update(unknown_reason_code="unresolved_action"),
        ):
            with self.subTest(mutate=mutate):
                report = self.validate_mutation(row, mutate)
                self.assertIn("iam", {group for group, _ in report.errors})

    def test_taxonomy_is_still_unclassified(self):
        taxonomy = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
        self.assertEqual("d008-v1", taxonomy["taxonomy_version"])
        self.assertIn("ec2:TagResource", taxonomy["unclassified_observed"])
        for category in ("read_observation", "operational_mutation",
                         "privilege_administration_or_unrestricted"):
            self.assertNotIn("ec2:TagResource", taxonomy[category])
        for row in self.rows:
            if row["check_id"] in {"CKV_AWS_290", "CKV_AWS_355"}:
                self.assertEqual("unknown", row["privilege_impact"])

    def test_module_detail_omission_and_fabrication_rejected(self):
        row = next(row for row in self.rows if row["check_id"] == "CKV_AWS_145")
        for mutate in (
            lambda basis: basis.update(unknown_reason_detail=basis["unknown_reason_detail"].replace(
                'module "vpc_dr"', "")),
            lambda basis: basis.update(unknown_reason_detail=basis["unknown_reason_detail"].replace(
                'module "vpc_dr"', 'module "vpc_fake"')),
            lambda basis: basis["facts"]["modules"][0].update(name="vpc_fake"),
        ):
            with self.subTest(mutate=mutate):
                report = self.validate_mutation(row, mutate)
                self.assertIn("control", {group for group, _ in report.errors})

    def test_candidate_without_external_module_unaffected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text('resource "aws_s3_bucket" "target" {\n  bucket = "target"\n}\n',
                            encoding="utf-8")
            value, facts, _ = s3_kms_control_decision({"resource": "aws_s3_bucket.target"}, path)
            self.assertEqual("yes", value)
            self.assertEqual([], facts["modules"])
            self.assertTrue(facts["absence_of_required_control"])


if __name__ == "__main__":
    unittest.main()
