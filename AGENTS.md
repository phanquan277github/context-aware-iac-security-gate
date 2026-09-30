# AGENTS.md

## Project

This repository implements the research project:

"Context-Aware Machine Learning for Security Risk Prioritization
of Generative AI-Generated Terraform"

This is research software for an academic thesis, not a generic
software engineering project.

---

## Source of Truth

The primary and authoritative research specification is:

`docs/THESIS_CONTEXT.md`

This document contains the current approved research design,
methodology, experimental design, dataset design, implementation
design, evaluation plan, and project plan.

When implementation details conflict with older documents,
scripts, comments, experimental notes, or previous protocol
versions, follow `docs/THESIS_CONTEXT.md`.

Older documents such as:

`docs/research_protocol_amendment_v2.2.md`

are historical/supporting references unless explicitly preserved
by the authoritative research specification.

Do NOT silently change the research methodology to fit the
existing implementation.

---

## Research Context Hierarchy

Use the following hierarchy when interpreting this repository:

1. `docs/THESIS_CONTEXT.md`
   - authoritative research design and methodology

2. `docs/DECISIONS.md`
   - accepted research and implementation decisions

3. `docs/CURRENT_STATE.md`
   - current implementation checkpoint

4. `PROJECT_RULES.md`
   - stable project constraints and engineering rules

5. Existing code, outputs, and historical documents
   - implementation evidence and historical context

Existing code does NOT automatically define the methodology.

If lower-priority evidence conflicts with a higher-priority source,
report the conflict instead of silently resolving it.

## Research vs Implementation

The research design is controlled outside Codex.

Codex is primarily responsible for:

- inspecting the repository
- implementing approved specifications
- fixing implementation defects
- running pipelines
- validating outputs
- writing tests
- maintaining implementation documentation

Codex must NOT independently redefine:

- research questions
- ground-truth semantics
- applicability semantics
- feature definitions
- labeling strategy
- dataset inclusion/exclusion policy
- train/test splitting policy
- evaluation metrics
- experimental protocol

If implementation requires changing one of these,
STOP and explain the conflict instead of making the decision.

---

## Research Integrity

Do not modify methodology merely to make tests pass or improve
experimental metrics.

Do not introduce:

- data leakage
- target leakage
- duplicate samples across evaluation boundaries
- undocumented heuristics
- hidden assumptions
- silent fallback labels
- fabricated context/evidence

Missing or non-applicable information must follow the semantics
defined by the research specification.

---

## Current Project State

For the current implementation status, read:

docs/CURRENT_STATE.md

For important research/implementation decisions, read:

docs/DECISIONS.md

Only read additional documents when they are relevant to the
current task.

---

## Working Rules

Before modifying code:

1. Inspect the relevant implementation.
2. Identify the specification governing the change.
3. Check whether the proposed change is implementation-only or
   changes research semantics.

For implementation-only changes:
- make the smallest appropriate change
- preserve existing research semantics
- run relevant validation/tests
- inspect generated outputs

For research-semantic changes:
- do not implement automatically
- report the issue and ask for a research decision

---

## Validation

After implementation changes:

- run the relevant script or pipeline
- run available tests
- inspect output schema
- check row counts when relevant
- check null / unknown / non-applicable values
- check validation errors
- report unexpected changes

Do not claim a task is complete only because the program exits
successfully.

---

## Scope

Keep changes scoped to the requested task.

Do not perform unrelated refactoring unless it is necessary for
correctness.

Do not rewrite working research code merely for stylistic
preferences.

---

## Communication Language

All user-facing Codex responses for this repository must be written
in Vietnamese unless the user explicitly requests another language.

This includes:

- repository audits
- implementation plans
- explanations
- validation reports
- conflict reports
- implementation summaries
- next-step recommendations

Keep the following in their original form when appropriate:

- source code
- variable/function/class names
- file and directory paths
- shell commands
- configuration keys
- literal program output
- literal error messages

Technical English terms may be retained when translating them would
reduce precision, but explanations around them should be in Vietnamese.

Do not translate source-code identifiers merely for presentation.

