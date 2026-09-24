#!/usr/bin/env python3

import argparse
import json
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


def load_checkov_json(path_str: str) -> dict:
    path = Path(path_str)

    if path.is_file():
        json_path = path
    elif path.is_dir():
        candidates = sorted(path.rglob("*.json"))
        if not candidates:
            raise FileNotFoundError(f"No JSON file found under: {path}")
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one JSON file under {path}, "
                f"found {len(candidates)}"
            )
        json_path = candidates[0]
    else:
        raise FileNotFoundError(f"Path does not exist: {path}")

    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_failed_checks(data: dict) -> list[dict]:
    return data.get("results", {}).get("failed_checks", [])


def raw_signature(failed_checks: list[dict]) -> list[tuple]:
    # Checkov 3.3.17 output observed in this dataset has
    # resource_address = null, so use resource.
    return sorted(
        (
            item.get("check_id"),
            item.get("resource"),
            item.get("file_path"),
        )
        for item in failed_checks
    )


def in_scope_signature(failed_checks: list[dict]) -> list[tuple]:
    return sorted(
        (
            item.get("check_id"),
            item.get("resource"),
            item.get("file_path"),
        )
        for item in failed_checks
        if item.get("check_id") in IN_SCOPE
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    args = parser.parse_args()

    data_a = load_checkov_json(args.a)
    data_b = load_checkov_json(args.b)

    failed_a = get_failed_checks(data_a)
    failed_b = get_failed_checks(data_b)

    raw_a = raw_signature(failed_a)
    raw_b = raw_signature(failed_b)

    scope_a = in_scope_signature(failed_a)
    scope_b = in_scope_signature(failed_b)

    raw_equal = raw_a == raw_b
    has_in_scope = len(scope_a) > 0 and len(scope_b) > 0

    if not raw_equal:
        status = "FAIL"
    elif not has_in_scope:
        status = "REVIEW"
    else:
        status = "VERIFIED"

    print(f"raw_failed_A={len(failed_a)}")
    print(f"raw_failed_B={len(failed_b)}")
    print(f"raw_signature_equal={'PASS' if raw_equal else 'FAIL'}")
    print(f"in_scope_A={len(scope_a)}")
    print(f"in_scope_B={len(scope_b)}")
    print(f"status={status}")

    print("\nA in-scope findings:")
    for row in scope_a:
        print(row)

    print("\nB in-scope findings:")
    for row in scope_b:
        print(row)


if __name__ == "__main__":
    main()
