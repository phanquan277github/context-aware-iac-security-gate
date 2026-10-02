"""Read-only D-009 Evidence v1 validator for finding context-feature CSVs.

It verifies provenance and deterministic assertions; it does not replace a
manual audit of static-analysis completeness or research interpretation.
"""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re

import yaml

from context_evidence import (CONTRACT_VERSION, assignment, finding_region,
                              s3_access_controls, sha256, source_inventory,
                              subnet_internet_route)


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "dataset/main/context"
GROUPS = ("input", "contract", "applicability", "provenance", "source_refs",
          "decision_basis", "resource_role", "iam", "control")
APPROVED_UNKNOWN_CODES = {
    "unresolved_reference", "partially_resolved_expression",
    "insufficient_static_relationship", "insufficient_static_path",
    "insufficient_access_control_evidence", "unresolved_statement",
    "unresolved_effect", "unresolved_action", "unresolved_resource",
    "unclassified_action", "unsupported_static_construct",
}


def reject_constant(value):
    raise ValueError(f"Non-standard JSON constant: {value}")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        headers = next(reader, [])
        if not headers or len(set(headers)) != len(headers) or any(not name for name in headers):
            raise ValueError(f"Missing or duplicate CSV headers: {path}")
        rows = []
        for number, cells in enumerate(reader, 2):
            if len(cells) != len(headers):
                raise ValueError(f"Malformed CSV row {number}: expected {len(headers)} cells, found {len(cells)}")
            rows.append(dict(zip(headers, cells)))
        return rows


def read_yaml(path):
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def taxonomy_map(path):
    taxonomy = read_yaml(path)
    if taxonomy.get("taxonomy_version") != "d010-v1":
        raise ValueError("Unexpected D-010 taxonomy version")
    result = {}
    for entry in taxonomy["mappings"]:
        name, role = entry["resource_type"], entry["role"]
        if name in result:
            raise ValueError(f"Duplicate D-010 resource_type: {name}")
        result[name] = role
    return result


def applicability_map(path, features):
    matrix = {}
    for row in read_csv(path):
        rule = row.get("check_id", "")
        if not rule or rule in matrix:
            raise ValueError(f"Blank or duplicate applicability check_id: {rule!r}")
        if set(row) != {"check_id", *features}:
            raise ValueError("Applicability columns differ from feature schema")
        values = {}
        for feature in features:
            token = row[feature].strip().lower()
            if token not in {"true", "false"}:
                raise ValueError(f"Invalid applicability Boolean: {rule}, {feature}, {row[feature]!r}")
            values[feature] = token == "true"
        matrix[rule] = values
    return matrix


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.counts = Counter()

    def error(self, group, label, message):
        self.errors.append((group, f"{label}: {message}"))

    def warn(self, group, label, message):
        self.warnings.append((group, f"{label}: {message}"))


def check_refs(refs, root, report, label, cache, candidate_dir=None):
    if not isinstance(refs, list) or not refs:
        report.error("source_refs", label, "source_refs must be a non-empty list")
        return
    for item in refs:
        report.counts["source_refs"] += 1
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"]:
            report.error("source_refs", label, "source reference lacks path")
            continue
        path = Path(item["path"])
        if not path.is_absolute():
            path = root / path
        if candidate_dir is not None and not path.resolve().is_relative_to(candidate_dir.resolve()):
            report.error("source_refs", label, f"source reference outside finding candidate: {path}")
            continue
        try:
            if path not in cache:
                cache[path] = (path.read_text(encoding="utf-8").splitlines(), sha256(path))
            lines, digest = cache[path]
            if "sha256" in item:
                if item["sha256"] != digest:
                    report.error("source_refs", label, f"source hash differs: {path}")
                else:
                    report.counts["source_hash_refs_verified"] += 1
            else:
                a, b = int(item["line_start"]), int(item["line_end"])
                literal = item["literal"]
                if not 1 <= a <= b <= len(lines) or not isinstance(literal, str) or not literal:
                    raise ValueError("invalid line range or blank literal")
                if literal not in "\n".join(lines[a - 1:b]):
                    report.error("source_refs", label, f"literal absent from {path}:{a}-{b}: {literal!r}")
                else:
                    report.counts["source_literals_verified"] += 1
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            report.error("source_refs", label, f"cannot verify source reference: {exc}")


def contains_all_refs(actual, required, root):
    def normalize(reference):
        if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
            return None
        item = dict(reference)
        item["path"] = str((root / reference["path"]).resolve())
        return item
    normalized = [normalize(reference) for reference in actual] if isinstance(actual, list) else []
    return all(normalize(reference) in normalized for reference in required)


def check_iam(feature, value, facts, provenance, source_refs, action_taxonomy, report, label):
    iam = facts.get("iam")
    if not isinstance(iam, dict):
        report.error("iam", label, "IAM decision basis lacks iam facts")
        return
    if facts.get("taxonomy_version") != "d008-v1" or iam.get("iam_action_taxonomy_version") != "d008-v1":
        report.error("iam", label, "IAM Action taxonomy version mismatch")
    if facts.get("evaluated_keys") != provenance.get("evaluated_keys"):
        report.error("iam", label, "evaluated_keys differ from shared provenance")
    selection = iam.get("statement_resolution")
    if selection == "unresolved":
        if value != "unknown":
            report.error("iam", label, "unresolved statement requires unknown")
        if (iam.get("statement_source") or iam.get("actions") or iam.get("resources") or
            iam.get("resolved_actions") or iam.get("action_raw") or iam.get("resource_raw")):
            report.error("iam", label, "unresolved selection contains statement-derived data")
        return
    index = iam.get("statement_index")
    if not isinstance(index, int) or selection != f"statement_{index}" or not iam.get("statement_source"):
        report.error("iam", label, "invalid selected statement provenance")
        return
    keys = provenance.get("evaluated_keys", "")
    if not isinstance(keys, str):
        report.error("iam", label, "evaluated_keys must be a string")
        return
    indexes = {int(x) for x in re.findall(r'Statement/\[(\d+)\]', keys)}
    if indexes != {index}:
        report.error("iam", label, "selected statement index differs from evaluated_keys")
    statement = iam["statement_source"]
    if not isinstance(statement, str):
        report.error("iam", label, "statement_source must be a string")
        return
    if not isinstance(source_refs, list) or not any(
        isinstance(item, dict) and item.get("literal") == statement for item in source_refs):
        report.error("iam", label, "selected statement has no exact source reference")
    for key, assignment in (("effect_raw", "Effect"), ("action_raw", "Action"),
                            ("resource_raw", "Resource")):
        raw = iam.get(key)
        if raw and (not isinstance(raw, str) or raw not in statement or
                    not re.search(r'\b' + assignment + r'\s*=', statement)):
            report.error("iam", label, f"{assignment} raw evidence absent from selected statement")
    effect, effect_raw = iam.get("effect"), iam.get("effect_raw", "")
    if effect in {"Allow", "Deny"} and (
        not isinstance(effect_raw, str) or effect_raw.strip() != json.dumps(effect)):
        report.error("iam", label, "resolved Effect differs from raw statement value")
    action_raw = iam.get("action_raw", "")
    actions = iam.get("resolved_actions", [])
    if not isinstance(action_raw, str) or not isinstance(actions, list):
        report.error("iam", label, "invalid Action evidence types")
        return
    for action in actions:
        if not isinstance(action, str) or json.dumps(action) not in action_raw:
            report.error("iam", label, "resolved Action is absent from raw statement value")
    if iam.get("action_unresolved") is False:
        literal = r'"(?:\\.|[^"\\])*"'
        raw = action_raw.strip()
        simple = re.fullmatch(literal, raw, re.S)
        sequence = re.fullmatch(r'\[\s*' + literal + r'(?:\s*,\s*' + literal + r')*\s*,?\s*\]', raw, re.S)
        if (not (simple or sequence) or "${" in raw or "%{" in raw):
            report.error("iam", label, "Action marked fully resolved but raw expression is not a literal string/list")
    condition = iam.get("condition_raw")
    if re.search(r'\bCondition\s*=', statement) and not condition:
        report.error("iam", label, "selected Condition is not preserved")
    if condition and (not isinstance(condition, str) or condition not in statement):
        report.error("iam", label, "Condition evidence absent from selected statement")
    if feature == "wildcard_action":
        actions = iam.get("resolved_actions", [])
        unresolved = iam.get("action_unresolved")
        if not isinstance(actions, list) or any(not isinstance(action, str) for action in actions):
            report.error("iam", label, "resolved_actions must be a string list")
            return
        expected = "yes" if any("*" in action for action in actions) else (
            "unknown" if unresolved or not actions else "no")
        if value != expected:
            report.error("iam", label, f"wildcard_action={value!r}, expected {expected!r} from resolved Actions")
    elif feature == "wildcard_resource":
        raw = iam.get("resource_raw", "")
        resources = iam.get("resources", [])
        if not isinstance(raw, str) or not isinstance(resources, list):
            report.error("iam", label, "Resource evidence has invalid types")
            return
        if value == "no" and (not resources or "${" in raw or "%{" in raw):
            report.error("iam", label, "non-wildcard Resource lacks fully resolved literal evidence")
        if value == "yes" and not any("*" in str(item) for item in resources):
            report.error("iam", label, "wildcard Resource has no wildcard match evidence")
    elif feature == "privilege_impact":
        classes = iam.get("action_capabilities", [])
        if not isinstance(classes, list):
            report.error("iam", label, "Action-to-capability classification is absent")
            return
        expected_classes = []
        actions = iam.get("resolved_actions", [])
        if not isinstance(actions, list) or any(not isinstance(action, str) for action in actions):
            report.error("iam", label, "resolved_actions must be a string list")
            return
        for action in actions:
            capability, level = action_taxonomy.get(action.casefold(), ("unclassified", None))
            expected_classes.append({"action": action, "class": capability, "level": level})
        if classes != expected_classes:
            report.error("iam", label, "Action classifications differ from D-008 taxonomy")
        if iam.get("effect") == "Deny" and value != "0":
            report.error("iam", label, "Deny statement must have privilege_impact=0")
        elif iam.get("effect") not in {"Allow", "Deny"} and value != "unknown":
            report.error("iam", label, "unresolved Effect requires unknown")
        elif iam.get("effect") == "Allow":
            levels = [item["level"] for item in expected_classes]
            expected = "3" if 3 in levels else (
                "unknown" if iam.get("action_unresolved") or not levels or None in levels
                else str(max(levels)))
            if value != expected:
                report.error("iam", label, f"privilege_impact={value!r}, expected {expected!r} from Action classes")


def validate_file(input_path, root=ROOT, contract_path=CONTEXT / "feature_evidence_contract.yaml",
                  schema_path=CONTEXT / "context_schema.yaml",
                  matrix_path=CONTEXT / "rule_context_applicability.csv",
                  taxonomy_path=CONTEXT / "resource_role_taxonomy.yaml",
                  action_taxonomy_path=CONTEXT / "iam_action_capability_taxonomy.yaml"):
    report = Report()
    try:
        rows = read_csv(input_path)
        contract = read_yaml(contract_path)
        if contract.get("contract_version") != CONTRACT_VERSION:
            raise ValueError("Unexpected Evidence v1 contract version")
        approved_codes = set(contract["unknown_reason_codes"])
        if approved_codes != APPROVED_UNKNOWN_CODES or len(approved_codes) != len(contract["unknown_reason_codes"]):
            raise ValueError("Invalid D-011 unknown reason-code registry")
        features = list(read_yaml(schema_path)["finding_context"])
        matrix = applicability_map(matrix_path, features)
        roles = taxonomy_map(taxonomy_path)
        action_config = read_yaml(action_taxonomy_path)
        if action_config.get("taxonomy_version") != "d008-v1":
            raise ValueError("Unexpected D-008 Action taxonomy version")
        action_taxonomy = {}
        for capability, level in (("read_observation", 1), ("operational_mutation", 2),
                                  ("privilege_administration_or_unrestricted", 3)):
            for action in action_config[capability]:
                key = action.casefold()
                if key in action_taxonomy:
                    raise ValueError(f"Duplicate D-008 Action: {action}")
                action_taxonomy[key] = capability, level
        matrix_hash = sha256(matrix_path)
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError, KeyError, csv.Error, yaml.YAMLError) as exc:
        report.error("contract", str(input_path), f"cannot load input/contract: {exc}")
        return report
    report.counts["records_loaded"] = len(rows)
    if not rows:
        report.warn("input", str(input_path), "no findings to validate")
    cache = {}
    seen = set()
    for number, row in enumerate(rows, 2):
        report.counts["records_checked"] += 1
        label = f"row {number}, finding_id={row.get('finding_id', '')!r}"
        if not row.get("finding_id") or row["finding_id"] in seen:
            report.error("input", label, "blank or duplicate finding_id")
        seen.add(row.get("finding_id"))
        if not set(features).issubset(row):
            report.error("input", label, "feature columns missing")
            continue
        rule = row.get("check_id", "")
        if rule not in matrix:
            report.error("applicability", label, f"no matrix row for {rule!r}")
            continue
        try:
            evidence = json.loads(row.get("feature_evidence", ""), parse_constant=reject_constant)
        except (ValueError, RecursionError) as exc:
            report.error("input", label, f"invalid feature_evidence JSON: {exc}")
            continue
        if not isinstance(evidence, dict) or evidence.get("contract_version") != CONTRACT_VERSION:
            report.error("contract", label, "expected d009-v1 evidence object")
            continue
        provenance, bases, na = (evidence.get(key) for key in ("provenance", "features", "not_applicable"))
        if not all(isinstance(value, dict) for value in (provenance, bases, na)):
            report.error("contract", label, "provenance/features/not_applicable must be objects")
            continue
        for key in contract["required_provenance"]:
            if key not in provenance or provenance[key] in (None, ""):
                report.error("provenance", label, f"required provenance absent: {key}")
        for key in ("finding_id", "candidate_id", "scenario_id", "check_id", "resource", "resource_type",
                    "source_path", "scanner", "scanner_version", "check_result", "evaluated_keys"):
            if key in row and provenance.get(key) != row[key]:
                report.error("provenance", label, f"{key} differs from feature row")
        if provenance.get("applicability_matrix_sha256") != matrix_hash:
            report.error("provenance", label, "applicability matrix hash mismatch")
        for key in ("line_start", "line_end"):
            try:
                if int(provenance[key]) != int(row[key]):
                    report.error("provenance", label, f"{key} differs from feature row")
            except (KeyError, ValueError, TypeError):
                report.error("provenance", label, f"invalid {key}")
        raw_source = provenance.get("source_path")
        if not isinstance(raw_source, str) or not raw_source:
            report.error("provenance", label, "source_path must be a non-empty string")
            continue
        source = Path(raw_source)
        if not source.is_absolute():
            source = root / source
        try:
            if provenance.get("source_sha256") != sha256(source):
                report.error("provenance", label, "finding source hash mismatch")
            inventory = provenance.get("terraform_sources")
            if not isinstance(inventory, list) or not inventory:
                raise ValueError("Terraform source inventory missing")
            actual = {path.resolve() for path in source.parent.rglob("*.tf")}
            declared = {(root / item["path"]).resolve() for item in inventory}
            if actual != declared:
                report.error("provenance", label, "Terraform source inventory incomplete or stale")
            check_refs(inventory, root, report, label, cache)
            report.counts["source_inventories_checked"] += 1
        except (OSError, ValueError, KeyError, TypeError) as exc:
            report.error("provenance", label, f"cannot verify source inventory: {exc}")
        applicable = {feature for feature in features if matrix[rule][feature]}
        excluded = set(features) - applicable
        if set(bases) != applicable or set(na) != excluded:
            report.error("applicability", label, "Evidence v1 feature/NA coverage differs from matrix")
        for feature in excluded:
            item = na.get(feature)
            if not isinstance(item, dict) or item != {"check_id": rule, "feature": feature,
                                                      "applicability_matrix_sha256": matrix_hash}:
                report.error("applicability", label, f"invalid not_applicable evidence: {feature}")
            if row[feature] != "not_applicable":
                report.error("applicability", label, f"non-applicable value differs: {feature}")
            report.counts["not_applicable_bases"] += 1
        for feature in applicable:
            item = bases.get(feature)
            report.counts["applicable_bases"] += 1
            if not isinstance(item, dict):
                report.error("decision_basis", label, f"missing basis: {feature}")
                continue
            sublabel = f"{label}, {feature}"
            for key in contract["required_decision_basis"]:
                if key not in item or item[key] in (None, ""):
                    report.error("decision_basis", sublabel, f"required field absent: {key}")
            value = row[feature]
            if item.get("value") != value or value == "not_applicable":
                report.error("decision_basis", sublabel, "basis value differs or is not_applicable")
            if item.get("object") != row.get("resource"):
                report.error("decision_basis", sublabel, "object differs from finding resource")
            if item.get("status") != ("unknown" if value == "unknown" else "determined"):
                report.error("decision_basis", sublabel, "status differs from value")
            if value == "unknown":
                if item.get("attempted") is not True:
                    report.error("decision_basis", sublabel, "unknown requires attempted=true")
                if item.get("unknown_reason_code") not in approved_codes:
                    report.error("decision_basis", sublabel, "missing or unapproved unknown_reason_code")
                if not isinstance(item.get("unknown_reason_detail"), str) or not item["unknown_reason_detail"].strip():
                    report.error("decision_basis", sublabel, "unknown_reason_detail is required")
                if row.get("feature_extraction_status") != "EXTRACTED" or row.get("schema_validation_errors"):
                    report.error("decision_basis", sublabel, "operational extraction failure cannot be unknown")
                if rule == "CKV_AWS_130":
                    required_code = ("insufficient_static_relationship" if
                                     feature in {"internet_exposure", "public_access"} and
                                     isinstance(item.get("facts"), dict) and
                                     item["facts"].get("resolved_route_path") is True else
                                     "insufficient_static_path")
                    if item.get("unknown_reason_code") != required_code:
                        report.error("decision_basis", sublabel, "subnet unknown reason code disagrees with D-011")
                report.counts["unknown_bases"] += 1
            else:
                if item.get("conclusion") != value:
                    report.error("decision_basis", sublabel, "conclusion differs from determined value")
                if value in {"no", "internal"} and item.get("scope_examined") is not True:
                    report.error("decision_basis", sublabel, "negative state lacks scope_examined=true")
            check_refs(item.get("source_refs"), root, report, sublabel, cache, source.parent)
            facts = item.get("facts")
            if not isinstance(facts, dict) or not facts:
                report.error("decision_basis", sublabel, "facts must be a non-empty object")
                continue
            if feature == "resource_role":
                expected = roles.get(row.get("resource_type"))
                if (expected is None or value != expected or
                    facts.get("taxonomy_version") != "d010-v1" or
                    facts.get("mapping_entry") != {"resource_type": row.get("resource_type"), "role": expected} or
                    item.get("method_version") != "d010-v1"):
                    report.error("resource_role", sublabel, "D-010 exact taxonomy mapping is not evidenced")
                else:
                    report.counts["resource_role_bases_verified"] += 1
            elif feature in {"wildcard_action", "wildcard_resource", "privilege_impact"}:
                if item.get("scope") != "selected IAM statement":
                    report.error("iam", sublabel, "IAM feature must use selected-statement scope")
                check_iam(feature, value, facts, provenance, item.get("source_refs"),
                          action_taxonomy, report, sublabel)
            elif feature in {"internet_exposure", "reachability", "public_access"}:
                if rule in {"CKV_AWS_260", "CKV_AWS_38", "CKV_AWS_382", "CKV_AWS_130"}:
                    if facts.get("direction") not in {"ingress", "egress"}:
                        report.error("decision_basis", sublabel, "network direction missing")
                    if rule == "CKV_AWS_38" and facts.get("source_cidr") is not None:
                        report.error("decision_basis", sublabel, "unproven EKS source CIDR is present")
                if rule == "CKV_AWS_260" and (facts.get("direction") != "ingress" or
                    facts.get("source_cidr") != "0.0.0.0/0" or facts.get("port") != 80):
                    report.error("decision_basis", sublabel, "public port-80 ingress facts disagree")
                if rule == "CKV_AWS_38" and facts.get("endpoint_public_access") is not True:
                    report.error("decision_basis", sublabel, "EKS public endpoint literal not evidenced")
                if rule == "CKV_AWS_382" and (facts.get("direction") != "egress" or
                    facts.get("destination_cidr") != "0.0.0.0/0" or facts.get("protocol") != "-1" or
                    facts.get("configured_rule_reachability") is not True or
                    facts.get("runtime_workload_attachment_asserted") is not False or
                    facts.get("inbound_exposure_asserted") is not False or
                    (feature == "reachability" and value != "internet")):
                    report.error("decision_basis", sublabel, "unrestricted egress facts disagree")
                if rule == "CKV_AWS_130" and facts.get("map_public_ip_on_launch") is not True:
                    report.error("decision_basis", sublabel, "subnet public-IP literal not evidenced")
                if rule == "CKV_AWS_130":
                    try:
                        proven, expected, required_refs = subnet_internet_route(
                            row, source_inventory(source))
                        if facts.get("candidate_scope_examined") != provenance.get("terraform_sources"):
                            report.error("decision_basis", sublabel, "subnet candidate inventory differs from provenance")
                        for key, expected_value in expected.items():
                            if key == "candidate_scope_examined":
                                continue
                            if facts.get(key) != expected_value:
                                report.error("decision_basis", sublabel,
                                             f"subnet path fact differs from source: {key}")
                        if facts.get("resolved_route_path") is not proven or facts.get(
                                "configured_reachability") != ("internet" if proven else "unknown"):
                            report.error("decision_basis", sublabel, "subnet route conclusion differs from source")
                        if feature == "reachability" and value != ("internet" if proven else "unknown"):
                            report.error("decision_basis", sublabel, "subnet reachability differs from resolved route")
                        if feature in {"internet_exposure", "public_access"} and (
                                value != "unknown" or not facts.get("unresolved_inbound_relationship")):
                            report.error("decision_basis", sublabel, "subnet inbound/public relationship unsupported")
                        actual_refs = item.get("source_refs", [])
                        if not contains_all_refs(actual_refs, required_refs, root):
                            report.error("source_refs", sublabel, "subnet route component reference missing")
                    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
                        report.error("decision_basis", sublabel, f"cannot verify subnet route: {exc}")
                if rule == "CKV_AWS_382" and feature == "reachability":
                    if not any(isinstance(reference, dict) and reference.get("literal") == "0.0.0.0/0"
                               for reference in item.get("source_refs", [])):
                        report.error("source_refs", sublabel, "egress destination source reference missing")
                    try:
                        region = finding_region(source, row["line_start"], row["line_end"])
                        if facts.get("security_group_id") != assignment(region, "security_group_id"):
                            report.error("decision_basis", sublabel, "egress security-group reference differs from source")
                    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
                        report.error("decision_basis", sublabel, f"cannot verify egress rule: {exc}")
                if rule == "CKV2_AWS_6" and feature == "public_access":
                    try:
                        bucket = row["resource"].split(".", 1)[-1]
                        expected, required_refs = s3_access_controls(source_inventory(source), bucket)
                        controls = expected["explicit_controls"]
                        explicit_access = (controls["inline_acl_or_grant"] or
                                           any(controls[name]["linked"] for name in
                                               ("public_access_block", "bucket_policy", "bucket_acl")))
                        if value == "unknown" and item.get("unknown_reason_code") != "insufficient_access_control_evidence":
                            report.error("decision_basis", sublabel, "S3 unknown needs access-control reason")
                        if value != "unknown" and not explicit_access:
                            report.error("decision_basis", sublabel,
                                         "S3 access state cannot be determined from absent explicit controls")
                        if row["resource"] not in item.get("unknown_reason_detail", ""):
                            report.error("decision_basis", sublabel, "S3 unknown detail lacks bucket identity")
                        if (facts.get("candidate_scope_examined") != provenance.get("terraform_sources") or
                            any(facts.get(key) != expected_value for key, expected_value in expected.items()
                                if key != "candidate_scope_examined")):
                            report.error("decision_basis", sublabel, "S3 access-control inventory differs from candidate")
                        if not contains_all_refs(item.get("source_refs", []), required_refs, root):
                            report.error("source_refs", sublabel, "S3 candidate-control source reference missing")
                    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
                        report.error("control", sublabel, f"cannot verify S3 access controls: {exc}")
            elif feature == "logging_missing":
                if not facts.get("candidate_scope_examined") or facts.get("flow_log_declarations") != []:
                    report.error("control", sublabel, "logging absence lacks complete candidate inventory")
                else:
                    for candidate in facts["candidate_scope_examined"]:
                        try:
                            candidate_path = Path(candidate["path"])
                            if not candidate_path.is_absolute():
                                candidate_path = root / candidate_path
                            if re.search(r'\bresource\s+"aws_flow_log"\s+"',
                                         candidate_path.read_text(encoding="utf-8")):
                                report.error("control", sublabel, "aws_flow_log exists in examined candidate scope")
                        except (OSError, UnicodeError, KeyError, TypeError) as exc:
                            report.error("control", sublabel, f"cannot verify flow-log scope: {exc}")
            elif feature == "encryption_missing":
                if facts.get("linked_bucket") != row["resource"] or facts.get("sse_algorithm") != "AES256":
                    report.error("control", sublabel, "linked non-KMS encryption configuration not evidenced")
                else:
                    bucket = row["resource"].split(".", 1)[-1]
                    linked = [ref for ref in item.get("source_refs", []) if isinstance(ref, dict)
                              and ref.get("literal") == f'aws_s3_bucket.{bucket}.id']
                    algorithm = [ref for ref in item.get("source_refs", []) if isinstance(ref, dict)
                                 and ref.get("literal") == 'sse_algorithm = "AES256"']
                    if (len(linked) != 1 or len(algorithm) != 1 or
                        any(linked[0].get(key) != algorithm[0].get(key)
                            for key in ("path", "line_start", "line_end"))):
                        report.error("control", sublabel, "bucket link and AES256 must share one configuration block")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    report = validate_file(args.input, args.source_root)
    print("D-009 EVIDENCE V1 VALIDATION")
    for key in sorted(report.counts):
        print(f"{key} = {report.counts[key]}")
    errors, warnings = Counter(group for group, _ in report.errors), Counter(group for group, _ in report.warnings)
    for group in GROUPS:
        print(f"{group}: errors={errors[group]}, warnings={warnings[group]}")
    for kind, issues in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for group, message in issues:
            print(f"{kind} [{group}] {message}")
    print(f"Errors = {len(report.errors)}; Warnings = {len(report.warnings)}")
    print("STATUS = " + ("FAIL" if report.errors else "PASS"))
    print("LIMITATION: Source assertions do not prove complete HCL/network semantics; manual research audit remains necessary.")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
