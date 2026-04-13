# ASTRA Specification

**Agentic Schema for Transparent Research Analysis**

[![Build and test](https://github.com/LightconeResearch/astra-spec/actions/workflows/main.yaml/badge.svg)](https://github.com/LightconeResearch/astra-spec/actions/workflows/main.yaml)
[![License: CC BY 4.0](https://img.shields.io/badge/Schema_License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![License: Apache 2.0](https://img.shields.io/badge/Code_License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

ASTRA is a declarative specification format for scientific analyses. It separates **what** you want to learn from **how** to compute it: you declare inputs, outputs, and decisions; an agent or workflow engine handles execution.

```
┌──────────────────┐       ┌───────────┐       ┌─────────┐
│  ASTRA Analysis  │ ────> │   Agent   │ ────> │ Results │
│                  │       │ (executes)│       │         │
│  - inputs        │       │           │       │ metrics │
│  - outputs       │       │           │       │ figures │
│  - decisions     │       │           │       │ data    │
└──────────────────┘       └───────────┘       └─────────┘
         ^                                          │
         └──── previous analyses (as inputs) ───────┘
```

**Specification**: [astra-spec.org](https://astra-spec.org) | **Namespace**: `https://w3id.org/ASTRA/`

## Why ASTRA?

Scientific analyses are built on a cascade of methodological choices -- which algorithm to use, how to split the data, what priors to assume. These decisions are rarely documented systematically, and the alternatives considered are almost never recorded. This makes it hard to reproduce results, understand why one approach was chosen, or explore what would have happened differently.

ASTRA provides a structured format where every analytical choice is explicit, every alternative is documented, and every decision is backed by traceable evidence.

## Design Principles

1. **Declarative** -- the spec says *what*, not *how*
2. **Self-similar** -- every level has the same structure; a sub-analysis is a valid analysis
3. **Transparent** -- all decisions and alternatives are documented, including rejected options
4. **Evidence-linked** -- decisions cite supporting evidence from papers or artifacts
5. **Composable** -- analyses build on each other; outputs become inputs
6. **Reproducible** -- precise provenance with W3C-compliant source references

## Core Concepts

### Analysis (self-similar tree)

An ASTRA document describes a tree of analyses. Every node has the same recursive structure:

```
Analysis
 ├── inputs            Data or upstream analyses feeding into this node
 ├── outputs           Expected results (metrics, figures, data, reports)
 │    └── recipe       How to produce each output (command, container, resources)
 ├── decisions         Methodological choice points
 │    └── options      Available alternatives, with evidence and constraints
 ├── prior_insights    Evidence-backed knowledge informing decisions
 ├── findings          Conclusions drawn from outputs
 └── analyses          Nested sub-analyses (same structure, recursively)
```

Simple analyses are flat -- just inputs, outputs, and decisions at the top level. Complex multi-stage analyses decompose into sub-analyses, each with their own scoped decisions.

### Decisions and constraints

Each decision point declares its options explicitly. Options can reference supporting insights, and declare relationships with other options:

```yaml
decisions:
  scaling:
    label: Feature scaling method
    default: standard
    options:
      none:
        label: No scaling
      standard:
        label: StandardScaler

  model:
    label: Classification model
    options:
      random_forest:
        label: Random forest
      svm:
        label: SVM
        incompatible_with:
          - scaling.none           # SVM requires scaled features
        requires:
          - scaling.standard
      knn:
        label: K-nearest neighbors
        excluded: true
        excluded_reason: Poor performance on high-dimensional data
```

Options that were considered and rejected are kept with `excluded: true` and a reason -- preserving the decision history.

### Evidence-backed insights

Insights are units of scientific knowledge that justify decisions. Each insight makes a claim and backs it with evidence traceable to specific locations in source documents, using W3C Web Annotation-compliant selectors:

```yaml
prior_insights:
  nn_performance:
    id: nn_performance
    claim: >-
      Neural networks achieve state-of-the-art photo-z performance
      on LSST-like photometry.
    created_at: "2025-06-15T10:30:00Z"
    evidence:
      - id: ev_nn_paper
        doi: "10.48550/arXiv.2301.12345"
        version: 2
        quote:
          exact: "FlexZBoost achieves a NMAD of 0.018 on the test set."
          prefix: "Results section."
        location:
          page: 8
```

This creates a traceable chain: **decision option** --> **insight** --> **evidence** --> **paper (DOI)**.

Insights appear in two roles:
- **Prior insights** -- existing knowledge that *informs* decisions
- **Findings** -- conclusions *produced* by the analysis, backed by its own output artifacts

### Universe and multiverse

A **universe** is a complete set of decisions -- one option selected for every decision point across the tree. It fully specifies a single concrete configuration of the analysis.

The **multiverse** is the space of all valid decision combinations. Its purpose is **transparency and traceability**, not exhaustive search:

| Approach | Purpose | Runs |
|----------|---------|------|
| **Single universe** | Produce declared outputs | 1 (the typical case) |
| **Multiverse documentation** | Show all possible paths | 0 (just documentation) |
| **Robustness check** | Verify conclusions are stable | Selected alternatives |

A well-specified analysis should produce its outputs with a **single universe** (the baseline). The multiverse exists to make the researcher's choices transparent and explorable.

```yaml
# universes/baseline.yaml
id: baseline
description: Default configuration using standard practices
decisions:
  scaling: standard
  model: random_forest
analyses:
  calibration:
    id: calibration
    decisions:
      cal_method: pitpz
```

### Composability

Analyses can reference other analyses as inputs. Sub-analyses wire their inputs from parents or siblings using `from`:

```yaml
analyses:
  feature_extraction:
    inputs:
      - id: raw_data
        type: data
        from: iris_data                    # from parent input

  classification:
    inputs:
      - id: features
        type: analysis
        from: feature_extraction.features  # from sibling output
```

## Getting Started

### Install

```bash
pip install astra-spec
```

### Use in Python

```python
from astra.datamodel import Analysis, Universe
from linkml_runtime.loaders import yaml_loader

# Load an analysis specification
analysis = yaml_loader.load("astra.yaml", target_class=Analysis)

# Load a universe (decision configuration)
universe = yaml_loader.load("universes/baseline.yaml", target_class=Universe)
```

### Schema Artifacts

ASTRA is defined in [LinkML](https://linkml.io) and generates bindings for Python, TypeScript, JSON Schema, JSON-LD, and more.

| Format | URL |
|--------|-----|
| LinkML (source) | [`astra-spec.org/schema/astra.yaml`](https://astra-spec.org/schema/astra.yaml) |
| JSON Schema | [`astra-spec.org/schema/astra.schema.json`](https://astra-spec.org/schema/astra.schema.json) |
| JSON-LD Context | [`astra-spec.org/schema/astra.context.jsonld`](https://astra-spec.org/schema/astra.context.jsonld) |

## Non-Goals

ASTRA intentionally does **not** address:

- **Workflow execution** -- ASTRA defines what to compute; execution is handled by agents or workflow engines
- **Code generation** -- the spec is not a template; agents interpret it
- **Data storage** -- ASTRA references data, it does not store it
- **Visualization** -- rendering is handled by separate tools

## Development

### Setup

```bash
git clone https://github.com/LightconeResearch/astra-spec.git
cd astra-spec
uv sync --dev
```

Requires Python 3.9+, [uv](https://docs.astral.sh/uv/), and [just](https://github.com/casey/just/).

### Commands

```bash
just test        # Run all tests
just gen-python  # Regenerate Python datamodels
just gen-doc     # Generate documentation
just lint        # Lint the schema
just testdoc     # Build and preview docs locally
```

Run `just --list` to see all available commands.

### Repository Structure

```
src/astra/
  schema/       # LinkML schema source (edit these)
  datamodel/    # Generated Python datamodel
tests/
  data/         # Example YAML fixtures (valid / invalid)
docs/           # Documentation source
project/        # Generated multi-language artifacts
```

## License

- **Schema**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code**: [Apache 2.0](LICENSE)

## Credits

Built with [LinkML](https://linkml.io) using the [linkml-project-copier](https://github.com/dalito/linkml-project-copier) template.
