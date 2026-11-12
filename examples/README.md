# Examples

Example ASTRA projects demonstrating the specification format.

## iris/

A single analysis: Iris classification with decisions for feature scaling, model
selection, test split and random seed, and the constraints between them
(`requires`, `incompatible_with`). The data is an output built once, whose recipe
loads it. Two universes are declared in the file: `baseline`, and `svm_focused`
as a change to it (`derived_from`). The output `model_comparison`, built once,
compares them through pinned inputs (`accuracy#baseline`, `accuracy#svm_focused`).

## iris_pipeline/

A two-stage pipeline in three analyses. The root (`iris_pipeline/`) loads and splits
the data, holds the decisions the stages share, and declares the stages under
`analyses`. Its universes drive the stages' own decisions with flat keys
(`feature_extraction.method`). Each stage declares the root as `iris` (`path: ..`)
and reads what it needs from it by address: `feature_extraction` reads
`iris.iris_data` and the decision `iris.random_seed`, and `classification` reads
`iris.split`, and also declares its sibling to read `feature_extraction.features`.
The root's `comparison` reads the classification accuracy pinned to its two
universes (`classification.accuracy#baseline`, `classification.accuracy#mlp_svm`).
