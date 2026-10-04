"""Regression tests for CKV_AWS_38 affected-EKS endpoint evidence."""

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

from context_evidence import eks_public_endpoint_decision
import extract_finding_context_features as extractor
import validate_context_evidence as validator


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
PILOT = ROOT / "results/context_feature_pilot/pilot_findings.csv"
CORPUS = ROOT / "dataset/main/corpus/geniac_tier_a"


class EksPublicEndpointTests(unittest.TestCase):
    def decide(self, config):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text('resource "aws_eks_cluster" "target" {\n' + config + '\n}\n',
                            encoding="utf-8")
            return eks_public_endpoint_decision(
                {"resource": "aws_eks_cluster.target", "resource_type": "aws_eks_cluster"}, path)

    def config(self, endpoint="", cidrs=""):
        return (' vpc_config {\n  subnet_ids = []\n' + endpoint + cidrs + ' }')

    def test_explicit_true_preserves_accepted_values_without_fabricated_cidr(self):
        values, facts, refs = self.decide(self.config('  endpoint_public_access = true\n'))
        self.assertEqual({"internet_exposure": "yes", "reachability": "internet",
                          "public_access": "yes"}, values)
        self.assertEqual("explicit_true", facts["endpoint_attribute_state"])
        self.assertIsNone(facts["public_access_cidrs_raw"])
        self.assertIsNone(facts["source_cidr"])
        self.assertNotIn("0.0.0.0/0", str(refs))

    def test_explicit_false_does_not_infer_complete_private_scope(self):
        values, facts, _ = self.decide(self.config('  endpoint_public_access = false\n'))
        self.assertEqual({"unknown"}, set(values.values()))
        self.assertEqual("explicit_false", facts["endpoint_attribute_state"])
        self.assertEqual("insufficient_static_relationship",
                         facts["feature_unknowns"]["public_access"]["code"])

    def test_absent_attribute_is_not_provider_default(self):
        values, facts, refs = self.decide(self.config())
        self.assertEqual({"unknown"}, set(values.values()))
        self.assertTrue(facts["endpoint_attribute_absent"])
        self.assertFalse(facts["provider_defaults_inferred"])
        self.assertEqual("insufficient_static_path",
                         facts["feature_unknowns"]["reachability"]["code"])
        self.assertNotIn("0.0.0.0/0", str(refs))

    def test_variable_endpoint_is_unresolved(self):
        values, facts, _ = self.decide(self.config('  endpoint_public_access = var.public\n'))
        self.assertEqual({"unknown"}, set(values.values()))
        self.assertEqual("var.public", facts["endpoint_public_access_raw"])
        self.assertEqual("unresolved_reference",
                         facts["feature_unknowns"]["internet_exposure"]["code"])

    def test_explicit_public_cidr_is_recorded(self):
        values, facts, refs = self.decide(self.config(
            '  endpoint_public_access = true\n',
            '  public_access_cidrs = ["0.0.0.0/0"]\n'))
        self.assertEqual("yes", values["public_access"])
        self.assertEqual(['0.0.0.0/0'], facts["public_access_cidrs_resolved"])
        self.assertTrue(any("0.0.0.0/0" in item.get("literal", "") for item in refs))

    def test_unresolved_public_cidrs_is_unknown(self):
        values, facts, _ = self.decide(self.config(
            '  endpoint_public_access = true\n',
            '  public_access_cidrs = var.allowed_cidrs\n'))
        self.assertEqual({"unknown"}, set(values.values()))
        self.assertEqual("var.allowed_cidrs", facts["public_access_cidrs_raw"])
        self.assertEqual("unresolved_reference",
                         facts["feature_unknowns"]["public_access"]["code"])

    def test_dynamic_vpc_config_is_static_uncertainty(self):
        values, facts, _ = self.decide('''dynamic "vpc_config" {
 for_each = var.configs
 content { subnet_ids = vpc_config.value.subnets }
}''')
        self.assertEqual({"unknown"}, set(values.values()))
        self.assertEqual("unsupported_static_construct",
                         facts["feature_unknowns"]["reachability"]["code"])

    def test_missing_source_and_malformed_hcl_are_failures(self):
        row = {"resource": "aws_eks_cluster.target", "resource_type": "aws_eks_cluster"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            with self.assertRaisesRegex(ValueError, "source missing"):
                eks_public_endpoint_decision(row, path)
            path.write_text('resource "aws_eks_cluster" "target" {\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                eks_public_endpoint_decision(row, path)

    def test_not_applicable_uses_matrix_guard(self):
        values = {feature: "yes" for feature in extractor.FEATURES}
        guarded = extractor.enforce_applicability(
            values, {feature: False for feature in extractor.FEATURES})
        self.assertEqual("not_applicable", guarded["public_access"])

    def test_exact_current_blocker_has_absent_attribute(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            row = next(item for item in csv.DictReader(stream) if item["finding_id"].startswith("c58ee14aded5"))
        values, facts, _ = eks_public_endpoint_decision(row, CORPUS / row["candidate_id"] / "main.tf")
        self.assertEqual({"unknown"}, set(values.values()))
        self.assertEqual("absent", facts["endpoint_attribute_state"])
        self.assertTrue(facts["public_access_cidrs_absent"])

    def test_pilot_eks_values_stay_accepted(self):
        with PILOT.open(encoding="utf-8", newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if row["check_id"] == "CKV_AWS_38"]
        self.assertEqual(2, len(rows))
        for row in rows:
            values, _, _ = eks_public_endpoint_decision(
                row, CORPUS / row["candidate_id"] / "main.tf")
            self.assertEqual(("yes", "internet", "yes"), tuple(values.values()))

    def test_validator_rejects_forged_facts_refs_and_reason(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if row["finding_id"].startswith(
                ("c58ee14aded5", "67280ac8681f"))]
        with tempfile.TemporaryDirectory() as folder:
            input_path, output_path = Path(folder) / "input.csv", Path(folder) / "output.csv"
            with input_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader(); writer.writerows(rows)
            with patch.object(sys, "argv", ["extract", "--input", str(input_path),
                                            "--output", str(output_path)]), redirect_stdout(io.StringIO()):
                extractor.main()
            with output_path.open(encoding="utf-8", newline="") as stream:
                original = list(csv.DictReader(stream))
            self.assertEqual([], validator.validate_file(output_path).errors)
            mutations = (
                (0, lambda basis: basis["facts"].update(endpoint_public_access=False)),
                (1, lambda basis: basis["facts"].update(endpoint_attribute_absent=False,
                                                         endpoint_public_access=True)),
                (0, lambda basis: basis["facts"].update(public_access_cidrs_resolved=["0.0.0.0/0"])),
                (0, lambda basis: basis["facts"].update(affected_cluster="aws_eks_cluster.wrong")),
                (0, lambda basis: basis["facts"]["vpc_config_span"].update(line_start=1)),
                (0, lambda basis: basis["source_refs"].clear()),
                (1, lambda basis: basis.update(unknown_reason_code="unresolved_reference")),
            )
            for index, mutate in mutations:
                changed = copy.deepcopy(original)
                evidence = json.loads(changed[index]["feature_evidence"])
                mutate(evidence["features"]["public_access"])
                changed[index]["feature_evidence"] = json.dumps(evidence)
                with output_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=changed[0].keys())
                    writer.writeheader(); writer.writerows(changed)
                self.assertTrue(validator.validate_file(output_path).errors)


if __name__ == "__main__":
    unittest.main()
