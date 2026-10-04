# Báo cáo validation contextual features chính — Phase 3

Checkpoint: 2026-10-04 16:17 UTC. Bộ finding-level contextual features chính đã được chấp nhận về nghiên cứu; artifact đã persist được kiểm tra; Feature Spec v1.0 được ghi tại `docs/feature_spec_v1.md`. Báo cáo này ghi lại kết quả acceptance audit độc lập đã hoàn tất và bước đóng Phase 3. Validator PASS tự nó không phải là quyết định research acceptance.

## Artifact và khả năng tái tạo

| Artifact | Đường dẫn | SHA-256 |
|---|---|---|
| Findings nguồn | `dataset/main/findings/geniac_tier_a_checkov.csv` | Chỉ đọc và lọc theo matrix; không sửa |
| Applicability matrix | `dataset/main/context/rule_context_applicability.csv` | `f04c781262e42407fc9b265a47fa463857f245774dbccd867fd8e3e380595b8a` |
| Input chính được dựng lại | `/tmp/phase3_closeout_main_input.csv` | `a2b2ad2dd00d38fc7250523df53f26a76037191a58ea7560195d536242eaa60b` |
| Output tạm đã được chấp nhận | `/tmp/phase3_closeout_features.csv` | `67295a1742a01a77dd35a3a817e591a6206356a963f5fe46edae6481b6ac9164` |
| Dataset đã persist, vị trí canonical | `results/main_context_features/features_v1.csv` | `67295a1742a01a77dd35a3a817e591a6206356a963f5fe46edae6481b6ac9164` |

Input được dựng lại bằng cách giữ nguyên thứ tự hàng/cột của `geniac_tier_a_checkov.csv` và chỉ lấy các hàng có `check_id` thuộc 10 rule của matrix. Cả hai hash input và output tạm đều khớp checkpoint acceptance **trước khi** output được sao chép nguyên byte sang vị trí canonical. Từ repository root, có thể tái dựng input như sau:

```sh
.venv/bin/python -B - <<'PY'
import csv
from pathlib import Path
with Path('dataset/main/context/rule_context_applicability.csv').open(newline='', encoding='utf-8') as stream:
    rules = {row['check_id'] for row in csv.DictReader(stream)}
with Path('dataset/main/findings/geniac_tier_a_checkov.csv').open(newline='', encoding='utf-8') as stream:
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    rows = [row for row in reader if row['check_id'] in rules]
with Path('/tmp/phase3_closeout_main_input.csv').open('w', newline='', encoding='utf-8') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
PY
.venv/bin/python -B scripts/extract_finding_context_features.py --input /tmp/phase3_closeout_main_input.csv --output /tmp/phase3_closeout_features.csv
sha256sum /tmp/phase3_closeout_main_input.csv /tmp/phase3_closeout_features.csv results/main_context_features/features_v1.csv
```

Terraform source có thể được tái dựng theo `docs/dataset_source_provenance.md`. Extractor chưa có release-version constant riêng. Snapshot implementation được chấp nhận được định danh bằng SHA-256: `scripts/extract_finding_context_features.py` = `7578abdf6fd9434dcc1edf6858d65f72608ca12cce7d643fff4ff26e7f30a954`; `scripts/context_evidence.py` = `db3685703b1ab80d623c9e0693121255fb9ecc8ba4ec9b9e787aa7c2092486df`. Evidence contract = `d009-v1`; schema = `1.1`; IAM Action taxonomy = `d008-v1`; resource-role taxonomy = `d010-v1`. Mỗi hàng giữ feature-specific method/version trong `feature_evidence`.

## Coverage và research acceptance

- 369 findings với 369 `finding_id` duy nhất, 10 research-scope rules, 81 candidates, 9 resource types và 9 finding-level contextual features.
- 3.321 feature cells: 1.031 applicable, 2.290 `not_applicable`, 216 applicable `unknown`.
- Extraction status: 369 `EXTRACTED`, 0 failures.
- Final semantic-evidence acceptance audit độc lập: 369 `AUTOMATED_VERIFIED`, 662 `MANUAL_VERIFIED`, 0 `INSUFFICIENT_EVIDENCE`, 0 `SEMANTIC_CONFLICT`, 0 `EXTRACTION_FAILURE`. Có 2.290 non-applicable cells được đối chiếu với applicability matrix. Các classification này là checkpoint audit đã chấp thuận, không suy từ exit code của validator.

| Rule | Findings |
|---|---:|
| CKV_AWS_130 | 87 |
| CKV_AWS_382 | 83 |
| CKV2_AWS_11 | 55 |
| CKV_AWS_145 | 30 |
| CKV2_AWS_6 | 26 |
| CKV_AWS_260 | 21 |
| CKV_AWS_355 | 21 |
| CKV_AWS_290 | 18 |
| CKV_AWS_38 | 16 |
| CKV_AWS_117 | 12 |

## Phân phối feature values

| Feature | Giá trị và số lượng |
|---|---|
| `internet_exposure` | `yes` 32; `unknown` 92; `not_applicable` 245 |
| `reachability` | `internet` 197; `unknown` 10; `not_applicable` 162 |
| `privilege_impact` | `1` 3; `2` 28; `3` 6; `unknown` 2; `not_applicable` 330 |
| `resource_role` | `network` 246; `primary_data` 56; `identity` 39; `compute` 28 |
| `public_access` | `yes` 40; `unknown` 110; `not_applicable` 219 |
| `wildcard_action` | `yes` 3; `no` 15; `not_applicable` 351 |
| `wildcard_resource` | `yes` 39; `not_applicable` 330 |
| `encryption_missing` | `yes` 28; `unknown` 2; `not_applicable` 339 |
| `logging_missing` | `yes` 55; `not_applicable` 314 |

## Phân phối unknown reason codes

| Reason code | Feature | Số lượng |
|---|---|---:|
| `insufficient_static_relationship` | `internet_exposure` | 82 |
| `insufficient_static_relationship` | `public_access` | 82 |
| `insufficient_static_path` | `internet_exposure` | 10 |
| `insufficient_static_path` | `reachability` | 10 |
| `insufficient_static_path` | `public_access` | 10 |
| `insufficient_access_control_evidence` | `public_access` | 18 |
| `unclassified_action` | `privilege_impact` | 2 |
| `unsupported_static_construct` | `encryption_missing` | 2 |
| **Tổng** | | **216** |

## Validation trên chính artifact đã persist

Các lệnh sau chạy từ repository root ngày 2026-10-04. Mỗi lệnh có exit code 0.

| Lệnh | Exit | Kết quả |
|---|---:|---|
| `.venv/bin/python -B scripts/validate_finding_context_features.py --input results/main_context_features/features_v1.csv --findings /tmp/phase3_closeout_main_input.csv` | 0 | PASS; 369 records, 3.321 cells, 1.031 applicable, 2.290 NA, 216 unknown; 0 errors, 0 warnings |
| `.venv/bin/python -B scripts/validate_context_evidence.py --input results/main_context_features/features_v1.csv` | 0 | PASS; 1.031 applicable bases, 2.290 NA bases, 216 unknown bases; 0 errors, 0 warnings |
| `.venv/bin/python -B scripts/validate_context_schema.py` | 0 | PASS; 9 finding features, 10 scope rules |
| `.venv/bin/python -B -m unittest discover -s scripts -p 'test_*.py' -q` | 0 | 180 tests, OK |
| `git diff --check` | 0 | PASS |
| `sha256sum results/main_context_features/features_v1.csv` | 0 | Khớp output hash đã chấp nhận |

## Phạm vi và giới hạn

Acceptance dựa trên Terraform tĩnh và Checkov scanner evidence được phê duyệt. Kết quả không khẳng định trạng thái AWS đã triển khai, provider defaults không có trong candidate, hay IAM permission thực tế sau toàn bộ policy evaluation. Evidence v1 validator kiểm các source assertions deterministic; nó không thay thế acceptance audit độc lập đã hoàn tất.

Các giới hạn provenance trong `docs/dataset_source_provenance.md` vẫn tồn tại: chưa có vị trí archive bất biến và procedure truy xuất historical raw Checkov JSON; implicit Checkov configuration/environment của lần chạy cũ chưa xác minh; license upstream của từng seed chưa được xác minh độc lập; khai báo Terraform version không chứng minh độc lập binary của mọi lần validate cũ; candidate provider-version manifest tự nó không phục hồi toàn bộ package hashes của lockfile. Theo contract đã duyệt, các giới hạn đó không làm thay đổi kết luận contextual-feature được chấp nhận.

Bộ features được khóa ở Feature Spec v1.0. Human annotation và ground-truth construction thuộc Phase 4 và phải tách khỏi model predictions/final experimental results. Closeout này không thực hiện annotation, ML training hay evaluation.
