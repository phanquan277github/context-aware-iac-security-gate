"""Regression coverage for D-011 standalone aws_route reachability proof."""

import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_evidence import source_inventory, subnet_internet_route


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
CORPUS = ROOT / "dataset/main/corpus/geniac_tier_a"
FORMER_FALLBACK_IDS = {
    "1b75d59865098bbcb42d5855bf705e67cba95e7079389e486adc24cc717bf946",
    "291b8c56628405f266262c4a150a1a21f26377941d3002b771969c43e6194ea1",
    "10f369810fbff72312ca5e333dc92afff0a16948a8d063599171b6a28513feb3",
    "41f53131f3688bdbc73342a7cc24007638fc94744e508b8b05b290c87d6a531e",
    "d27545a5878370bfbb93824d645147fac7b3baa1508ec1b56076019ccf05654a",
    "e035326f6a95d1f03e6636052acf27d968e5b0225a8aa2dce9d991f0abadcd45",
    "4ee0a0ee1be97706dfde8a8e6d33c82d0c08b5d82beb2eb1f119c4dc646c97b1",
    "99ef2a897b14776a286308c16ec9758c3390789234431dbadf51a60edc28ff9f",
}


class StandaloneRouteTests(unittest.TestCase):
    def route(self, *, indexed=False, standalone=True, route_table="public",
              gateway="aws_internet_gateway.main.id", igw_vpc="aws_vpc.main.id",
              association=True):
        subnet_ref = "aws_subnet.public[count.index].id" if indexed else "aws_subnet.public.id"
        count = "count = 2" if indexed else ""
        route = (f'''resource "aws_route" "public" {{
  route_table_id = aws_route_table.{route_table}.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id = {gateway}
}}''' if standalone else "")
        inline = ("" if standalone else '''route {
  cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.main.id
}''')
        assoc = (f'''resource "aws_route_table_association" "public" {{
  {count}
  subnet_id = {subnet_ref}
  route_table_id = aws_route_table.public.id
}}''' if association else "")
        source = f'''resource "aws_vpc" "main" {{}}
resource "aws_vpc" "other" {{}}
resource "aws_subnet" "public" {{
  {count}
  vpc_id = aws_vpc.main.id
  map_public_ip_on_launch = true
}}
resource "aws_route_table" "public" {{
  vpc_id = aws_vpc.main.id
  {inline}
}}
resource "aws_route_table" "other" {{ vpc_id = aws_vpc.main.id }}
{assoc}
{route}
resource "aws_internet_gateway" "main" {{
  vpc_id = {igw_vpc}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "main.tf"
            path.write_text(source, encoding="utf-8")
            row = {"resource": "aws_subnet.public[1]" if indexed else "aws_subnet.public"}
            return subnet_internet_route(row, source_inventory(path))

    def test_standalone_default_route_proves_internet_and_records_path(self):
        proven, facts, refs = self.route()
        self.assertTrue(proven)
        self.assertEqual("aws_route_table_association.public", facts["route_table_association"])
        self.assertEqual("aws_route_table.public", facts["route_table"])
        self.assertEqual("aws_route.public", facts["standalone_route"])
        self.assertEqual("0.0.0.0/0", facts["default_route"])
        self.assertEqual("aws_internet_gateway.main", facts["internet_gateway"])
        self.assertEqual("d011-standalone-route-v1", facts["route_resolution_method"])
        self.assertEqual([], facts["unresolved_path_elements"])
        literals = {item.get("literal") for item in refs}
        self.assertTrue({'resource "aws_route_table_association" "public"',
                         'resource "aws_route" "public"',
                         'resource "aws_internet_gateway" "main"',
                         "aws_route_table.public.id", 'destination_cidr_block = "0.0.0.0/0"',
                         "aws_internet_gateway.main.id", "aws_vpc.main.id"} <= literals)

    def test_indexed_subnet_and_association(self):
        proven, facts, refs = self.route(indexed=True)
        self.assertTrue(proven)
        self.assertEqual("aws_subnet.public[1]", facts["subnet"])
        self.assertIn("aws_subnet.public[count.index].id", {item.get("literal") for item in refs})

    def test_route_to_other_table_does_not_match(self):
        proven, facts, _ = self.route(route_table="other")
        self.assertFalse(proven)
        self.assertIn("unique default route", facts["unresolved_path_elements"])

    def test_route_to_nat_does_not_prove_igw(self):
        proven, facts, _ = self.route(gateway="aws_nat_gateway.main.id")
        self.assertFalse(proven)
        self.assertIn("default route to Internet Gateway", facts["unresolved_path_elements"])

    def test_igw_in_other_vpc_does_not_match(self):
        proven, facts, _ = self.route(igw_vpc="aws_vpc.other.id")
        self.assertFalse(proven)
        self.assertIn("same-VPC Internet Gateway", facts["unresolved_path_elements"])

    def test_missing_association_remains_unknown(self):
        proven, facts, _ = self.route(association=False)
        self.assertFalse(proven)
        self.assertIn("unique indexed route-table association", facts["unresolved_path_elements"])

    def test_inline_route_behavior_unchanged(self):
        proven, facts, _ = self.route(standalone=False)
        self.assertTrue(proven)
        self.assertNotIn("standalone_route", facts)
        self.assertEqual("0.0.0.0/0", facts["default_route"])

    def test_eight_corpus_routes_resolve(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["finding_id"] in FORMER_FALLBACK_IDS]
        self.assertEqual(8, len(rows))
        for row in rows:
            with self.subTest(finding_id=row["finding_id"]):
                path = CORPUS / row["candidate_id"] / "main.tf"
                proven, facts, _ = subnet_internet_route(row, source_inventory(path))
                self.assertTrue(proven)
                self.assertEqual("0.0.0.0/0", facts["default_route"])
                self.assertTrue(facts["standalone_route"].startswith("aws_route."))


if __name__ == "__main__":
    unittest.main()
