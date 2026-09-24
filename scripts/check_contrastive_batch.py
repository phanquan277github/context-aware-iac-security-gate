#!/usr/bin/env python3

import csv
import json
import re
from pathlib import Path


IN_SCOPE = {
    "CKV2_AWS_40",
    "CKV_AWS_129",
    "CKV_AWS_145",
    "CKV_AWS_16",
    "CKV_AWS_17",
    "CKV_AWS_18",
    "CKV_AWS_20",
    "CKV_AWS_24",
    "CKV_AWS_286",
    "CKV_AWS_289",
    "CKV_AWS_355",
    "CKV_AWS_62",
    "CKV_AWS_63",
}

FAMILIES = [f"CTX-{i:02d}" for i in range(1, 11)]


def load_checkov_json(path_str: str) -> dict:
    path = Path(path_str)

    if path.is_file():
        json_path = path
    elif path.is_dir():
        candidates = sorted(path.rglob("*.json"))
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one JSON file under {path}, "
                f"found {len(candidates)}"
            )
        json_path = candidates[0]
    else:
        raise FileNotFoundError(path)

    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def failed_checks(data: dict) -> list[dict]:
    return data.get("results", {}).get("failed_checks", [])


def family_findings(findings, family_id, side):
    marker = f"/{family_id}/context_{side}/"

    out = []
    for x in findings:
        file_abs = x.get("file_abs_path", "")
        if marker in file_abs:
            out.append(x)

    return out


def signature(findings):
    return sorted(
        (
            x.get("check_id"),
            x.get("resource"),
        )
        for x in findings
    )


def main():
    parser_input = __import__("argparse").ArgumentParser()
    parser_input.add_argument("--a", required=True)
    parser_input.add_argument("--b", required=True)
    parser_input.add_argument("--output", required=True)
    args = parser_input.parse_args()

    data_a = load_checkov_json(args.a)
    data_b = load_checkov_json(args.b)

    failed_a = failed_checks(data_a)
    failed_b = failed_checks(data_b)

    rows = []

    for family_id in FAMILIES:
        a = family_findings(failed_a, family_id, "a")
        b = family_findings(failed_b, family_id, "b")

        sig_equal = signature(a) == signature(b)

        in_scope_a = [
            x for x in a if x.get("check_id") in IN_SCOPE
        ]
        in_scope_b = [
            x for x in b if x.get("check_id") in IN_SCOPE
        ]

        if not sig_equal:
            status = "FAIL"
        elif len(in_scope_a) >= 1 and len(in_scope_b) >= 1:
            status = "VERIFIED"
        else:
            status = "REVIEW"

        rows.append({
            "family_id": family_id,
            "raw_failed_A": len(a),
            "raw_failed_B": len(b),
            "raw_signature_equal": "PASS" if sig_equal else "FAIL",
            "in_scope_A": len(in_scope_a),
            "in_scope_B": len(in_scope_b),
            "status": status,
        })

        print(
            f"{family_id}: "
            f"A={len(a)} "
            f"B={len(b)} "
            f"signature={'PASS' if sig_equal else 'FAIL'} "
            f"in_scope_A={len(in_scope_a)} "
            f"in_scope_B={len(in_scope_b)} "
            f"status={status}"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "family_id",
                "raw_failed_A",
                "raw_failed_B",
                "raw_signature_equal",
                "in_scope_A",
                "in_scope_B",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
