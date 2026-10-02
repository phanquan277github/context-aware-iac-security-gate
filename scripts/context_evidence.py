"""D-009 evidence construction for the approved finding-level extractor.

The assertions here are deliberately narrow. An unsupported source form is an
extraction failure, not evidence for a negative observation.
"""

import hashlib
from pathlib import Path
import re


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


def blocks(text, kind):
    """Locate resource blocks with brace tracking; reject incomplete blocks."""
    pattern = re.compile(r'\bresource\s+"' + re.escape(kind) + r'"\s+"([^"]+)"\s*\{')
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


def subnet_internet_route(row, inventory):
    """Prove only an exact subnet -> association -> default route -> IGW path."""
    name = str(row["resource"]).split(".", 1)[-1].split("[", 1)[0]
    indexed = bool(re.search(r'\[\d+\]$', str(row["resource"])))
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
    assoc_target = f"aws_subnet.{name}" + ("[count.index].id" if indexed else ".id")
    matches = []
    for aname, ablock, apath, aa, ab in resource_blocks(inventory, "aws_route_table_association"):
        if assignment(ablock, "subnet_id") != assoc_target:
            continue
        if indexed and assignment(ablock, "count") != count:
            continue
        matches.append((aname, ablock, apath, aa, ab))
    if len(matches) != 1:
        facts["unresolved_path_elements"].append("unique indexed route-table association")
        return False, facts, refs
    aname, ablock, apath, aa, ab = matches[0]
    table_id = assignment(ablock, "route_table_id")
    facts["route_table_association"] = f"aws_route_table_association.{aname}"
    facts["resolved_components"].append("route_table_association")
    refs.extend((ref(apath, aa, ab, assoc_target), ref(apath, aa, ab, table_id or "route_table_id")))
    if indexed and count:
        refs.append(ref(apath, aa, ab, assignment_literal(ablock, "count")))
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
    gateways = [(assignment(route, "gateway_id"), route) for route in routes
                if assignment(route, "cidr_block") == '"0.0.0.0/0"']
    if len(gateways) != 1:
        facts["unresolved_path_elements"].append("unique default route")
        return False, facts, refs
    gateway, selected_route = gateways[0]
    match = re.fullmatch(r'aws_internet_gateway\.([\w-]+)\.id', gateway or "")
    if not match:
        facts["unresolved_path_elements"].append("default route to Internet Gateway")
        return False, facts, refs
    facts["default_route"] = "0.0.0.0/0"
    facts["resolved_components"].append("default_route")
    refs.extend((ref(tpath, ta, tb, assignment_literal(selected_route, "cidr_block")),
                 ref(tpath, ta, tb, gateway)))
    igws = [(block, ipath, ia, ib) for n, block, ipath, ia, ib in
            resource_blocks(inventory, "aws_internet_gateway") if n == match.group(1)]
    if len(igws) != 1 or assignment(igws[0][0], "vpc_id") != vpc:
        facts["unresolved_path_elements"].append("same-VPC Internet Gateway")
        return False, facts, refs
    _, ipath, ia, ib = igws[0]
    facts["internet_gateway"] = f"aws_internet_gateway.{match.group(1)}"
    facts["resolved_components"].append("internet_gateway")
    refs.append(ref(ipath, ia, ib, vpc))
    return True, facts, refs


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
        declarations = [(path, name) for path, text in candidate_text(inventory)
                        for name, _, _ in blocks(text, "aws_flow_log")]
        if declarations:
            raise ValueError("Cannot prove logging_missing=yes: aws_flow_log exists in candidate scope")
        facts.update(control="VPC flow logging", candidate_scope_examined=inventory,
                     flow_log_declarations=[])
        refs.extend({"path": item["path"], "sha256": item["sha256"]} for item in inventory)
        method = "candidate_resource_inventory"
    elif check == "CKV2_AWS_6":
        controls, control_refs = s3_access_controls(inventory, resource_name)
        facts.update(control="S3 Public Access Block", **controls,
                     static_public_access_relation="unresolved")
        refs.extend(control_refs)
        method = "candidate_access_control_inventory"
        uncertainty = (f"Explicit access controls for {row['resource']} in this candidate do not "
                       "establish effective public or non-public access; no provider defaults inferred")
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
        bucket_name = str(row["resource"]).split(".", 1)[-1]
        path, a, b, algorithm, block = linked_s3_encryption(inventory, bucket_name)
        if algorithm != "AES256":
            raise ValueError(f"Unsupported KMS-control evidence: sse_algorithm={algorithm}")
        facts.update(control="KMS-based S3 default encryption", linked_bucket=row["resource"],
                     sse_algorithm=algorithm, relationship="bucket reference in encryption configuration")
        refs.append(ref(path, a, b, 'sse_algorithm = "AES256"'))
        refs.append(ref(path, a, b, f'aws_s3_bucket.{bucket_name}.id'))
        method = "linked_resource_and_scanner"
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
        match = re.search(r'\bendpoint_public_access\s*=\s*true\b', region)
        if not match:
            raise ValueError("EKS public endpoint literal absent from finding region")
        facts.update(direction="ingress", endpoint_public_access=True,
                     path="EKS public endpoint", source_cidr=None)
        refs.append(ref(source_path, start, end, match.group(0)))
    elif check == "CKV_AWS_382":
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
            detail = uncertainty or (
                f"Selected IAM statement does not statically resolve {feature}")
            basis.update(attempted=True,
                         unknown_reason_code=unknown_reason_code(row, feature, facts),
                         unknown_reason_detail=detail)
        else:
            basis["conclusion"] = str(value)
            if value in {"no", "internal"}:
                basis["scope_examined"] = True
        feature_basis[feature] = basis
    return {"contract_version": CONTRACT_VERSION, "provenance": provenance,
            "features": feature_basis, "not_applicable": non_applicable}
