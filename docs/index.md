# ASTRA Format Specification

> **Version**: draft \
> **Status**: Active Development

## Abstract

**ASTRA** (Agentic Schema for Transparent Research Analysis) is a declarative YAML format for specifying scientific analyses. An ASTRA file describes *what* an analysis needs (inputs), *what* it should produce (outputs), and *what* choices are involved (decisions) — without prescribing *how* to execute the computation.

AI agents read the specification and generate implementations. The format captures the full decision space (the **multiverse**) so that every analytical choice is transparent, traceable, and reproducible.

```
Analysis (YAML)  ─────▶  Agent  ─────▶  Implementation  ─────▶  Results
  inputs                                   scripts/               metrics
  outputs                                  pipelines/             figures
  decisions                                                       tables
      ▲                                                              │
      └──────────────── previous analyses (as inputs) ───────────────┘

Universe (decision selections)  ─────▶  Execution Parameters
```

## Goals

1. **Declarative** — Specify what, not how. Execution is the agent's job.
2. **Self-similar** — Every node in the analysis tree has the same structure: inputs, outputs, decisions, insights, and optional sub-analyses.
3. **Transparent** — All analytical choices are documented, including alternatives not taken.
4. **Evidence-linked** — Decisions can reference literature-backed insights with verifiable quotes.
5. **Composable** — Analyses can use other analyses as inputs, enabling formal research chains.

## Non-Goals

- **Workflow execution** — ASTRA does not define execution order, scheduling, or runtime behavior. That is the domain of agents.
- **Code generation** — The specification does not contain or generate implementation code.
- **Data storage** — ASTRA references data sources but does not store data.
- **Visualization** — Rendering and display are handled by separate tools.

## Terminology

| Term | Definition |
|------|-----------|
| **Analysis** | A self-similar node with inputs, outputs, decisions, prior insights, findings, and optional sub-analyses |
| **Decision** | A choice point with multiple options (e.g., "which scaling method?") |
| **Option** | One possible choice for a decision |
| **Universe** | One complete set of decisions — one option selected per decision point |
| **Multiverse** | The space of all valid decision combinations |
| **Prior Insight** | A scientific claim backed by verifiable evidence from literature that informs decisions |
| **Finding** | A conclusion derived from the analysis outputs, framed in terms of the analysis aims |
| **Evidence** | A reference to a specific quote or location in a paper or analysis artifact |
| **Recipe** | An inline build rule on an output declaring how to produce it |
| **Constraint** | A rule between options: `incompatible_with` or `requires` |

---

## Core Specification

### File Format

ASTRA analyses are written in YAML. The top-level file is typically named `astra.yaml`.

The schema is defined in [LinkML](https://linkml.io) and generates bindings for Python, TypeScript, JSON Schema, JSON-LD, and more. See [Schema Artifacts](#schema-artifacts) for available formats.

### Minimal Example

```yaml
version: "1.0"
name: Iris Classification

inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris

outputs:
  - id: accuracy
    type: metric

decisions:
  scaling:
    label: Feature Scaling
    default: standard
    options:
      none:
        label: No Scaling
      standard:
        label: StandardScaler
```

### Full Example

```yaml
version: "1.0"
name: Iris Classification Study
description: |
  A demonstration analysis that builds a classifier for the classic
  Iris dataset, exploring different preprocessing and model choices.
authors:
  - ASTRA Examples
tags:
  - classification
  - sklearn

inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris
    description: "Fisher's classic 150-sample, 3-class dataset"

  - id: preprocessing_study
    type: analysis
    ref: analyses/scaling_comparison_2024
    description: Our previous study on scaling methods

outputs:
  - id: trained_output
    type: data
    description: Best performing classifier
    recipe:
      command: python src/train.py

  - id: accuracy
    type: metric
    description: Classification accuracy on held-out test set
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

  - id: confusion_matrix
    type: figure
    description: Confusion matrix heatmap
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

decisions:
  scaling:
    label: Feature Scaling
    rationale: Scaling affects distance-based algorithms like SVM
    default: standard
    options:
      none:
        label: No Scaling
        description: Use raw feature values
      standard:
        label: StandardScaler
        description: Z-score normalization (mean=0, std=1)
      minmax:
        label: MinMaxScaler
        description: Scale to [0, 1] range
        incompatible_with:
          - model.svm

  model:
    label: Classification Model
    rationale: Core algorithmic choice affecting accuracy and interpretability
    default: random_forest
    options:
      svm:
        label: Support Vector Machine
        description: Maximum margin classifier
        requires:
          - scaling.standard
      random_forest:
        label: Random Forest
        description: Ensemble of decision trees
      logistic:
        label: Logistic Regression
        description: Linear classifier with probabilistic output
```

---

## Analysis Schema

The `Analysis` is the root type. Every field marked *optional* can be omitted.

### Document Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | No | Analysis identifier (used as key when nested as sub-analysis) |
| `version` | `string` | No | ASTRA spec version (semver: `"1.0"`, `"1.0.0"`) |
| `name` | `string` | No | Human-readable name |
| `description` | `string` | No | Detailed description |
| `authors` | `string[]` | No | List of authors |
| `tags` | `string[]` | No | Tags for categorization |

**Version format**: `^\d+\.\d+(\.\d+)?$`

### Inputs

Each input declares a data source or a reference to another analysis.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **Yes** | Unique identifier |
| `type` | `"data"` \| `"analysis"` | **Yes** | Kind of input |
| `description` | `string` | No | What this input is |
| `source` | `string` | No | URI or path (for `type: data`) |
| `ref` | `string` | No | Reference to another ASTRA analysis (for `type: analysis`) |
| `ref_version` | `string` | No | Version of referenced analysis |
| `use_outputs` | `string[]` | No | Specific outputs to use from referenced analysis |
| `from_ref` | `string` | No | Parent input or sibling output reference (for sub-analyses) |

**ID pattern**: `^[a-z][a-z0-9_]*$` (lowercase, underscores, starts with letter)

**Input wiring in sub-analyses**: The `from_ref` field references either a parent input by ID (`from_ref: parent_input_id`) or a sibling's output (`from_ref: sibling_id.output_id`).

### Outputs

Each output declares an expected result from the analysis.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **Yes** | Unique identifier |
| `type` | `"metric"` \| `"figure"` \| `"table"` \| `"data"` \| `"report"` | **Yes** | Kind of output |
| `description` | `string` | No | What this output is |
| `from_ref` | `string` | No | Sub-analysis output that produces this (e.g., `"sub.output_id"`) |
| `when` | `string[]` | No | Conditions for when this output is active (see [Conditional Elements](#conditional-elements)) |
| `recipe` | `Recipe` | No | Inline build rule |

**Output types**:

| Type | Purpose | Example |
|------|---------|---------|
| `metric` | Numeric or categorical value | Accuracy, p-value, AUC |
| `figure` | Visualization | Confusion matrix, ROC curve |
| `table` | Structured tabular data | Feature importances |
| `data` | Processed data files | Predictions, models |
| `report` | Text/document output | Summary, conclusion |

### Recipes

A `Recipe` is an inline build rule on an output. Outputs with recipes form a DAG via their `inputs` field.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | `string` | **Yes** | Command to execute |
| `inputs` | `string[]` | No | Output IDs that must be produced first |
| `container` | `string` | No | Pre-built container image name |
| `container_build` | `ContainerBuildSpec` | No | Container image build specification (alternative to `container`) |
| `resources` | `Resources` | No | Compute requirements |

**Resources**:

| Field | Type | Description |
|-------|------|-------------|
| `cpus` | `integer` | Number of CPUs (min: 1) |
| `memory` | `string` | Memory requirement (e.g., `"8GB"`) |
| `gpus` | `integer` | Number of GPUs (min: 1) |
| `time_limit` | `string` | Wall time limit (e.g., `"2h"`) |

**Container build spec**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `build` | `string` | **Yes** | Path to Containerfile |
| `context` | `string` | No | Build context directory |
| `args` | `KeyValuePair[]` | No | Build arguments |

A node-level `container` (or `container_build`) field on the Analysis sets the default container for all recipes in that node. Individual recipes can override it.

### Decisions

Decisions are the core of the multiverse. Each decision is a named choice point with multiple options.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | `string` | **Yes** | Human-readable name |
| `rationale` | `string` | No | Why this decision exists |
| `tags` | `string[]` | No | Grouping/categorization tags |
| `when` | `string[]` | No | Conditions for when this decision is active (see [Conditional Elements](#conditional-elements)) |
| `default` | `string` | No | Default option ID for baseline universes |
| `options` | `map[string, Option]` | **Yes** | Available choices |
| `from_ref` | `string` | No | Reference to a parent decision (see [Decision References](#decision-references)) |

A decision with `from_ref` set is a pure reference — it must not have `label`, `options`, or `default`.

### Options

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | `string` | **Yes** | Human-readable name |
| `description` | `string` | No | Detailed description |
| `insights` | `string[]` | No | Insight IDs supporting this choice |
| `incompatible_with` | `string[]` | No | Options that conflict (format: `"decision.option"`) |
| `requires` | `string[]` | No | Options that must coexist (format: `"decision.option"`) |
| `excluded` | `boolean` | No | Whether this option was considered and rejected (default: `false`) |
| `excluded_reason` | `string` | No | Why this option was excluded |

**Constraint reference format**: `"decision_id.option_id"` — constraints are scoped within the same analysis node.

### Sub-Analyses

The `analyses` field contains a map of sub-analysis IDs to nested `Analysis` objects. Each sub-analysis has the exact same structure as the root — the format is fully self-similar.

```yaml
analyses:
  feature_extraction:
    description: Learn a compact representation of the raw features
    inputs:
      - id: raw_features
        type: data
        from_ref: iris_data               # Parent input
    outputs:
      - id: features
        type: data
        recipe:
          command: python src/extract_features.py
    decisions:
      seed:
        from_ref: ../random_seed           # Parent decision reference

      method:
        label: Extraction Method
        default: pca
        options:
          pca:
            label: PCA
          mlp_encoder:
            label: MLP Encoder

  classification:
    description: Train a classifier on extracted features
    inputs:
      - id: features
        type: data
        from_ref: feature_extraction.features  # Sibling output
    outputs:
      - id: accuracy
        type: metric
        recipe:
          command: python src/evaluate.py
          resources:
            gpus: 1
            memory: "32GB"
    decisions:
      classifier:
        label: Classifier
        default: logistic
        options:
          logistic:
            label: Logistic Regression
          svm:
            label: SVM (RBF)
```

---

## Universe Schema

A **universe** is one complete set of decisions — one option selected per decision point. It mirrors the analysis tree structure, using a compact dict format where each key is a decision ID and each value is the selected option ID.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **Yes** | Unique identifier |
| `description` | `string` | No | What this universe represents |
| `decisions` | `map[string, string]` | No | Decision ID → selected option ID (root level) |
| `analyses` | `map[string, UniverseNode]` | No | Sub-analysis selections |

**Universe ID pattern**: `^[a-z][a-z0-9_-]*$` (also allows hyphens)

A `UniverseNode` has the same shape: `decisions` and `analyses`, recursively mirroring the analysis tree.

### Flat Universe

```yaml
id: baseline
description: Default configuration using standard practices

decisions:
  scaling: standard
  model: random_forest
  test_size: small
  random_seed: seed_42
```

### Nested Universe

```yaml
id: baseline
description: PCA with logistic regression — the simplest sensible pipeline

decisions:
  test_split: twenty_pct
  random_seed: seed_42

analyses:
  feature_extraction:
    decisions:
      method: pca
      n_components: two
  classification:
    decisions:
      classifier: logistic
```

---

## Prior Insights and Findings

ASTRA distinguishes two kinds of knowledge, both using the same `Insight` model:

- **Prior insights** (`prior_insights:`) — knowledge from literature or prior artifacts that informs decisions.
- **Findings** (`findings:`) — conclusions derived from running the analysis, backed by output artifacts.

Both use `evidence` to ground the claim. The placement determines direction; the model is the same.

### Insight (shared model)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **Yes** | Unique identifier |
| `claim` | `string` | **Yes** | What we learned (1-2 sentences) |
| `created_at` | `datetime` | **Yes** | ISO 8601 timestamp |
| `evidence` | `Evidence[]` | **Yes** | Supporting evidence (at least one) |
| `derived` | `boolean` | No | Whether synthesized/inferred (default: `false`) |
| `scope` | `string` | No | Applicability conditions |
| `tags` | `string[]` | No | Categorization tags |
| `notes` | `string` | No | Reasoning notes |

### Evidence

Each evidence item references either a paper (by DOI) or an analysis output artifact (by output ID). Exactly one source type must be set. Literature evidence requires a text quote for verifiability.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **Yes** | Evidence ID |
| `doi` | `string` | **Exactly one of `doi` or `artifact`** | DOI of source paper |
| `artifact` | `string` | **Exactly one of `doi` or `artifact`** | Output ID of a declared analysis output |
| `version` | `integer` | No | Paper version (arXiv; literature only) |
| `snapshot` | `string` | No | Path to immutable artifact copy (artifact only) |
| `source_commit` | `string` | No | Git commit that produced artifact (artifact only) |
| `quote` | `TextQuoteSelector` | No | Text quote anchor |
| `location` | `FragmentSelector` | No | Location hint (page number) |

**DOI pattern**: `^10\.\d{4,}/.*$`

### W3C Selectors

Evidence uses [W3C Web Annotation](https://www.w3.org/TR/annotation-model/) compliant selectors for precise references.

**TextQuoteSelector** — Locates a text passage in a document:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `exact` | `string` | **Yes** | Exact quoted text (1-3 sentences) |
| `prefix` | `string` | No | ~20-100 chars before the quote |
| `suffix` | `string` | No | ~20-100 chars after the quote |

**FragmentSelector** — PDF location hint:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | `string` | No | Fragment (e.g., `"page=6"`) |
| `page` | `integer` | No | 1-indexed page number |

### Example

```yaml
prior_insights:
  compute_scaling:
    id: compute_scaling
    claim: >-
      Neural networks achieve state-of-the-art photo-z performance
      on LSST-like photometry.
    created_at: "2025-06-15T10:30:00Z"
    evidence:
      - id: ev_nn_paper
        doi: "10.48550/arXiv.2301.12345"
        version: 2
        quote:
          exact: >-
            FlexZBoost achieves a normalized median absolute deviation
            of 0.018 on the test set.
          prefix: "Results section."
        location:
          value: page=8
          page: 8
    scope: "LSST-like photometry with neural networks"
    tags: [machine-learning]

findings:
  pipeline_result:
    id: pipeline_result
    claim: The pipeline achieves target bias with the neural network method.
    created_at: "2025-08-20T16:45:00Z"
    evidence:
      - id: ev_bias_artifact
        artifact: bias_metric
        quote:
          exact: "bias = 0.0021 +/- 0.0003"
    derived: true

decisions:
  method:
    label: Redshift estimation method
    options:
      neural_net:
        label: Neural network
        insights:
          - compute_scaling        # Links decision to prior insight
```

The chain **decision option** → **prior insight** → **evidence** → **paper (DOI)** provides end-to-end traceability from analytical choice to published literature. The chain **finding** → **evidence** → **output artifact** captures what was learned from running the analysis.

---

## Constraints

Options can declare two kinds of constraints, scoped within the same analysis node:

### `incompatible_with`

Options that cannot coexist in the same universe:

```yaml
decisions:
  scaling:
    options:
      minmax:
        label: MinMaxScaler
        incompatible_with:
          - model.svm          # MinMax and SVM cannot be selected together
```

### `requires`

Options that must coexist in the same universe:

```yaml
decisions:
  model:
    options:
      svm:
        label: SVM
        requires:
          - scaling.standard   # SVM requires standard scaling
```

Constraint references use the format `decision_id.option_id`. Universe validation rejects any selection that violates these constraints.

---

## Composability

Analyses can reference other analyses as inputs, enabling formal research chains:

```yaml
inputs:
  - id: prior_study
    type: analysis
    ref: analyses/preprocessing_comparison
    ref_version: "v1.2"
    use_outputs: [best_method, performance_table]
```

Within a nested analysis, sub-analyses wire inputs from the parent or from siblings using `from_ref`:

```yaml
analyses:
  stage_a:
    inputs:
      - id: raw
        type: data
        from_ref: survey_catalog          # Parent input
    outputs:
      - id: processed
        type: data

  stage_b:
    inputs:
      - id: data
        type: data
        from_ref: stage_a.processed       # Sibling output
```

---

## Conditional Elements

The `when` field makes decisions or outputs conditional. It accepts a list of conditions in the format `decision_id.option_id` or `~decision_id.option_id` (negated). Multiple conditions are AND'd together.

### Conditional Decisions

A decision that only exists when a specific option is selected elsewhere:

```yaml
decisions:
  model:
    label: Model
    options:
      neural_net:
        label: Neural Network
      svm:
        label: SVM

  optimizer:
    label: Optimizer
    when:
      - model.neural_net      # Only exists when neural_net is selected
    options:
      adam:
        label: Adam
      sgd:
        label: SGD
```

### Conditional Outputs

An output that is only produced under certain decision selections:

```yaml
outputs:
  - id: scatter_plot
    type: figure
    description: Photo-z scatter plot
    when:
      - method.neural_net     # Only produced for neural net runs
    recipe:
      command: python src/plot_scatter.py
```

### Negation

Prefix a condition with `~` to negate it:

```yaml
decisions:
  fallback_method:
    label: Fallback Method
    when:
      - ~model.neural_net     # Only active when neural_net is NOT selected
    options:
      interpolation:
        label: Linear Interpolation
```

---

## Decision References

Sub-analyses can reference a parent decision using the `from_ref` field with a `../` prefix. This avoids duplicating the decision definition and ensures the sub-analysis uses the same selection as the parent:

```yaml
decisions:
  random_seed:
    label: Random Seed
    default: seed_42
    options:
      seed_42:
        label: "42"
      seed_7:
        label: "7"

analyses:
  feature_extraction:
    decisions:
      seed:
        from_ref: ../random_seed    # Uses parent's random_seed decision
      method:
        label: Extraction Method
        default: pca
        options:
          pca:
            label: PCA
```

A decision with `from_ref` set is a pure reference — it must not define `label`, `options`, or `default`.

---

## External Sub-Analyses

A sub-analysis can be defined externally by specifying a `path` to a directory containing its own `astra.yaml`:

```yaml
analyses:
  preprocessing:
    path: stages/preprocessing    # Directory with its own astra.yaml
```

The `path` field is mutually exclusive with inline content fields (`inputs`, `outputs`, `decisions`, etc.). This allows large analyses to be split across multiple files while remaining composable.

---

## Excluded Options

Options can be marked as considered-and-rejected, preserving the decision history:

```yaml
options:
  knn:
    label: K-nearest Neighbors
    excluded: true
    excluded_reason: Poor performance on high-dimensional data
```

Excluded options are kept in the specification for transparency but are not valid selections in any universe.

---

## Validation

ASTRA provides two-stage validation:

### Stage 1: Schema Validation

Checks that the YAML file conforms to the JSON schema — correct structure, types, required fields, and format patterns.

### Stage 2: Semantic Validation

Checks logical correctness:

- No duplicate IDs within a node
- Default options exist in their decision's option map
- Constraint references (`incompatible_with`, `requires`) resolve to valid `decision.option` pairs
- Input `from_ref` references resolve to parent inputs or sibling outputs
- Output `from_ref` references resolve to sub-analysis outputs
- Recipe input dependencies reference valid output IDs
- Universe selections match analysis decisions
- Universe selections respect all constraints

### Evidence Verification

Optionally, evidence quotes can be verified against source PDFs:

```bash
astra validate astra.yaml --verify-evidence
```

This downloads papers by DOI, extracts text from PDFs, and uses fuzzy matching to locate quoted text. Fabricated quotes fail verification.

---

## ID Conventions

| Context | Pattern | Example |
|---------|---------|---------|
| Input, output, decision, sub-analysis IDs | `^[a-z][a-z0-9_]*$` | `iris_data`, `scaling` |
| Universe IDs | `^[a-z][a-z0-9_-]*$` | `baseline`, `svm-focused` |
| Constraint references | `decision_id.option_id` | `scaling.standard` |
| Decision references | `../decision_id` | `../random_seed` |
| Version | `^\d+\.\d+(\.\d+)?$` | `"1.0"`, `"1.0.0"` |
| DOI | `^10\.\d{4,}/.*$` | `"10.48550/arXiv.1706.03762"` |

---

## Schema Artifacts

ASTRA is defined in [LinkML](https://linkml.io). The source schema files live in `src/astra/schema/` and generate bindings for multiple formats:

| Format | Description |
|--------|-------------|
| [LinkML YAML](schema/astra.yaml) | Source schema definition |
| [JSON Schema](schema/astra.schema.json) | For YAML validation |
| [JSON-LD Context](schema/astra.context.jsonld) | For linked data interoperability |

Python datamodels are generated from the LinkML schema and are available via `pip install astra-spec`. See the [auto-generated schema reference](elements/index.md) for detailed class and field documentation.

### Source Schema Files

| File | Exports | Description |
|------|---------|-------------|
| `analysis.yaml` | `Analysis`, `Input`, `Output`, `Decision`, `Option`, `Recipe`, `Resources`, `ContainerBuildSpec` | Core analysis specification |
| `universe.yaml` | `Universe`, `UniverseNode`, `DecisionSelection` | Universe (decision selections) |
| `insight.yaml` | `Insight`, `Evidence`, `InsightCollection`, `TextQuoteSelector`, `FragmentSelector` | Insights, evidence, and W3C selectors |
