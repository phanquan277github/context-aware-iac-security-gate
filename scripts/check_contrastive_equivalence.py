from pathlib import Path
import hashlib
import sys

root = Path(sys.argv[1])

a_dir = root / "context_a"
b_dir = root / "context_b"

def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)

    return h.hexdigest()

a_files = sorted(
    p.name for p in a_dir.glob("*.tf")
)

b_files = sorted(
    p.name for p in b_dir.glob("*.tf")
)

print("A Terraform files:", a_files)
print("B Terraform files:", b_files)

if a_files != b_files:
    print("RESULT: FAIL")
    raise SystemExit(1)

for name in a_files:
    a_hash = sha256(a_dir / name)
    b_hash = sha256(b_dir / name)

    print(name)
    print("  A:", a_hash)
    print("  B:", b_hash)

    if a_hash != b_hash:
        print("RESULT: FAIL")
        print("Terraform content differs.")
        raise SystemExit(1)

print("RESULT: PASS")
print("Terraform content is identical.")
