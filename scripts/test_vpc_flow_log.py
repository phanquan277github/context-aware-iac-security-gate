"""Regression tests for CKV2_AWS_11 affected-VPC flow-log evidence."""

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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_evidence import vpc_flow_log_decision
import extract_finding_context_features as extractor
import validate_context_evidence as validator


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
CORPUS = ROOT / "dataset/main/corpus/geniac_tier_a"


class VpcFlowLogTests(unittest.TestCase):
    def decide(self, extra=""):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text('resource "aws_vpc" "target" {\n  cidr_block = "10.0.0.0/16"\n}\n'
                            + extra, encoding="utf-8")
            return vpc_flow_log_decision(
                {"resource": "aws_vpc.target", "resource_type": "aws_vpc"}, path)

    @staticmethod
    def flow(name, relation):
        return f'\nresource "aws_flow_log" "{name}" {{\n  vpc_id = {relation}\n}}\n'

    def test_no_flow_log_proves_candidate_scope_absence(self):
        value, facts, refs = self.decide()
        self.assertEqual("yes", value)
        self.assertTrue(facts["absence_of_affected_vpc_flow_log"])
        self.assertEqual([], facts["flow_log_declarations"])
        self.assertTrue(any(item.get("sha256") for item in refs))

    def test_other_vpc_flow_log_does_not_cover_affected_vpc(self):
        extra = ('resource "aws_vpc" "other" {}\n' +
                 self.flow("other", "aws_vpc.other.id"))
        value, facts, refs = self.decide(extra)
        self.assertEqual("yes", value)
        self.assertEqual("other_vpc", facts["flow_log_declarations"][0]["relationship"])
        self.assertEqual("aws_vpc.other", facts["flow_log_declarations"][0]["resolved_target_vpc"])
        self.assertTrue(any(item.get("literal") == "vpc_id = aws_vpc.other.id" for item in refs))

    def test_linked_flow_log_conflicts_with_failed_finding(self):
        with self.assertRaisesRegex(ValueError, "conflicts with linked flow log"):
            self.decide(self.flow("linked", "aws_vpc.target.id"))

    def test_multiple_flow_logs_other_and_linked(self):
        extra = ('resource "aws_vpc" "other" {}\n' +
                 self.flow("other", "aws_vpc.other.id") +
                 self.flow("target", "aws_vpc.target.id"))
        with self.assertRaisesRegex(ValueError, "conflicts with linked flow log"):
            self.decide(extra)

    def test_unresolved_reference_is_unknown(self):
        value, facts, _ = self.decide(self.flow("maybe", "var.vpc_id"))
        self.assertEqual("unknown", value)
        self.assertEqual("unresolved_reference", facts["unknown_reason_code"])
        self.assertEqual("var.vpc_id", facts["flow_log_declarations"][0]["vpc_id_expression"])

    def test_reference_to_undeclared_vpc_is_not_proven_other(self):
        value, facts, _ = self.decide(self.flow("maybe", "aws_vpc.absent.id"))
        self.assertEqual("unknown", value)
        self.assertEqual("unresolved", facts["flow_log_declarations"][0]["relationship"])

    def test_dynamic_expression_is_unknown(self):
        value, facts, _ = self.decide(self.flow("maybe", "aws_vpc.targets[count.index].id"))
        self.assertEqual("unknown", value)
        self.assertEqual("unresolved", facts["flow_log_declarations"][0]["relationship"])

    def test_external_module_is_unknown(self):
        value, facts, _ = self.decide('module "network" {\n  source = "./network"\n}\n')
        self.assertEqual("unknown", value)
        self.assertEqual("unsupported_static_construct", facts["unknown_reason_code"])

    def test_missing_source_and_parser_failure_are_errors(self):
        row = {"resource": "aws_vpc.target", "resource_type": "aws_vpc"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            with self.assertRaisesRegex(ValueError, "source missing"):
                vpc_flow_log_decision(row, path)
            path.write_text('resource "aws_vpc" "target" {\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot parse candidate Terraform source"):
                vpc_flow_log_decision(row, path)

    def test_not_applicable_remains_matrix_guarded(self):
        values = {feature: "yes" for feature in extractor.FEATURES}
        guarded = extractor.enforce_applicability(
            values, {feature: False for feature in extractor.FEATURES})
        self.assertEqual("not_applicable", guarded["logging_missing"])

    def test_current_blocker_resolves_other_vpc_relation(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            row = next(item for item in csv.DictReader(stream) if item["finding_id"].startswith("985fccd1919f"))
        value, facts, _ = vpc_flow_log_decision(row, CORPUS / row["candidate_id"] / "main.tf")
        self.assertEqual("yes", value)
        self.assertEqual("aws_vpc.secondary", facts["affected_vpc"])
        self.assertEqual("aws_vpc.primary", facts["flow_log_declarations"][0]["resolved_target_vpc"])
        self.assertEqual("other_vpc", facts["flow_log_declarations"][0]["relationship"])

    def test_validator_rejects_forged_relation_affected_vpc_and_absence(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            row = next(item for item in csv.DictReader(stream) if item["finding_id"].startswith("985fccd1919f"))
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
            with output_path.open(encoding="utf-8", newline="") as stream:
                result = next(csv.DictReader(stream))
            self.assertEqual([], validator.validate_file(output_path).errors)
            for mutate in (
                lambda f: f["flow_log_declarations"][0].update(relationship="affected_vpc"),
                lambda f: f.update(affected_vpc="aws_vpc.primary"),
                lambda f: f.update(absence_of_affected_vpc_flow_log=False),
            ):
                changed = copy.deepcopy(result)
                evidence = json.loads(changed["feature_evidence"])
                mutate(evidence["features"]["logging_missing"]["facts"])
                changed["feature_evidence"] = json.dumps(evidence)
                with output_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=changed.keys())
                    writer.writeheader()
                    writer.writerow(changed)
                self.assertTrue(any(group == "control" for group, _ in
                                    validator.validate_file(output_path).errors))


if __name__ == "__main__":
    unittest.main()
