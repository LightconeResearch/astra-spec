# Examples

Example ASTRA projects demonstrating the specification format.

Both examples name a `workflow_engine` and give each output a `workflow_target`.
The stage definitions those targets refer to — command, environment, dependencies —
would live in the engine's own file (a `Snakefile`, here) alongside
`astra.yaml`; these examples ship the ASTRA document only.

## iris/

A flat, single-level analysis: Iris classification with decisions for feature scaling,
model selection, test split, and random seed. Includes decision constraints
(`incompatible_with`, `requires`). Several outputs share a single `evaluate` rule,
which is the normal case when one script emits multiple artifacts.

## iris_pipeline/

A nested, two-stage pipeline demonstrating sub-analyses. A feature extraction stage
(PCA or MLP encoder) feeds into a classification stage. Shows input wiring between
parent and sibling analyses via `from: ../...`, decision aliasing from a parent via
`from: ../parent_decision`, and parent-level Output re-exports via `from: child.out_id`.
A single `workflow_engine: snakemake` at the root is inherited by both sub-analyses.
