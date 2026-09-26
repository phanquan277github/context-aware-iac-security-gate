Input:
146 Checkov rules
1706 normalized findings

Selection criteria:
- security relevance
- context sensitivity
- sufficient finding count
- scenario diversity
- resource diversity
- phù hợp phạm vi đồ án cá nhân

Primary scope:
10 rules
~369 findings
5 security domains

Excluded rules:
không bị xóa khỏi raw dataset;
chỉ không thuộc primary ML experiment.

Leakage consideration:
ưu tiên rules có nhiều scenario;
sau này split theo scenario_id.
