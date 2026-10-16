# The ASTRA Specification Explained

As agents make it easier to generate analyses, the bottleneck shifts from producing results to inspecting whether each result should be trusted. An `astra.yaml` file is a scientific record that chains together inputs, outputs, methodological choices, evidence, and claims. It allows an experiment to be quickly checked and expanded upon. `astra.yaml` is meant to be written and read by agents as readily as by people.

Here, we explain each part of the format piece by piece.

## What an ASTRA document describes

An ASTRA document describes the purpose of an experiment, which artifacts matter, which choices shape those artifacts, and how a reader can trace claims back to evidence.

An `astra.yaml` file contains an `Analysis`, which declares:

| Section | Question it answers |
|---|---|
| `description` | How is this analysis explained in prose? |
| `inputs` | What data or prior analyses does this analysis consume? |
| `outputs` | What metrics, figures, tables, data products, or reports does it produce? |
| `decisions` | Which methodological choice points shape the outputs? |
| `universes` | Which combinations of choices is the analysis run under? |
| `prior_insights` | Which existing claims or sources inform the analysis? |
| `findings` | What claims does this analysis make after its outputs are produced? |
| `analyses` | Which nested sub-analyses make up a larger analysis tree? |

## Minimal ASTRA document

A minimal useful ASTRA document names the analysis, declares an input, an output, and the decisions that affect that output. In the example below, the analysis consumes the `catalog_data` input, produces the `fit_params` output, and exposes a methodological choice, `fit_method`.

```yaml
version: "1.0"
name: Period-Luminosity Fit

description: |
  Fit a period-luminosity relation from a measurement catalog.

inputs:
  - id: catalog_data
    type: data
    source: data/catalog_data.csv
    description: Periods and mean apparent magnitudes.

outputs:
  - id: fit_params
    type: table
    format: csv
    description: Slope, intercept, and scatter for the period-luminosity relation.
    inputs: [catalog_data]
    decisions: [fit_method]
    recipe:
      command: >-
        python src/fit_period_luminosity.py
        --catalog {inputs.catalog_data}
        --method {decisions.fit_method}
        --out {output}

decisions:
  fit_method:
    label: Fitting method
    rationale: The fitting method determines how outliers influence the inferred relation.
    options:
      ordinary_least_squares:
        label: Ordinary least squares
      robust_linear:
        label: Robust linear fit
```

Validating this document gives a warning: it declares a decision but no universes, so nothing that depends on `fit_method` can be built yet. [Universes](#universes) shows how to declare them.

## Reading the example from top to bottom

```yaml
version: "1.0"
name: Period-Luminosity Fit
```

The `version` field records the ASTRA schema version the document expects. The `name` field gives the analysis a human-readable title. Real projects usually also include `id`, `tags`, and sometimes a node-level `container` used as the default execution environment for recipes.

### Description

```yaml
description: |
  Fit a period-luminosity relation from a measurement catalog.
```

`description` is a single optional free-prose field — the same field every other content object carries (`Input`, `Output`, `Option`, `Universe`). It gives readers a short orientation to the analysis. ASTRA deliberately keeps this lightweight: a richer write-up — with figures, citations, live numbers, and multi-page structure — is authored *outside* `astra.yaml` as a report that **references** the analysis's elements rather than restating them. ASTRA is not prescriptive about the authoring framework; [MySTRA](https://github.com/LightconeResearch/MySTRA) is one example — a MyST plugin that renders ASTRA components straight from `astra.yaml`. See [RFC-0002](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0002-decouple-reports.md) for the rationale.

### Inputs

```yaml
inputs:
  - id: catalog_data
    type: data
    source: data/catalog_data.csv
    description: Periods and mean apparent magnitudes.
```

An input is something the analysis consumes. It can be a dataset, a file, an external resource, or the outputs of another ASTRA analysis. The `id` is the local name used by outputs and recipes. The `type` says whether the input is `data` or an external `analysis`. Notably, the `source` is usually a path or URI, a loader name, or another data locator, and it is *descriptive* rather than prescriptive because it records enough information for agents to know where the input is sourced.

### Outputs

```yaml
outputs:
  - id: fit_params
    type: table
    format: csv
    description: Slope, intercept, and scatter for the period-luminosity relation.
    inputs: [catalog_data]
    decisions: [fit_method]
    recipe:
      command: >-
        python src/fit_period_luminosity.py
        --catalog {inputs.catalog_data}
        --method {decisions.fit_method}
        --out {output}
```

An output is a scientific artifact the analysis produces: a metric, figure, table, data product, or report. Where `type` says what the artifact *is*, `format` says how it is encoded — the file extension it is written with, so a consumer can render, diff, or open it without inspecting the bytes. Importantly, each output says what it depends on, i.e. `inputs` names the upstream artifacts required to produce it, and `decisions` names the methodological choices that parameterize it. Finally, `recipe` gives the Python command the runner invokes.

The recipe is not allowed to invent hidden dependencies, which makes the output a reviewable unit.

### Decisions

A reviewer might ask: "What if you used fitting method B instead of method A?" In ASTRA, you can codify this decision and track how it changes the outputs.

```yaml
decisions:
  fit_method:
    label: Fitting method
    rationale: The fitting method determines how outliers influence the inferred relation.
    options:
      ordinary_least_squares:
        label: Ordinary least squares
      robust_linear:
        label: Robust linear fit
```

The `fit_method` decision captures the fitting-method choice and `options` records the alternatives. None of them is singled out as the default - which option is used is chosen by each universe (see [Universes](#universes)).

Use a decision when changing a methodological choice could change an output. Give the choice an `id` and list the allowed `options`. Then attach the decision to each affected output. In this example, `fit_params.decisions: [fit_method]` tells the reader that the fitted parameters depend on the selected fitting method.

## Building up the specification

The minimal document above is enough to explain the basic shape. The rest of the specification adds structure that becomes important in real analyses: constraints between options, conditional outputs, evidence-backed claims, and nested sub-analyses.

### Options

Usually, a methodological question has a small set of plausible answers. ASTRA records those answers as `options` inside a decision. In the example below, the `photometric_band` decision asks which measurement band should be used in the fit, and the options are `g_band`, `i_band`, and `w1_band`.

```yaml
decisions:
  photometric_band:
    label: Photometric band
    rationale: The chosen band changes the fitted relation and its scatter.
    options:
      g_band:
        label: G band
        description: Use mean G-band magnitudes.
      i_band:
        label: I band
        description: Use mean I-band magnitudes.
      w1_band:
        label: W1 band
        description: Use near-infrared W1 magnitudes.
```

### Constraints between options

Sometimes, methodological choices are linked: one choice may require another, or two choices may not make sense together. ASTRA records these relationships with `requires` and `incompatible_with`. Constraint references use `decision_id.option_id`, so each rule points to a specific option inside a specific decision.

```yaml
decisions:
  fit_method:
    label: Line fitting method
    options:
      ordinary_least_squares:
        label: Ordinary least squares
      robust_linear:
        label: Robust linear fit

  outlier_handling:
    label: Outlier handling
    options:
      keep_all:
        label: Keep all points
      sigma_clip:
        label: Remove extreme outliers
        incompatible_with:
          - fit_method.robust_linear
```

Here, `outlier_handling.sigma_clip` is incompatible with `fit_method.robust_linear`. Both choices reduce the influence of points far from the fitted trend: `sigma_clip` removes extreme points before fitting, while `robust_linear` keeps them but downweights them. A universe that selects both is invalid, so ASTRA makes that methodological boundary explicit.

### Universes

A universe selects one option for each decision. Universes are declared in `astra.yaml` under `universes`. If the analysis defines `fit_method` and `outlier_handling` then each universe chooses an option for both.

```yaml
universes:
  - id: baseline
    description: Fit the relation with ordinary least squares and keep all points.
    decisions:
      fit_method: ordinary_least_squares
      outlier_handling: keep_all

  - id: robust
    description: Same as baseline with a robust linear fit.
    derived_from: baseline
    decisions:
      fit_method: robust_linear

  - id: clean
    description: Same as baseline with extreme outliers removed.
    derived_from: baseline
    decisions:
      outlier_handling: sigma_clip
```

A universe written in full lists an option for every decision. A universe can instead be written as a diff of another with `derived_from` - it inherits that universe's selections and lists only what changes. `robust` above is `baseline` with the fitting method switched. Diffs can chain but must not loop. The full set of selections a universe ends up with is its *effective selection*. If a diff switches off a conditional decision (see [Conditional elements](#conditional-elements)) the selection it inherited for that decision is dropped.

No universe is privileged. ASTRA has no default or implicit universe and reserves no universe id - `baseline` above is only a name. `derived_from` records how two universes relate and doesn't make either of them special.

Each universe produces its own outputs. For example the plot from `baseline` might be written to `results/baseline/` while the plot from `clean` might be written to `results/clean/`.

### Comparing universes

An output's inputs normally mean "in the same universe as this output". A *pin* names a universe instead: `fit_params#robust` is `fit_params` as built in `robust`. Pins let one output compare universes.

```yaml
outputs:
  - id: method_comparison
    type: table
    format: csv
    description: Fitted parameters under the two fitting methods side by side.
    inputs:
      - fit_params#baseline
      - fit_params#robust
    recipe:
      command: >-
        python src/compare_fits.py
        --a {inputs.fit_params#baseline}
        --b {inputs.fit_params#robust}
        --out {output}
```

A pin must name a universe declared in the analysis and the artifact must be active in that universe. Only outputs can be pinned - an external input is the same in every universe. Mind YAML here: `fit_params #robust` with a space is `fit_params` followed by a comment.

Whether an output is built once per universe or only once is worked out from what it depends on. It is built per universe if it declares `decisions` or reads an unpinned input that is built per universe. Otherwise it is built once - `method_comparison` depends on no universe because both its inputs are pinned. An output built once must declare its `format` and can't use `when` since there is no current universe to evaluate it in.

### Recipes and command templates

After an output has declared what it depends on, the recipe says how a runner should produce it. In this example, the recipe passes the declared catalog and selected fitting method to a Python script, then writes the fitted parameters to `{output}`.

```yaml
outputs:
  - id: fit_params
    type: table
    inputs: [catalog_data]
    decisions: [fit_method]
    recipe:
      command: >-
        python src/fit_period_luminosity.py
        --catalog {inputs.catalog_data}
        --method {decisions.fit_method}
        --out {output}
```

The command is the only required part of a recipe. You can add optional `container` and `resources` elements when the runner needs execution context, for example a Docker image for the software environment, or CPU, memory, and wall-time requests for compute.

### Prior insights, findings, and evidence

Scientific review is not only about checking the final result. It is also about checking why the analysis was set up the way it was and what the analysis claimed afterward. ASTRA separates claims that motivate the analysis from claims produced by the analysis. A `prior_insight` records an imported claim used to justify a choice, while a `finding` records a claim made by the current analysis. Both use the shared `Insight` model and can point to evidence.

```yaml
prior_insights:
  calibration_reference:
    claim: External calibration information can shift the fitted relation.
    created_at: "2026-05-11T00:00:00Z"
    evidence:
      - id: ev_calibration_reference
        doi: "10.1051/0004-6361/202244775"

decisions:
  correction_mode:
    label: Correction mode
    rationale: Calibration choices can shift the fitted intercept.
    options:
      calibrated:
        label: Apply calibration
        insights: [calibration_reference]

findings:
  cleaned_fit:
    claim: The cleaned-data universe reduced the fit scatter.
    created_at: "2026-05-11T00:00:00Z"
    evidence:
      - id: ev_fit_params
        artifact: fit_params#clean
        quote:
          exact: "scatter = 0.18 mag"
    derived: true
```

Evidence is what lets a reader check a claim instead of simply accepting it. It can cite a paper, identify a passage in a source document, or point to an artifact produced by the analysis. The same structure works for prior insights and findings: a decision can say which insight supports it, and each insight can say exactly which source or output supports the claim. With evidence verification enabled, tools can check whether quoted text actually appears in the cited source.

When the cited output is built per universe, pin it to the universe the claim is about (`fit_params#clean` above) - the quoted scatter is only true of that universe's fit.

### Excluded options

A rejected option can still be scientifically important. ASTRA lets authors keep it in the record while marking it as unavailable for valid universes.

```yaml
options:
  quadratic_fit:
    label: Quadratic relation
    excluded: true
    excluded_reason: Pilot residuals did not justify adding curvature.
```

In this way, a reviewer can see not only what was chosen, but what was considered and why it was rejected.

### Sub-analyses

Experiments are usually made of smaller analyses. In ASTRA, you can build them up as nested `analyses`: a cleaning stage can feed a fitting stage, which can feed a summary plot.

```yaml
analyses:
  catalog_cleaning:
    id: catalog_cleaning
    inputs:
      - id: raw_catalog
        from: ../source_catalog
    outputs:
      - id: cleaned_catalog
        type: data
        decisions: [outlier_handling]
        recipe:
          command: python src/clean_catalog.py --out {output}
    decisions:
      outlier_handling:
        label: Outlier handling
        options:
          keep_all: { label: Keep all points }
          sigma_clip: { label: Remove extreme outliers }
```

A sub-analysis is itself an Analysis. It can have its own description, inputs, outputs, decisions, findings, and nested children. This self-similar structure lets authors describe a project at multiple levels of detail without switching formats.

Sub-analyses can be written inline, as above, or split into their own directories when a project becomes large. If `path` is set, that child analysis is read from another `astra.yaml`, while still belonging to the same conceptual analysis tree.

```yaml
analyses:
  catalog_cleaning:
    path: stages/catalog_cleaning
```

If the dependency is a separate ASTRA record rather than a child of the current analysis, declare it as an input with `type: analysis` and `ref`.

```yaml
inputs:
  - id: prior_fit
    type: analysis
    ref: analyses/baseline_fit
    ref_version: "v1.2"
    use_outputs: [fit_params, residual_plot]
```

### Conditional elements

Use `when` when a choice creates a branch of the analysis. For example, one choice may require an extra assumption, diagnostic, or output that should not appear in every universe. Conditions use `decision.option`, with a `~` prefix for negation. Multiple conditions are ANDed together.

```yaml
decisions:
  correction_mode:
    label: Correction mode
    options:
      none: { label: No correction }
      calibrated: { label: Apply calibration }

  calibration_prior:
    label: Calibration prior
    when:
      - correction_mode.calibrated
    options:
      weak: { label: Weak prior }
      informative: { label: Informative prior }

outputs:
  - id: calibrated_table
    type: table
    when:
      - correction_mode.calibrated
    recipe:
      command: python src/apply_calibration.py --out {output}
```

In the example, `calibration_prior` and `calibrated_table` exist only for the calibrated branch. A baseline universe that selects `correction_mode.none` stays simpler: it does not carry a prior or output that it never uses.

## Validation model

ASTRA validation is designed to catch both syntax errors and scientific-record errors.

| Stage | What it checks |
|---|---|
| Schema validation | YAML shape, types, enums, version and DOI patterns. |
| Semantic validation | Duplicate IDs, references, `from` paths, recipe placeholders, and constraint satisfaction. Universes and pins: `derived_from` chains, complete effective selections, pinned universes that exist and where the artifact is active. |
| Evidence verification | Optional quote matching against cited sources. |

Not every finding is fatal. Fields that are *recommended* rather than required — currently `Output.format` — produce a **warning**: the document still validates, but the validator flags what will become an error in a future release.

Semantic validation also warns about things that are allowed but probably not meant: a pin on an output that is built once anyway, evidence citing an output built per universe without a pin, and decisions declared with no universes to build them.

Run validation with:

```bash
astra validate astra.yaml
```

Evidence verification is opt-in:

```bash
astra validate astra.yaml --verify-evidence
```

Remember, validation does not prove that the science is correct, obviously! It proves that the record is structured enough to inspect.

## Conclusion

That covers the ASTRA format. If you're curious, try asking your agent to turn a piece of your own research into an `astra.yaml` and see what comes back. The rest of this page is a field reference for the individual schema elements.

---

## Field reference

For generated class-level documentation, see the [schema reference](elements/index.md).

### Analysis

The `Analysis` object is the root of `astra.yaml` and the type used for every sub-analysis.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | No | Identifier for this analysis, especially when nested. |
| `version` | `string` | No | ASTRA schema version, e.g. `"1.0"` or `"1.0.0"`. |
| `name` | `string` | No | Human-readable analysis name. |
| `description` | `string` | No | Free-prose description of the analysis. |
| `tags` | `string[]` | No | Free-form categorization tags. |
| `container` | `string` | No | Default container for recipes in this analysis node. |
| `inputs` | `Input[]` | No | Data or prior analyses consumed by this analysis. |
| `outputs` | `Output[]` | No | Artifacts produced or re-exported by this analysis. |
| `decisions` | map of `Decision` | No | Methodological choice points. |
| `prior_insights` | map of `Insight` | No | Existing claims used to motivate choices. |
| `findings` | map of `Insight` | No | Claims produced by this analysis. |
| `analyses` | map of `Analysis` | No | Nested sub-analyses. |
| `universes` | `Universe[]` | No | Universes declared in this analysis. The root analysis's universes are the ones that are built. |
| `path` | `string` | No | External directory containing a sub-analysis ASTRA file. |

`path` is for nested analyses only. It is mutually exclusive with inline content fields on that sub-analysis.

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

When `from` is present, the input is a pure alias. Only `id` and `from` may be declared, and content is inherited from the source.

### Output

An output is an artifact produced locally or re-exported from a child sub-analysis.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Local identifier. |
| `label` | `string` | No | Short display name. |
| `type` | `metric`, `figure`, `table`, `data`, or `report` | Yes when `from` is absent | Artifact kind. |
| `format` | `string` | Recommended | Serialization of the artifact, as a lowercase token: the file extension without the leading dot. Becomes required at 0.1.0 — see below. Required on an output built once. |
| `description` | `string` | No | What the output represents. |
| `from` | `string` | No | Path alias to a child output. |
| `when` | `string[]` | No | Conditions under which the output is active. Not allowed on an output built once. |
| `inputs` | `string[]` | No | Local input or sibling output IDs this output depends on. An output can be pinned to a universe (`fit_params#robust`). |
| `decisions` | `string[]` | No | Local decision IDs that parameterize the output. |
| `recipe` | `Recipe` | No | Command and execution context for producing the output. |

Output types:

| Type | Use for |
|---|---|
| `metric` | A scalar or categorical measurement such as fit scatter, p-value, likelihood, or score. |
| `figure` | A visual artifact such as a plot, map, diagnostic, or image. |
| `table` | Structured tabular output. |
| `data` | A processed dataset, catalog, calibration table, or intermediate artifact. |
| `report` | Textual or document output. |

Output formats:

`format` is a lowercase token matching `^[a-z0-9][a-z0-9_.+-]*$` — the extension the artifact is written with, minus the leading dot. The value space is deliberately **open**: common values are `png`, `svg`, `pdf`, `csv`, `parquet`, `json`, `fits`, `hdf5`, `html`, and `md`, but any token matching the pattern is legal, so field-specific formats (`asdf`, `zarr`, `nc`) need no schema change.

!!! warning "`format` becomes required at 0.1.0"

    Throughout the 0.0.x series `format` is **recommended**, not required: a document that omits it validates, and `astra validate` reports a warning rather than an error. From **0.1.0** it is required on every non-aliased output, so add it now — the warning is your migration runway.

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
| `{inputs.<entry>}` | Path to one input, naming the entry exactly as written in the parent output's `inputs` (`{inputs.catalog_data}`, `{inputs.fit_params#robust}`). |
| `{inputs}` | Space-separated paths to all parent output inputs in declaration order. |
| `{decisions.<id>}` | Active option ID for a decision declared in the parent output's `decisions`. |
| `{output}` | Path where the runner should write the produced artifact. |
| `{{` and `}}` | Literal braces. |

The command string is a typed template. Every `{inputs.<entry>}` placeholder must match an entry of the parent `Output.inputs` exactly - including any dots and pin. Every `{decisions.<id>}` placeholder must name a decision listed in the parent `Output.decisions`. Validators reject unresolved or undeclared placeholders.

Placeholders always use local IDs in the surrounding analysis scope. If an input or decision is aliased from another scope with `from`, the recipe still names the local alias. Recipes do not use `../` path syntax. Cross-scope wiring is declared once on the `Input`, `Output`, or `Decision`.

Decision placeholders resolve to the selected option ID in the current universe. If a script needs a numeric value, such as a seed, either map the option ID inside the script or choose option IDs that are usable directly.

Resources:

| Field | Type | Meaning |
|---|---|---|
| `cpus` | `number` | Requested CPU cores. Fractional values are allowed. |
| `memory` | `string` | Memory with units, e.g. `"16Gi"` or `"8GB"`. |
| `time_limit` | `string` | Wall-time duration, e.g. `"30m"` or `"2h"`. |
| `disk` | `string` | Disk with units. |
| `gpus` | `integer` | Number of GPUs. |

A node-level `container` on `Analysis` sets the default for recipes in that node. A recipe-level `container` overrides it. Image names such as `python:3.12-slim` or `ghcr.io/org/image:latest` are interpreted as pre-built images. Paths such as `Containerfile` or `containers/Dockerfile` are interpreted as build contexts by runners that support them.

Example rendered command after a runner materializes paths and selects a universe:

```bash
python src/fit_period_luminosity.py \
  --catalog /work/baseline/catalog.csv \
  --method ordinary_least_squares \
  --out /work/baseline/fit_params.csv
```

### Decision

A decision is a methodological choice point.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `label` | `string` | Yes when `from` is absent | Human-readable name. |
| `rationale` | `string` | No | Why this choice matters scientifically. |
| `tags` | `string[]` | No | Grouping labels. |
| `when` | `string[]` | No | Conditions under which this decision is active. |
| `from` | `string` | No | Alias to an ancestor decision. |
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
| `id` | `string` | Yes | Unique insight identifier. |
| `claim` | `string` | Yes | The scientific claim. |
| `label` | `string` | No | Short display name. |
| `created_at` | `datetime` | Yes | Creation timestamp. |
| `evidence` | `Evidence[]` | Yes | Sources or artifacts supporting the claim. |
| `derived` | `boolean` | No | Whether the claim was produced by this analysis. |
| `scope` | `string` | No | Applicability conditions for the claim. |
| `tags` | `string[]` | No | Categorization tags. |
| `notes` | `string` | No | Additional prose. |

Each evidence item references either literature with `doi` or an analysis artifact with `artifact`. Exactly one of those source fields must be set. Literature evidence should include a text quote for verifiability.

Evidence fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Local evidence identifier. |
| `doi` | `string` | Exactly one of `doi` or `artifact` | DOI for a cited paper or source. |
| `artifact` | `string` | Exactly one of `doi` or `artifact` | ASTRA artifact ID, often an output. Pin it to a universe when the output is built per universe (`fit_params#clean`). |
| `version` | `integer` | No | Source paper version, especially for arXiv papers. |
| `snapshot` | `string` | No | Path to an immutable copy of an artifact. |
| `source_commit` | `string` | No | Commit that produced an artifact. |
| `quote` | `TextQuoteSelector` | No | Exact text quote and optional prefix/suffix. |
| `location` | `FragmentSelector` | No | Source location hint such as a PDF page. |

ASTRA follows the spirit of W3C selectors: evidence should identify not just a source, but the specific location or text that supports the claim.

`TextQuoteSelector` fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `exact` | `string` | Yes | Exact quoted text. |
| `prefix` | `string` | No | Text before the quote, used for disambiguation. |
| `suffix` | `string` | No | Text after the quote, used for disambiguation. |

`FragmentSelector` fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `value` | `string` | No | Fragment value, such as `page=6`. |
| `page` | `integer` | No | One-indexed page number. |

### Universe

A universe selects one option for every active decision.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Universe identifier. |
| `description` | `string` | No | Human-readable explanation. |
| `derived_from` | `string` | No | Another universe of the same analysis whose effective selection this one inherits. |
| `decisions` | map of `decision_id: option_id` | No | Selections at the current analysis scope. Complete unless `derived_from` is set - then only what differs. |
| `analyses` | map of `UniverseNode` | No | Nested selections mirroring sub-analyses. |

Universe IDs may use lowercase letters, numbers, underscores, and hyphens. Decision and option IDs use lowercase snake_case.

An `analyses` entry either lists the sub-analysis's `decisions` or names one of that sub-analysis's own universes with `universe: <id>`. With `derived_from` the entries are inherited per sub-analysis - an entry's `decisions` override the inherited ones and an entry naming `universe` replaces the inherited entry.

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

For example, using a calibrated input can require a selected correction method:

```yaml
decisions:
  data_version:
    options:
      calibrated:
        label: Calibrated input
        requires:
          - correction_mode.calibrated
```

An option can also rule out another option:

```yaml
decisions:
  outlier_handling:
    options:
      sigma_clip:
        label: Remove extreme outliers
        incompatible_with:
          - fit_method.robust_linear
```

Negated conditions use the same `~decision.option` form:

```yaml
decisions:
  residual_summary:
    label: Residual summary
    when:
      - ~outlier_handling.sigma_clip
    options:
      all_points:
        label: Use all residuals
```

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

`from` is the only primitive for crossing analysis scopes. Recipe templates, `Output.inputs`, and `Output.decisions` continue to use local IDs in their surrounding scope. When `from` is set, the node is a pure alias: only `id`, `from`, and, where applicable, `when` may be declared locally. Content fields such as `type`, `description`, `label`, `source`, `options`, and `recipe` are inherited from the source.

Inputs and outputs can reach into subordinate scopes for artifacts, which can flow upward by re-export or laterally between sibling sub-analyses. Decisions only flow downward from ancestors into descendants. To share a decision between siblings, declare it on their common ancestor and alias it with `from` inside each child.

Sibling output alias:

```yaml
analyses:
  preprocessing:
    outputs:
      - id: cleaned_catalog
        type: data

  fitting:
    inputs:
      - id: catalog
        from: ../preprocessing.cleaned_catalog
```

Child output re-export:

```yaml
outputs:
  - id: fit_parameters
    from: fitting.fit_parameters
```

Ancestor decision alias:

```yaml
analyses:
  fitting:
    decisions:
      magnitude:
        from: ../magnitude
```

External analysis dependencies are separate from `from`. Use `type: analysis` with `ref` when the dependency is a different ASTRA analysis rather than an element inside the current analysis tree:

```yaml
inputs:
  - id: prior_fit
    type: analysis
    ref: analyses/baseline_fit
    ref_version: "1.2"
    use_outputs: [fit_parameters, residual_plot]
```

### ID conventions

| Context | Pattern | Example |
|---|---|---|
| Input, output, decision, option, sub-analysis, insight, evidence IDs | `^[a-z][a-z0-9_]*$` | `catalog_data`, `fit_method` |
| Universe IDs | `^[a-z][a-z0-9_-]*$` | `baseline`, `cleaned-data` |
| Constraint references | `decision_id.option_id` | `fit_method.robust_linear` |
| Version | `^\d+\.\d+(\.\d+)?$` | `"1.0"`, `"1.0.0"` |
| DOI | `^10\.\d{4,}/.*$` | `"10.48550/arXiv.1706.03762"` |

These category names are reserved and cannot be used as entity IDs:

```text
inputs   outputs   decisions   findings   prior_insights
analyses options   content
```

The reserved names prevent ambiguity in tree-path references and element addressing.

### Schema artifacts

ASTRA is defined in LinkML. The source schema files live in `src/astra/schema/` and generate datamodels and validation artifacts for multiple ecosystems.

Generated artifacts:

| Artifact | Purpose |
|---|---|
| [LinkML YAML](schema/astra.yaml) | Merged source schema definition. |
| [JSON Schema](schema/astra.schema.json) | YAML/JSON validation artifact. |
| [JSON-LD Context](schema/astra.context.jsonld) | Linked-data context. |
| Python datamodels | Generated classes distributed with the package. |

| File | Defines |
|---|---|
| `analysis.yaml` | `Analysis`, `Input`, `Output`, `Decision`, `Option`, `Recipe`, `Resources`, and cross-scope aliases. |
| `universe.yaml` | `Universe`, `UniverseNode`, `DecisionSelection`, and decision selections. |
| `insight.yaml` | `Insight`, `Evidence`, `InsightCollection`, quote selectors, and fragment selectors. |

Generated Python datamodels are distributed with the package. The documentation site also includes the [auto-generated schema reference](elements/index.md) for exact class and slot details.
