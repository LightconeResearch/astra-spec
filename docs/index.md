# ASTRA

**Agentic Schema for Transparent Research Analysis** — a declarative YAML format for scientific analyses that separates *what* you want to learn from *how* to compute it.

You declare inputs, outputs, and the decisions that shape the analysis. An agent or workflow engine reads the spec and produces results. Every analytical choice is documented, every alternative is recorded, and every decision can be backed by traceable evidence.

ASTRA is intentionally agnostic to any execution engine: agents, workflow runners, or humans can all consume an ASTRA spec.

[:lucide-rocket: **Get started**](getting-started.md){ .md-button .md-button--primary }
[:lucide-book-open: Read the specification](specification/draft/){ .md-button }

!!! warning "Alpha development"
    ASTRA is in **early alpha**. The schema, CLI, and tooling are all still moving — expect breaking changes between minor versions, and pin the schema version in your analyses. Bug reports, design challenges, and use cases that the spec doesn't yet cover are exactly what we want to hear at this stage; please open an issue on the [GitHub repo](https://github.com/LightconeResearch/astra-spec/issues) or join the [Community](community.md) tab.

## Why ASTRA?

Scientific analyses are built on a cascade of methodological choices — which algorithm, how to split the data, what priors to assume. These decisions are rarely documented systematically, and the alternatives considered are almost never recorded. That makes results hard to reproduce, hard to audit, and hard to revisit.

ASTRA gives every analytical choice an explicit place in the spec. Decisions name the options that were considered, link to evidence, and feed into a *universe* — one complete selection that yields one set of results. The collection of valid selections is the *multiverse*.

## At a glance

Three pieces fit together: an **analysis** declares the design space, a **universe** picks one option per decision, and the **CLI** validates and inspects.

=== "Analysis (`astra.yaml`)"

    ```yaml
    version: "1.0"
    name: Iris Classification

    inputs:                          # data and prior analyses this one consumes
      - id: iris_data
        type: data
        source: sklearn.datasets.load_iris

    outputs:                         # what to produce; recipe says how
      - id: accuracy
        type: metric
        decisions: [scaling, model]  # decisions that parameterize this output
        recipe:
          command: python src/evaluate.py

    decisions:                       # the choice points
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
            requires: [scaling.standard]   # SVM is only valid with standard scaling
    ```

=== "Universe (`universes/baseline.yaml`)"

    ```yaml
    # One option per decision; the same analysis can have many universes.
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
