# Feature Spec v1.0 — Phase 3 Feature Freeze

`FEATURE_SPEC_VERSION = v1.0`

Feature Freeze được thiết lập ngày 2026-10-04, sau khi bộ contextual features chính gồm 369 finding được chấp nhận về nghiên cứu và artifact đã persist vượt qua validation. Tài liệu này định danh các thành phần specification đã chấp thuận; các contract được dẫn chiếu mới là nguồn định nghĩa semantics. Chín finding-level features được khóa cho các bước annotation và evaluation tiếp theo. Mọi thay đổi sau này phải đi theo quy trình quyết định nghiên cứu, không dựa trên kết quả model.

## Phạm vi và thành phần được khóa

- Chín finding-level features: `internet_exposure`, `reachability`, `privilege_impact`, `resource_role`, `public_access`, `wildcard_action`, `wildcard_resource`, `encryption_missing`, `logging_missing`.
- Methodology: `docs/THESIS_CONTEXT.md` — SHA-256 `f43512b2d93a3abf7b17172ad4c4a1975f386488f0dd8d91449e327780b8931a`; các quyết định D-007 đến D-012 trong `docs/DECISIONS.md` — SHA-256 `b5ecbd06ea0a9fdb28f6c1b9f2fb5a527248639414e90ff2adfebc51c0e879b9`.
- Schema version `1.1`: `dataset/main/context/context_schema.yaml` — SHA-256 `49ab0378bc817df0a91c9f33349eaa3c7840dee3d7dfdb3d94364dfb4068989e`.
- Feature definitions: `dataset/main/context/feature_definitions.yaml` — SHA-256 `d5e4620329754207829f0c1d0d8fc18f59f3f1d69c60f9e1bae8da3a4e8f4bf3`.
- Applicability matrix (10 rules): `dataset/main/context/rule_context_applicability.csv` — SHA-256 `f04c781262e42407fc9b265a47fa463857f245774dbccd867fd8e3e380595b8a`.
- Evidence v1 contract `d009-v1`: `dataset/main/context/feature_evidence_contract.yaml` — SHA-256 `5ba474084de5788819ec169410c08576c9118e47521f3cedd0cb4493733fe475`.
- IAM Action capability taxonomy `d008-v1`: `dataset/main/context/iam_action_capability_taxonomy.yaml` — SHA-256 `8dfecadc19c7fc6ebb01dce7e3402967e3b60b5cf69dfa175e47dc9878561357`.
- Resource-role taxonomy `d010-v1`: `dataset/main/context/resource_role_taxonomy.yaml` — SHA-256 `23604bdbc534d94914f1245b1299cd4618a21d86ec30da0347f7462b3299e57f`.

Nhãn tổng hợp `v1.0` khác với version của schema, Evidence v1 và hai taxonomy. Bản ghi này không đổi tên hoặc định nghĩa lại bất kỳ thành phần nào.

## Dataset đã chấp nhận

- Artifact canonical: `results/main_context_features/features_v1.csv`.
- SHA-256 của artifact: `67295a1742a01a77dd35a3a817e591a6206356a963f5fe46edae6481b6ac9164`.
- SHA-256 của input được lọc deterministic: `a2b2ad2dd00d38fc7250523df53f26a76037191a58ea7560195d536242eaa60b`.
- Bản ghi validation và acceptance: `results/main_context_features/feature_validation_report.md`.

Feature Freeze này có trước human annotation. Nó không đồng nghĩa với freeze của ground truth, nhãn dataset, baseline hay ML evaluation.
