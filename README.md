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

## Quick Example

```yaml
# astra.yaml
version: "1.0"
name: Iris Classification

inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris

outputs:
  - id: accuracy
    type: metric
    recipe:
      command: python src/evaluate.py

decisions:
  scaling:
    label: Feature Scaling
    default: standard
    options:
      none:
        label: No Scaling
      standard:
        label: StandardScaler
  model:
    label: Classification Model
    default: random_forest
    options:
      random_forest:
        label: Random Forest
      svm:
        label: SVM
        requires:
          - scaling.standard
```

See the [full specification](https://astra-spec.org) for details on sub-analyses, evidence-backed insights, universes, constraints, and more.

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
