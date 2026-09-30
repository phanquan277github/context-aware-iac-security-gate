from pathlib import Path
import subprocess
import json
import pandas as pd
from datetime import datetime, timezone


CORPUS = Path(
    "dataset/main/corpus/geniac_tier_a"
)

MANIFEST = Path(
    "dataset/main/manifests/"
    "geniac_corpus_manifest.csv"
)

OUT_DIR = Path(
    "results/security_scans/"
    "checkov/geniac_tier_a"
)

RAW_DIR = OUT_DIR / "raw"
LOG_DIR = OUT_DIR / "logs"

SUMMARY_OUT = (
    OUT_DIR / "scan_summary.csv"
)

FINDINGS_OUT = (
    OUT_DIR / "findings_raw.csv"
)

METADATA_OUT = (
    OUT_DIR / "run_metadata.json"
)

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def decode(data):
    if data is None:
        return ""

    if isinstance(data, str):
        return data

    return data.decode(
        "utf-8",
        errors="replace",
    )


def get_checkov_version():
    result = subprocess.run(
        ["checkov", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
    )

    return decode(
        result.stdout
    ).strip()


def normalize_checkov_result(obj):
    """
    Checkov normally returns one dict for:
        --framework terraform

    Keep support for list output so the pipeline
    remains robust to CLI output differences.
    """

    if isinstance(obj, dict):
        return [obj]

    if isinstance(obj, list):
        return [
            x for x in obj
            if isinstance(x, dict)
        ]

    return []


manifest = pd.read_csv(
    MANIFEST
).fillna("")

manifest = manifest[
    manifest[
        "include_main_evaluation"
    ].astype(str).str.lower().eq("true")
].copy()

manifest_by_id = {
    row["candidate_id"]: row
    for _, row in manifest.iterrows()
}


checkov_version = (
    get_checkov_version()
)

print(
    "Checkov version =",
    checkov_version,
)

print(
    "Tier A artifacts =",
    len(manifest),
)


run_metadata = {
    "scanner": "checkov",
    "scanner_version": checkov_version,
    "framework": "terraform",
    "corpus": "geniac_tier_a",
    "expected_artifacts": len(manifest),
    "external_module_download": False,
    "soft_fail": True,
    "scan_scope": (
        "Root generated Terraform artifact only; "
        "external modules are not downloaded."
    ),
    "started_at_utc": (
        datetime.now(
            timezone.utc
        ).isoformat()
    ),
    "command_template": (
        "checkov --file main.tf "
        "--framework terraform "
        "--output json "
        "--quiet "
        "--soft-fail "
        "--download-external-modules false"
    ),
}

METADATA_OUT.write_text(
    json.dumps(
        run_metadata,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


candidate_dirs = sorted(
    p
    for p in CORPUS.iterdir()
    if p.is_dir()
)


summary_rows = []
finding_rows = []


for i, candidate in enumerate(
    candidate_dirs,
    start=1,
):

    candidate_id = candidate.name

    print(
        f"[{i}/{len(candidate_dirs)}] "
        f"{candidate_id}"
    )

    tf_file = candidate / "main.tf"

    manifest_row = (
        manifest_by_id.get(
            candidate_id
        )
    )

    if manifest_row is None:

        summary_rows.append({
            "candidate_id": candidate_id,
            "scan_status": (
                "MANIFEST_MISSING"
            ),
        })

        continue

    try:

        result = subprocess.run(
            [
                "checkov",
                "--file",
                "main.tf",
                "--framework",
                "terraform",
                "--output",
                "json",
                "--quiet",
                "--soft-fail",
                "--download-external-modules",
                "false",
            ],
            cwd=candidate,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            timeout=300,
        )

        stdout = decode(
            result.stdout
        )

        stderr = decode(
            result.stderr
        )

        raw_file = (
            RAW_DIR
            / f"{candidate_id}.json"
        )

        raw_file.write_text(
            stdout,
            encoding="utf-8",
            errors="replace",
        )

        log_file = (
            LOG_DIR
            / f"{candidate_id}.log"
        )

        log_file.write_text(
            stderr,
            encoding="utf-8",
            errors="replace",
        )

    except subprocess.TimeoutExpired as exc:

        summary_rows.append({
            "candidate_id": candidate_id,
            "scenario_id": (
                manifest_row[
                    "scenario_id"
                ]
            ),
            "complexity": (
                manifest_row[
                    "complexity"
                ]
            ),
            "model": (
                manifest_row[
                    "model"
                ]
            ),
            "sha256": (
                manifest_row[
                    "sha256"
                ]
            ),
            "scan_status": "TIMEOUT",
            "scanner": "checkov",
            "scanner_version": (
                checkov_version
            ),
        })

        continue

    except Exception as exc:

        summary_rows.append({
            "candidate_id": candidate_id,
            "scenario_id": (
                manifest_row[
                    "scenario_id"
                ]
            ),
            "complexity": (
                manifest_row[
                    "complexity"
                ]
            ),
            "model": (
                manifest_row[
                    "model"
                ]
            ),
            "sha256": (
                manifest_row[
                    "sha256"
                ]
            ),
            "scan_status": (
                "EXECUTION_ERROR"
            ),
            "execution_error": (
                repr(exc)
            ),
            "scanner": "checkov",
            "scanner_version": (
                checkov_version
            ),
        })

        continue

    try:

        parsed = json.loads(
            stdout
        )

        blocks = (
            normalize_checkov_result(
                parsed
            )
        )

    except Exception as exc:

        summary_rows.append({
            "candidate_id": candidate_id,
            "scenario_id": (
                manifest_row[
                    "scenario_id"
                ]
            ),
            "complexity": (
                manifest_row[
                    "complexity"
                ]
            ),
            "model": (
                manifest_row[
                    "model"
                ]
            ),
            "sha256": (
                manifest_row[
                    "sha256"
                ]
            ),
            "scan_status": (
                "JSON_PARSE_ERROR"
            ),
            "process_exit_code": (
                result.returncode
            ),
            "execution_error": (
                repr(exc)
            ),
            "scanner": "checkov",
            "scanner_version": (
                checkov_version
            ),
        })

        continue


    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_parsing_errors = 0
    total_resources = 0

    artifact_failed_checks = []


    for block in blocks:

        summary = block.get(
            "summary",
            {},
        ) or {}

        total_passed += int(
            summary.get(
                "passed",
                0,
            ) or 0
        )

        total_failed += int(
            summary.get(
                "failed",
                0,
            ) or 0
        )

        total_skipped += int(
            summary.get(
                "skipped",
                0,
            ) or 0
        )

        total_parsing_errors += int(
            summary.get(
                "parsing_errors",
                0,
            ) or 0
        )

        total_resources += int(
            summary.get(
                "resource_count",
                0,
            ) or 0
        )

        results = block.get(
            "results",
            {},
        ) or {}

        artifact_failed_checks.extend(
            results.get(
                "failed_checks",
                [],
            ) or []
        )


    if not blocks:

        scan_status = (
            "UNEXPECTED_JSON_STRUCTURE"
        )

    elif total_parsing_errors > 0:

        scan_status = (
            "SCAN_WITH_PARSING_ERRORS"
        )

    else:

        scan_status = "SCAN_OK"


    summary_rows.append({
        "candidate_id": candidate_id,
        "scenario_id": (
            manifest_row[
                "scenario_id"
            ]
        ),
        "complexity": (
            manifest_row[
                "complexity"
            ]
        ),
        "model": (
            manifest_row[
                "model"
            ]
        ),
        "sha256": (
            manifest_row[
                "sha256"
            ]
        ),
        "corpus_tier": (
            manifest_row[
                "corpus_tier"
            ]
        ),
        "scanner": "checkov",
        "scanner_version": (
            checkov_version
        ),
        "process_exit_code": (
            result.returncode
        ),
        "scan_status": (
            scan_status
        ),
        "passed_checks": (
            total_passed
        ),
        "failed_checks": (
            total_failed
        ),
        "skipped_checks": (
            total_skipped
        ),
        "parsing_errors": (
            total_parsing_errors
        ),
        "resource_count": (
            total_resources
        ),
        "raw_json_path": str(
            RAW_DIR
            / f"{candidate_id}.json"
        ),
    })


    for finding in (
        artifact_failed_checks
    ):

        check_result = (
            finding.get(
                "check_result",
                {},
            )
            or {}
        )

        file_line_range = (
            finding.get(
                "file_line_range",
                []
            )
        )

        finding_rows.append({
            "candidate_id": (
                candidate_id
            ),

            "scenario_id": (
                manifest_row[
                    "scenario_id"
                ]
            ),

            "complexity": (
                manifest_row[
                    "complexity"
                ]
            ),

            "model": (
                manifest_row[
                    "model"
                ]
            ),

            "artifact_sha256": (
                manifest_row[
                    "sha256"
                ]
            ),

            "scanner": "checkov",

            "scanner_version": (
                checkov_version
            ),

            "check_id": (
                finding.get(
                    "check_id",
                    ""
                )
            ),

            "bc_check_id": (
                finding.get(
                    "bc_check_id",
                    ""
                )
            ),

            "check_name": (
                finding.get(
                    "check_name",
                    ""
                )
            ),

            "severity": (
                finding.get(
                    "severity",
                    ""
                )
            ),

            "resource": (
                finding.get(
                    "resource",
                    ""
                )
            ),

            "file_path": (
                finding.get(
                    "file_path",
                    ""
                )
            ),

            "file_line_range": (
                json.dumps(
                    file_line_range
                )
            ),

            "check_result": (
                check_result.get(
                    "result",
                    ""
                )
            ),

            "evaluated_keys": (
                json.dumps(
                    check_result.get(
                        "evaluated_keys",
                        [],
                    ),
                    ensure_ascii=False,
                )
            ),

            "guideline": (
                finding.get(
                    "guideline",
                    ""
                )
            ),
        })


summary_df = pd.DataFrame(
    summary_rows
)

findings_df = pd.DataFrame(
    finding_rows
)


summary_df.to_csv(
    SUMMARY_OUT,
    index=False,
)

findings_df.to_csv(
    FINDINGS_OUT,
    index=False,
)


run_metadata[
    "finished_at_utc"
] = datetime.now(
    timezone.utc
).isoformat()

run_metadata[
    "artifacts_scanned"
] = len(summary_df)

run_metadata[
    "findings_extracted"
] = len(findings_df)

METADATA_OUT.write_text(
    json.dumps(
        run_metadata,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


print()
print("==============================")
print("CHECKOV TIER A SCAN")
print("==============================")

print(
    "Artifacts =",
    len(summary_df),
)

print()

print("=== SCAN STATUS ===")

print(
    summary_df[
        "scan_status"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)

print()

if len(summary_df):

    print(
        "Total resources =",
        int(
            summary_df[
                "resource_count"
            ]
            .fillna(0)
            .sum()
        ),
    )

    print(
        "Total failed checks =",
        int(
            summary_df[
                "failed_checks"
            ]
            .fillna(0)
            .sum()
        ),
    )

    print(
        "Total parsing errors =",
        int(
            summary_df[
                "parsing_errors"
            ]
            .fillna(0)
            .sum()
        ),
    )


print(
    "Finding rows =",
    len(findings_df),
)

print()

print(
    "Summary =",
    SUMMARY_OUT,
)

print(
    "Findings =",
    FINDINGS_OUT,
)

print(
    "Run metadata =",
    METADATA_OUT,
)
