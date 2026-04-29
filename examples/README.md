# Examples

Example ASTRA projects demonstrating the specification format.

## iris/

A flat, single-level analysis: Iris classification with decisions for feature scaling,
model selection, test split, and random seed. Includes decision constraints
(`incompatible_with`, `requires`).

## iris_pipeline/

A nested, two-stage pipeline demonstrating sub-analyses. A feature extraction stage
(PCA or MLP encoder) feeds into a classification stage. Shows input wiring between
parent and sibling analyses via `from: ../...`, decision aliasing from a parent via
`from: ../parent_decision`, and parent-level Output re-exports via `from: child.out_id`.
