# Examples

Example ASTRA projects demonstrating the specification format.

## iris/

A flat, single-level analysis: Iris classification with decisions for feature scaling,
model selection, test split, and random seed. Includes decision constraints
(`incompatible_with`, `requires`). The data is an output built once, whose recipe
loads it. Two universes are declared in the file: `baseline`, and `svm_focused`
as a change to it (`derived_from`). The output `model_comparison`, built once,
compares them through pinned inputs (`accuracy#baseline`, `accuracy#svm_focused`).

## iris_pipeline/

A nested, two-stage pipeline demonstrating sub-analyses. A feature extraction stage
(PCA or MLP encoder) feeds into a classification stage. The root (`iris_pipeline/`)
loads and splits the data, holds the decisions the stages share, and declares the
stages under `analyses`. Its universes drive the stages' own decisions with flat keys
(`feature_extraction.method`). Each stage declares the root as `iris` (`path: ..`)
and reads what it needs from it by address: `feature_extraction` reads
`iris.iris_data` and the decision `iris.random_seed`, and `classification` reads
`iris.split`, and also declares its sibling to read `feature_extraction.features`.
The root's `comparison` reads the classification accuracy pinned to its two
universes (`classification.accuracy#baseline`, `classification.accuracy#mlp_svm`).
