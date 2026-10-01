"""Regression checks for D-007 IAM statement-level feature scope."""

import csv
from pathlib import Path
import unittest

import extract_finding_context_features as extractor


ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "dataset/main/findings/geniac_tier_a_checkov.csv"
APPLICABILITY = ROOT / "dataset/main/context/rule_context_applicability.csv"
FORMER_FALLBACK_IDS = {
    "a6a385f95a7db642b6ff2ebfbd5a21aa2f1df7dc64617bdc71d3c64672e00c11",
    "3a99089230f626932ddbcc884d773760f14e29e61284031acb3f63ae0db00e15",
}


def two_statement_policy(opener="Statement = ["):
    prefix = "policy = jsonencode({\n" + f"  {opener}\n"
    if opener == "Statement = [":
        prefix += "    {\n"
    return prefix + (
        '      Effect = "Allow"\n'
        '      Action = "s3:GetObject"\n'
        '      Resource = "arn:aws:s3:::bucket/object"\n'
        '    },\n'
        '    {\n'
        '      Effect = "Allow"\n'
        '      Action = "iam:PassRole"\n'
        '      Resource = "*"\n'
        '    }\n'
        '  ]\n'
        '})\n'
    )


class IamStatementSelectionTests(unittest.TestCase):
    def assert_unresolved(self, source, evaluated_keys):
        result = extractor.analyze_iam_statement(source, evaluated_keys)
        self.assertEqual("unresolved", result["evidence"]["statement_resolution"])
        for feature in ("wildcard_action", "wildcard_resource", "privilege_impact"):
            self.assertEqual("unknown", result[feature], feature)
        self.assertEqual([], result["evidence"]["actions"])
        self.assertEqual([], result["evidence"]["resources"])
        self.assertEqual("", result["evidence"]["action_raw"])
        self.assertEqual("", result["evidence"]["resource_raw"])
        return result

    def test_statement_opening_on_following_line(self):
        source = two_statement_policy()
        result = extractor.analyze_iam_statement(
            source, '["policy/Statement/[0]/Action"]'
        )
        self.assertEqual("statement_0", result["evidence"]["statement_resolution"])
        self.assertEqual("1", result["privilege_impact"])
        self.assertEqual("no", result["wildcard_action"])
        self.assertEqual("no", result["wildcard_resource"])

    def test_statement_opening_on_header_line(self):
        for opener in ("Statement = [ {", "Statement = [{"):
            with self.subTest(opener=opener):
                source = two_statement_policy(opener)
                result = extractor.analyze_iam_statement(
                    source, '["policy/Statement/[0]/Action"]'
                )
                self.assertEqual(
                    "statement_0", result["evidence"]["statement_resolution"]
                )
                self.assertEqual(["s3:GetObject"], result["evidence"]["actions"])

    def test_valid_index_selects_only_relevant_statement(self):
        source = two_statement_policy()
        first = extractor.analyze_iam_statement(
            source, '["policy/Statement/[0]/Action"]'
        )
        second = extractor.analyze_iam_statement(
            source, '["policy/Statement/[1]/Action"]'
        )
        self.assertEqual("statement_0", first["evidence"]["statement_resolution"])
        self.assertEqual(["s3:GetObject"], first["evidence"]["actions"])
        self.assertEqual("statement_1", second["evidence"]["statement_resolution"])
        self.assertEqual(["iam:PassRole"], second["evidence"]["actions"])
        self.assertEqual("3", second["privilege_impact"])
        self.assertEqual("yes", second["wildcard_resource"])

    def test_plain_statement_path_remains_supported(self):
        result = extractor.analyze_iam_statement(
            two_statement_policy(), "policy/Statement/[0]/Action"
        )
        self.assertEqual("statement_0", result["evidence"]["statement_resolution"])
        self.assertEqual(["s3:GetObject"], result["evidence"]["actions"])

    def test_missing_invalid_and_out_of_range_index_do_not_aggregate(self):
        source = two_statement_policy()
        for evaluated_keys in (
            "",
            '["policy/Action"]',
            '["policy/Statement/[0]/Action"',
            '["policy/Statement/[0]/Action", "policy/Statement/[1]/Action"]',
            '["policy/Statement/[9]/Action"]',
        ):
            with self.subTest(evaluated_keys=evaluated_keys):
                self.assert_unresolved(source, evaluated_keys)

    def test_unparsed_statement_does_not_aggregate(self):
        source = (
            'Statement = [{\n'
            '  Action = "iam:PassRole"\n'
            '  Resource = "*"\n'
        )
        self.assert_unresolved(source, '["policy/Statement/[0]/Action"]')

    def test_applicability_remains_final_authority(self):
        analyzed = self.assert_unresolved(two_statement_policy(), "")
        features = {feature: "unknown" for feature in extractor.FEATURES}
        for feature in ("wildcard_action", "wildcard_resource", "privilege_impact"):
            features[feature] = analyzed[feature]
        applicability = {feature: True for feature in extractor.FEATURES}
        applicability["wildcard_action"] = False
        result = extractor.enforce_applicability(features, applicability)
        self.assertEqual("not_applicable", result["wildcard_action"])
        self.assertEqual("unknown", result["wildcard_resource"])
        self.assertEqual("unknown", result["privilege_impact"])

    def test_unresolved_selection_in_rule_handlers(self):
        with APPLICABILITY.open(encoding="utf-8", newline="") as stream:
            matrix = {row["check_id"]: row for row in csv.DictReader(stream)}
        for rule in ("CKV_AWS_290", "CKV_AWS_355"):
            with self.subTest(rule=rule):
                finding = {
                    "check_id": rule,
                    "resource_type": "aws_iam_policy",
                    "resource": "aws_iam_policy.example",
                    "evaluated_keys": "",
                }
                features, evidence = extractor.extract_features(
                    finding, matrix[rule], two_statement_policy()
                )
                features = extractor.enforce_applicability(features, matrix[rule])
                self.assertEqual("unresolved", evidence["iam"]["statement_resolution"])
                self.assertEqual("unknown", features["privilege_impact"])
                self.assertEqual("unknown", features["wildcard_resource"])
                self.assertEqual(
                    "unknown" if rule == "CKV_AWS_290" else "not_applicable",
                    features["wildcard_action"],
                )

    def test_two_corpus_findings_select_statement_zero(self):
        with FINDINGS.open(encoding="utf-8", newline="") as stream:
            rows = [
                row for row in csv.DictReader(stream)
                if row["finding_id"] in FORMER_FALLBACK_IDS
            ]
        self.assertEqual(FORMER_FALLBACK_IDS, {row["finding_id"] for row in rows})
        for row in rows:
            with self.subTest(finding_id=row["finding_id"]):
                source_path = ROOT / extractor.get_source_path(row["candidate_id"])
                source = extractor.source_region(
                    extractor.read_source(source_path),
                    row["line_start"], row["line_end"],
                )
                result = extractor.analyze_iam_statement(
                    source, row["evaluated_keys"]
                )
                self.assertEqual(
                    "statement_0", result["evidence"]["statement_resolution"]
                )
                self.assertEqual("2", result["privilege_impact"])
                self.assertEqual("no", result["wildcard_action"])
                self.assertEqual("yes", result["wildcard_resource"])


if __name__ == "__main__":
    unittest.main()
