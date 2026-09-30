from pathlib import Path
import pandas as pd


INPUT = Path(
    "results/context_feature_pilot/"
    "finding_context_features_pilot.csv"
)

OUTPUT = Path(
    "results/context_feature_pilot/"
    "pilot_evidence_review.txt"
)

CONTEXT = 8


df = pd.read_csv(INPUT).fillna("")


def read_source_excerpt(
    path_value,
    line_start,
    line_end,
    context=CONTEXT,
):
    path = Path(str(path_value))

    if not path.exists():
        return (
            f"[SOURCE FILE NOT FOUND]\n"
            f"{path}\n"
        )

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except Exception as exc:
        return (
            "[SOURCE READ ERROR]\n"
            f"{type(exc).__name__}: {exc}\n"
        )

    try:
        start = int(float(line_start))
        end = int(float(line_end))
    except Exception:
        start = 1
        end = min(
            len(lines),
            40,
        )

    show_start = max(
        1,
        start - context,
    )

    show_end = min(
        len(lines),
        end + context,
    )

    out = []

    for n in range(
        show_start,
        show_end + 1,
    ):
        marker = (
            ">>>"
            if start <= n <= end
            else "   "
        )

        out.append(
            f"{marker} {n:5d} | "
            f"{lines[n - 1]}"
        )

    return "\n".join(out)


def feature_summary(row):
    features = [
        "internet_exposure",
        "reachability",
        "privilege_impact",
        "resource_role",
        "public_access",
        "wildcard_action",
        "wildcard_resource",
        "encryption_missing",
        "logging_missing",
    ]

    return "\n".join(
        f"{name:22s} = {row[name]}"
        for name in features
    )


sections = []


for i, row in df.iterrows():

    section = []

    section.append(
        "=" * 110
    )

    section.append(
        f"ROW {i + 1}/{len(df)}"
    )

    section.append(
        "=" * 110
    )

    section.append(
        f"finding_id   : {row['finding_id']}"
    )

    section.append(
        f"candidate_id : {row['candidate_id']}"
    )

    section.append(
        f"scenario_id  : {row['scenario_id']}"
    )

    section.append(
        f"check_id     : {row['check_id']}"
    )

    section.append(
        f"resource     : {row['resource']}"
    )

    section.append(
        f"resource_type: {row['resource_type']}"
    )

    section.append(
        f"source_path  : {row['source_path']}"
    )

    section.append(
        f"line range   : "
        f"{row['line_start']} - "
        f"{row['line_end']}"
    )

    section.append("")

    section.append(
        "--- EXTRACTED FEATURES ---"
    )

    section.append(
        feature_summary(row)
    )

    section.append("")

    section.append(
        "applicable_unknown_count = "
        f"{row.get('applicable_unknown_count', '')}"
    )

    section.append(
        "applicable_unknown_features = "
        f"{row.get('applicable_unknown_features', '')}"
    )

    section.append("")

    if "feature_evidence" in df.columns:
        section.append(
            "--- EXTRACTOR EVIDENCE ---"
        )

        section.append(
            str(
                row.get(
                    "feature_evidence",
                    "",
                )
            )
        )

        section.append("")

    section.append(
        "--- TERRAFORM SOURCE ---"
    )

    section.append(
        read_source_excerpt(
            row["source_path"],
            row["line_start"],
            row["line_end"],
        )
    )

    section.append("")

    section.append(
        "--- MANUAL REVIEW ---"
    )

    section.append(
        "Expected features:"
    )

    section.append(
        "Review status: PASS / FIX"
    )

    section.append(
        "Review note:"
    )

    sections.append(
        "\n".join(section)
    )


OUTPUT.write_text(
    "\n\n".join(sections),
    encoding="utf-8",
)


print("==============================")
print("PILOT EVIDENCE PACK")
print("==============================")

print(
    "Rows =",
    len(df),
)

print(
    "Output =",
    OUTPUT,
)
