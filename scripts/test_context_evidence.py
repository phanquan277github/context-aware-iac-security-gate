"""Regression tests for D-009 Evidence v1 and D-010 provenance."""

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

import context_evidence
import extract_finding_context_features as extractor
import validate_context_evidence as validator


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "results/context_feature_pilot/pilot_findings.csv"
SAVED = ROOT / "results/context_feature_pilot/finding_context_features_pilot.csv"


def load_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class EvidenceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.replay = Path(cls.folder.name) / "replay.csv"
        args = ["extract_finding_context_features.py", "--input", str(PILOT),
                "--output", str(cls.replay)]
        with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
            extractor.main()
        cls.rows = load_rows(cls.replay)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def validate_mutation(self, finding_index, change):
        rows = copy.deepcopy(self.rows)
        evidence = json.loads(rows[finding_index]["feature_evidence"])
        change(evidence)
        rows[finding_index]["feature_evidence"] = json.dumps(evidence)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mutated.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return validator.validate_file(path)

    def test_replay_has_only_approved_d011_value_changes_and_v1_valid(self):
        saved = load_rows(SAVED)
        self.assertEqual(20, len(self.rows))
        for old, new in zip(saved, self.rows):
            expected = dict(old)
            if old["check_id"] == "CKV_AWS_130":
                expected.update(reachability="internet", applicable_unknown_count="2",
                                applicable_unknown_features="internet_exposure|public_access")
            self.assertEqual({key: value for key, value in expected.items() if key != "feature_evidence"},
                             {key: value for key, value in new.items() if key != "feature_evidence"})
        report = validator.validate_file(self.replay)
        self.assertEqual([], report.errors)
        self.assertEqual(56, report.counts["applicable_bases"])
        self.assertEqual(124, report.counts["not_applicable_bases"])
        self.assertEqual(6, report.counts["unknown_bases"])

    def test_current_saved_pilot_is_valid_evidence_v1(self):
        saved = load_rows(SAVED)
        self.assertEqual(20, len(saved))
        self.assertTrue(all(json.loads(row["feature_evidence"]).get("contract_version") == "d009-v1"
                            for row in saved))
        report = validator.validate_file(SAVED)
        self.assertEqual([], report.errors)

    def test_legacy_evidence_is_not_misidentified_as_v1(self):
        def use_legacy_shape(evidence):
            evidence.clear()
            evidence["network"] = "legacy pilot evidence"

        report = self.validate_mutation(0, use_legacy_shape)
        self.assertGreater(len(report.errors), 0)
        self.assertTrue(any(group == "contract" for group, _ in report.errors))

    def test_unknown_requires_attempt_and_approved_reason(self):
        basis = json.loads(self.rows[2]["feature_evidence"])["features"]["public_access"]
        self.assertEqual("insufficient_access_control_evidence", basis["unknown_reason_code"])
        self.assertTrue(basis["unknown_reason_detail"])
        report = self.validate_mutation(2, lambda evidence:
            evidence["features"]["public_access"].pop("unknown_reason_code"))
        self.assertIn("decision_basis", {group for group, _ in report.errors})
        report = self.validate_mutation(2, lambda evidence:
            evidence["features"]["public_access"].update(unknown_reason_code="extractor_failed"))
        self.assertIn("decision_basis", {group for group, _ in report.errors})
        report = self.validate_mutation(2, lambda evidence:
            evidence["features"]["public_access"].pop("unknown_reason_detail"))
        self.assertIn("decision_basis", {group for group, _ in report.errors})

    def test_operational_failure_cannot_be_unknown(self):
        rows = copy.deepcopy(self.rows)
        rows[2]["feature_extraction_status"] = "SOURCE_MISSING"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "failed.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = validator.validate_file(path)
        self.assertTrue(any("operational extraction failure" in message for _, message in report.errors))

    def test_s3_candidate_specific_unknown_does_not_infer_public(self):
        for row in self.rows:
            if row["check_id"] != "CKV2_AWS_6":
                continue
            basis = json.loads(row["feature_evidence"])["features"]["public_access"]
            self.assertEqual("unknown", row["public_access"])
            self.assertEqual("insufficient_access_control_evidence", basis["unknown_reason_code"])
            facts = basis["facts"]
            self.assertEqual(row["resource"], facts["bucket"])
            self.assertFalse(facts["provider_defaults_inferred"])
            self.assertEqual([], facts["explicit_controls"]["public_access_block"]["linked"])
            self.assertEqual([], facts["explicit_controls"]["bucket_policy"]["linked"])
            self.assertEqual([], facts["explicit_controls"]["bucket_acl"]["linked"])
            self.assertFalse(facts["explicit_controls"]["inline_acl_or_grant"])
            self.assertEqual(1, len(facts["candidate_scope_examined"]))

    def test_subnet_resolved_route_only_changes_reachability(self):
        for row in self.rows:
            if row["check_id"] != "CKV_AWS_130":
                continue
            evidence = json.loads(row["feature_evidence"])
            self.assertEqual("internet", row["reachability"])
            self.assertEqual("unknown", row["internet_exposure"])
            self.assertEqual("unknown", row["public_access"])
            facts = evidence["features"]["reachability"]["facts"]
            self.assertTrue(facts["resolved_route_path"])
            self.assertEqual("aws_route_table_association.public", facts["route_table_association"])
            self.assertEqual("aws_route_table.public", facts["route_table"])
            self.assertEqual("0.0.0.0/0", facts["default_route"])
            self.assertEqual("aws_internet_gateway.main", facts["internet_gateway"])
            self.assertEqual([], facts["unresolved_path_elements"])
            for feature in ("internet_exposure", "public_access"):
                basis = evidence["features"][feature]
                self.assertEqual("insufficient_static_relationship", basis["unknown_reason_code"])
                self.assertIn("Internet-origin inbound", basis["facts"]["unresolved_inbound_relationship"])
                self.assertEqual("true", basis["facts"]["related_cluster_configs"][0]["endpoint_public_access"])

    def test_subnet_route_mutation_is_rejected(self):
        report = self.validate_mutation(6, lambda evidence:
            evidence["features"]["reachability"]["facts"].update(default_route=None))
        self.assertIn("decision_basis", {group for group, _ in report.errors})

    def test_unresolved_subnet_gateway_does_not_prove_internet(self):
        row = next(row for row in load_rows(PILOT) if row["check_id"] == "CKV_AWS_130")
        source = ROOT / "dataset/main/corpus/geniac_tier_a" / row["candidate_id"] / "main.tf"
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "main.tf"
            candidate.write_text(source.read_text(encoding="utf-8").replace(
                "gateway_id = aws_internet_gateway.main.id", "gateway_id = var.gateway_id", 1),
                encoding="utf-8")
            proven, facts, _ = context_evidence.subnet_internet_route(
                row, context_evidence.source_inventory(candidate))
        self.assertFalse(proven)
        self.assertIn("default route to Internet Gateway", facts["unresolved_path_elements"])

    def test_egress_reachability_is_configured_rule_only(self):
        for row in self.rows:
            if row["check_id"] != "CKV_AWS_382":
                continue
            self.assertEqual("internet", row["reachability"])
            facts = json.loads(row["feature_evidence"])["features"]["reachability"]["facts"]
            self.assertEqual("egress", facts["direction"])
            self.assertEqual("0.0.0.0/0", facts["destination_cidr"])
            self.assertTrue(facts["configured_rule_reachability"])
            self.assertFalse(facts["runtime_workload_attachment_asserted"])
            self.assertFalse(facts["inbound_exposure_asserted"])

    def test_not_applicable_requires_matrix_hash(self):
        report = self.validate_mutation(0, lambda evidence:
            evidence["not_applicable"]["internet_exposure"].update(
                applicability_matrix_sha256="bad"))
        self.assertIn("applicability", {group for group, _ in report.errors})

    def test_source_literal_and_hash_are_verified(self):
        report = self.validate_mutation(16, lambda evidence:
            evidence["features"]["reachability"]["source_refs"][1].update(
                literal="fabricated_provider_default"))
        self.assertIn("source_refs", {group for group, _ in report.errors})
        report = self.validate_mutation(0, lambda evidence:
            evidence["provenance"].update(source_sha256="bad"))
        self.assertIn("provenance", {group for group, _ in report.errors})

    def test_corrupt_source_reference_reports_error(self):
        report = self.validate_mutation(0, lambda evidence:
            evidence["features"]["resource_role"]["source_refs"][0].update(path=[]))
        self.assertIn("source_refs", {group for group, _ in report.errors})

    def test_cross_candidate_source_reference_is_rejected(self):
        other = self.rows[1]["source_path"]
        report = self.validate_mutation(0, lambda evidence:
            evidence["features"]["resource_role"]["source_refs"][0].update(path=other))
        self.assertIn("source_refs", {group for group, _ in report.errors})

    def test_role_must_match_versioned_taxonomy(self):
        report = self.validate_mutation(0, lambda evidence:
            evidence["features"]["resource_role"]["facts"]["mapping_entry"].update(
                role="other"))
        self.assertIn("resource_role", {group for group, _ in report.errors})

    def test_iam_action_classification_must_match_taxonomy(self):
        report = self.validate_mutation(13, lambda evidence:
            evidence["features"]["privilege_impact"]["facts"]["iam"]["action_capabilities"][0].update(
                level=3))
        self.assertIn("iam", {group for group, _ in report.errors})

    def test_selected_iam_statement_requires_exact_source_reference(self):
        report = self.validate_mutation(12, lambda evidence:
            evidence["features"]["privilege_impact"]["source_refs"].pop())
        self.assertIn("iam", {group for group, _ in report.errors})

    def test_unresolved_iam_selection_rejects_unrelated_actions(self):
        report = validator.Report()
        validator.check_iam("wildcard_action", "unknown",
            {"taxonomy_version": "d008-v1", "evaluated_keys": "[]",
             "iam": {"iam_action_taxonomy_version": "d008-v1",
                     "statement_resolution": "unresolved", "actions": ["iam:*"]}},
            {"evaluated_keys": "[]"}, [], {}, report, "synthetic")
        self.assertIn("iam", {group for group, _ in report.errors})

    def test_eks_evidence_does_not_invent_cidr(self):
        eks = next(row for row in self.rows if row["check_id"] == "CKV_AWS_38")
        basis = json.loads(eks["feature_evidence"])["features"]["internet_exposure"]
        self.assertIsNone(basis["facts"]["source_cidr"])
        self.assertIn("endpoint_public_access", str(basis["source_refs"]))

    def test_missing_source_is_failure_not_unknown(self):
        with self.assertRaisesRegex(ValueError, "Required Terraform source missing"):
            context_evidence.source_inventory(Path(self.folder.name) / "absent.tf")

    def test_supported_iam_parser_failure_is_not_unknown(self):
        malformed = 'Statement = [{\n  Action = "s3:GetObject"\n'
        with self.assertRaisesRegex(ValueError, "could not be parsed"):
            extractor.validate_supported_iam_parse(
                malformed, '["policy/Statement/[0]/Action"]')
        # An absent Checkov statement index remains D-007 selection uncertainty.
        extractor.validate_supported_iam_parse(malformed, "[]")

    def test_partial_action_does_not_create_false_negative(self):
        def analyze(action):
            statement = ('Statement = [{\n  Effect = "Allow"\n'
                         f'  Action = {action}\n  Resource = "*"\n}}]')
            return extractor.analyze_iam_statement(
                statement, '["Statement/[0]/Action"]')["wildcard_action"]
        self.assertEqual("unknown", analyze('["s3:GetObject", var.more]'))
        self.assertEqual("yes", analyze('["s3:*", var.more]'))

    def test_logging_absence_requires_candidate_scope(self):
        row = next(row for row in load_rows(PILOT) if row["check_id"] == "CKV2_AWS_11")
        values = next(value for value in self.rows if value["finding_id"] == row["finding_id"])
        source = ROOT / "dataset/main/corpus/geniac_tier_a" / row["candidate_id"] / "main.tf"
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "main.tf"
            candidate.write_text(source.read_text(encoding="utf-8") +
                                 '\nresource "aws_flow_log" "existing" {}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot prove logging_missing=yes"):
                context_evidence.build_evidence(row, values,
                    {feature: feature in {"resource_role", "logging_missing"} for feature in extractor.FEATURES},
                    {}, candidate, extractor.APPLICABILITY)

    def test_s3_encryption_requires_linked_aes256(self):
        row = next(row for row in load_rows(PILOT) if row["check_id"] == "CKV_AWS_145")
        source = ROOT / "dataset/main/corpus/geniac_tier_a" / row["candidate_id"] / "main.tf"
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "main.tf"
            candidate.write_text(source.read_text(encoding="utf-8").replace(
                'sse_algorithm = "AES256"', 'sse_algorithm = "aws:kms"'), encoding="utf-8")
            inventory = context_evidence.source_inventory(candidate)
            result = context_evidence.linked_s3_encryption(inventory, "static_assets_primary")
            self.assertEqual("aws:kms", result[3])


if __name__ == "__main__":
    unittest.main()
