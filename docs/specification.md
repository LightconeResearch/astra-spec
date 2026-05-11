# The ASTRA Specification Explained

> **Version**: draft  
> **Status**: active development

The formal ASTRA schema is the source of truth, but a schema is not the easiest place to learn the format. This page is a soft landing for readers who want to understand what an `astra.yaml` file means before looking at the generated LinkML reference. It introduces the main building blocks, shows a minimal document, grows that document piece by piece, and ends with a compact field reference.

ASTRA documents are written for two audiences at the same time. Humans should be able to inspect the file and understand the scientific design of the analysis. Tools and AI agents should be able to parse the same file and know which inputs, outputs, decisions, options, constraints, and evidence links they are allowed to rely on.

## What an ASTRA document describes

An ASTRA document describes a scientific analysis, not merely a program. A program says what to execute. An ASTRA analysis says what the computation is meant to establish, which artifacts matter, which choices shape those artifacts, and how a reader can trace claims back to evidence.

The central object is an **Analysis**. A typical analysis is stored in `astra.yaml` and declares:

| Section | Question it answers |
|---|---|
| `narrative` | How should a scientist understand the purpose, methods, inputs, outputs, and findings? |
| `inputs` | What data or prior analyses does this analysis consume? |
| `outputs` | What metrics, figures, tables, data products, or reports does it produce? |
| `decisions` | Which methodological choice points shape the outputs? |
| `prior_insights` | Which existing claims or sources inform the analysis? |
| `findings` | What claims does this analysis make after its outputs are produced? |
| `analyses` | Which nested sub-analyses make up a larger analysis tree? |

The point of the structure is to make the analysis reviewable. A reader can start at a figure or metric, follow it to the decisions that parameterized it, inspect the options that were available, and then descend to the recipe or evidence when more detail is needed.

## Syntax

ASTRA analyses are written in YAML. The entry document is conventionally named `astra.yaml`.

YAML represents mappings, lists, strings, numbers, booleans, and nested objects. Indentation matters. Field names are case-sensitive, so `decisions` and `Decisions` are different fields. Comments begin with `#` and are ignored by parsers.

```yaml
# A mapping from field names to values
name: Example Analysis
version: "1.0"

# A list of objects
inputs:
  - id: raw_data
    type: data
    source: data/raw.csv
```

Most examples in this guide use ellipses (`...`) to indicate omitted content. Ellipses are not part of the ASTRA format.

## Minimal ASTRA document

A minimal useful ASTRA document names the analysis, declares at least one input, declares at least one output, and declares the decisions that affect that output.

```yaml
version: "1.0"
name: Iris Classification

narrative:
  summary: |
    Train a classifier for the Iris dataset.
  methods: |
    The [model](#decisions.model) decision selects the classifier.
  inputs: |
    The [iris_data](#inputs.iris_data) input provides the dataset.
  outputs: |
    The [accuracy](#outputs.accuracy) output reports held-out performance.

inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris
    description: Fisher's classic 150-sample, 3-class dataset.

outputs:
  - id: accuracy
    type: metric
    description: Classification accuracy on a held-out test set.
    inputs: [iris_data]
    decisions: [model]
    recipe:
      command: >-
        python src/evaluate.py
        --data {inputs.iris_data}
        --model {decisions.model}
        --out {output}

decisions:
  model:
    label: Classification model
    rationale: The algorithm determines the hypothesis class being tested.
    default: random_forest
    options:
      random_forest:
        label: Random forest
      svm:
        label: Support vector machine
```

This example is small, but it already shows the ASTRA contract. The `accuracy` output is not just a name. It declares that it depends on `iris_data`, that it is parameterized by `model`, and that the recipe may only refer to the declared input and declared decision. The validator can therefore reject a command that silently uses an undeclared decision.

## Reading the example from top to bottom

### Metadata

```yaml
version: "1.0"
name: Iris Classification
```

The `version` field records the ASTRA schema version the document expects. The `name` field gives the analysis a human-readable title. Real projects usually also include `id`, `authors`, `tags`, and sometimes a node-level `container` used as the default execution environment for recipes.

### Narrative

```yaml
narrative:
  summary: |
    Train a classifier for the Iris dataset.
  methods: |
    The [model](#decisions.model) decision selects the classifier.
  inputs: |
    The [iris_data](#inputs.iris_data) input provides the dataset.
  outputs: |
    The [accuracy](#outputs.accuracy) output reports held-out performance.
```

The `narrative` block is prose with stable anchors. It gives the analysis-level explanation that a paper, report, or review tool can render. The structured fields below it provide the machine-readable record. The two should agree: the prose tells the story, and the structured objects give tools something precise to validate.

ASTRA defines five narrative sections: `summary`, `findings`, `methods`, `inputs`, and `outputs`. They are optional in the raw schema, but `astra validate` conditionally requires prose when the corresponding structured data exists. If an analysis declares `inputs`, it should explain them in `narrative.inputs`; if it declares `outputs`, it should explain them in `narrative.outputs`; if it declares `decisions` or nested `analyses`, it should explain them in `narrative.methods`; if it declares structured `findings`, it should explain them in `narrative.findings`.

### Inputs

```yaml
inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris
    description: Fisher's classic 150-sample, 3-class dataset.
```

An input is something the analysis consumes. It can be a dataset, a file, an external resource, or the outputs of another ASTRA analysis. The `id` is the local name used by outputs and recipes. The `type` says whether the input is raw `data` or an external `analysis`. The `source` field usually points to a path, URI, loader name, or other data locator.

Inputs are intentionally descriptive rather than prescriptive. ASTRA does not store the data. It records enough information for humans and tools to know what the analysis claims to consume.

### Outputs

```yaml
outputs:
  - id: accuracy
    type: metric
    description: Classification accuracy on a held-out test set.
    inputs: [iris_data]
    decisions: [model]
    recipe:
      command: >-
        python src/evaluate.py
        --data {inputs.iris_data}
        --model {decisions.model}
        --out {output}
```

An output is a scientific artifact the analysis produces: a metric, figure, table, data product, or report. The important design choice is that provenance lives on the output. `inputs` names the upstream artifacts required to produce it. `decisions` names the methodological choices that parameterize it. `recipe` gives a command a runner can invoke, but the recipe is not allowed to invent hidden dependencies.

This makes the output a reviewable unit. A reader can ask, “What would have to change for this number to change?” and the ASTRA file points to the input data and decision values that matter.

### Decisions

```yaml
decisions:
  model:
    label: Classification model
    rationale: The algorithm determines the hypothesis class being tested.
    default: random_forest
    options:
      random_forest:
        label: Random forest
      svm:
        label: Support vector machine
```

A decision is a named methodological choice point. Each decision contains options. The decision says what has to be chosen; the options say what could be chosen.

Decisions are the core of ASTRA because scientific analyses are rarely defined by code alone. They are defined by defensible choices: which sample cut, which model, which prior, which coordinate transform, which null hypothesis, which feature engineering step. ASTRA gives those choices first-class names so they can be reviewed, constrained, varied, and attached to outputs.

## Building up the specification

The minimal document above is enough to explain the basic shape. The rest of the specification adds structure that becomes important in real analyses: multiple choices, constraints between options, conditional outputs, evidence-backed claims, and nested sub-analyses.

### Options

Options live inside decisions. An option can have a label, description, notes, constraints, linked insights, and exclusion metadata.

```yaml
decisions:
  scaling:
    label: Feature scaling
    rationale: Scaling affects distance-based algorithms.
    default: standard
    options:
      none:
        label: No scaling
        description: Use raw feature values.
      standard:
        label: StandardScaler
        description: Z-score normalize each feature.
      minmax:
        label: MinMaxScaler
        description: Scale each feature to [0, 1].
```

The `default` option is the baseline selection used by tools that generate a default universe. Defaults should be boring and defensible, not necessarily optimal.

### Constraints between options

Some option combinations are invalid. ASTRA supports two local constraint types: `requires` and `incompatible_with`. Constraint references use `decision_id.option_id`.

```yaml
decisions:
  scaling:
    label: Feature scaling
    default: standard
    options:
      none:
        label: No scaling
      standard:
        label: StandardScaler

  model:
    label: Classification model
    default: random_forest
    options:
      random_forest:
        label: Random forest
      svm:
        label: Support vector machine
        requires:
          - scaling.standard
```

Here, selecting `model.svm` requires `scaling.standard`. A universe that selects `model: svm` and `scaling: none` is invalid. This matters because the multiverse of possible analyses is not the raw Cartesian product of every option. It is the set of combinations that survive the declared constraints.

### Excluded options

A rejected option can still be scientifically important. ASTRA lets authors keep it in the record while marking it as unavailable for valid universes.

```yaml
options:
  knn:
    label: k-nearest neighbors
    excluded: true
    excluded_reason: Poor performance on high-dimensional pilot data.
```

This is useful during review. A reader can see not only what was chosen, but what was considered and why it was rejected.

### Universes

A universe is one complete selection of decision options. If the analysis defines `scaling` and `model`, then a universe chooses one option for `scaling` and one option for `model`.

```yaml
id: baseline
description: Default configuration

decisions:
  scaling: standard
  model: random_forest
```

One analysis can have many universes. A baseline universe might use conventional defaults. A robustness universe might select a different estimator. A stress-test universe might use a more restrictive data cut. Each universe yields one set of outputs under one declared choice configuration.

For nested analyses, the universe mirrors the analysis tree:

```yaml
id: baseline

decisions:
  test_split: twenty_pct

analyses:
  feature_extraction:
    decisions:
      method: pca
      n_components: two
  classification:
    decisions:
      classifier: logistic
```

### Recipes and command templates

A recipe is an inline build rule attached to an output. It describes how to produce that output once a runner has materialized inputs and selected decision values.

```yaml
outputs:
  - id: predictions
    type: data
    inputs: [training_data, features]
    decisions: [classifier, seed]
    recipe:
      command: >-
        python src/classify.py
        --train {inputs.training_data}
        --features {inputs.features}
        --classifier {decisions.classifier}
        --seed {decisions.seed}
        --out {output}
      container: ghcr.io/lightcone/sklearn:latest
      resources:
        cpus: 4
        memory: "8Gi"
        time_limit: "30m"
```

The key rule is that every placeholder must be declared on the parent output. `{inputs.training_data}` is legal only because `training_data` appears in `Output.inputs`. `{decisions.classifier}` is legal only because `classifier` appears in `Output.decisions`. The validator rejects undeclared template references.

Recipes are intentionally thin. ASTRA does not define scheduling, caching, retries, cluster submission, or path layout. Those are runner responsibilities. ASTRA defines the provenance contract that a runner must respect.

### Conditional elements

The `when` field makes an output or decision active only under certain selections. Conditions use `decision.option`; prefix with `~` for negation. Multiple conditions are ANDed together.

```yaml
decisions:
  model:
    label: Model
    default: neural_net
    options:
      neural_net: { label: Neural network }
      svm: { label: Support vector machine }

  optimizer:
    label: Optimizer
    when:
      - model.neural_net
    default: adam
    options:
      adam: { label: Adam }
      sgd: { label: SGD }

outputs:
  - id: training_curve
    type: figure
    when:
      - model.neural_net
    recipe:
      command: python src/plot_training_curve.py --out {output}
```

Conditional structure keeps the record honest when some parts of an analysis only exist for particular methods. A neural-network optimizer should not be forced into an SVM universe.

### Prior insights, findings, and evidence

ASTRA separates two kinds of scientific claims. A `prior_insight` is a claim imported from previous literature or earlier work and used to justify choices. A `finding` is a claim produced by the current analysis. Both use the shared `Insight` model and can point to evidence.

```yaml
prior_insights:
  scaling_matters:
    claim: Distance-based classifiers are sensitive to feature scale.
    created_at: "2026-05-11T00:00:00Z"
    evidence:
      - id: ev_scaling_reference
        doi: "10.48550/arXiv.1706.03762"
        quote:
          exact: "Distance-based classifiers are sensitive to feature scale."

decisions:
  scaling:
    label: Feature scaling
    rationale: Scaling affects distance-based algorithms.
    options:
      standard:
        label: StandardScaler
        insights: [scaling_matters]

findings:
  svm_result:
    claim: The SVM universe achieved the highest held-out accuracy.
    created_at: "2026-05-11T00:00:00Z"
    evidence:
      - id: ev_accuracy_table
        artifact: accuracy
        quote:
          exact: "svm accuracy = 0.97"
    derived: true
```

Evidence may point to text in a paper, a fragment of a source document, or an artifact produced by the analysis. The intended chain is inspectable: decision option → insight → evidence → source, or finding → evidence → output artifact. With evidence verification enabled, tools can check whether quoted text actually appears in the cited source.

### Sub-analyses

Large analyses are naturally hierarchical. A simulation may feed a calibration stage, which feeds a summary plot. A data-cleaning stage may be reused by several model comparisons. ASTRA represents this with nested `analyses`.

```yaml
analyses:
  feature_extraction:
    id: feature_extraction
    inputs:
      - id: raw_features
        from: ../iris_data
    outputs:
      - id: features
        type: data
        decisions: [method]
        recipe:
          command: python src/extract_features.py --out {output}
    decisions:
      method:
        label: Extraction method
        default: pca
        options:
          pca: { label: PCA }
          mlp_encoder: { label: MLP encoder }
```

A sub-analysis is itself an Analysis. It can have its own narrative, inputs, outputs, decisions, findings, and nested children. This self-similar structure lets authors describe a project at multiple levels of detail without switching formats.

### Bridges with `from`

Each analysis scope has its own local IDs. Cross-scope linkage happens through `from`. A node with `from` is a pure alias: it points to another element and inherits its content.

```yaml
inputs:
  - id: raw_features
    from: ../iris_data

outputs:
  - id: accuracy
    from: classification.accuracy

decisions:
  seed:
    from: ../random_seed
```

The path grammar is tree-shaped. `../` moves up one scope. Bare names descend into a named child scope. Inputs may point upward or to sibling outputs; outputs may re-export child outputs; decisions flow downward from ancestors into descendants. Recipes still use local IDs. The bridge is declared once in the ASTRA structure rather than repeatedly inside commands.

### External analyses

To consume a separate ASTRA analysis as a dependency, declare an input with `type: analysis` and `ref`.

```yaml
inputs:
  - id: prior_study
    type: analysis
    ref: analyses/preprocessing_comparison
    ref_version: "v1.2"
    use_outputs: [best_method, performance_table]
```

This is different from `from`. `ref` points to an external analysis record. `from` aliases an element inside the current analysis tree.

### External sub-analysis files

A sub-analysis can also live in another directory with its own `astra.yaml`.

```yaml
analyses:
  preprocessing:
    path: stages/preprocessing
```

When `path` is set, inline content fields such as `inputs`, `outputs`, and `decisions` are mutually exclusive with it. This allows large projects to keep one conceptual analysis tree while splitting the files into manageable pieces.

## Validation model

ASTRA validation is designed to catch both syntax errors and scientific-record errors.

| Stage | What it checks |
|---|---|
| Schema validation | YAML shape, field types, required fields, enum values, version and DOI patterns. |
| Semantic validation | Duplicate IDs, default options, constraint references, `from` paths, output dependencies, recipe placeholders, universe selections, and constraint satisfaction. |
| Narrative validation | Internal Markdown anchors, required narrative sections, and coverage warnings for declared elements not mentioned in prose. |
| Evidence verification | Optional quote matching against cited PDFs or artifacts. |

Run validation with:

```bash
astra validate astra.yaml
```

Evidence verification is opt-in:

```bash
astra validate astra.yaml --verify-evidence
```

A valid ASTRA file is not a guarantee that the science is correct. It is a guarantee that the record is structured enough for the science to be inspected.

---

## Field reference

The rest of this page is a compact reference. For generated class-level documentation, see the [schema reference](elements/index.md).

### Analysis

The `Analysis` object is the root of `astra.yaml` and the type used for every sub-analysis.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | No | Identifier for this analysis, especially when nested. |
| `version` | `string` | No | ASTRA schema version, e.g. `"1.0"` or `"1.0.0"`. |
| `name` | `string` | No | Human-readable analysis name. |
| `narrative` | `Narrative` | No | Structured prose sections. |
| `authors` | `string[]` | No | Authors or maintainers of the analysis. |
| `tags` | `string[]` | No | Free-form categorization tags. |
| `container` | `string` | No | Default container for recipes in this analysis node. |
| `inputs` | `Input[]` | No | Data or prior analyses consumed by this analysis. |
| `outputs` | `Output[]` | No | Artifacts produced or re-exported by this analysis. |
| `decisions` | map of `Decision` | No | Methodological choice points. |
| `prior_insights` | map of `Insight` | No | Existing claims used to motivate choices. |
| `findings` | map of `Insight` | No | Claims produced by this analysis. |
| `analyses` | map of `Analysis` | No | Nested sub-analyses. |
| `path` | `string` | No | External directory containing a sub-analysis ASTRA file. |

`path` is for nested analyses only. It is mutually exclusive with inline content fields on that sub-analysis.

### Narrative

`narrative` contains Markdown prose. It lets renderers and review tools present the analysis in a stable order.

| Field | Required by validator when... | Meaning |
|---|---|---|
| `summary` | Never required | High-level orientation: question, scope, and purpose. |
| `findings` | `Analysis.findings` has entries | Prose framing the structured findings. |
| `methods` | `Analysis.decisions` or `Analysis.analyses` has entries | Methodology, decision space, and sub-analysis structure. |
| `inputs` | `Analysis.inputs` has entries | Prose framing the declared inputs. |
| `outputs` | `Analysis.outputs` has entries | Prose framing the declared outputs. |

Internal narrative links use Markdown anchors:

| Target | Anchor form |
|---|---|
| Input | `#inputs.<id>` |
| Output | `#outputs.<id>` |
| Decision | `#decisions.<id>` |
| Option | `#decisions.<id>.options.<id>` |
| Finding | `#findings.<id>` |
| Prior insight | `#prior_insights.<id>` |
| Sub-analysis | `#analyses.<sub>` |
| Element inside a sub-analysis | `#<sub>.<category>.<id>` |

References are interpreted relative to the analysis that contains the prose. Use `../` to link to a parent scope, for example `#../decisions.model`.

### Input

An input declares something the analysis consumes, or aliases an upstream artifact with `from`.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Local identifier. |
| `label` | `string` | No | Short display name. |
| `type` | `data` or `analysis` | Yes when `from` is absent | Kind of input. |
| `description` | `string` | No | Human-readable explanation. |
| `source` | `string` | No | URI, path, loader, or other data locator for `type: data`. |
| `ref` | `string` | No | Reference to another ASTRA analysis for `type: analysis`. |
| `ref_version` | `string` | No | Version of the referenced analysis. |
| `use_outputs` | `string[]` | No | Outputs to consume from a referenced analysis. |
| `from` | `string` | No | Path alias to an upstream input or sibling output. |

When `from` is present, the input is a pure alias. Only `id` and `from` may be declared; content is inherited from the source.

### Output

An output is an artifact produced locally or re-exported from a child sub-analysis.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Local identifier. |
| `label` | `string` | No | Short display name. |
| `type` | `metric`, `figure`, `table`, `data`, or `report` | Yes when `from` is absent | Artifact kind. |
| `description` | `string` | No | What the output represents. |
| `from` | `string` | No | Path alias to a child output. |
| `when` | `string[]` | No | Conditions under which the output is active. |
| `inputs` | `string[]` | No | Local input or sibling output IDs this output depends on. |
| `decisions` | `string[]` | No | Local decision IDs that parameterize the output. |
| `recipe` | `Recipe` | No | Command and execution context for producing the output. |

Output types:

| Type | Use for |
|---|---|
| `metric` | A scalar or categorical measurement such as accuracy, p-value, likelihood, or score. |
| `figure` | A visual artifact such as a plot, map, diagnostic, or image. |
| `table` | Structured tabular output. |
| `data` | A processed dataset, model file, catalog, or intermediate artifact. |
| `report` | Textual or document output. |

When `from` is present, the output is a pure re-export. Only `id`, `from`, and `when` may be declared locally.

### Recipe

A recipe is a command plus optional execution context.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `command` | `string` | Yes | POSIX shell command template. |
| `resources` | `Resources` | No | Compute requirements. |
| `container` | `string` | No | Container image or path to a Containerfile. |

Recipe placeholders:

| Placeholder | Meaning |
|---|---|
| `{inputs.<id>}` | Path to a named input declared in the parent output's `inputs`. |
| `{inputs}` | Space-separated paths to all parent output inputs in declaration order. |
| `{decisions.<id>}` | Active option ID for a decision declared in the parent output's `decisions`. |
| `{output}` | Path where the runner should write the produced artifact. |
| `{{` and `}}` | Literal braces. |

Resources:

| Field | Type | Meaning |
|---|---|---|
| `cpus` | `number` | Requested CPU cores. Fractional values are allowed. |
| `memory` | `string` | Memory with units, e.g. `"16Gi"` or `"8GB"`. |
| `time_limit` | `string` | Wall-time duration, e.g. `"30m"` or `"2h"`. |
| `disk` | `string` | Disk with units. |
| `gpus` | `integer` | Number of GPUs. |

### Decision

A decision is a methodological choice point.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `label` | `string` | Yes when `from` is absent | Human-readable name. |
| `rationale` | `string` | No | Why this choice matters scientifically. |
| `tags` | `string[]` | No | Grouping labels. |
| `when` | `string[]` | No | Conditions under which this decision is active. |
| `from` | `string` | No | Alias to an ancestor decision. |
| `default` | `string` | No | Default option ID. |
| `options` | map of `Option` | Yes when `from` is absent | Available choices. |

When `from` is present, the decision is a pure alias to an ancestor decision. Only `from` and, where needed, `when` may be declared locally.

### Option

An option is one possible selection for a decision.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `label` | `string` | Yes | Human-readable name. |
| `description` | `string` | No | Explanation of what the option does. |
| `notes` | `string` | No | Additional author notes. |
| `insights` | `string[]` | No | Prior insight IDs supporting the option. |
| `requires` | `string[]` | No | Other options that must be selected with this one. |
| `incompatible_with` | `string[]` | No | Other options that cannot be selected with this one. |
| `excluded` | `boolean` | No | Marks an option as considered but unavailable. |
| `excluded_reason` | `string` | No | Why the option was excluded. |

Constraint references use `decision_id.option_id` and are scoped within the same analysis node.

### Insight and Evidence

`Insight` is used for both `prior_insights` and `findings`.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `claim` | `string` | Yes | The scientific claim. |
| `label` | `string` | No | Short display name. |
| `created_at` | `datetime` | Yes | Creation timestamp. |
| `evidence` | `Evidence[]` | Yes | Sources or artifacts supporting the claim. |
| `derived` | `boolean` | No | Whether the claim was produced by this analysis. |
| `tags` | `string[]` | No | Categorization tags. |
| `notes` | `string` | No | Additional prose. |

Evidence fields:

| Field | Type | Meaning |
|---|---|---|
| `id` | `string` | Local evidence identifier. |
| `doi` | `string` | DOI for a cited paper or source. |
| `artifact` | `string` | ASTRA artifact ID, often an output. |
| `version` | `integer` | Source paper version, especially for arXiv papers. |
| `snapshot` | `string` | Path to an immutable copy of an artifact. |
| `source_commit` | `string` | Commit that produced an artifact. |
| `quote` | `TextQuoteSelector` | Exact text quote and optional prefix/suffix. |
| `location` | `FragmentSelector` | Source location hint such as a PDF page. |

ASTRA follows the spirit of W3C selectors: evidence should identify not just a source, but the specific location or text that supports the claim.

### Universe

A universe selects one option for every active decision.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Universe identifier. |
| `description` | `string` | No | Human-readable explanation. |
| `decisions` | map of `decision_id: option_id` | No | Selections at the current analysis scope. |
| `analyses` | map of `UniverseNode` | No | Nested selections mirroring sub-analyses. |

Universe IDs may use lowercase letters, numbers, underscores, and hyphens. Decision and option IDs use lowercase snake_case.

### Conditions and constraints

`when` conditions use:

```text
decision_id.option_id
~decision_id.option_id
```

The first form means “active when this option is selected.” The second means “active when this option is not selected.” Multiple entries are ANDed.

Option constraints use the same `decision_id.option_id` reference form:

| Field | Meaning |
|---|---|
| `requires` | The referenced option must also be selected. |
| `incompatible_with` | The referenced option must not be selected. |

### Bridges and path grammar

`from` aliases elements across analysis scopes. The grammar is shared by inputs, outputs, and decisions, but each slot restricts which directions are legal.

| Form | Meaning |
|---|---|
| `../id` | Move up one scope and reference `id`. |
| `../../id` | Move up two scopes and reference `id`. |
| `../scope.id` | Move up, then descend into a named child scope. |
| `scope.id` | Descend into a named child scope. |
| `scope.sub.id` | Descend through nested child scopes. |

Legal directions:

| Slot | Legal forms | Purpose |
|---|---|---|
| `Input.from` | `../id`, `../../id`, `../scope.out_id` | Alias an ancestor input or sibling sub-analysis output. |
| `Output.from` | `child.out_id`, `child.sub.out_id` | Re-export a child output. |
| `Decision.from` | `../id`, `../../id` | Inherit an ancestor decision. |

### ID conventions

| Context | Pattern | Example |
|---|---|---|
| Input, output, decision, option, sub-analysis, insight, evidence IDs | `^[a-z][a-z0-9_]*$` | `iris_data`, `scaling` |
| Universe IDs | `^[a-z][a-z0-9_-]*$` | `baseline`, `svm-focused` |
| Constraint references | `decision_id.option_id` | `scaling.standard` |
| Version | `^\d+\.\d+(\.\d+)?$` | `"1.0"`, `"1.0.0"` |
| DOI | `^10\.\d{4,}/.*$` | `"10.48550/arXiv.1706.03762"` |

These category names are reserved and cannot be used as entity IDs:

```text
inputs   outputs   decisions   findings   prior_insights
analyses options   content     narrative
```

The reserved names prevent ambiguity in narrative anchors and path references.

### Schema artifacts

ASTRA is defined in LinkML. The source schema files live in `src/astra/schema/` and generate datamodels and validation artifacts for multiple ecosystems.

| File | Defines |
|---|---|
| `analysis.yaml` | `Analysis`, `Input`, `Output`, `Decision`, `Option`, `Recipe`, `Resources`, narrative structure, and cross-scope aliases. |
| `universe.yaml` | `Universe`, `UniverseNode`, and decision selections. |
| `insight.yaml` | `Insight`, `Evidence`, quote selectors, fragment selectors, and insight collections. |

Generated Python datamodels are distributed with the package. The documentation site also includes the [auto-generated schema reference](elements/index.md) for exact class and slot details.
