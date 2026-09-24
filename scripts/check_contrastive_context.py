from pathlib import Path
import sys
import yaml

root = Path(sys.argv[1])

a_path = root / "context_a" / "context.yaml"
b_path = root / "context_b" / "context.yaml"

with a_path.open(encoding="utf-8") as f:
    a = yaml.safe_load(f)

with b_path.open(encoding="utf-8") as f:
    b = yaml.safe_load(f)

required = [
    "family_id",
    "scenario_id",
    "base_seed_id",
    "context_variant",
    "environment",
    "asset_criticality",
    "data_sensitivity",
]

for name, data in [("A", a), ("B", b)]:
    missing = [
        key for key in required
        if key not in data
    ]

    if missing:
        raise SystemExit(
            f"{name}: missing fields: {missing}"
        )

if a["family_id"] != b["family_id"]:
    raise SystemExit("family_id mismatch")

if a["base_seed_id"] != b["base_seed_id"]:
    raise SystemExit("base_seed_id mismatch")

if a["context_variant"] != "A":
    raise SystemExit("Context A has wrong variant")

if b["context_variant"] != "B":
    raise SystemExit("Context B has wrong variant")

expected_a = {
    "environment": "dev",
    "asset_criticality": "low",
    "data_sensitivity": "low",
}

expected_b = {
    "environment": "prod",
    "asset_criticality": "high",
    "data_sensitivity": "high",
}

for key, value in expected_a.items():
    if a[key] != value:
        raise SystemExit(
            f"Context A {key}: expected {value}, got {a[key]}"
        )

for key, value in expected_b.items():
    if b[key] != value:
        raise SystemExit(
            f"Context B {key}: expected {value}, got {b[key]}"
        )

for key in expected_a:
    if a[key] == b[key]:
        raise SystemExit(
            f"Context factor did not differ: {key}"
        )

print("RESULT: PASS")
print("family:", a["family_id"])
print("A:", a)
print("B:", b)
