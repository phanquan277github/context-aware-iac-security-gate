"""D-011 regression tests for Checkov-selected inline security-group egress."""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_evidence import (build_evidence, facts_for_rule, finding_region, inline_egress_decision,
                              source_inventory)
from extract_finding_context_features import enforce_applicability, extract_features
import validate_context_evidence


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
CORPUS = ROOT / "dataset/main/corpus/geniac_tier_a"


class InlineEgressTests(unittest.TestCase):
    def decide(self, egress, *, index=0, ingress=""):
        source = f'''resource "aws_security_group" "test" {{
{ingress}
{egress}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text(source, encoding="utf-8")
            row = {"resource": "aws_security_group.test", "line_start": 1,
                   "line_end": len(source.splitlines()),
                   "evaluated_keys": json.dumps([f"egress/[{index}]/cidr_blocks"])}
            return inline_egress_decision(row, path)

    def test_inline_ipv4_default_destination_and_all_protocols(self):
        value, facts, refs = self.decide('''egress {
  from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}''')
        self.assertEqual("internet", value)
        self.assertEqual("egress", facts["direction"])
        self.assertEqual("0.0.0.0/0", facts["destination_cidr"])
        self.assertEqual("all", facts["protocol_scope"])
        self.assertEqual(0, facts["selected_egress_index"])
        self.assertTrue(any("egress {" in item["literal"] and
                            'cidr_blocks = ["0.0.0.0/0"]' in item["literal"]
                            for item in refs))

    def test_specific_protocol_preserves_scope_with_internet_destination(self):
        value, facts, _ = self.decide('''egress {
  from_port = 443
  to_port = 443
  protocol = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}''')
        self.assertEqual("internet", value)
        self.assertEqual("tcp", facts["protocol"])
        self.assertEqual("specific", facts["protocol_scope"])
        self.assertEqual(443, facts["from_port"])

    def test_multiple_egress_blocks_selects_only_evaluated_index(self):
        egress = '''egress {
  from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}
egress {
  from_port = 443
  to_port = 443
  protocol = "tcp"
  cidr_blocks = ["10.0.0.0/8"]
}'''
        value, facts, refs = self.decide(egress, index=1)
        self.assertEqual("unknown", value)
        self.assertEqual(1, facts["selected_egress_index"])
        self.assertEqual(["10.0.0.0/8"], facts["destination_cidrs"])
        self.assertFalse(any(item["literal"] == "0.0.0.0/0" for item in refs))
        self.assertEqual("insufficient_static_path", facts["unknown_reason_code"])

    def test_ingress_internet_cidr_does_not_supply_egress_destination(self):
        ingress = '''ingress {
  from_port = 443
  to_port = 443
  protocol = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}'''
        egress = '''egress {
  from_port = 443
  to_port = 443
  protocol = "tcp"
  cidr_blocks = ["10.0.0.0/8"]
}'''
        value, facts, refs = self.decide(egress, ingress=ingress)
        self.assertEqual("unknown", value)
        self.assertEqual(["10.0.0.0/8"], facts["destination_cidrs"])
        self.assertFalse(any(item["literal"] == "0.0.0.0/0" for item in refs))

    def test_dynamic_cidr_is_unknown_with_source_trace(self):
        value, facts, refs = self.decide('''egress {
  from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = var.egress_cidrs
}''')
        self.assertEqual("unknown", value)
        self.assertEqual("unresolved_reference", facts["unknown_reason_code"])
        self.assertEqual(1, len(facts["unresolved_destinations"]))
        self.assertIn("var.egress_cidrs", str(facts["unresolved_destinations"]))
        self.assertTrue(any("var.egress_cidrs" in item["literal"] for item in refs))

    def test_dynamic_cidr_builds_approved_unknown_evidence(self):
        source = '''resource "aws_security_group" "test" {
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = var.egress_cidrs
  }
}
'''
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            row = next(row for row in csv.DictReader(stream)
                       if row["check_id"] == "CKV_AWS_382" and
                       row["resource_type"] == "aws_security_group")
        matrix = ROOT / "dataset/main/context/rule_context_applicability.csv"
        with matrix.open(encoding="utf-8", newline="") as stream:
            applicability = next(item for item in csv.DictReader(stream)
                                 if item["check_id"] == "CKV_AWS_382")
        applicability = {key: value == "True" for key, value in applicability.items()
                         if key != "check_id"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text(source, encoding="utf-8")
            row.update(resource="aws_security_group.test", line_start="1",
                       line_end=str(len(source.splitlines())))
            values, legacy = extract_features(row, applicability, source, path)
            values = enforce_applicability(values, applicability)
            evidence = build_evidence(row, values, applicability, legacy, path, matrix)
            output = {key: row[key] for key in ("finding_id", "candidate_id", "scenario_id",
                                                "check_id", "resource", "resource_type",
                                                "line_start", "line_end", "evaluated_keys")}
            output.update(source_path=str(path), **values,
                          feature_extraction_status="EXTRACTED", schema_validation_errors="",
                          applicable_unknown_count="1", applicable_unknown_features="reachability",
                          feature_evidence=json.dumps(evidence))
            result = Path(folder) / "synthetic_features.csv"
            with result.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=output.keys())
                writer.writeheader()
                writer.writerow(output)
            report = validate_context_evidence.validate_file(result)
        basis = evidence["features"]["reachability"]
        self.assertEqual("unknown", values["reachability"])
        self.assertEqual("unknown", basis["status"])
        self.assertEqual("unresolved_reference", basis["unknown_reason_code"])
        self.assertEqual("d011-inline-egress-v1", basis["method_version"])
        self.assertTrue(basis["attempted"])
        self.assertEqual([], report.errors)

    def test_missing_evaluated_index_stays_unknown(self):
        value, facts, _ = self.decide('''egress {
  from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}''', index=1)
        self.assertEqual("unknown", value)
        self.assertEqual("insufficient_static_relationship", facts["unknown_reason_code"])

    def test_standalone_corpus_rules_remain_source_supported(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["check_id"] == "CKV_AWS_382" and
                    row["resource_type"] == "aws_security_group_rule"]
        self.assertEqual(2, len(rows))
        for row in rows:
            with self.subTest(finding_id=row["finding_id"]):
                source = CORPUS / row["candidate_id"] / "main.tf"
                facts, refs, _, _ = facts_for_rule(
                    row, {"reachability": "internet"}, {}, source,
                    finding_region(source, row["line_start"], row["line_end"]),
                    source_inventory(source))
                self.assertEqual("egress", facts["direction"])
                self.assertEqual("0.0.0.0/0", facts["destination_cidr"])
                self.assertTrue(any(item.get("literal") == "0.0.0.0/0" for item in refs))


if __name__ == "__main__":
    unittest.main()
