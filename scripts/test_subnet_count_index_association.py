"""D-011 regression tests for count.index subnet route-table associations."""

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

from context_evidence import source_inventory, subnet_internet_route
import extract_finding_context_features as extractor
import validate_context_evidence as validator


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"


class CountIndexAssociationTests(unittest.TestCase):
    def route(self, index=0, *, subnet_name="public", association_count="length(aws_subnet.public)",
              association_subnet="aws_subnet.public[count.index].id",
              association_table="aws_route_table.public.id",
              route_table="public", gateway="aws_internet_gateway.main.id",
              igw_vpc="aws_vpc.main.id"):
        source = f'''resource "aws_subnet" "public" {{
  count = 3
  vpc_id = aws_vpc.main.id
  map_public_ip_on_launch = true
}}
resource "aws_subnet" "private" {{
  count = 3
  vpc_id = aws_vpc.main.id
  map_public_ip_on_launch = true
}}
resource "aws_route_table_association" "public" {{
  count = {association_count}
  subnet_id = {association_subnet}
  route_table_id = {association_table}
}}
resource "aws_route_table" "public" {{
  vpc_id = aws_vpc.main.id
  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = {gateway}
  }}
}}
resource "aws_route_table" "other" {{ vpc_id = aws_vpc.main.id }}
resource "aws_internet_gateway" "main" {{
  vpc_id = {igw_vpc}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text(source, encoding="utf-8")
            row = {"resource": f"aws_subnet.{subnet_name}[{index}]"}
            return subnet_internet_route(row, source_inventory(path))

    def test_indexes_zero_one_two_map_to_same_indexed_association(self):
        for index in range(3):
            with self.subTest(index=index):
                proven, facts, refs = self.route(index)
                self.assertTrue(proven)
                self.assertEqual(index, facts["subnet_index"])
                self.assertEqual(index, facts["resolved_association_index"])
                self.assertEqual("length(aws_subnet.public)", facts["association_count_expression"])
                self.assertEqual("aws_subnet.public[count.index].id", facts["association_indexed_expression"])
                self.assertEqual("d011-count-index-association-v1", facts["association_resolution_method"])
                self.assertIn('resource "aws_internet_gateway" "main"',
                              {item.get("literal") for item in refs})

    def test_wrong_base_subnet_name_remains_unresolved(self):
        self.assertFalse(self.route(subnet_name="private")[0])

    def test_unproven_association_count_remains_unresolved(self):
        proven, facts, _ = self.route(association_count="length(var.subnets)")
        self.assertFalse(proven)
        self.assertIn("unique indexed route-table association", facts["unresolved_path_elements"])

    def test_missing_association_remains_unresolved(self):
        self.assertFalse(self.route(association_subnet="aws_subnet.private[count.index].id")[0])

    def test_index_outside_literal_subnet_count_remains_unresolved(self):
        proven, facts, _ = self.route(index=3)
        self.assertFalse(proven)
        self.assertIn("indexed subnet count bounds", facts["unresolved_path_elements"])

    def test_wrong_association_subnet_or_route_table_remains_unresolved(self):
        for change in ({"association_subnet": "aws_subnet.other[count.index].id"},
                       {"association_table": "aws_route_table.missing.id"}):
            with self.subTest(change=change):
                self.assertFalse(self.route(**change)[0])

    def test_nat_or_other_vpc_gateway_remains_unresolved(self):
        for change in ({"gateway": "aws_nat_gateway.main.id"},
                       {"igw_vpc": "aws_vpc.other.id"}):
            with self.subTest(change=change):
                self.assertFalse(self.route(**change)[0])


class CountIndexEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.input = Path(cls.folder.name) / "finding.csv"
        cls.output = Path(cls.folder.name) / "features.csv"
        with FINDINGS.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            row = next(row for row in reader if row["check_id"] == "CKV_AWS_130" and
                       row["resource"].startswith("aws_subnet.public[") and
                       "length(aws_subnet.public)" in
                       extractor.get_source_path(row["candidate_id"]).read_text(encoding="utf-8") and
                       subnet_internet_route(row, source_inventory(
                           extractor.get_source_path(row["candidate_id"])))[0])
            headers = reader.fieldnames
        with cls.input.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            writer.writerow(row)
        args = ["extract_finding_context_features.py", "--input", str(cls.input),
                "--output", str(cls.output)]
        with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
            extractor.main()
        with cls.output.open(newline="", encoding="utf-8") as stream:
            cls.row = next(csv.DictReader(stream))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def validate_mutation(self, mutate):
        row = copy.deepcopy(self.row)
        evidence = json.loads(row["feature_evidence"])
        mutate(evidence)
        row["feature_evidence"] = json.dumps(evidence)
        path = Path(self.folder.name) / "mutated.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
        return validator.validate_file(path)

    def test_reachability_and_inbound_features(self):
        self.assertEqual("internet", self.row["reachability"])
        self.assertEqual("unknown", self.row["internet_exposure"])
        self.assertEqual("unknown", self.row["public_access"])
        evidence = json.loads(self.row["feature_evidence"])
        reach = evidence["features"]["reachability"]
        self.assertEqual("d011-count-index-association-v1", reach["method_version"])
        self.assertEqual([], validator.validate_file(self.output).errors)
        for feature in ("internet_exposure", "public_access"):
            basis = evidence["features"][feature]
            self.assertEqual("insufficient_static_relationship", basis["unknown_reason_code"])
            self.assertIn("route is resolved", basis["unknown_reason_detail"])
            self.assertNotIn("route/association/Internet Gateway path cannot", basis["unknown_reason_detail"])

    def test_mutated_index_association_route_igw_and_source_refs_rejected(self):
        changes = (
            lambda b: b["facts"].__setitem__("resolved_association_index", 99),
            lambda b: b["facts"].__setitem__("route_table_association", "aws_route_table_association.other"),
            lambda b: b["facts"].__setitem__("route_table", "aws_route_table.other"),
            lambda b: b["facts"].__setitem__("internet_gateway", "aws_internet_gateway.other"),
            lambda b: b["source_refs"].__setitem__(0, {"path": "/tmp/fabricated.tf", "line_start": 1,
                                                       "line_end": 1, "literal": "fabricated"}),
        )
        for change in changes:
            with self.subTest(change=change):
                def mutate(evidence):
                    change(evidence["features"]["reachability"])
                report = self.validate_mutation(mutate)
                self.assertTrue(report.errors)
                self.assertTrue(any(group in {"decision_basis", "source_refs"}
                                    for group, _ in report.errors))

    def test_stale_unresolved_reachability_and_reason_rejected(self):
        def mutate(evidence):
            basis = evidence["features"]["internet_exposure"]
            basis["unknown_reason_code"] = "insufficient_static_path"
            basis["unknown_reason_detail"] = "Subnet route/path unresolved"
        report = self.validate_mutation(mutate)
        self.assertTrue(any(group == "decision_basis" for group, _ in report.errors))

    def test_false_unknown_reachability_rejected_when_indexed_path_exists(self):
        row = copy.deepcopy(self.row)
        row["reachability"] = "unknown"
        evidence = json.loads(row["feature_evidence"])
        basis = evidence["features"]["reachability"]
        basis.update(value="unknown", status="unknown", attempted=True,
                     unknown_reason_code="insufficient_static_path",
                     unknown_reason_detail="Subnet route/path unresolved")
        row["feature_evidence"] = json.dumps(evidence)
        path = Path(self.folder.name) / "false_unknown.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
        report = validator.validate_file(path)
        self.assertTrue(any(group == "decision_basis" and "reachability differs" in message
                            for group, message in report.errors))


if __name__ == "__main__":
    unittest.main()
