"""D-009 evidence construction for the approved finding-level extractor.

The assertions here are deliberately narrow. An unsupported source form is an
extraction failure, not evidence for a negative observation.
"""

import ast
import hashlib
import json
from pathlib import Path
import re

import hcl2


CONTRACT_VERSION = "d009-v1"
RESOURCE_ROLE_VERSION = "d010-v1"
IAM_ACTION_VERSION = "d008-v1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_inventory(source_path):
    source_path = Path(source_path)
    if not source_path.is_file():
        raise ValueError(f"Required Terraform source missing: {source_path}")
    files = sorted(source_path.parent.rglob("*.tf"))
    if not files or source_path not in files:
        raise ValueError(f"Incomplete Terraform source inventory: {source_path}")
    if list(source_path.parent.rglob("*.tf.json")):
        raise ValueError(f"Unsupported Terraform JSON source in {source_path.parent}")
    return [{"path": str(path), "sha256": sha256(path)} for path in files]


def finding_region(source_path, start, end):
    lines = Path(source_path).read_text(encoding="utf-8").splitlines()
    try:
        start, end = int(start), int(end)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid finding source range: {start!r}-{end!r}") from exc
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f"Finding source range outside {source_path}: {start}-{end}")
    return "\n".join(lines[start - 1:end])


def ref(path, start, end, literal):
    span = finding_region(path, start, end)
    if literal not in span:
        raise ValueError(f"Source literal {literal!r} absent from {path}:{start}-{end}")
    return {"path": str(path), "line_start": int(start),
            "line_end": int(end), "literal": literal}


def blocks(text, kind, declaration="resource"):
    """Locate resource blocks with brace tracking; reject incomplete blocks."""
    pattern = re.compile(r'\b' + re.escape(declaration) + r'\s+"' +
                         re.escape(kind) + r'"\s+"([^"]+)"\s*\{')
    for match in pattern.finditer(text):
        depth, quoted, escaped = 0, False, False
        for index in range(match.end() - 1, len(text)):
            char = text[index]
            if escaped:
                escaped = False
            elif char == "\\" and quoted:
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted and char == "{":
                depth += 1
            elif not quoted and char == "}":
                depth -= 1
                if depth == 0:
                    yield match.group(1), text[match.start():index + 1], match.start()
                    break
        else:
            raise ValueError(f"Unclosed {kind} resource block")


def candidate_text(inventory):
    return [(entry["path"], Path(entry["path"]).read_text(encoding="utf-8"))
            for entry in inventory]


def resource_blocks(inventory, kind):
    for path, text in candidate_text(inventory):
        for name, block, offset in blocks(text, kind):
            start = text.count("\n", 0, offset) + 1
            yield name, block, path, start, start + block.count("\n")


def data_blocks(inventory, kind):
    for path, text in candidate_text(inventory):
        for name, block, offset in blocks(text, kind, "data"):
            start = text.count("\n", 0, offset) + 1
            yield name, block, path, start, start + block.count("\n")


def assignment(block, key):
    match = re.search(r'^\s*' + re.escape(key) + r'\s*=\s*([^\n#]+)', block, re.M)
    return match.group(1).strip() if match else None


def assignment_literal(block, key):
    match = re.search(r'^\s*' + re.escape(key) + r'\s*=\s*[^\n#]+', block, re.M)
    return match.group(0).strip() if match else None


def s3_access_controls(inventory, bucket_name):
    """Inventory explicit candidate controls; never infer provider defaults."""
    target = f"aws_s3_bucket.{bucket_name}"
    buckets = [(block, path, a, b) for name, block, path, a, b in
               resource_blocks(inventory, "aws_s3_bucket") if name == bucket_name]
    if len(buckets) != 1:
        raise ValueError(f"Expected one S3 bucket declaration for {target}")
    bucket, path, a, b = buckets[0]
    controls = {}
    refs = [ref(path, a, b, f'resource "aws_s3_bucket" "{bucket_name}"')]
    for label, kind in (("public_access_block", "aws_s3_bucket_public_access_block"),
                        ("bucket_policy", "aws_s3_bucket_policy"),
                        ("bucket_acl", "aws_s3_bucket_acl")):
        linked, unresolved = [], []
        for name, block, cpath, ca, cb in resource_blocks(inventory, kind):
            expression = assignment(block, "bucket")
            if expression in {f"{target}.id", f"{target}.bucket"}:
                linked.append(f"{kind}.{name}")
                refs.append(ref(cpath, ca, cb, expression))
            elif expression is None or not re.fullmatch(r'aws_s3_bucket\.[\w-]+\.(?:id|bucket)', expression):
                unresolved.append(f"{kind}.{name}: {expression or '<missing bucket link>'}")
        controls[label] = {"linked": linked, "unresolved_links": unresolved}
    controls["inline_acl_or_grant"] = bool(re.search(r'^\s*(?:acl\s*=|grant\s*\{)', bucket, re.M))
    if controls["inline_acl_or_grant"]:
        refs.append(ref(path, a, b, "acl" if re.search(r'^\s*acl\s*=', bucket, re.M) else "grant"))
    refs.extend({"path": item["path"], "sha256": item["sha256"]} for item in inventory)
    return {"bucket": target, "candidate_scope_examined": inventory,
            "explicit_controls": controls,
            "relationship_resolution": "exact bucket reference or unresolved expression",
            "provider_defaults_inferred": False}, refs


S3_PAB_FLAGS = ("block_public_acls", "ignore_public_acls",
                "block_public_policy", "restrict_public_buckets")


def _s3_resource_data(kind, name, block):
    """Parse a selected control block; malformed HCL is an extraction failure."""
    parsed = hcl2.loads(block)
    return parsed["resource"][0][kind][name]


def _s3_scalar(data, key):
    values = data.get(key)
    return values[0] if isinstance(values, list) and len(values) == 1 else None


def _s3_policy_document(expression):
    """Resolve only literal JSON or HCL jsonencode maps, not references."""
    if not isinstance(expression, str):
        return None
    if expression.startswith("${jsonencode(") and expression.endswith(")}"):
        try:
            document = ast.literal_eval(expression[len("${jsonencode("):-2])
        except (ValueError, SyntaxError, RecursionError):
            return None
    else:
        try:
            document = json.loads(expression)
        except (TypeError, ValueError):
            return None
    return document if isinstance(document, dict) else None


def _s3_policy_document_from_data(inventory, name):
    matches = [(block, path, a, b) for found, block, path, a, b in
               data_blocks(inventory, "aws_iam_policy_document") if found == name]
    if len(matches) != 1:
        return None, []
    block, path, a, b = matches[0]
    refs = [ref(path, a, b, f'data "aws_iam_policy_document" "{name}"')]
    parsed = hcl2.loads(block)["data"][0]["aws_iam_policy_document"][name]
    if any(key in parsed for key in ("dynamic", "source_policy_documents",
                                     "override_policy_documents")):
        return None, refs
    statements = []
    for raw in parsed.get("statement", []):
        if not isinstance(raw, dict) or any(key in raw for key in
                                            ("dynamic", "not_principals", "not_actions",
                                             "not_resources")):
            return None, refs
        principals = raw.get("principals", [])
        if len(principals) == 1 and isinstance(principals[0], dict):
            principal = principals[0]
            public_principal = (_s3_scalar(principal, "type") == "*" and
                                _s3_scalar(principal, "identifiers") == ["*"])
        else:
            public_principal = False
        statement = {"Effect": _s3_scalar(raw, "effect"),
                     "Principal": "*" if public_principal else None,
                     "Action": _s3_scalar(raw, "actions"),
                     "Resource": _s3_scalar(raw, "resources")}
        if "condition" in raw:
            statement["Condition"] = raw["condition"]
        statements.append(statement)
    for key in ("effect", "type", "identifiers", "actions", "resources", "condition"):
        for literal in re.findall(r'^\s*' + key + r'\s*=\s*[^\n#]+', block, re.M):
            refs.append(ref(path, a, b, literal.strip()))
    return {"Statement": statements}, refs


def _s3_policy_statement_proves_public(statement, bucket_name, bucket_literal):
    if not isinstance(statement, dict):
        return False, "unresolved statement"
    if any(key in statement for key in ("NotPrincipal", "NotAction", "NotResource")):
        return False, "unsupported negated policy element"
    if "Condition" in statement:
        return False, "unsupported or unresolved Condition"
    if statement.get("Effect") != "Allow" or statement.get("Principal") != "*":
        return False, "Effect or public Principal not established"
    actions = statement.get("Action")
    if isinstance(actions, str):
        actions = [actions]
    if not isinstance(actions, list) or "s3:GetObject" not in actions:
        return False, "supported public object-read Action not established"
    resources = statement.get("Resource")
    if isinstance(resources, str):
        resources = [resources]
    if not isinstance(resources, list):
        return False, "Resource unresolved"
    exact = f"${{aws_s3_bucket.{bucket_name}.arn}}/*"
    if bucket_literal:
        explicit_arn = f"arn:aws:s3:::{bucket_literal}/*"
    else:
        explicit_arn = None
    if exact not in resources and (explicit_arn is None or explicit_arn not in resources):
        return False, "affected bucket object Resource not established"
    return True, "Allow public s3:GetObject on affected bucket objects"


def s3_public_access_decision(inventory, bucket_name):
    """Apply D-012 to one bucket using only explicit candidate-level facts."""
    inventory_facts, refs = s3_access_controls(inventory, bucket_name)
    target = f"aws_s3_bucket.{bucket_name}"
    bucket_blocks = [(block, path, a, b) for name, block, path, a, b in
                     resource_blocks(inventory, "aws_s3_bucket") if name == bucket_name]
    bucket, bucket_path, bucket_start, bucket_end = bucket_blocks[0]
    configured_name = assignment(bucket, "bucket")
    bucket_literal = (configured_name[1:-1] if configured_name and
                      re.fullmatch(r'"[^"$]+"', configured_name) else None)
    details = {"contract": "D-012", "bucket": target, "pab_flags": None,
               "acl_paths": [], "policy_paths": [], "selected_mechanism": None,
               "unresolved_links": [], "unknown_reasons": [],
               "provider_defaults_inferred": False}
    controls = inventory_facts["explicit_controls"]
    for control in ("public_access_block", "bucket_policy", "bucket_acl"):
        details["unresolved_links"].extend(controls[control]["unresolved_links"])

    pab = []
    for name, block, path, a, b in resource_blocks(inventory, "aws_s3_bucket_public_access_block"):
        if assignment(block, "bucket") != f"{target}.id" and assignment(block, "bucket") != f"{target}.bucket":
            continue
        data = _s3_resource_data("aws_s3_bucket_public_access_block", name, block)
        flags = {key: _s3_scalar(data, key) for key in S3_PAB_FLAGS}
        flags = {key: value if type(value) is bool else None for key, value in flags.items()}
        pab.append({"resource": f"aws_s3_bucket_public_access_block.{name}", "flags": flags})
        for key in S3_PAB_FLAGS:
            literal = assignment_literal(block, key)
            if literal:
                refs.append(ref(path, a, b, literal))
    if len(pab) == 1:
        details["pab_flags"] = pab[0]["flags"]
        details["pab_resource"] = pab[0]["resource"]
    elif len(pab) > 1:
        details["conflicting_pab_resources"] = [item["resource"] for item in pab]

    inline_acl = assignment(bucket, "acl")
    if inline_acl is not None:
        literal = assignment_literal(bucket, "acl")
        refs.append(ref(bucket_path, bucket_start, bucket_end, literal))
        details["acl_paths"].append({"resource": target, "acl": inline_acl,
                                     "public": inline_acl in {'"public-read"', '"public-read-write"'}})
    for name, block, path, a, b in resource_blocks(inventory, "aws_s3_bucket_acl"):
        if assignment(block, "bucket") not in {f"{target}.id", f"{target}.bucket"}:
            continue
        data = _s3_resource_data("aws_s3_bucket_acl", name, block)
        acl = _s3_scalar(data, "acl")
        details["acl_paths"].append({"resource": f"aws_s3_bucket_acl.{name}",
                                     "acl": acl, "public": acl in {"public-read", "public-read-write"}})
        literal = assignment_literal(block, "acl")
        if literal:
            refs.append(ref(path, a, b, literal))

    for name, block, path, a, b in resource_blocks(inventory, "aws_s3_bucket_policy"):
        if assignment(block, "bucket") not in {f"{target}.id", f"{target}.bucket"}:
            continue
        data = _s3_resource_data("aws_s3_bucket_policy", name, block)
        expression = _s3_scalar(data, "policy")
        document = _s3_policy_document(expression)
        data_match = re.fullmatch(
            r'\$\{data\.aws_iam_policy_document\.([\w-]+)\.json\}',
            expression or "")
        if document is None and data_match:
            document, data_refs = _s3_policy_document_from_data(
                inventory, data_match.group(1))
            refs.extend(data_refs)
        statements = document.get("Statement", []) if document else []
        if isinstance(statements, dict):
            statements = [statements]
        if not isinstance(statements, list):
            statements = []
        path_facts = {"resource": f"aws_s3_bucket_policy.{name}",
                      "resolved_document": document is not None,
                      "statements": [], "public": False}
        conflicting_deny = any(isinstance(item, dict) and item.get("Effect") == "Deny"
                               for item in statements)
        for index, statement in enumerate(statements):
            proven, reason = _s3_policy_statement_proves_public(
                statement, bucket_name, bucket_literal)
            if proven and conflicting_deny:
                proven, reason = False, "conflicting Deny statement requires review"
            fields = statement if isinstance(statement, dict) else {}
            path_facts["statements"].append({"index": index, "effect": fields.get("Effect"),
                                             "principal": fields.get("Principal"),
                                             "action": fields.get("Action"),
                                             "resource": fields.get("Resource"),
                                             "condition": fields.get("Condition"),
                                             "public": proven, "reason": reason})
            if proven:
                path_facts["public"] = True
        details["policy_paths"].append(path_facts)
        literal = assignment_literal(block, "policy")
        if literal:
            refs.append(ref(path, a, b, literal))
        for key in ("Effect", "Principal", "Action", "Resource", "Condition"):
            for literal in re.findall(r'^\s*' + key + r'\s*=\s*[^\n#]+', block, re.M):
                refs.append(ref(path, a, b, literal.strip()))

    flags = details["pab_flags"]
    pab_unresolved = controls["public_access_block"]["unresolved_links"]
    if flags and not pab_unresolved and all(value is True for value in flags.values()):
        details["selected_mechanism"] = "all_four_bucket_pab_flags_true"
        return "no", details, refs
    if flags and not pab_unresolved:
        if flags["block_public_acls"] is False and flags["ignore_public_acls"] is False:
            public_acl = next((item for item in details["acl_paths"] if item["public"]), None)
            if public_acl:
                details["selected_mechanism"] = "public_acl_with_unblocked_pab"
                details["selected_resource"] = public_acl["resource"]
                return "yes", details, refs
        if flags["block_public_policy"] is False and flags["restrict_public_buckets"] is False:
            public_policy = next((item for item in details["policy_paths"] if item["public"]), None)
            if public_policy:
                details["selected_mechanism"] = "public_policy_with_unblocked_pab"
                details["selected_resource"] = public_policy["resource"]
                return "yes", details, refs
    reasons = details["unknown_reasons"]
    if not pab:
        reasons.append("affected bucket has no explicit bucket-level Public Access Block")
    elif len(pab) != 1:
        reasons.append("affected bucket has multiple Public Access Block declarations")
    elif any(value is None for value in flags.values()):
        reasons.append("Public Access Block flags are missing or unresolved")
    if pab_unresolved:
        reasons.append("candidate has unresolved Public Access Block bucket link")
    if details["unresolved_links"]:
        reasons.append("candidate contains unresolved access-control bucket link")
    for policy in details["policy_paths"]:
        if not policy["resolved_document"]:
            reasons.append(f"{policy['resource']} policy expression is unresolved or unsupported")
        for statement in policy["statements"]:
            if "Condition" in statement["reason"]:
                reasons.append(f"{policy['resource']} has unsupported or unresolved Condition")
    if not reasons:
        reasons.append("no complete public grant or all-four-flag preventive proof")
    return "unknown", details, refs


def subnet_internet_route(row, inventory):
    """Prove only an exact subnet -> association -> default route -> IGW path."""
    name = str(row["resource"]).split(".", 1)[-1].split("[", 1)[0]
    index_match = re.search(r'\[(\d+)\]$', str(row["resource"]))
    indexed = index_match is not None
    subnets = [(block, path, a, b) for n, block, path, a, b in
               resource_blocks(inventory, "aws_subnet") if n == name]
    if len(subnets) != 1:
        raise ValueError(f"Expected one subnet declaration for {row['resource']}")
    subnet, path, a, b = subnets[0]
    vpc = assignment(subnet, "vpc_id")
    count = assignment(subnet, "count")
    refs = [ref(path, a, b, f'resource "aws_subnet" "{name}"')]
    if indexed and count:
        refs.append(ref(path, a, b, assignment_literal(subnet, "count")))
    facts = {"subnet": row["resource"], "subnet_vpc": vpc,
             "map_public_ip_on_launch": assignment(subnet, "map_public_ip_on_launch") == "true",
             "route_table_association": None, "route_table": None,
             "default_route": None, "internet_gateway": None,
             "resolved_components": ["subnet"],
             "unresolved_path_elements": [],
             "related_cluster_configs": [],
             "candidate_scope_examined": inventory}
    cluster_token = f"aws_subnet.{name}[*].id"
    for cluster_name, cluster, cpath, ca, cb in resource_blocks(inventory, "aws_eks_cluster"):
        if cluster_token in cluster:
            endpoint = assignment(cluster, "endpoint_public_access")
            facts["related_cluster_configs"].append({
                "resource": f"aws_eks_cluster.{cluster_name}",
                "subnet_reference": cluster_token,
                "endpoint_public_access": endpoint})
            refs.append(ref(cpath, ca, cb, cluster_token))
            if endpoint:
                refs.append(ref(cpath, ca, cb, assignment_literal(cluster, "endpoint_public_access")))
    refs.extend({"path": item["path"], "sha256": item["sha256"]} for item in inventory)
    if not re.fullmatch(r'aws_vpc\.[\w-]+\.id', vpc or ""):
        facts["unresolved_path_elements"].append("subnet VPC reference")
    if indexed and not count:
        facts["unresolved_path_elements"].append("indexed subnet count expression")
        return False, facts, refs
    if indexed and re.fullmatch(r"\d+", count or "") and int(index_match.group(1)) >= int(count):
        facts["unresolved_path_elements"].append("indexed subnet count bounds")
        return False, facts, refs
    assoc_target = f"aws_subnet.{name}" + ("[count.index].id" if indexed else ".id")
    matches = []
    for aname, ablock, apath, aa, ab in resource_blocks(inventory, "aws_route_table_association"):
        if assignment(ablock, "subnet_id") != assoc_target:
            continue
        if indexed:
            association_count = assignment(ablock, "count")
            if association_count != count and association_count != f"length(aws_subnet.{name})":
                continue
        matches.append((aname, ablock, apath, aa, ab))
    if len(matches) != 1:
        facts["unresolved_path_elements"].append("unique indexed route-table association")
        return False, facts, refs
    aname, ablock, apath, aa, ab = matches[0]
    table_id = assignment(ablock, "route_table_id")
    facts["route_table_association"] = f"aws_route_table_association.{aname}"
    if indexed and assignment(ablock, "count") == f"length(aws_subnet.{name})":
        facts.update(association_indexed_expression=assoc_target,
                     association_count_expression=assignment(ablock, "count"),
                     subnet_index=int(index_match.group(1)),
                     resolved_association_index=int(index_match.group(1)),
                     association_resolution_method="d011-count-index-association-v1")
    facts["resolved_components"].append("route_table_association")
    refs.extend((ref(apath, aa, ab, assoc_target), ref(apath, aa, ab, table_id or "route_table_id")))
    if indexed and count:
        refs.append(ref(apath, aa, ab, assignment_literal(ablock, "count")))
    if facts.get("association_resolution_method"):
        refs.append(ref(apath, aa, ab, f'resource "aws_route_table_association" "{aname}"'))
    table_match = re.fullmatch(r'aws_route_table\.([\w-]+)\.id', table_id or "")
    if not table_match:
        facts["unresolved_path_elements"].append("route-table reference")
        return False, facts, refs
    tables = [(block, tpath, ta, tb) for n, block, tpath, ta, tb in
              resource_blocks(inventory, "aws_route_table") if n == table_match.group(1)]
    if len(tables) != 1:
        facts["unresolved_path_elements"].append("unique route table")
        return False, facts, refs
    table, tpath, ta, tb = tables[0]
    facts["route_table"] = f"aws_route_table.{table_match.group(1)}"
    facts["resolved_components"].append("route_table")
    refs.append(ref(tpath, ta, tb, f'resource "aws_route_table" "{table_match.group(1)}"'))
    if vpc:
        refs.append(ref(tpath, ta, tb, vpc))
    if assignment(table, "vpc_id") != vpc:
        facts["unresolved_path_elements"].append("same-VPC route-table relationship")
        return False, facts, refs
    routes = re.findall(r'\broute\s*\{([^{}]*)\}', table, re.S)
    defaults = [(assignment(route, "gateway_id"), route, tpath, ta, tb, "cidr_block", None)
                for route in routes if assignment(route, "cidr_block") == '"0.0.0.0/0"']
    for route_name, route, rpath, ra, rb in resource_blocks(inventory, "aws_route"):
        if (assignment(route, "route_table_id") == table_id and
                assignment(route, "destination_cidr_block") == '"0.0.0.0/0"'):
            defaults.append((assignment(route, "gateway_id"), route, rpath, ra, rb,
                             "destination_cidr_block", route_name))
    if len(defaults) != 1:
        facts["unresolved_path_elements"].append("unique default route")
        return False, facts, refs
    gateway, selected_route, rpath, ra, rb, destination_key, route_name = defaults[0]
    if route_name is not None:
        facts["standalone_route"] = f"aws_route.{route_name}"
        facts["route_resolution_method"] = "d011-standalone-route-v1"
        facts["resolved_components"].append("standalone_route")
        refs.extend((ref(apath, aa, ab, f'resource "aws_route_table_association" "{aname}"'),
                     ref(rpath, ra, rb, f'resource "aws_route" "{route_name}"'),
                     ref(rpath, ra, rb, table_id)))
    match = re.fullmatch(r'aws_internet_gateway\.([\w-]+)\.id', gateway or "")
    if not match:
        facts["unresolved_path_elements"].append("default route to Internet Gateway")
        return False, facts, refs
    facts["default_route"] = "0.0.0.0/0"
    facts["resolved_components"].append("default_route")
    refs.extend((ref(rpath, ra, rb, assignment_literal(selected_route, destination_key)),
                 ref(rpath, ra, rb, gateway)))
    igws = [(block, ipath, ia, ib) for n, block, ipath, ia, ib in
            resource_blocks(inventory, "aws_internet_gateway") if n == match.group(1)]
    if len(igws) != 1 or assignment(igws[0][0], "vpc_id") != vpc:
        facts["unresolved_path_elements"].append("same-VPC Internet Gateway")
        return False, facts, refs
    _, ipath, ia, ib = igws[0]
    facts["internet_gateway"] = f"aws_internet_gateway.{match.group(1)}"
    facts["resolved_components"].append("internet_gateway")
    refs.append(ref(ipath, ia, ib, vpc))
    if route_name is not None or facts.get("association_resolution_method"):
        refs.append(ref(ipath, ia, ib, f'resource "aws_internet_gateway" "{match.group(1)}"'))
    return True, facts, refs


def inline_egress_decision(row, source_path):
    """Resolve only the Checkov-selected inline security-group egress block."""
    source_path = Path(source_path).resolve()
    region = finding_region(source_path, row["line_start"], row["line_end"])
    name = str(row["resource"]).split(".", 1)[-1]
    declaration = f'resource "aws_security_group" "{name}"'
    if not re.search(r'^\s*' + re.escape(declaration) + r'\s*\{', region, re.M):
        raise ValueError(f"Affected security group absent from finding region: {row['resource']}")
    start = int(row["line_start"])
    refs = [ref(source_path, start, int(row["line_end"]), declaration)]
    facts = {"direction": "egress", "security_group": str(row["resource"]),
             "selected_egress_index": None, "inline_egress_span": None,
             "destination_cidrs": [], "destination_cidr": None,
             "unresolved_destinations": [], "protocol": None, "protocol_scope": "unresolved",
             "from_port": None, "to_port": None,
             "configured_rule_reachability": False,
             "runtime_workload_attachment_asserted": False,
             "inbound_exposure_asserted": False}
    try:
        keys = json.loads(str(row.get("evaluated_keys", "")))
    except (ValueError, TypeError):
        keys = None
    indices = (set(int(match.group(1)) for key in keys
                   if (match := re.match(r'^egress/\[(\d+)\]/', key)))
               if isinstance(keys, list) and all(isinstance(key, str) for key in keys)
               else set())
    if len(indices) != 1:
        facts["unknown_reason_code"] = "insufficient_static_relationship"
        facts["unknown_detail"] = "Checkov evaluated_keys does not select one inline egress index"
        return "unknown", facts, refs
    index = indices.pop()
    matches = []
    for match in re.finditer(r'(?m)^[ \t]*egress[ \t]*\{', region):
        depth, quoted, escaped = 0, False, False
        for position in range(region.find("{", match.start()), len(region)):
            char = region[position]
            if escaped:
                escaped = False
            elif char == "\\" and quoted:
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted and char == "{":
                depth += 1
            elif not quoted and char == "}":
                depth -= 1
                if depth == 0:
                    block = region[match.start():position + 1].strip()
                    first = start + region[:match.start()].count("\n")
                    matches.append((block, first, first + block.count("\n")))
                    break
        else:
            raise ValueError(f"Unclosed inline egress block: {row['resource']}")
    if index >= len(matches):
        facts["unknown_reason_code"] = "insufficient_static_relationship"
        facts["unknown_detail"] = f"Evaluated egress index {index} has no inline source block"
        return "unknown", facts, refs
    block, first, last = matches[index]
    facts["selected_egress_index"] = index
    facts["inline_egress_span"] = {"path": str(source_path),
                                   "line_start": first, "line_end": last}
    refs.append(ref(source_path, first, last, block))
    try:
        parsed = hcl2.loads(block)["egress"][0]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError(f"Cannot parse selected inline egress block: {row['resource']}") from exc
    protocol_raw = assignment(block, "protocol")
    protocol_match = re.fullmatch(r'"([^"\n]+)"', protocol_raw or "")
    if protocol_match:
        facts["protocol"] = protocol_match.group(1)
        facts["protocol_scope"] = "all" if facts["protocol"] == "-1" else "specific"
        refs.append(ref(source_path, first, last, assignment_literal(block, "protocol")))
    for key in ("from_port", "to_port"):
        token = assignment(block, key)
        if token is not None and re.fullmatch(r'-?\d+', token):
            facts[key] = int(token)
            refs.append(ref(source_path, first, last, assignment_literal(block, key)))
    for key in ("cidr_blocks", "ipv6_cidr_blocks"):
        if key not in parsed:
            continue
        literal = assignment_literal(block, key)
        if literal:
            refs.append(ref(source_path, first, last, literal))
        value = parsed[key]
        if (isinstance(value, list) and len(value) == 1 and
                isinstance(value[0], list) and
                all(isinstance(token, str) and "${" not in token for token in value[0])):
            facts["destination_cidrs"].extend(value[0])
            refs.extend(ref(source_path, first, last, token) for token in value[0])
        else:
            facts["unresolved_destinations"].append({"attribute": key, "expression": literal})
    destination = next((value for value in ("0.0.0.0/0", "::/0")
                        if value in facts["destination_cidrs"]), None)
    if (destination and not facts["unresolved_destinations"] and
            facts["protocol"] is not None and
            facts["from_port"] is not None and facts["to_port"] is not None):
        facts["destination_cidr"] = destination
        facts["configured_rule_reachability"] = True
        return "internet", facts, refs
    facts["unknown_reason_code"] = ("unresolved_reference" if facts["unresolved_destinations"]
                                    else "insufficient_static_path")
    facts["unknown_detail"] = (
        f"Selected inline egress[{index}] lacks a fully resolved Internet-wide "
        "destination/protocol/port configuration")
    return "unknown", facts, refs


def linked_s3_encryption(inventory, bucket_name):
    link = re.compile(r'\bbucket\s*=\s*aws_s3_bucket\.' + re.escape(bucket_name) + r'\.id\b')
    matches = []
    for path, text in candidate_text(inventory):
        for _, block, offset in blocks(text, "aws_s3_bucket_server_side_encryption_configuration"):
            if link.search(block):
                algorithm = re.search(r'\bsse_algorithm\s*=\s*"([^"]+)"', block)
                if not algorithm:
                    raise ValueError(f"Linked S3 encryption algorithm unresolved: {path}")
                start = text.count("\n", 0, offset) + 1
                matches.append((path, start, start + block.count("\n"), algorithm.group(1), block))
    if len(matches) != 1:
        raise ValueError(f"Expected one linked S3 encryption configuration for {bucket_name}, found {len(matches)}")
    return matches[0]


def _inline_s3_encryption_blocks(bucket):
    """Locate explicit inline SSE blocks and their offsets in one bucket declaration."""
    pattern = re.compile(r'(?m)^[ \t]*server_side_encryption_configuration[ \t]*\{')
    for match in pattern.finditer(bucket):
        depth, quoted, escaped = 0, False, False
        for position in range(bucket.find("{", match.start()), len(bucket)):
            char = bucket[position]
            if escaped:
                escaped = False
            elif char == "\\" and quoted:
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted and char == "{":
                depth += 1
            elif not quoted and char == "}":
                depth -= 1
                if depth == 0:
                    yield bucket[match.start():position + 1].strip(), match.start()
                    break
        else:
            raise ValueError("Unclosed inline S3 encryption configuration")


def s3_kms_control_decision(row, source_path):
    """Inspect affected-bucket KMS default encryption in the candidate Terraform scope."""
    source_path = Path(source_path)
    inventory = source_inventory(source_path)
    for path, text in candidate_text(inventory):
        try:
            hcl2.loads(text)
        except Exception as exc:
            raise ValueError(f"Cannot parse candidate Terraform source for S3 KMS inventory: {path}") from exc
    bucket_name = str(row["resource"]).split(".", 1)[-1]
    bucket_id = f"aws_s3_bucket.{bucket_name}"
    buckets = [(block, path, a, b) for name, block, path, a, b in
               resource_blocks(inventory, "aws_s3_bucket") if name == bucket_name]
    if len(buckets) != 1:
        raise ValueError(f"Expected one affected S3 bucket declaration for {bucket_id}")
    bucket, bucket_path, bucket_start, bucket_end = buckets[0]
    refs = [ref(bucket_path, bucket_start, bucket_end,
                f'resource "aws_s3_bucket" "{bucket_name}"')]
    normalized_inventory = [{"path": str(Path(item["path"]).resolve()),
                             "sha256": item["sha256"]} for item in inventory]
    refs.extend(normalized_inventory)
    facts = {"control": "KMS-based S3 default encryption",
             "affected_bucket": bucket_id,
             "candidate_scope_examined": normalized_inventory,
             "standalone_configurations": [], "inline_configurations": [],
             "modules": [], "unresolved_bucket_links": [],
             "dynamic_control_constructs": [], "explicit_sse_configuration_present": False,
             "absence_of_required_control": False,
             "provider_defaults_inferred": False}

    def algorithm_in(block):
        tokens = re.findall(r'(?m)^[ \t]*sse_algorithm[ \t]*=[ \t]*([^\n#]+)', block)
        if len(tokens) != 1:
            return None, "missing or multiple sse_algorithm assignments"
        token = tokens[0].strip()
        match = re.fullmatch(r'"([^"\n]+)"', token)
        return (match.group(1), None) if match else (None, token)

    for name, block, path, a, b in resource_blocks(
            inventory, "aws_s3_bucket_server_side_encryption_configuration"):
        expression = assignment(block, "bucket")
        if expression in {f"{bucket_id}.id", f"{bucket_id}.bucket"}:
            relationship = "affected_bucket"
        elif expression and re.fullmatch(r'aws_s3_bucket\.[\w-]+\.(?:id|bucket)', expression):
            relationship = "other_bucket"
        else:
            relationship = "unresolved"
            facts["unresolved_bucket_links"].append({"resource": name,
                                                      "bucket_expression": expression})
        algorithm, unresolved_algorithm = algorithm_in(block)
        item = {"resource": f"aws_s3_bucket_server_side_encryption_configuration.{name}",
                "bucket_expression": expression, "relationship": relationship,
                "algorithm": algorithm, "unresolved_algorithm": unresolved_algorithm,
                "source_path": str(Path(path).resolve()), "line_start": a, "line_end": b}
        facts["standalone_configurations"].append(item)
        refs.append(ref(path, a, b,
                        f'resource "aws_s3_bucket_server_side_encryption_configuration" "{name}"'))
        if expression:
            refs.append(ref(path, a, b, assignment_literal(block, "bucket")))
        literal = assignment_literal(block, "sse_algorithm")
        if literal:
            refs.append(ref(path, a, b, literal))
        if relationship == "affected_bucket" and re.search(
                r'\bdynamic[ \t]+"(?:rule|apply_server_side_encryption_by_default)"', block):
            facts["dynamic_control_constructs"].append(item["resource"])

    for block, offset in _inline_s3_encryption_blocks(bucket):
        a = bucket_start + bucket[:offset].count("\n")
        b = a + block.count("\n")
        algorithm, unresolved_algorithm = algorithm_in(block)
        item = {"resource": bucket_id, "relationship": "affected_bucket",
                "algorithm": algorithm, "unresolved_algorithm": unresolved_algorithm,
                "source_path": str(Path(bucket_path).resolve()),
                "line_start": a, "line_end": b}
        facts["inline_configurations"].append(item)
        refs.append(ref(bucket_path, a, b, block))
        literal = assignment_literal(block, "sse_algorithm")
        if literal:
            refs.append(ref(bucket_path, a, b, literal))
        if re.search(r'\bdynamic[ \t]+"(?:rule|apply_server_side_encryption_by_default)"', block):
            facts["dynamic_control_constructs"].append(f"{bucket_id}.inline_sse")
    if re.search(r'\bdynamic[ \t]+"server_side_encryption_configuration"', bucket):
        facts["dynamic_control_constructs"].append(f"{bucket_id}.dynamic_sse")
        refs.append(ref(bucket_path, bucket_start, bucket_end,
                        'dynamic "server_side_encryption_configuration"'))

    for path, text in candidate_text(inventory):
        for match in re.finditer(r'(?m)^[ \t]*module[ \t]+"([^"\n]+)"[ \t]*\{', text):
            line = text.count("\n", 0, match.start()) + 1
            facts["modules"].append({"name": match.group(1),
                                     "source_path": str(Path(path).resolve()), "line": line})
            refs.append(ref(path, line, line, f'module "{match.group(1)}"'))

    affected = ([item for item in facts["standalone_configurations"]
                 if item["relationship"] == "affected_bucket"] + facts["inline_configurations"])
    facts["explicit_sse_configuration_present"] = bool(affected)
    if facts["unresolved_bucket_links"] or facts["modules"] or facts["dynamic_control_constructs"]:
        facts["unknown_reason_code"] = ("unresolved_reference" if facts["unresolved_bucket_links"]
                                        else "unsupported_static_construct")
        if facts["modules"] and not facts["unresolved_bucket_links"] and not facts["dynamic_control_constructs"]:
            modules = ", ".join(f'module "{item["name"]}"' for item in facts["modules"])
            facts["unknown_detail"] = (f"Candidate scope for {bucket_id} cannot prove absence of "
                                       f"KMS-based default encryption: external Terraform {modules} "
                                       "are outside the inspected local source inventory")
        else:
            facts["unknown_detail"] = (f"Candidate scope for {bucket_id} includes unresolved bucket links, "
                                       "external modules, or dynamic SSE constructs")
        return "unknown", facts, refs
    if len(affected) > 1:
        facts["unknown_reason_code"] = "insufficient_static_relationship"
        facts["unknown_detail"] = f"Multiple SSE configurations target {bucket_id}"
        return "unknown", facts, refs
    if affected:
        selected = affected[0]
        if selected["algorithm"] == "aws:kms":
            raise ValueError(f"Explicit aws:kms configuration for CKV_AWS_145 FAILED finding: {bucket_id}")
        if selected["algorithm"] == "AES256" and not selected["unresolved_algorithm"]:
            return "yes", facts, refs
        facts["unknown_reason_code"] = ("unresolved_reference" if selected["unresolved_algorithm"]
                                        else "unsupported_static_construct")
        facts["unknown_detail"] = f"SSE algorithm for {bucket_id} cannot be classified as KMS control"
        return "unknown", facts, refs
    facts["absence_of_required_control"] = True
    return "yes", facts, refs


def vpc_flow_log_decision(row, source_path):
    """Resolve explicit flow-log relations for the affected VPC in candidate scope."""
    if row.get("resource_type") != "aws_vpc" or not re.fullmatch(
            r"aws_vpc\.[\w-]+", str(row.get("resource", ""))):
        raise ValueError("CKV2_AWS_11 requires an affected aws_vpc resource")
    affected = row["resource"]
    name = affected.split(".", 1)[1]
    inventory = source_inventory(source_path)
    for path, content in candidate_text(inventory):
        try:
            hcl2.loads(content)
        except Exception as exc:
            raise ValueError(f"Cannot parse candidate Terraform source for VPC flow-log inventory: {path}") from exc
    vpc_blocks = list(resource_blocks(inventory, "aws_vpc"))
    matches = [(path, start, end) for found, _, path, start, end in
               vpc_blocks if found == name]
    if len(matches) != 1:
        raise ValueError(f"Expected one affected VPC declaration for {affected}")
    path, start, end = matches[0]
    refs = [ref(path, start, end, f'resource "aws_vpc" "{name}"')]
    normalized_inventory = [{"path": str(Path(item["path"]).resolve()),
                             "sha256": item["sha256"]} for item in inventory]
    refs.extend(normalized_inventory)
    facts = {"control": "VPC Flow Logging", "affected_vpc": affected,
             "candidate_scope_examined": normalized_inventory,
             "flow_log_declarations": [], "modules": [],
             "absence_of_affected_vpc_flow_log": False,
             "provider_defaults_inferred": False}
    unresolved = []
    for found, block, log_path, a, b in resource_blocks(inventory, "aws_flow_log"):
        expression = assignment(block, "vpc_id")
        direct = re.fullmatch(r"aws_vpc\.([\w-]+)\.id", expression or "")
        target = (f"aws_vpc.{direct.group(1)}" if direct and
                  sum(found == direct.group(1) for found, *_ in vpc_blocks) == 1 else None)
        relation = ("affected_vpc" if target == affected else
                    "other_vpc" if target else "unresolved")
        item = {"resource": f"aws_flow_log.{found}",
                "vpc_id_expression": expression, "resolved_target_vpc": target,
                "relationship": relation, "source_path": str(Path(log_path).resolve()),
                "line_start": a, "line_end": b}
        facts["flow_log_declarations"].append(item)
        refs.append(ref(log_path, a, b, f'resource "aws_flow_log" "{found}"'))
        if expression:
            refs.append(ref(log_path, a, b, assignment_literal(block, "vpc_id")))
        if relation == "affected_vpc":
            raise ValueError(f"CKV2_AWS_11 FAILED conflicts with linked flow log: {affected}, {item['resource']}")
        if relation == "unresolved":
            unresolved.append(item["resource"])
    for module_path, content in candidate_text(inventory):
        for match in re.finditer(r'(?m)^[ \t]*module[ \t]+"([^"\n]+)"[ \t]*\{', content):
            line = content.count("\n", 0, match.start()) + 1
            facts["modules"].append({"name": match.group(1),
                                     "source_path": str(Path(module_path).resolve()), "line": line})
            refs.append(ref(module_path, line, line, f'module "{match.group(1)}"'))
    if unresolved or facts["modules"]:
        facts["unknown_reason_code"] = ("unresolved_reference" if unresolved
                                        else "unsupported_static_construct")
        facts["unknown_detail"] = (f"Candidate scope for {affected} has unresolved flow-log "
                                   "VPC relation or module source")
        return "unknown", facts, refs
    facts["absence_of_affected_vpc_flow_log"] = True
    return "yes", facts, refs


def _eks_vpc_config_blocks(cluster):
    """Return exact source spans for vpc_config blocks in one EKS declaration."""
    pattern = re.compile(r'\bdynamic\s+"vpc_config"\s*\{|\bvpc_config\s*\{')
    for match in pattern.finditer(cluster):
        depth, quoted, escaped = 0, False, False
        for position in range(match.end() - 1, len(cluster)):
            char = cluster[position]
            if escaped:
                escaped = False
            elif char == "\\" and quoted:
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted and char == "{":
                depth += 1
            elif not quoted and char == "}":
                depth -= 1
                if depth == 0:
                    yield (cluster[match.start():position + 1], match.start(),
                           "dynamic" if match.group().startswith("dynamic") else "literal")
                    break
        else:
            raise ValueError("Unclosed EKS vpc_config block")


def _eks_raw_assignment(block, key):
    match = re.search(r'\b' + re.escape(key) + r'\s*=\s*', block)
    if not match:
        return None
    start, depth, quoted, escaped = match.end(), 0, False, False
    for position in range(start, len(block)):
        char = block[position]
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char in "[({":
                depth += 1
            elif char in "])}":
                if depth == 0:
                    return block[start:position].strip()
                depth -= 1
            elif char in "\n#" and depth == 0:
                return block[start:position].strip()
    return block[start:].strip()


def eks_public_endpoint_decision(row, source_path):
    """Use only the affected EKS declaration; never materialize endpoint defaults."""
    affected = str(row.get("resource", ""))
    if row.get("resource_type") != "aws_eks_cluster" or not re.fullmatch(
            r"aws_eks_cluster\.[\w-]+", affected):
        raise ValueError("CKV_AWS_38 requires an affected aws_eks_cluster resource")
    name = affected.split(".", 1)[1]
    inventory = source_inventory(source_path)
    matches = [(block, path, a, b) for found, block, path, a, b in
               resource_blocks(inventory, "aws_eks_cluster") if found == name]
    if len(matches) != 1:
        raise ValueError(f"Expected one affected EKS declaration for {affected}")
    cluster, path, start, end = matches[0]
    try:
        parsed = hcl2.loads(cluster)["resource"][0]["aws_eks_cluster"][name]
    except Exception as exc:
        raise ValueError(f"Cannot parse affected EKS source declaration: {affected}") from exc
    configs = list(_eks_vpc_config_blocks(cluster))
    parsed_configs = parsed.get("vpc_config", [])
    if len(configs) != 1:
        raise ValueError(f"Cannot uniquely inspect EKS vpc_config for {affected}")
    vpc, offset, config_kind = configs[0]
    vpc_start = start + cluster[:offset].count("\n")
    vpc_end = vpc_start + vpc.count("\n")
    if config_kind == "literal" and len(parsed_configs) != 1:
        raise ValueError(f"Cannot uniquely inspect parsed EKS vpc_config for {affected}")
    config = parsed_configs[0] if config_kind == "literal" else {}
    if not isinstance(config, dict):
        raise ValueError(f"Invalid EKS vpc_config for {affected}")
    endpoint = _eks_raw_assignment(vpc, "endpoint_public_access") if config_kind == "literal" else None
    cidrs = _eks_raw_assignment(vpc, "public_access_cidrs") if config_kind == "literal" else None
    if config_kind == "literal" and (
            (endpoint is None) != ("endpoint_public_access" not in config) or
            (cidrs is None) != ("public_access_cidrs" not in config)):
        raise ValueError(f"Cannot locate parsed EKS endpoint attributes in source: {affected}")
    state = ("unsupported_static_construct" if config_kind == "dynamic" else
             "absent" if endpoint is None else "explicit_true" if endpoint == "true"
             else "explicit_false" if endpoint == "false" else "unresolved_expression")
    resolved_cidrs = None
    if cidrs is not None:
        parsed_cidrs = config["public_access_cidrs"]
        if isinstance(parsed_cidrs, list) and len(parsed_cidrs) == 1:
            parsed_cidrs = parsed_cidrs[0]
        if (isinstance(parsed_cidrs, list) and
                all(isinstance(item, str) and "${" not in item for item in parsed_cidrs)
                and cidrs.startswith("[") and cidrs.endswith("]")):
            resolved_cidrs = parsed_cidrs
    refs = [ref(path, start, end, f'resource "aws_eks_cluster" "{name}"'),
            ref(path, vpc_start, vpc_end, vpc)]
    if endpoint is not None:
        refs.append(ref(path, vpc_start, vpc_end, "endpoint_public_access"))
    if cidrs is not None:
        refs.append(ref(path, vpc_start, vpc_end, "public_access_cidrs"))
    facts = {"affected_cluster": affected, "eks_declaration_span":
             {"path": str(Path(path).resolve()), "line_start": start, "line_end": end},
             "vpc_config_span": {"path": str(Path(path).resolve()),
                                 "line_start": vpc_start, "line_end": vpc_end},
             "direction": "ingress", "endpoint_attribute_state": state,
             "endpoint_public_access_raw": endpoint,
             "endpoint_public_access": True if state == "explicit_true" else
             False if state == "explicit_false" else None,
             "endpoint_attribute_absent": state == "absent",
             "public_access_cidrs_raw": cidrs,
             "public_access_cidrs_resolved": resolved_cidrs,
             "public_access_cidrs_absent": cidrs is None and config_kind == "literal",
             "source_cidr": None, "provider_defaults_inferred": False}
    features = ("internet_exposure", "reachability", "public_access")
    proven = (state == "explicit_true" and
              (cidrs is None or resolved_cidrs is not None and "0.0.0.0/0" in resolved_cidrs))
    values = dict(zip(features, ("yes", "internet", "yes") if proven else
                      ("unknown", "unknown", "unknown")))
    unknowns = {}
    if not proven:
        if state == "unsupported_static_construct":
            code = "unsupported_static_construct"
            detail = f"{affected}: dynamic vpc_config cannot be resolved from static source"
        elif state == "unresolved_expression" or cidrs is not None and resolved_cidrs is None:
            code = "unresolved_reference"
            detail = (f"{affected}: endpoint_public_access or public_access_cidrs "
                      "contains an unresolved expression")
        elif state == "absent":
            code = "insufficient_static_path"
            detail = (f"{affected}: endpoint_public_access is absent in the inspected "
                      "EKS vpc_config; no provider default or public endpoint path is inferred")
        elif state == "explicit_false":
            code = "insufficient_static_relationship"
            detail = (f"{affected}: endpoint_public_access=false disables this explicit public "
                      "endpoint path, but other resource-level access paths are not established")
        else:
            code = "insufficient_static_path"
            detail = f"{affected}: explicit public_access_cidrs does not prove an Internet-wide endpoint path"
        unknowns = {feature: {"code": code, "detail": f"{feature}: {detail}"}
                    for feature in features}
    facts["feature_conclusions"] = values
    facts["feature_unknowns"] = unknowns
    return values, facts, refs


def facts_for_rule(row, values, legacy, source_path, region, inventory):
    check = str(row["check_id"])
    start, end = int(row["line_start"]), int(row["line_end"])
    resource_name = str(row["resource"]).split(".", 1)[-1].split("[", 1)[0]
    common_ref = ref(source_path, start, end,
                     f'resource "{row["resource_type"]}" "{resource_name}"')
    facts = {"scanner_check": check, "scanner_result": row.get("check_result", "")}
    refs = [common_ref]
    method = "source_and_scanner"
    uncertainty = None

    if check == "CKV2_AWS_11":
        decision, flow_facts, flow_refs = vpc_flow_log_decision(row, source_path)
        if values["logging_missing"] != decision:
            raise ValueError("VPC flow-log control value differs from affected-VPC source inventory")
        facts.update(flow_facts)
        refs.extend(flow_refs)
        method = "affected_vpc_flow_log_inventory"
        uncertainty = flow_facts.get("unknown_detail")
    elif check == "CKV2_AWS_6":
        controls, control_refs = s3_access_controls(inventory, resource_name)
        decision, d012, decision_refs = s3_public_access_decision(inventory, resource_name)
        if values["public_access"] != decision:
            raise ValueError("D-012 S3 public_access differs from candidate evidence")
        facts.update(control="S3 Public Access Block", **controls,
                     static_public_access_relation=decision,
                     d012_decision=d012)
        refs.extend(control_refs + decision_refs)
        method = "candidate_access_control_inventory"
        uncertainty = (f"D-012 static evidence for {row['resource']} is insufficient: "
                       + "; ".join(d012["unknown_reasons"]))
    elif check == "CKV_AWS_117":
        facts.update(control="Lambda VPC configuration", inferred_network_values=False)
    elif check == "CKV_AWS_130":
        match = re.search(r'\bmap_public_ip_on_launch\s*=\s*true\b', region)
        if not match:
            raise ValueError("Subnet public-IP literal absent from finding region")
        route_proven, route_facts, route_refs = subnet_internet_route(row, inventory)
        if not route_facts["map_public_ip_on_launch"]:
            raise ValueError("Subnet map_public_ip_on_launch not corroborated by source inventory")
        facts.update(route_facts, direction="ingress",
                     configured_reachability="internet" if route_proven else "unknown",
                     unresolved_inbound_relationship=(
                         f"For {row['resource']}, the observed EKS public endpoint/subnet reference "
                         "does not establish a subnet-specific Internet-origin inbound path to "
                         "an attached workload/ENI or endpoint" if route_facts["related_cluster_configs"] else
                         f"For {row['resource']}, no deterministic Internet-origin ingress path "
                         "through an attached workload/ENI or subnet-specific public endpoint is established"),
                     resolved_route_path=route_proven)
        refs.extend(route_refs)
        refs.append(ref(source_path, start, end, match.group(0)))
        uncertainty = ("Configured Internet route is resolved, but the affected workload/endpoint "
                       "and Internet-origin inbound relationship are not established" if route_proven else
                       "Subnet route/association/Internet Gateway path cannot be fully resolved statically")
        method = "subnet_route_association_igw"
    elif check == "CKV_AWS_145":
        decision, kms_facts, kms_refs = s3_kms_control_decision(row, source_path)
        if values["encryption_missing"] != decision:
            raise ValueError("S3 KMS control value differs from affected-bucket source inventory")
        facts.update(kms_facts)
        refs.extend(kms_refs)
        method = "candidate_bucket_kms_control_inventory"
        uncertainty = kms_facts.get("unknown_detail")
    elif check == "CKV_AWS_260":
        ingress = re.findall(r'\bingress\s*\{([^{}]*)\}', region, re.S)
        matched = [block for block in ingress if re.search(r'\bfrom_port\s*=\s*80\b', block)
                   and re.search(r'\bto_port\s*=\s*80\b', block)
                   and '0.0.0.0/0' in block]
        if not matched:
            raise ValueError("Public port-80 ingress not established in finding region")
        facts.update(direction="ingress", source_cidr="0.0.0.0/0", port=80,
                     path="security-group ingress rule to Internet")
        refs.append(ref(source_path, start, end, matched[0].strip()))
    elif check == "CKV_AWS_38":
        decisions, endpoint_facts, endpoint_refs = eks_public_endpoint_decision(row, source_path)
        if any(values[feature] != decision for feature, decision in decisions.items()):
            raise ValueError("EKS feature values differ from affected endpoint source evidence")
        facts.update(endpoint_facts)
        refs.extend(endpoint_refs)
        method = "affected_eks_public_endpoint"
    elif check == "CKV_AWS_382":
        if row["resource_type"] == "aws_security_group":
            decision, inline_facts, inline_refs = inline_egress_decision(row, source_path)
            if values["reachability"] != decision:
                raise ValueError("Inline egress reachability differs from selected source block")
            facts.update(inline_facts)
            refs.extend(inline_refs)
            method = "selected_inline_security_group_egress"
            uncertainty = inline_facts.get("unknown_detail")
        else:
            if not (re.search(r'\btype\s*=\s*"egress"', region)
                    and re.search(r'\bprotocol\s*=\s*"-1"', region)
                    and '0.0.0.0/0' in region):
                raise ValueError("Unrestricted Internet egress not established in finding region")
            facts.update(direction="egress", destination_cidr="0.0.0.0/0",
                         protocol="-1", path="security-group outbound rule to Internet",
                         security_group_id=assignment(region, "security_group_id"),
                         configured_rule_reachability=True,
                         runtime_workload_attachment_asserted=False,
                         inbound_exposure_asserted=False)
            refs.append(ref(source_path, start, end, '0.0.0.0/0'))
            refs.append(ref(source_path, start, end, assignment_literal(region, "type")))
            refs.append(ref(source_path, start, end, assignment_literal(region, "protocol")))
            refs.append(ref(source_path, start, end, assignment_literal(region, "security_group_id")))
            uncertainty = "Outbound path does not establish inbound Internet exposure"
    elif check in {"CKV_AWS_290", "CKV_AWS_355"}:
        iam = legacy.get("iam")
        if not isinstance(iam, dict):
            raise ValueError("IAM statement evidence missing")
        facts.update(iam=iam, evaluated_keys=row.get("evaluated_keys", ""),
                     taxonomy_version=IAM_ACTION_VERSION)
        if iam["statement_resolution"] == "unresolved":
            uncertainty = "Checkov-relevant IAM statement could not be selected from evaluated_keys and source"
        else:
            index = iam["statement_index"]
            if index is None or f"statement_{index}" != iam["statement_resolution"]:
                raise ValueError("IAM statement index and resolution disagree")
            literal = iam.get("statement_source", "")
            if not literal or literal not in region:
                raise ValueError("Selected IAM statement not located in finding source region")
            offset = region.index(literal)
            statement_start = start + region[:offset].count("\n")
            statement_end = statement_start + literal.count("\n")
            refs.append(ref(source_path, statement_start, statement_end, literal))
        method = "d007_statement_d008_action_taxonomy"
    else:
        raise ValueError(f"No D-009 evidence builder for {check}")
    return facts, refs, method, uncertainty


def unknown_reason_code(row, feature, facts):
    check = row["check_id"]
    if check == "CKV2_AWS_11" and feature == "logging_missing":
        return facts["unknown_reason_code"]
    if check == "CKV_AWS_145" and feature == "encryption_missing":
        return facts["unknown_reason_code"]
    if check == "CKV_AWS_382" and feature == "reachability":
        return facts["unknown_reason_code"]
    if check == "CKV_AWS_38" and feature in facts.get("feature_unknowns", {}):
        return facts["feature_unknowns"][feature]["code"]
    if check == "CKV2_AWS_6" and feature == "public_access":
        return "insufficient_access_control_evidence"
    if check == "CKV_AWS_130":
        if feature in {"internet_exposure", "public_access"}:
            return ("insufficient_static_relationship" if facts.get("resolved_route_path")
                    else "insufficient_static_path")
        if feature == "reachability" and facts.get("unresolved_path_elements"):
            return "insufficient_static_path"
    if check in {"CKV_AWS_290", "CKV_AWS_355"}:
        iam = facts.get("iam", {})
        if iam.get("statement_resolution") == "unresolved":
            return "unresolved_statement"
        if feature == "privilege_impact":
            if iam.get("effect") not in {"Allow", "Deny"}:
                return "unresolved_effect"
            if iam.get("action_unresolved"):
                return "unresolved_action"
            if any(item.get("class") == "unclassified" for item in iam.get("action_capabilities", [])):
                return "unclassified_action"
        if feature == "wildcard_action" and iam.get("action_unresolved"):
            return "unresolved_action"
        if feature == "wildcard_resource":
            return "unresolved_resource"
    raise ValueError(f"No approved unknown reason for {check}/{feature}")


def build_evidence(row, values, applicability, legacy, source_path, matrix_path):
    """Construct one shared provenance object and one basis per applicable feature."""
    for key in ("finding_id", "candidate_id", "scenario_id", "check_id", "resource",
                "resource_type", "scanner", "scanner_version", "check_result"):
        if not str(row.get(key, "")).strip():
            raise ValueError(f"Required finding provenance missing: {key}")
    if row["check_result"] != "FAILED":
        raise ValueError(f"Expected FAILED scanner finding, got {row['check_result']!r}")
    source_path, matrix_path = Path(source_path), Path(matrix_path)
    inventory = source_inventory(source_path)
    region = finding_region(source_path, row.get("line_start"), row.get("line_end"))
    matrix_hash = sha256(matrix_path)
    provenance = {name: str(row.get(name, "")) for name in
                  ("finding_id", "candidate_id", "scenario_id", "check_id",
                   "resource", "resource_type", "scanner", "scanner_version",
                   "check_result", "evaluated_keys")}
    provenance.update(source_path=str(source_path), source_sha256=sha256(source_path),
                      line_start=int(row["line_start"]), line_end=int(row["line_end"]),
                      applicability_matrix_sha256=matrix_hash, terraform_sources=inventory)
    facts, refs, method, uncertainty = facts_for_rule(
        row, values, legacy, source_path, region, inventory)
    feature_basis, non_applicable = {}, {}
    for feature, value in values.items():
        if not bool(applicability[feature]):
            non_applicable[feature] = {"check_id": row["check_id"], "feature": feature,
                                       "applicability_matrix_sha256": matrix_hash}
            continue
        if value == "not_applicable":
            raise ValueError(f"Applicable feature unexpectedly not_applicable: {feature}")
        if feature == "resource_role":
            role = legacy.get("resource_role", {})
            if role.get("resource_type") != row["resource_type"] or role.get("resource_role") != value:
                raise ValueError("D-010 resource-role evidence disagrees with feature value")
            basis_facts = {"mapping_entry": role["mapping_entry"],
                           "taxonomy_version": role["taxonomy_version"]}
            basis_method, basis_version = "exact_resource_type_taxonomy", RESOURCE_ROLE_VERSION
            resource_name = str(row["resource"]).split(".", 1)[-1].split("[", 1)[0]
            basis_refs = [{"path": str(source_path), "line_start": provenance["line_start"],
                           "line_end": provenance["line_end"],
                           "literal": f'resource "{row["resource_type"]}" "{resource_name}"'}]
        else:
            basis_facts, basis_method, basis_version, basis_refs = facts, method, CONTRACT_VERSION, refs
            if row["check_id"] == "CKV2_AWS_6" and feature == "public_access":
                basis_version = "d012-v1"
            if (row["check_id"] == "CKV_AWS_130" and feature == "reachability" and
                    facts.get("standalone_route")):
                basis_version = "d011-standalone-route-v1"
            if (row["check_id"] == "CKV_AWS_130" and feature == "reachability" and
                    facts.get("association_resolution_method")):
                basis_version = "d011-count-index-association-v1"
            if (row["check_id"] == "CKV_AWS_382" and feature == "reachability" and
                    row["resource_type"] == "aws_security_group"):
                basis_version = "d011-inline-egress-v1"
            if row["check_id"] == "CKV_AWS_145" and feature == "encryption_missing":
                basis_version = "d009-s3-kms-inventory-v1"
            if row["check_id"] == "CKV2_AWS_11" and feature == "logging_missing":
                basis_version = "d009-vpc-flow-log-inventory-v1"
            if row["check_id"] == "CKV_AWS_38" and feature in (
                    "internet_exposure", "reachability", "public_access"):
                basis_version = "d011-eks-public-endpoint-v1"
        basis = {"value": str(value), "status": "unknown" if value == "unknown" else "determined",
                 "object": row["resource"], "scope": "selected IAM statement" if feature in
                 {"wildcard_action", "wildcard_resource", "privilege_impact"} else
                 ("candidate Terraform artifact" if feature in {"logging_missing", "encryption_missing"}
                  else "finding source region"),
                 "method": basis_method, "method_version": basis_version,
                 "facts": basis_facts, "source_refs": basis_refs}
        if value == "unknown":
            if feature == "resource_role":
                raise ValueError("D-010 resource role cannot be unknown for mapped type")
            reason_code = unknown_reason_code(row, feature, facts)
            detail = facts.get("feature_unknowns", {}).get(feature, {}).get("detail") or uncertainty or (
                f"Selected IAM statement does not statically resolve {feature}")
            if reason_code == "unclassified_action":
                unclassified = list(dict.fromkeys(item["action"] for item in
                    facts["iam"]["action_capabilities"] if item["class"] == "unclassified"))
                detail = ("Selected IAM statement contains unclassified Action " +
                          ", ".join(unclassified) + f" under taxonomy {IAM_ACTION_VERSION}; "
                          "maximum potential capability cannot be determined")
            basis.update(attempted=True,
                         unknown_reason_code=reason_code,
                         unknown_reason_detail=detail)
        else:
            basis["conclusion"] = str(value)
            if value in {"no", "internal"}:
                basis["scope_examined"] = True
        feature_basis[feature] = basis
    return {"contract_version": CONTRACT_VERSION, "provenance": provenance,
            "features": feature_basis, "not_applicable": non_applicable}
