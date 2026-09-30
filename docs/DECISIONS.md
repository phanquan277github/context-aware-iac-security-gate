# Research and Implementation Decisions

This file records accepted decisions that affect implementation.

This file does not replace the full research specification in
`docs/THESIS_CONTEXT.md`.

---

## D-001 — Authoritative Research Specification

Status: Accepted

Decision:

`docs/THESIS_CONTEXT.md` is the primary source of truth for the
current research design and methodology.

Older research protocol documents remain historical/supporting
references.

If they conflict with THESIS_CONTEXT.md, the latter takes
precedence.

---

## D-002 — Research Design vs Existing Code

Status: Accepted

Decision:

Existing implementation does not automatically define the research
methodology.

If implementation conflicts with the approved research design,
the conflict must be reported.

The methodology must not be silently changed simply to preserve
existing code behavior.

---

## D-003 — Applicability Is Not Unknown

Status: Accepted

Decision:

A contextual feature that is not applicable to a finding/rule is
semantically different from an unknown feature value.

Non-applicable:
the feature does not belong to the semantics of that rule/finding.

Unknown:
the feature is applicable, but its value cannot be reliably
determined from available evidence.

These states must not be collapsed.

---

## D-004 — Context Evidence

Status: Accepted

Decision:

Contextual feature extraction should retain sufficient evidence to
trace important extracted values back to the Terraform source.

No fabricated evidence or silent default evidence is permitted.

---

## D-005 — Research Integrity

Status: Accepted

Implementation must not introduce undocumented heuristics simply
to improve downstream metrics.

In particular, avoid:

- target leakage
- data leakage
- silent fallback labels
- fabricated context
- evaluation contamination
- methodology changes made only to make tests pass

---

## D-006 — Current Phase Boundary

Status: Accepted

Do not advance to final ML training/evaluation until the
finding-level contextual feature dataset and semantic validation
are considered stable.
