"""Regression checks for the accepted D-008 IAM capability contract."""

import unittest

import extract_finding_context_features as extractor


class PrivilegeImpactTests(unittest.TestCase):
    def analyze(self, action, resource='"*"', effect='"Allow"', condition=""):
        source = (
            'Statement = [{\n'
            f'  Effect = {effect}\n'
            f'  Action = {action}\n'
            f'  Resource = {resource}\n'
            f'{condition}'
            '}]\n'
        )
        result = extractor.analyze_iam_statement(
            source, '["Statement/[0]/Action"]'
        )
        self.assertEqual("statement_0", result["evidence"]["statement_resolution"])
        return result

    def test_taxonomy_is_versioned_and_exact_match(self):
        self.assertEqual("d008-v1", extractor.IAM_TAXONOMY_VERSION)
        self.assertNotIn("rds:promoteotheraction", extractor.IAM_ACTION_LEVELS)

    def test_deny_grants_no_capability(self):
        result = self.analyze('var.actions', effect='"Deny"')
        self.assertEqual("0", result["privilege_impact"])
        self.assertEqual("Deny", result["evidence"]["effect"])

    def test_read_and_list_are_level_one(self):
        for action in ('"s3:GetObject"', '"route53:ListHostedZones"'):
            with self.subTest(action=action):
                self.assertEqual("1", self.analyze(action)["privilege_impact"])

    def test_operational_mutation_is_level_two(self):
        for action in ('"s3:PutObject"', '"rds:PromoteReadReplica"'):
            with self.subTest(action=action):
                result = self.analyze(action)
                self.assertEqual("2", result["privilege_impact"])
                self.assertEqual(
                    "operational_mutation",
                    result["evidence"]["action_capabilities"][0]["class"],
                )

    def test_iam_control_and_delegation_are_level_three(self):
        for action in ('"iam:PassRole"', '"sts:AssumeRole"'):
            with self.subTest(action=action):
                self.assertEqual("3", self.analyze(action)["privilege_impact"])

    def test_explicit_unrestricted_actions_are_level_three(self):
        for action in ('"*"', '"iam:*"'):
            with self.subTest(action=action):
                self.assertEqual("3", self.analyze(action)["privilege_impact"])

    def test_service_wildcard_is_not_automatically_level_three(self):
        result = self.analyze('"s3:*"')
        self.assertEqual("unknown", result["privilege_impact"])
        self.assertEqual(
            "unclassified", result["evidence"]["action_capabilities"][0]["class"]
        )

    def test_resource_breadth_does_not_change_capability(self):
        resources = ('"*"', '"arn:aws:s3:::bucket/key"', 'var.resources')
        for action, level in (('"s3:GetObject"', "1"),
                              ('"s3:PutObject"', "2"),
                              ('"iam:PassRole"', "3")):
            for resource in resources:
                with self.subTest(action=action, resource=resource):
                    self.assertEqual(
                        level, self.analyze(action, resource)["privilege_impact"]
                    )

    def test_unresolved_action_is_unknown(self):
        for action in ('var.actions', '"${var.action}"',
                       'concat(["s3:GetObject"], var.more)',
                       '["s3:PutObject", var.more]'):
            with self.subTest(action=action):
                self.assertEqual("unknown", self.analyze(action)["privilege_impact"])

    def test_unclassified_action_is_unknown(self):
        for action in ('"ec2:TagResource"', '"future:UnmappedAction"'):
            with self.subTest(action=action):
                self.assertEqual("unknown", self.analyze(action)["privilege_impact"])

    def test_multiple_resolved_actions_use_maximum(self):
        self.assertEqual(
            "2",
            self.analyze('["s3:GetObject", "s3:PutObject"]')["privilege_impact"],
        )
        self.assertEqual(
            "3",
            self.analyze('["s3:PutObject", "iam:PassRole"]')["privilege_impact"],
        )

    def test_known_level_three_dominates_unresolved_action(self):
        self.assertEqual(
            "3",
            self.analyze('["iam:PassRole", var.more]')["privilege_impact"],
        )
        self.assertEqual(
            "3",
            self.analyze('["s3:*", "iam:PassRole"]')["privilege_impact"],
        )

    def test_unresolved_effect_is_unknown(self):
        self.assertEqual(
            "unknown", self.analyze('"*"', effect='var.effect')["privilege_impact"]
        )

    def test_condition_is_traceable_without_reducing_level(self):
        result = self.analyze(
            '"iam:PassRole"',
            condition='  Condition = {\n'
                      '    StringEquals = { "aws:PrincipalTag/team" = "ops" }\n'
                      '  }\n',
        )
        self.assertEqual("3", result["privilege_impact"])
        self.assertIn("aws:PrincipalTag/team", result["evidence"]["condition_raw"])

    def test_non_applicable_guard_is_unchanged(self):
        features = {feature: "unknown" for feature in extractor.FEATURES}
        features["privilege_impact"] = self.analyze('"iam:PassRole"')["privilege_impact"]
        matrix = {feature: True for feature in extractor.FEATURES}
        matrix["privilege_impact"] = False
        self.assertEqual(
            "not_applicable",
            extractor.enforce_applicability(features, matrix)["privilege_impact"],
        )


if __name__ == "__main__":
    unittest.main()
