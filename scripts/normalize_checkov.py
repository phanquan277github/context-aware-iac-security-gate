#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_FINDING_FIELDS = [
    "check_id",
    "bc_check_id",
    "check_name",
    "resource",
    "repo_file_path",
    "file_line_range",
    "severity",
    "guideline",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Checkov JSON top level must be an object.")

    return data


def make_finding_id(
    scenario_id: str,
    check_id: Any,
    resource: Any,
    repo_file_path: Any,
    file_line_range: Any,
) -> str:
    raw = json.dumps(
        {
            "scenario_id": scenario_id,
            "check_id": check_id,
            "resource": resource,
            "repo_file_path": repo_file_path,
            "file_line_range": file_line_range,
        },
        sort_keys=True,
        ensure_ascii=False,
    )

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{scenario_id}:{digest}"


def normalize_finding(
    scenario_id: str,
    finding: dict[str, Any],
) -> dict[str, Any]:

    check_result = finding.get("check_result")

    if not isinstance(check_result, dict):
        check_result = {}

    normalized = {
        "finding_id": make_finding_id(
            scenario_id=scenario_id,
            check_id=finding.get("check_id"),
            resource=finding.get("resource"),
            repo_file_path=finding.get("repo_file_path"),
            file_line_range=finding.get("file_line_range"),
        ),
        "scenario_id": scenario_id,
        "check_id": finding.get("check_id"),
        "bc_check_id": finding.get("bc_check_id"),
        "check_name": finding.get("check_name"),
        "resource": finding.get("resource"),
        "repo_file_path": finding.get("repo_file_path"),
        "file_line_range": finding.get("file_line_range"),
        "severity": finding.get("severity"),
        "guideline": finding.get("guideline"),
        "check_result": check_result.get("result"),
        "evaluated_keys": check_result.get("evaluated_keys"),
    }

    return normalized


def normalize_checkov(
    input_path: Path,
    output_path: Path,
    scenario_id: str,
) -> None:

    data = load_json(input_path)

    if data.get("check_type") != "terraform":
        raise ValueError(
            f"Expected Terraform Checkov output, got: {data.get('check_type')!r}"
        )

    results = data.get("results")
    if not isinstance(results, dict):
        raise ValueError("Missing or invalid 'results' object.")

    failed_checks = results.get("failed_checks")

    if not isinstance(failed_checks, list):
        raise ValueError("'results.failed_checks' must be a list.")

    normalized_findings = []

    for index, finding in enumerate(failed_checks, start=1):
        if not isinstance(finding, dict):
            raise ValueError(
                f"failed_checks[{index - 1}] is not an object."
            )

        missing = [
            field
            for field in REQUIRED_FINDING_FIELDS
            if field not in finding
        ]

        if missing:
            raise ValueError(
                f"failed_checks[{index - 1}] is missing fields: {missing}"
            )

        normalized_findings.append(
            normalize_finding(
                scenario_id=scenario_id,
                finding=finding,
            )
        )

    output = {
        "schema_version": "pilot-v1",
        "scenario_id": scenario_id,
        "source": {
            "tool": "Checkov",
            "version": data.get("summary", {}).get("checkov_version"),
            "check_type": data.get("check_type"),
            "input_file": str(input_path),
        },
        "summary": {
            "raw_failed_checks": len(failed_checks),
            "raw_passed_checks": len(results.get("passed_checks", [])),
            "raw_skipped_checks": len(results.get("skipped_checks", [])),
            "raw_parsing_errors": len(results.get("parsing_errors", [])),
            "normalized_findings": len(normalized_findings),
        },
        "findings": normalized_findings,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    print(f"Findings normalized: {len(normalized_findings)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize Checkov Terraform JSON output."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Raw Checkov JSON file.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Normalized JSON output file.",
    )

    parser.add_argument(
        "--scenario-id",
        required=True,
        help="Scenario identifier, e.g. SCN-001.",
    )

    args = parser.parse_args()

    normalize_checkov(
        input_path=args.input,
        output_path=args.output,
        scenario_id=args.scenario_id,
    )


if __name__ == "__main__":
    main()
