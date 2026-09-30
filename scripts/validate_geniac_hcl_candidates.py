from pathlib import Path
import csv
import subprocess


ROOT = Path(
    "dataset/main/candidates/geniac_hcl"
)

OUT_DIR = Path(
    "results/source_corpus/"
    "geniac_hcl_validation"
)

SUMMARY = (
    OUT_DIR / "validation_summary.csv"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def decode_output(data):
    """
    Decode subprocess output safely.

    Terraform/provider output may contain bytes that are not valid UTF-8.
    We deliberately replace undecodable bytes instead of crashing the batch.
    """

    if data is None:
        return ""

    if isinstance(data, str):
        return data

    return data.decode(
        "utf-8",
        errors="replace",
    )


def run_command(
    cmd,
    cwd,
    timeout,
):
    """
    Run a command without letting encoding errors, timeouts,
    or execution errors terminate the whole validation batch.
    """

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            timeout=timeout,
        )

        return {
            "returncode": result.returncode,
            "output": decode_output(
                result.stdout
            ),
            "timed_out": False,
            "execution_error": "",
        }

    except subprocess.TimeoutExpired as exc:

        output = decode_output(
            exc.stdout
        )

        if output:
            output += "\n"

        output += "TIMEOUT\n"

        return {
            "returncode": 124,
            "output": output,
            "timed_out": True,
            "execution_error": "",
        }

    except Exception as exc:

        return {
            "returncode": 125,
            "output": (
                "EXECUTION ERROR\n"
                f"{type(exc).__name__}: {exc}\n"
            ),
            "timed_out": False,
            "execution_error": repr(exc),
        }


rows = []

candidates = sorted(
    p
    for p in ROOT.iterdir()
    if p.is_dir()
)


for i, candidate in enumerate(
    candidates,
    start=1,
):

    candidate_id = candidate.name

    print(
        f"[{i}/{len(candidates)}] "
        f"{candidate_id}"
    )

    init_log = (
        OUT_DIR
        / f"{candidate_id}_init.log"
    )

    validate_log = (
        OUT_DIR
        / f"{candidate_id}_validate.log"
    )

    # ==========================================================
    # TERRAFORM INIT
    # ==========================================================

    init_result = run_command(
        [
            "terraform",
            "init",
            "-backend=false",
            "-input=false",
            "-no-color",
        ],
        cwd=candidate,
        timeout=180,
    )

    init_log.write_text(
        init_result["output"],
        encoding="utf-8",
        errors="replace",
    )

    init_rc = (
        init_result["returncode"]
    )

    init_timeout = (
        init_result["timed_out"]
    )

    init_execution_error = (
        init_result["execution_error"]
    )

    # ==========================================================
    # TERRAFORM VALIDATE
    # ==========================================================

    if init_rc == 0:

        validate_result = run_command(
            [
                "terraform",
                "validate",
                "-no-color",
            ],
            cwd=candidate,
            timeout=120,
        )

        validate_log.write_text(
            validate_result["output"],
            encoding="utf-8",
            errors="replace",
        )

        validate_rc = (
            validate_result["returncode"]
        )

        validate_timeout = (
            validate_result["timed_out"]
        )

        validate_execution_error = (
            validate_result[
                "execution_error"
            ]
        )

    else:

        validate_rc = ""

        validate_timeout = False

        validate_execution_error = ""

        validate_log.write_text(
            (
                "SKIPPED: terraform validate "
                "was not executed because "
                "terraform init failed.\n"
            ),
            encoding="utf-8",
        )

    # ==========================================================
    # CLASSIFICATION
    # ==========================================================

    if init_timeout:

        status = "TIMEOUT_INIT"

    elif init_execution_error:

        status = "EXECUTION_ERROR_INIT"

    elif init_rc != 0:

        status = "INIT_FAILED"

    elif validate_timeout:

        status = "TIMEOUT_VALIDATE"

    elif validate_execution_error:

        status = "EXECUTION_ERROR_VALIDATE"

    elif validate_rc != 0:

        status = "VALIDATE_FAILED"

    else:

        status = "PASS"

    rows.append({
        "candidate_id": candidate_id,
        "init_exit_code": init_rc,
        "validate_exit_code": validate_rc,
        "init_timeout": init_timeout,
        "validate_timeout": validate_timeout,
        "init_execution_error": (
            init_execution_error
        ),
        "validate_execution_error": (
            validate_execution_error
        ),
        "status": status,
    })


# ==============================================================
# WRITE SUMMARY
# ==============================================================

with SUMMARY.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "candidate_id",
            "init_exit_code",
            "validate_exit_code",
            "init_timeout",
            "validate_timeout",
            "init_execution_error",
            "validate_execution_error",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


# ==============================================================
# PRINT SUMMARY
# ==============================================================

passed = sum(
    r["status"] == "PASS"
    for r in rows
)

init_failed = sum(
    r["status"] == "INIT_FAILED"
    for r in rows
)

validate_failed = sum(
    r["status"] == "VALIDATE_FAILED"
    for r in rows
)

timeout_init = sum(
    r["status"] == "TIMEOUT_INIT"
    for r in rows
)

timeout_validate = sum(
    r["status"] == "TIMEOUT_VALIDATE"
    for r in rows
)

execution_error_init = sum(
    r["status"] == "EXECUTION_ERROR_INIT"
    for r in rows
)

execution_error_validate = sum(
    r["status"] == "EXECUTION_ERROR_VALIDATE"
    for r in rows
)


print()
print("==============================")
print("GENIAC LOCAL VALIDATION")
print("==============================")
print("Candidates =", len(rows))
print("PASS =", passed)
print("INIT_FAILED =", init_failed)
print("VALIDATE_FAILED =", validate_failed)
print("TIMEOUT_INIT =", timeout_init)
print(
    "TIMEOUT_VALIDATE =",
    timeout_validate,
)
print(
    "EXECUTION_ERROR_INIT =",
    execution_error_init,
)
print(
    "EXECUTION_ERROR_VALIDATE =",
    execution_error_validate,
)
print("Output =", SUMMARY)
