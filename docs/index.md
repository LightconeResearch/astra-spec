# ASTRA

**Agentic Schema for Transparent Research Analysis** — a declarative YAML format for scientific analyses that separates *what* you want to learn from *how* to compute it.

You declare inputs, outputs, and the decisions that shape the analysis. An agent or workflow engine reads the spec and produces results. Every analytical choice is documented, every alternative is recorded, and every decision can be backed by traceable evidence.

ASTRA is intentionally agnostic to any execution engine: agents, workflow runners, notebooks, or humans can all consume an ASTRA spec.

[:lucide-rocket: **Get started**](getting-started.md){ .md-button .md-button--primary }
[:lucide-book-open: Read the specification](specification.md){ .md-button }

## Why ASTRA?

Scientific analyses are built on a cascade of methodological choices — which algorithm, how to split the data, what priors to assume. These decisions are rarely documented systematically, and the alternatives considered are almost never recorded. That makes results hard to reproduce, hard to audit, and hard to revisit.

ASTRA gives every analytical choice an explicit place in the spec. Decisions name the options that were considered, link to evidence, and feed into a *universe* — one complete selection that yields one set of results. The collection of valid selections is the *multiverse*: not a grid search, but a transparent record of the design space.

## At a glance

=== "Analysis (`astra.yaml`)"

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
        decisions: [scaling, model]
        recipe:
          command: python src/evaluate.py

    decisions:
      scaling:
        label: Feature Scaling
        default: standard
        options:
          none: { label: No Scaling }
          standard: { label: StandardScaler }

      model:
        label: Classification Model
        default: random_forest
        options:
          random_forest: { label: Random Forest }
          svm:
            label: SVM
            requires: [scaling.standard]
    ```

=== "Universe (`universes/baseline.yaml`)"

    ```yaml
    id: baseline
    description: Default configuration

    decisions:
      scaling: standard
      model: random_forest
    ```

=== "Run it"

    ```bash
    uv tool install astra-tools

    astra validate astra.yaml
    astra info
    astra viz
    ```

---

[:simple-github: GitHub](https://github.com/LightconeResearch/astra-spec){ .md-button }
[:lucide-package: PyPI (`astra-tools`)](https://pypi.org/project/astra-tools/){ .md-button }
