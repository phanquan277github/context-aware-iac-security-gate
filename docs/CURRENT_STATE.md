# Current Project State

Cập nhật: 2026-10-04

Đây là checkpoint implementation hiện tại. Methodology có thẩm quyền nằm trong `docs/THESIS_CONTEXT.md`; các quyết định đã chấp thuận nằm trong `docs/DECISIONS.md`.

## Giai đoạn nghiên cứu hiện tại

Phase 3 — Context & Feature Engineering đã hoàn thành. Main finding-level contextual-feature dataset đã persist và được research-accepted. Phase-3 feature validation đã hoàn tất; `FEATURE_SPEC_VERSION = v1.0` được khóa tại `docs/feature_spec_v1.md`. Giai đoạn kế tiếp là Phase 4 — Ground Truth & Benchmark Construction; closeout này chưa bắt đầu annotation.

## Main feature dataset đã chấp nhận

- Artifact canonical: `results/main_context_features/features_v1.csv`.
- SHA-256: `67295a1742a01a77dd35a3a817e591a6206356a963f5fe46edae6481b6ac9164`.
- SHA-256 của source/input đã lọc: `a2b2ad2dd00d38fc7250523df53f26a76037191a58ea7560195d536242eaa60b`.
- 369 unique findings, 10 research-scope rules, 81 candidates, 9 resource types, 9 contextual features.
- 3.321 feature cells: 1.031 applicable, 2.290 `not_applicable`, 216 `unknown`.
- Semantic-evidence acceptance độc lập: 369 `AUTOMATED_VERIFIED`, 662 `MANUAL_VERIFIED`, 0 `INSUFFICIENT_EVIDENCE`, 0 `SEMANTIC_CONFLICT`, 0 `EXTRACTION_FAILURE`.
- General validator và Evidence v1 validator trên artifact đã persist đều PASS với 0 lỗi, 0 cảnh báo; schema validator PASS; full regression suite 180/180 PASS.
- Validation record: `results/main_context_features/feature_validation_report.md`.

Feature semantics và applicability tiếp tục do D-007–D-012 cùng schema, feature definitions, Evidence v1 `d009-v1`, IAM Action taxonomy `d008-v1` và resource-role taxonomy `d010-v1` quy định. Evidence từ Terraform tĩnh/scanner được duyệt không khẳng định trạng thái runtime đã triển khai.

## Pilot checkpoint đã chấp nhận

Saved pilot 20 findings vẫn là Evidence v1 `d009-v1` tại `results/context_feature_pilot/finding_context_features_pilot.csv`, SHA-256 `7c88f02ad28648e8ff434ebc5cfe59f35be67781cbca8d53225076e332278cc8`. Closeout này không sửa pilot.

## Ranh giới giai đoạn tiếp theo

Phase 4 có thể bắt đầu với human annotation và benchmark construction theo research protocol được duyệt. Human annotation phải diễn ra sau Feature Freeze và không được dựa trên model predictions hoặc final experimental results. Chưa train/evaluate ML trước khi các gate về ground truth và experiment được đáp ứng. Historical raw Checkov JSON archive và independent upstream license verification vẫn là các giới hạn provenance được ghi trong `docs/dataset_source_provenance.md`.
