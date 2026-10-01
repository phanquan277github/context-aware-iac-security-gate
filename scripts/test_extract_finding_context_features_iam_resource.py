"""Regression tests for evidence-based IAM Resource scope extraction."""

import unittest

import extract_finding_context_features as extractor


class IamResourceScopeTests(unittest.TestCase):
    def analyze(self, resource_expression):
        source = (
            'Statement = [\n'
            '  {\n'
            '    Action = "s3:PutObject"\n'
            f'    Resource = {resource_expression}\n'
            '  }\n'
            ']\n'
        )
        result = extractor.analyze_iam_statement(
            source, '["Statement/[0]/Resource"]'
        )
        self.assertEqual("statement_0", result["evidence"]["statement_resolution"])
        return result

    def test_literal_wildcard(self):
        self.assertEqual("yes", self.analyze('"*"')["wildcard_resource"])

    def test_literal_wildcard_arn(self):
        self.assertEqual(
            "yes",
            self.analyze('"arn:aws:s3:::bucket/*"')["wildcard_resource"],
        )

    def test_explicit_non_wildcard_resource(self):
        self.assertEqual(
            "no",
            self.analyze('"arn:aws:s3:::bucket/object"')["wildcard_resource"],
        )

    def test_list_with_wildcard(self):
        self.assertEqual(
            "yes",
            self.analyze('["arn:aws:s3:::bucket/object", "*"]')["wildcard_resource"],
        )

    def test_list_of_explicit_non_wildcard_resources(self):
        self.assertEqual(
            "no",
            self.analyze(
                '["arn:aws:s3:::first/object", "arn:aws:s3:::second/object"]'
            )["wildcard_resource"],
        )

    def test_mixed_list_with_direct_wildcard_is_yes(self):
        self.assertEqual(
            "yes",
            self.analyze('["*", var.extra_resources]')["wildcard_resource"],
        )

    def test_mixed_list_without_proven_wildcard_is_unknown(self):
        self.assertEqual(
            "unknown",
            self.analyze(
                '["arn:aws:s3:::bucket/object", var.extra_resources]'
            )["wildcard_resource"],
        )

    def test_unresolved_variable_is_unknown(self):
        result = self.analyze("var.policy_resources")
        self.assertEqual("unknown", result["wildcard_resource"])
        self.assertEqual([], result["evidence"]["resources"])
        self.assertEqual("var.policy_resources", result["evidence"]["resource_raw"])

    def test_unresolved_interpolation_is_unknown(self):
        self.assertEqual(
            "unknown",
            self.analyze('"${var.policy_resource}"')["wildcard_resource"],
        )

    def test_unresolved_expression_is_unknown(self):
        for expression in (
            'concat(["arn:aws:s3:::bucket/object"], var.extra_resources)',
            'concat(["*"], var.extra_resources)',
        ):
            with self.subTest(expression=expression):
                self.assertEqual(
                    "unknown", self.analyze(expression)["wildcard_resource"]
                )

    def test_non_applicable_final_guard_is_unchanged(self):
        features = {feature: "unknown" for feature in extractor.FEATURES}
        features["wildcard_resource"] = self.analyze('"*"')["wildcard_resource"]
        applicability = {feature: True for feature in extractor.FEATURES}
        applicability["wildcard_resource"] = False
        result = extractor.enforce_applicability(features, applicability)
        self.assertEqual("not_applicable", result["wildcard_resource"])


if __name__ == "__main__":
    unittest.main()