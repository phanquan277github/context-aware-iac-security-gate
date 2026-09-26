from pathlib import Path
import pandas as pd


FINDINGS = Path(
    "dataset/main/findings/"
    "geniac_tier_a_checkov.csv"
)

SCOPE = Path(
    "dataset/main/research_scope/"
    "research_scope_rules.csv"
)

OUT = Path(
    "dataset/main/research_scope/"
    "research_scope_findings.csv"
)


findings = pd.read_csv(
    FINDINGS
)

scope = pd.read_csv(
    SCOPE
)


scope_ids = set(
    scope["check_id"]
)


df = findings[
    findings[
        "check_id"
    ].isin(scope_ids)
].copy()


df = df.merge(
    scope[
        [
            "check_id",
            "security_domain",
            "context_sensitive",
            "research_priority",
        ]
    ],
    on="check_id",
    how="left",
)


df.to_csv(
    OUT,
    index=False,
)


print(
    "Research-scope findings =",
    len(df),
)

print(
    "Unique finding IDs =",
    df["finding_id"].nunique(),
)

print(
    "Artifacts =",
    df["candidate_id"].nunique(),
)

print(
    "Scenarios =",
    df["scenario_id"].nunique(),
)

print(
    "Rules =",
    df["check_id"].nunique(),
)

print(
    "Output =",
    OUT,
)
